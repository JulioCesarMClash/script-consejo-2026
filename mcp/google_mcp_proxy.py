#!/usr/bin/env python3
"""
Google MCP Proxy — stdio MCP server para Google Slides & Sheets.
Usa la REST API directa con service account, evitando el server MCP oficial
de Google que no soporta service accounts.
"""

import json
import sys
import os
import time
import re
from pathlib import Path
from google.oauth2 import service_account
from google.auth.transport.requests import Request

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent

SCOPES = [
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_creds = None
_creds_expiry = 0


def _get_creds():
    global _creds, _creds_expiry
    now = time.time()
    if _creds and now < _creds_expiry - 60:
        return _creds

    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not key_path:
        for f in PROJECT_DIR.glob("script-consejo-2026-gcp-*.json"):
            key_path = str(f)
            break
    if not key_path or not Path(key_path).exists():
        raise RuntimeError("Service account key not found")

    _creds = service_account.Credentials.from_service_account_file(
        key_path, scopes=SCOPES
    )
    _creds.refresh(Request())
    _creds_expiry = now + 3500
    return _creds


def _api_call(service, method, params=None, body=None):
    """Make a REST API call to Google APIs."""
    import urllib.request

    creds = _get_creds()
    base = {
        "slides": "https://slides.googleapis.com/v1",
        "sheets": "https://sheets.googleapis.com/v4",
    }[service]

    url = f"{base}/{method}"
    if params:
        qs = "&".join(f"{k}={urllib.request.quote(str(v))}" for k, v in params.items())
        url += "?" + qs

    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {creds.token}",
        },
    )
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        try:
            err_json = json.loads(err_body)
            msg = err_json.get("error", {}).get("message", e.reason)
        except json.JSONDecodeError:
            msg = err_body[:200]
        return {"error": f"HTTP {e.code}: {msg}"}


# ── Tool definitions ────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "read_presentation",
        "description": "Lee una presentación de Google Slides y devuelve su contenido completo (slides, pageElements, text).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "presentationId": {"type": "string", "description": "ID de la presentación (de la URL: /d/PRESENTATION_ID/edit)"}
            },
            "required": ["presentationId"],
        },
    },
    {
        "name": "update_presentation",
        "description": "Actualiza una presentación con batch updates (replaceAllText, insertText, createShape, etc).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "presentationId": {"type": "string", "description": "ID de la presentación"},
                "requests": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Lista de requests batchUpdate (formato REST API)",
                },
            },
            "required": ["presentationId", "requests"],
        },
    },
    {
        "name": "get_values",
        "description": "Lee valores de un rango en una hoja de Google Sheets.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spreadsheetId": {"type": "string", "description": "ID del spreadsheet"},
                "range": {"type": "string", "description": "Rango en notación A1 (ej: 'Sheet1!A1:D10')"},
            },
            "required": ["spreadsheetId", "range"],
        },
    },
    {
        "name": "get_spreadsheet",
        "description": "Obtiene metadatos de un spreadsheet (sheets, propiedades, rangos con nombres).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spreadsheetId": {"type": "string", "description": "ID del spreadsheet"},
                "includeGridData": {"type": "boolean", "description": "Incluir datos de celdas"},
            },
            "required": ["spreadsheetId"],
        },
    },
    {
        "name": "update_sheet",
        "description": "Actualiza celdas en un spreadsheet. Envía un batchUpdate con los requests especificados.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spreadsheetId": {"type": "string", "description": "ID del spreadsheet"},
                "requests": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Lista de requests batchUpdate (formato REST API de Sheets)",
                },
            },
            "required": ["spreadsheetId", "requests"],
        },
    },
]


def handle_request(req: dict) -> dict | None:
    method = req.get("method")
    rid = req.get("id", 0)

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": rid,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}, "resources": {}},
                "serverInfo": {"name": "google-workspace-mcp", "version": "1.0.0"},
            },
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}

    if method == "resources/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"resources": []}}

    if method == "tools/call":
        params = req.get("params", {})
        tool = params.get("name")
        args = params.get("arguments", {})

        try:
            result = _execute_tool(tool, args)
            if "error" in result:
                return {
                    "jsonrpc": "2.0", "id": rid,
                    "error": {"code": -32000, "message": result["error"]},
                }
            return {"jsonrpc": "2.0", "id": rid, "result": result}
        except Exception as e:
            return {
                "jsonrpc": "2.0", "id": rid,
                "error": {"code": -32000, "message": str(e)},
            }

    return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


def _execute_tool(tool: str, args: dict) -> dict:
    if tool == "read_presentation":
        pres = _api_call("slides", f"presentations/{args['presentationId']}")
        return {"content": json.dumps(pres, ensure_ascii=False)}

    if tool == "update_presentation":
        result = _api_call(
            "slides",
            f"presentations/{args['presentationId']}:batchUpdate",
            body={"requests": args["requests"]},
        )
        return {"replies": result.get("replies", [])}

    if tool == "get_values":
        sid = args["spreadsheetId"]
        rng = args["range"]
        result = _api_call("sheets", f"spreadsheets/{sid}/values/{urllib.request.quote(rng)}")
        return {
            "range": result.get("range", rng),
            "values": result.get("values", []),
        }

    if tool == "get_spreadsheet":
        sid = args["spreadsheetId"]
        params = {"includeGridData": "true"} if args.get("includeGridData") else {}
        result = _api_call("sheets", f"spreadsheets/{sid}", params=params)
        return {"fields": result}

    if tool == "update_sheet":
        result = _api_call(
            "sheets",
            f"spreadsheets/{args['spreadsheetId']}:batchUpdate",
            body={"requests": args["requests"]},
        )
        return result

    return {"error": f"Unknown tool: {tool}"}


def main():
    # Send initialize response
    init_resp = handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    sys.stdout.write(json.dumps(init_resp) + "\n")
    sys.stdout.flush()

    # Read and process requests from stdin
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue

        response = handle_request(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    import urllib.request
    main()
