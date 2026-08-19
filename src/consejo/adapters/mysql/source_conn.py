"""Adaptador MySQL para SourceConn.

Conexión parametrizada a las DBs `carso_analisis` y `academica_analisis`
con sanitización de errores: ningún mensaje de error expone contraseñas
ni connection strings.

La conexión es lazy: se abre recién al invocar `fetch`. Si una métrica
nunca se consulta contra MySQL, no se establece conexión.

Si `settings.mysql_database` es None, no se selecciona DB por default al
conectar; las queries deben usar prefijo `<db>.tabla` (ej.
`SELECT * FROM carso_analisis.mi_tabla`).
"""

from __future__ import annotations

import re
from typing import Mapping, Sequence

import pymysql
import pymysql.cursors

from src.consejo.application.ports import SourceConn
from src.consejo.config.settings import Settings

# Placeholders nombrados estilo psycopg2: `%(period_start)s`. pymysql solo
# soporta `%s` posicional, así que se convierten antes de ejecutar.
_NAMED_PLACEHOLDER = re.compile(r"%\((\w+)\)s")
_POSITIONAL_PLACEHOLDER = re.compile(r"%\(\w+\)s")


class MysqlSourceConn(SourceConn):
    """Conexión a MySQL con consultas parametrizadas seguras."""

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
        # pymysql no soporta placeholders nombrados `%(name)s`; se convierten
        # a `%s` posicionales en orden de aparición. El catálogo queda uniforme
        # con named style (`%(period_start)s`) para todas las fuentes.
        names = _NAMED_PLACEHOLDER.findall(sql)
        new_sql = _POSITIONAL_PLACEHOLDER.sub("%s", sql)

        connect_kwargs: dict[str, object] = {
            "host": self._settings.mysql_host,
            "port": self._settings.mysql_port,
            "user": self._settings.mysql_user,
            "password": self._settings.mysql_password,
            "connect_timeout": 5,
            "cursorclass": pymysql.cursors.DictCursor,
        }
        if self._settings.mysql_database:
            connect_kwargs["database"] = self._settings.mysql_database

        try:
            conn = pymysql.connect(**connect_kwargs)
        except pymysql.MySQLError as e:
            raise ConnectionError(
                "Credencial de base de datos no configurada: "
                "no se pudo conectar a MySQL. "
                "Verificar MYSQL_HOST, MYSQL_PORT, MYSQL_USER, "
                "MYSQL_PASSWORD, MYSQL_DATABASE."
            ) from e

        try:
            missing = [name for name in names if name not in params]
            if missing:
                raise KeyError(
                    "Faltan valores para los parámetros: "
                    f"{', '.join(missing)}"
                )
            values = tuple(params[name] for name in names)
            with conn.cursor() as cur:
                cur.execute(new_sql, values)
                rows = cur.fetchall()
                return [dict(r) for r in rows]
        except Exception as e:
            msg = str(e).replace(
                self._settings.mysql_password, "***"
            ).replace(
                self._settings.mysql_host, "***"
            ).replace(
                self._settings.mysql_user, "***"
            )
            if self._settings.mysql_database:
                msg = msg.replace(self._settings.mysql_database, "***")
            raise RuntimeError(
                f"Error en consulta MySQL: {msg}"
            ) from e
        finally:
            try:
                conn.close()
            except Exception:
                pass
