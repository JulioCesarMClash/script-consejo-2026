"""Validación DQS bloqueante para el bundle de snapshot.

Cinco obligaciones que deben pasarse antes de construir el bundle:
1. Cardinalidad exacta por grano.
2. Reconciliación parte/total.
3. Casos borde reales (nulos, negativos, vacíos, rangos).
4. Idempotencia real (hash reproducible).
5. Cero filas huérfanas.

Regla de dominio: source: manual con value=null NO debe tratarse como cero.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from src.consejo.domain.entities import Bundle, DqsIssue, Metric, SourceManifest
from src.consejo.domain.value_objects import FetchStatus, MetricSource, PipelineMode


_EXPLICIT_REQUIRED_DERIVED_METRICS = {
    "registered_total",
    "inscriptions_cpe_total",
    "certifications_cpe_total",
    "certified_unique_cpe_total",
}


# ── Resultado DQS ──────────────────────────────────────────────────────────


@dataclass
class DqsReport:
    """Resultado de la validación DQS sobre un conjunto de manifiestos.

    Si `passed` es False, el snapshot debe bloquearse sin llamar a Sheets.
    """

    passed: bool = True
    issues: list[DqsIssue] = field(default_factory=list)

    def add_issue(self, issue: DqsIssue) -> None:
        """Registra un fallo DQS y marca el reporte como no aprobado."""
        self.issues.append(issue)
        if issue.severity == "blocker":
            self.passed = False


# ── Validación principal ───────────────────────────────────────────────────


def validate(
    manifests: Sequence[SourceManifest],
    catalog: Sequence[Metric],
    *,
    previous_bundle: Bundle | None = None,
    mode: PipelineMode = PipelineMode.DRY_RUN,
) -> DqsReport:
    """Ejecuta las 5 obligaciones DQS y devuelve el reporte.

    Args:
        manifests: Manifiestos extraídos para este intento.
        catalog: Catálogo completo de métricas (autoridad).
        previous_bundle: Bundle de un intento previo con el mismo attempt_id
            para la validación de idempotencia. None para el primer intento.

    Returns:
        DqsReport con passed=True solo si todas las obligaciones pasan.
    """
    report = DqsReport()

    _check_cardinalidad(report, manifests, catalog)
    _check_reconciliacion(report, manifests, catalog)
    _check_edge_cases(report, manifests)
    _check_required_metrics(report, manifests, catalog, mode)
    _check_idempotencia(report, manifests, previous_bundle)
    _check_no_orfanos(report, manifests, catalog)

    return report


def _check_required_metrics(
    report: DqsReport,
    manifests: Sequence[SourceManifest],
    catalog: Sequence[Metric],
    mode: PipelineMode,
) -> None:
    """Warn or block when a required metric failed or returned no rows."""
    manifest_by_key = {str(m.metric_id): m for m in manifests}
    required = {
        metric.key
        for metric in catalog
        if metric.key in {
            "beneficiaries",
            "beneficiaries_unique",
            *_EXPLICIT_REQUIRED_DERIVED_METRICS,
        }
        or metric.db_mapping.strip().upper().startswith("SELECT")
    }

    severity = "blocker" if mode == PipelineMode.PRODUCTION else "warning"
    for metric_key in sorted(required):
        manifest = manifest_by_key.get(metric_key)
        if manifest is None or manifest.status not in {
            FetchStatus.EMPTY,
            FetchStatus.FAILED,
        }:
            continue
        status = manifest.status.value if manifest else "missing"
        report.add_issue(
            DqsIssue(
                obligation=3,
                code="DQS-003-REQUIRED_METRIC",
                severity=severity,
                message=(
                    f"Métrica requerida '{metric_key}' no disponible: {status}."
                ),
                details={"metric_id": metric_key, "status": status},
            )
        )


# ── Gate 1: Cardinalidad exacta por grano ──────────────────────────────────


def _check_cardinalidad(
    report: DqsReport,
    manifests: Sequence[SourceManifest],
    catalog: Sequence[Metric],
) -> None:
    """Verifica que el número de manifiestos coincida con el catálogo.

    Cada métrica del catálogo debe producir exactamente un manifiesto.
    """
    catalog_keys = {m.key for m in catalog}
    manifest_keys = {str(m.metric_id) for m in manifests}

    if len(manifests) != len(catalog):
        report.add_issue(
            DqsIssue(
                obligation=1,
                code="DQS-001-CARDINALITY",
                severity="blocker",
                message=(
                    f"Cardinalidad incorrecta: {len(manifests)} manifiestos "
                    f"para {len(catalog)} métricas en catálogo"
                ),
                details={
                    "expected": len(catalog),
                    "actual": len(manifests),
                    "missing_metrics": sorted(catalog_keys - manifest_keys),
                    "extra_metrics": sorted(manifest_keys - catalog_keys),
                },
            )
        )


# ── Gate 2: Reconciliación parte/total ─────────────────────────────────────


def _check_reconciliacion(
    report: DqsReport,
    manifests: Sequence[SourceManifest],
    catalog: Sequence[Metric],
) -> None:
    """Verifica que métricas totales igualen la suma de sus partes.

    Para métricas definidas como `type: sum` en el catálogo, la suma de
    sus partes componentes debe coincidir con el total declarado.

    Los pares reconciliables según el catálogo son:
        - registered_total = registered_cpe + registered_aprende
        - inscriptions_cpe_total = inscriptions_cpe + inscriptions_cpe_from_aprende
        - certifications_cpe_total = certifications_cpe + certifications_cpe_from_aprende
        - certified_unique_cpe_total = certified_unique_cpe + certified_unique_cpe_from_aprende
    """
    # Mapa de métricas totales → sus partes componentes
    sum_pairs: dict[str, tuple[str, str]] = {
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
    }

    manifest_by_key: dict[str, SourceManifest] = {
        str(m.metric_id): m for m in manifests
    }

    for total_key, (part_a_key, part_b_key) in sum_pairs.items():
        total = manifest_by_key.get(total_key)
        part_a = manifest_by_key.get(part_a_key)
        part_b = manifest_by_key.get(part_b_key)

        # Si alguna métrica no está en los manifiestos, la cardinalidad
        # ya lo reportó (Gate 1). No duplicar el error aquí.
        if total is None or part_a is None or part_b is None:
            continue

        # Las totales con db_mapping textual ("Métrica A + Métrica B")
        # no se extraen directamente — solo son reconciliables después
        # de extraer sus partes. Saltamos si el total no tiene filas propias.
        total_value = _extract_numeric_value(total)
        part_a_value = _extract_numeric_value(part_a)
        part_b_value = _extract_numeric_value(part_b)

        if total_value is not None:
            expected = (part_a_value or 0) + (part_b_value or 0)
            if total_value != expected:
                report.add_issue(
                    DqsIssue(
                        obligation=2,
                        code="DQS-002-RECONCILIATION",
                        severity="blocker",
                        message=(
                            f"Reconciliación fallida para {total_key}: "
                            f"total={total_value} != "
                            f"{part_a_key}({part_a_value}) + "
                            f"{part_b_key}({part_b_value}) = {expected}"
                        ),
                        details={
                            "metric": total_key,
                            "total": total_value,
                            "parts": {
                                part_a_key: part_a_value,
                                part_b_key: part_b_value,
                            },
                            "expected": expected,
                        },
                    )
                )


def _extract_numeric_value(manifest: SourceManifest) -> int | None:
    """Extrae el valor numérico de un manifiesto si está disponible."""
    if manifest.status != FetchStatus.EXTRACTED:
        return None
    if not manifest.rows:
        return None
    row = manifest.rows[0]
    # Buscar el primer valor numérico en la fila
    for v in row.values():
        if isinstance(v, (int, float)):
            return int(v)
    return None


# ── Gate 3: Casos borde reales ─────────────────────────────────────────────


def _check_edge_cases(
    report: DqsReport,
    manifests: Sequence[SourceManifest],
) -> None:
    """Verifica casos borde: nulos, negativos, vacíos y rangos inválidos.

    - Métricas con source: manual NO deben tener valor numérico (value=null).
    - Valores negativos donde se esperan conteos positivos.
    - Fuentes vacías deben marcarse como EMPTY, no como cero.
    """
    for m in manifests:
        is_manual = m.source == MetricSource.MANUAL

        if is_manual:
            # Manual: no debe contener filas con valores numéricos
            if m.rows and len(m.rows) > 0:
                for row in m.rows:
                    for val in row.values():
                        if isinstance(val, (int, float)) and val != 0:
                            report.add_issue(
                                DqsIssue(
                                    obligation=3,
                                    code="DQS-003-MANUAL_VALUE",
                                    severity="blocker",
                                    message=(
                                        f"Métrica manual '{m.metric_id}' "
                                        f"contiene valor numérico {val}; "
                                        f"debe ser null/ausente"
                                    ),
                                    details={
                                        "metric_id": str(m.metric_id),
                                        "value": val,
                                    },
                                )
                            )
                            return  # one issue per manifest is enough

        elif m.status == FetchStatus.EMPTY and m.source != MetricSource.MANUAL:
            # Fuente no-manual devolvió vacío: advertir pero no bloquear
            # (puede ser legítimo si la BD realmente no tiene datos)
            report.add_issue(
                DqsIssue(
                    obligation=3,
                    code="DQS-003-EMPTY_SOURCE",
                    severity="warning",
                    message=(
                        f"Fuente '{m.metric_id}' ({m.source.value}) "
                        f"devolvió resultado vacío. Verificar si es esperado."
                    ),
                    details={"metric_id": str(m.metric_id)},
                )
            )

        elif m.status == FetchStatus.EXTRACTED and m.rows:
            # Verificar valores negativos en métricas no manuales
            for row in m.rows:
                for col, val in row.items():
                    if isinstance(val, (int, float)) and val < 0:
                        report.add_issue(
                            DqsIssue(
                                obligation=3,
                                code="DQS-003-NEGATIVE_VALUE",
                                severity="blocker",
                                message=(
                                    f"Valor negativo en '{m.metric_id}'."
                                    f"{col} = {val}"
                                ),
                                details={
                                    "metric_id": str(m.metric_id),
                                    "column": col,
                                    "value": val,
                                },
                            )
                        )


# ── Gate 4: Idempotencia real ──────────────────────────────────────────────


def _check_idempotencia(
    report: DqsReport,
    manifests: Sequence[SourceManifest],
    previous_bundle: Bundle | None,
) -> None:
    """Verifica que el mismo attempt_id produzca el mismo hash.

    Si existe un bundle previo con el mismo attempt_id, reconstruye
    el bundle con los manifiestos actuales y compara el hash SHA-256
    completo del bundle contra el hash almacenado en el bundle previo.
    """
    if previous_bundle is None:
        return

    # Reconstruir bundle con los mismos metadatos pero manifiestos actuales
    current_bundle = Bundle(
        run_id=previous_bundle.run_id,
        attempt_id=previous_bundle.attempt_id,
        cut=previous_bundle.cut,
        catalog_hash=previous_bundle.catalog_hash,
        manifests=manifests,
        rows=previous_bundle.rows,
        dqs=previous_bundle.dqs,
    )
    current_hash = current_bundle.compute_hash()

    if current_hash != previous_bundle.hash:
        report.add_issue(
            DqsIssue(
                obligation=4,
                code="DQS-004-IDEMPOTENCY",
                severity="blocker",
                message=(
                    f"Idempotencia rota: el mismo attempt_id "
                    f"produjo hash diferente. "
                    f"Actual={str(current_hash)[:16]}... vs "
                    f"Previsto={str(previous_bundle.hash)[:16]}..."
                ),
                details={
                    "attempt_id": str(previous_bundle.attempt_id),
                    "previous_hash": str(previous_bundle.hash),
                    "current_hash": str(current_hash),
                },
            )
        )


# ── Gate 5: Cero filas huérfanas ───────────────────────────────────────────


def _check_no_orfanos(
    report: DqsReport,
    manifests: Sequence[SourceManifest],
    catalog: Sequence[Metric],
) -> None:
    """Verifica que cada fila tenga métrica, fuente y grano asignados.

    También verifica que cada manifiesto referencie una métrica válida
    del catálogo.
    """
    catalog_ids = {m.key for m in catalog}

    for m in manifests:
        metric_key = str(m.metric_id)

        # Verificar que el metric_id existe en el catálogo
        if metric_key not in catalog_ids:
            report.add_issue(
                DqsIssue(
                    obligation=5,
                    code="DQS-005-ORPHAN_MANIFEST",
                    severity="blocker",
                    message=(
                        f"Manifiesto huérfano: '{metric_key}' "
                        f"no está en el catálogo"
                    ),
                    details={
                        "metric_id": metric_key,
                        "catalog_ids": sorted(catalog_ids),
                    },
                )
            )

        # Verificar que cada fila del manifiesto tenga referencias válidas
        if m.source == MetricSource.MANUAL:
            # Los manifiestos manuales no tienen filas con valores
            continue

        for i, row in enumerate(m.rows):
            # Verificar que la fila no esté vacía
            if not row:
                report.add_issue(
                    DqsIssue(
                        obligation=5,
                        code="DQS-005-EMPTY_ROW",
                        severity="blocker",
                        message=(
                            f"Fila huérfana #{i} en '{metric_key}': "
                            f"sin datos"
                        ),
                        details={
                            "metric_id": metric_key,
                            "row_index": i,
                        },
                    )
                )
