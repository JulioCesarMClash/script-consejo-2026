# Script Consejo 2026

Plan de automatizacion para generar y publicar el reporte del consejo 2026 con trazabilidad, validacion y aprobacion humana.

## Objetivo

Construir un flujo que:

1. Extraiga datos desde PostgreSQL remoto y, cuando haga falta, desde MySQL local temporal.
2. Valide cobertura, consistencia historica e idempotencia.
3. Genere un snapshot provisional en Google Sheets.
4. Use Apps Script para renderizar tablas ejecutivas.
5. Pase por revision maker-checker.
6. Publique solo una copia de la presentacion en Google Slides.

## Fuentes

- PostgreSQL remoto como fuente principal.
- MySQL local `carso_analisis` y `academica_analisis` en puerto `8889` como respaldo temporal.
- Consultas historicas de referencia.
- Entradas manuales solo para casos autorizados.

## Reglas

- `run_id` identifica la entrega y el corte.
- `attempt_id` identifica reintentos o correcciones.
- Sheet y Slides deben coincidir con el mismo bundle canonico.
- Cualquier diferencia entre Sheet y Slides bloquea la publicacion.
- No se modifica la presentacion original; solo una copia temporal.

## Estados

```text
extracting -> extracted -> validating -> ready_for_review -> approved -> publishing -> published
```

Estados terminales:

```text
blocked | failed | superseded
```

## Reglas de datos

- Cada metrico debe tener fuente, corte, formula y destino.
- Los periodos parciales deben marcarse como tales.
- Las proyecciones se publican separadas de los valores reales.
- Los valores manuales requieren revision y evidencia.

## Control de calidad

Obligaciones activas:

1. Cardinalidad exacta por grano.
2. Reconciliacion matematica entre partes y total.
3. Casos borde reales.
4. Idempotencia real.
5. Cero filas huérfanas.

## Entregables

- Catologo de metricas versionado.
- Manifiestos por fuente y por corrida.
- Snapshot provisional en Google Sheets.
- Copia de Google Slides completada y validada.
- Evidencia de revision y aprobacion.

## Pendientes

- Definir la formula final de algunas proyecciones.
- Confirmar el mapeo exacto de objetos de Slides.
- Completar la migracion futura de fuentes temporales a bases analiticas definitivas.
