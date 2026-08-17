"""Adaptador de Google Sheets vía proxy MCP por stdio.

Comunica con mcp/google_mcp_proxy.py mediante JSON-RPC por stdin/stdout.
Usa shell=False y argv fijo. Solo expone get_spreadsheet + update_sheet.
Cero llamadas a Slides. Errores sanitizados sin secretos.
"""

from __future__ import annotations

import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

from src.consejo.application.ports import SheetRepo
from src.consejo.domain.entities import Bundle, DqsIssue, Metric, SourceManifest

# ── Constantes ──────────────────────────────────────────────────────────────

PROXY_PATH = str(
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "mcp"
    / "google_mcp_proxy.py"
)

SHEET_NAMES = ["Control", "Datos", "Reporte", "Errores", "Configuracion"]


# ── Excepciones sanitizadas ─────────────────────────────────────────────────


class SheetProxyError(Exception):
    """Error de comunicación con el proxy MCP. Mensaje sanitizado."""


# ── Repositorio ─────────────────────────────────────────────────────────────


class GoogleMcpSheetRepo(SheetRepo):
    """Implementa SheetRepo comunicándose con el proxy MCP por stdio."""

    def __init__(
        self,
        proxy_path: str = PROXY_PATH,
        python: str = sys.executable,
    ) -> None:
        self._proxy_path = proxy_path
        self._python = python
        self._process: subprocess.Popen | None = None
        self._next_id: int = 1

    def snapshot(
        self,
        bundle: Bundle,
        spreadsheet_id: str,
        catalogo: Sequence[Metric],
    ) -> str:
        """Crea o actualiza las 5 hojas del snapshot.

        Args:
            bundle: Bundle canónico validado.
            spreadsheet_id: ID del spreadsheet destino.
            catalogo: Catálogo de métricas para resolver nombres y plataformas
                en Reporte y Configuracion.

        Returns:
            El mismo spreadsheet_id como confirmación.

        Raises:
            SheetProxyError: Si la comunicación con el proxy falla.
        """
        self._start_proxy()

        try:
            self._init_handshake()

            existing = self._get_spreadsheet_meta(spreadsheet_id)

            existing_sheets: set[str] = set()
            sheet_ids: dict[str, int] = {}
            if existing and "fields" in existing:
                fields = existing["fields"]
                if "sheets" in fields:
                    for s in fields["sheets"]:
                        properties = s.get("properties", {})
                        title = properties.get("title", "")
                        sheet_id = properties.get("sheetId")
                        if title and isinstance(sheet_id, int):
                            existing_sheets.add(title)
                            sheet_ids[title] = sheet_id

            requests: list[dict] = []
            missing_names: list[str] = []

            # Crear hojas faltantes
            for name in SHEET_NAMES:
                if name not in existing_sheets:
                    missing_names.append(name)
                    requests.append(
                        {
                            "addSheet": {
                                "properties": {"title": name}
                            }
                        }
                    )

            if requests:
                result = self._call_tool("update_sheet", {
                    "spreadsheetId": spreadsheet_id,
                    "requests": requests,
                })
                for name, reply in zip(missing_names, result.get("replies", [])):
                    properties = reply.get("addSheet", {}).get("properties", {})
                    title = properties.get("title", name)
                    sheet_id = properties.get("sheetId")
                    if title in SHEET_NAMES and isinstance(sheet_id, int):
                        sheet_ids[title] = sheet_id

            if not set(SHEET_NAMES).issubset(sheet_ids):
                raise SheetProxyError("Google no devolvió IDs válidos para todas las hojas")

            requests = []
            requests.extend(_build_control_requests(bundle, existing_sheets, sheet_ids))
            requests.extend(_build_datos_requests(bundle, existing_sheets, sheet_ids))
            requests.extend(_build_reporte_requests(bundle, existing_sheets, sheet_ids, catalogo))
            requests.extend(_build_errores_requests(bundle.dqs, existing_sheets, sheet_ids))
            requests.extend(_build_config_requests(bundle, existing_sheets, sheet_ids, catalogo))
            self._call_tool("update_sheet", {
                "spreadsheetId": spreadsheet_id,
                "requests": requests,
            })

            return spreadsheet_id

        except SheetProxyError:
            raise
        except Exception as e:
            raise SheetProxyError(
                f"Error en snapshot Sheets: {_sanitize(str(e))}"
            ) from e
        finally:
            self._stop_proxy()

    # ── Proxy lifecycle ─────────────────────────────────────────────────

    def _start_proxy(self) -> None:
        """Lanza el proxy MCP como subproceso."""
        if self._process is not None:
            return
        self._process = subprocess.Popen(
            [self._python, self._proxy_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
        )

    def _stop_proxy(self) -> None:
        """Detiene el proxy MCP y limpia recursos."""
        if self._process is None:
            return
        try:
            self._process.stdin.close()
        except Exception:
            pass
        try:
            self._process.terminate()
        except Exception:
            pass
        try:
            self._process.wait(timeout=5)
        except Exception:
            try:
                self._process.kill()
            except Exception:
                pass
        self._process = None

    def _rpc(self, method: str, params: dict | None = None) -> dict:
        """Envía una solicitud JSON-RPC y devuelve la respuesta."""
        rid = self._next_id
        self._next_id += 1

        req: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": rid,
            "method": method,
        }
        if params is not None:
            req["params"] = params

        line = json.dumps(req, ensure_ascii=False) + "\n"
        try:
            assert self._process is not None
            assert self._process.stdin is not None
            assert self._process.stdout is not None
            self._process.stdin.write(line)
            self._process.stdin.flush()
            resp_line = self._process.stdout.readline()
            if not resp_line:
                raise SheetProxyError(
                    "Proxy MCP no respondió (EOF)"
                )
            resp = json.loads(resp_line)
            if resp.get("id") != rid:
                raise SheetProxyError("Respuesta desalineada del proxy MCP")
            if "error" in resp:
                raise SheetProxyError(
                    f"Proxy MCP error: {resp['error'].get('message', 'desconocido')}"
                )
            return resp.get("result", {})
        except json.JSONDecodeError:
            raise SheetProxyError("Respuesta inválida del proxy MCP")
        except BrokenPipeError:
            raise SheetProxyError(
                "Conexión con proxy MCP rota"
            )

    def _init_handshake(self) -> None:
        """Envía el handshake JSON-RPC initialize."""
        result = self._rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "consejo-2026-snapshot", "version": "0.1.0"},
        })
        if result.get("protocolVersion") != "2024-11-05":
            raise SheetProxyError("Handshake MCP inválido")
        if not isinstance(result.get("capabilities"), dict):
            raise SheetProxyError("Handshake MCP inválido")
        # notifications/initialized no espera respuesta
        line = (
            json.dumps(
                {"jsonrpc": "2.0", "method": "notifications/initialized"}
            )
            + "\n"
        )
        assert self._process is not None
        assert self._process.stdin is not None
        self._process.stdin.write(line)
        self._process.stdin.flush()

    def _call_tool(self, name: str, arguments: dict) -> dict:
        """Invoca una herramienta del proxy MCP."""
        return self._rpc("tools/call", {
            "name": name,
            "arguments": arguments,
        })

    def _get_spreadsheet_meta(
        self, spreadsheet_id: str
    ) -> dict | None:
        """Obtiene metadatos del spreadsheet."""
        try:
            return self._call_tool("get_spreadsheet", {
                "spreadsheetId": spreadsheet_id,
                "includeGridData": False,
            })
        except SheetProxyError:
            return None


# ── Helpers de contenido ────────────────────────────────────────────────────


def _build_control_requests(
    bundle: Bundle, existing: set[str], sheet_ids: dict[str, int]
) -> list[dict]:
    """Construye requests para la hoja Control."""
    sheet_id = sheet_ids["Control"]
    clear = _clear_sheet_if_exists("Control", existing, sheet_id)

    rows_data = [
        {"values": [{"userEnteredValue": {"stringValue": "Campo"}},
                     {"userEnteredValue": {"stringValue": "Valor"}}]},
        {"values": [
            {"userEnteredValue": {"stringValue": "run_id"}},
            {"userEnteredValue": {"stringValue": str(bundle.run_id)}},
        ]},
        {"values": [
            {"userEnteredValue": {"stringValue": "attempt_id"}},
            {"userEnteredValue": {"stringValue": str(bundle.attempt_id)}},
        ]},
        {"values": [
            {"userEnteredValue": {"stringValue": "cut"}},
            {"userEnteredValue": {"stringValue": str(bundle.cut)}},
        ]},
        {"values": [
            {"userEnteredValue": {"stringValue": "catalog_hash"}},
            {"userEnteredValue": {"stringValue": bundle.catalog_hash}},
        ]},
        {"values": [
            {"userEnteredValue": {"stringValue": "bundle_hash"}},
            {"userEnteredValue": {"stringValue": str(bundle.hash)}},
        ]},
        {"values": [
            {"userEnteredValue": {"stringValue": "metrics"}},
            {"userEnteredValue": {"stringValue": str(len(bundle.manifests))}},
        ]},
        {"values": [
            {"userEnteredValue": {"stringValue": "rows"}},
            {"userEnteredValue": {"stringValue": str(len(bundle.rows))}},
        ]},
        {"values": [
            {"userEnteredValue": {"stringValue": "dqs_issues"}},
            {"userEnteredValue": {"stringValue": str(len(bundle.dqs))}},
        ]},
    ]

    # Frescura por fuente
    freshness: dict[str, float] = {}
    for m in bundle.manifests:
        src = m.source.value
        freshness[src] = max(
            freshness.get(src, 0.0), m.freshness_hours
        )
    for src, hours in sorted(freshness.items()):
        rows_data.append({
            "values": [
                {"userEnteredValue": {"stringValue": f"freshness_{src}"}},
                {"userEnteredValue": {"numberValue": round(hours, 1)}},
            ]
        })

    return clear + [
        {
            "updateCells": {
                "start": {
                    "sheetId": sheet_id,
                    "rowIndex": 0,
                    "columnIndex": 0,
                },
                "rows": rows_data,
                "fields": "userEnteredValue",
            }
        }
    ]


def _build_datos_requests(
    bundle: Bundle, existing: set[str], sheet_ids: dict[str, int]
) -> list[dict]:
    """Construye requests para la hoja Datos (tablas de slides).

    Cada manifest cuyo metric_id empieza con 'slide' (y no es slide_naming,
    una nota conceptual sin SQL) y tiene filas produce una tabla con su
    layout propio: slide1 (8 columnas, =SUM en B/C/D/E), slide12 (8 columnas
    Sección/Ruta/Cursos/Inscripciones/Certificados/Período inicio/
    Período fin/Fuente, con SUBTOTALES POR SECCIÓN y un TOTAL global que
    suma solo los subtotales, ver _build_slide12_block), slide2 (7 columnas Categoría/Sector/
    Curso/Certificados/Período inicio/
    Período fin/Fuente, =SUM en D) o slide3 (9 columnas Categoría/Programa/
    2025/sep2026/dic2026/Acumulado sep2026/Período inicio/Período fin/
    Fuente, UNA tabla comparativa que agrupa todos los manifests slide3) y
    slide4 (9 columnas Categoría/Programa/2025/sep2026/dic2026/Acumulado
    sep2026/Período inicio/Período fin/Fuente, UNA tabla comparativa que
    agrupa todos los manifests slide4). Las tablas se escriben consecutivas
    separadas por una fila en blanco. Al final se escriben SIEMPRE los bloques
    fijos de slide 7 y slide 8 (grillas de plataformas, ver
    _build_slide7_block y _build_slide8_block), que no provienen de ningún
    manifest y por lo tanto dejan rows_data no vacío en la práctica.
    """
    sheet_id = sheet_ids["Datos"]
    clear = _clear_sheet_if_exists("Datos", existing, sheet_id)

    slides = [m for m in bundle.manifests if _is_slide_table_manifest(m)]
    slide3_manifests = [
        m for m in slides if str(m.metric_id).startswith("slide3")
    ]
    slide4_manifests = [
        m for m in slides if str(m.metric_id).startswith("slide4")
    ]
    # slide13_* se agrupa en un solo bloque (la tarjeta de KPIs de
    # Centros Penitenciarios junta las 4 métricas en 5 filas; ver
    # _build_slide13_block). Excluir de single_slides para que NO se
    # rutee via _build_slide_block (que rechazaría slide13 con
    # ValueError).
    slide13_manifests = [
        m for m in slides if str(m.metric_id).startswith("slide13")
    ]
    # slide15_* (Mario Molina) se agrupa en un solo bloque con 2 KPIs;
    # se excluye de single_slides por la misma razón que slide13.
    slide15_manifests = [
        m for m in slides if str(m.metric_id).startswith("slide15")
    ]
    # slide19_* (Pilotos por la seguridad vial / Aprende de seguridad
    # vial) se agrupa en un solo bloque con 4 KPIs desde queries + 1
    # hardcoded; se excluye de single_slides por la misma razón.
    slide19_manifests = [
        m for m in slides if str(m.metric_id).startswith("slide19")
    ]
    # slide20_* (Crecimiento integral) se agrupa en un solo bloque con 2
    # KPIs desde queries + 1 hardcoded; se excluye de single_slides por
    # la misma razón.
    slide20_manifests = [
        m for m in slides if str(m.metric_id).startswith("slide20")
    ]
    single_slides = [
        m for m in slides
        if not str(m.metric_id).startswith("slide3")
        and not str(m.metric_id).startswith("slide4")
        and not str(m.metric_id).startswith("slide13")
        and not str(m.metric_id).startswith("slide15")
        and not str(m.metric_id).startswith("slide19")
        and not str(m.metric_id).startswith("slide20")
    ]

    rows_data: list[dict] = []
    row_0based = 0
    for index, manifest in enumerate(single_slides):
        if index > 0:
            rows_data.append(_blank_row())
            row_0based += 1

        block, row_0based = _build_slide_block(manifest, row_0based)
        rows_data.extend(block)

    if slide3_manifests:
        if rows_data:
            rows_data.append(_blank_row())
            row_0based += 1
        block, row_0based = _build_slide3_block(slide3_manifests, row_0based)
        rows_data.extend(block)

    if slide4_manifests:
        if rows_data:
            rows_data.append(_blank_row())
            row_0based += 1
        block, row_0based = _build_slide4_block(slide4_manifests, row_0based)
        rows_data.extend(block)

    # Slide 7: bloque FIJO al final de la hoja. La grilla de plataformas
    # siempre se escribe aunque no haya manifests, por lo que rows_data
    # nunca queda vacío en la práctica.
    if rows_data:
        rows_data.append(_blank_row())
        row_0based += 1
    block, row_0based = _build_slide7_block(row_0based)
    rows_data.extend(block)

    # Slide 8: bloque FIJO al final de la hoja (mismo patrón que slide 7).
    if rows_data:
        rows_data.append(_blank_row())
        row_0based += 1
    block, row_0based = _build_slide8_block(row_0based)
    rows_data.extend(block)

    # Slide 13: bloque dinámico con 4 KPIs desde el pipeline (Centros
    # Penitenciarios: inscripciones, certificados, usuarios únicos,
    # cursos únicos) + 1 KPI hardcoded (Centros, sin query natural).
    # Solo se escribe si hay manifests de slide13 en el bundle.
    if slide13_manifests:
        if rows_data:
            rows_data.append(_blank_row())
            row_0based += 1
        block, row_0based = _build_slide13_block(
            slide13_manifests, row_0based
        )
        rows_data.extend(block)

    # Slide 15: bloque dinámico con 2 KPIs desde el pipeline (Mario
    # Molina: inscripciones a cursos, consultas a la sección). Solo se
    # escribe si hay manifests de slide15 en el bundle.
    if slide15_manifests:
        if rows_data:
            rows_data.append(_blank_row())
            row_0based += 1
        block, row_0based = _build_slide15_block(
            slide15_manifests, row_0based
        )
        rows_data.extend(block)

    # Slide 19: bloque dinámico con 4 KPIs desde el pipeline (Pilotos
    # por la seguridad vial / Aprende de seguridad vial: 4 queries con
    # lista de 16 cursos del panel) + 1 KPI hardcoded (Cursos: 16).
    # Solo se escribe si hay manifests de slide19 en el bundle.
    if slide19_manifests:
        if rows_data:
            rows_data.append(_blank_row())
            row_0based += 1
        block, row_0based = _build_slide19_block(
            slide19_manifests, row_0based
        )
        rows_data.extend(block)

    # Slide 20: bloque dinámico con 2 KPIs desde el pipeline
    # (Crecimiento integral: 2 queries con lista de 78 cursos del panel)
    # + 1 KPI hardcoded (Contenido: 78). Solo se escribe si hay
    # manifests de slide20 en el bundle.
    if slide20_manifests:
        if rows_data:
            rows_data.append(_blank_row())
            row_0based += 1
        block, row_0based = _build_slide20_block(
            slide20_manifests, row_0based
        )
        rows_data.extend(block)

    if not rows_data:
        rows_data = [_text_row(SLIDE_TABLE_HEADERS)]

    return clear + [
        {
            "updateCells": {
                "start": {
                    "sheetId": sheet_id,
                    "rowIndex": 0,
                    "columnIndex": 0,
                },
                "rows": rows_data,
                "fields": "userEnteredValue",
            }
        }
    ]


# ── Helpers de tabla Slide ───────────────────────────────────────────────────


SLIDE_TABLE_HEADERS = [
    "Categoría",
    "Cursos únicos",
    "Compartidos",
    "Cursos totales",
    "Certificados",
    "Período inicio",
    "Período fin",
    "Fuente",
]

# Columnas numéricas (1-indexadas: B, C, D, E) que llevan fórmula =SUM en el total.
SLIDE_SUM_COLUMNS = (2, 3, 4, 5)

# Layout de Slide 12: rutas de aprendizaje (Cursos | Inscripciones |
# Certificados) en 4 secciones (Construcción, Habilidades digitales,
# Capacitación básica, Emprendimiento). Misma nomenclatura que las otras
# slides: Categoría = metric_id ("slide12_rutas_aprendizaje") en todas
# las filas de la slide; Sección = nombre de la subsección (Construcción,
# Habilidades digitales, etc.); Ruta = nombre del curso/ruta.
SLIDE12_METRIC_ID = "slide12_rutas_aprendizaje"
SLIDE12_TABLE_HEADERS = [
    "Categoría",
    "Sección",
    "Ruta",
    "Cursos",
    "Inscripciones",
    "Certificados",
    "Período inicio",
    "Período fin",
    "Fuente",
]
# Columnas numéricas (1-indexadas: D, E, F) que llevan fórmula =SUM en
# el total. La columna Categoría (A) lleva el metric_id repetido, igual
# que slide1 lleva slide1_alimentos, slide1_desastres, etc.
SLIDE12_SUM_COLUMNS = (4, 5, 6)

# Layout de Slide 2: certificados por sector empleo incluyente.
SLIDE2_TABLE_HEADERS = [
    "Categoría",
    "Sector",
    "Curso",
    "Certificados",
    "Período inicio",
    "Período fin",
    "Fuente",
]
# Columna 1-indexada (D) que lleva fórmula =SUM en la fila TOTAL de slide2.
SLIDE2_SUM_COLUMN = 4

# Layout de Slide 3: tabla comparativa de programas de educación y empleo.
# Mismo contrato columnas que slides 1/2 (Categoría/Programa + ventanas de
# valor + Período inicio/Período fin/Fuente) para la consistencia transversal.
SLIDE3_TABLE_HEADERS = [
    "Categoría",
    "Programa",
    "2025",
    "sep2026",
    "dic2026",
    "Acumulado sep2026",
    "Período inicio",
    "Período fin",
    "Fuente",
]

# Ventanas fijas de los valores visibles: 2025 = [2025-01-01, 2026-01-01),
# sep2026 = [2026-01-01, 2026-08-02); el union de ventanas visibles es
# 2025-01-01..2026-08-02. Las filas slide3 de MySQL no traen estos campos.
SLIDE3_PERIODO_INICIO = "2025-01-01"
SLIDE3_PERIODO_FIN = "2026-08-02"
SLIDE3_FUENTE_MYSQL = "mysql"

# Label legible por key de métrica slide3 (se deriva de la key porque
# _build_datos_requests no recibe el catálogo).
SLIDE3_LABELS = {
    "slide3_capacitate_carso": "Capacitate Carso",
    "slide3_academica_labs": "Academica Labs",
}

# Layout de Slide 4: tabla comparativa de programas de educación y
# divulgación (mismo contrato columnas que slides 1/2/3).
SLIDE4_TABLE_HEADERS = [
    "Categoría",
    "Programa",
    "2025",
    "sep2026",
    "dic2026",
    "Acumulado sep2026",
    "Período inicio",
    "Período fin",
    "Fuente",
]

# Layout de Slide 7: grilla de plataformas de educación y empleo.
# Valores aprobados tal cual de la presentación (definición = columna
# acumulada de slide 3). Ninguno proviene del pipeline: fuente 'manual'
# para las 3 filas, aunque la definición coincide con la de slide 3.
SLIDE7_TABLE_HEADERS = [
    "Categoría",
    "Programa",
    "Usuarios",
    "Período inicio",
    "Período fin",
    "Fuente",
]
SLIDE7_ROWS = [
    ("slide7_capacitate_empleo", "Capacítate para el Empleo", ""),
    ("slide7_academica_labs", "Académica Labs", 4317),
    ("slide7_capacitate_carso", "Capacítate Carso", 593490),
]

# Layout de Slide 8: grilla de plataformas de educación y divulgación.
# Valores aprobados tal cual de la presentación (definición = columna
# acumulada de slide 4). Ninguno proviene del pipeline: fuente 'manual'
# para las 3 filas, aunque la definición coincide con la de slide 4.
SLIDE8_TABLE_HEADERS = [
    "Categoría",
    "Programa",
    "Usuarios",
    "Período inicio",
    "Período fin",
    "Fuente",
]
SLIDE8_ROWS = [
    ("slide8_pilotos_seguridad_vial", "Pilotos por la Seguridad Vial", 146132, "slide4"),
    ("slide8_formacion_penitenciarios", "Formación en Centros Penitenciarios", 2757, "slide13"),
    ("slide8_aprende_seguridad_vial", "Aprende de Seguridad Vial", 207559, "slide4"),
    ("slide8_cultura_salud_aprende", "Cultura y Salud Aprende", 1523219, "slide4"),
]

# Layout de Slide 13: tarjeta de KPIs del programa "Formación en Centros
# Penitenciarios" (objectId g3735641ff7a_1_115 en la presentación del
# Consejo 2026). 4 KPIs vienen de las métricas `slide13_*` del catálogo
# (inscripciones, certificados, usuarios únicos, cursos únicos) que
# consultan la BD MySQL `capacitate_analisis` con las queries del archivo
# `Consultas_consejo_panel.sql` (filtro por brandId IN (16, 18) — los
# únicos brands relacionados a Centros Penitenciarios en la BD: 16 =
# DETPCDMX y 18 = CEFERESOS — más la lista de 98 course IDs del
# programa; se excluyen 2 cursos con `course.hide = 1`: ID 100
# 'Management operativo' e ID 297 'Prácticas de cortesía'). 1 KPI
# ("Centros": 7) queda hardcoded porque no tiene query natural — es la
# cantidad de penitenciarías físicas operadas por el programa, dato
# aprobado de la presentación que no se infiere de la BD.
# Sin TOTAL: cada métrica es independiente. El texto narrativo de la
# slide original queda en la presentación de Slides — el Sheet "Datos"
# solo escribe las tablas de datos. Mismo formato de 6 columnas que las
# otras slides (Período inicio / Período fin / Fuente al final).
SLIDE13_METRIC_ID = "slide13_penitenciarios"
SLIDE13_CENTROS = 7
SLIDE13_PERIODO_INICIO = "Acumulado"
SLIDE13_PERIODO_FIN = "2026-08-01"
SLIDE13_FUENTE_INSCRIPCION = "inscription"
SLIDE13_TABLE_HEADERS = [
    "Categoría",
    "Métrica",
    "Valor",
    "Período inicio",
    "Período fin",
    "Fuente",
]

# Layout de Slide 15: tarjeta de KPIs de "Mario Molina Premio Nobel"
# (objectId g3735641ff7a_1_93 en la presentación del Consejo 2026).
# 2 KPIs vienen de las métricas `slide15_*` del catálogo:
#   - slide15_mario_molina_inscripciones: COUNT(u.id) sobre inscription
#     JOIN course JOIN user con c.id IN (217, 236, 310) (los 3 cursos
#     del programa Mario Molina) y i.inscripcionDate < '2026-08-01'.
#   - slide15_mario_molina_vistas: SUM(ur.count) sobre userresource
#     JOIN resource con r.id IN (33 IDs de recursos de la sección
#     Mario Molina) y ur.lastUpdate < '2026-08-01'.
# Queries del archivo Consultas_consejo_panel.sql (sección Mario
# Molina). El texto narrativo "Mario Molina Premio Nobel" + descripción
# de la sección queda en la presentación de Slides — el Sheet "Datos"
# solo escribe las tablas de datos. Mismo formato de 6 columnas que
# las otras slides (Período inicio / Período fin / Fuente al final).
SLIDE15_METRIC_ID = "slide15_mario_molina"
SLIDE15_PERIODO_INICIO = "Acumulado"
SLIDE15_PERIODO_FIN = "2026-08-01"
SLIDE15_FUENTE_INSCRIPCION = "inscription"
SLIDE15_FUENTE_USERRESOURCE = "userresource"
SLIDE15_TABLE_HEADERS = [
    "Categoría",
    "Métrica",
    "Valor",
    "Período inicio",
    "Período fin",
    "Fuente",
]

# Layout de Slide 19: tarjeta de KPIs de "Pilotos por la seguridad
# vial / Aprende de seguridad vial" (objectId g3735641ff7a_1_161 en
# la presentación del Consejo 2026). 4 KPIs vienen de las métricas
# `slide19_*` del catálogo (4 queries de
# `Consultas_consejo_panel.sql` con la lista de 16 cursos de seguridad
# vial); 1 KPI (Cursos: 16) queda hardcoded porque la lista de cursos
# la define el panel SQL, no un COUNT. Mismo formato de 6 columnas que
# las otras slides (Período inicio / Período fin / Fuente al final).
SLIDE19_METRIC_ID = "slide19_seguridad_vial"
SLIDE19_CURSOS_TOTAL = 16
SLIDE19_PERIODO_INICIO = "Acumulado"
SLIDE19_PERIODO_FIN = "2026-08-01"
SLIDE19_FUENTE_INSCRIPCION = "fact_inscription"
SLIDE19_TABLE_HEADERS = [
    "Categoría",
    "Métrica",
    "Valor",
    "Período inicio",
    "Período fin",
    "Fuente",
]

# Layout de Slide 20: tarjeta de KPIs de "Crecimiento integral" (última
# slide de la presentación del Consejo 2026). 2 KPIs vienen de las
# métricas `slide20_*` del catálogo (2 queries en `analisis_cpe_db`
# PostgreSQL con la lista de 78 cursos de crecimiento integral del
# archivo Consultas_consejo_panel.sql, con filtro cross-pollination
# `c.platformId = 1 AND du.plataformaId = 2`). Mismo formato de 6
# columnas que las otras slides (Período inicio / Período fin / Fuente
# al final).
SLIDE20_METRIC_ID = "slide20_crecimiento_integral"
SLIDE20_PERIODO_INICIO = "Acumulado"
SLIDE20_PERIODO_FIN = "2026-08-01"
SLIDE20_FUENTE_INSCRIPCION = "fact_inscription"
SLIDE20_TABLE_HEADERS = [
    "Categoría",
    "Métrica",
    "Valor",
    "Período inicio",
    "Período fin",
    "Fuente",
]

# Ventanas fijas de los valores visibles de slide 4: 2025 =
# [2025-01-01, 2026-01-01), sep2026 = [2026-01-01, 2026-10-01),
# dic2026 = [2026-01-01, 2026-08-01) y acumulado histórico < 2026-08-01
# (la fecha 2026-08-01 documenta el cierre de la ventana visible y se
# alinea con el patrón de slide3). Las filas slide4 de PostgreSQL no
# traen estos campos.
SLIDE4_PERIODO_INICIO = "2025-01-01"
SLIDE4_PERIODO_FIN = "2026-08-01"
SLIDE4_FUENTE_POSTGRES = "postgres"
SLIDE4_FUENTE_MYSQL = "mysql"
# Fuente mixta: la fila combina ventanas desde PostgreSQL con el acumulado
# histórico proveniente de la métrica hermana *_acumulado (MySQL), p.ej.
# slide4_aprende_seguridad_vial + slide4_aprende_seguridad_vial_acumulado.
SLIDE4_FUENTE_MIXTA = "postgres + mysql"
# Sufijo de la métrica hermana que provee el acumulado histórico a su
# métrica base de slide 4 (p.ej. slide4_aprende_seguridad_vial_acumulado).
SLIDE4_ACUMULADO_SUFFIX = "_acumulado"

# Label legible por key de métrica slide4 (se deriva de la key porque
# _build_datos_requests no recibe el catálogo).
SLIDE4_LABELS = {
    "slide4_aprende_seguridad_vial": "Aprende de seguridad vial",
    "slide4_cultura_salud_aprende": "Cultura y Salud Aprende (registros)",
}

# Proyección lineal de dic2026: el total anual estimado se deriva del ritmo
# mensual observado en la ventana sep2026 (enero a julio completos) aplicado
# a los meses restantes del año (agosto a diciembre).
SLIDE3_MESES_OBSERVADOS = 7
SLIDE3_MESES_RESTANTES = 5


def _project_dic2026(sep2026_value: int) -> int:
    """Proyección lineal del total de enero a diciembre de 2026.

    dic2026 = round(sep2026 + (sep2026 / MESES_OBSERVADOS) * MESES_RESTANTES)
            = round(sep2026 * (1 + MESES_RESTANTES / MESES_OBSERVADOS))

    El promedio mensual observado (sep2026 / 7 meses completos ene-jul) se
    extiende a los meses restantes ago-dic. Es una estimación de ritmo
    constante, no una predicción con tendencia.
    """
    factor = 1 + SLIDE3_MESES_RESTANTES / SLIDE3_MESES_OBSERVADOS
    return round(sep2026_value * factor)


def _slide3_label(key: str) -> str:
    """Label legible para un programa de slide 3 a partir de su key.

    'slide3_capacitate_carso' -> 'Capacitate Carso'
    'slide3_academica_labs'   -> 'Academica Labs'
    Cualquier otra key slide3 se devuelve tal cual.
    """
    return SLIDE3_LABELS.get(key, key)


def _slide4_label(key: str) -> str:
    """Label legible para un programa de slide 4 a partir de su key.

    'slide4_aprende_seguridad_vial'    -> 'Aprende de seguridad vial'
    'slide4_cultura_salud_aprende'     -> 'Cultura y Salud Aprende (registros)'
    Cualquier otra key slide4 se devuelve tal cual.
    """
    return SLIDE4_LABELS.get(key, key)


def _is_slide_table_manifest(manifest: SourceManifest) -> bool:
    """True si el manifest es una tabla de slide con filas."""
    key = str(manifest.metric_id)
    return key.startswith("slide") and key != "slide_naming" and bool(manifest.rows)


def _build_slide_block(
    manifest: SourceManifest, row_0based: int
) -> tuple[list[dict], int]:
    """Construye el bloque (header + filas + TOTAL) para una slide.

    El layout se elige por prefijo de la key: 'slide12' usa 8 columnas
    (ver _build_slide12_block), 'slide1' usa 8 columnas
    (ver _build_slide1_block), 'slide2' usa 3 columnas Sector/Curso/
    Certificados (ver _build_slide2_block) y 'slide3' usa la tabla
    comparativa de programas (ver _build_slide3_block). Devuelve
    (rows_data_list, next_row_0based).
    """
    key = str(manifest.metric_id)
    # 'slide12_*' empieza con 'slide1', así que debe ruteo ANTES del check
    # de slide1 (si no, slide12 caería en _build_slide1_block).
    if key.startswith("slide12"):
        return _build_slide12_block(manifest, row_0based)
    # 'slide13_*' (Centros Penitenciarios): se rutean desde el caller
    # _build_datos_requests que junta los 4 manifests de slide13 en un
    # solo bloque. Si llega acá con un solo manifest, levantamos
    # ValueError para no escribir un bloque parcial.
    if key.startswith("slide13"):
        raise ValueError(
            f"slide13_* debe rutearse via _build_slide13_block con todos "
            f"los manifests juntos, no via _build_slide_block (key={key})"
        )
    # 'slide15_*' (Mario Molina): se rutean desde el caller
    # _build_datos_requests que junta los 2 manifests de slide15 en un
    # solo bloque. Si llega acá con un solo manifest, levantamos
    # ValueError para no escribir un bloque parcial.
    if key.startswith("slide15"):
        raise ValueError(
            f"slide15_* debe rutearse via _build_slide15_block con todos "
            f"los manifests juntos, no via _build_slide_block (key={key})"
        )
    # 'slide19_*' (Pilotos por la seguridad vial / Aprende de seguridad
    # vial): se rutean desde el caller _build_datos_requests que junta
    # los 4 manifests de slide19 en un solo bloque. Si llega acá con un
    # solo manifest, levantamos ValueError.
    if key.startswith("slide19"):
        raise ValueError(
            f"slide19_* debe rutearse via _build_slide19_block con todos "
            f"los manifests juntos, no via _build_slide_block (key={key})"
        )
    # 'slide20_*' (Crecimiento integral): se rutean desde el caller
    # _build_datos_requests que junta los 2 manifests de slide20 en un
    # solo bloque. Si llega acá con un solo manifest, levantamos
    # ValueError.
    if key.startswith("slide20"):
        raise ValueError(
            f"slide20_* debe rutearse via _build_slide20_block con todos "
            f"los manifests juntos, no via _build_slide_block (key={key})"
        )
    if key.startswith("slide1"):
        return _build_slide1_block(manifest, row_0based)
    if key.startswith("slide2"):
        return _build_slide2_block(manifest, row_0based)
    if key.startswith("slide3"):
        return _build_slide3_block([manifest], row_0based)
    if key.startswith("slide4"):
        return _build_slide4_block([manifest], row_0based)
    raise ValueError(f"Slide manifest sin layout conocido: {key}")


def _build_slide1_block(
    manifest: SourceManifest, row_0based: int
) -> tuple[list[dict], int]:
    """Bloque slide1: 8 columnas, TOTAL con =SUM en B, C, D, E."""
    rows: list[dict] = []
    rows.append(_text_row(SLIDE_TABLE_HEADERS))
    header_0 = row_0based
    row_0based += 1

    for r in manifest.rows:
        rows.append(_slide_data_row(r))
        row_0based += 1

    rows.append(_slide_total_row(header_0, row_0based))
    row_0based += 1
    return rows, row_0based


def _build_slide12_block(
    manifest: SourceManifest, row_0based: int
) -> tuple[list[dict], int]:
    """Bloque slide12: 9 columnas (Categoría, Sección, Ruta, Cursos,
    Inscripciones, Certificados, Período inicio, Período fin, Fuente) con
    SUBTOTALES POR SECCIÓN y un TOTAL global.

    La columna Categoría lleva el metric_id de la slide
    ("slide12_rutas_aprendizaje") en TODAS las filas (datos, subtotales y
    TOTAL), igual que slide1 lleva el metric_id de cada subcategoría
    (slide1_alimentos, slide1_desastres, etc.) en su columna Categoría.
    Sección y Ruta se mapean desde el row (seccion, ruta) por cada ruta.

    Las filas del manifest llegan YA ordenadas por la columna `orden` de la
    SQL, así que cada sección (Construcción, Habilidades digitales,
    Capacitación básica, Emprendimiento) aparece en filas consecutivas. Al
    detectar un cambio de sección se emite UNA fila "Subtotal <seccion>" con
    =SUM en D/E/F sobre las filas de ESA sección (ver _slide12_subtotal_row),
    ANTES de la primera fila de la sección siguiente. Al final, la fila
    "TOTAL" global suma SOLO las celdas de los subtotales (ver
    _slide12_global_total_row).

    Decisión de diseño del TOTAL global: usa una suma aditiva
    ``=D<sub1>+D<sub2>+...`` apuntando a las celdas numéricas (D/E/F) de
    los subtotales de cada sección, nunca un rango continuo sobre todas las
    filas de datos: un rango continuo que incluyera subtotales DUPLICARÍA
    los conteos (cada ruta se contaría en su fila y otra vez vía su
    subtotal). Como cada subtotal ya agrega su sección, la suma de
    subtotales es exacta y no depende del largo de las secciones."""
    rows: list[dict] = []
    rows.append(_text_row(SLIDE12_TABLE_HEADERS))
    row_0based += 1

    seccion_actual: str | None = None
    primera_fila_1 = 0
    subtotal_filas_1: list[int] = []

    # La columna Categoría lleva el metric_id de la slide (constante para
    # TODAS las filas de la slide, igual que slide1 lleva el metric_id de
    # cada subcategoría). Se resuelve desde el manifest porque la SQL no
    # lo trae en cada row.
    categoria = str(manifest.metric_id)

    def _emitir_subtotal() -> None:
        nonlocal row_0based
        subtotal_1 = row_0based + 1
        rows.append(_slide12_subtotal_row(
            seccion_actual, primera_fila_1, row_0based
        ))
        row_0based += 1
        subtotal_filas_1.append(subtotal_1)

    for r in manifest.rows:
        seccion = str(r.get("seccion", ""))
        if seccion != seccion_actual:
            if seccion_actual is not None:
                _emitir_subtotal()
            seccion_actual = seccion
            primera_fila_1 = row_0based + 1
        rows.append(_slide12_data_row(r, categoria))
        row_0based += 1

    if seccion_actual is not None:
        _emitir_subtotal()

    rows.append(_slide12_global_total_row(subtotal_filas_1))
    row_0based += 1
    return rows, row_0based


def _slide12_data_row(
    row: Mapping[str, object], categoria: str = ""
) -> dict:
    """Fila de datos slide12: 9 celdas.

    Columna A Categoría = metric_id de la slide (igual para todas las
    filas, "slide12_rutas_aprendizaje"); Sección y Ruta se mapean desde
    el row (seccion, ruta); Cursos usa value; Inscripciones y
    Certificados usan sus keys; y el resto del contrato (período y
    fuente) es idéntico a slides 1/2.

    ``categoria`` se resuelve en _build_slide12_block desde
    ``manifest.metric_id`` (la SQL real no lo trae en cada row; se
    prefiere ese origen antes que un fallback del row para garantizar
    que la columna Categoría nunca quede vacía).
    """
    cat = categoria or str(row.get("metric_id", ""))
    values = [
        cat,
        row.get("seccion", ""),
        row.get("ruta", ""),
        row.get("value", ""),
        row.get("inscripciones", ""),
        row.get("certificados", ""),
        row.get("periodo_inicio", ""),
        row.get("periodo_fin", ""),
        row.get("source", ""),
    ]
    cells = [_value_cell(v) for v in values]
    return {"values": cells}


def _slide12_total_row(header_0: int, total_0: int) -> dict:
    """Fila TOTAL slide12: 9 celdas con =SUM en columnas Cursos (D),
    Inscripciones (E) y Certificados (F).

    A diferencia de _slide_total_row (slide1), las columnas con =SUM no
    arrancan en la columna B: la columna A lleva el metric_id, la
    columna B lleva "TOTAL", la columna C (Ruta) queda vacía y los =SUM
    caen en los índices 4, 5 y 6 (D, E, F).

    NOTA: esta función ya NO se usa en el pipeline actual — ver
    _slide12_global_total_row, que arma el TOTAL global con suma aditiva
    sobre los subtotales. Se conserva por compatibilidad con tests
    históricos y para uso futuro si el patrón cambia.
    """
    first_data_1 = header_0 + 2
    last_data_1 = total_0
    cells: list[dict] = [
        {"userEnteredValue": {"stringValue": SLIDE12_METRIC_ID}},
        {"userEnteredValue": {"stringValue": "TOTAL"}},
        {"userEnteredValue": {}},
    ]
    for col in SLIDE12_SUM_COLUMNS:
        letter = chr(ord("A") + col - 1)
        cells.append({
            "userEnteredValue": {
                "formulaValue": f"=SUM({letter}{first_data_1}:{letter}{last_data_1})"
            }
        })
    cells.extend(
        {"userEnteredValue": {}}
        for _ in range(len(SLIDE12_TABLE_HEADERS) - len(cells))
    )
    return {"values": list(cells)}


def _slide12_subtotal_row(seccion: str, first_1: int, last_1: int) -> dict:
    """Fila de subtotal de UNA sección slide12: 9 celdas.

    Col A Categoría = metric_id de la slide, col B "Subtotal <seccion>",
    col C (Ruta) vacía y =SUM en las columnas Cursos (D), Inscripciones
    (E) y Certificados (F) sobre las filas de datos [first_1..last_1]
    de esa sección (1-indexed, mismo contrato de rango que
    _slide12_total_row).
    """
    cells: list[dict] = [
        {"userEnteredValue": {"stringValue": SLIDE12_METRIC_ID}},
        {"userEnteredValue": {"stringValue": f"Subtotal {seccion}"}},
        {"userEnteredValue": {}},
    ]
    for col in SLIDE12_SUM_COLUMNS:
        letter = chr(ord("A") + col - 1)
        cells.append({
            "userEnteredValue": {
                "formulaValue": f"=SUM({letter}{first_1}:{letter}{last_1})"
            }
        })
    cells.extend(
        {"userEnteredValue": {}}
        for _ in range(len(SLIDE12_TABLE_HEADERS) - len(cells))
    )
    return {"values": list(cells)}


def _slide12_global_total_row(subtotal_filas_1: Sequence[int]) -> dict:
    """Fila TOTAL global slide12: 9 celdas con suma aditiva en D/E/F que
    suma SOLO los subtotales de cada sección.

    Col A Categoría = metric_id de la slide, col B "TOTAL", col C (Ruta)
    vacía, y suma aditiva ``=D<sub1>+D<sub2>+...`` apuntando a las celdas
    numéricas (D/E/F) de los subtotales. Nunca un rango continuo sobre
    las filas de datos ni un rango discontinuo ``=SUM(refs)`` con comas:
    ambas alternativas sumarían subtotales DUPLICARÍA los conteos (cada
    ruta se contaría en su fila y otra vez vía su subtotal). Como cada
    subtotal ya agrega su sección, la suma de subtotales es exacta e
    independiente del largo de las secciones.

    Nota: se eligió suma aditiva explícita (``=A+B+C``) en lugar de
    ``=SUM(refs)`` con comas porque Google Sheets devolvió ``#ERROR!`` al
    evaluar el rango discontinuo con comas en este contexto (los
    subtotales por sección ``=SUM(D12:D15)`` y el TOTAL slide1
    ``=SUM(B<first>:B<last>)``, todos con rangos continuos, sí evalúan
    correctamente). La suma aditiva con ``+`` es la sintaxis que evalúa
    consistentemente.
    """
    cells: list[dict] = [
        {"userEnteredValue": {"stringValue": SLIDE12_METRIC_ID}},
        {"userEnteredValue": {"stringValue": "TOTAL"}},
        {"userEnteredValue": {}},
    ]
    for col in SLIDE12_SUM_COLUMNS:
        letter = chr(ord("A") + col - 1)
        refs = "+".join(f"{letter}{fila}" for fila in subtotal_filas_1)
        cells.append({
            "userEnteredValue": {"formulaValue": f"={refs}"}
        })
    cells.extend(
        {"userEnteredValue": {}}
        for _ in range(len(SLIDE12_TABLE_HEADERS) - len(cells))
    )
    return {"values": list(cells)}


def _build_slide2_block(
    manifest: SourceManifest, row_0based: int
) -> tuple[list[dict], int]:
    """Bloque slide2: 7 columnas (Categoría, Sector, Curso, Certificados,
    Período inicio, Período fin, Fuente). Estructura por sector con
    subtotales:

      - Header (Categoría | Sector | Curso | Certificados | Período...).
      - Por cada sector del manifest (las filas del manifest vienen YA
        agrupadas y ordenadas alfabéticamente por `curso` dentro de cada
        sector; ver db_mapping en el catálogo):
          - Fila header de sector: Categoría=metric_id, Sector=nombre,
            resto de columnas vacío.
          - Filas de cursos del sector: Categoría=metric_id, Sector=vacío,
            Curso+Certificados del row.
          - Fila subtotal del sector: Categoría=metric_id,
            Sector="Subtotal <nombre>", Certificados=`=SUM(D<primera>:D<última>)`
            sobre las filas de cursos de ese sector.
      - Fila en blanco.
      - TOTAL GENERAL: Categoría=metric_id, Sector="TOTAL",
        Certificados=suma aditiva `=D<sub1>+D<sub2>+...+D<sub6>`
        (sintaxis con ``+`` — probamos ``=SUM(D<sub1>,D<sub2>,...)``
        con comas y Sheets devolvió ``#ERROR!``; un rango continuo
        ``=SUM(D<sub1>:D<sub_n>)`` tampoco sirve porque las filas
        intermedias tienen cursos de Construcción que duplicarían
        el conteo).

    Las filas del manifest llegan YA ordenadas por la SQL
    (`ORDER BY grupo, curso ASC`), así que cada sector aparece en filas
    consecutivas y dentro de él los cursos van alfabéticos. Al detectar
    un cambio de sector se emite UNA fila header + UNA fila subtotal
    ANTES de la primera fila del sector siguiente (header del nuevo
    sector al inicio, subtotal del anterior al final)."""
    rows: list[dict] = []
    rows.append(_text_row(SLIDE2_TABLE_HEADERS))
    row_0based += 1

    categoria = str(manifest.metric_id)

    seccion_actual: str | None = None
    primera_fila_1 = 0
    ultima_fila_1 = 0
    subtotal_filas_1: list[int] = []

    def _emitir_subtotal() -> None:
        nonlocal row_0based, ultima_fila_1
        subtotal_1 = row_0based + 1
        rows.append(_slide2_subtotal_row(
            categoria, seccion_actual, primera_fila_1, ultima_fila_1
        ))
        row_0based += 1
        subtotal_filas_1.append(subtotal_1)

    for r in manifest.rows:
        seccion = str(r.get("grupo", ""))
        if seccion != seccion_actual:
            # Header del nuevo sector
            if seccion_actual is not None:
                _emitir_subtotal()
            rows.append(_slide2_sector_header_row(categoria, seccion))
            row_0based += 1
            seccion_actual = seccion
            primera_fila_1 = row_0based + 1
        rows.append(_slide2_data_row(r, categoria))
        row_0based += 1
        ultima_fila_1 = row_0based

    if seccion_actual is not None:
        _emitir_subtotal()

    # Fila en blanco entre los sectores y el TOTAL GENERAL
    rows.append(_blank_row())
    row_0based += 1

    # TOTAL GENERAL — suma aditiva sobre los subtotales (columna D)
    rows.append(_slide2_global_total_row(categoria, subtotal_filas_1))
    row_0based += 1
    return rows, row_0based


def _blank_row() -> dict:
    return {
        "values": [
            {"userEnteredValue": {}} for _ in SLIDE_TABLE_HEADERS
        ]
    }


def _text_row(values: Sequence[str]) -> dict:
    return {
        "values": [
            {"userEnteredValue": {"stringValue": v}} for v in values
        ]
    }


def _value_cell(value: object) -> dict:
    if isinstance(value, (int, float)):
        return {"userEnteredValue": {"numberValue": float(value)}}
    s = str(value)
    if not s:
        return {"userEnteredValue": {}}
    return {"userEnteredValue": {"stringValue": s}}


def _slide_data_row(row: Mapping[str, object]) -> dict:
    values = [
        row.get("metric_id", ""),
        row.get("value", ""),
        row.get("compartidos", ""),
        row.get("cursos_totales", ""),
        row.get("certificados", ""),
        row.get("periodo_inicio", ""),
        row.get("periodo_fin", ""),
        row.get("source", ""),
    ]
    return {"values": [_value_cell(v) for v in values]}


def _slide_total_row(header_0: int, total_0: int) -> dict:
    """Fila TOTAL con =SUM sobre la filas de datos 1-indexed [first..last]."""
    first_data_1 = header_0 + 2
    last_data_1 = total_0
    cells = [{"userEnteredValue": {"stringValue": "TOTAL"}}]
    for col in SLIDE_SUM_COLUMNS:
        letter = chr(ord("A") + col - 1)
        cells.append({
            "userEnteredValue": {
                "formulaValue": f"=SUM({letter}{first_data_1}:{letter}{last_data_1})"
            }
        })
    cells.extend({"userEnteredValue": {}} for _ in range(len(SLIDE_TABLE_HEADERS) - 1 - len(SLIDE_SUM_COLUMNS)))
    return {"values": list(cells)}


def _slide2_data_row(row: Mapping[str, object], categoria: str) -> dict:
    """Fila de datos slide2 (un curso): 7 celdas.

    Categoría = metric_id de la slide (constante para todas las filas
    del bloque). Sector queda VACÍO en las filas de cursos — el
    nombre del sector vive solo en la fila header del sector
    (ver _slide2_sector_header_row) para no repetir el label. Curso,
    Certificados, Período y Fuente se mapean desde el row.
    """
    values = [
        categoria,
        "",
        row.get("curso", ""),
        row.get("value", ""),
        row.get("periodo_inicio", ""),
        row.get("periodo_fin", ""),
        row.get("source", ""),
    ]
    cells = [_value_cell(v) for v in values]
    return {"values": cells}


def _slide2_sector_header_row(categoria: str, seccion: str) -> dict:
    """Fila header de sector slide2: 7 celdas.

    Col A Categoría = metric_id, col B Sector = nombre del sector
    (ej. 'Construcción y mantenimiento'), resto vacío. Es la fila que
    antecede a los cursos de ese sector y le da nombre al bloque."""
    values = [
        categoria,
        seccion,
        "",
        "",
        "",
        "",
        "",
    ]
    cells = [_value_cell(v) for v in values]
    return {"values": cells}


def _slide2_subtotal_row(
    categoria: str, seccion: str, first_1: int, last_1: int
) -> dict:
    """Fila de subtotal de UN sector slide2: 7 celdas.

    Col A Categoría = metric_id, col B Sector = 'Subtotal <seccion>',
    col C (Curso) vacía, col D Certificados = =SUM(D<first_1>:D<last_1>)
    sobre las filas de cursos de ese sector (1-indexed, mismo
    contrato de rango que _slide12_subtotal_row)."""
    letter = chr(ord("A") + SLIDE2_SUM_COLUMN - 1)
    cells: list[dict] = [
        _value_cell(categoria),
        _value_cell(f"Subtotal {seccion}"),
        {"userEnteredValue": {}},
        {
            "userEnteredValue": {
                "formulaValue": f"=SUM({letter}{first_1}:{letter}{last_1})"
            }
        },
        {"userEnteredValue": {}},
        {"userEnteredValue": {}},
        {"userEnteredValue": {}},
    ]
    return {"values": list(cells)}


def _slide2_global_total_row(
    categoria: str, subtotal_filas_1: Sequence[int]
) -> dict:
    """Fila TOTAL global slide2: 7 celdas con suma aditiva en D sobre
    las 6 celdas de subtotal.

    Misma sintaxis aditiva (``=D<sub1>+D<sub2>+...``) que
    _slide12_global_total_row — probamos ``=SUM(D<sub1>,D<sub2>,...)``
    con comas y Google Sheets devolvió ``#ERROR!`` (igual que con
    slide12). Las filas subtotal están en posiciones discontinuas
    (5, 12, 27, 33, 41, 47 en el preview, separadas por cursos + filas
    en blanco + headers de sector), por lo que tampoco se puede usar
    un rango continuo ``=SUM(D<sub1>:D<sub_n>)`` — eso sumaría los
    subtotales + los cursos de Construcción dos veces. La suma aditiva
    explícita con ``+`` es la única sintaxis que evalúa consistente.
    """
    letter = chr(ord("A") + SLIDE2_SUM_COLUMN - 1)
    refs = "+".join(f"{letter}{fila}" for fila in subtotal_filas_1)
    cells: list[dict] = [
        _value_cell(categoria),
        _value_cell("TOTAL"),
        {"userEnteredValue": {}},
        {"userEnteredValue": {"formulaValue": f"={refs}"}},
        {"userEnteredValue": {}},
        {"userEnteredValue": {}},
        {"userEnteredValue": {}},
    ]
    return {"values": list(cells)}


def _build_slide3_block(
    manifests: Sequence[SourceManifest], row_0based: int
) -> tuple[list[dict], int]:
    """Bloque slide 3: tabla comparativa de programas de educación y empleo.

    9 columnas (Categoría, Programa, 2025, sep2026, dic2026, Acumulado
    sep2026, Período inicio, Período fin, Fuente) con la misma nomenclatura
    de slides 1/2 (metric_id 'slide3_*' en Categoría, ventanas de valor,
    período y fuente).

    Fila fija "Capacitate Empleo" (manual, fuente 'manual', resto vacío
    incluido el acumulado — no hay query de acumulado para esa fila)
    que SIEMPRE está presente, seguida de UNA fila por cada manifest slide3
    con: Categoría = metric_id tal cual (slide3_capacitate_carso ->
    "slide3_capacitate_carso"), Programa = label legible derivado de la
    key (slide3_capacitate_carso -> "Capacitate Carso") y los valores de
    las columnas de ventana fija "2025", "sep2026" y "acumulado"
    (rango histórico [2000-01-01, 2026-08-01) calculado en el SQL).
    dic2026 es la proyección lineal del total anual sobre sep2026 real
    (ver _project_dic2026). base_dic2026 NO se escribe. Los períodos son
    las ventanas fijas 2025-01-01..2026-08-02 y la fuente es 'mysql'
    (db_source de las métricas slide3 de MySQL). Sin fila TOTAL: el =SUM
    no tiene sentido entre programas distintos.
    """
    rows: list[dict] = []
    rows.append(_text_row(SLIDE3_TABLE_HEADERS))
    row_0based += 1

    cap_empleo = [
        "slide3_capacitate_empleo",
        "Capacitate Empleo",
        "",
        "",
        "",
        "",
        "",
        "",
        "manual",
    ]
    rows.append({"values": [_value_cell(v) for v in cap_empleo]})
    row_0based += 1

    for m in manifests:
        if not m.rows:
            continue
        data = dict(m.rows[0])
        sep2026_raw = data.get("sep2026", "")
        # dic2026 es proyección lineal del total anual sobre el acumulado
        # real sep2026; solo aplica cuando hay valor observado.
        dic2026 = (
            _project_dic2026(int(sep2026_raw)) if str(sep2026_raw) else ""
        )
        cells = [
            _value_cell(str(m.metric_id)),
            _value_cell(_slide3_label(str(m.metric_id))),
            _value_cell(data.get("2025", "")),
            _value_cell(sep2026_raw),
            _value_cell(dic2026),
            _value_cell(data.get("acumulado", "")),
            _value_cell(SLIDE3_PERIODO_INICIO),
            _value_cell(SLIDE3_PERIODO_FIN),
            _value_cell(SLIDE3_FUENTE_MYSQL),
        ]
        rows.append({"values": cells})
        row_0based += 1

    return rows, row_0based


def _build_slide4_block(
    manifests: Sequence[SourceManifest], row_0based: int
) -> tuple[list[dict], int]:
    """Bloque slide 4: tabla comparativa de programas de educación y divulgación.

    9 columnas (Categoría, Programa, 2025, sep2026, dic2026, Acumulado
    sep2026, Período inicio, Período fin, Fuente) con la misma nomenclatura
    de slides 1/2/3 (metric_id 'slide4_*' en Categoría, ventanas de valor,
    período y fuente).

    Fila fija "Pilotos por la Seguridad Vial" (manual, fuente 'manual',
    resto vacío) que SIEMPRE está presente, seguida de UNA fila por cada
    programa slide4 con filas: Categoría = metric_id tal cual
    (slide4_aprende_seguridad_vial -> "slide4_aprende_seguridad_vial"),
    Programa = label legible derivado de la key
    (slide4_aprende_seguridad_vial -> "Aprende de seguridad vial") y los
    valores de las columnas de ventana fija "2025", "sep2026", "dic2026" y
    "acumulado". Los períodos son las ventanas fijas 2025-01-01..2026-09-30
    y la fuente es el db_source del manifest ('postgres' o 'mysql'). Sin
    fila TOTAL: el =SUM no tiene sentido entre programas distintos.

    FUENTE MIXTA: si un programa tiene su métrica hermana *_acumulado en
    el mismo bundle (p.ej. slide4_aprende_seguridad_vial con su hermana
    slide4_aprende_seguridad_vial_acumulado, que vive en MySQL y devuelve
    UN solo valor en la clave "value"), la hermana NO genera fila propia:
    su valor se fusiona en la columna "Acumulado sep2026" de la fila de su
    base y la fuente de esa fila pasa a "postgres + mysql". Sin la base en
    el bundle, la hermana tampoco genera fila (solo aporta su valor).

    Soporta dos shapes de fila:
    - Ventanas fijas (2025/sep2026/dic2026/acumulado): la fila trae las
      claves "2025", "sep2026", "dic2026", "acumulado" -> se escriben las
      4 columnas, períodos fijos y fuente = db_source del manifest (o
      "postgres + mysql" si la base tiene hermana *_acumulado fusionada).
    - Fallback single-value: la fila trae UN solo valor acumulado (clave
      "value" sin "2025") -> se escribe solo la columna "Acumulado
      sep2026", 2025/sep2026/dic2026 vacías, períodos de la fila y fuente
      = db_source del manifest (compatibilidad con queries que devolvían
      el acumulado único, p.ej. la query de slide 19).
    """
    rows: list[dict] = []
    rows.append(_text_row(SLIDE4_TABLE_HEADERS))
    row_0based += 1

    pilotos = [
        "slide4_pilotos_seguridad_vial",
        "Pilotos por la Seguridad Vial",
        "",
        "",
        "",
        146132,
        "",
        "",
        "manual",
    ]
    rows.append({"values": [_value_cell(v) for v in pilotos]})
    row_0based += 1

    # Métricas hermanas *_acumulado: NO generan fila propia. Su único valor
    # (clave "value") se fusiona en la fila de la métrica base, que pasa a
    # fuente mixta "postgres + mysql". Sin la base, la hermana solo aporta
    # su valor (nadie lo consume) y no se escribe fila alguna.
    sibling_values: dict[str, object] = {}
    for m in manifests:
        key = str(m.metric_id)
        if key.endswith(SLIDE4_ACUMULADO_SUFFIX) and m.rows:
            sibling_values[key[: -len(SLIDE4_ACUMULADO_SUFFIX)]] = dict(
                m.rows[0]
            ).get("value", "")

    for m in manifests:
        if not m.rows:
            continue
        key = str(m.metric_id)
        # Las hermanas *_acumulado ya se absorbieron en su base; si no hay
        # base en el bundle no se escribe fila para la hermana.
        if key.endswith(SLIDE4_ACUMULADO_SUFFIX):
            continue
        data = dict(m.rows[0])
        has_sibling = key in sibling_values
        source_label = (
            SLIDE4_FUENTE_MIXTA
            if has_sibling
            else (
                SLIDE4_FUENTE_MYSQL
                if m.db_source == "mysql"
                else SLIDE4_FUENTE_POSTGRES
            )
        )
        # Shape de ventanas fijas: la query devuelve las 4 columnas de
        # ventana (2025/sep2026/dic2026/acumulado). Escribirlas todas con
        # los períodos fijos y la fuente del manifest. El acumulado, si la
        # base tiene hermana *_acumulado, llega de la hermana (MySQL), no
        # de la propia query.
        if "2025" in data:
            sep2026_raw = data.get("sep2026", "")
            # dic2026 es proyección lineal del total anual sobre el
            # acumulado real sep2026 (mismo patrón que slide3): la query
            # devuelve 0 como placeholder; el sheet repo calcula el valor
            # final con _project_dic2026 sobre sep2026.
            dic2026 = (
                _project_dic2026(int(sep2026_raw)) if str(sep2026_raw) else ""
            )
            cells = [
                _value_cell(key),
                _value_cell(_slide4_label(key)),
                _value_cell(data.get("2025", "")),
                _value_cell(sep2026_raw),
                _value_cell(dic2026),
                _value_cell(
                    sibling_values[key]
                    if has_sibling
                    else data.get("acumulado", "")
                ),
                _value_cell(SLIDE4_PERIODO_INICIO),
                _value_cell(SLIDE4_PERIODO_FIN),
                _value_cell(source_label),
            ]
        else:
            # Fallback single-value: la query devuelve UN solo valor
            # acumulado sin ventanas fijas. Escribir ese valor solo en la
            # columna "Acumulado sep2026", dejar 2025/sep2026/dic2026
            # vacías, usar los períodos de la fila y la fuente del
            # manifest.
            cells = [
                _value_cell(key),
                _value_cell(_slide4_label(key)),
                _value_cell(""),
                _value_cell(""),
                _value_cell(""),
                _value_cell(data.get("value", "")),
                _value_cell(data.get("periodo_inicio", "")),
                _value_cell(data.get("periodo_fin", "")),
                _value_cell(source_label),
            ]
        rows.append({"values": cells})
        row_0based += 1

    return rows, row_0based


def _build_slide7_block(row_0based: int) -> tuple[list[dict], int]:
    """Bloque slide 7: grilla de plataformas de educación y empleo.

    6 columnas (Categoría, Programa, Usuarios, Período inicio, Período fin,
    Fuente). Bloque FIJO: las 6 plataformas se escriben siempre con los
    valores aprobados tal cual de la presentación (definición = columna
    acumulada de slide 3). No recibe manifests: ningún valor de esta grilla
    proviene del pipeline. Períodos vacíos y fuente 'manual' para todas las
    filas. Sin fila TOTAL: el =SUM no tiene sentido entre plataformas
    distintas.
    """
    rows: list[dict] = []
    rows.append(_text_row(SLIDE7_TABLE_HEADERS))
    row_0based += 1
    for metric_id, programa, usuarios in SLIDE7_ROWS:
        cells = [
            _value_cell(metric_id),
            _value_cell(programa),
            _value_cell(usuarios),
            _value_cell(""),
            _value_cell(""),
            _value_cell("slide3"),
        ]
        rows.append({"values": cells})
        row_0based += 1
    return rows, row_0based


def _build_slide8_block(row_0based: int) -> tuple[list[dict], int]:
    """Bloque slide 8: grilla de plataformas de educación y divulgación.

    6 columnas (Categoría, Programa, Usuarios, Período inicio, Período fin,
    Fuente). Bloque FIJO: las 8 plataformas se escriben siempre con los
    valores aprobados tal cual de la presentación (definición = columna
    acumulada de slide 4). No recibe manifests: ningún valor de esta grilla
    proviene del pipeline. Períodos vacíos y fuente 'manual' para todas las
    filas. Sin fila TOTAL.
    """
    rows: list[dict] = []
    rows.append(_text_row(SLIDE8_TABLE_HEADERS))
    row_0based += 1
    for metric_id, programa, usuarios, fuente in SLIDE8_ROWS:
        cells = [
            _value_cell(metric_id),
            _value_cell(programa),
            _value_cell(usuarios),
            _value_cell(""),
            _value_cell(""),
            _value_cell(fuente),
        ]
        rows.append({"values": cells})
        row_0based += 1
    return rows, row_0based


def _build_slide13_block(
    manifests: Sequence[SourceManifest], row_0based: int
) -> tuple[list[dict], int]:
    """Bloque slide 13: tarjeta de KPIs de "Formación en Centros
    Penitenciarios".

    6 columnas (Categoría, Métrica, Valor, Período inicio, Período fin,
    Fuente). 4 KPIs (Inscripciones totales, Certificados, Usuarios
    registrados, Cursos ofertados) se extraen de los manifests del
    catálogo con prefijo `slide13_` (4 métricas en
    `data/catalogo-metricas.yaml`); 1 KPI (Centros) queda hardcoded
    porque no tiene query natural (es la cantidad de penitenciarías
    físicas, no de brands ni de cursos).

    Cada manifest de slide13_* devuelve 1 fila con `value` numérico.
    Resolvemos el valor buscando por metric_id en un dict; si falta
    alguno, levantamos ValueError para no escribir un bloque parcial
    silenciosamente.

    Sin fila TOTAL: cada métrica es independiente (no suman entre sí).
    La columna Categoría lleva SLIDE13_METRIC_ID en todas las filas,
    misma nomenclatura que slide12_rutas_aprendizaje y
    slide1_alimentos (categoría = a qué slide pertenece la fila).

    Las 4 KPIs del pipeline llevan "Acumulado" / "2026-08-01" /
    "inscription" como Período inicio / Período fin / Fuente (la query
    ataca `capacitate_analisis.inscription` en MySQL). El KPI Centros
    hardcoded lleva "2026-08-01" / "2026-08-01" / "manual" porque no
    tiene query — es un dato aprobado de la presentación.
    """
    # Indexar los manifests de slide13 por key → value de su primera fila
    by_key: dict[str, object] = {}
    for m in manifests:
        key = str(m.metric_id)
        if not key.startswith("slide13"):
            continue
        if not m.rows:
            raise ValueError(
                f"Manifest {key} sin filas — slide 13 requiere 1 fila "
                f"con 'value' numérico"
            )
        by_key[key] = m.rows[0].get("value")

    rows: list[dict] = []
    rows.append(_text_row(SLIDE13_TABLE_HEADERS))
    row_0based += 1

    # Plan: (etiqueta legible, valor, periodo_inicio, periodo_fin, fuente).
    # Las 4 KPIs desde pipeline comparten Período/Fuente. Centros usa
    # fecha fija y fuente manual porque es hardcoded (sin query).
    plan: list[tuple[str, object, str, str, str]] = [
        (
            "Inscripciones totales",
            by_key["slide13_penitenciarios_inscripciones"],
            SLIDE13_PERIODO_INICIO,
            SLIDE13_PERIODO_FIN,
            SLIDE13_FUENTE_INSCRIPCION,
        ),
        (
            "Certificados",
            by_key["slide13_penitenciarios_certificados"],
            SLIDE13_PERIODO_INICIO,
            SLIDE13_PERIODO_FIN,
            SLIDE13_FUENTE_INSCRIPCION,
        ),
        (
            "Usuarios registrados",
            by_key["slide13_penitenciarios_usuarios_registrados"],
            SLIDE13_PERIODO_INICIO,
            SLIDE13_PERIODO_FIN,
            SLIDE13_FUENTE_INSCRIPCION,
        ),
        (
            "Cursos ofertados",
            by_key["slide13_penitenciarios_cursos_ofertados"],
            SLIDE13_PERIODO_INICIO,
            SLIDE13_PERIODO_FIN,
            SLIDE13_FUENTE_INSCRIPCION,
        ),
        (
            "Centros",
            SLIDE13_CENTROS,
            SLIDE13_PERIODO_FIN,  # hardcoded — sin query
            SLIDE13_PERIODO_FIN,
            "manual",
        ),
    ]
    for metrica, valor, periodo_inicio, periodo_fin, fuente in plan:
        cells = [
            _value_cell(SLIDE13_METRIC_ID),
            _value_cell(metrica),
            _value_cell(valor),
            _value_cell(periodo_inicio),
            _value_cell(periodo_fin),
            _value_cell(fuente),
        ]
        rows.append({"values": cells})
        row_0based += 1
    return rows, row_0based


def _build_slide15_block(
    manifests: Sequence[SourceManifest], row_0based: int
) -> tuple[list[dict], int]:
    """Bloque slide 15: tarjeta de KPIs de "Mario Molina Premio Nobel".

    6 columnas (Categoría, Métrica, Valor, Período inicio, Período fin,
    Fuente). 2 KPIs (Inscripciones a cursos, Consultas a la sección) se
    extraen de los manifests del catálogo con prefijo `slide15_`
    (2 métricas en `data/catalogo-metricas.yaml`).

    Cada manifest de slide15_* devuelve 1 fila con `value` numérico.
    Resolvemos el valor buscando por metric_id en un dict; si falta
    alguno, levantamos KeyError para no escribir un bloque parcial
    silenciosamente.

    Sin fila TOTAL: cada métrica es independiente. La columna Categoría
    lleva SLIDE15_METRIC_ID en todas las filas, misma nomenclatura que
    slide12_rutas_aprendizaje, slide1_alimentos y slide13_penitenciarios.
    """
    # Indexar los manifests de slide15 por key → value de su primera fila
    by_key: dict[str, object] = {}
    for m in manifests:
        key = str(m.metric_id)
        if not key.startswith("slide15"):
            continue
        if not m.rows:
            raise ValueError(
                f"Manifest {key} sin filas — slide 15 requiere 1 fila "
                f"con 'value' numérico"
            )
        by_key[key] = m.rows[0].get("value")

    rows: list[dict] = []
    rows.append(_text_row(SLIDE15_TABLE_HEADERS))
    row_0based += 1

    # Plan: (etiqueta legible, valor, periodo_inicio, periodo_fin, fuente).
    # Inscripciones: la query ataca capacitate_analisis.inscription.
    # Vistas: la query ataca capacitate_analisis.userresource (suma
    # de count agregado por recurso).
    plan: list[tuple[str, object, str, str, str]] = [
        (
            "Inscripciones a cursos",
            by_key["slide15_mario_molina_inscripciones"],
            SLIDE15_PERIODO_INICIO,
            SLIDE15_PERIODO_FIN,
            SLIDE15_FUENTE_INSCRIPCION,
        ),
        (
            "Consultas a la sección",
            by_key["slide15_mario_molina_vistas"],
            SLIDE15_PERIODO_INICIO,
            SLIDE15_PERIODO_FIN,
            SLIDE15_FUENTE_USERRESOURCE,
        ),
    ]
    for metrica, valor, periodo_inicio, periodo_fin, fuente in plan:
        cells = [
            _value_cell(SLIDE15_METRIC_ID),
            _value_cell(metrica),
            _value_cell(valor),
            _value_cell(periodo_inicio),
            _value_cell(periodo_fin),
            _value_cell(fuente),
        ]
        rows.append({"values": cells})
        row_0based += 1
    return rows, row_0based


def _build_slide19_block(
    manifests: Sequence[SourceManifest], row_0based: int
) -> tuple[list[dict], int]:
    """Bloque slide 19: tarjeta de KPIs de "Pilotos por la seguridad
    vial / Aprende de seguridad vial".

    6 columnas (Categoría, Métrica, Valor, Período inicio, Período
    fin, Fuente). 4 KPIs (Inscripciones, Personas únicas inscritas,
    Certificados, Personas certificadas únicas) se extraen de los
    manifests del catálogo con prefijo `slide19_` (4 métricas en
    `data/catalogo-metricas.yaml` con la lista de 16 cursos de
    seguridad vial del archivo Consultas_consejo_panel.sql). 1 KPI
    (Cursos: 16) queda hardcoded porque la lista de cursos la define
    el panel SQL, no un COUNT.

    Cada manifest de slide19_* devuelve 1 fila con `value` numérico.
    Resolvemos el valor buscando por metric_id en un dict; si falta
    alguno, levantamos KeyError para no escribir un bloque parcial
    silenciosamente.

    Sin fila TOTAL: cada métrica es independiente. La columna Categoría
    lleva SLIDE19_METRIC_ID en todas las filas, misma nomenclatura que
    slide12/13/15.
    """
    by_key: dict[str, object] = {}
    for m in manifests:
        key = str(m.metric_id)
        if not key.startswith("slide19"):
            continue
        if not m.rows:
            raise ValueError(
                f"Manifest {key} sin filas — slide 19 requiere 1 fila "
                f"con 'value' numérico"
            )
        by_key[key] = m.rows[0].get("value")

    rows: list[dict] = []
    rows.append(_text_row(SLIDE19_TABLE_HEADERS))
    row_0based += 1

    # Plan: (etiqueta legible, valor, periodo_inicio, periodo_fin,
    # fuente). 4 KPIs vienen de queries en analisis_cpe_db (PG);
    # Cursos=16 queda hardcoded (lista de cursos del panel SQL).
    plan: list[tuple[str, object, str, str, str]] = [
        (
            "Cursos",
            SLIDE19_CURSOS_TOTAL,
            SLIDE19_PERIODO_FIN,  # hardcoded
            SLIDE19_PERIODO_FIN,
            "manual",
        ),
        (
            "Inscripciones a cursos",
            by_key["slide19_seguridad_vial_inscripciones"],
            SLIDE19_PERIODO_INICIO,
            SLIDE19_PERIODO_FIN,
            SLIDE19_FUENTE_INSCRIPCION,
        ),
        (
            "Personas únicas inscritas",
            by_key["slide19_seguridad_vial_personas_unicas_inscritas"],
            SLIDE19_PERIODO_INICIO,
            SLIDE19_PERIODO_FIN,
            SLIDE19_FUENTE_INSCRIPCION,
        ),
        (
            "Certificados",
            by_key["slide19_seguridad_vial_certificados"],
            SLIDE19_PERIODO_INICIO,
            SLIDE19_PERIODO_FIN,
            SLIDE19_FUENTE_INSCRIPCION,
        ),
        (
            "Personas certificadas únicas",
            by_key["slide19_seguridad_vial_personas_certificadas_unicas"],
            SLIDE19_PERIODO_INICIO,
            SLIDE19_PERIODO_FIN,
            SLIDE19_FUENTE_INSCRIPCION,
        ),
    ]
    for metrica, valor, periodo_inicio, periodo_fin, fuente in plan:
        cells = [
            _value_cell(SLIDE19_METRIC_ID),
            _value_cell(metrica),
            _value_cell(valor),
            _value_cell(periodo_inicio),
            _value_cell(periodo_fin),
            _value_cell(fuente),
        ]
        rows.append({"values": cells})
        row_0based += 1
    return rows, row_0based


def _build_slide20_block(
    manifests: Sequence[SourceManifest], row_0based: int
) -> tuple[list[dict], int]:
    """Bloque slide 20: tarjeta de KPIs de "Crecimiento integral".

    6 columnas (Categoría, Métrica, Valor, Período inicio, Período
    fin, Fuente). 2 KPIs (Inscripciones a cursos, Personas únicas
    inscritas) se extraen de los manifests del catálogo con prefijo
    `slide20_` (2 métricas en `data/catalogo-metricas.yaml` con la
    lista de 78 cursos de crecimiento integral del archivo
    Consultas_consejo_panel.sql y filtro cross-pollination
    `c.platformId = 1 AND du.plataformaId = 2`).

    Cada manifest de slide20_* devuelve 1 fila con `value` numérico.
    Resolvemos el valor buscando por metric_id en un dict; si falta
    alguno, levantamos KeyError para no escribir un bloque parcial
    silenciosamente.

    Sin fila TOTAL: cada métrica es independiente. La columna Categoría
    lleva SLIDE20_METRIC_ID en todas las filas, misma nomenclatura que
    slide12/13/15/19.
    """
    by_key: dict[str, object] = {}
    for m in manifests:
        key = str(m.metric_id)
        if not key.startswith("slide20"):
            continue
        if not m.rows:
            raise ValueError(
                f"Manifest {key} sin filas — slide 20 requiere 1 fila "
                f"con 'value' numérico"
            )
        by_key[key] = m.rows[0].get("value")

    rows: list[dict] = []
    rows.append(_text_row(SLIDE20_TABLE_HEADERS))
    row_0based += 1

    # Plan: (etiqueta legible, valor, periodo_inicio, periodo_fin,
    # fuente). 2 KPIs desde `analisis_cpe_db` PostgreSQL con filtro
    # cross-pollination (cursos CPE × usuarios Aprende).
    plan: list[tuple[str, object, str, str, str]] = [
        (
            "Inscripciones a cursos",
            by_key["slide20_crecimiento_integral_inscripciones"],
            SLIDE20_PERIODO_INICIO,
            SLIDE20_PERIODO_FIN,
            SLIDE20_FUENTE_INSCRIPCION,
        ),
        (
            "Personas únicas inscritas",
            by_key["slide20_crecimiento_integral_personas_unicas_inscritas"],
            SLIDE20_PERIODO_INICIO,
            SLIDE20_PERIODO_FIN,
            SLIDE20_FUENTE_INSCRIPCION,
        ),
    ]
    for metrica, valor, periodo_inicio, periodo_fin, fuente in plan:
        cells = [
            _value_cell(SLIDE20_METRIC_ID),
            _value_cell(metrica),
            _value_cell(valor),
            _value_cell(periodo_inicio),
            _value_cell(periodo_fin),
            _value_cell(fuente),
        ]
        rows.append({"values": cells})
        row_0based += 1
    return rows, row_0based


def _catalog_index(catalogo: Sequence[Metric]) -> dict[str, Metric]:
    """Índice key -> Metric para resolver nombre y plataformas por metric_id."""
    return {m.key: m for m in catalogo}


def _is_slide_metric(manifest: SourceManifest) -> bool:
    """True si el manifest pertenece a una slide del reporte."""
    key = str(manifest.metric_id)
    return key.startswith("slide") and key != "slide_naming"


# ── Selección de valor para el Reporte ───────────────────────────────────────


def _select_reporte_value(row: Mapping[str, Any]) -> int | float | Decimal | None:
    """Selecciona el valor representativo de una fila para el Reporte.

    Prioriza la ventana observada más reciente (sep2026) sobre 'value'
    y sobre el primer valor numérico. Acepta Decimal porque las
    agregaciones de MySQL (SUM) devuelven Decimal.
    """
    for key in ("sep2026", "value"):
        v = row.get(key)
        if isinstance(v, (int, float, Decimal)) and not isinstance(v, bool):
            return v
    for v in row.values():
        if isinstance(v, (int, float, Decimal)) and not isinstance(v, bool):
            return v
    return None


def _build_reporte_requests(
    bundle: Bundle,
    existing: set[str],
    sheet_ids: dict[str, int],
    catalogo: Sequence[Metric],
) -> list[dict]:
    """Construye requests para la hoja Reporte (tablas ejecutivas).

    Solo se listan las métricas de slides del catálogo (prefix 'slide'),
    excluyendo slide_naming. Al generarse una nueva slide se agrega una
    fila; si ya existe, solo se actualizan sus valores.
    """
    sheet_id = sheet_ids["Reporte"]
    clear = _clear_sheet_if_exists("Reporte", existing, sheet_id)
    by_key = _catalog_index(catalogo)

    rows_data = [
        {"values": [
            {"userEnteredValue": {"stringValue": "Métrica"}},
            {"userEnteredValue": {"stringValue": "Valor"}},
            {"userEnteredValue": {"stringValue": "Tipo"}},
        ]}
    ]

    slide_manifests = [m for m in bundle.manifests if _is_slide_metric(m)]

    for m in slide_manifests:
        is_manual = m.source.value == "manual"
        tipo = "Manual" if is_manual else "Real"
        val_str = "— (manual, sin valor)"
        if m.status.value == "extracted" and m.rows:
            val = _select_reporte_value(m.rows[0])
            if val is not None:
                val_str = f"{int(val):,}"
        elif m.status.value == "empty" and not is_manual:
            val_str = f"Vacío ({m.status.value})"

        metric = by_key.get(str(m.metric_id))
        nombre = metric.name if metric is not None else str(m.metric_id)

        rows_data.append({
            "values": [
                {"userEnteredValue": {"stringValue": nombre}},
                {"userEnteredValue": {"stringValue": val_str}},
                {"userEnteredValue": {"stringValue": tipo}},
            ]
        })

    return clear + [
        {
            "updateCells": {
                "start": {
                    "sheetId": sheet_id,
                    "rowIndex": 0,
                    "columnIndex": 0,
                },
                "rows": rows_data,
                "fields": "userEnteredValue",
            }
        }
    ]


def _build_errores_requests(
    dqs_issues: tuple[DqsIssue, ...] | list[DqsIssue],
    existing: set[str],
    sheet_ids: dict[str, int],
) -> list[dict]:
    """Construye requests para la hoja Errores (DQS issues sanitizados)."""
    sheet_id = sheet_ids["Errores"]
    clear = _clear_sheet_if_exists("Errores", existing, sheet_id)

    rows_data = [
        {"values": [
            {"userEnteredValue": {"stringValue": "Código"}},
            {"userEnteredValue": {"stringValue": "Severidad"}},
            {"userEnteredValue": {"stringValue": "Mensaje"}},
        ]}
    ]

    for issue in dqs_issues:
        rows_data.append({
            "values": [
                {"userEnteredValue": {"stringValue": issue.code}},
                {"userEnteredValue": {"stringValue": issue.severity}},
                {"userEnteredValue": {
                    "stringValue": _sanitize(issue.message)
                }},
            ]
        })

    return clear + [
        {
            "updateCells": {
                "start": {
                    "sheetId": sheet_id,
                    "rowIndex": 0,
                    "columnIndex": 0,
                },
                "rows": rows_data,
                "fields": "userEnteredValue",
            }
        }
    ]


def _build_config_requests(
    bundle: Bundle,
    existing: set[str],
    sheet_ids: dict[str, int],
    catalogo: Sequence[Metric],
) -> list[dict]:
    """Construye requests para la hoja Configuracion.

    Solo se listan las métricas de slides del catálogo (prefix 'slide'),
    excluyendo slide_naming. Al generarse una nueva slide se agrega una
    fila; si ya existe, solo se actualizan sus datos.
    """
    sheet_id = sheet_ids["Configuracion"]
    clear = _clear_sheet_if_exists("Configuracion", existing, sheet_id)
    by_key = _catalog_index(catalogo)

    rows_data = [
        {"values": [
            {"userEnteredValue": {"stringValue": "Key"}},
            {"userEnteredValue": {"stringValue": "Nombre"}},
            {"userEnteredValue": {"stringValue": "Fuente"}},
            {"userEnteredValue": {"stringValue": "Plataformas"}},
        ]}
    ]

    slide_manifests = [m for m in bundle.manifests if _is_slide_metric(m)]

    for m in slide_manifests:
        metric = by_key.get(str(m.metric_id))
        nombre = metric.name if metric is not None else str(m.metric_id)
        plataformas = (
            ", ".join(metric.platform_scope)
            if metric is not None
            else ""
        )

        rows_data.append({
            "values": [
                {"userEnteredValue": {"stringValue": str(m.metric_id)}},
                {"userEnteredValue": {"stringValue": nombre}},
                {"userEnteredValue": {"stringValue": m.source.value}},
                {"userEnteredValue": {"stringValue": plataformas}},
            ]
        })

    return clear + [
        {
            "updateCells": {
                "start": {
                    "sheetId": sheet_id,
                    "rowIndex": 0,
                    "columnIndex": 0,
                },
                "rows": rows_data,
                "fields": "userEnteredValue",
            }
        }
    ]


# ── Helpers de Sheets API ───────────────────────────────────────────────────


def _clear_sheet_if_exists(
    name: str, existing: set[str], sheet_id: int
) -> list[dict]:
    """Limpia por completo el contenido de la hoja si ya existe.

    Borra el grid entero (hasta 1000 filas x max_cols) con repeatCell para
    evitar que queden restos de contenido previo más alto que el nuevo
    (un updateCells dirigido a fila 0 no borra filas más allá).
    """
    if name not in existing:
        return []

    max_cols = {
        "Control": 2,
        "Datos": 8,
        "Reporte": 3,
        "Errores": 3,
        "Configuracion": 4,
    }
    cols = max_cols.get(name, 5)
    return [
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1000,
                    "startColumnIndex": 0,
                    "endColumnIndex": cols,
                },
                "cell": {"userEnteredValue": {"stringValue": ""}},
                "fields": "userEnteredValue",
            }
        }
    ]


def _sanitize(message: str) -> str:
    """Remueve posibles secretos de un mensaje de error."""
    import os
    sanitized = message
    for var in ["DB_PASSWORD", "DB_HOST", "DB_USER", "DB_NAME"]:
        val = os.environ.get(var, "")
        if val and len(val) > 2:
            sanitized = sanitized.replace(val, "***")
    return sanitized
