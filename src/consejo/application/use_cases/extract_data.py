"""Use case: metric extraction with traceable manifests.

    Iterates the metric catalog, runs SQL queries via SourceConn, and builds a
    SourceManifest per metric. Derived sum metrics are built from their
    component manifests without running queries.
"""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime, timezone
from typing import Mapping, Sequence

from src.consejo.application.ports import MetricRepo, SourceConn
from src.consejo.domain.entities import SourceManifest
from src.consejo.domain.value_objects import (
    AttemptId,
    Cut,
    FetchStatus,
    MetricId,
    MetricSource,
    RunId,
)


# Derived sum metrics: computed from two pre-extracted parts, never fetched
# directly from the database. Keyed by the derived metric key, mapping to the
# two component metric keys that must each be EXTRACTED first.
_SUM_PARTS: dict[str, tuple[str, str]] = {
    "registered_total": ("registered_cpe", "registered_aprende"),
    "inscriptions_cpe_total": (
        "inscriptions_cpe",
        "inscriptions_cpe_from_aprende",
    ),
    "certifications_cpe_total": (
        "certifications_cpe",
        "certifications_cpe_from_aprende",
    ),
    "certified_unique_cpe_total": (
        "certified_unique_cpe",
        "certified_unique_cpe_from_aprende",
    ),
    "beneficiaries_unique": (
        "inscribed_unique_cpe",
        "inscribed_unique_cpe_from_aprende",
    ),
    "beneficiaries": ("registered_cpe", "inscribed_unique_cpe_from_aprende"),
}


def extract_data(
    metric_repo: MetricRepo,
    source_conn: SourceConn,
    run_id: RunId,
    attempt_id: AttemptId,
    cut: Date,
    fetched_at: datetime | None = None,
    query_params: Mapping[str, object] | None = None,
    mysql_conn: SourceConn | None = None,
) -> list[SourceManifest]:
    """Extracts metrics from the catalog and builds traceable manifests.

    Two passes over the catalog, so derived sums are computed regardless of the
    order in which their parts appear:
    - Pass 1: extract every metric whose key is NOT in _SUM_PARTS. For those:
      - source manual -> manifest without a DB query and without rows.
      - non-SQL db_mapping (other textual formulas) -> EMPTY manifest.
      - SQL db_mapping -> execute via SourceConn.fetch and normalize rows.
      - Query failure -> manifest with FAILED status.
    - Pass 2: for each metric whose key IS in _SUM_PARTS, build the sum from
      its two pre-extracted parts via _build_automatic_sum.

    Si una métrica tiene `db_source == "mysql"` y se provee `mysql_conn`, la
    consulta se ejecuta contra MySQL; en caso contrario, se usa
    `source_conn` (PostgreSQL por default). Si `mysql_conn` es None, todas las
    métricas se extraen contra `source_conn`, manteniendo compatibilidad
    hacia atrás.

    Args:
        metric_repo: Metric repository backed by the catalog.
        source_conn: Database connection used for extraction (default PG).
        run_id: Identifier of the run.
        attempt_id: Identifier of the attempt.
        cut: Snapshot cut-off date.
        fetched_at: UTC extraction timestamp. If None, now() is used.
        mysql_conn: Conexión MySQL opcional para métricas con
            `db_source: "mysql"`.

    Returns:
        List of SourceManifest, one per catalog metric, in catalog order.
    """
    if fetched_at is None:
        fetched_at = datetime.now(timezone.utc)

    metrics = list(metric_repo.list_metrics())
    by_key: dict[str, SourceManifest] = {}

    # Pass 1: normal extraction (skip derived sum metrics; defer them).
    for metric in metrics:
        if metric.key in _SUM_PARTS:
            continue

        if metric.source == MetricSource.MANUAL:
            by_key[metric.key] = _build_manifest(
                metric_key=metric.key,
                source=metric.source,
                cut=cut,
                fetched_at=fetched_at,
                freshness_hours=0.0,
                rows=(),
                status=FetchStatus.EMPTY,
            )
            continue

        db_mapping = metric.db_mapping.strip()

        if not _is_executable_sql(db_mapping):
            by_key[metric.key] = _build_manifest(
                metric_key=metric.key,
                source=metric.source,
                cut=cut,
                fetched_at=fetched_at,
                freshness_hours=0.0,
                rows=(),
                status=FetchStatus.EMPTY,
            )
            continue

        conn = _select_conn(metric.db_source, source_conn, mysql_conn)
        try:
            params = {"cut": cut.isoformat()}
            if query_params:
                params.update(query_params)
            raw_rows = conn.fetch(db_mapping, params)
            normalized = _normalize_rows(raw_rows)
            freshness = _compute_freshness_hours(fetched_at)
            status = (
                FetchStatus.EXTRACTED if normalized else FetchStatus.EMPTY
            )
        except Exception:
            normalized = ()
            freshness = 0.0
            status = FetchStatus.FAILED

        by_key[metric.key] = _build_manifest(
            metric_key=metric.key,
            source=metric.source,
            cut=cut,
            fetched_at=fetched_at,
            freshness_hours=freshness,
            rows=tuple(normalized),
            status=status,
        )

    # Pass 2: derived sums, built from their already-extracted parts.
    for metric in metrics:
        if metric.key not in _SUM_PARTS:
            continue
        part_a_key, part_b_key = _SUM_PARTS[metric.key]
        by_key[metric.key] = _build_automatic_sum(
            metric_key=metric.key,
            source=metric.source,
            part_a_key=part_a_key,
            part_b_key=part_b_key,
            by_key=by_key,
            cut=cut,
            fetched_at=fetched_at,
        )

    return [by_key[metric.key] for metric in metrics]


# ── Helpers ─────────────────────────────────────────────────────────────────


def _build_manifest(
    *,
    metric_key: str,
    source: MetricSource,
    cut: Date,
    fetched_at: datetime,
    freshness_hours: float,
    rows: Sequence[Mapping[str, object]],
    status: FetchStatus,
) -> SourceManifest:
    """Construye un SourceManifest con los valores dados."""
    return SourceManifest(
        metric_id=MetricId(metric_key),
        source=source,
        cut=Cut(cut),
        fetched_at=fetched_at,
        freshness_hours=freshness_hours,
        rows=rows,
        status=status,
    )


def _is_executable_sql(db_mapping: str) -> bool:
    """Devuelve True si db_mapping es una consulta SQL ejecutable.

    Acepta SELECT y CTEs (WITH ... SELECT), que también son ejecutables.
    """
    stripped = db_mapping.upper().strip()
    return stripped.startswith("SELECT") or stripped.startswith("WITH")


def _select_conn(
    db_source: str,
    pg_conn: SourceConn,
    mysql_conn: SourceConn | None,
) -> SourceConn:
    """Elige la conexión a usar para una métrica según su `db_source`.

    Convención:
    - `db_source == "mysql"` y `mysql_conn` provisto -> MySQL.
    - `db_source == "mysql"` y `mysql_conn` NO provisto -> fallback a PG
      (la falla se registrará como FAILED en el manifiesto si MySQL no
      estuviera disponible, evitando crashes silenciosos).
    - cualquier otro valor (incluido "postgres", default, vacío) -> PG.
    """
    if db_source == "mysql" and mysql_conn is not None:
        return mysql_conn
    return pg_conn


def _normalize_rows(
    rows: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Normaliza las filas asegurando que tengan clave 'value'.

    Si la fila no tiene clave 'value', extrae el primer valor numérico
    y lo asigna bajo esa clave.
    """
    result: list[dict[str, object]] = []
    for row in rows:
        normalized = dict(row)
        if "value" not in normalized:
            for val in normalized.values():
                if isinstance(val, (int, float)):
                    normalized["value"] = val
                    break
        result.append(normalized)
    return result


def _compute_freshness_hours(fetched_at: datetime) -> float:
    """Calcula las horas transcurridas desde fetched_at."""
    delta = datetime.now(timezone.utc) - fetched_at
    return max(0.0, delta.total_seconds() / 3600.0)


def _build_automatic_sum(
    *,
    metric_key: str,
    source: MetricSource,
    part_a_key: str,
    part_b_key: str,
    by_key: Mapping[str, SourceManifest],
    cut: Date,
    fetched_at: datetime,
) -> SourceManifest:
    """Builds a derived sum metric from its two pre-extracted parts.

    If either part is missing or not EXTRACTED, the derived metric becomes an
    EMPTY manifest with no rows. Otherwise it sums both part values, marks the
    manifest EXTRACTED, and uses the freshest of the two parts.
    """
    part_a = by_key.get(part_a_key)
    part_b = by_key.get(part_b_key)
    values = [_extract_numeric_value(part_a), _extract_numeric_value(part_b)]

    if any(value is None for value in values):
        return _build_manifest(
            metric_key=metric_key,
            source=source,
            cut=cut,
            fetched_at=fetched_at,
            freshness_hours=0.0,
            rows=(),
            status=FetchStatus.EMPTY,
        )

    return _build_manifest(
        metric_key=metric_key,
        source=source,
        cut=cut,
        fetched_at=fetched_at,
        freshness_hours=max(
            part_a.freshness_hours, part_b.freshness_hours
        ),
        rows=({"value": sum(values)},),
        status=FetchStatus.EXTRACTED,
    )


def _extract_numeric_value(manifest: SourceManifest | None) -> int | None:
    if manifest is None or manifest.status != FetchStatus.EXTRACTED:
        return None
    for value in manifest.rows[0].values() if manifest.rows else ():
        if isinstance(value, (int, float)):
            return int(value)
    return None
