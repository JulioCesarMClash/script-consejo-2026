"""Tests para las 5 obligaciones DQS del dominio.

Cubre cada obligación con fixtures de éxito y escenarios de fallo.

Obligaciones:
1. Cardinalidad exacta por grano.
2. Reconciliación parte/total.
3. Casos borde reales (nulos, negativos, vacíos, rangos).
4. Idempotencia real (hash reproducible).
5. Cero filas huérfanas.

Regla clave: source: manual con value=null NO debe tratarse como cero.
"""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from src.consejo.domain.dqs import DqsReport, validate
from src.consejo.domain.entities import Bundle, Metric, SourceManifest
from src.consejo.domain.value_objects import (
    AttemptId,
    Cut,
    FetchStatus,
    MetricId,
    MetricSource,
    RunId,
)


# ── Helpers ─────────────────────────────────────────────────────────────────


SAMPLE_CUT = Cut(date(2026, 7, 1))
NOW = datetime(2026, 7, 2, 10, 0, tzinfo=timezone.utc)


def _make_catalog(
    keys: list[str] | None = None,
) -> list[Metric]:
    """Crea un catálogo con las métricas indicadas."""
    if keys is None:
        keys = [f"metric_{i}" for i in range(16)]
    return [
        Metric(
            id=MetricId(k), name=k, key=k,
            source=MetricSource.DIM_USER, formula="count", db_mapping=f"SELECT count FROM {k}",
        )
        for k in keys
    ]


def _make_manifest(
    metric_id: str,
    source: MetricSource = MetricSource.DIM_USER,
    rows: list[dict] | None = None,
    status: FetchStatus = FetchStatus.EXTRACTED,
) -> SourceManifest:
    """Crea un manifiesto para una métrica."""
    return SourceManifest(
        metric_id=MetricId(metric_id),
        source=source,
        cut=SAMPLE_CUT,
        fetched_at=NOW,
        freshness_hours=0.0,
        rows=rows or [{"count": 100}],
        status=status,
    )


def _make_empty_manifest(metric_id: str) -> SourceManifest:
    """Crea un manifiesto vacío (sin filas, EMPTY)."""
    return SourceManifest(
        metric_id=MetricId(metric_id),
        source=MetricSource.DIM_USER,
        cut=SAMPLE_CUT,
        fetched_at=NOW,
        freshness_hours=0.0,
        rows=[],
        status=FetchStatus.EMPTY,
    )


# ── Gate 1: Cardinalidad ───────────────────────────────────────────────────


class TestCardinalidad:
    def test_matching_cardinality_passes(self) -> None:
        catalog = _make_catalog(["m1", "m2", "m3"])
        manifests = [
            _make_manifest("m1"),
            _make_manifest("m2"),
            _make_manifest("m3"),
        ]
        report = validate(manifests, catalog)
        assert report.passed is True

    def test_missing_metrics_fails(self) -> None:
        catalog = _make_catalog(["m1", "m2", "m3"])
        manifests = [_make_manifest("m1")]
        report = validate(manifests, catalog)
        assert report.passed is False
        assert any(
            i.code == "DQS-001-CARDINALITY" for i in report.issues
        )

    def test_extra_metrics_fails(self) -> None:
        catalog = _make_catalog(["m1"])
        manifests = [_make_manifest("m1"), _make_manifest("m2")]
        report = validate(manifests, catalog)
        assert report.passed is False
        assert any(
            i.code == "DQS-001-CARDINALITY" for i in report.issues
        )

    def test_empty_manifests_with_nonempty_catalog_fails(self) -> None:
        catalog = _make_catalog(["m1", "m2"])
        report = validate([], catalog)
        assert report.passed is False


# ── Gate 2: Reconciliación ─────────────────────────────────────────────────


class TestReconciliacion:
    def _make_sum_catalog(self) -> list[Metric]:
        return [
            Metric(
                id=MetricId("registered_cpe"), name="Reg CPE", key="registered_cpe",
                source=MetricSource.DIM_USER, formula="count", db_mapping="x",
            ),
            Metric(
                id=MetricId("registered_aprende"), name="Reg Aprende", key="registered_aprende",
                source=MetricSource.DIM_USER, formula="count", db_mapping="x",
            ),
            Metric(
                id=MetricId("registered_total"), name="Reg Total", key="registered_total",
                source=MetricSource.DIM_USER, formula="sum", db_mapping="x",
            ),
        ]

    def test_reconciliation_passes_when_parts_match(self) -> None:
        catalog = self._make_sum_catalog()
        manifests = [
            _make_manifest("registered_cpe", rows=[{"count": 100}]),
            _make_manifest("registered_aprende", rows=[{"count": 50}]),
            _make_manifest("registered_total", rows=[{"count": 150}]),
        ]
        report = validate(manifests, catalog)
        assert report.passed is True

    def test_reconciliation_fails_when_mismatch(self) -> None:
        catalog = self._make_sum_catalog()
        manifests = [
            _make_manifest("registered_cpe", rows=[{"count": 100}]),
            _make_manifest("registered_aprende", rows=[{"count": 50}]),
            _make_manifest("registered_total", rows=[{"count": 999}]),
        ]
        report = validate(manifests, catalog)
        assert report.passed is False
        assert any(
            i.code == "DQS-002-RECONCILIATION" for i in report.issues
        )


# ── Gate 3: Casos borde ────────────────────────────────────────────────────


class TestEdgeCases:
    def test_manual_metric_rejects_numeric_value_at_entity_level(self) -> None:
        """El SourceManifest impide construir manifiestos manuales con filas.
        Esta validación ocurre en la entidad, no en DQS — es defensa temprana."""
        from src.consejo.domain.entities import SourceManifest

        with pytest.raises(ValueError, match="manual no debe contener filas"):
            SourceManifest(
                metric_id=MetricId("beneficiaries"),
                source=MetricSource.MANUAL,
                cut=SAMPLE_CUT,
                fetched_at=NOW,
                freshness_hours=0.0,
                rows=[{"value": 5000}],
                status=FetchStatus.EXTRACTED,
            )

    def test_manual_metric_with_empty_rows_passes(self) -> None:
        catalog = _make_catalog(["beneficiaries"])
        manifests = [
            SourceManifest(
                metric_id=MetricId("beneficiaries"),
                source=MetricSource.MANUAL,
                cut=SAMPLE_CUT,
                fetched_at=NOW,
                freshness_hours=0.0,
                rows=[],
                status=FetchStatus.EMPTY,
            ),
        ]
        report = validate(manifests, catalog)
        # Cardinalidad pasa (1 == 1), reconciliación no aplica,
        # edge cases pasan (manual sin valor), no huérfanos
        assert report.passed is True

    def test_negative_value_in_non_manual_metric_fails(self) -> None:
        catalog = _make_catalog(["registered_cpe"])
        manifests = [
            _make_manifest("registered_cpe", rows=[{"count": -5}]),
        ]
        report = validate(manifests, catalog)
        assert report.passed is False
        assert any(
            i.code == "DQS-003-NEGATIVE_VALUE" for i in report.issues
        )

    def test_empty_source_warns_but_does_not_block(self) -> None:
        catalog = _make_catalog(["registered_cpe"])
        manifests = [
            SourceManifest(
                metric_id=MetricId("registered_cpe"),
                source=MetricSource.DIM_USER,
                cut=SAMPLE_CUT,
                fetched_at=NOW,
                freshness_hours=0.0,
                rows=[],
                status=FetchStatus.EMPTY,
            ),
        ]
        report = validate(manifests, catalog)
        # Empty source is a warning, not a blocker
        assert report.passed is True
        assert any(
            i.code == "DQS-003-EMPTY_SOURCE" for i in report.issues
        )


# ── Gate 4: Idempotencia ───────────────────────────────────────────────────


class TestIdempotencia:
    def test_no_previous_bundle_passes(self) -> None:
        catalog = _make_catalog(["m1"])
        manifests = [_make_manifest("m1")]
        report = validate(manifests, catalog, previous_bundle=None)
        assert report.passed is True

    def test_same_data_same_hash_passes(self) -> None:
        catalog = _make_catalog(["m1"])
        manifests = [_make_manifest("m1", rows=[{"count": 100}])]

        run_id = RunId.generate()
        attempt_id = AttemptId.generate()

        # Construir bundle previo con estos manifiestos y su hash
        prev_bundle = Bundle(
            run_id=run_id,
            attempt_id=attempt_id,
            cut=SAMPLE_CUT,
            catalog_hash="abc",
            manifests=tuple(manifests),
        )
        prev_hash = prev_bundle.compute_hash()

        # Bundle previo almacenado (incluye hash)
        stored_bundle = Bundle(
            run_id=run_id,
            attempt_id=attempt_id,
            cut=SAMPLE_CUT,
            catalog_hash="abc",
            manifests=tuple(manifests),
            hash=prev_hash,
        )

        # Validar con los mismos manifiestos
        report = validate(
            manifests, catalog, previous_bundle=stored_bundle
        )
        assert report.passed is True

    def test_different_data_different_hash_fails(self) -> None:
        catalog = _make_catalog(["m1"])
        current_manifests = [_make_manifest("m1", rows=[{"count": 999}])]

        # Previous bundle with different data (count=100)
        prev_manifests = [_make_manifest("m1", rows=[{"count": 100}])]
        prev_bundle = Bundle(
            run_id=RunId.generate(),
            attempt_id=AttemptId.generate(),
            cut=SAMPLE_CUT,
            catalog_hash="abc",
            manifests=prev_manifests,
        )
        prev_hash = prev_bundle.compute_hash()
        prev_bundle_with_hash = Bundle(
            run_id=prev_bundle.run_id,
            attempt_id=prev_bundle.attempt_id,
            cut=SAMPLE_CUT,
            catalog_hash="abc",
            manifests=prev_manifests,
            hash=prev_hash,
        )

        report = validate(
            current_manifests, catalog,
            previous_bundle=prev_bundle_with_hash,
        )
        assert report.passed is False
        assert any(
            i.code == "DQS-004-IDEMPOTENCY" for i in report.issues
        )


# ── Gate 5: Cero filas huérfanas ───────────────────────────────────────────


class TestNoOrfanos:
    def test_valid_manifests_pass(self) -> None:
        catalog = _make_catalog(["m1", "m2"])
        manifests = [_make_manifest("m1"), _make_manifest("m2")]
        report = validate(manifests, catalog)
        assert report.passed is True

    def test_orphan_manifest_not_in_catalog_fails(self) -> None:
        catalog = _make_catalog(["m1"])
        manifests = [_make_manifest("m1"), _make_manifest("m2")]
        report = validate(manifests, catalog)
        assert report.passed is False
        assert any(
            i.code == "DQS-005-ORPHAN_MANIFEST" for i in report.issues
        )

    def test_empty_row_fails(self) -> None:
        catalog = _make_catalog(["m1"])
        manifests = [
            SourceManifest(
                metric_id=MetricId("m1"),
                source=MetricSource.DIM_USER,
                cut=SAMPLE_CUT,
                fetched_at=NOW,
                freshness_hours=0.0,
                rows=[{}],  # empty dict row
                status=FetchStatus.EXTRACTED,
            ),
        ]
        report = validate(manifests, catalog)
        assert report.passed is False
        assert any(
            i.code == "DQS-005-EMPTY_ROW" for i in report.issues
        )

    def test_manual_manifest_skips_row_validation(self) -> None:
        catalog = _make_catalog(["beneficiaries"])
        manifests = [
            SourceManifest(
                metric_id=MetricId("beneficiaries"),
                source=MetricSource.MANUAL,
                cut=SAMPLE_CUT,
                fetched_at=NOW,
                freshness_hours=0.0,
                rows=[],
                status=FetchStatus.EMPTY,
            ),
        ]
        report = validate(manifests, catalog)
        assert report.passed is True


# ── DqsReport ───────────────────────────────────────────────────────────────


class TestDqsReport:
    def test_default_is_passed(self) -> None:
        report = DqsReport()
        assert report.passed is True
        assert report.issues == []

    def test_warning_does_not_block(self) -> None:
        from src.consejo.domain.entities import DqsIssue

        report = DqsReport()
        report.add_issue(DqsIssue(
            obligation=3, code="WARN-001", severity="warning",
            message="advertencia",
        ))
        assert report.passed is True

    def test_blocker_marks_failed(self) -> None:
        from src.consejo.domain.entities import DqsIssue

        report = DqsReport()
        report.add_issue(DqsIssue(
            obligation=1, code="BLOCK-001", severity="blocker",
            message="bloqueante",
        ))
        assert report.passed is False
