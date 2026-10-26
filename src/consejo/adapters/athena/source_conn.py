"""Adaptador Athena para SourceConn.

Consulta el datalake Iceberg (S3 Tables) vía Amazon Athena (motor Trino,
engine v3). La autenticación usa la sesión AWS del perfil SSO configurado
(boto3 la resuelve sola); no hay llaves que pasar ni sanitizar.

PyAthena usa paramstyle `pyformat`, el mismo que psycopg2: los placeholders
nombrados del catálogo (`%(cut)s`, `%(period_start)s`) se pasan tal cual,
sin traducción (a diferencia del adaptador MySQL, que convierte a `%s`).

El SQL ejecutado es `athena_mapping` (dialecto Trino), no `db_mapping` (PG):
el ruteo lo hace extract_data según la fuente activa.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from src.consejo.application.ports import SourceConn
from src.consejo.config.settings import Settings


class AthenaSourceConn(SourceConn):
    """Conexión a Athena/S3 Tables con consultas parametrizadas seguras."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch(
        self, sql: str, params: Mapping[str, object]
    ) -> Sequence[Mapping[str, object]]:
        """Ejecuta SQL (dialecto Trino) parametrizado y devuelve las filas.

        Args:
            sql: Consulta SQL Trino a ejecutar (athena_mapping).
            params: Parámetros nombrados estilo pyformat (`%(cut)s`).

        Returns:
            Lista de diccionarios con las filas resultantes.

        Raises:
            ConnectionError: Si no se puede conectar/autenticar (mensaje
                sanitizado, sin exponer ARNs ni tokens de sesión).
            RuntimeError: Si la consulta falla (mensaje sanitizado).
        """
        # Importación local: boto3/pyathena solo se cargan cuando la fuente
        # activa es Athena, manteniendo el arranque liviano para corridas PG.
        import boto3
        from pyathena import connect

        try:
            session = boto3.Session(
                profile_name=self._settings.aws_profile or None,
                region_name=self._settings.aws_region,
            )
            conn = connect(
                work_group=self._settings.athena_workgroup,
                catalog_name=self._settings.athena_catalog,
                schema_name=self._settings.athena_database,
                region_name=self._settings.aws_region,
                # Credenciales resueltas por la sesión SSO (boto3).
                aws_access_key_id=None,
                aws_secret_access_key=None,
                profile_name=self._settings.aws_profile or None,
                session=session,
            )
        except Exception as e:
            raise ConnectionError(
                "Credencial AWS no configurada o sesión SSO expirada: "
                "no se pudo conectar a Athena. "
                "Verificar AWS_PROFILE/SSO (aws sso login), AWS_REGION, "
                "ATHENA_WORKGROUP, ATHENA_CATALOG, ATHENA_DATABASE."
            ) from e

        try:
            with conn.cursor() as cur:
                cur.execute(sql, dict(params) if params else None)
                columns = [d[0] for d in (cur.description or [])]
                rows = cur.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            raise RuntimeError(
                f"Error en consulta Athena: {_sanitize(str(e), self._settings)}"
            ) from e
        finally:
            try:
                conn.close()
            except Exception:
                pass


def _sanitize(msg: str, settings: Settings) -> str:
    """Oculta identificadores de cuenta/infra en mensajes de error.

    Athena no expone contraseñas, pero sí puede filtrar el ID de cuenta,
    el bucket de resultados o ARNs. Se enmascaran los que conocemos.
    """
    for secret in (settings.aws_account_id, settings.athena_catalog):
        if secret:
            msg = msg.replace(secret, "***")
    return msg
