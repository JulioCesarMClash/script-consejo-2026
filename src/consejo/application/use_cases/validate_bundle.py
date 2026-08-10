"""Caso de uso: validación DQS y construcción del bundle canónico.

Ejecuta las 5 obligaciones DQS del dominio. Si hay fallos bloqueantes,
lanza DqsBlockedError sin construir el bundle. Si pasa, construye el
bundle canónico con hash SHA-256 idempotente.
"""

from __future__ import annotations

from typing import Sequence

from src.consejo.domain.entities import (
    Bundle,
    DqsIssue,
    Metric,
    SourceManifest,
)
from src.consejo.domain.dqs import validate
from src.consejo.domain.value_objects import AttemptId, Cut, PipelineMode, RunId


class DqsBlockedError(Exception):
    """El bundle no pasó la validación DQS y el snapshot está bloqueado.

    Atributos:
        issues: Lista de fallos DQS que causaron el bloqueo.
    """

    def __init__(self, issues: Sequence[DqsIssue]) -> None:
        self.issues = list(issues)
        blocker_codes = [
            i.code for i in self.issues if i.severity == "blocker"
        ]
        super().__init__(
            f"DQS validation blocked: {len(blocker_codes)} blocker(s) — "
            f"{', '.join(blocker_codes) if blocker_codes else 'none'}"
        )


def validate_bundle(
    manifests: Sequence[SourceManifest],
    catalog: Sequence[Metric],
    run_id: RunId,
    attempt_id: AttemptId,
    cut: Cut,
    catalog_hash: str,
    mode: PipelineMode = PipelineMode.DRY_RUN,
) -> Bundle:
    """Valida los manifiestos contra las 5 obligaciones DQS.

    Si todas las obligaciones pasan, construye el bundle canónico con
    claves ordenadas, fechas ISO 8601 UTC, y hash SHA-256 calculado
    sin incluir el propio campo hash.

    Args:
        manifests: Manifiestos extraídos para este intento.
        catalog: Catálogo completo de métricas (autoridad).
        run_id: Identificador de la corrida.
        attempt_id: Identificador del intento.
        cut: Fecha de corte del snapshot.
        catalog_hash: Hash SHA-256 del catálogo usado.

    Returns:
        Bundle canónico con hash SHA-256.

    Raises:
        DqsBlockedError: Si al menos una obligación DQS bloqueante falla.
    """
    report = validate(manifests, catalog, mode=mode)

    if not report.passed:
        raise DqsBlockedError(report.issues)

    rows = _collect_rows(manifests)

    bundle = Bundle(
        run_id=run_id,
        attempt_id=attempt_id,
        cut=cut,
        catalog_hash=catalog_hash,
        manifests=tuple(manifests),
        rows=tuple(rows),
        dqs=tuple(report.issues),
    )
    real_hash = bundle.compute_hash()

    return Bundle(
        run_id=run_id,
        attempt_id=attempt_id,
        cut=cut,
        catalog_hash=catalog_hash,
        manifests=tuple(manifests),
        rows=tuple(rows),
        dqs=tuple(report.issues),
        hash=real_hash,
    )


def _collect_rows(
    manifests: Sequence[SourceManifest],
) -> list[dict[str, object]]:
    """Recolecta y enriquece las filas de todos los manifiestos extraídos.

    Cada fila se enriquece con metric_id y source para trazabilidad.
    """
    rows: list[dict[str, object]] = []
    for m in manifests:
        for row in m.rows:
            enriched = dict(row)
            enriched["metric_id"] = str(m.metric_id)
            enriched["source"] = m.source.value
            rows.append(enriched)
    return rows
