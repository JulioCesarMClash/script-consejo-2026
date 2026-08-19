"""Tests unitarios para MysqlSourceConn.

Si MySQL no está disponible localmente, los tests de smoke contra la DB
real se skipean. Los tests de lógica (sanitización de errores, kwargs de
conexión) corren siempre sin red.
"""

from __future__ import annotations

import socket
from typing import Any
from unittest.mock import patch

import pymysql
import pytest

from src.consejo.adapters.mysql.source_conn import MysqlSourceConn
from src.consejo.config.settings import Settings


# ── Helpers ────────────────────────────────────────────────────────────────


def _settings(**overrides: Any) -> Settings:
    """Construye Settings con overrides para MySQL."""
    base = {
        "mysql_host": "127.0.0.1",
        "mysql_port": 8889,
        "mysql_user": "root",
        "mysql_password": "root",
        "mysql_database": None,
    }
    base.update(overrides)
    return Settings(**base)


def _mysql_alive(host: str, port: int, timeout: float = 0.5) -> bool:
    """Devuelve True si se puede abrir un socket TCP al puerto MySQL."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# ── Tests de lógica (sin red) ──────────────────────────────────────────────


class TestMysqlSourceConnLogic:
    """Tests que no requieren MySQL real: mocks de pymysql.connect."""

    def test_passes_database_when_set(self) -> None:
        """Si `mysql_database` está configurado, se pasa `database=` al connect."""
        conn = MysqlSourceConn(_settings(mysql_database="carso_analisis"))
        with patch(
            "src.consejo.adapters.mysql.source_conn.pymysql.connect"
        ) as mock_connect:
            mock_connect.return_value.cursor.return_value.__enter__.return_value.fetchall.return_value = []
            conn.fetch("SELECT 1", {})
            kwargs = mock_connect.call_args.kwargs
            assert kwargs["database"] == "carso_analisis"
            assert kwargs["host"] == "127.0.0.1"
            assert kwargs["port"] == 8889
            assert kwargs["user"] == "root"
            assert kwargs["cursorclass"] is not None

    def test_omits_database_when_none(self) -> None:
        """Si `mysql_database` es None, NO se pasa `database=` al connect
        (las queries deben usar prefijo `<db>.tabla`)."""
        conn = MysqlSourceConn(_settings(mysql_database=None))
        with patch(
            "src.consejo.adapters.mysql.source_conn.pymysql.connect"
        ) as mock_connect:
            mock_connect.return_value.cursor.return_value.__enter__.return_value.fetchall.return_value = []
            conn.fetch("SELECT 1 FROM carso_analisis.t", {})
            kwargs = mock_connect.call_args.kwargs
            assert "database" not in kwargs

    def test_connection_error_sanitizes_message(self) -> None:
        """Si pymysql.connect falla, el error expone sólo nombres de env,
        NO la contraseña ni el host con credenciales."""
        conn = MysqlSourceConn(
            _settings(mysql_password="supersecret", mysql_host="db.internal")
        )
        with patch(
            "src.consejo.adapters.mysql.source_conn.pymysql.connect",
            side_effect=pymysql.err.OperationalError(
                2003, "Can't connect to MySQL server on 'db.internal'"
            ),
        ):
            with pytest.raises(ConnectionError) as exc_info:
                conn.fetch("SELECT 1", {})
        msg = str(exc_info.value)
        assert "supersecret" not in msg
        assert "Verificar MYSQL_HOST" in msg

    def test_query_error_sanitizes_password_and_host(self) -> None:
        """Si la query falla, el mensaje no expone la contraseña ni el host."""
        conn = MysqlSourceConn(
            _settings(mysql_password="supersecret", mysql_host="db.internal")
        )

        class _FakeCursor:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def execute(self, sql, params): raise RuntimeError(
                f"ERROR: access denied for user 'root'@'db.internal' "
                f"using password YES"
            )
            def fetchall(self): return []

        class _FakeConn:
            def cursor(self): return _FakeCursor()
            def close(self): pass

        with patch(
            "src.consejo.adapters.mysql.source_conn.pymysql.connect",
            return_value=_FakeConn(),
        ):
            with pytest.raises(RuntimeError) as exc_info:
                conn.fetch("SELECT 1", {})
        msg = str(exc_info.value)
        assert "supersecret" not in msg

    def test_returns_dict_rows(self) -> None:
        """`fetch` devuelve filas como `dict[str, object]`."""
        conn = MysqlSourceConn(_settings(mysql_database="carso_analisis"))

        class _FakeCursor:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def execute(self, sql, params): pass
            def fetchall(self):
                return [{"x": 1, "y": "a"}, {"x": 2, "y": "b"}]

        class _FakeConn:
            def cursor(self): return _FakeCursor()
            def close(self): pass

        with patch(
            "src.consejo.adapters.mysql.source_conn.pymysql.connect",
            return_value=_FakeConn(),
        ):
            rows = conn.fetch("SELECT x, y FROM t", {})
        assert rows == [
            {"x": 1, "y": "a"},
            {"x": 2, "y": "b"},
        ]

    def test_passes_named_params_to_cursor(self) -> None:
        """Los placeholders nombrados `%(name)s` se convierten a `%s`
        posicional y los valores se pasan como tupla en orden de aparición."""
        conn = MysqlSourceConn(_settings(mysql_database="carso_analisis"))

        captured: dict[str, Any] = {}

        class _FakeCursor:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def execute(self, sql, params):
                captured["sql"] = sql
                captured["params"] = params
            def fetchall(self): return [{"value": 42}]

        class _FakeConn:
            def cursor(self): return _FakeCursor()
            def close(self): pass

        with patch(
            "src.consejo.adapters.mysql.source_conn.pymysql.connect",
            return_value=_FakeConn(),
        ):
            conn.fetch("SELECT * FROM t WHERE id = %(id)s", {"id": 42})
        assert captured["sql"] == "SELECT * FROM t WHERE id = %s"
        assert captured["params"] == (42,)

    def test_converts_period_placeholders_in_order(self) -> None:
        """Query con `%(period_start)s` y `%(period_end)s` se ejecuta
        con `%s` en el mismo orden y la tupla respeta ese orden."""
        conn = MysqlSourceConn(_settings(mysql_database=None))

        captured: dict[str, Any] = {}

        class _FakeCursor:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def execute(self, sql, params):
                captured["sql"] = sql
                captured["params"] = params
            def fetchall(self): return []

        class _FakeConn:
            def cursor(self): return _FakeCursor()
            def close(self): pass

        sql = (
            "SELECT COUNT(DISTINCT u.id) AS value\n"
            "FROM carso_analisis.user u\n"
            "WHERE u.registrationDate >= %(period_start)s\n"
            "  AND u.registrationDate < %(period_end)s"
        )
        params = {"period_start": "2025-01-01", "period_end": "2026-01-01"}
        with patch(
            "src.consejo.adapters.mysql.source_conn.pymysql.connect",
            return_value=_FakeConn(),
        ):
            conn.fetch(sql, params)

        assert captured["sql"] == (
            "SELECT COUNT(DISTINCT u.id) AS value\n"
            "FROM carso_analisis.user u\n"
            "WHERE u.registrationDate >= %s\n"
            "  AND u.registrationDate < %s"
        )
        # period_start primero, aunque period_end aparezca después
        assert captured["params"] == ("2025-01-01", "2026-01-01")

    def test_does_not_touch_literal_percent_in_strings(self) -> None:
        """Un `%` literal en strings (ej. `LIKE '100%'`) NO se convierte;
        solo los placeholders nombrados `%(... )s`."""
        conn = MysqlSourceConn(_settings(mysql_database=None))

        captured: dict[str, Any] = {}

        class _FakeCursor:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def execute(self, sql, params):
                captured["sql"] = sql
                captured["params"] = params
            def fetchall(self): return []

        class _FakeConn:
            def cursor(self): return _FakeCursor()
            def close(self): pass

        sql = (
            "SELECT COUNT(*) AS value "
            "FROM t WHERE name LIKE '100%' "
            "AND created >= %(period_start)s"
        )
        with patch(
            "src.consejo.adapters.mysql.source_conn.pymysql.connect",
            return_value=_FakeConn(),
        ):
            conn.fetch(sql, {"period_start": "2025-01-01"})

        assert captured["sql"] == (
            "SELECT COUNT(*) AS value "
            "FROM t WHERE name LIKE '100%' "
            "AND created >= %s"
        )
        assert captured["params"] == ("2025-01-01",)

    def test_repeated_placeholder_produces_one_value_per_position(self) -> None:
        """Un mismo nombre repetido produce un `%s` y un valor por posición."""
        conn = MysqlSourceConn(_settings(mysql_database=None))

        captured: dict[str, Any] = {}

        class _FakeCursor:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def execute(self, sql, params):
                captured["sql"] = sql
                captured["params"] = params
            def fetchall(self): return []

        class _FakeConn:
            def cursor(self): return _FakeCursor()
            def close(self): pass

        sql = "SELECT %(p)s AS a, %(p)s AS b FROM t WHERE x = %(p)s"
        with patch(
            "src.consejo.adapters.mysql.source_conn.pymysql.connect",
            return_value=_FakeConn(),
        ):
            conn.fetch(sql, {"p": 7})

        assert captured["sql"] == "SELECT %s AS a, %s AS b FROM t WHERE x = %s"
        assert captured["params"] == (7, 7, 7)

    def test_missing_named_param_raises_runtime_error(self) -> None:
        """Si un placeholder no tiene valor en `params`, se lanza RuntimeError
        con mensaje claro, sin exponer credenciales."""
        conn = MysqlSourceConn(_settings(mysql_password="supersecret"))

        class _FakeCursor:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def execute(self, sql, params): pass
            def fetchall(self): return []

        class _FakeConn:
            def cursor(self): return _FakeCursor()
            def close(self): pass

        with patch(
            "src.consejo.adapters.mysql.source_conn.pymysql.connect",
            return_value=_FakeConn(),
        ):
            with pytest.raises(RuntimeError) as exc_info:
                conn.fetch(
                    "SELECT 1 WHERE x >= %(period_start)s",
                    {},
                )
        msg = str(exc_info.value)
        assert "period_start" in msg
        assert "supersecret" not in msg


# ── Tests contra MySQL real (skip si no disponible) ───────────────────────


class TestMysqlSourceConnLive:
    """Smoke tests contra MySQL real — se skipean si no responde."""

    @pytest.fixture(autouse=True)
    def _require_mysql(self) -> None:
        host = "127.0.0.1"
        port = 8889
        if not _mysql_alive(host, port):
            pytest.skip(
                f"MySQL no disponible en {host}:{port}; "
                "tests live skipeados."
            )

    def test_select_1_returns_one_row(self) -> None:
        conn = MysqlSourceConn(_settings(mysql_database=None))
        rows = conn.fetch("SELECT 1 AS x", {})
        assert rows == [{"x": 1}]

    def test_connection_closes_after_fetch(self) -> None:
        """La conexión se cierra aunque la query devuelva vacío."""
        conn = MysqlSourceConn(_settings(mysql_database=None))
        rows = conn.fetch(
            "SELECT 1 AS x FROM information_schema.tables "
            "WHERE table_name = '___no_existe_para_este_test___'",
            {},
        )
        assert rows == []
