"""Contenedor de inyección de dependencias manual.

Instancia y conecta los componentes del pipeline sin framework externo.
"""

from __future__ import annotations

from datetime import date as Date
from typing import Callable

from src.consejo.adapters.catalog.yaml_metric_repo import YamlMetricRepo
from src.consejo.adapters.postgres.source_conn import PostgresSourceConn
from src.consejo.adapters.sheets.google_mcp_sheet_repo import (
    GoogleMcpSheetRepo,
)
from src.consejo.application.use_cases.create_snapshot import (
    create_snapshot,
)
from src.consejo.application.use_cases.extract_data import extract_data
from src.consejo.application.use_cases.validate_bundle import (
    validate_bundle,
)
from src.consejo.config.settings import Settings
from src.consejo.domain.value_objects import AttemptId, Cut, RunId


def build_pipeline(
    cut: Date,
    spreadsheet_id: str,
    settings: Settings | None = None,
) -> Callable[[], dict]:
    """Construye y devuelve un callable que ejecuta el pipeline completo.

    Args:
        cut: Fecha de corte del snapshot.
        spreadsheet_id: ID del spreadsheet Google Sheets.
        settings: Configuración del entorno. Si es None, se instancia
            desde variables de entorno.

    Returns:
        Callable sin argumentos que ejecuta extract→validate→snapshot
        y devuelve un dict con el resultado.
    """
    if settings is None:
        settings = Settings()

    metric_repo = YamlMetricRepo(settings.catalog_path)
    source_conn = PostgresSourceConn(settings)
    sheet_repo = GoogleMcpSheetRepo()

    def _run() -> dict:
        run_id = RunId.generate()
        attempt_id = AttemptId.generate()

        manifests = extract_data(
            metric_repo=metric_repo,
            source_conn=source_conn,
            run_id=run_id,
            attempt_id=attempt_id,
            cut=cut,
        )

        catalog = list(metric_repo.list_metrics())
        catalog_hash = metric_repo.compute_catalog_hash()

        bundle = validate_bundle(
            manifests=manifests,
            catalog=catalog,
            run_id=run_id,
            attempt_id=attempt_id,
            cut=Cut(cut),
            catalog_hash=catalog_hash,
        )

        sid = create_snapshot(bundle, sheet_repo)

        return {
            "run_id": str(run_id),
            "attempt_id": str(attempt_id),
            "cut": cut.isoformat(),
            "catalog_hash": catalog_hash,
            "bundle_hash": str(bundle.hash),
            "spreadsheet_id": sid,
            "manifests": len(manifests),
            "rows": len(bundle.rows),
        }

    return _run
