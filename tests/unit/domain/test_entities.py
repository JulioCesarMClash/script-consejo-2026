"""Tests para entidades del dominio.

Cubre construcción de Metric, SourceManifest, Run, Bundle y transiciones de estado.
"""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from src.consejo.domain.entities import (
    Bundle,
    DqsIssue,
    Metric,
    Run,
    SourceManifest,
)
from src.consejo.domain.value_objects import (
    AttemptId,
    Cut,
    FetchStatus,
    HashSha256,
    MetricId,
    MetricSource,
    RunId,
    RunState,
)


# ── Metric ──────────────────────────────────────────────────────────────────


class TestMetric:
    def test_create_valid(self) -> None:
        m = Metric(
            id=MetricId("registered_cpe"),
            name="Registrados CPE",
            key="registered_cpe",
            source=MetricSource.DIM_USER,
            formula="COUNT(DISTINCT userId)",
            db_mapping="SELECT COUNT(DISTINCT userId) FROM dim_user WHERE plataformaId = 1",
            platform_scope=["cpe"],
            grain="usuario × plataforma",
        )
        assert m.id == MetricId("registered_cpe")
        assert m.name == "Registrados CPE"
        assert m.key == "registered_cpe"
        assert m.source == MetricSource.DIM_USER
        assert m.platform_scope == ["cpe"]

    def test_rejects_empty_name(self) -> None:
        with pytest.raises(ValueError, match="name"):
            Metric(
                id=MetricId("key"), name="", key="key",
                source=MetricSource.DIM_USER, formula="x", db_mapping="x",
            )

    def test_rejects_empty_key(self) -> None:
        with pytest.raises(ValueError, match="key"):
            Metric(
                id=MetricId("key"), name="name", key="",
                source=MetricSource.DIM_USER, formula="x", db_mapping="x",
            )

    def test_frozen(self) -> None:
        m = Metric(
            id=MetricId("k"), name="n", key="k",
            source=MetricSource.DIM_USER, formula="f", db_mapping="d",
        )
        with pytest.raises(Exception):
            m.name = "new"  # type: ignore[misc]


# ── SourceManifest ──────────────────────────────────────────────────────────


class TestSourceManifest:
    def test_create_valid(self) -> None:
        sm = SourceManifest(
            metric_id=MetricId("registered_cpe"),
            source=MetricSource.DIM_USER,
            cut=Cut(date(2026, 7, 1)),
            fetched_at=datetime(2026, 7, 2, 10, 30, tzinfo=timezone.utc),
            freshness_hours=24.0,
            rows=[{"count": 1500}],
            status=FetchStatus.EXTRACTED,
        )
        assert sm.metric_id == MetricId("registered_cpe")
        assert sm.status == FetchStatus.EXTRACTED
        assert sm.rows == [{"count": 1500}]

    def test_adds_utc_timezone(self) -> None:
        sm = SourceManifest(
            metric_id=MetricId("k"),
            source=MetricSource.DIM_USER,
            cut=Cut(date(2026, 7, 1)),
            fetched_at=datetime(2026, 7, 2, 10, 30),
            freshness_hours=0.0,
        )
        assert sm.fetched_at.tzinfo == timezone.utc

    def test_rejects_negative_freshness(self) -> None:
        with pytest.raises(ValueError, match="freshness"):
            SourceManifest(
                metric_id=MetricId("k"),
                source=MetricSource.DIM_USER,
                cut=Cut(date(2026, 7, 1)),
                fetched_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
                freshness_hours=-1.0,
            )

    def test_manual_rejects_rows_with_data(self) -> None:
        with pytest.raises(ValueError, match="manual no debe contener filas"):
            SourceManifest(
                metric_id=MetricId("beneficiaries"),
                source=MetricSource.MANUAL,
                cut=Cut(date(2026, 7, 1)),
                fetched_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
                freshness_hours=0.0,
                rows=[{"value": 5000}],
            )

    def test_manual_allows_empty_rows(self) -> None:
        sm = SourceManifest(
            metric_id=MetricId("beneficiaries"),
            source=MetricSource.MANUAL,
            cut=Cut(date(2026, 7, 1)),
            fetched_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
            freshness_hours=0.0,
            rows=[],
            status=FetchStatus.EMPTY,
        )
        assert sm.source == MetricSource.MANUAL
        assert sm.rows == []

    def test_frozen(self) -> None:
        sm = SourceManifest(
            metric_id=MetricId("k"),
            source=MetricSource.DIM_USER,
            cut=Cut(date(2026, 7, 1)),
            fetched_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
            freshness_hours=0.0,
        )
        with pytest.raises(Exception):
            sm.status = FetchStatus.FAILED  # type: ignore[misc]


# ── Run ─────────────────────────────────────────────────────────────────────


class TestRun:
    def test_create_valid(self) -> None:
        rid = RunId.generate()
        aid = AttemptId.generate()
        r = Run(
            run_id=rid,
            attempt_id=aid,
            state=RunState.EXTRACTING,
            cut=Cut(date(2026, 7, 1)),
        )
        assert r.state == RunState.EXTRACTING

    def test_valid_transition(self) -> None:
        r = Run(
            run_id=RunId.generate(),
            attempt_id=AttemptId.generate(),
            state=RunState.EXTRACTING,
            cut=Cut(date(2026, 7, 1)),
        )
        r.transition_to(RunState.EXTRACTED)
        assert r.state == RunState.EXTRACTED

    def test_cannot_transition_from_terminal(self) -> None:
        r = Run(
            run_id=RunId.generate(),
            attempt_id=AttemptId.generate(),
            state=RunState.BLOCKED,
            cut=Cut(date(2026, 7, 1)),
        )
        with pytest.raises(ValueError, match="terminal"):
            r.transition_to(RunState.VALIDATING)

    def test_cannot_transition_to_same_state(self) -> None:
        r = Run(
            run_id=RunId.generate(),
            attempt_id=AttemptId.generate(),
            state=RunState.EXTRACTING,
            cut=Cut(date(2026, 7, 1)),
        )
        with pytest.raises(ValueError, match="ya está"):
            r.transition_to(RunState.EXTRACTING)


# ── Bundle ──────────────────────────────────────────────────────────────────


class TestBundle:
    def _make_bundle(self, attempt_id: AttemptId | None = None) -> Bundle:
        if attempt_id is None:
            attempt_id = AttemptId.generate()
        return Bundle(
            run_id=RunId.generate(),
            attempt_id=attempt_id,
            cut=Cut(date(2026, 7, 1)),
            catalog_hash="abc123",
            manifests=(),
            rows=(),
            dqs=(),
        )

    def test_create_empty_bundle(self) -> None:
        b = self._make_bundle()
        assert b.manifests == ()
        assert b.rows == ()
        assert b.dqs == ()

    def test_compute_hash_reproducible(self) -> None:
        rid = RunId.generate()
        aid = AttemptId.generate()

        b1 = Bundle(
            run_id=rid,
            attempt_id=aid,
            cut=Cut(date(2026, 7, 1)),
            catalog_hash="abc123",
        )
        b2 = Bundle(
            run_id=rid,
            attempt_id=aid,
            cut=Cut(date(2026, 7, 1)),
            catalog_hash="abc123",
        )

        h1 = b1.compute_hash()
        h2 = b2.compute_hash()
        assert h1 == h2

    def test_compute_hash_differs_with_different_data(self) -> None:
        b1 = self._make_bundle()
        b2 = Bundle(
            run_id=b1.run_id,
            attempt_id=AttemptId.generate(),  # different
            cut=Cut(date(2026, 7, 1)),
            catalog_hash="xyz",
        )

        h1 = b1.compute_hash()
        h2 = b2.compute_hash()
        assert h1 != h2

    def test_hash_excluded_from_computation(self) -> None:
        """Verifica que el hash se calcula excluyendo el campo hash."""
        b = self._make_bundle()
        canonical = b._canonical_dict(exclude_hash=True)
        assert "hash" not in canonical

        full = b._canonical_dict(exclude_hash=False)
        assert "hash" in full

    def test_canonical_json_sorted_keys(self) -> None:
        b = self._make_bundle()
        json_str = b.canonical_json()
        # Verificar que las claves de primer nivel están ordenadas
        import json
        parsed = json.loads(json_str)
        keys = list(parsed.keys())
        assert keys == sorted(keys)

    def test_frozen(self) -> None:
        b = self._make_bundle()
        with pytest.raises(Exception):
            b.hash = HashSha256("f" * 64)  # type: ignore[misc]


# ── DqsIssue ────────────────────────────────────────────────────────────────


class TestDqsIssue:
    def test_create(self) -> None:
        issue = DqsIssue(
            obligation=1,
            code="DQS-001",
            severity="blocker",
            message="Cardinalidad incorrecta",
        )
        assert issue.obligation == 1
        assert issue.code == "DQS-001"
        assert issue.severity == "blocker"
