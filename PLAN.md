# Script Consejo 2026

## Objetivo

Automatizar la generacion, validacion y publicacion de la presentacion del consejo 2026 con trazabilidad completa, revision humana y salida segura a Google Slides.

## Decision

La solucion se implementa como un flujo por fases:

1. Extraccion de datos desde PostgreSQL remoto y, cuando sea necesario, MySQL local temporal.
2. Validacion de cobertura, consistencia historica, reconciliacion y idempotencia.
3. Construccion de un snapshot provisional en Google Sheets.
4. Render de tablas ejecutivas mediante Apps Script.
5. Revision maker-checker.
6. Publicacion de una copia temporal de Google Slides.
7. Verificacion final Sheet vs Slides.

## Alcance

### Incluido

- Extraccion desde PostgreSQL remoto.
- Complemento temporal desde MySQL local `carso_analisis` y `academica_analisis`.
- Uso de Google Sheets como snapshot provisional.
- Apps Script para preparar la vista ejecutiva.
- Reglas de validacion tipo DQS.
- Entradas manuales autorizadas.
- Publicacion solo sobre copia de Slides.
- Trazabilidad por `run_id`, `attempt_id` y hash canonico.

### Fuera de alcance inicial

- Modificar la presentacion original.
- Persistir datos fuente en PostgreSQL como sistema principal de este flujo.
- Contenerizar la ejecucion.
- Automatizar Matomo en esta primera entrega.
- Resolver la proyeccion final de Academica Labs sin backtesting.

## Fuentes

| Fuente | Uso | Estado |
|---|---|---|
| PostgreSQL remoto | Fuente principal | Activa |
| `carso_analisis` | Capacitate Carso | Temporal |
| `academica_analisis` | Academica Labs | Temporal |
| Consultas historicas | Referencia | Control |
| Reportes manuales | Casos autorizados | Manual |
| Matomo | Redes sociales | Pendiente |

## Principios

- No asumir que una fuente vacia implica cero.
- No mezclar reales, proyectados y manuales sin marcarlo.
- No publicar si existe discrepancia entre Sheets y Slides.
- No sobrescribir la presentacion original.
- No duplicar registros por reejecucion.

## Estados

```text
extracting -> extracted -> validating -> ready_for_review -> approved -> publishing -> published
```

Terminales:

```text
blocked | failed | superseded
```

## Modelo de corrida

- `run_id`: identifica la entrega y el corte.
- `attempt_id`: identifica reintentos o correcciones.
- Cada cambio de datos, mapping, formula o entrada manual genera un nuevo intento.
- Los intentos terminales no se reabren.

## Bundle canonico

Cada intento genera un bundle con:

- Datos normalizados.
- Catalogo versionado.
- Manifiestos por fuente.
- Hashes de consulta.
- Mappings y formulas.
- Entradas manuales aprobadas.
- Resultados de validacion.
- IDs de Sheet y Slides.
- Versiones de scripts.

El bundle se canoniza en UTF-8, claves ordenadas, fechas ISO 8601 UTC y hash SHA-256.

## Google Sheet provisional

Hojas esperadas:

- `Control`
- `Datos`
- `Reporte`
- `Errores`
- `Configuracion`

### Control

- Estado de corrida.
- Fuente y frescura.
- Hash activo.
- Aprobaciones.
- Release activo.

### Datos

- Filas normalizadas.
- Version historica por intento.
- Inmutable despues de validacion.

### Reporte

- Tablas ejecutivas.
- Valores reales, proyectados y manuales claramente diferenciados.

### Errores

- Codigo.
- Severidad.
- Mensaje sanitizado.

### Configuracion

- Catalogo de metricas.
- Orden de slides.
- Formatos.
- Mapeos de objetos.

## Entradas manuales

Casos previstos:

- CPE: acumulado historico a septiembre 2026.
- Cultura y Salud Aprende: registros acumulados a septiembre 2026.

Reglas:

- Solo se usan cuando la automatizacion no entrega un valor viable.
- Deben tener responsable, corte, referencia y justificacion.
- Pasan por revision y validacion igual que el resto.

## Proyecciones

- Las series con historia comparable pueden proyectarse con base en 2025 vs 2026.
- Academica Labs queda pendiente de backtesting.
- Mientras no se apruebe el metodo, se publica solo el dato real.

## DQS

Obligaciones activas:

1. Cardinalidad exacta por grano.
2. Reconciliacion matematica entre partes y total.
3. Casos borde reales.
4. Idempotencia real.
5. Cero filas huérfanas.

## Reglas de publicacion

- Solo se publica un intento aprobado.
- Sheet y Slides deben coincidir con el mismo hash.
- Cualquier diferencia bloquea la salida.
- La copia de Slides es la unica superficie modificada.

## Pendientes

- Confirmar la formula final de proyeccion para Academica Labs.
- Completar el mapeo exacto de objetos de Slides.
- Definir el catalogo inicial de metricas.
- Incorporar Matomo cuando haya fuente disponible.
