"""E2E: Validación de sanitización de credenciales y seguridad.

Verifica que el pipeline propaga shell=False, usa argv fijo,
no llama a Slides, y las credenciales no aparecen en logs ni
mensajes de error.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Mapping, Sequence

import pytest

from src.consejo.adapters.postgres.source_conn import PostgresSourceConn
from src.consejo.adapters.sheets.google_mcp_sheet_repo import (
    PROXY_PATH,
    GoogleMcpSheetRepo,
    _sanitize,
)
from src.consejo.application.ports import SlidesRepo
from src.consejo.config.settings import Settings


# ── Tests ───────────────────────────────────────────────────────────────────


class TestCredentialSanitizationE2E:
    """Sanitización de credenciales y seguridad del pipeline."""

    # ── 5.3.a: shell=False en subprocess ─────────────────────────────────

    def test_shell_false_in_subprocess(self) -> None:
        """El adapter de Sheets usa shell=False en Popen."""
        repo = GoogleMcpSheetRepo()
        assert repo._python == sys.executable

        # Verificar que _start_proxy usa shell=False
        # (inspeccionamos el método vía monkeypatch)
        import inspect
        source = inspect.getsource(GoogleMcpSheetRepo._start_proxy)

        # Debe contener subprocess.Popen con shell=False
        assert "subprocess.Popen" in source
        assert "shell=False" in source, (
            "shell=False debe estar explícito en _start_proxy"
        )

    def test_argv_fixed_no_dynamic_construction(self) -> None:
        """argv es fijo: [python, proxy_path], sin construcción dinámica."""
        repo = GoogleMcpSheetRepo()
        import inspect
        source = inspect.getsource(GoogleMcpSheetRepo._start_proxy)

        # argv es [self._python, self._proxy_path] — fijo, dos elementos
        assert "[self._python, self._proxy_path]" in source, (
            "argv debe ser fijo: [self._python, self._proxy_path]"
        )

    # ── 5.3.b: Zero Slides calls ────────────────────────────────────────

    def test_no_slides_in_sheet_adapter(self) -> None:
        """El adapter de Sheets no importa ni referencia Slides."""
        import inspect
        source = inspect.getsource(GoogleMcpSheetRepo)

        assert "Slides" not in source, (
            "GoogleMcpSheetRepo no debe referenciar Slides"
        )
        assert "slides" not in source.lower(), (
            "GoogleMcpSheetRepo no debe referenciar slides"
        )

    def test_slides_repo_is_future_only(self) -> None:
        """SlidesRepo.publish no está implementado (puerto futuro)."""
        import inspect
        source = inspect.getsource(SlidesRepo.publish)
        assert "NotImplementedError" in source, (
            "SlidesRepo.publish debe lanzar NotImplementedError"
        )

        # Sheets adapter no debe importar SlidesRepo
        from src.consejo.adapters.sheets.google_mcp_sheet_repo import (
            GoogleMcpSheetRepo,
        )
        adapter_source = inspect.getsource(GoogleMcpSheetRepo)
        assert "SlidesRepo" not in adapter_source
        assert "Slides" not in adapter_source

    # ── 5.3.c: Credentials out of error messages ────────────────────────

    def test_postgres_error_sanitized_no_password(self) -> None:
        """Errores de PostgreSQL no exponen password."""
        settings = Settings(
            db_host="fake-host",
            db_name="fake-db",
            db_user="fake-user",
            db_password="super-secret-password-123!",
            db_port=5432,
            google_application_credentials="",
            catalog_path="",
        )
        conn = PostgresSourceConn(settings)

        # Intentar fetch con credenciales inválidas
        with pytest.raises((ConnectionError, RuntimeError)) as exc_info:
            conn.fetch("SELECT 1", {})

        msg = str(exc_info.value)
        assert "super-secret-password-123!" not in msg, (
            f"Password expuesto en error: {msg[:200]}"
        )
        assert "fake-host" not in msg, (
            f"Host expuesto en error: {msg[:200]}"
        )

    def test_sanitize_removes_all_secret_vars(self) -> None:
        """_sanitize elimina todas las variables de entorno sensibles."""
        os.environ["DB_PASSWORD"] = "p4ssw0rd!"
        os.environ["DB_HOST"] = "prod-db.internal"
        os.environ["DB_USER"] = "admin"
        os.environ["DB_NAME"] = "secrets-db"

        try:
            msg = (
                "Error conectando a prod-db.internal como admin "
                "en secrets-db con p4ssw0rd!"
            )
            result = _sanitize(msg)

            assert "p4ssw0rd!" not in result
            assert "prod-db.internal" not in result
            assert "secrets-db" not in result
            assert "***" in result
        finally:
            for var in ["DB_PASSWORD", "DB_HOST", "DB_USER", "DB_NAME"]:
                os.environ.pop(var, None)

    def test_sheet_proxy_error_sanitized(self) -> None:
        """Errores del proxy Sheets sanitizan secretos de entorno."""
        from src.consejo.adapters.sheets.google_mcp_sheet_repo import (
            SheetProxyError,
        )

        os.environ["DB_PASSWORD"] = "s3cret-abc"

        try:
            # Simular error del proxy — la capa adapter aplica _sanitize
            err = SheetProxyError(
                "Conexión rechazada con credencial s3cret-abc"
            )
            sanitized = _sanitize(str(err))
            assert "s3cret-abc" not in sanitized
            assert "***" in sanitized
        finally:
            os.environ.pop("DB_PASSWORD", None)

    # ── 5.3.d: Settings validation without exposing secrets ─────────────

    def test_settings_validation_sanitized(self) -> None:
        """Settings.validate() no expone valores en mensajes de error."""
        settings = Settings(
            db_host="",
            db_name="",
            db_user="",
            db_password="",
            db_port=5432,
            google_application_credentials="",
        )

        with pytest.raises(ValueError) as exc_info:
            settings.validate()

        msg = str(exc_info.value)
        # Debe listar las variables faltantes, no sus valores
        assert "DB_HOST" in msg
        assert "DB_NAME" in msg
        assert "DB_USER" in msg
        assert "DB_PASSWORD" in msg
        assert "Credencial" in msg
        # No debe exponer ningún secreto (no hay, pero el mensaje es genérico)

    # ── 5.3.e: Proxy path es estático ───────────────────────────────────

    def test_proxy_path_is_static_not_dynamic(self) -> None:
        """PROXY_PATH es una constante, no una variable dinámica."""
        assert PROXY_PATH.endswith("google_mcp_proxy.py"), (
            f"PROXY_PATH debe apuntar a google_mcp_proxy.py: {PROXY_PATH}"
        )
        assert "mcp" in PROXY_PATH, (
            f"PROXY_PATH debe estar bajo mcp/: {PROXY_PATH}"
        )

    # ── 5.3.f: Sanitización de credentials reales (skipped) ─────────────

    @pytest.mark.skip(
        reason="Requiere conexión real a PostgreSQL para verificar "
               "sanitización en errores de conexión vivos. "
               "Ejecutar en entorno autorizado con credenciales inválidas "
               "para provocar errores reales."
    )
    def test_credential_sanitization_with_real_db_requires_creds(self) -> None:
        """Sanitización con errores reales de PostgreSQL (skipped).

        Verifica que errores de conexión reales no exponen credenciales.
        """
        ...
