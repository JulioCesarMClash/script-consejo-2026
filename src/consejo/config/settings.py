"""Settings del pipeline leídos de variables de entorno.

Ningún secreto se hardcodea; las variables se validan al inicio.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Configuración del pipeline desde entorno."""

    db_host: str = field(
        default_factory=lambda: os.environ.get("DB_HOST", "")
    )
    db_name: str = field(
        default_factory=lambda: os.environ.get("DB_NAME", "")
    )
    db_user: str = field(
        default_factory=lambda: os.environ.get("DB_USER", "")
    )
    db_password: str = field(
        default_factory=lambda: os.environ.get("DB_PASSWORD", "")
    )
    db_port: int = field(
        default_factory=lambda: int(os.environ.get("DB_PORT", "5432"))
    )
    google_application_credentials: str = field(
        default_factory=lambda: os.environ.get(
            "GOOGLE_APPLICATION_CREDENTIALS", ""
        )
    )
    catalog_path: str = field(
        default_factory=lambda: os.environ.get(
            "CATALOG_PATH",
            str(
                Path(__file__).resolve().parent.parent.parent.parent
                / "data"
                / "catalogo-metricas.yaml"
            ),
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
