# Propuesta: Pipeline de snapshot para Corte 1

## Intención

Entregar un corte verificable: extraer métricas de `analisis_cpe_db`, validarlas y generar un snapshot trazable en Google Sheets, sin modificar Slides.

## Alcance

### Incluido
- Habilitar primero `pyproject.toml`, `pytest` y pruebas mínimas.
- Crear Clean Architecture: `domain/` (Metric, Run, Bundle, SourceManifest, IDs, hash, DQS), `application/` (puertos MetricRepo, SourceConn, SheetRepo, SlidesRepo; casos extract, validate, snapshot), `adapters/` (postgres, sheets, cli) y `config/` (settings, DI). Dependencias: dominio→ninguna; aplicación→dominio; adaptadores→dominio+aplicación.
- Extraer las 16 métricas con manifiestos. Inscripciones y certificaciones consultan `fact_inscription`; certificar exige `advance = 100 AND certificationDate IS NOT NULL`.
- Validar cardinalidad exacta por grano, reconciliación parte/total, casos borde reales, idempotencia real y cero filas huérfanas; construir el bundle canónico con `run_id`, `attempt_id`, UTF-8, claves ordenadas, fechas ISO 8601 UTC y SHA-256.
- Crear mediante el proxy existente las hojas `Control`, `Datos`, `Reporte`, `Errores` y `Configuracion`.
- Admitir `source: manual` con responsable, corte, referencia y justificación, sin valores. Fuente vacía no equivale a cero.

### Fuera de alcance
- Proyecciones, valores manuales concretos, Apps Script, Matomo y publicación en Slides.
- Usar `mapping-slides.yaml` o modificar la presentación original; `SlidesRepo` queda como límite futuro.

## Capacidades

### Capacidades nuevas
- `extraccion-trazable-metricas`: extracción PostgreSQL y manifiestos.
- `validacion-dqs-bundle`: obligaciones DQS, estados, idempotencia y bundle canónico.
- `snapshot-google-sheets`: snapshot de cinco hojas.

### Capacidades modificadas
- Ninguna.

## Enfoque

Puertos desacoplan PostgreSQL, Sheets y CLI. Plataforma 1 es Capacítate y 2 Aprende; “Usuarios registrados” significa Beneficiarios. Cambiar datos, fórmula, catálogo o entrada manual crea otro `attempt_id`; un intento terminal no se reabre.

## Áreas afectadas

| Área | Impacto | Descripción |
|---|---|---|
| `pyproject.toml`, `tests/` | Nueva | Pruebas |
| `domain/`, `application/` | Nueva | Núcleo y casos |
| `adapters/`, `config/` | Nueva | Integraciones |
| `data/catalogo-metricas.yaml`, `mcp/google_mcp_proxy.py` | Referencia | Métricas y Sheets |

## Riesgos

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Datos incorrectos | Alta | Cinco gates DQS bloqueantes |
| Duplicación | Media | IDs, hash e idempotencia |
| Credenciales PostgreSQL/Google expuestas | Media | Entorno, secretos fuera de Git, errores sanitizados |
| Alterar Slides original | Baja | Prohibir llamadas de escritura/publicación |

## Plan de reversión

Marcar el intento `superseded`, retirar el Sheet y revertir aplicación/configuración; PostgreSQL y Slides no reciben escrituras.

## Dependencias

- Lectura de `analisis_cpe_db` y service account autorizada para Sheets.

## Criterios de éxito

- [ ] Las 16 métricas producen manifiestos y superan DQS.
- [ ] Reejecutar el mismo intento no duplica filas y conserva el hash.
- [ ] El Sheet contiene las cinco hojas y referencia el bundle activo.
- [ ] No se modifica ninguna presentación de Google Slides.
