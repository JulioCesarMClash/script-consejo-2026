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
from typing import Any

from src.consejo.application.ports import SheetRepo
from src.consejo.domain.entities import Bundle, DqsIssue, SourceManifest

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
        self._next_id: int = 2  # id=1 es initialize

    def snapshot(self, bundle: Bundle, spreadsheet_id: str) -> str:
        """Crea o actualiza las 5 hojas del snapshot.

        Args:
            bundle: Bundle canónico validado.
            spreadsheet_id: ID del spreadsheet destino.

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
            if existing and "fields" in existing:
                fields = existing["fields"]
                if "sheets" in fields:
                    for s in fields["sheets"]:
                        title = (
                            s.get("properties", {}).get("title", "")
                        )
                        if title:
                            existing_sheets.add(title)

            requests: list[dict] = []

            # Crear hojas faltantes
            for name in SHEET_NAMES:
                if name not in existing_sheets:
                    requests.append(
                        {
                            "addSheet": {
                                "properties": {"title": name}
                            }
                        }
                    )

            # Poblar contenido
            requests.extend(
                _build_control_requests(bundle, existing_sheets)
            )
            requests.extend(
                _build_datos_requests(bundle, existing_sheets)
            )
            requests.extend(
                _build_reporte_requests(bundle, existing_sheets)
            )
            requests.extend(
                _build_errores_requests(bundle.dqs, existing_sheets)
            )
            requests.extend(
                _build_config_requests(bundle, existing_sheets)
            )

            if requests:
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
        self._rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "consejo-2026-snapshot", "version": "0.1.0"},
        })
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
    bundle: Bundle, existing: set[str]
) -> list[dict]:
    """Construye requests para la hoja Control."""
    sheet_id = _sheet_id_for("Control")
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
    bundle: Bundle, existing: set[str]
) -> list[dict]:
    """Construye requests para la hoja Datos (append inmutable)."""
    sheet_id = _sheet_id_for("Datos")
    clear = _clear_sheet_if_exists("Datos", existing, sheet_id)

    if not bundle.rows:
        headers_row = {
            "values": [
                {"userEnteredValue": {"stringValue": "metric_id"}},
                {"userEnteredValue": {"stringValue": "source"}},
                {"userEnteredValue": {"stringValue": "value"}},
            ]
        }
        return clear + [
            {
                "updateCells": {
                    "start": {
                        "sheetId": sheet_id,
                        "rowIndex": 0,
                        "columnIndex": 0,
                    },
                    "rows": [headers_row],
                    "fields": "userEnteredValue",
                }
            }
        ]

    rows_data = [
        {
            "values": [
                {"userEnteredValue": {"stringValue": "metric_id"}},
                {"userEnteredValue": {"stringValue": "source"}},
                {"userEnteredValue": {"stringValue": "value"}},
            ]
        }
    ]

    for row in bundle.rows:
        metric_id = str(row.get("metric_id", ""))
        source = str(row.get("source", ""))
        val = row.get("value") or row.get("count") or ""
        if isinstance(val, (int, float)):
            cell = {"userEnteredValue": {"numberValue": float(val)}}
        else:
            cell = {"userEnteredValue": {"stringValue": str(val)}}
        rows_data.append({
            "values": [
                {"userEnteredValue": {"stringValue": metric_id}},
                {"userEnteredValue": {"stringValue": source}},
                cell,
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


def _build_reporte_requests(
    bundle: Bundle, existing: set[str]
) -> list[dict]:
    """Construye requests para la hoja Reporte (tablas ejecutivas)."""
    sheet_id = _sheet_id_for("Reporte")
    clear = _clear_sheet_if_exists("Reporte", existing, sheet_id)

    rows_data = [
        {"values": [
            {"userEnteredValue": {"stringValue": "Métrica"}},
            {"userEnteredValue": {"stringValue": "Valor"}},
            {"userEnteredValue": {"stringValue": "Tipo"}},
        ]}
    ]

    for m in bundle.manifests:
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

        rows_data.append({
            "values": [
                {"userEnteredValue": {"stringValue": str(m.metric_id)}},
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
) -> list[dict]:
    """Construye requests para la hoja Errores (DQS issues sanitizados)."""
    sheet_id = _sheet_id_for("Errores")
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
    bundle: Bundle, existing: set[str]
) -> list[dict]:
    """Construye requests para la hoja Configuracion."""
    sheet_id = _sheet_id_for("Configuracion")
    clear = _clear_sheet_if_exists("Configuracion", existing, sheet_id)

    rows_data = [
        {"values": [
            {"userEnteredValue": {"stringValue": "Key"}},
            {"userEnteredValue": {"stringValue": "Nombre"}},
            {"userEnteredValue": {"stringValue": "Fuente"}},
            {"userEnteredValue": {"stringValue": "Plataformas"}},
        ]}
    ]

    for m in bundle.manifests:
        rows_data.append({
            "values": [
                {"userEnteredValue": {"stringValue": str(m.metric_id)}},
                {"userEnteredValue": {
                    "stringValue": str(m.metric_id)
                }},
                {"userEnteredValue": {"stringValue": m.source.value}},
                {"userEnteredValue": {"stringValue": ""}},
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


def _sheet_id_for(name: str) -> int:
    """Sheet ID determinístico basado en el nombre de la hoja."""
    ids = {
        "Control": 0,
        "Datos": 1,
        "Reporte": 2,
        "Errores": 3,
        "Configuracion": 4,
    }
    return ids.get(name, 100)


def _clear_sheet_if_exists(
    name: str, existing: set[str], sheet_id: int
) -> list[dict]:
    """Limpia el contenido de la hoja si ya existe."""
    if name not in existing:
        return []

    max_cols = {
        "Control": 2,
        "Datos": 3,
        "Reporte": 3,
        "Errores": 3,
        "Configuracion": 4,
    }
    cols = max_cols.get(name, 5)
    return [
        {
            "updateCells": {
                "start": {
                    "sheetId": sheet_id,
                    "rowIndex": 0,
                    "columnIndex": 0,
                },
                "rows": [
                    {"values": [
                        {"userEnteredValue": {"stringValue": ""}}
                        for _ in range(cols)
                    ]}
                ],
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
