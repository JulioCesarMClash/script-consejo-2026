# Spec: Pipeline de snapshot para Corte 1

## Propósito

Especificar las tres capacidades nuevas del cambio `corte-1-pipeline-snapshot`: extracción trazable de métricas, validación DQS con bundle canónico, y snapshot en Google Sheets.

---

## Capacidad 1: `extraccion-trazable-metricas`

### Requisito: Habilitación del entorno de pruebas

El proyecto DEBE disponer de `pyproject.toml` con dependencias declaradas y `pytest` ejecutable antes de cualquier lógica de negocio.

| Escenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Instalación limpia | Entorno virtual vacío | `pip install -e .[dev]` | `pytest` se ejecuta y reporta 0 tests sin error |
| Sin credenciales en repo | Se revisa el árbol | `git grep` busca patrones de credencial | Cero coincidencias |

### Requisito: Arquitectura limpia por capas

El código DEBE organizarse en `domain/`, `application/`, `adapters/`, `config/`. Regla de dependencias: dominio→ninguna; aplicación→dominio; adaptadores→dominio+aplicación.

| Escenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Violación de capas | Un archivo en `domain/` importa de `adapters/` | Se ejecuta el linter de arquitectura | Falla con error de dependencia prohibida |

### Requisito: Extracción de 16 métricas con manifiestos

El sistema DEBE extraer las 16 métricas desde `analisis_cpe_db` y generar un manifiesto por fuente con `source`, `cut` (fecha de corte), `fetched_at` (ISO 8601 UTC) y `freshness_hours`.

| Escenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Extracción exitosa | Conexión PostgreSQL válida | Se ejecuta el caso `extract` | Se producen 16 manifiestos con métricas y metadatos |
| Inscripciones/certificaciones | Se consultan métricas de inscripción | Se ejecuta la consulta | La consulta usa `fact_inscription` directamente, NO `agg_*` |
| Certificación | Se evalúa certificación | Se aplica la regla | DEBE cumplir `advance = 100 AND certificationDate IS NOT NULL` |
| Fuente vacía | Una fuente no devuelve filas | Se construye el manifiesto | El valor se marca como `empty`, NO se convierte en cero |
| Plataforma 1 vs 2 | Se extraen métricas | Se clasifica por plataforma | Plataforma 1 = Capacitate (CPE); Plataforma 2 = Aprende |

### Requisito: Entradas manuales sin valores concretos

El sistema DEBE admitir `source: manual` con `responsable`, `corte`, `referencia` y `justificacion`. NO DEBE almacenar valores numéricos manuales en este alcance.

| Escenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Entrada manual registrada | Se declara una métrica manual | Se guarda el manifiesto | Contiene metadata completa pero campo `value` ausente o nulo |

---

## Capacidad 2: `validacion-dqs-bundle`

### Requisito: Cinco obligaciones DQS bloqueantes

El sistema DEBE validar las cinco obligaciones antes de construir el bundle. Cualquier fallo DEBE bloquear el snapshot.

| Obligación | Regla | Escenario de fallo |
|---|---|---|
| 1. Cardinalidad exacta por grano | Cada métrica DEBE producir exactamente las filas esperadas por grano | Métrica con 5 filas cuando se esperan 4 → bloqueo |
| 2. Reconciliación parte/total | La suma de partes DEBE igualar el total declarado | Subtotales de plataformas no suman el total → bloqueo |
| 3. Casos borde reales | Se DEBEN validar divisiones por cero, nulos y rangos | Valor negativo donde solo se esperan positivos → bloqueo |
| 4. Idempotencia real | Reejecutar el mismo intento DEBE producir el mismo hash | Segundo run genera hash distinto → bloqueo |
| 5. Cero filas huérfanas | Cada fila DEBE tener métrica, fuente y grano asignados | Fila sin `metric_id` → bloqueo |

### Requisito: Bundle canónico

El sistema DEBE construir un bundle con `run_id`, `attempt_id`, datos en UTF-8, claves JSON ordenadas alfabéticamente, fechas ISO 8601 UTC y hash SHA-256 del contenido canónico.

| Escenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Bundle generado | Validación DQS exitosa | Se construye el bundle | Contiene todos los campos; hash SHA-256 es reproducible |
| Reejecución idempotente | Mismo `attempt_id`, mismos datos | Se reconstruye el bundle | El hash SHA-256 es idéntico al anterior |

### Requisito: Ciclo de vida de intentos

Cada cambio de datos, catálogo, fórmula o entrada manual DEBE generar un nuevo `attempt_id`. Un intento en estado terminal (`blocked`, `failed`, `superseded`) NO DEBE reabrirse.

| Escenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Nuevo intento | Existe un intento `published` | Se modifica una entrada manual | Se crea un nuevo `attempt_id`; el anterior permanece `published` |
| Intento terminal | Un intento está `blocked` | Se intenta modificar | El sistema rechaza la operación y sugiere crear un nuevo intento |

### Requisito: Manejo de credenciales

Las credenciales DEBE leerse de variables de entorno. Los secretos DEBEN estar fuera de Git. Los errores DEBEN sanitizarse (sin credenciales en logs ni mensajes).

| Escenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Credencial ausente | `DB_PASSWORD` no está definida | Se intenta conectar | Error sanitizado: "Credencial de base de datos no configurada" (sin valor) |
| Secreto en log | Ocurre un error de conexión | Se escribe el log | El log NO contiene passwords, tokens ni connection strings completas |

---

## Capacidad 3: `snapshot-google-sheets`

### Requisito: Creación de cinco hojas

El sistema DEBE crear mediante el proxy Google MCP las hojas: `Control`, `Datos`, `Reporte`, `Errores`, `Configuracion`.

| Escenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Snapshot exitoso | Bundle validado | Se ejecuta el caso `snapshot` | Se crean/actualizan las 5 hojas con el contenido esperado |
| DQS falla | Al menos una obligación DQS no pasa | Se intenta snapshot | El snapshot se bloquea; no se escribe en Sheets |

### Requisito: Contenido por hoja

| Hoja | Contenido obligatorio |
|---|---|
| `Control` | Estado de corrida, fuente, frescura, hash activo, aprobaciones, release activo |
| `Datos` | Filas normalizadas, versión histórica por intento, inmutable post-validación |
| `Reporte` | Tablas ejecutivas; valores reales vs manuales diferenciados |
| `Errores` | Código, severidad, mensaje sanitizado |
| `Configuracion` | Catálogo de métricas, orden de slides, formatos, mapeos |

### Requisito: No modificación de Google Slides

El sistema NO DEBE realizar ninguna llamada de escritura o publicación sobre Google Slides en este alcance. `SlidesRepo` existe solo como puerto futuro.

| Escenario | GIVEN | WHEN | THEN |
|---|---|---|---|
| Ejecución completa | Pipeline corre exitosamente | Se verifica la actividad | Cero llamadas de escritura a Slides; la presentación original permanece intacta |

---

## Resumen de cobertura

| Dimensión | Estado |
|---|---|
| Happy paths | Cubiertos (extracción, validación, snapshot) |
| Casos borde | Cubiertos (fuente vacía ≠ 0, credencial ausente, intento terminal) |
| Estados de error | Cubiertos (DQS bloqueo, error sanitizado, idempotencia) |
