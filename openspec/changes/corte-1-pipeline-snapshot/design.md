# Diseño: Pipeline de snapshot para Corte 1

## Enfoque técnico

Primero se habilitarán `pyproject.toml`, extras `dev`, `pytest` y pruebas mínimas. Luego se implementará un pipeline Clean Architecture: extracción PostgreSQL dirigida por catálogo, cinco gates DQS, bundle canónico y snapshot idempotente en Sheets. Render, aprobación y publicación quedan como fases posteriores; publicación solo podrá operar sobre una copia temporal de Slides.

```text
CLI → extract_data → PostgreSQL + catálogo → SourceManifest[16]
             ↓
       validate_bundle (5 gates) → Bundle + SHA-256
             ↓ aprobado
       create_snapshot → Google MCP proxy → Sheets(5)
                                             ╳ Slides
```

Dependencias: `domain → nada`; `application → domain`; `adapters → application + domain`; `config` instancia y conecta.

## Estructura y cambios

| Ruta | Acción / responsabilidad |
|---|---|
| `pyproject.toml`, `tests/` | Crear primero; pytest, extras dev y pruebas unitarias/integración. |
| `src/consejo/domain/entities.py` | `Metric`, `Run`, `Bundle`, `SourceManifest`. |
| `src/consejo/domain/value_objects.py` | `MetricId`, `RunId`, `AttemptId`, `HashSha256`. |
| `src/consejo/domain/dqs.py` | Reglas puras y resultados bloqueantes. |
| `src/consejo/application/ports.py` | Puertos abstractos. |
| `src/consejo/application/use_cases/{extract_data,validate_bundle,create_snapshot}.py` | Orquestación sin I/O concreto. |
| `src/consejo/adapters/catalog/yaml_metric_repo.py` | Lee `data/catalogo-metricas.yaml`. |
| `src/consejo/adapters/postgres/{source_conn,metric_reader}.py` | Lectura parametrizada de `analisis_cpe_db`; nunca `agg_*`. |
| `src/consejo/adapters/sheets/google_mcp_sheet_repo.py` | JSON-RPC por stdio a `mcp/google_mcp_proxy.py`. |
| `src/consejo/adapters/cli/main.py` | Comandos extract/validate/snapshot. |
| `src/consejo/config/{settings,container}.py` | Entorno y DI. |

## Interfaces / contratos

```python
class MetricRepo(Protocol):
    def list_metrics(self) -> Sequence[Metric]: ...
class SourceConn(Protocol):
    def fetch(self, sql: str, params: Mapping[str, object]) -> Sequence[Mapping]: ...
class SheetRepo(Protocol):
    def snapshot(self, bundle: Bundle) -> str: ...
class SlidesRepo(Protocol):
    def publish(self, bundle: Bundle, copy_id: str) -> str: ...  # futuro
def extract_data(run_id: RunId, attempt_id: AttemptId, cut: date) -> Sequence[SourceManifest]: ...
def validate_bundle(manifests: Sequence[SourceManifest]) -> Bundle: ...
def create_snapshot(bundle: Bundle) -> str: ...
```

Cada manifiesto contiene `metric_id`, `source`, `cut`, `fetched_at` UTC y `freshness_hours`; `empty` es estado, no cero. `source: manual` exige responsable/corte/referencia/justificación y `value=null`.

## Granos y cardinalidad resueltos desde el catálogo

Grano de salida común: una fila escalar por `(attempt_id, metric_id, cut)`; cardinalidad exacta: 16 filas y una por clave. Granos de cálculo/familias:

| Familia | Grano de cálculo | Filas |
|---|---|---:|
| registrados | usuario distinto × plataforma de origen | 3 |
| beneficiarios manuales | declaración × corte, sin valor | 2 |
| inscripciones | evento de inscripción × origen | 3 |
| inscritos únicos | usuario distinto × origen | 2 |
| certificados | evento × origen; `advance=100` y fecha no nula | 3 |
| certificados únicos | usuario distinto × origen | 3 |

Plataforma 1=CPE; 2=Aprende. Reconciliaciones: `registered_total`, `inscriptions_cpe_total`, `certifications_cpe_total` y `certified_unique_cpe_total` igualan sus partes, ahora con partes disjuntas confirmadas.

## Flujo, bundle y gates

```json
{"run_id":"…","attempt_id":"…","cut":"…Z","catalog_hash":"…","manifests":[],"rows":[],"dqs":[],"hash":"sha256:…"}
```

JSON UTF-8, claves ordenadas, separadores estables y fechas UTC; el hash se calcula sin el campo `hash`. `fetched_at` se fija al crear el intento y se reutiliza: refetch o cambio de datos/catálogo/fórmula/manual crea otro intento.

Gates bloqueantes: 16 claves exactas; partes=total; nulos/ceros/vacíos/rangos; doble snapshot del mismo intento conserva hash y no duplica; toda fila referencia métrica, fuente, grano, run e intento. Fallo → `blocked`, sin llamada a Sheets.

```text
extracting → extracted → validating → ready_for_review
     └──────────────→ failed/blocked
ready_for_review → superseded
```

Estados terminales no reabren; cambios crean `attempt_id`; un intento publicado permanece inmutable.

## Sheets, errores y credenciales

El adapter usa solo `get_spreadsheet`/`update_sheet`, `shell=False` y service account indicada por `GOOGLE_APPLICATION_CREDENTIALS` fuera del repositorio. DI no registra `SlidesRepo`; cero llamadas Slides. Hojas: `Control` (estado, fuente, frescura, hash, aprobaciones, release); `Datos` (filas, historia inmutable); `Reporte` (reales/manuales); `Errores` (código, severidad, mensaje sanitizado); `Configuracion` (catálogo, formatos y campos de orden/mapeo Slides marcados fuera de alcance, sin leer `mapping-slides.yaml`). Ningún error expone secretos.

## Decisiones arquitectónicas

| Decisión | Alternativa | Razón |
|---|---|---|
| Catálogo YAML como autoridad | SQL embebido | Versiona fórmula, fuente y formato. |
| Batch idempotente por `attempt_id+hash` | Append ciego | Evita duplicados y preserva historia. |
| Proxy existente limitado por adapter/DI | API Google directa | Reutiliza integración sin habilitar Slides. |

## Estrategia de pruebas

Unitarias: value objects, canonización, estados y cinco DQS. Integración: catálogo+PostgreSQL con fixtures reales anonimizados y proxy falso verificando cinco hojas/cero Slides. E2E: extract→validate→snapshot en entorno autorizado; no se activa TDD estricto.

## Matriz de amenazas

La integración stdio existe, pero las cinco filas de la matriz (paths ejecutables, selección Git, commit, push y PR) son N/A: no se clasifican archivos ni se automatizan VCS/PR. El adapter usa argv fijo y `shell=False`.

## Migración / despliegue

No requiere migración. Despliegue por unidades: entorno de pruebas, núcleo/adapters, validación y finalmente snapshot. La credencial local detectada debe retirarse del árbol y rotarse si fue compartida.
