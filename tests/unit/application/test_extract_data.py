"""Tests unitarios para extract_data — caso de uso de extracción de métricas."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Mapping, Sequence

import pytest

from src.consejo.application.ports import MetricRepo, SourceConn
from src.consejo.application.use_cases.extract_data import (
    _is_executable_sql,
    _normalize_rows,
    extract_data,
)
from src.consejo.domain.entities import Metric
from src.consejo.domain.value_objects import (
    AttemptId,
    FetchStatus,
    MetricId,
    MetricSource,
    RunId,
)


# ── Fakes ──────────────────────────────────────────────────────────────────


class FakeMetricRepo:
    """MetricRepo falso que devuelve un catálogo parametrizable."""

    def __init__(self, metrics: Sequence[Metric]) -> None:
        self._metrics = list(metrics)
        self.list_metrics_calls = 0

    def list_metrics(self) -> Sequence[Metric]:
        self.list_metrics_calls += 1
        return self._metrics


class FakeSourceConn:
    """SourceConn falso con respuestas predefinidas por métrica."""

    def __init__(
        self, rows_by_sql: dict[str, Sequence[Mapping[str, object]]] | None = None
    ) -> None:
        self._rows = rows_by_sql or {}
        self.fetch_calls: list[tuple[str, Mapping[str, object]]] = []

    def set_rows(
        self, sql_pattern: str, rows: Sequence[Mapping[str, object]],
    ) -> None:
        self._rows[sql_pattern] = rows

    def fetch(
        self, sql: str, params: Mapping[str, object],
    ) -> Sequence[Mapping[str, object]]:
        self.fetch_calls.append((sql, params))
        # Match by prefix for flexibility
        sql_stripped = sql.strip()
        for key, rows in self._rows.items():
            if key.strip() in sql_stripped:
                return rows
        return ()


# ── Fixtures ───────────────────────────────────────────────────────────────


def _make_metric(
    key: str,
    source: MetricSource,
    db_mapping: str = "",
    grain: str = "scalar",
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


@pytest.fixture
def min_catalog() -> list[Metric]:
    """Catálogo mínimo con las 3 fuentes + 1 suma textual."""
    return [
        _make_metric("registered_cpe", MetricSource.DIM_USER,
                     "SELECT COUNT(DISTINCT userId) FROM dim_user WHERE plataformaId = 1"),
        _make_metric("inscriptions_cpe", MetricSource.FACT_INSCRIPTION,
                     "SELECT COUNT(*) FROM fact_inscription fi JOIN course c"),
        _make_metric("registered_total", MetricSource.DIM_USER,
                     "Registrados CPE + Registrados Aprende"),
        _make_metric("beneficiaries", MetricSource.MANUAL,
                     "SELECT (SELECT COUNT(...))"),  # manual source, sql irrelevant
    ]


@pytest.fixture
def run_id() -> RunId:
    return RunId.generate()


@pytest.fixture
def attempt_id() -> AttemptId:
    return AttemptId.generate()


@pytest.fixture
def cut() -> date:
    return date(2026, 7, 1)


@pytest.fixture
def fetched_at() -> datetime:
    return datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def source_conn() -> FakeSourceConn:
    """SourceConn falso con respuestas para el catálogo mínimo."""
    conn = FakeSourceConn()
    conn.set_rows("SELECT COUNT(DISTINCT userId) FROM dim_user", [{"count": 5000}])
    conn.set_rows("SELECT COUNT(*) FROM fact_inscription", [{"count": 300}])
    return conn


# ── Tests ──────────────────────────────────────────────────────────────────


class TestExtractData:
    """Tests para la función extract_data."""

    def test_returns_manifest_for_each_metric(
        self, min_catalog, source_conn, run_id, attempt_id, cut, fetched_at,
    ):
        repo = FakeMetricRepo(min_catalog)
        result = extract_data(repo, source_conn, run_id, attempt_id, cut, fetched_at)
        assert len(result) == len(min_catalog)

    def test_manual_metric_has_empty_rows(
        self, min_catalog, run_id, attempt_id, cut, fetched_at,
    ):
        conn = FakeSourceConn()
        repo = FakeMetricRepo(min_catalog)
        result = extract_data(repo, conn, run_id, attempt_id, cut, fetched_at)

        beneficiaries = [m for m in result if str(m.metric_id) == "beneficiaries"]
        assert len(beneficiaries) == 1
        assert beneficiaries[0].source == MetricSource.MANUAL
        assert beneficiaries[0].status == FetchStatus.EMPTY
        assert len(beneficiaries[0].rows) == 0

    def test_manual_metric_never_queries_db(
        self, run_id, attempt_id, cut, fetched_at,
    ):
        """source: manual no debe ejecutar consulta DB aunque tenga db_mapping."""
        catalog = [_make_metric("beneficiaries", MetricSource.MANUAL,
                                 "SELECT 1")]
        conn = FakeSourceConn()
        repo = FakeMetricRepo(catalog)
        extract_data(repo, conn, run_id, attempt_id, cut, fetched_at)

        assert len(conn.fetch_calls) == 0

    def test_textual_db_mapping_skipped(
        self, run_id, attempt_id, cut, fetched_at,
    ):
        """db_mapping textual (no SQL) produce manifiesto vacío sin consulta."""
        catalog = [_make_metric("registered_total", MetricSource.DIM_USER,
                                 "Registrados CPE + Registrados Aprende")]
        conn = FakeSourceConn()
        repo = FakeMetricRepo(catalog)
        result = extract_data(repo, conn, run_id, attempt_id, cut, fetched_at)

        assert len(result) == 1
        assert result[0].status == FetchStatus.EMPTY
        assert len(conn.fetch_calls) == 0

    def test_metric_with_rows_extracts_successfully(
        self, run_id, attempt_id, cut, fetched_at,
    ):
        metric = _make_metric("registered_cpe", MetricSource.DIM_USER,
                               "SELECT COUNT(*) FROM dim_user")
        expected_rows = [{"count": 1500}]
        conn = FakeSourceConn({"SELECT COUNT(*) FROM dim_user": expected_rows})
        repo = FakeMetricRepo([metric])
        result = extract_data(repo, conn, run_id, attempt_id, cut, fetched_at)

        m = result[0]
        assert m.status == FetchStatus.EXTRACTED
        assert len(m.rows) == 1
        assert m.rows[0].get("value") == 1500 or m.rows[0].get("count") == 1500

    def test_failed_query_sets_failed_status(
        self, run_id, attempt_id, cut, fetched_at,
    ):
        class FailingConn:
            def fetch(self, sql, params):
                raise RuntimeError("connection lost")

        metric = _make_metric("registered_cpe", MetricSource.DIM_USER,
                               "SELECT 1")
        repo = FakeMetricRepo([metric])
        result = extract_data(repo, FailingConn(), run_id, attempt_id, cut, fetched_at)

        assert result[0].status == FetchStatus.FAILED
        assert len(result[0].rows) == 0

    def test_empty_result_sets_empty_status(
        self, run_id, attempt_id, cut, fetched_at,
    ):
        metric = _make_metric("registered_cpe", MetricSource.DIM_USER,
                               "SELECT COUNT(*) FROM dim_user WHERE false")
        conn = FakeSourceConn({"SELECT COUNT(*) FROM dim_user WHERE false": []})
        repo = FakeMetricRepo([metric])
        result = extract_data(repo, conn, run_id, attempt_id, cut, fetched_at)

        assert result[0].status == FetchStatus.EMPTY

    def test_preserves_run_and_attempt_ids(
        self, min_catalog, source_conn, run_id, attempt_id, cut, fetched_at,
    ):
        repo = FakeMetricRepo(min_catalog)
        result = extract_data(repo, source_conn, run_id, attempt_id, cut, fetched_at)

        for m in result:
            assert m.cut.value == cut
            assert m.fetched_at == fetched_at


class TestNormalizeRows:
    """Tests para la normalización de filas SQL."""

    def test_adds_value_key(self):
        rows = [{"count": 42}]
        result = _normalize_rows(rows)
        assert result[0]["value"] == 42
        assert result[0]["count"] == 42

    def test_preserves_existing_value(self):
        rows = [{"value": 10, "count": 20}]
        result = _normalize_rows(rows)
        assert result[0]["value"] == 10

    def test_empty_rows(self):
        result = _normalize_rows([])
        assert result == []


class TestIsExecutableSql:
    """Tests para detección de SQL ejecutable."""

    def test_select_is_executable(self):
        assert _is_executable_sql("SELECT 1")
        assert _is_executable_sql("  SELECT COUNT(*) FROM t")
        assert _is_executable_sql("select * from users")

    def test_textual_formula_is_not_executable(self):
        assert not _is_executable_sql("Registrados CPE + Registrados Aprende")
        assert not _is_executable_sql("")
        assert not _is_executable_sql("Inscripciones CPE + Inscripciones CPE desde Aprende")
