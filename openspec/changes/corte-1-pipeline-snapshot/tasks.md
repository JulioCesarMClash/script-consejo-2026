# Tasks: Pipeline de snapshot para Corte 1

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 1000–1300 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | 4 work units (ver Suggested Work Units) |
| Delivery strategy | ask-on-risk |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | pyproject.toml + test harness + dominio (value objects, entities, DQS) + unit tests | PR 1 | `pytest tests/unit/domain/ -v` | `pytest tests/unit/domain/ -v` | rm `src/consejo/domain/` + `tests/unit/domain/`; restore pyproject.toml |
| 2 | Puertos de aplicación + casos de uso (extract, validate) + tests unitarios | PR 2 | `pytest tests/unit/application/ -v` | N/A — casos de uso sin adaptadores dependen de fakes en tests | rm `src/consejo/application/` + `tests/unit/application/` |
| 3 | Adaptadores (catalog, postgres, sheets, CLI) + config/DI + creación de snapshot use case | PR 3 | `pytest tests/integration/ -v` | `python -m src.consejo.adapters.cli.main snapshot --cut 2026-07-01` (requiere DB + creds) | rm `src/consejo/adapters/` + `src/consejo/config/` + `tests/integration/` + snapshot use case |
| 4 | Verificación E2E: extract→validate→snapshot completo + cobertura DQS + ajustes | PR 4 | `pytest tests/e2e/ -v` | `python -m src.consejo.adapters.cli.main pipeline --cut 2026-07-01` (requiere DB + creds + sheet test) | Revertir ajustes de wiring; reponer versión previa de `create_snapshot.py` si existiera |

---

## Fase 1: Habilitación del entorno

- [x] 1.1 Crear `pyproject.toml` con dependencias (`psycopg2-binary`, `pyyaml`, `click`), extras `[dev]` (`pytest`, `pytest-mock`, `pytest-cov`) y entry points del CLI (`src/consejo/adapters/cli/main.py`)
- [x] 1.2 Crear `src/consejo/__init__.py` y estructura de paquetes vacíos: `domain/`, `application/`, `application/use_cases/`, `adapters/`, `adapters/catalog/`, `adapters/postgres/`, `adapters/sheets/`, `adapters/cli/`, `config/` (todos con `__init__.py`)
- [x] 1.3 Crear `tests/__init__.py`, `tests/conftest.py` con fixtures base (`tmp_path`, `sample_catalog_path`), y `tests/unit/test_env.py` que verifica `pytest --collect-only` reporta 1 test (pasa: `assert True`)
- [x] 1.4 Agregar `.gitignore` patrones extendidos: `script-consejo-2026-gcp-*.json`, `*.env`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `*.pyc`, `htmlcov/`, `.coverage`

## Fase 2: Dominio (value objects, entidades, DQS)

- [x] 2.1 Crear `src/consejo/domain/value_objects.py`: `MetricId`, `RunId` (UUID v4), `AttemptId` (UUID v4), `HashSha256`, `MetricSource` (dim_user | fact_inscription | manual), `Cut` (date, validación no futuro), `FetchStatus` (empty | extracted | failed), `RunState` (extracting | extracted | validating | ready_for_review | blocked | failed | superseded | published)
- [x] 2.2 Crear `src/consejo/domain/entities.py`: `Metric` (id, name, key, source, formula, db_mapping, platform_scope, grain), `SourceManifest` (metric_id, source, cut, fetched_at, freshness_hours, rows, status), `Run` (run_id, attempt_id, state, cut, catalog_hash, manifests), `Bundle` (run_id, attempt_id, cut, catalog_hash, manifests, rows, dqs[], hash)
- [x] 2.3 Crear `src/consejo/domain/dqs.py`: reglas puras con función `validate(manifests: list[SourceManifest], catalog: list[Metric]) → DqsReport`; 5 gates: cardinalidad exacta por grano, reconciliación parte/total, casos borde (nulos, negativos, rangos), idempotencia (hash), cero filas huérfanas
- [x] 2.4 Escribir `tests/unit/domain/test_value_objects.py`: cubre creación, validación, igualdad y serialización de cada value object
- [x] 2.5 Escribir `tests/unit/domain/test_entities.py`: cubre construcción de `Metric`, `SourceManifest`, `Run`, `Bundle` y transiciones de estado
- [x] 2.6 Escribir `tests/unit/domain/test_dqs.py`: cada obligación con fixtures de éxito y cada escenario de fallo, incluyendo `source: manual` con `value=null` que NO debe tratarse como cero

## Fase 3: Aplicación (puertos, casos de uso)

- [x] 3.1 Crear `src/consejo/application/ports.py`: `MetricRepo` (list_metrics), `SourceConn` (fetch con SQL parametrizado), `SheetRepo` (snapshot), `SlidesRepo` (publish, marcado futuro con `raise NotImplementedError`)
- [x] 3.2 Crear `src/consejo/application/use_cases/extract_data.py`: `extract_data(run_id, attempt_id, cut) → list[SourceManifest]`; itera catálogo, ejecuta `db_mapping` vía `SourceConn.fetch`, construye 16 manifiestos, respeta `source: manual` sin consulta DB
- [x] 3.3 Crear `src/consejo/application/use_cases/validate_bundle.py`: `validate_bundle(manifests, catalog) → Bundle`; ejecuta `domain/dqs.validate()`, si hay fallo lanza `DqsBlockedError` sin construir bundle; bundle canónico con claves ordenadas, ISO 8601 UTC, SHA-256 sin campo `hash`
- [x] 3.4 Crear `src/consejo/application/use_cases/create_snapshot.py`: `create_snapshot(bundle, sheet_repo) → str`; delega en `SheetRepo.snapshot(bundle)`, crea/actualiza 5 hojas; si bundle no pasó DQS, aborta sin llamar a Sheets
- [x] 3.5 Escribir `tests/unit/application/test_extract_data.py`: con `MetricRepo` y `SourceConn` falsos, verifica 16 manifiestos, `source: manual` sin filas, `empty` como estado
- [x] 3.6 Escribir `tests/unit/application/test_validate_bundle.py`: con manifiestos válidos/inválidos, verifica DQS bloqueo, bundle canónico, hash reproducible, idempotencia con mismo `attempt_id`
- [x] 3.7 Escribir `tests/unit/application/test_create_snapshot.py`: verifica que `SheetRepo.snapshot` recibe bundle correcto, aborta si `bundle.dqs` tiene fallos, no llama a `SlidesRepo`

## Fase 4: Adaptadores e integración

- [x] 4.1 Crear `src/consejo/adapters/catalog/yaml_metric_repo.py`: implementa `MetricRepo` leyendo `data/catalogo-metricas.yaml` con PyYAML, expone `list_metrics() → list[Metric]` y compute `catalog_hash`
- [x] 4.2 Crear `src/consejo/adapters/postgres/source_conn.py`: implementa `SourceConn` con `psycopg2`, credenciales desde `DB_HOST/DB_NAME/DB_USER/DB_PASSWORD/DB_PORT`, fetch parametrizado, errores sanitizados sin passwords
- [x] 4.3 Crear `src/consejo/adapters/postgres/metric_reader.py`: función helper `read_metric(conn, metric: Metric, cut: date) → SourceManifest` que ejecuta `db_mapping`, mapea resultado a manifiesto con `freshness_hours`
- [x] 4.4 Crear `src/consejo/adapters/sheets/google_mcp_sheet_repo.py`: implementa `SheetRepo.snapshot(bundle) → str` via JSON-RPC stdio a `mcp/google_mcp_proxy.py`; usa `get_spreadsheet` + `update_sheet` batch; crea hojas `Control`, `Datos`, `Reporte`, `Errores`, `Configuracion`; `shell=False`, argv fijo; sanitiza errores
- [x] 4.5 Crear `src/consejo/adapters/cli/main.py`: CLI con Click; comandos `extract`, `validate`, `snapshot`, `pipeline` (extract→validate→snapshot); opción `--cut` (ISO date), `--spreadsheet-id`; emite bundle JSON por stdout en `--dry-run`
- [x] 4.6 Crear `src/consejo/config/settings.py`: `Settings` con pydantic/dataclass validando `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`, `GOOGLE_APPLICATION_CREDENTIALS`, `CATALOG_PATH`
- [x] 4.7 Crear `src/consejo/config/container.py`: wiring manual sin framework; instancia `Settings` desde entorno, `YamlMetricRepo`, `PostgresSourceConn`, `GoogleMcpSheetRepo`; función `build_pipeline(cut, spreadsheet_id) → callable`
- [x] 4.8 Escribir `tests/integration/test_catalog_repo.py`: con `data/catalogo-metricas.yaml` real, verifica 16 métricas, plataformas (id=1,2), y `source: manual` en beneficiarios
- [x] 4.9 Escribir `tests/integration/test_sheet_repo.py`: con `GoogleMcpSheetRepo` falso que captura llamadas; verifica 5 hojas creadas, contenido por hoja, cero llamadas a Slides
- [x] 4.10 Escribir `tests/integration/test_pipeline_dry.py`: pipeline completo con DB falsa y Sheets falso; verifica flujo extract→validate→snapshot, DQS bloqueo detiene snapshot, hash estable

## Fase 5: Verificación E2E y cierre

- [ ] 5.1 Escribir `tests/e2e/test_full_pipeline.py`: ejecuta comando `pipeline --cut <fecha> --spreadsheet-id <id>` en entorno autorizado; verifica 16 manifiestos, bundle con SHA-256, 5 hojas creadas, cero escrituras Slides
- [ ] 5.2 Escribir `tests/e2e/test_idempotency.py`: reejecución con mismo `attempt_id` produce hash idéntico y no duplica filas en hoja `Datos`
- [ ] 5.3 Escribir `tests/e2e/test_credential_sanitization.py`: verifica que errores de conexión DB no exponen passwords ni connection strings en logs ni mensajes
- [ ] 5.4 Revisar `spec-superseded.md` y confirmar que ningún requisito descartado fue reintroducido; validar cobertura completa de las 3 specs contra tasks 1.1–5.3
