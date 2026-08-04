"""CLI del pipeline de snapshot para Corte 1.

Comandos:
    extract   — Extrae métricas y emite JSON de manifiestos.
    validate  — Valida manifiestos contra DQS y construye bundle.
    snapshot  — Crea snapshot en Google Sheets.
    pipeline  — Ejecuta extract → validate → snapshot.
"""

from __future__ import annotations

import json
import sys
from datetime import date as Date
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click

from src.consejo.adapters.catalog.yaml_metric_repo import YamlMetricRepo
from src.consejo.adapters.postgres.source_conn import PostgresSourceConn
from src.consejo.adapters.sheets.google_mcp_sheet_repo import (
    GoogleMcpSheetRepo,
)
from src.consejo.application.use_cases.create_snapshot import (
    create_snapshot,
)
from src.consejo.application.use_cases.extract_data import extract_data
from src.consejo.application.use_cases.validate_bundle import (
    DqsBlockedError,
    validate_bundle,
)
from src.consejo.config.settings import Settings
from src.consejo.domain.value_objects import AttemptId, Cut, RunId


@click.group()
def main() -> None:
    """Pipeline de snapshot — Consejo 2026."""


@main.command()
@click.option(
    "--cut",
    required=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Fecha de corte (YYYY-MM-DD).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Emitir manifiestos por stdout sin DB.",
)
def extract(cut: datetime, dry_run: bool) -> None:
    """Extrae métricas del catálogo y emite manifiestos JSON."""
    cut_date: Date = cut.date()
    fetched_at = datetime.now(timezone.utc)
    run_id = RunId.generate()
    attempt_id = AttemptId.generate()

    settings = Settings()
    metric_repo = YamlMetricRepo(settings.catalog_path)
    source_conn = PostgresSourceConn(settings)

    try:
        manifests = extract_data(
            metric_repo=metric_repo,
            source_conn=source_conn,
            run_id=run_id,
            attempt_id=attempt_id,
            cut=cut_date,
            fetched_at=fetched_at,
        )
    except ConnectionError as e:
        if dry_run:
            manifests = []
            click.echo(
                f"# Dry-run: conexión DB no disponible ({e})",
                err=True,
            )
        else:
            raise click.ClickException(str(e)) from e

    output = _serialize_manifests(manifests, run_id, attempt_id, cut_date)
    click.echo(json.dumps(output, ensure_ascii=False, indent=2))


@main.command()
@click.option(
    "--cut",
    required=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Fecha de corte (YYYY-MM-DD).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Usar datos mock en vez de DB real.",
)
def validate(cut: datetime, dry_run: bool) -> None:
    """Valida métricas contra DQS y construye bundle canónico."""
    cut_date: Date = cut.date()
    run_id = RunId.generate()
    attempt_id = AttemptId.generate()

    settings = Settings()
    metric_repo = YamlMetricRepo(settings.catalog_path)
    catalog = list(metric_repo.list_metrics())
    catalog_hash = metric_repo.compute_catalog_hash()
    source_conn = PostgresSourceConn(settings)

    try:
        manifests = extract_data(
            metric_repo=metric_repo,
            source_conn=source_conn,
            run_id=run_id,
            attempt_id=attempt_id,
            cut=cut_date,
        )
    except ConnectionError as e:
        if dry_run:
            manifests = []
            click.echo(
                f"# Dry-run: usando 0 manifiestos ({e})",
                err=True,
            )
        else:
            raise click.ClickException(str(e)) from e

    try:
        bundle = validate_bundle(
            manifests=manifests,
            catalog=catalog,
            run_id=run_id,
            attempt_id=attempt_id,
            cut=Cut(cut_date),
            catalog_hash=catalog_hash,
        )
    except DqsBlockedError as e:
        raise click.ClickException(str(e)) from e

    result = {
        "status": "validated",
        "run_id": str(bundle.run_id),
        "attempt_id": str(bundle.attempt_id),
        "cut": bundle.cut.isoformat(),
        "catalog_hash": bundle.catalog_hash,
        "hash": str(bundle.hash),
        "manifests_count": len(bundle.manifests),
        "rows_count": len(bundle.rows),
        "dqs_issues": len(bundle.dqs),
        "canonical_json": bundle.canonical_json(),
    }
    click.echo(json.dumps(result, ensure_ascii=False, indent=2))


@main.command()
@click.option(
    "--cut",
    required=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Fecha de corte (YYYY-MM-DD).",
)
@click.option(
    "--spreadsheet-id",
    required=True,
    help="ID del spreadsheet Google Sheets destino.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Emitir bundle JSON por stdout sin escribir Sheets.",
)
def snapshot(cut: datetime, spreadsheet_id: str, dry_run: bool) -> None:
    """Crea snapshot en Google Sheets."""
    cut_date: Date = cut.date()
    run_id = RunId.generate()
    attempt_id = AttemptId.generate()

    settings = Settings()
    metric_repo = YamlMetricRepo(settings.catalog_path)
    catalog = list(metric_repo.list_metrics())
    catalog_hash = metric_repo.compute_catalog_hash()
    source_conn = PostgresSourceConn(settings)

    try:
        manifests = extract_data(
            metric_repo=metric_repo,
            source_conn=source_conn,
            run_id=run_id,
            attempt_id=attempt_id,
            cut=cut_date,
        )
    except ConnectionError as e:
        raise click.ClickException(str(e)) from e

    try:
        bundle = validate_bundle(
            manifests=manifests,
            catalog=catalog,
            run_id=run_id,
            attempt_id=attempt_id,
            cut=Cut(cut_date),
            catalog_hash=catalog_hash,
        )
    except DqsBlockedError as e:
        raise click.ClickException(str(e)) from e

    if dry_run:
        click.echo(bundle.canonical_json())
        return

    sheet_repo = GoogleMcpSheetRepo()
    try:
        sid = create_snapshot(bundle, sheet_repo)
        click.echo(f"Snapshot creado: {sid}")
        click.echo(f"Hash: {bundle.hash}")
    except Exception as e:
        raise click.ClickException(str(e)) from e


@main.command()
@click.option(
    "--cut",
    required=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Fecha de corte (YYYY-MM-DD).",
)
@click.option(
    "--spreadsheet-id",
    required=True,
    help="ID del spreadsheet Google Sheets destino.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="No escribir Sheets, emitir bundle por stdout.",
)
def pipeline(cut: datetime, spreadsheet_id: str, dry_run: bool) -> None:
    """Ejecuta el pipeline completo: extract → validate → snapshot."""
    cut_date: Date = cut.date()
    run_id = RunId.generate()
    attempt_id = AttemptId.generate()
    fetched_at = datetime.now(timezone.utc)

    settings = Settings()
    metric_repo = YamlMetricRepo(settings.catalog_path)
    catalog = list(metric_repo.list_metrics())
    catalog_hash = metric_repo.compute_catalog_hash()
    source_conn = PostgresSourceConn(settings)

    # Extract
    try:
        manifests = extract_data(
            metric_repo=metric_repo,
            source_conn=source_conn,
            run_id=run_id,
            attempt_id=attempt_id,
            cut=cut_date,
            fetched_at=fetched_at,
        )
    except ConnectionError as e:
        raise click.ClickException(str(e)) from e
    click.echo(
        f"[extract] {len(manifests)} manifiestos extraídos", err=True
    )

    # Validate
    try:
        bundle = validate_bundle(
            manifests=manifests,
            catalog=catalog,
            run_id=run_id,
            attempt_id=attempt_id,
            cut=Cut(cut_date),
            catalog_hash=catalog_hash,
        )
    except DqsBlockedError as e:
        raise click.ClickException(str(e)) from e
    click.echo(
        f"[validate] DQS OK — bundle hash: {str(bundle.hash)[:16]}...",
        err=True,
    )

    if dry_run:
        click.echo(bundle.canonical_json())
        return

    # Snapshot
    sheet_repo = GoogleMcpSheetRepo()
    try:
        sid = create_snapshot(bundle, sheet_repo)
        click.echo(f"[snapshot] Creado en {sid}")
    except Exception as e:
        raise click.ClickException(str(e)) from e

    click.echo(f"Pipeline completo. Hash: {bundle.hash}")


# ── Helpers ─────────────────────────────────────────────────────────────────


def _serialize_manifests(
    manifests: list,
    run_id: RunId,
    attempt_id: AttemptId,
    cut_date: Date,
) -> dict:
    """Serializa manifiestos a diccionario para JSON output."""
    result: dict = {
        "run_id": str(run_id),
        "attempt_id": str(attempt_id),
        "cut": cut_date.isoformat(),
        "manifests_count": len(manifests),
        "manifests": [],
    }
    for m in manifests:
        result["manifests"].append({
            "metric_id": str(m.metric_id),
            "source": m.source.value,
            "status": m.status.value,
            "rows": [dict(r) for r in m.rows],
            "fetched_at": m.fetched_at.isoformat(),
            "freshness_hours": m.freshness_hours,
        })
    return result


if __name__ == "__main__":
    main()
