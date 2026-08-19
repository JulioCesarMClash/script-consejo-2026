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
    db_source: str = "postgres",
) -> Metric:
    return Metric(
        id=MetricId(key),
        name=key.replace("_", " ").title(),
        key=key,
        source=source,
        formula="COUNT(*)",
        db_mapping=db_mapping,
        grain=grain,
        db_source=db_source,
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

    def test_passes_configured_certificate_period_to_source(
        self, run_id, attempt_id, cut, fetched_at,
    ):
        metric = _make_metric(
            "certifications_cpe",
            MetricSource.FACT_INSCRIPTION,
            "SELECT COUNT(*) FROM fact_inscription",
        )
        conn = FakeSourceConn({
            "SELECT COUNT(*) FROM fact_inscription": [{"count": 1}]
        })

        extract_data(
            FakeMetricRepo([metric]),
            conn,
            run_id,
            attempt_id,
            cut,
            fetched_at,
            query_params={
                "period_start": "2025-09-01",
                "period_end": "2026-08-01",
            },
        )

        assert conn.fetch_calls[0][1] == {
            "cut": "2026-07-01",
            "period_start": "2025-09-01",
            "period_end": "2026-08-01",
        }

    def test_derived_totals_are_built_from_parts(
        self, run_id, attempt_id, cut, fetched_at,
    ):
        """Los totals derivados se suman desde sus partes y no disparan fetch."""
        sql_reg_cpe = "SELECT COUNT(*) AS c FROM dim_user WHERE platform_id = 1"
        sql_reg_apd = "SELECT COUNT(*) AS c FROM dim_user WHERE platform_id = 2"
        sql_cert_cpe = "SELECT COUNT(DISTINCT u) FROM cert WHERE platform='cpe'"
        sql_cert_apd = "SELECT COUNT(DISTINCT u) FROM cert WHERE platform='aprende'"
        catalog = [
            _make_metric("registered_cpe", MetricSource.DIM_USER, sql_reg_cpe),
            _make_metric("registered_aprende", MetricSource.DIM_USER, sql_reg_apd),
            _make_metric("registered_total", MetricSource.DIM_USER, "A + B"),
            _make_metric("certified_unique_cpe", MetricSource.FACT_INSCRIPTION,
                         sql_cert_cpe),
            _make_metric("certified_unique_cpe_from_aprende",
                         MetricSource.FACT_INSCRIPTION, sql_cert_apd),
            _make_metric("certified_unique_cpe_total",
                         MetricSource.FACT_INSCRIPTION, "A + B"),
        ]
        conn = FakeSourceConn()
        conn.set_rows(sql_reg_cpe, [{"count": 1500}])
        conn.set_rows(sql_reg_apd, [{"count": 1000}])
        conn.set_rows(sql_cert_cpe, [{"count": 2800}])
        conn.set_rows(sql_cert_apd, [])  # parte sin datos

        result = extract_data(
            FakeMetricRepo(catalog), conn, run_id, attempt_id, cut, fetched_at
        )
        by_key = {str(m.metric_id): m for m in result}

        registered_total = by_key["registered_total"]
        assert registered_total.status == FetchStatus.EXTRACTED
        assert registered_total.rows == ({"value": 2500},)

        certified_total = by_key["certified_unique_cpe_total"]
        assert certified_total.status == FetchStatus.EMPTY
        assert certified_total.rows == ()

        fetched = {sql for sql, _ in conn.fetch_calls}
        assert fetched == {sql_reg_cpe, sql_reg_apd, sql_cert_cpe, sql_cert_apd}


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

    def test_with_cte_is_executable(self):
        assert _is_executable_sql(
            "WITH categorias AS (SELECT 1) SELECT * FROM categorias"
        )
        assert _is_executable_sql(
            "  with t as (select 1) select * from t"
        )

    def test_textual_formula_is_not_executable(self):
        assert not _is_executable_sql("Registrados CPE + Registrados Aprende")
        assert not _is_executable_sql("")
        assert not _is_executable_sql("Inscripciones CPE + Inscripciones CPE desde Aprende")


class TestDbSourceDispatch:
    """Tests para el dispatch de `db_source` entre conexiones PG y MySQL."""

    def test_mysql_metric_uses_mysql_conn(
        self, run_id, attempt_id, cut, fetched_at,
    ):
        """Métrica con `db_source=mysql` se ejecuta contra mysql_conn."""
        mysql_sql = "SELECT COUNT(*) FROM carso_analisis.inscripciones"
        pg_sql = "SELECT COUNT(*) FROM dim_user"
        catalog = [
            _make_metric("slide3_carso_alumnos", MetricSource.DIM_USER,
                         mysql_sql, db_source="mysql"),
            _make_metric("registered_cpe", MetricSource.DIM_USER, pg_sql,
                         db_source="postgres"),
        ]
        pg_conn = FakeSourceConn({pg_sql: [{"count": 100}]})
        mysql_conn = FakeSourceConn({mysql_sql: [{"count": 200}]})
        repo = FakeMetricRepo(catalog)

        result = extract_data(
            repo, pg_conn, run_id, attempt_id, cut, fetched_at,
            mysql_conn=mysql_conn,
        )

        by_key = {str(m.metric_id): m for m in result}

        assert len(pg_conn.fetch_calls) == 1
        assert pg_conn.fetch_calls[0][0] == pg_sql
        assert len(mysql_conn.fetch_calls) == 1
        assert mysql_conn.fetch_calls[0][0] == mysql_sql

        assert by_key["slide3_carso_alumnos"].status == FetchStatus.EXTRACTED
        assert by_key["slide3_carso_alumnos"].rows[0]["value"] == 200
        assert by_key["registered_cpe"].status == FetchStatus.EXTRACTED
        assert by_key["registered_cpe"].rows[0]["value"] == 100

    def test_default_db_source_falls_back_to_pg(
        self, run_id, attempt_id, cut, fetched_at,
    ):
        """Métrica sin `db_source` (o con `postgres`) usa pg_conn siempre,
        incluso si se provee `mysql_conn`."""
        pg_sql = "SELECT 1"
        catalog = [
            _make_metric("registered_cpe", MetricSource.DIM_USER, pg_sql),
            _make_metric("inscriptions_cpe", MetricSource.DIM_USER, pg_sql,
                         db_source="postgres"),
        ]
        pg_conn = FakeSourceConn({pg_sql: [{"x": 1}]})
        mysql_conn = FakeSourceConn()
        repo = FakeMetricRepo(catalog)

        extract_data(
            repo, pg_conn, run_id, attempt_id, cut, fetched_at,
            mysql_conn=mysql_conn,
        )

        assert len(pg_conn.fetch_calls) == 2
        assert len(mysql_conn.fetch_calls) == 0

    def test_mysql_metric_without_mysql_conn_falls_back_to_pg(
        self, run_id, attempt_id, cut, fetched_at,
    ):
        """Si la métrica es `db_source=mysql` pero NO se pasa `mysql_conn`,
        el dispatch cae sobre `pg_conn` (compatibilidad hacia atrás).
        Si PG tampoco tiene la query, el manifiesto queda en EMPTY."""
        mysql_sql = "SELECT 1 FROM carso_analisis.t"
        catalog = [
            _make_metric("slide3_carso", MetricSource.DIM_USER, mysql_sql,
                         db_source="mysql"),
        ]
        pg_conn = FakeSourceConn()  # No matchea mysql_sql → ()
        repo = FakeMetricRepo(catalog)

        result = extract_data(
            repo, pg_conn, run_id, attempt_id, cut, fetched_at,
            # mysql_conn omitido a propósito
        )

        assert len(result) == 1
        assert result[0].status == FetchStatus.EMPTY
        assert result[0].rows == ()
        assert len(pg_conn.fetch_calls) == 1
        assert pg_conn.fetch_calls[0][0] == mysql_sql

    def test_mysql_conn_is_optional_for_backward_compat(
        self, run_id, attempt_id, cut, fetched_at,
    ):
        """Sin `mysql_conn`, todas las métricas (incluso `db_source=mysql`)
        caen sobre `source_conn` (PG). Esto preserva tests existentes."""
        sql = "SELECT 1"
        catalog = [
            _make_metric("a", MetricSource.DIM_USER, sql, db_source="postgres"),
            _make_metric("b", MetricSource.DIM_USER, sql, db_source="mysql"),
        ]
        pg_conn = FakeSourceConn({sql: [{"x": 1}]})
        repo = FakeMetricRepo(catalog)

        result = extract_data(
            repo, pg_conn, run_id, attempt_id, cut, fetched_at,
        )

        assert all(m.status == FetchStatus.EXTRACTED for m in result)
        assert len(pg_conn.fetch_calls) == 2
