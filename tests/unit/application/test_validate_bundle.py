"""Tests unitarios para validate_bundle — validación DQS y bundle canónico."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Sequence

import pytest

from src.consejo.application.use_cases.validate_bundle import (
    DqsBlockedError,
    validate_bundle,
)
from src.consejo.domain.entities import Bundle, DqsIssue, Metric, SourceManifest
from src.consejo.domain.value_objects import (
    AttemptId,
    Cut,
    FetchStatus,
    HashSha256,
    MetricId,
    MetricSource,
    PipelineMode,
    RunId,
)


# ── Builders ───────────────────────────────────────────────────────────────


def _make_metric(
    key: str,
    source: MetricSource = MetricSource.DIM_USER,
    grain: str = "scalar",
    db_mapping: str = "",
) -> Metric:
    return Metric(
        id=MetricId(key),
        name=key.replace("_", " ").title(),
        key=key,
        source=source,
        formula="COUNT(*)",
        db_mapping=db_mapping,
        grain=grain,
    )


def _make_manifest(
    metric_key: str,
    source: MetricSource = MetricSource.DIM_USER,
    status: FetchStatus = FetchStatus.EXTRACTED,
    rows: Sequence[dict] | None = None,
    cut: date = date(2026, 7, 1),
    freshness_hours: float = 0.0,
) -> SourceManifest:
    effective_rows = rows if rows is not None else [{"value": 100}]
    return SourceManifest(
        metric_id=MetricId(metric_key),
        source=source,
        cut=Cut(cut),
        fetched_at=datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc),
        freshness_hours=freshness_hours,
        rows=tuple(effective_rows),
        status=status,
    )


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def run_id() -> RunId:
    return RunId.generate()


@pytest.fixture
def attempt_id() -> AttemptId:
    return AttemptId.generate()


@pytest.fixture
def cut() -> Cut:
    return Cut(date(2026, 7, 1))


@pytest.fixture
def catalog_hash() -> str:
    return "a" * 64


@pytest.fixture
def small_catalog() -> list[Metric]:
    """Catálogo con 4 métricas: 3 dim_user, 1 manual."""
    return [
        _make_metric("registered_cpe", MetricSource.DIM_USER),
        _make_metric("registered_aprende", MetricSource.DIM_USER),
        _make_metric("registered_total", MetricSource.DIM_USER),
        _make_metric("beneficiaries", MetricSource.MANUAL),
    ]


@pytest.fixture
def valid_manifests(small_catalog) -> list[SourceManifest]:
    """Manifiestos válidos que coinciden con small_catalog."""
    return [
        _make_manifest("registered_cpe", MetricSource.DIM_USER,
                       rows=[{"value": 5000}]),
        _make_manifest("registered_aprende", MetricSource.DIM_USER,
                       rows=[{"value": 3000}]),
        _make_manifest("registered_total", MetricSource.DIM_USER,
                       rows=[{"value": 8000}]),  # 5000 + 3000 = 8000
        _make_manifest("beneficiaries", MetricSource.MANUAL,
                       rows=(), status=FetchStatus.EMPTY),
    ]


# ── Tests ──────────────────────────────────────────────────────────────────


class TestValidateBundle:
    """Tests para la validación DQS y construcción del bundle."""

    def test_returns_bundle_when_dqs_passes(
        self, valid_manifests, small_catalog, run_id, attempt_id, cut,
        catalog_hash,
    ):
        bundle = validate_bundle(
            valid_manifests, small_catalog, run_id, attempt_id, cut,
            catalog_hash,
        )
        assert isinstance(bundle, Bundle)
        assert bundle.run_id == run_id
        assert bundle.attempt_id == attempt_id
        assert bundle.cut == cut
        assert bundle.catalog_hash == catalog_hash

    def test_bundle_has_canonical_hash(
        self, valid_manifests, small_catalog, run_id, attempt_id, cut,
        catalog_hash,
    ):
        bundle = validate_bundle(
            valid_manifests, small_catalog, run_id, attempt_id, cut,
            catalog_hash,
        )
        assert isinstance(bundle.hash, HashSha256)
        assert len(str(bundle.hash)) == 64
        # Hash should not be all zeros
        assert str(bundle.hash) != "0" * 64

    def test_hash_is_idempotent(
        self, valid_manifests, small_catalog, run_id, attempt_id, cut,
        catalog_hash,
    ):
        """Mismo input produce mismo hash en ejecuciones separadas."""
        b1 = validate_bundle(
            valid_manifests, small_catalog, run_id, attempt_id, cut,
            catalog_hash,
        )
        b2 = validate_bundle(
            valid_manifests, small_catalog, run_id, attempt_id, cut,
            catalog_hash,
        )
        assert b1.hash == b2.hash

    def test_hash_changes_with_different_data(
        self, valid_manifests, small_catalog, run_id, attempt_id, cut,
        catalog_hash,
    ):
        """Datos diferentes producen hash diferente."""
        b1 = validate_bundle(
            valid_manifests, small_catalog, run_id, attempt_id, cut,
            catalog_hash,
        )
        mod_manifests = [
            _make_manifest("registered_cpe", MetricSource.DIM_USER,
                           rows=[{"value": 6000}]),  # changed value
            _make_manifest("registered_aprende", MetricSource.DIM_USER,
                           rows=[{"value": 4000}]),  # changed value
            _make_manifest("registered_total", MetricSource.DIM_USER,
                           rows=[{"value": 10000}]),  # must reconcile
            valid_manifests[3],
        ]
        b2 = validate_bundle(
            mod_manifests, small_catalog, run_id, attempt_id, cut,
            catalog_hash,
        )
        assert b1.hash != b2.hash

    def test_raises_dqs_blocked_on_cardinality_mismatch(
        self, small_catalog, run_id, attempt_id, cut, catalog_hash,
    ):
        """Faltan manifiestos → cardinalidad incorrecta → DqsBlockedError."""
        partial_manifests = [
            _make_manifest("registered_cpe", MetricSource.DIM_USER,
                           rows=[{"value": 100}]),
        ]
        with pytest.raises(DqsBlockedError) as exc:
            validate_bundle(
                partial_manifests, small_catalog, run_id, attempt_id, cut,
                catalog_hash,
            )
        assert "cardinality" in str(exc.value).lower() or any(
            "DQS-001" in i.code for i in exc.value.issues
        )

    def test_raises_dqs_blocked_on_orphan_manifest(
        self, small_catalog, run_id, attempt_id, cut, catalog_hash,
    ):
        """Manifiesto con métrica fuera del catálogo → DqsBlockedError."""
        bad_manifests = [
            _make_manifest("registered_cpe", MetricSource.DIM_USER,
                           rows=[{"value": 100}]),
            _make_manifest("registered_aprende", MetricSource.DIM_USER,
                           rows=[{"value": 200}]),
            _make_manifest("registered_total", MetricSource.DIM_USER,
                           rows=[{"value": 300}]),
            _make_manifest("unknown_metric", MetricSource.DIM_USER,
                           rows=[{"value": 999}]),
        ]
        with pytest.raises(DqsBlockedError) as exc:
            validate_bundle(
                bad_manifests, small_catalog, run_id, attempt_id, cut,
                catalog_hash,
            )
        assert any("DQS-005" in i.code for i in exc.value.issues)

    def test_dqs_blocked_error_contains_issues(
        self, small_catalog, run_id, attempt_id, cut, catalog_hash,
    ):
        partial_manifests = [
            _make_manifest("registered_cpe", MetricSource.DIM_USER,
                           rows=[{"value": 100}]),
        ]
        with pytest.raises(DqsBlockedError) as exc:
            validate_bundle(
                partial_manifests, small_catalog, run_id, attempt_id, cut,
                catalog_hash,
            )
        assert len(exc.value.issues) > 0
        assert all(isinstance(i, DqsIssue) for i in exc.value.issues)

    def test_bundle_has_empty_dqs_when_all_pass(
        self, valid_manifests, small_catalog, run_id, attempt_id, cut,
        catalog_hash,
    ):
        bundle = validate_bundle(
            valid_manifests, small_catalog, run_id, attempt_id, cut,
            catalog_hash,
        )
        blockers = [i for i in bundle.dqs if i.severity == "blocker"]
        assert len(blockers) == 0

    def test_manifests_with_manual_source_pass_dqs(
        self, run_id, attempt_id, cut, catalog_hash,
    ):
        """Métricas manuales sin filas deben pasar DQS sin errores."""
        catalog = [
            _make_metric("beneficiaries", MetricSource.MANUAL),
            _make_metric("beneficiaries_unique", MetricSource.MANUAL),
        ]
        manifests = [
            _make_manifest("beneficiaries", MetricSource.MANUAL,
                           rows=(), status=FetchStatus.EMPTY),
            _make_manifest("beneficiaries_unique", MetricSource.MANUAL,
                           rows=(), status=FetchStatus.EMPTY),
        ]
        bundle = validate_bundle(
            manifests, catalog, run_id, attempt_id, cut, catalog_hash,
        )
        assert isinstance(bundle, Bundle)

    def test_production_blocks_empty_required_external_metric(
        self, run_id, attempt_id, cut, catalog_hash,
    ):
        catalog = [_make_metric(
            "registered_cpe", MetricSource.DIM_USER, db_mapping="SELECT 1"
        )]
        manifests = [_make_manifest(
            "registered_cpe",
            MetricSource.DIM_USER,
            status=FetchStatus.EMPTY,
            rows=(),
        )]

        with pytest.raises(DqsBlockedError) as exc:
            validate_bundle(
                manifests, catalog, run_id, attempt_id, cut, catalog_hash,
                mode=PipelineMode.PRODUCTION,
            )

        assert any(
            issue.code == "DQS-003-REQUIRED_METRIC" and
            issue.details["metric_id"] == "registered_cpe"
            for issue in exc.value.issues
        )

    def test_dry_run_warns_on_empty_required_external_metric(
        self, run_id, attempt_id, cut, catalog_hash,
    ):
        catalog = [_make_metric(
            "registered_cpe", MetricSource.DIM_USER, db_mapping="SELECT 1"
        )]
        manifests = [_make_manifest(
            "registered_cpe",
            MetricSource.DIM_USER,
            status=FetchStatus.EMPTY,
            rows=(),
        )]

        bundle = validate_bundle(
            manifests, catalog, run_id, attempt_id, cut, catalog_hash,
            mode=PipelineMode.DRY_RUN,
        )

        assert any(
            issue.code == "DQS-003-REQUIRED_METRIC" and
            issue.severity == "warning"
            for issue in bundle.dqs
        )

    def test_production_blocks_empty_manual_beneficiaries(
        self, run_id, attempt_id, cut, catalog_hash,
    ):
        catalog = [_make_metric("beneficiaries", MetricSource.MANUAL)]
        manifests = [_make_manifest(
            "beneficiaries",
            MetricSource.MANUAL,
            status=FetchStatus.EMPTY,
            rows=(),
        )]

        with pytest.raises(DqsBlockedError):
            validate_bundle(
                manifests, catalog, run_id, attempt_id, cut, catalog_hash,
                mode=PipelineMode.PRODUCTION,
            )

    def test_production_blocks_empty_automatic_beneficiaries_unique(
        self, run_id, attempt_id, cut, catalog_hash,
    ):
        catalog = [
            _make_metric("inscribed_unique_cpe", MetricSource.FACT_INSCRIPTION),
            _make_metric(
                "inscribed_unique_cpe_from_aprende",
                MetricSource.FACT_INSCRIPTION,
            ),
            _make_metric("beneficiaries_unique", MetricSource.FACT_INSCRIPTION),
        ]
        manifests = [
            _make_manifest(
                "inscribed_unique_cpe",
                MetricSource.FACT_INSCRIPTION,
                status=FetchStatus.EMPTY,
                rows=(),
            ),
            _make_manifest(
                "inscribed_unique_cpe_from_aprende",
                MetricSource.FACT_INSCRIPTION,
                status=FetchStatus.EXTRACTED,
                rows=[{"value": 10}],
            ),
            _make_manifest(
                "beneficiaries_unique",
                MetricSource.FACT_INSCRIPTION,
                status=FetchStatus.EMPTY,
                rows=(),
            ),
        ]

        with pytest.raises(DqsBlockedError) as exc:
            validate_bundle(
                manifests, catalog, run_id, attempt_id, cut, catalog_hash,
                mode=PipelineMode.PRODUCTION,
            )

        assert any(
            issue.code == "DQS-003-REQUIRED_METRIC" and
            issue.details["metric_id"] == "beneficiaries_unique"
            for issue in exc.value.issues
        )

    @pytest.mark.parametrize(
        "metric_key",
        [
            "registered_total",
            "inscriptions_cpe_total",
            "certifications_cpe_total",
            "certified_unique_cpe_total",
            "beneficiaries_unique",
        ],
    )
    def test_production_blocks_empty_explicitly_required_derived_total(
        self, metric_key, run_id, attempt_id, cut, catalog_hash,
    ):
        catalog = [_make_metric(metric_key, MetricSource.DIM_USER)]
        manifests = [_make_manifest(
            metric_key,
            MetricSource.DIM_USER,
            status=FetchStatus.EMPTY,
            rows=(),
        )]

        with pytest.raises(DqsBlockedError) as exc:
            validate_bundle(
                manifests, catalog, run_id, attempt_id, cut, catalog_hash,
                mode=PipelineMode.PRODUCTION,
            )

        assert any(
            issue.code == "DQS-003-REQUIRED_METRIC"
            and issue.details["metric_id"] == metric_key
            for issue in exc.value.issues
        )

    @pytest.mark.parametrize(
        "metric_key",
        [
            "registered_total",
            "inscriptions_cpe_total",
            "certifications_cpe_total",
            "certified_unique_cpe_total",
            "beneficiaries_unique",
        ],
    )
    def test_dry_run_warns_on_empty_explicitly_required_derived_total(
        self, metric_key, run_id, attempt_id, cut, catalog_hash,
    ):
        catalog = [_make_metric(metric_key, MetricSource.DIM_USER)]
        manifests = [_make_manifest(
            metric_key,
            MetricSource.DIM_USER,
            status=FetchStatus.EMPTY,
            rows=(),
        )]

        bundle = validate_bundle(
            manifests, catalog, run_id, attempt_id, cut, catalog_hash,
            mode=PipelineMode.DRY_RUN,
        )

        assert any(
            issue.code == "DQS-003-REQUIRED_METRIC"
            and issue.details["metric_id"] == metric_key
            and issue.severity == "warning"
            for issue in bundle.dqs
        )

    def test_bundle_rows_are_enriched(
        self, valid_manifests, small_catalog, run_id, attempt_id, cut,
        catalog_hash,
    ):
        bundle = validate_bundle(
            valid_manifests, small_catalog, run_id, attempt_id, cut,
            catalog_hash,
        )
        for row in bundle.rows:
            assert "metric_id" in row
            assert "source" in row
