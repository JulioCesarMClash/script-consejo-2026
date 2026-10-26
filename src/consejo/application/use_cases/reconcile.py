"""Reconciliación PostgreSQL vs Athena para la migración al datalake.

Corre cada métrica traducida (con `athena_mapping` no vacío) contra ambas
fuentes con los MISMOS parámetros y compara el valor escalar `value`.

La reconciliación es OBLIGATORIA antes de confiar en Athena: una diferencia
inesperada BLOQUEA (no basta con que ambas queries corran sin error).

Clasificación por fila:
- OK:    valores idénticos.
- WARN:  difieren pero dentro de la tolerancia declarada (abs o %).
- BLOCK: difieren fuera de tolerancia, o una fuente falló.

Las métricas `db_source: mysql` se omiten: no viven en el lake, así que
no hay nada que reconciliar contra Athena.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as Date
from typing import Mapping, Sequence

from src.consejo.application.ports import MetricRepo, SourceConn
from src.consejo.domain.value_objects import MetricSource


@dataclass(frozen=True)
class ReconcileRow:
    """Resultado de reconciliar una métrica entre PG y Athena."""

    metric_key: str
    pg_value: float | None
    athena_value: float | None
    diff_abs: float | None
    diff_pct: float | None
    status: str  # "OK" | "WARN" | "BLOCK"
    detail: str = ""


@dataclass(frozen=True)
class ReconcileReport:
    """Reporte agregado de la reconciliación."""

    rows: Sequence[ReconcileRow]

    @property
    def blocked(self) -> bool:
        """True si alguna métrica quedó en BLOCK: el corte a Athena no procede."""
        return any(r.status == "BLOCK" for r in self.rows)

    @property
    def counts(self) -> dict[str, int]:
        c = {"OK": 0, "WARN": 0, "BLOCK": 0}
        for r in self.rows:
            c[r.status] = c.get(r.status, 0) + 1
        return c


def reconcile(
    metric_repo: MetricRepo,
    pg_conn: SourceConn,
    athena_conn: SourceConn,
    cut: Date,
    query_params: Mapping[str, object] | None = None,
    tolerance_abs: float = 0.0,
    tolerance_pct: float = 0.0,
    only_keys: Sequence[str] | None = None,
) -> ReconcileReport:
    """Reconcilia PG vs Athena para las métricas traducidas.

    Args:
        metric_repo: Catálogo de métricas.
        pg_conn: Adaptador PostgreSQL (ejecuta db_mapping).
        athena_conn: Adaptador Athena (ejecuta athena_mapping).
        cut: Fecha de corte.
        query_params: Parámetros extra (period_start, period_end).
        tolerance_abs: Diferencia absoluta tolerada (default 0 = exacto).
        tolerance_pct: Diferencia porcentual tolerada, 0..100 (default 0).
        only_keys: Si se provee, reconcilia solo esas keys (piloto).

    Returns:
        ReconcileReport con una fila por métrica evaluada.
    """
    base_params: dict[str, object] = {"cut": cut.isoformat()}
    if query_params:
        base_params.update(query_params)

    rows: list[ReconcileRow] = []
    for metric in metric_repo.list_metrics():
        if only_keys is not None and metric.key not in only_keys:
            continue
        # Solo métricas que viven en el lake y están traducidas.
        if metric.source == MetricSource.MANUAL:
            continue
        if metric.db_source == "mysql":
            continue
        if not metric.athena_mapping.strip():
            continue

        pg_value, pg_err = _run_scalar(
            pg_conn, metric.db_mapping, base_params, metric.reconcile_column
        )
        ath_value, ath_err = _run_scalar(
            athena_conn, metric.athena_mapping, base_params,
            metric.reconcile_column,
        )

        rows.append(
            _classify(
                metric.key,
                pg_value,
                ath_value,
                pg_err,
                ath_err,
                tolerance_abs,
                tolerance_pct,
            )
        )

    return ReconcileReport(rows=tuple(rows))


def _run_scalar(
    conn: SourceConn,
    sql: str,
    params: Mapping[str, object],
    column: str = "value",
) -> tuple[float | None, str]:
    """Ejecuta una query y agrega la columna `column` sobre todas las filas.

    Devuelve (total, "") en éxito, o (None, mensaje_error) si falla o no
    hay valor numérico. Para métricas multi-fila (slide1/slide2) suma la
    columna objetivo de todas las filas: reconcilia el agregado, no fila a
    fila. `column` default "value"; slides pueden apuntar a 'certificados'.
    """
    try:
        result = conn.fetch(sql.strip(), params)
    except Exception as e:
        return None, str(e)[:200]

    if not result:
        return None, "sin filas"

    total = 0.0
    found = False
    for row in result:
        v = _numeric(row, column)
        if v is not None:
            total += v
            found = True
    if not found:
        return None, f"sin columna numérica '{column}'"
    return total, ""


def _numeric(row: Mapping[str, object], column: str = "value") -> float | None:
    """Extrae el valor numérico de `column` (o el primer numérico si falta)."""
    if column in row and isinstance(row[column], (int, float)) and not isinstance(
        row[column], bool
    ):
        return float(row[column])
    if "value" in row and isinstance(row["value"], (int, float)):
        return float(row["value"])
    for v in row.values():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
    return None


def _classify(
    metric_key: str,
    pg_value: float | None,
    athena_value: float | None,
    pg_err: str,
    athena_err: str,
    tolerance_abs: float,
    tolerance_pct: float,
) -> ReconcileRow:
    """Clasifica la fila en OK / WARN / BLOCK."""
    if pg_value is None or athena_value is None:
        detail = []
        if pg_err:
            detail.append(f"PG: {pg_err}")
        if athena_err:
            detail.append(f"Athena: {athena_err}")
        return ReconcileRow(
            metric_key=metric_key,
            pg_value=pg_value,
            athena_value=athena_value,
            diff_abs=None,
            diff_pct=None,
            status="BLOCK",
            detail="; ".join(detail) or "fuente sin valor",
        )

    diff_abs = abs(pg_value - athena_value)
    diff_pct = (diff_abs / abs(pg_value) * 100.0) if pg_value else (
        0.0 if diff_abs == 0 else 100.0
    )

    if diff_abs == 0:
        status = "OK"
    elif diff_abs <= tolerance_abs or diff_pct <= tolerance_pct:
        status = "WARN"
    else:
        status = "BLOCK"

    return ReconcileRow(
        metric_key=metric_key,
        pg_value=pg_value,
        athena_value=athena_value,
        diff_abs=diff_abs,
        diff_pct=diff_pct,
        status=status,
        detail="",
    )
