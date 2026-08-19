"""Settings del pipeline leídos de variables de entorno.

Ningún secreto se hardcodea; las variables se validan al inicio.

Variables de entorno reconocidas (todas opcionales excepto las marcadas
como requeridas en `validate()`):

PostgreSQL (requeridas para extraer):
    DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT
    DB_STATEMENT_TIMEOUT_MS, DB_LOCK_TIMEOUT_MS

MySQL (opcional, solo si alguna métrica usa `db_source: "mysql"`):
    MYSQL_HOST (default 127.0.0.1)
    MYSQL_PORT (default 8889)
    MYSQL_USER (default root)
    MYSQL_PASSWORD (default root)
    MYSQL_DATABASE (opcional; si está vacío, las queries deben usar
        prefijo `<db>.tabla` y no se selecciona DB por default al conectar)

Google:
    GOOGLE_APPLICATION_CREDENTIALS (requerida para snapshot en Sheets)
    GOOGLE_SPREADSHEET_ID (requerida para snapshot en Sheets)

Catálogo y corte:
    CATALOG_PATH, CERTIFICATE_PERIOD_START, CERTIFICATE_PERIOD_END
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


def _dotenv_values() -> dict[str, str]:
    """Lee valores simples de .env sin modificar el entorno del proceso."""
    if not ENV_FILE.is_file():
        return {}

    values: dict[str, str] = {}
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1]
        elif len(value) >= 2 and value[0] == value[-1] == "'":
            value = value[1:-1]
        values[key] = value
    return values


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, _dotenv_values().get(name, default))


def _date_env(name: str, default: str) -> date:
    return date.fromisoformat(_env(name, default))


@dataclass(frozen=True)
class Settings:
    """Configuración del pipeline desde entorno."""

    db_host: str = field(
        default_factory=lambda: _env("DB_HOST")
    )
    db_name: str = field(
        default_factory=lambda: _env("DB_NAME")
    )
    db_user: str = field(
        default_factory=lambda: _env("DB_USER")
    )
    db_password: str = field(
        default_factory=lambda: _env("DB_PASSWORD")
    )
    db_port: int = field(
        default_factory=lambda: int(_env("DB_PORT", "5432"))
    )
    db_statement_timeout_ms: int = field(
        default_factory=lambda: int(
            _env("DB_STATEMENT_TIMEOUT_MS", "300000")
        )
    )
    db_lock_timeout_ms: int = field(
        default_factory=lambda: int(_env("DB_LOCK_TIMEOUT_MS", "5000"))
    )
    mysql_host: str = field(
        default_factory=lambda: _env("MYSQL_HOST", "127.0.0.1")
    )
    mysql_port: int = field(
        default_factory=lambda: int(_env("MYSQL_PORT", "8889"))
    )
    mysql_user: str = field(
        default_factory=lambda: _env("MYSQL_USER", "root")
    )
    mysql_password: str = field(
        default_factory=lambda: _env("MYSQL_PASSWORD", "root")
    )
    mysql_database: str | None = field(
        default_factory=lambda: _env("MYSQL_DATABASE") or None
    )
    google_application_credentials: str = field(
        default_factory=lambda: _env("GOOGLE_APPLICATION_CREDENTIALS")
    )
    google_spreadsheet_id: str = field(
        default_factory=lambda: _env("GOOGLE_SPREADSHEET_ID")
    )
    catalog_path: str = field(
        default_factory=lambda: _env(
            "CATALOG_PATH",
            str(
                Path(__file__).resolve().parent.parent.parent.parent
                / "data"
                / "catalogo-metricas.yaml"
            ),
        )
    )
    certificate_period_start: date = field(
        default_factory=lambda: _date_env(
            "CERTIFICATE_PERIOD_START", "2025-09-01"
        )
    )
    certificate_period_end: date = field(
        default_factory=lambda: _date_env(
            "CERTIFICATE_PERIOD_END", "2026-08-01"
        )
    )

    def validate(self) -> None:
        """Valida que las variables requeridas estén configuradas.

        Raises:
            ValueError: Si falta alguna variable requerida, con mensaje
                sanitizado (sin exponer valores de credenciales).
        """
        missing: list[str] = []
        if not self.db_host:
            missing.append("DB_HOST")
        if not self.db_name:
            missing.append("DB_NAME")
        if not self.db_user:
            missing.append("DB_USER")
        if not self.db_password:
            missing.append("DB_PASSWORD")
        if not self.google_application_credentials:
            missing.append("GOOGLE_APPLICATION_CREDENTIALS")
        if missing:
            raise ValueError(
                "Credenciales de base de datos no configuradas. "
                f"Variables faltantes: {', '.join(missing)}"
            )
