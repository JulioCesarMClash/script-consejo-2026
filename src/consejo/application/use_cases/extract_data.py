"""Caso de uso: extracción de métricas con manifiestos trazables.

Itera el catálogo de métricas, ejecuta las consultas SQL vía SourceConn,
y construye un SourceManifest por métrica. Respeta las métricas manuales
y las fórmulas textuales (tipo sum) sin ejecutar consultas.
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


def extract_data(
    metric_repo: MetricRepo,
    source_conn: SourceConn,
    run_id: RunId,
    attempt_id: AttemptId,
    cut: Date,
    fetched_at: datetime | None = None,
) -> list[SourceManifest]:
    """Extrae métricas del catálogo y construye manifiestos trazables.

    Para cada métrica del catálogo:
    - source: manual → manifiesto sin consulta DB, sin filas.
    - db_mapping no SQL (fórmulas textuales sum) → manifiesto vacío.
    - db_mapping SQL → ejecuta vía SourceConn.fetch, normaliza filas.
    - Fallo en consulta → manifiesto con status FAILED.

    Args:
        metric_repo: Repositorio de métricas del catálogo.
        source_conn: Conexión a base de datos para extracción.
        run_id: Identificador de la corrida.
        attempt_id: Identificador del intento.
        cut: Fecha de corte del snapshot.
        fetched_at: Timestamp UTC de extracción. Si es None, se usa now().

    Returns:
        Lista de 16 SourceManifest, uno por métrica del catálogo.
    """
    if fetched_at is None:
        fetched_at = datetime.now(timezone.utc)

    metrics = list(metric_repo.list_metrics())
    manifests: list[SourceManifest] = []

    for metric in metrics:
        if metric.source == MetricSource.MANUAL:
            manifests.append(
                _build_manifest(
                    metric_key=metric.key,
                    source=metric.source,
                    cut=cut,
                    fetched_at=fetched_at,
                    freshness_hours=0.0,
                    rows=(),
                    status=FetchStatus.EMPTY,
                )
            )
            continue

        db_mapping = metric.db_mapping.strip()

        if not _is_executable_sql(db_mapping):
            manifests.append(
                _build_manifest(
                    metric_key=metric.key,
                    source=metric.source,
                    cut=cut,
                    fetched_at=fetched_at,
                    freshness_hours=0.0,
                    rows=(),
                    status=FetchStatus.EMPTY,
                )
            )
            continue

        try:
            raw_rows = source_conn.fetch(db_mapping, {"cut": cut.isoformat()})
            normalized = _normalize_rows(raw_rows)
            freshness = _compute_freshness_hours(fetched_at)
            status = (
                FetchStatus.EXTRACTED if normalized else FetchStatus.EMPTY
            )
        except Exception:
            normalized = ()
            freshness = 0.0
            status = FetchStatus.FAILED

        manifests.append(
            _build_manifest(
                metric_key=metric.key,
                source=metric.source,
                cut=cut,
                fetched_at=fetched_at,
                freshness_hours=freshness,
                rows=tuple(normalized),
                status=status,
            )
        )

    return manifests


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
    """Devuelve True si db_mapping es una consulta SQL ejecutable."""
    return db_mapping.upper().strip().startswith("SELECT")


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
