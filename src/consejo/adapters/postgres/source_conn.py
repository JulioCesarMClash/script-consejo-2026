"""Adaptador PostgreSQL para SourceConn.

Conexión parametrizada a analisis_cpe_db con sanitización de errores:
ningún mensaje de error expone contraseñas ni connection strings.
"""

from __future__ import annotations

from typing import Mapping, Sequence

import psycopg2
import psycopg2.extras

from src.consejo.application.ports import SourceConn
from src.consejo.config.settings import Settings


class PostgresSourceConn(SourceConn):
    """Conexión a PostgreSQL con consultas parametrizadas seguras."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch(
        self, sql: str, params: Mapping[str, object]
    ) -> Sequence[Mapping[str, object]]:
        """Ejecuta SQL parametrizado y devuelve filas como diccionarios.

        Args:
            sql: Consulta SQL a ejecutar.
            params: Parámetros de la consulta (nombrados).

        Returns:
            Lista de diccionarios con las filas resultantes.

        Raises:
            ConnectionError: Si no se puede conectar (mensaje sanitizado).
            RuntimeError: Si la consulta falla (mensaje sanitizado).
        """
        try:
            conn = psycopg2.connect(
                host=self._settings.db_host,
                dbname=self._settings.db_name,
                user=self._settings.db_user,
                password=self._settings.db_password,
                port=self._settings.db_port,
                connect_timeout=5,
                options=(
                    f"-c statement_timeout="
                    f"{self._settings.db_statement_timeout_ms} "
                    f"-c lock_timeout={self._settings.db_lock_timeout_ms}"
                ),
            )
        except psycopg2.OperationalError as e:
            raise ConnectionError(
                "Credencial de base de datos no configurada: "
                "no se pudo conectar a PostgreSQL. "
                "Verificar DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT."
            ) from e

        try:
            with conn:
                with conn.cursor(
                    cursor_factory=psycopg2.extras.RealDictCursor
                ) as cur:
                    cur.execute(sql, params)
                    rows = cur.fetchall()
                    return [dict(r) for r in rows]
        except Exception as e:
            msg = str(e).replace(
                self._settings.db_password, "***"
            ).replace(
                self._settings.db_host, "***"
            ).replace(
                self._settings.db_name, "***"
            ).replace(
                self._settings.db_user, "***"
            )
            raise RuntimeError(
                f"Error en consulta PostgreSQL: {msg}"
            ) from e
        finally:
            try:
                conn.close()
            except Exception:
                pass
