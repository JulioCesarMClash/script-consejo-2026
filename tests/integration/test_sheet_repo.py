"""Tests de integración para GoogleMcpSheetRepo con proxy falso.

Verifica que el adapter de Sheets construye correctamente los 5 sheets,
que no llama a Slides, y que maneja correctamente bundles con/sin DQS issues.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.consejo.adapters.sheets.google_mcp_sheet_repo import (
    GoogleMcpSheetRepo,
    SHEET_NAMES,
)
from src.consejo.domain.entities import Bundle, DqsIssue
from src.consejo.domain.value_objects import (
    AttemptId,
    Cut,
    HashSha256,
    RunId,
)


class FakeMcpProcess:
    """Simula la comunicación stdio con el proxy MCP."""

    def __init__(self) -> None:
        self.stdin_lines: list[str] = []
        self.stdout_lines: list[str] = []
        self.next_id = 1

    def write_stdin(self, line: str) -> None:
        self.stdin_lines.append(line.strip())

    def read_stdout(self) -> str:
        if not self.stdout_lines:
            return ""
        return self.stdout_lines.pop(0) + "\n"


@pytest.fixture
def sample_bundle() -> Bundle:
    """Bundle válido de prueba."""
    return Bundle(
        run_id=RunId.generate(),
        attempt_id=AttemptId.generate(),
        cut=Cut(date(2026, 7, 1)),
        catalog_hash="a" * 64,
        manifests=(),
        rows=(),
        dqs=(),
        hash=HashSha256("b" * 64),
    )


@pytest.fixture
def bundle_with_dqs_issues() -> Bundle:
    """Bundle con issues DQS (warnings, no blockers)."""
    return Bundle(
        run_id=RunId.generate(),
        attempt_id=AttemptId.generate(),
        cut=Cut(date(2026, 7, 1)),
        catalog_hash="c" * 64,
        manifests=(),
        rows=(
            {"metric_id": "registered_cpe", "source": "dim_user", "value": 150},
        ),
        dqs=(
            DqsIssue(
                obligation=3,
                code="DQS-003-EMPTY_SOURCE",
                severity="warning",
                message="Fuente vacía para beneficiaries",
            ),
        ),
        hash=HashSha256("d" * 64),
    )


def _build_proxy_response(req_id: int, result: Any = None) -> dict:
    """Construye una respuesta JSON-RPC exitosa."""
    return {"jsonrpc": "2.0", "id": req_id, "result": result or {}}


def _build_spreadsheet_meta(
    existing_sheets: list[str] | None = None,
) -> dict:
    """Construye metadatos de spreadsheet."""
    if existing_sheets is None:
        existing_sheets = SHEET_NAMES[:2]  # solo Control y Datos
    return {
        "fields": {
            "sheets": [
                {"properties": {"title": name}}
                for name in existing_sheets
            ]
        }
    }


class TestGoogleMcpSheetRepo:
    """Verifica el comportamiento del adapter de Sheets con proxy falso."""

    def test_snapshot_creates_five_sheets(
        self, sample_bundle: Bundle
    ) -> None:
        """El snapshot debe crear/actualizar las 5 hojas."""
        captured_requests: list[dict] = []

        with patch.object(
            GoogleMcpSheetRepo, "_start_proxy"
        ), patch.object(
            GoogleMcpSheetRepo, "_init_handshake"
        ), patch.object(
            GoogleMcpSheetRepo, "_get_spreadsheet_meta",
            return_value=_build_spreadsheet_meta([]),
        ), patch.object(
            GoogleMcpSheetRepo, "_call_tool",
        ) as mock_call:
            repo = GoogleMcpSheetRepo()

            def capture_and_return(name: str, arguments: dict) -> dict:
                if name == "update_sheet":
                    captured_requests.append(arguments)
                elif name == "get_spreadsheet":
                    return _build_spreadsheet_meta([])
                return {}

            mock_call.side_effect = capture_and_return

            result = repo.snapshot(sample_bundle, "test-spreadsheet-id")
            assert result == "test-spreadsheet-id"

        assert len(captured_requests) >= 1
        all_requests = captured_requests[0].get("requests", [])
        created_sheets = [
            r["addSheet"]["properties"]["title"]
            for r in all_requests
            if "addSheet" in r
        ]
        assert set(created_sheets) == set(SHEET_NAMES)

    def test_snapshot_with_existing_sheets_partial(
        self, sample_bundle: Bundle
    ) -> None:
        """Si algunas hojas ya existen, solo crea las faltantes."""
        existing = ["Control", "Datos"]

        with patch.object(
            GoogleMcpSheetRepo, "_start_proxy"
        ), patch.object(
            GoogleMcpSheetRepo, "_init_handshake"
        ), patch.object(
            GoogleMcpSheetRepo, "_get_spreadsheet_meta",
            return_value=_build_spreadsheet_meta(existing),
        ), patch.object(
            GoogleMcpSheetRepo, "_call_tool",
        ) as mock_call:
            captured_requests: list[dict] = []

            def capture(name: str, arguments: dict) -> dict:
                if name == "update_sheet":
                    captured_requests.append(arguments)
                elif name == "get_spreadsheet":
                    return _build_spreadsheet_meta(existing)
                return {}

            mock_call.side_effect = capture

            repo = GoogleMcpSheetRepo()
            repo.snapshot(sample_bundle, "test-id")

        assert len(captured_requests) >= 1
        all_reqs = captured_requests[0].get("requests", [])
        created = [
            r["addSheet"]["properties"]["title"]
            for r in all_reqs
            if "addSheet" in r
        ]
        expected_new = ["Reporte", "Errores", "Configuracion"]
        assert set(created) == set(expected_new)

    def test_snapshot_populates_control_sheet(
        self, sample_bundle: Bundle
    ) -> None:
        """La hoja Control debe tener campos clave del bundle."""
        with patch.object(
            GoogleMcpSheetRepo, "_start_proxy"
        ), patch.object(
            GoogleMcpSheetRepo, "_init_handshake"
        ), patch.object(
            GoogleMcpSheetRepo, "_get_spreadsheet_meta",
            return_value=_build_spreadsheet_meta([]),
        ), patch.object(
            GoogleMcpSheetRepo, "_call_tool",
        ) as mock_call:
            captured: list[dict] = []

            def cap(name: str, args: dict) -> dict:
                if name == "update_sheet":
                    captured.append(args)
                elif name == "get_spreadsheet":
                    return _build_spreadsheet_meta([])
                return {}

            mock_call.side_effect = cap

            repo = GoogleMcpSheetRepo()
            repo.snapshot(sample_bundle, "test-id")

        all_reqs = captured[0].get("requests", [])
        # Buscar el updateCells para Control (sheetId=0)
        control_updates = [
            r for r in all_reqs
            if r.get("updateCells", {}).get("start", {}).get("sheetId") == 0
        ]
        assert len(control_updates) >= 1
        control_rows = control_updates[0]["updateCells"]["rows"]
        # Debe contener: run_id, attempt_id, cut, catalog_hash, bundle_hash
        all_strings = ""
        for row_data in control_rows:
            for cell in row_data.get("values", []):
                all_strings += cell.get("userEnteredValue", {}).get("stringValue", "")
        assert "run_id" in all_strings
        assert "attempt_id" in all_strings
        assert str(sample_bundle.cut) in all_strings
        assert sample_bundle.catalog_hash in all_strings
        assert str(sample_bundle.hash) in all_strings

    def test_snapshot_populates_datos_sheet(
        self, bundle_with_dqs_issues: Bundle
    ) -> None:
        """La hoja Datos debe tener las filas del bundle."""
        with patch.object(
            GoogleMcpSheetRepo, "_start_proxy"
        ), patch.object(
            GoogleMcpSheetRepo, "_init_handshake"
        ), patch.object(
            GoogleMcpSheetRepo, "_get_spreadsheet_meta",
            return_value=_build_spreadsheet_meta([]),
        ), patch.object(
            GoogleMcpSheetRepo, "_call_tool",
        ) as mock_call:
            captured: list[dict] = []

            def cap(name: str, args: dict) -> dict:
                if name == "update_sheet":
                    captured.append(args)
                elif name == "get_spreadsheet":
                    return _build_spreadsheet_meta([])
                return {}

            mock_call.side_effect = cap

            repo = GoogleMcpSheetRepo()
            repo.snapshot(bundle_with_dqs_issues, "test-id")

        all_reqs = captured[0].get("requests", [])
        datos_updates = [
            r for r in all_reqs
            if r.get("updateCells", {}).get("start", {}).get("sheetId") == 1
        ]
        assert len(datos_updates) >= 1
        datos_rows = datos_updates[0]["updateCells"]["rows"]
        # header + 1 data row = 2 rows
        assert len(datos_rows) == 2

    def test_snapshot_populates_errores_sheet(
        self, bundle_with_dqs_issues: Bundle
    ) -> None:
        """La hoja Errores debe tener los DQS issues."""
        with patch.object(
            GoogleMcpSheetRepo, "_start_proxy"
        ), patch.object(
            GoogleMcpSheetRepo, "_init_handshake"
        ), patch.object(
            GoogleMcpSheetRepo, "_get_spreadsheet_meta",
            return_value=_build_spreadsheet_meta([]),
        ), patch.object(
            GoogleMcpSheetRepo, "_call_tool",
        ) as mock_call:
            captured: list[dict] = []

            def cap(name: str, args: dict) -> dict:
                if name == "update_sheet":
                    captured.append(args)
                elif name == "get_spreadsheet":
                    return _build_spreadsheet_meta([])
                return {}

            mock_call.side_effect = cap

            repo = GoogleMcpSheetRepo()
            repo.snapshot(bundle_with_dqs_issues, "test-id")

        all_reqs = captured[0].get("requests", [])
        errores_updates = [
            r for r in all_reqs
            if r.get("updateCells", {}).get("start", {}).get("sheetId") == 3
        ]
        assert len(errores_updates) >= 1
        errores_rows = errores_updates[0]["updateCells"]["rows"]
        assert len(errores_rows) == 2  # header + 1 issue

    def test_snapshot_does_not_call_slides(
        self, sample_bundle: Bundle
    ) -> None:
        """El snapshot no debe hacer ninguna llamada a Slides."""
        with patch.object(
            GoogleMcpSheetRepo, "_start_proxy"
        ), patch.object(
            GoogleMcpSheetRepo, "_init_handshake"
        ), patch.object(
            GoogleMcpSheetRepo, "_get_spreadsheet_meta",
            return_value=_build_spreadsheet_meta([]),
        ), patch.object(
            GoogleMcpSheetRepo, "_call_tool",
        ) as mock_call:
            mock_call.return_value = {}

            repo = GoogleMcpSheetRepo()
            repo.snapshot(sample_bundle, "test-id")

        # Verificar que todas las llamadas fueron a get_spreadsheet o update_sheet
        for call_args in mock_call.call_args_list:
            tool_name = call_args[0][0] if call_args[0] else ""
            assert tool_name in (
                "get_spreadsheet",
                "update_sheet",
            ), f"No se debe llamar a {tool_name}"

    def test_snapshot_handles_proxy_error(
        self, sample_bundle: Bundle
    ) -> None:
        """Error de proxy debe propagarse sin exponer secretos."""
        from src.consejo.adapters.sheets.google_mcp_sheet_repo import (
            SheetProxyError,
        )

        with patch.object(
            GoogleMcpSheetRepo, "_start_proxy"
        ), patch.object(
            GoogleMcpSheetRepo, "_init_handshake"
        ), patch.object(
            GoogleMcpSheetRepo, "_get_spreadsheet_meta",
            side_effect=SheetProxyError("Proxy caído"),
        ):
            repo = GoogleMcpSheetRepo()
            with pytest.raises(SheetProxyError) as exc_info:
                repo.snapshot(sample_bundle, "test-id")
            # El mensaje debe ser sanitizado (sin secretos)
            assert "Proxy" in str(exc_info.value)

    def test_sanitize_removes_secrets(self) -> None:
        """_sanitize debe eliminar DB_PASSWORD de los mensajes."""
        import os
        from src.consejo.adapters.sheets.google_mcp_sheet_repo import (
            _sanitize,
        )

        os.environ["DB_PASSWORD"] = "super-secret-123"
        msg = "Error con super-secret-123 en conexión"
        result = _sanitize(msg)
        assert "super-secret-123" not in result
        assert "***" in result
