"""Tests de integración para GoogleMcpSheetRepo con proxy falso.

Verifica que el adapter de Sheets construye correctamente los 5 sheets,
que no llama a Slides, y que maneja correctamente bundles con/sin DQS issues.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.consejo.adapters.sheets.google_mcp_sheet_repo import (
    GoogleMcpSheetRepo,
    SHEET_NAMES,
    SLIDE3_TABLE_HEADERS,
    SLIDE4_TABLE_HEADERS,
    _build_slide3_block,
    _build_slide4_block,
    _build_slide_block,
    _project_dic2026,
)
from src.consejo.domain.entities import Bundle, DqsIssue, Metric, SourceManifest
from src.consejo.domain.value_objects import (
    AttemptId,
    Cut,
    FetchStatus,
    HashSha256,
    MetricId,
    MetricSource,
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
def sample_catalog() -> list[Metric]:
    """Catálogo de prueba con nombres y plataformas reales."""
    return [
        Metric(
            id=MetricId("registered_cpe"),
            name="Registrados CPE",
            key="registered_cpe",
            source=MetricSource.DIM_USER,
            formula="COUNT(DISTINCT ...)",
            db_mapping="dim_user",
            platform_scope=["CPE"],
        ),
        Metric(
            id=MetricId("slide1_herramientas_pobreza"),
            name="Herramientas de capacitación combate pobreza extrema (Slide 1)",
            key="slide1_herramientas_pobreza",
            source=MetricSource.FACT_INSCRIPTION,
            formula="...",
            db_mapping="fact_inscription",
            platform_scope=["CPE", "Aprende"],
        ),
    ]


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


_SLIDE_CATEGORIES: list[tuple[str, int, int]] = [
    ("slide1_vivienda", 16, 0),
    ("slide1_digital", 21, 0),
    ("slide1_alimentos", 22, 0),
    ("slide1_desastres", 11, 0),
    ("slide1_empleo", 26, 0),
]


@pytest.fixture
def bundle_with_slide1() -> Bundle:
    """Bundle con un manifest slide1 de 5 categorías."""
    rows = [
        {
            "metric_id": key,
            "source": "fact_inscription",
            "value": cursos,
            "compartidos": compartidos,
            "cursos_totales": cursos + compartidos,
            "certificados": 0,
            "periodo_inicio": "2025-09-01",
            "periodo_fin": "2026-07-31",
        }
        for key, cursos, compartidos in _SLIDE_CATEGORIES
    ]
    manifest = SourceManifest(
        metric_id=MetricId("slide1_herramientas_pobreza"),
        source=MetricSource.FACT_INSCRIPTION,
        cut=Cut(date(2026, 7, 1)),
        fetched_at=datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc),
        freshness_hours=0.5,
        rows=rows,
        status=FetchStatus.EXTRACTED,
    )
    return Bundle(
        run_id=RunId.generate(),
        attempt_id=AttemptId.generate(),
        cut=Cut(date(2026, 7, 1)),
        catalog_hash="e" * 64,
        manifests=(manifest,),
        rows=(),
        dqs=(),
        hash=HashSha256("f" * 64),
    )


_SLIDE2_SECTORES: list[tuple[str, str, int]] = [
    ("Construcción y mantenimiento", "Albañilería básica", 1234),
    ("Construcción y mantenimiento", "Instalaciones eléctricas", 567),
    ("Limpieza y mantenimiento", "Limpieza industrial", 890),
]

_SLIDE3_PROGRAMS: dict[str, dict[str, int]] = {
    "slide3_capacitate_carso": {
        "2025": 45807,
        "sep2026": 23850,
        "base_dic2026": 176,
    },
    "slide3_academica_labs": {
        "2025": 0,
        "sep2026": 4347,
        "base_dic2026": 130,
    },
}

_SLIDE4_PROGRAMS: dict[str, dict[str, int]] = {
    "slide4_aprende_seguridad_vial": {
        "2024": 25254,
        "sep2025": 18578,
        "dic2025": 27129,
        "acumulado": 184288,
    },
    "slide4_cultura_salud_aprende": {
        "2024": 104736,
        "sep2025": 102916,
        "dic2025": 134327,
        "acumulado": 1413528,
    },
}


@pytest.fixture
def catalog_with_slide3() -> list[Metric]:
    """Catálogo de prueba con las dos métricas slide3 (nombres reales)."""
    return [
        Metric(
            id=MetricId("slide3_capacitate_carso"),
            name="Capacítate Carso — usuarios registrados por ventana fija (Slide 3)",
            key="slide3_capacitate_carso",
            source=MetricSource.DIM_USER,
            formula="...",
            db_mapping="ventana fija carso",
            platform_scope=[],
        ),
        Metric(
            id=MetricId("slide3_academica_labs"),
            name="Académica Labs — usuarios inscritos por ventana fija (Slide 3)",
            key="slide3_academica_labs",
            source=MetricSource.DIM_USER,
            formula="...",
            db_mapping="ventana fija academica",
            platform_scope=[],
        ),
    ]


@pytest.fixture
def bundle_with_slide1_slide2_slide3(
    bundle_with_both_slides: Bundle,
) -> Bundle:
    """Bundle con slide1 + slide2 + los DOS programas de slide3."""
    slide3_manifests = []
    for key, data in _SLIDE3_PROGRAMS.items():
        slide3_manifests.append(
            SourceManifest(
                metric_id=MetricId(key),
                source=MetricSource.DIM_USER,
                cut=Cut(date(2026, 7, 1)),
                fetched_at=datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc),
                freshness_hours=0.5,
                rows=(
                    {
                        "2025": data["2025"],
                        "sep2026": data["sep2026"],
                        "base_dic2026": data["base_dic2026"],
                    },
                ),
                status=FetchStatus.EXTRACTED,
            )
        )
    return Bundle(
        run_id=bundle_with_both_slides.run_id,
        attempt_id=bundle_with_both_slides.attempt_id,
        cut=bundle_with_both_slides.cut,
        catalog_hash="8" * 64,
        manifests=(
            *bundle_with_both_slides.manifests,
            *tuple(slide3_manifests),
        ),
        rows=(),
        dqs=(),
        hash=HashSha256("a" * 64),
    )


@pytest.fixture
def bundle_with_slide1_slide2_slide3_slide4(
    bundle_with_slide1_slide2_slide3: Bundle,
) -> Bundle:
    """Bundle con slide1 + slide2 + slide3 + los DOS programas de slide4."""
    slide4_manifests = []
    for key, data in _SLIDE4_PROGRAMS.items():
        slide4_manifests.append(
            SourceManifest(
                metric_id=MetricId(key),
                source=MetricSource.DIM_USER,
                cut=Cut(date(2026, 7, 1)),
                fetched_at=datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc),
                freshness_hours=0.5,
                rows=(
                    {
                        "2024": data["2024"],
                        "sep2025": data["sep2025"],
                        "dic2025": data["dic2025"],
                        "acumulado": data["acumulado"],
                    },
                ),
                status=FetchStatus.EXTRACTED,
            )
        )
    return Bundle(
        run_id=bundle_with_slide1_slide2_slide3.run_id,
        attempt_id=bundle_with_slide1_slide2_slide3.attempt_id,
        cut=bundle_with_slide1_slide2_slide3.cut,
        catalog_hash="8" * 64,
        manifests=(
            *bundle_with_slide1_slide2_slide3.manifests,
            *tuple(slide4_manifests),
        ),
        rows=(),
        dqs=(),
        hash=HashSha256("b" * 64),
    )


@pytest.fixture
def catalog_with_slide4() -> list[Metric]:
    """Catálogo de prueba con las dos métricas slide4 (nombres reales)."""
    return [
        Metric(
            id=MetricId("slide4_aprende_seguridad_vial"),
            name="Aprende de seguridad vial — certificados únicos por ventana fija (Slide 4)",
            key="slide4_aprende_seguridad_vial",
            source=MetricSource.FACT_INSCRIPTION,
            formula="...",
            db_mapping="ventana fija seguridad vial",
            platform_scope=[],
        ),
        Metric(
            id=MetricId("slide4_cultura_salud_aprende"),
            name="Cultura y Salud Aprende (registros) — usuarios sin inscripción por ventana fija (Slide 4)",
            key="slide4_cultura_salud_aprende",
            source=MetricSource.DIM_USER,
            formula="...",
            db_mapping="ventana fija cultura salud",
            platform_scope=[],
        ),
    ]


@pytest.fixture
def catalog_with_both_slides() -> list[Metric]:
    """Catálogo de prueba con slide1 y slide2 (nombres reales)."""
    return [
        Metric(
            id=MetricId("slide1_herramientas_pobreza"),
            name="Herramientas de capacitación combate pobreza extrema (Slide 1)",
            key="slide1_herramientas_pobreza",
            source=MetricSource.FACT_INSCRIPTION,
            formula="...",
            db_mapping="fact_inscription",
            platform_scope=["CPE", "Aprende"],
        ),
        Metric(
            id=MetricId("slide2_empleo_incluyente_por_sector"),
            name="Certificados por sector — empleo incluyente (Slide 2)",
            key="slide2_empleo_incluyente_por_sector",
            source=MetricSource.FACT_INSCRIPTION,
            formula="...",
            db_mapping="fact_inscription",
            platform_scope=["CPE", "Aprende"],
        ),
    ]


@pytest.fixture
def bundle_with_both_slides() -> Bundle:
    """Bundle con manifest slide1 (5 categorías) y slide2 (sectores)."""
    slide1_rows = [
        {
            "metric_id": key,
            "source": "fact_inscription",
            "value": cursos,
            "compartidos": compartidos,
            "cursos_totales": cursos + compartidos,
            "certificados": 0,
            "periodo_inicio": "2025-09-01",
            "periodo_fin": "2026-07-31",
        }
        for key, cursos, compartidos in _SLIDE_CATEGORIES
    ]
    slide1_manifest = SourceManifest(
        metric_id=MetricId("slide1_herramientas_pobreza"),
        source=MetricSource.FACT_INSCRIPTION,
        cut=Cut(date(2026, 7, 1)),
        fetched_at=datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc),
        freshness_hours=0.5,
        rows=slide1_rows,
        status=FetchStatus.EXTRACTED,
    )
    slide2_rows = [
        {"grupo": grupo, "curso": curso, "value": value}
        for grupo, curso, value in _SLIDE2_SECTORES
    ]
    slide2_manifest = SourceManifest(
        metric_id=MetricId("slide2_empleo_incluyente_por_sector"),
        source=MetricSource.FACT_INSCRIPTION,
        cut=Cut(date(2026, 7, 1)),
        fetched_at=datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc),
        freshness_hours=0.5,
        rows=slide2_rows,
        status=FetchStatus.EXTRACTED,
    )
    return Bundle(
        run_id=RunId.generate(),
        attempt_id=AttemptId.generate(),
        cut=Cut(date(2026, 7, 1)),
        catalog_hash="8" * 64,
        manifests=(slide1_manifest, slide2_manifest),
        rows=(),
        dqs=(),
        hash=HashSha256("9" * 64),
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
                {"properties": {"title": name, "sheetId": 10 + index}}
                for index, name in enumerate(existing_sheets)
            ]
        }
    }


def _add_sheet_response(arguments: dict) -> dict:
    replies = []
    for index, request in enumerate(arguments.get("requests", [])):
        properties = request.get("addSheet", {}).get("properties")
        if properties:
            replies.append({
                "addSheet": {
                    "properties": {
                        "title": properties["title"],
                        "sheetId": 100 + index,
                    }
                }
            })
    return {"replies": replies}


class TestGoogleMcpSheetRepo:
    """Verifica el comportamiento del adapter de Sheets con proxy falso."""

    def test_snapshot_creates_five_sheets(
        self, sample_bundle: Bundle, sample_catalog: list[Metric]
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
                    return _add_sheet_response(arguments)
                elif name == "get_spreadsheet":
                    return _build_spreadsheet_meta([])
                return {}

            mock_call.side_effect = capture_and_return

            result = repo.snapshot(sample_bundle, "test-spreadsheet-id", sample_catalog)
            assert result == "test-spreadsheet-id"

        assert len(captured_requests) >= 1
        all_requests = captured_requests[0].get("requests", [])
        created_sheets = [
            r["addSheet"]["properties"]["title"]
            for r in all_requests
            if "addSheet" in r
        ]
        assert set(created_sheets) == set(SHEET_NAMES)

    def test_snapshot_uses_sheet_ids_returned_by_add_sheet(
        self, sample_bundle: Bundle, sample_catalog: list[Metric]
    ) -> None:
        """Los updates deben usar los IDs asignados por Google."""
        captured_requests: list[dict] = []
        metadata = _build_spreadsheet_meta(["Hoja 1"])
        metadata["fields"]["sheets"][0]["properties"]["sheetId"] = 0
        assigned_ids = {
            "Control": 17,
            "Datos": 29,
            "Reporte": 43,
            "Errores": 61,
            "Configuracion": 89,
        }

        with patch.object(
            GoogleMcpSheetRepo, "_start_proxy"
        ), patch.object(
            GoogleMcpSheetRepo, "_init_handshake"
        ), patch.object(
            GoogleMcpSheetRepo, "_get_spreadsheet_meta",
            return_value=metadata,
        ), patch.object(
            GoogleMcpSheetRepo, "_call_tool",
        ) as mock_call:
            def capture(name: str, arguments: dict) -> dict:
                if name == "update_sheet":
                    captured_requests.append(arguments)
                    if len(captured_requests) == 1:
                        return {
                            "replies": [
                                {"addSheet": {"properties": {"title": title, "sheetId": sheet_id}}}
                                for title, sheet_id in assigned_ids.items()
                            ]
                        }
                return {}

            mock_call.side_effect = capture

            repo = GoogleMcpSheetRepo()
            repo.snapshot(sample_bundle, "test-id", sample_catalog)

        assert len(captured_requests) == 2
        update_requests = captured_requests[1]["requests"]
        update_ids = {
            request["updateCells"]["start"]["sheetId"]
            for request in update_requests
            if "updateCells" in request
        }
        assert update_ids == set(assigned_ids.values())

    def test_snapshot_fresh_sheet_uses_two_valid_batches(
        self, sample_bundle: Bundle, sample_catalog: list[Metric]
    ) -> None:
        """Una spreadsheet fresca debe crear y poblar en batches separados."""
        captured_requests: list[dict] = []

        with patch.object(
            GoogleMcpSheetRepo, "_start_proxy"
        ), patch.object(
            GoogleMcpSheetRepo, "_init_handshake"
        ), patch.object(
            GoogleMcpSheetRepo, "_get_spreadsheet_meta",
            return_value=_build_spreadsheet_meta(["Hoja 1"]),
        ), patch.object(
            GoogleMcpSheetRepo, "_call_tool",
        ) as mock_call:
            assigned_ids = {
                title: 100 + index
                for index, title in enumerate(SHEET_NAMES)
            }

            def capture(name: str, arguments: dict) -> dict:
                if name == "update_sheet":
                    captured_requests.append(arguments)
                    if len(captured_requests) == 1:
                        return {
                            "replies": [
                                {"addSheet": {"properties": {"title": title, "sheetId": sheet_id}}}
                                 for title, sheet_id in assigned_ids.items()
                            ]
                        }
                return {}

            mock_call.side_effect = capture

            GoogleMcpSheetRepo().snapshot(sample_bundle, "test-id", sample_catalog)

        assert len(captured_requests) == 2
        assert all("addSheet" in request for request in captured_requests[0]["requests"])
        assert all("addSheet" not in request for request in captured_requests[1]["requests"])

    def test_snapshot_with_existing_sheets_partial(
        self, sample_bundle: Bundle, sample_catalog: list[Metric]
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
                return _add_sheet_response(arguments)

            mock_call.side_effect = capture

            repo = GoogleMcpSheetRepo()
            repo.snapshot(sample_bundle, "test-id", sample_catalog)

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
        self, sample_bundle: Bundle, sample_catalog: list[Metric]
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
                return _add_sheet_response(args)

            mock_call.side_effect = cap

            repo = GoogleMcpSheetRepo()
            repo.snapshot(sample_bundle, "test-id", sample_catalog)

        all_reqs = captured[-1].get("requests", [])
        # Buscar el updateCells para Control.
        control_updates = [
            r for r in all_reqs
            if r.get("updateCells", {}).get("start", {}).get("sheetId") == 100
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
        self, bundle_with_dqs_issues: Bundle, sample_catalog: list[Metric]
    ) -> None:
        """Sin manifest de slide, Datos queda con solo la fila de headers."""
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
                return _add_sheet_response(args)

            mock_call.side_effect = cap

            repo = GoogleMcpSheetRepo()
            repo.snapshot(bundle_with_dqs_issues, "test-id", sample_catalog)

        all_reqs = captured[-1].get("requests", [])
        datos_updates = [
            r for r in all_reqs
            if r.get("updateCells", {}).get("start", {}).get("sheetId") == 101
        ]
        assert len(datos_updates) >= 1
        datos_rows = datos_updates[0]["updateCells"]["rows"]
        # sin slides: solo la fila de headers
        assert len(datos_rows) == 1

    def test_snapshot_populates_datos_sheet_with_slide_tables(
        self, bundle_with_slide1: Bundle, sample_catalog: list[Metric]
    ) -> None:
        """Datos debe tener headers de 8 columnas + 5 categorías + TOTAL con =SUM."""
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
                return _add_sheet_response(args)

            mock_call.side_effect = cap

            repo = GoogleMcpSheetRepo()
            repo.snapshot(bundle_with_slide1, "test-id", sample_catalog)

        all_reqs = captured[-1].get("requests", [])
        datos_updates = [
            r for r in all_reqs
            if r.get("updateCells", {}).get("start", {}).get("sheetId") == 101
        ]
        assert len(datos_updates) >= 1
        datos_rows = datos_updates[0]["updateCells"]["rows"]
        # header + 5 categorías + TOTAL = 7 rows
        assert len(datos_rows) == 7

        header = datos_rows[0]["values"]
        assert len(header) == 8
        header_texts = [
            c["userEnteredValue"]["stringValue"] for c in header
        ]
        assert header_texts == [
            "Categoría", "Cursos únicos", "Compartidos", "Cursos totales",
            "Certificados", "Período inicio", "Período fin", "Fuente",
        ]

        first = datos_rows[1]["values"]
        assert first[0]["userEnteredValue"]["stringValue"] == "slide1_vivienda"
        assert first[1]["userEnteredValue"]["numberValue"] == 16

        total = datos_rows[6]["values"]
        assert total[0]["userEnteredValue"]["stringValue"] == "TOTAL"
        assert total[1]["userEnteredValue"]["formulaValue"] == "=SUM(B2:B6)"
        assert total[2]["userEnteredValue"]["formulaValue"] == "=SUM(C2:C6)"
        assert total[3]["userEnteredValue"]["formulaValue"] == "=SUM(D2:D6)"
        assert total[4]["userEnteredValue"]["formulaValue"] == "=SUM(E2:E6)"

    def test_snapshot_datos_includes_slide2_with_own_structure(
        self, bundle_with_both_slides: Bundle,
        catalog_with_both_slides: list[Metric],
    ) -> None:
        """Datos debe contener DOS tablas contiguas separadas por blank:
        slide1 (8 cols) y slide2 (7 cols Categoría/Sector/Curso/
        Certificados/Período inicio/Período fin/Fuente) con TOTAL
        =SUM(Dfirst:last) en Certificados.
        """
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
                return _add_sheet_response(args)

            mock_call.side_effect = cap

            repo = GoogleMcpSheetRepo()
            repo.snapshot(bundle_with_both_slides, "test-id", catalog_with_both_slides)

        all_reqs = captured[-1].get("requests", [])
        datos_updates = [
            r for r in all_reqs
            if r.get("updateCells", {}).get("start", {}).get("sheetId") == 101
        ]
        assert len(datos_updates) >= 1
        datos_rows = datos_updates[0]["updateCells"]["rows"]

        # slide1 (header + 5 data + TOTAL = 7) + blank (1) + slide2
        # (header + 3 data + TOTAL = 5) = 13
        assert len(datos_rows) == 13

        # ── Slide 1 (índice 0..6) ──
        slide1_header = datos_rows[0]["values"]
        assert len(slide1_header) == 8
        assert [c["userEnteredValue"]["stringValue"] for c in slide1_header] == [
            "Categoría", "Cursos únicos", "Compartidos", "Cursos totales",
            "Certificados", "Período inicio", "Período fin", "Fuente",
        ]
        slide1_total = datos_rows[6]["values"]
        assert slide1_total[0]["userEnteredValue"]["stringValue"] == "TOTAL"
        assert slide1_total[1]["userEnteredValue"]["formulaValue"] == "=SUM(B2:B6)"
        assert slide1_total[2]["userEnteredValue"]["formulaValue"] == "=SUM(C2:C6)"
        assert slide1_total[3]["userEnteredValue"]["formulaValue"] == "=SUM(D2:D6)"
        assert slide1_total[4]["userEnteredValue"]["formulaValue"] == "=SUM(E2:E6)"

        # ── Blank row (índice 7) ──
        blank = datos_rows[7]["values"]
        for cell in blank:
            assert cell == {"userEnteredValue": {}}, (
                f"Blank row debe tener celdas vacías, got {cell}"
            )

        # ── Slide 2 (índice 8..12) ──
        slide2_header = datos_rows[8]["values"]
        assert len(slide2_header) == 7
        assert [c["userEnteredValue"]["stringValue"] for c in slide2_header] == [
            "Categoría", "Sector", "Curso", "Certificados",
            "Período inicio", "Período fin", "Fuente",
        ]

        slide2_first = datos_rows[9]["values"]
        assert len(slide2_first) == 7
        # col A: Categoría con nomenclatura slide2_<sector>
        assert (
            slide2_first[0]["userEnteredValue"]["stringValue"]
            == "slide2_construccion_y_mantenimiento"
        )
        # col B: Sector ← grupo
        assert (
            slide2_first[1]["userEnteredValue"]["stringValue"]
            == "Construcción y mantenimiento"
        )
        # col C: Curso
        assert slide2_first[2]["userEnteredValue"]["stringValue"] == "Albañilería básica"
        # col D: Certificados ← value
        assert slide2_first[3]["userEnteredValue"]["numberValue"] == 1234
        # Período inicio / Período fin / Fuente vacías en datos (mock no las tiene)
        for c in slide2_first[4:7]:
            assert c == {"userEnteredValue": {}}

        slide2_total = datos_rows[12]["values"]
        assert len(slide2_total) == 7
        assert slide2_total[0]["userEnteredValue"]["stringValue"] == "TOTAL"
        # col B vacía (Sector)
        assert slide2_total[1] == {"userEnteredValue": {}}
        # col C vacía (Curso)
        assert slide2_total[2] == {"userEnteredValue": {}}
        # col D con =SUM(D10:D12) (header 1-based 9, data 10-12)
        assert slide2_total[3]["userEnteredValue"]["formulaValue"] == "=SUM(D10:D12)"
        # Período inicio / Período fin / Fuente vacías en TOTAL
        for c in slide2_total[4:7]:
            assert c == {"userEnteredValue": {}}

        # Reporte/Configuracion deben incluir el nombre real de slide2.
        reporte_update = next(
            r for r in all_reqs
            if r.get("updateCells", {}).get("start", {}).get("sheetId") == 102
        )
        reporte_rows = reporte_update["updateCells"]["rows"]
        # header + slide1 + slide2
        assert len(reporte_rows) == 3
        assert (
            reporte_rows[2]["values"][0]["userEnteredValue"]["stringValue"]
            == "Certificados por sector — empleo incluyente (Slide 2)"
        )

        config_update = next(
            r for r in all_reqs
            if r.get("updateCells", {}).get("start", {}).get("sheetId") == 104
        )
        config_rows = config_update["updateCells"]["rows"]
        assert len(config_rows) == 3
        assert (
            config_rows[2]["values"][0]["userEnteredValue"]["stringValue"]
            == "slide2_empleo_incluyente_por_sector"
        )
        assert (
            config_rows[2]["values"][1]["userEnteredValue"]["stringValue"]
            == "Certificados por sector — empleo incluyente (Slide 2)"
        )

    def test_snapshot_datos_includes_slide3_comparative_table(
        self,
        bundle_with_slide1_slide2_slide3: Bundle,
        catalog_with_both_slides: list[Metric],
    ) -> None:
        """Datos debe contener UNA tabla comparativa slide3 agrupando los
        dos programas: header de 9 cols, fila fija 'Capacitate Empleo'
        (categoría slide3_* y fuente manual), y una fila por programa
        (Carso y Academica Labs) con su Categoría slide3_*, valores de
        2025/sep2026, dic2026 proyectado linealmente, períodos fijos
        2025-01-01..2026-08-02 y fuente mysql. Acumulado queda vacío y
        NO hay fila TOTAL.
        """
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
                return _add_sheet_response(args)

            mock_call.side_effect = cap

            repo = GoogleMcpSheetRepo()
            repo.snapshot(
                bundle_with_slide1_slide2_slide3,
                "test-id",
                catalog_with_both_slides,
            )

        all_reqs = captured[-1].get("requests", [])
        datos_updates = [
            r for r in all_reqs
            if r.get("updateCells", {}).get("start", {}).get("sheetId") == 101
        ]
        assert len(datos_updates) >= 1
        datos_rows = datos_updates[0]["updateCells"]["rows"]

        # slide1 (7) + blank (1) + slide2 (5) + blank (1) + slide3 (4) = 18
        assert len(datos_rows) == 18

        # ── Slide 3 (índice 14..17) ──
        slide3_header = datos_rows[14]["values"]
        assert len(slide3_header) == 9
        assert [
            c["userEnteredValue"]["stringValue"] for c in slide3_header
        ] == list(SLIDE3_TABLE_HEADERS)

        cap_empleo = datos_rows[15]["values"]
        assert len(cap_empleo) == 9
        assert (
            cap_empleo[0]["userEnteredValue"]["stringValue"]
            == "slide3_capacitate_empleo"
        )
        assert (
            cap_empleo[1]["userEnteredValue"]["stringValue"]
            == "Capacitate Empleo"
        )
        for c in cap_empleo[2:8]:
            assert c == {"userEnteredValue": {}}
        assert (
            cap_empleo[8]["userEnteredValue"]["stringValue"] == "manual"
        )

        carso = datos_rows[16]["values"]
        assert len(carso) == 9
        assert (
            carso[0]["userEnteredValue"]["stringValue"]
            == "slide3_capacitate_carso"
        )
        assert (
            carso[1]["userEnteredValue"]["stringValue"] == "Capacitate Carso"
        )
        assert carso[2]["userEnteredValue"]["numberValue"] == 45807
        assert carso[3]["userEnteredValue"]["numberValue"] == 23850
        # dic2026 = round(23850 * 12/7) = 40886 (proyección lineal)
        assert carso[4]["userEnteredValue"]["numberValue"] == 40886
        assert carso[5] == {"userEnteredValue": {}}
        assert (
            carso[6]["userEnteredValue"]["stringValue"] == "2025-01-01"
        )
        assert (
            carso[7]["userEnteredValue"]["stringValue"] == "2026-08-02"
        )
        assert carso[8]["userEnteredValue"]["stringValue"] == "mysql"

        academica = datos_rows[17]["values"]
        assert len(academica) == 9
        assert (
            academica[0]["userEnteredValue"]["stringValue"]
            == "slide3_academica_labs"
        )
        assert (
            academica[1]["userEnteredValue"]["stringValue"]
            == "Academica Labs"
        )
        assert academica[2]["userEnteredValue"]["numberValue"] == 0
        assert academica[3]["userEnteredValue"]["numberValue"] == 4347
        # dic2026 = round(4347 * 12/7) = 7452 (proyección lineal)
        assert academica[4]["userEnteredValue"]["numberValue"] == 7452
        assert academica[5] == {"userEnteredValue": {}}
        assert (
            academica[6]["userEnteredValue"]["stringValue"] == "2025-01-01"
        )
        assert (
            academica[7]["userEnteredValue"]["stringValue"] == "2026-08-02"
        )
        assert academica[8]["userEnteredValue"]["stringValue"] == "mysql"

        # Sin fila TOTAL: el bloque termina en la fila Academica Labs.
        assert len(datos_rows) == 18

    def test_build_slide_block_does_not_raise_for_slide3(self) -> None:
        """_build_slide_block NO debe lanzar ValueError para keys slide3_*."""
        manifest = SourceManifest(
            metric_id=MetricId("slide3_capacitate_carso"),
            source=MetricSource.DIM_USER,
            cut=Cut(date(2026, 7, 1)),
            fetched_at=datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc),
            freshness_hours=0.5,
            rows=({"2025": 100, "sep2026": 50, "base_dic2026": 7},),
            status=FetchStatus.EXTRACTED,
        )

        rows, next_row = _build_slide_block(manifest, 0)

        assert next_row == 3
        assert len(rows) == 3
        assert (
            rows[0]["values"][0]["userEnteredValue"]["stringValue"]
            == "Categoría"
        )
        assert (
            rows[1]["values"][0]["userEnteredValue"]["stringValue"]
            == "slide3_capacitate_empleo"
        )
        assert (
            rows[1]["values"][1]["userEnteredValue"]["stringValue"]
            == "Capacitate Empleo"
        )
        assert (
            rows[1]["values"][8]["userEnteredValue"]["stringValue"]
            == "manual"
        )
        assert (
            rows[2]["values"][0]["userEnteredValue"]["stringValue"]
            == "slide3_capacitate_carso"
        )
        assert (
            rows[2]["values"][1]["userEnteredValue"]["stringValue"]
            == "Capacitate Carso"
        )
        assert rows[2]["values"][2]["userEnteredValue"]["numberValue"] == 100
        assert rows[2]["values"][3]["userEnteredValue"]["numberValue"] == 50
        # dic2026 = round(50 * 12/7) = 86 (proyección lineal sobre sep2026)
        assert rows[2]["values"][4]["userEnteredValue"]["numberValue"] == 86
        assert rows[2]["values"][5] == {"userEnteredValue": {}}
        assert (
            rows[2]["values"][6]["userEnteredValue"]["stringValue"]
            == "2025-01-01"
        )
        assert (
            rows[2]["values"][7]["userEnteredValue"]["stringValue"]
            == "2026-08-02"
        )
        assert (
            rows[2]["values"][8]["userEnteredValue"]["stringValue"]
            == "mysql"
        )

    def test_project_dic2026_linear_projection(self) -> None:
        """La proyección dic2026 es el total anual a ritmo constante.

        dic2026 = sep2026 * (1 + 5/7): los valores reales conocidos de
        Carso (23849) y Académica (4347) deben producir 40884 y 7452.
        """
        assert _project_dic2026(23849) == 40884  # round(23849 * 12/7)
        assert _project_dic2026(4347) == 7452  # round(4347 * 12/7)
        assert _project_dic2026(23850) == 40886  # round(23850 * 12/7)
        assert _project_dic2026(50) == 86  # round(50 * 12/7)
        assert _project_dic2026(0) == 0

    def test_build_slide3_block_keeps_capacitate_empleo_manual(self) -> None:
        """La fila Capacitate Empleo sigue sin proyección (dic2026 vacío)."""
        carso = SourceManifest(
            metric_id=MetricId("slide3_capacitate_carso"),
            source=MetricSource.DIM_USER,
            cut=Cut(date(2026, 7, 1)),
            fetched_at=datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc),
            freshness_hours=0.5,
            rows=({"2025": 45807, "sep2026": 23849, "base_dic2026": 176},),
            status=FetchStatus.EXTRACTED,
        )

        rows, next_row = _build_slide3_block([carso], 0)

        assert next_row == 3
        assert len(rows) == 3
        # Capacitate Empleo: dic2026 (col 4) y Acumulado (col 5) vacíos.
        assert rows[1]["values"][4] == {"userEnteredValue": {}}
        assert rows[1]["values"][5] == {"userEnteredValue": {}}
        # Carso: dic2026 proyectado = 40884, Acumulado vacío.
        assert rows[2]["values"][4]["userEnteredValue"]["numberValue"] == 40884
        assert rows[2]["values"][5] == {"userEnteredValue": {}}

    def test_snapshot_datos_includes_slide4_comparative_table(
        self,
        bundle_with_slide1_slide2_slide3_slide4: Bundle,
        catalog_with_both_slides: list[Metric],
    ) -> None:
        """Datos debe contener UNA tabla comparativa slide4 agrupando los
        dos programas: header de 9 cols, fila fija 'Pilotos por la
        Seguridad Vial' (categoría slide4_* y fuente manual), y una fila
        por programa (seguridad vial y cultura/salud) con su Categoría
        slide4_*, valores de 2024/sep2025/dic2025/acumulado, períodos
        fijos 2024-01-01..2025-09-30 y fuente postgres. NO hay fila TOTAL.
        """
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
                return _add_sheet_response(args)

            mock_call.side_effect = cap

            repo = GoogleMcpSheetRepo()
            repo.snapshot(
                bundle_with_slide1_slide2_slide3_slide4,
                "test-id",
                catalog_with_both_slides,
            )

        all_reqs = captured[-1].get("requests", [])
        datos_updates = [
            r for r in all_reqs
            if r.get("updateCells", {}).get("start", {}).get("sheetId") == 101
        ]
        assert len(datos_updates) >= 1
        datos_rows = datos_updates[0]["updateCells"]["rows"]

        # slide1 (7) + blank (1) + slide2 (5) + blank (1) + slide3 (4)
        # + blank (1) + slide4 (4) = 23
        assert len(datos_rows) == 23

        # ── Slide 4 (índice 19..22) ──
        slide4_header = datos_rows[19]["values"]
        assert len(slide4_header) == 9
        assert [
            c["userEnteredValue"]["stringValue"] for c in slide4_header
        ] == list(SLIDE4_TABLE_HEADERS)

        pilotos = datos_rows[20]["values"]
        assert len(pilotos) == 9
        assert (
            pilotos[0]["userEnteredValue"]["stringValue"]
            == "slide4_pilotos_seguridad_vial"
        )
        assert (
            pilotos[1]["userEnteredValue"]["stringValue"]
            == "Pilotos por la Seguridad Vial"
        )
        for c in pilotos[2:8]:
            assert c == {"userEnteredValue": {}}
        assert (
            pilotos[8]["userEnteredValue"]["stringValue"] == "manual"
        )

        seguridad = datos_rows[21]["values"]
        assert len(seguridad) == 9
        assert (
            seguridad[0]["userEnteredValue"]["stringValue"]
            == "slide4_aprende_seguridad_vial"
        )
        assert (
            seguridad[1]["userEnteredValue"]["stringValue"]
            == "Aprende de seguridad vial"
        )
        assert seguridad[2]["userEnteredValue"]["numberValue"] == 25254
        assert seguridad[3]["userEnteredValue"]["numberValue"] == 18578
        assert seguridad[4]["userEnteredValue"]["numberValue"] == 27129
        assert seguridad[5]["userEnteredValue"]["numberValue"] == 184288
        assert (
            seguridad[6]["userEnteredValue"]["stringValue"] == "2024-01-01"
        )
        assert (
            seguridad[7]["userEnteredValue"]["stringValue"] == "2025-09-30"
        )
        assert seguridad[8]["userEnteredValue"]["stringValue"] == "postgres"

        cultura = datos_rows[22]["values"]
        assert len(cultura) == 9
        assert (
            cultura[0]["userEnteredValue"]["stringValue"]
            == "slide4_cultura_salud_aprende"
        )
        assert (
            cultura[1]["userEnteredValue"]["stringValue"]
            == "Cultura y Salud Aprende (registros)"
        )
        assert cultura[2]["userEnteredValue"]["numberValue"] == 104736
        assert cultura[3]["userEnteredValue"]["numberValue"] == 102916
        assert cultura[4]["userEnteredValue"]["numberValue"] == 134327
        assert cultura[5]["userEnteredValue"]["numberValue"] == 1413528
        assert (
            cultura[6]["userEnteredValue"]["stringValue"] == "2024-01-01"
        )
        assert (
            cultura[7]["userEnteredValue"]["stringValue"] == "2025-09-30"
        )
        assert cultura[8]["userEnteredValue"]["stringValue"] == "postgres"

        # Sin fila TOTAL: el bloque termina en la fila Cultura y Salud.
        assert len(datos_rows) == 23

    def test_build_slide_block_does_not_raise_for_slide4(self) -> None:
        """_build_slide_block NO debe lanzar ValueError para keys slide4_*."""
        manifest = SourceManifest(
            metric_id=MetricId("slide4_aprende_seguridad_vial"),
            source=MetricSource.FACT_INSCRIPTION,
            cut=Cut(date(2026, 7, 1)),
            fetched_at=datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc),
            freshness_hours=0.5,
            rows=({"2024": 100, "sep2025": 50, "dic2025": 70, "acumulado": 999},),
            status=FetchStatus.EXTRACTED,
        )

        rows, next_row = _build_slide_block(manifest, 0)

        assert next_row == 3
        assert len(rows) == 3
        assert (
            rows[0]["values"][0]["userEnteredValue"]["stringValue"]
            == "Categoría"
        )
        assert (
            rows[1]["values"][0]["userEnteredValue"]["stringValue"]
            == "slide4_pilotos_seguridad_vial"
        )
        assert (
            rows[1]["values"][1]["userEnteredValue"]["stringValue"]
            == "Pilotos por la Seguridad Vial"
        )
        assert (
            rows[1]["values"][8]["userEnteredValue"]["stringValue"]
            == "manual"
        )
        assert (
            rows[2]["values"][0]["userEnteredValue"]["stringValue"]
            == "slide4_aprende_seguridad_vial"
        )
        assert (
            rows[2]["values"][1]["userEnteredValue"]["stringValue"]
            == "Aprende de seguridad vial"
        )
        assert rows[2]["values"][2]["userEnteredValue"]["numberValue"] == 100
        assert rows[2]["values"][3]["userEnteredValue"]["numberValue"] == 50
        assert rows[2]["values"][4]["userEnteredValue"]["numberValue"] == 70
        assert rows[2]["values"][5]["userEnteredValue"]["numberValue"] == 999
        assert (
            rows[2]["values"][6]["userEnteredValue"]["stringValue"]
            == "2024-01-01"
        )
        assert (
            rows[2]["values"][7]["userEnteredValue"]["stringValue"]
            == "2025-09-30"
        )
        assert (
            rows[2]["values"][8]["userEnteredValue"]["stringValue"]
            == "postgres"
        )

    def test_build_slide4_block_keeps_pilotos_manual(self) -> None:
        """La fila Pilotos queda toda manual (valores y acumulado vacíos)."""
        seguridad = SourceManifest(
            metric_id=MetricId("slide4_aprende_seguridad_vial"),
            source=MetricSource.FACT_INSCRIPTION,
            cut=Cut(date(2026, 7, 1)),
            fetched_at=datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc),
            freshness_hours=0.5,
            rows=({"2024": 25254, "sep2025": 18578, "dic2025": 27129, "acumulado": 184288},),
            status=FetchStatus.EXTRACTED,
        )

        rows, next_row = _build_slide4_block([seguridad], 0)

        assert next_row == 3
        assert len(rows) == 3
        # Pilotos: todas las celdas de valor (cols 2..7) vacías.
        for col in range(2, 8):
            assert rows[1]["values"][col] == {"userEnteredValue": {}}
        assert rows[1]["values"][8]["userEnteredValue"]["stringValue"] == "manual"
        # Seguridad vial: todos los valores reales presentes.
        assert rows[2]["values"][2]["userEnteredValue"]["numberValue"] == 25254
        assert rows[2]["values"][3]["userEnteredValue"]["numberValue"] == 18578
        assert rows[2]["values"][4]["userEnteredValue"]["numberValue"] == 27129
        assert rows[2]["values"][5]["userEnteredValue"]["numberValue"] == 184288

    def test_snapshot_populates_errores_sheet(
        self, bundle_with_dqs_issues: Bundle, sample_catalog: list[Metric]
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
                return _add_sheet_response(args)

            mock_call.side_effect = cap

            repo = GoogleMcpSheetRepo()
            repo.snapshot(bundle_with_dqs_issues, "test-id", sample_catalog)

        all_reqs = captured[-1].get("requests", [])
        errores_updates = [
            r for r in all_reqs
            if r.get("updateCells", {}).get("start", {}).get("sheetId") == 103
        ]
        assert len(errores_updates) >= 1
        errores_rows = errores_updates[0]["updateCells"]["rows"]
        assert len(errores_rows) == 2  # header + 1 issue

    def test_snapshot_report_config_use_catalog_metadata(
        self, sample_catalog: list[Metric]
    ) -> None:
        """Reporte y Configuracion contienen solo métricas de slide y usan
        name y platform_scope del catálogo cuando hay match."""
        known = SourceManifest(
            metric_id=MetricId("slide1_herramientas_pobreza"),
            source=MetricSource.FACT_INSCRIPTION,
            cut=Cut(date(2026, 7, 1)),
            fetched_at=datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc),
            freshness_hours=1.0,
            rows=(
                {
                    "metric_id": "slide1_herramientas_pobreza",
                    "source": "fact_inscription",
                    "value": 22,
                },
            ),
            status=FetchStatus.EXTRACTED,
        )
        unknown = SourceManifest(
            metric_id=MetricId("slide2_empleo_incluyente"),
            source=MetricSource.FACT_INSCRIPTION,
            cut=Cut(date(2026, 7, 1)),
            fetched_at=datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc),
            freshness_hours=1.0,
            rows=(),
            status=FetchStatus.EMPTY,
        )
        # Métrica no-slide: no debe aparecer en Reporte ni Configuracion.
        non_slide = SourceManifest(
            metric_id=MetricId("registered_cpe"),
            source=MetricSource.DIM_USER,
            cut=Cut(date(2026, 7, 1)),
            fetched_at=datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc),
            freshness_hours=1.0,
            rows=({"metric_id": "registered_cpe", "source": "dim_user", "value": 1500},),
            status=FetchStatus.EXTRACTED,
        )
        bundle = Bundle(
            run_id=RunId.generate(),
            attempt_id=AttemptId.generate(),
            cut=Cut(date(2026, 7, 1)),
            catalog_hash="g" * 64,
            manifests=(known, unknown, non_slide),
            rows=(),
            dqs=(),
            hash=HashSha256("1" * 64),
        )

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
                return _add_sheet_response(args)

            mock_call.side_effect = cap

            repo = GoogleMcpSheetRepo()
            repo.snapshot(bundle, "test-id", sample_catalog)

        all_reqs = captured[-1].get("requests", [])
        reporte_update = next(
            r for r in all_reqs
            if r.get("updateCells", {}).get("start", {}).get("sheetId") == 102
        )
        reporte_rows = reporte_update["updateCells"]["rows"]
        # header + known (slide) + unknown (slide). Métrica no-slide excluida.
        assert len(reporte_rows) == 3
        assert (
            reporte_rows[1]["values"][0]["userEnteredValue"]["stringValue"]
            == "Herramientas de capacitación combate pobreza extrema (Slide 1)"
        )
        assert reporte_rows[1]["values"][1]["userEnteredValue"]["stringValue"] == "22"
        # Sin match en catálogo: fallback al metric_id.
        assert (
            reporte_rows[2]["values"][0]["userEnteredValue"]["stringValue"]
            == "slide2_empleo_incluyente"
        )

        config_update = next(
            r for r in all_reqs
            if r.get("updateCells", {}).get("start", {}).get("sheetId") == 104
        )
        config_rows = config_update["updateCells"]["rows"]
        assert len(config_rows) == 3
        # col2 = Nombre real del catálogo, col4 = plataformas unidas.
        assert (
            config_rows[1]["values"][1]["userEnteredValue"]["stringValue"]
            == "Herramientas de capacitación combate pobreza extrema (Slide 1)"
        )
        assert config_rows[1]["values"][3]["userEnteredValue"]["stringValue"] == "CPE, Aprende"
        # Sin match: Nombre = metric_id y Plataformas vacío.
        assert (
            config_rows[2]["values"][1]["userEnteredValue"]["stringValue"]
            == "slide2_empleo_incluyente"
        )
        assert config_rows[2]["values"][3]["userEnteredValue"]["stringValue"] == ""

    def test_snapshot_does_not_call_slides(
        self, sample_bundle: Bundle, sample_catalog: list[Metric]
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
            mock_call.side_effect = lambda name, args: (
                _add_sheet_response(args)
                if name == "update_sheet"
                else {}
            )

            repo = GoogleMcpSheetRepo()
            repo.snapshot(sample_bundle, "test-id", sample_catalog)

        # Verificar que todas las llamadas fueron a get_spreadsheet o update_sheet
        for call_args in mock_call.call_args_list:
            tool_name = call_args[0][0] if call_args[0] else ""
            assert tool_name in (
                "get_spreadsheet",
                "update_sheet",
            ), f"No se debe llamar a {tool_name}"

    def test_snapshot_handles_proxy_error(
        self, sample_bundle: Bundle, sample_catalog: list[Metric]
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
                repo.snapshot(sample_bundle, "test-id", sample_catalog)
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

    def test_proxy_waits_for_initialize_request(self) -> None:
        """The proxy must not emit an unsolicited JSON-RPC response."""
        process = subprocess.Popen(
            [sys.executable, "mcp/google_mcp_proxy.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            assert process.stdin is not None
            assert process.stdout is not None
            process.stdin.write(
                '{"jsonrpc":"2.0","id":41,"method":"initialize"}\n'
            )
            process.stdin.flush()
            response = json.loads(process.stdout.readline())
        finally:
            process.terminate()
            process.wait(timeout=5)

        assert response["id"] == 41
        assert response["result"]["protocolVersion"] == "2024-11-05"
