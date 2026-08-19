"""Helper para lectura individual de métricas desde PostgreSQL.

Función de conveniencia que ejecuta el db_mapping de una métrica
y construye un SourceManifest con metadatos de frescura.
"""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

from src.consejo.domain.entities import SourceManifest
from src.consejo.domain.value_objects import (
    Cut,
    FetchStatus,
    MetricId,
    MetricSource,
)


def read_metric(
    conn: "psycopg2.extensions.connection",
    metric_key: str,
    source: MetricSource,
    db_mapping: str,
    cut: Date,
    fetched_at: datetime | None = None,
) -> SourceManifest:
    """Lee una métrica individual desde PostgreSQL y retorna su manifiesto.

    Args:
        conn: Conexión psycopg2 activa.
        metric_key: Clave de la métrica (ej: 'registered_cpe').
        source: Fuente de datos (dim_user, fact_inscription, manual).
        db_mapping: SQL parametrizado de la métrica.
        cut: Fecha de corte del snapshot.
        fetched_at: Timestamp UTC de extracción (default: now).

    Returns:
        SourceManifest con filas, estado y frescura.
    """
    if fetched_at is None:
        fetched_at = datetime.now(timezone.utc)

    if source == MetricSource.MANUAL:
        return SourceManifest(
            metric_id=MetricId(metric_key),
            source=source,
            cut=Cut(cut),
            fetched_at=fetched_at,
            freshness_hours=0.0,
            rows=(),
            status=FetchStatus.EMPTY,
        )

    sql_stripped = db_mapping.strip()
    if not sql_stripped.upper().startswith("SELECT"):
        return SourceManifest(
            metric_id=MetricId(metric_key),
            source=source,
            cut=Cut(cut),
            fetched_at=fetched_at,
            freshness_hours=0.0,
            rows=(),
            status=FetchStatus.EMPTY,
        )

    try:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(sql_stripped, {"cut": cut.isoformat()})
            raw_rows = cur.fetchall()
            rows = [dict(r) for r in raw_rows]

            normalized = _normalize_rows(rows)
            freshness = _compute_freshness(fetched_at)

            return SourceManifest(
                metric_id=MetricId(metric_key),
                source=source,
                cut=Cut(cut),
                fetched_at=fetched_at,
                freshness_hours=freshness,
                rows=tuple(normalized),
                status=(
                    FetchStatus.EXTRACTED
                    if normalized
                    else FetchStatus.EMPTY
                ),
            )
    except Exception:
        return SourceManifest(
            metric_id=MetricId(metric_key),
            source=source,
            cut=Cut(cut),
            fetched_at=fetched_at,
            freshness_hours=0.0,
            rows=(),
            status=FetchStatus.FAILED,
        )


def _normalize_rows(
    rows: list[dict],
) -> list[dict]:
    """Asegura que cada fila tenga clave 'value' con el primer numérico."""
    result: list[dict] = []
    for row in rows:
        normalized = dict(row)
        if "value" not in normalized:
            for val in normalized.values():
                if isinstance(val, (int, float)):
                    normalized["value"] = val
                    break
        result.append(normalized)
    return result


def _compute_freshness(fetched_at: datetime) -> float:
    """Horas desde fetched_at hasta ahora."""
    delta = datetime.now(timezone.utc) - fetched_at
    return max(0.0, delta.total_seconds() / 3600.0)
