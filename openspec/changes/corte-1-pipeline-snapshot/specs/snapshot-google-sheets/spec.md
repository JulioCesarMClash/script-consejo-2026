# Especificación: Snapshot en Google Sheets

## Propósito

Especificar la capacidad de crear un snapshot trazable en cinco hojas de Google Sheets mediante el proxy Google MCP, sin modificar Google Slides.

---

## Requisitos

### Requisito: Creación de cinco hojas

El sistema DEBE crear mediante el proxy Google MCP las hojas: `Control`, `Datos`, `Reporte`, `Errores`, `Configuracion`.

#### Escenario: Snapshot exitoso

- GIVEN un bundle validado
- WHEN se ejecuta el caso `snapshot`
- THEN se crean/actualizan las 5 hojas con el contenido esperado

#### Escenario: DQS falla

- GIVEN que al menos una obligación DQS no pasa
- WHEN se intenta snapshot
- THEN el snapshot se bloquea; no se escribe en Sheets

---

### Requisito: Contenido por hoja

| Hoja | Contenido obligatorio |
|---|---|
| `Control` | Estado de corrida, fuente, frescura, hash activo, aprobaciones, release activo |
| `Datos` | Filas normalizadas, versión histórica por intento, inmutable post-validación |
| `Reporte` | Tablas ejecutivas; valores reales vs manuales diferenciados |
| `Errores` | Código, severidad, mensaje sanitizado |
| `Configuracion` | Catálogo de métricas, orden de slides, formatos, mapeos |

---

### Requisito: No modificación de Google Slides

El sistema NO DEBE realizar ninguna llamada de escritura o publicación sobre Google Slides en este alcance. `SlidesRepo` existe solo como puerto futuro.

#### Escenario: Ejecución completa

- GIVEN que el pipeline corre exitosamente
- WHEN se verifica la actividad
- THEN cero llamadas de escritura a Slides; la presentación original permanece intacta
