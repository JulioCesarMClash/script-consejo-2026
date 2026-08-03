# Especificación: Validación DQS y Bundle Canónico

## Propósito

Especificar la capacidad de validar las cinco obligaciones DQS bloqueantes, construir el bundle canónico con hash SHA-256 idempotente, gestionar el ciclo de vida de intentos y manejar credenciales de forma segura.

---

## Requisitos

### Requisito: Cinco obligaciones DQS bloqueantes

El sistema DEBE validar las cinco obligaciones antes de construir el bundle. Cualquier fallo DEBE bloquear el snapshot.

| Obligación | Regla | Escenario de fallo |
|---|---|---|
| 1. Cardinalidad exacta por grano | Cada métrica DEBE producir exactamente las filas esperadas por grano | Métrica con 5 filas cuando se esperan 4 → bloqueo |
| 2. Reconciliación parte/total | La suma de partes DEBE igualar el total declarado | Subtotales de plataformas no suman el total → bloqueo |
| 3. Casos borde reales | Se DEBEN validar divisiones por cero, nulos y rangos | Valor negativo donde solo se esperan positivos → bloqueo |
| 4. Idempotencia real | Reejecutar el mismo intento DEBE producir el mismo hash | Segundo run genera hash distinto → bloqueo |
| 5. Cero filas huérfanas | Cada fila DEBE tener métrica, fuente y grano asignados | Fila sin `metric_id` → bloqueo |

---

### Requisito: Bundle canónico

El sistema DEBE construir un bundle con `run_id`, `attempt_id`, datos en UTF-8, claves JSON ordenadas alfabéticamente, fechas ISO 8601 UTC y hash SHA-256 del contenido canónico.

#### Escenario: Bundle generado

- GIVEN validación DQS exitosa
- WHEN se construye el bundle
- THEN contiene todos los campos; hash SHA-256 es reproducible

#### Escenario: Reejecución idempotente

- GIVEN mismo `attempt_id` y mismos datos
- WHEN se reconstruye el bundle
- THEN el hash SHA-256 es idéntico al anterior

---

### Requisito: Ciclo de vida de intentos

Cada cambio de datos, catálogo, fórmula o entrada manual DEBE generar un nuevo `attempt_id`. Un intento en estado terminal (`blocked`, `failed`, `superseded`) NO DEBE reabrirse.

#### Escenario: Nuevo intento

- GIVEN que existe un intento `published`
- WHEN se modifica una entrada manual
- THEN se crea un nuevo `attempt_id`; el anterior permanece `published`

#### Escenario: Intento terminal

- GIVEN que un intento está `blocked`
- WHEN se intenta modificar
- THEN el sistema rechaza la operación y sugiere crear un nuevo intento

---

### Requisito: Manejo de credenciales

Las credenciales DEBEN leerse de variables de entorno. Los secretos DEBEN estar fuera de Git. Los errores DEBEN sanitizarse (sin credenciales en logs ni mensajes).

#### Escenario: Credencial ausente

- GIVEN que `DB_PASSWORD` no está definida
- WHEN se intenta conectar
- THEN error sanitizado: "Credencial de base de datos no configurada" (sin valor)

#### Escenario: Secreto en log

- GIVEN que ocurre un error de conexión
- WHEN se escribe el log
- THEN el log NO contiene passwords, tokens ni connection strings completas
