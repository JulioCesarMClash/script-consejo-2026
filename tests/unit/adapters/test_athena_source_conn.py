"""Tests unitarios para AthenaSourceConn.

Los tests de lógica (sanitización de errores, mapeo de filas, paso de
placeholders pyformat) corren sin red mockeando `pyathena.connect` y
`boto3.Session`. Los smoke tests contra Athena real se skipean si no hay
sesión SSO activa (variable de entorno RUN_ATHENA_LIVE).
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.consejo.adapters.athena.source_conn import AthenaSourceConn
from src.consejo.config.settings import Settings


def _settings(**overrides: Any) -> Settings:
    base = {
        "source": "athena",
        "aws_profile": "sandbox-datalake",
        "aws_region": "us-east-1",
        "aws_account_id": "278711064005",
        "athena_workgroup": "datalake-fcs",
        "athena_catalog": "s3tablescatalog/datalake-fcs",
        "athena_database": "silver_cpe",
    }
    base.update(overrides)
    return Settings(**base)


def _patch_conn(cursor: Any) -> Any:
    """Devuelve un context manager que mockea boto3.Session y
    pyathena.connect, con `connect(...).cursor()` -> `cursor`."""
    fake_conn = MagicMock()
    fake_conn.cursor.return_value.__enter__.return_value = cursor
    fake_conn.cursor.return_value.__exit__.return_value = False
    return fake_conn


class TestAthenaSourceConnLogic:
    """Tests sin red: mocks de boto3 y pyathena."""

    def test_returns_dict_rows_from_description_and_rows(self) -> None:
        """`fetch` combina `cursor.description` con `fetchall` en dicts."""
        conn = AthenaSourceConn(_settings())

        cursor = MagicMock()
        cursor.description = [("value", "bigint", None, None, None, None, None)]
        cursor.fetchall.return_value = [(10000750,)]
        fake_conn = _patch_conn(cursor)

        with patch("boto3.Session"), patch(
            "pyathena.connect", return_value=fake_conn
        ):
            rows = conn.fetch("SELECT COUNT(*) AS value FROM dim_user", {})

        assert rows == [{"value": 10000750}]

    def test_passes_pyformat_params_unchanged(self) -> None:
        """Los placeholders nombrados se pasan tal cual (paramstyle pyformat);
        el adaptador NO los convierte (a diferencia de MySQL)."""
        conn = AthenaSourceConn(_settings())

        captured: dict[str, Any] = {}
        cursor = MagicMock()
        cursor.description = [("value", "bigint", None, None, None, None, None)]

        def _execute(sql: str, params: Any) -> None:
            captured["sql"] = sql
            captured["params"] = params

        cursor.execute.side_effect = _execute
        cursor.fetchall.return_value = [(1,)]
        fake_conn = _patch_conn(cursor)

        sql = (
            "SELECT COUNT(DISTINCT user_id) AS value FROM dim_user "
            "WHERE plataforma_id = %(pid)s"
        )
        with patch("boto3.Session"), patch(
            "pyathena.connect", return_value=fake_conn
        ):
            conn.fetch(sql, {"pid": 1})

        # SQL intacto, params como dict (pyformat nativo)
        assert captured["sql"] == sql
        assert captured["params"] == {"pid": 1}

    def test_empty_params_pass_none(self) -> None:
        """Sin params, se pasa None al cursor (no un dict vacío)."""
        conn = AthenaSourceConn(_settings())
        captured: dict[str, Any] = {}
        cursor = MagicMock()
        cursor.description = [("x", "integer", None, None, None, None, None)]
        cursor.execute.side_effect = lambda sql, params: captured.update(
            params=params
        )
        cursor.fetchall.return_value = [(1,)]
        fake_conn = _patch_conn(cursor)

        with patch("boto3.Session"), patch(
            "pyathena.connect", return_value=fake_conn
        ):
            conn.fetch("SELECT 1 AS x", {})

        assert captured["params"] is None

    def test_connection_failure_raises_sanitized_connection_error(self) -> None:
        """Si la conexión/SSO falla, se lanza ConnectionError con guía de
        env vars y SIN exponer el account id ni el catálogo."""
        conn = AthenaSourceConn(_settings())

        with patch("boto3.Session"), patch(
            "pyathena.connect",
            side_effect=Exception(
                "token expired for arn:aws:iam::278711064005:role/x"
            ),
        ):
            with pytest.raises(ConnectionError) as exc:
                conn.fetch("SELECT 1", {})

        msg = str(exc.value)
        assert "aws sso login" in msg
        assert "ATHENA_WORKGROUP" in msg
        # El mensaje de guía es fijo; el error crudo con el ARN no se propaga.
        assert "278711064005" not in msg

    def test_query_failure_sanitizes_account_and_catalog(self) -> None:
        """Si la query falla, el account id y el catálogo se enmascaran."""
        conn = AthenaSourceConn(_settings())

        cursor = MagicMock()
        cursor.execute.side_effect = Exception(
            "SYNTAX_ERROR near s3tablescatalog/datalake-fcs "
            "account 278711064005"
        )
        fake_conn = _patch_conn(cursor)

        with patch("boto3.Session"), patch(
            "pyathena.connect", return_value=fake_conn
        ):
            with pytest.raises(RuntimeError) as exc:
                conn.fetch("SELECT bad", {})

        msg = str(exc.value)
        assert "278711064005" not in msg
        assert "s3tablescatalog/datalake-fcs" not in msg
        assert "Error en consulta Athena" in msg

    def test_connection_closed_after_fetch(self) -> None:
        """La conexión se cierra siempre (finally), aun con filas vacías."""
        conn = AthenaSourceConn(_settings())
        cursor = MagicMock()
        cursor.description = []
        cursor.fetchall.return_value = []
        fake_conn = _patch_conn(cursor)

        with patch("boto3.Session"), patch(
            "pyathena.connect", return_value=fake_conn
        ):
            conn.fetch("SELECT 1 WHERE 1=0", {})

        fake_conn.close.assert_called_once()


class TestAthenaSourceConnLive:
    """Smoke test contra Athena real — skip salvo RUN_ATHENA_LIVE=1."""

    @pytest.fixture(autouse=True)
    def _require_live(self) -> None:
        if os.environ.get("RUN_ATHENA_LIVE") != "1":
            pytest.skip(
                "Athena live test skipeado (exportar RUN_ATHENA_LIVE=1 "
                "con sesión SSO activa para correrlo)."
            )

    def test_registered_cpe_count(self) -> None:
        conn = AthenaSourceConn(_settings())
        rows = conn.fetch(
            "SELECT COUNT(DISTINCT user_id) AS value FROM dim_user "
            "WHERE plataforma_id = %(pid)s",
            {"pid": 1},
        )
        assert rows and rows[0]["value"] > 0
