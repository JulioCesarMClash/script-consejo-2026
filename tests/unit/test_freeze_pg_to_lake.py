"""Tests del congelado PG -> datalake (partes puras, sin red)."""

from __future__ import annotations

import importlib.util
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

# pyarrow no es dependencia del proyecto: el script corre con
# `uv run --with "pyiceberg[pyarrow]"`. Sin pyarrow estos tests se omiten.
pa = pytest.importorskip("pyarrow")

_RUTA = Path(__file__).resolve().parents[2] / "scripts" / "freeze_pg_to_lake.py"
_spec = importlib.util.spec_from_file_location("freeze_pg_to_lake", _RUTA)
freeze = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(freeze)


COLUMNAS_DIM_USER = [
    ("userId", "character varying", None, None),
    ("plataformaId", "smallint", None, None),
    ("registrationDate", "timestamp without time zone", None, None),
    ("localId", "bigint", None, None),
    ("email", "character varying", None, None),
    ("isDeleted", "boolean", None, None),
    ("birthday", "date", None, None),
]


def test_dim_user_excluye_email_y_baja_nombres_a_minuscula():
    schema, select_cols = freeze.construir_schema("dim_user", COLUMNAS_DIM_USER)

    assert select_cols == [
        "userId", "plataformaId", "registrationDate", "localId", "isDeleted", "birthday",
    ]
    assert schema.names == [
        "userid", "plataformaid", "registrationdate", "localid", "isdeleted", "birthday",
    ]
    assert "email" not in [n.lower() for n in schema.names]


def test_mapeo_de_tipos_pg_a_arrow():
    schema, _ = freeze.construir_schema("dim_user", COLUMNAS_DIM_USER)

    assert schema.field("userid").type == pa.string()
    assert schema.field("plataformaid").type == pa.int32()  # Iceberg no tiene int16
    assert schema.field("localid").type == pa.int64()
    assert schema.field("registrationdate").type == pa.timestamp("us")
    assert schema.field("isdeleted").type == pa.bool_()
    assert schema.field("birthday").type == pa.date32()


def test_numeric_conserva_precision_y_escala():
    cols = [("scoreCourse", "numeric", 4, 2), ("courseId", "integer", None, None)]
    schema, _ = freeze.construir_schema("fact_inscription", cols)

    assert schema.field("scorecourse").type == pa.decimal128(4, 2)
    assert schema.field("courseid").type == pa.int32()


def test_tablas_snapshot_permitidas_y_timestamptz_en_utc():
    cols = [
        ("run_id", "integer", None, None),
        ("notes", "text", None, None),
        ("created_at", "timestamp with time zone", None, None),
    ]
    schema, select_cols = freeze.construir_schema("cpe_snapshot_meta", cols)

    assert select_cols == ["run_id", "notes", "created_at"]
    assert schema.field("notes").type == pa.string()
    assert schema.field("created_at").type == pa.timestamp("us", tz="UTC")
    for t in (
        "analytics_snapshot_run",
        "analytics_snapshot_course_metric",
        "analytics_snapshot_user_metric",
        "analytics_snapshot_course_metric_current",
        "analytics_snapshot_user_metric_current",
    ):
        assert t in freeze.TABLAS


def test_numeric_sin_precision_falla():
    with pytest.raises(ValueError, match="scoreCourse"):
        freeze.construir_schema("fact_inscription", [("scoreCourse", "numeric", None, None)])


def test_tipo_desconocido_falla():
    with pytest.raises(ValueError, match="jsonb"):
        freeze.construir_schema("course", [("extra", "jsonb", None, None)])


def test_tabla_fuera_de_la_lista_permitida_falla():
    with pytest.raises(ValueError, match="no permitida"):
        freeze.construir_schema("users_plaintext", COLUMNAS_DIM_USER)


def test_filas_a_arrow_respeta_schema_y_nulos():
    cols = [
        ("userId", "character varying", None, None),
        ("courseId", "integer", None, None),
        ("certificationDate", "timestamp without time zone", None, None),
        ("scoreCourse", "numeric", 4, 2),
    ]
    schema, _ = freeze.construir_schema("fact_inscription", cols)
    filas = [
        ("u1", 9, datetime(2026, 9, 30, 23, 59, 59), Decimal("9.50")),
        ("u2", 187, None, None),
    ]

    tabla = freeze.filas_a_arrow(filas, schema)

    assert tabla.schema == schema
    assert tabla.num_rows == 2
    assert tabla.column("courseid").to_pylist() == [9, 187]
    assert tabla.column("certificationdate").to_pylist() == [datetime(2026, 9, 30, 23, 59, 59), None]
    assert tabla.column("scorecourse").to_pylist() == [Decimal("9.50"), None]


def test_select_sql_cita_identificadores():
    sql = freeze.select_sql("course", ["id", "platformId"])

    assert sql == 'SELECT "id", "platformId" FROM public."course"'


def test_fecha_date_se_conserva():
    schema, _ = freeze.construir_schema("dim_user", [("birthday", "date", None, None)])
    tabla = freeze.filas_a_arrow([(date(1990, 1, 2),)], schema)

    assert tabla.column("birthday").to_pylist() == [date(1990, 1, 2)]
