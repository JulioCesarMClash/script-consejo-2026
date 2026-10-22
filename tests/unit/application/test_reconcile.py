"""Tests unitarios para reconcile — PG vs Athena, sin red."""

from __future__ import annotations

from datetime import date
from typing import Mapping, Sequence

from src.consejo.application.use_cases.reconcile import (
    ReconcileReport,
    reconcile,
)
from src.consejo.domain.entities import Metric
from src.consejo.domain.value_objects import MetricId, MetricSource


class FakeRepo:
    def __init__(self, metrics: Sequence[Metric]) -> None:
        self._m = list(metrics)

    def list_metrics(self) -> Sequence[Metric]:
        return self._m


class FakeConn:
    """Devuelve filas fijas, ignora el SQL."""

    def __init__(self, rows: Sequence[Mapping[str, object]] | Exception) -> None:
        self._rows = rows

    def fetch(self, sql: str, params: Mapping[str, object]):
        if isinstance(self._rows, Exception):
            raise self._rows
        return self._rows


def _metric(
    key: str,
    db_mapping: str = "SELECT 1",
    athena_mapping: str = "SELECT 1",
    db_source: str = "postgres",
    source: MetricSource = MetricSource.DIM_USER,
    reconcile_column: str = "value",
) -> Metric:
    return Metric(
        id=MetricId(key),
        name=key,
        key=key,
        source=source,
        formula="",
        db_mapping=db_mapping,
        db_source=db_source,
        athena_mapping=athena_mapping,
        reconcile_column=reconcile_column,
    )


CUT = date(2026, 10, 1)


def test_identical_values_are_ok() -> None:
    repo = FakeRepo([_metric("m")])
    rep = reconcile(repo, FakeConn([{"value": 100}]), FakeConn([{"value": 100}]), CUT)
    assert rep.counts == {"OK": 1, "WARN": 0, "BLOCK": 0}
    assert not rep.blocked


def test_difference_beyond_tolerance_blocks() -> None:
    repo = FakeRepo([_metric("m")])
    rep = reconcile(
        repo, FakeConn([{"value": 100}]), FakeConn([{"value": 80}]), CUT
    )
    assert rep.rows[0].status == "BLOCK"
    assert rep.blocked
    assert rep.rows[0].diff_abs == 20
    assert abs(rep.rows[0].diff_pct - 20.0) < 1e-9


def test_difference_within_pct_tolerance_warns() -> None:
    repo = FakeRepo([_metric("m")])
    rep = reconcile(
        repo,
        FakeConn([{"value": 100}]),
        FakeConn([{"value": 96}]),
        CUT,
        tolerance_pct=5.0,
    )
    assert rep.rows[0].status == "WARN"
    assert not rep.blocked


def test_difference_within_abs_tolerance_warns() -> None:
    repo = FakeRepo([_metric("m")])
    rep = reconcile(
        repo,
        FakeConn([{"value": 1000}]),
        FakeConn([{"value": 995}]),
        CUT,
        tolerance_abs=10,
    )
    assert rep.rows[0].status == "WARN"


def test_source_error_blocks() -> None:
    repo = FakeRepo([_metric("m")])
    rep = reconcile(
        repo,
        FakeConn([{"value": 100}]),
        FakeConn(RuntimeError("Athena boom")),
        CUT,
    )
    assert rep.rows[0].status == "BLOCK"
    assert "Athena" in rep.rows[0].detail


def test_mysql_metric_is_skipped() -> None:
    """Las métricas db_source=mysql no se reconcilian (no están en el lake)."""
    repo = FakeRepo([_metric("m", db_source="mysql")])
    rep = reconcile(repo, FakeConn([{"value": 1}]), FakeConn([{"value": 1}]), CUT)
    assert len(rep.rows) == 0


def test_untranslated_metric_is_skipped() -> None:
    """Métrica sin athena_mapping no se reconcilia."""
    repo = FakeRepo([_metric("m", athena_mapping="")])
    rep = reconcile(repo, FakeConn([{"value": 1}]), FakeConn([{"value": 1}]), CUT)
    assert len(rep.rows) == 0


def test_manual_metric_is_skipped() -> None:
    repo = FakeRepo([_metric("m", source=MetricSource.MANUAL)])
    rep = reconcile(repo, FakeConn([{"value": 1}]), FakeConn([{"value": 1}]), CUT)
    assert len(rep.rows) == 0


def test_reconcile_column_aggregates_target_column() -> None:
    """Con reconcile_column='certificados', suma esa columna, no 'value'."""
    repo = FakeRepo([_metric("slide1", reconcile_column="certificados")])
    pg_rows = [
        {"value": 19, "certificados": 10965},
        {"value": 21, "certificados": 35569},
    ]
    ath_rows = [
        {"value": 19, "certificados": 10965},
        {"value": 21, "certificados": 35569},
    ]
    rep = reconcile(repo, FakeConn(pg_rows), FakeConn(ath_rows), CUT)
    # Suma certificados: 46534 en ambos -> OK
    assert rep.rows[0].pg_value == 46534
    assert rep.rows[0].status == "OK"


def test_only_keys_filters() -> None:
    repo = FakeRepo([_metric("a"), _metric("b")])
    rep = reconcile(
        repo,
        FakeConn([{"value": 1}]),
        FakeConn([{"value": 1}]),
        CUT,
        only_keys=["b"],
    )
    assert len(rep.rows) == 1
    assert rep.rows[0].metric_key == "b"


def test_multirow_sum_value() -> None:
    """slide2: suma 'value' de todas las filas (personas por curso)."""
    repo = FakeRepo([_metric("slide2")])
    pg = [{"value": 100}, {"value": 200}, {"value": 50}]
    ath = [{"value": 100}, {"value": 200}, {"value": 50}]
    rep = reconcile(repo, FakeConn(pg), FakeConn(ath), CUT)
    assert rep.rows[0].pg_value == 350
    assert rep.rows[0].status == "OK"
