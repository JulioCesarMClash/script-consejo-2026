"""Adaptador de Google Sheets vía proxy MCP por stdio.

Comunica con mcp/google_mcp_proxy.py mediante JSON-RPC por stdin/stdout.
Usa shell=False y argv fijo. Solo expone get_spreadsheet + update_sheet.
Cero llamadas a Slides. Errores sanitizados sin secretos.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

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
    layout propio: slide1 (8 columnas, =SUM en B/C/D/E), slide2
    (7 columnas Categoría/Sector/Curso/Certificados/Período inicio/
    Período fin/Fuente, =SUM en D) o slide3 (9 columnas Categoría/Programa/
    2025/sep2026/dic2026/Acumulado sep2026/Período inicio/Período fin/
    Fuente, UNA tabla comparativa que agrupa todos los manifests slide3) y
    slide4 (9 columnas Categoría/Programa/2024/sep2025/dic2025/Acumulado
    sep2025/Período inicio/Período fin/Fuente, UNA tabla comparativa que
    agrupa todos los manifests slide4). Las tablas se escriben consecutivas
    separadas por una fila en blanco.
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
    single_slides = [
        m for m in slides
        if not str(m.metric_id).startswith("slide3")
        and not str(m.metric_id).startswith("slide4")
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
    "2024",
    "sep2025",
    "dic2025",
    "Acumulado sep2025",
    "Período inicio",
    "Período fin",
    "Fuente",
]

# Ventanas fijas de los valores visibles de slide 4: 2024 =
# [2024-01-01, 2025-01-01), sep2025 = [2025-01-01, 2025-10-01),
# dic2025 = [2025-01-01, 2026-01-01) y acumulado histórico < 2025-10-01
# (la fecha 2025-09-30 documenta el cierre de la ventana visible). Las
# filas slide4 de PostgreSQL no traen estos campos.
SLIDE4_PERIODO_INICIO = "2024-01-01"
SLIDE4_PERIODO_FIN = "2025-09-30"
SLIDE4_FUENTE_POSTGRES = "postgres"

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

    El layout se elige por prefijo de la key: 'slide1' usa 8 columnas
    (ver _build_slide1_block), 'slide2' usa 3 columnas Sector/Curso/
    Certificados (ver _build_slide2_block) y 'slide3' usa la tabla
    comparativa de programas (ver _build_slide3_block). Devuelve
    (rows_data_list, next_row_0based).
    """
    key = str(manifest.metric_id)
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


def _build_slide2_block(
    manifest: SourceManifest, row_0based: int
) -> tuple[list[dict], int]:
    """Bloque slide2: 7 columnas (Categoría, Sector, Curso, Certificados,
    Período inicio, Período fin, Fuente); TOTAL con =SUM en la columna
    Certificados (D). Las filas usan las keys grupo, curso, value,
    periodo_inicio, periodo_fin, source de la SQL."""
    rows: list[dict] = []
    rows.append(_text_row(SLIDE2_TABLE_HEADERS))
    header_0 = row_0based
    row_0based += 1

    for r in manifest.rows:
        rows.append(_slide2_data_row(r))
        row_0based += 1

    rows.append(_slide2_total_row(header_0, row_0based))
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


def _slide2_categoria(row: Mapping[str, object]) -> str:
    """Categoría con nomenclatura 'slide2_<sector>' donde <sector> es el
    nombre del sector normalizado (minúsculas, sin acentos, guiones bajos).

    Ejemplos:
      'Construcción y mantenimiento' -> 'slide2_construccion_y_mantenimiento'
      'Alimentos y atención'        -> 'slide2_alimentos_y_atencion'
    """
    import unicodedata
    grupo = str(row.get("grupo", "") or "")
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", grupo)
        if not unicodedata.combining(c)
    )
    normalizado = (
        sin_acentos.lower()
        .replace(" ", "_")
        .replace("-", "_")
    )
    # colapsar underscores repetidos
    while "__" in normalizado:
        normalizado = normalizado.replace("__", "_")
    return f"slide2_{normalizado}" if normalizado else "slide2"


def _slide2_data_row(row: Mapping[str, object]) -> dict:
    """Fila de datos slide2: 7 celdas.

    Categoría usa nomenclatura 'slide2_<sector>' para identificar a qué
    espacio de slide 2 pertenece la fila. El resto de las columnas se
    mapea desde el row (grupo, curso, value, periodo_inicio, periodo_fin,
    source).
    """
    values = [
        _slide2_categoria(row),
        row.get("grupo", ""),
        row.get("curso", ""),
        row.get("value", ""),
        row.get("periodo_inicio", ""),
        row.get("periodo_fin", ""),
        row.get("source", ""),
    ]
    cells = [_value_cell(v) for v in values]
    return {"values": cells}


def _slide2_total_row(header_0: int, total_0: int) -> dict:
    """Fila TOTAL slide2: 7 celdas con =SUM en columna Certificados (D)."""
    first_data_1 = header_0 + 2
    last_data_1 = total_0
    letter = chr(ord("A") + SLIDE2_SUM_COLUMN - 1)
    cells: list[dict] = [
        {"userEnteredValue": {"stringValue": "TOTAL"}},
        {"userEnteredValue": {}},
        {"userEnteredValue": {}},
        {
            "userEnteredValue": {
                "formulaValue": f"=SUM({letter}{first_data_1}:{letter}{last_data_1})"
            }
        },
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

    Fila fija "Capacitate Empleo" (manual, fuente 'manual', resto vacío)
    que SIEMPRE está presente, seguida de UNA fila por cada manifest slide3
    con filas: Categoría = metric_id tal cual (slide3_capacitate_carso ->
    "slide3_capacitate_carso"), Programa = label legible derivado de la key
    (slide3_capacitate_carso -> "Capacitate Carso") y los valores de las
    columnas de ventana fija "2025" y "sep2026". dic2026 es la proyección
    lineal del total anual (ver _project_dic2026) sobre sep2026 real.
    base_dic2026 NO se escribe. La columna Acumulado sep2026 (manual)
    queda vacía. Los períodos son las ventanas fijas 2025-01-01..2026-08-02
    y la fuente es 'mysql' (db_source de las métricas slide3 de MySQL).
    Sin fila TOTAL: el =SUM no tiene sentido entre programas distintos.
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
            _value_cell(""),
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

    9 columnas (Categoría, Programa, 2024, sep2025, dic2025, Acumulado
    sep2025, Período inicio, Período fin, Fuente) con la misma nomenclatura
    de slides 1/2/3 (metric_id 'slide4_*' en Categoría, ventanas de valor,
    período y fuente).

    Fila fija "Pilotos por la Seguridad Vial" (manual, fuente 'manual',
    resto vacío) que SIEMPRE está presente, seguida de UNA fila por cada
    manifest slide4 con filas: Categoría = metric_id tal cual
    (slide4_aprende_seguridad_vial -> "slide4_aprende_seguridad_vial"),
    Programa = label legible derivado de la key
    (slide4_aprende_seguridad_vial -> "Aprende de seguridad vial") y los
    valores de las columnas de ventana fija "2024", "sep2025", "dic2025" y
    "acumulado". Los períodos son las ventanas fijas 2024-01-01..2025-09-30
    y la fuente es 'postgres' (db_source de las métricas slide4 de
    PostgreSQL). Sin fila TOTAL: el =SUM no tiene sentido entre programas
    distintos.
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
        "",
        "",
        "",
        "manual",
    ]
    rows.append({"values": [_value_cell(v) for v in pilotos]})
    row_0based += 1

    for m in manifests:
        if not m.rows:
            continue
        data = dict(m.rows[0])
        cells = [
            _value_cell(str(m.metric_id)),
            _value_cell(_slide4_label(str(m.metric_id))),
            _value_cell(data.get("2024", "")),
            _value_cell(data.get("sep2025", "")),
            _value_cell(data.get("dic2025", "")),
            _value_cell(data.get("acumulado", "")),
            _value_cell(SLIDE4_PERIODO_INICIO),
            _value_cell(SLIDE4_PERIODO_FIN),
            _value_cell(SLIDE4_FUENTE_POSTGRES),
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
            row = m.rows[0]
            for v in row.values():
                if isinstance(v, (int, float)):
                    val_str = f"{int(v):,}"
                    break
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
