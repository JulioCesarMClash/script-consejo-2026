# Exploración: Script Consejo 2026

**Estado**: Completada
**Fecha**: 2026-07-30
**Persistencia**: Hybrid (Engram + OpenSpec)

---

## Resumen

Exploración inicial del proyecto para cerrar decisiones técnicas abiertas antes de formalizar un cambio SDD. Se analizaron 5 áreas: stack técnico, catálogo de métricas, mapeo de Slides, proyección de Academica Labs y arquitectura de fases.

---

## 1. Stack técnico concreto

### Extracción PostgreSQL (fuente principal)

| Opción | Pros | Cons | Recomendación |
|--------|------|------|---------------|
| `psycopg2-binary` | Maduro, directo, estándar de facto | Síncrono | ✅ Recomendado |
| `SQLAlchemy` + psycopg2 | Abstraction layer reutilizable | Overkill para queries directas | — |

### Extracción MySQL (fuentes temporales)

| Opción | Pros | Cons | Recomendación |
|--------|------|------|---------------|
| `mysql-connector-python` | Oficial Oracle | Instalación pesada | — |
| `pymysql` | Pure Python, zero deps nativas | — | ✅ Recomendado |

### Transformación y modelos

| Opción | Uso | Recomendación |
|--------|-----|---------------|
| `pandas` | Agrupaciones, joins, validaciones | ✅ Recomendado |
| `pydantic` | Modelos de datos con validación de esquemas | ✅ Recomendado |
| Dicts/listas nativas | Solo si los aggregates son triviales | — |

### Google APIs

| API | Librería | Recomendación |
|-----|----------|---------------|
| Sheets | `gspread` | ✅ Recomendado |
| Slides | `google-api-python-client` | ✅ Necesario (no hay wrapper específico de calidad) |
| Apps Script | Proyecto separado + `clasp` CLI | ✅ Recomendado |
| Autenticación | `google-auth` con service account | ✅ Recomendado |

### Estructura de proyecto recomendada

```
script-consejo-2026/
├── pyproject.toml
├── src/
│   ├── extraction/
│   │   ├── postgres.py
│   │   └── mysql.py
│   ├── validation/
│   │   └── dqs.py
│   ├── sheets/
│   │   └── snapshot.py
│   ├── slides/
│   │   ├── mapping.py
│   │   └── publisher.py
│   └── core/
│       ├── models.py        # run_id, attempt_id, bundle
│       ├── catalog.py       # catálogo de métricas
│       └── hashing.py       # bundle canónico
├── data/
│   └── catalogo-metricas.yaml
├── scripts/
│   └── apps-script/         # código AppsScript separado
└── tests/
    └── ...
```

---

## 2. Catálogo de métricas

**Formato**: YAML (legible por humanos y Python, versionable en Git).

```yaml
# data/catalogo-metricas.yaml
version: 1
metricas:
  - id: alumnos_activos
    nombre: "Alumnos activos"
    descripcion: "Total de alumnos con estatus activo al corte"
    fuente: postgresql
    tipo: real
    query: "SELECT COUNT(*) FROM alumnos WHERE status = 'activo' AND fecha_corte = :corte"
    destino_slides: "slide_3_txt_total"
    formato: numero_entero
    periodo: anual
    responsable: null
    evidencia: null

  - id: cpe_acumulado
    nombre: "CPE acumulado a septiembre"
    descripcion: "Acumulado histórico de CPE"
    fuente: manual
    tipo: manual
    valor: null
    destino_slides: "slide_5_txt_cpe"
    formato: numero_entero
    responsable: "TBD"
    evidencia: "Descargar reporte de CPE antes del corte"
```

**Campos del catálogo**:

| Campo | Descripción | Obligatorio |
|-------|-------------|-------------|
| `id` | Identificador único de la métrica | Sí |
| `nombre` | Nombre legible | Sí |
| `descripcion` | Qué mide y cómo | Sí |
| `fuente` | postgresql, mysql_carso, mysql_academica, manual | Sí |
| `tipo` | real, proyectado, manual | Sí |
| `query` | Consulta SQL (si aplica) | Condicional |
| `valor` | Valor fijo (si es manual) | Condicional |
| `destino_slides` | ID del objeto en Slides | Sí |
| `formato` | numero_entero, decimal, porcentaje, moneda | Sí |
| `periodo` | Corte temporal de la métrica | Sí |
| `responsable` | Persona responsable (para manuales) | Condicional |
| `evidencia` | Referencia a fuente de evidencia | Condicional |

---

## 3. Mapeo de objetos de Slides

Cada elemento en Google Slides tiene un `objectId` único que no cambia entre ediciones. Se necesita un archivo de mapping estático.

```yaml
# data/mapping-slides.yaml
version: 1
slides:
  - numero: 3
    titulo: "Resumen de alumnos"
    objetos:
      - id: "gABC123456789_TOTAL"
        tipo: text_box
        metrica: alumnos_activos
        formato_texto: "{valor:,.0f}"
      - id: "gABC123456789_TABLA"
        tipo: table
        metrica: tabla_crecimiento
        formato_tabla: cabecera_fija

  - numero: 5
    titulo: "CPE y programas especiales"
    objetos:
      - id: "gDEF987654321_CPE"
        tipo: text_box
        metrica: cpe_acumulado
        formato_texto: "{valor:,.0f}"
```

> **Importante**: El mapping se construye UNA VEZ abriendo la presentación original e inspeccionando los `objectId` de cada elemento mediante la API de Slides o Google Apps Script. Es un paso manual pero estable.

---

## 4. Proyección Academica Labs

### Opciones de fórmula

| Método | Pros | Cons | Complejidad |
|--------|------|------|-------------|
| YoY Growth Rate | Simple, fácil de explicar | Sensible a anomalías | Baja |
| Moving Average (3yr) | Suaviza picos extremos | Necesita 3 años de historia | Baja |
| Regresión lineal | Captura tendencia | Asume linealidad | Media |
| Holt-Winters | Captura estacionalidad + tendencia | Complejo, necesita varios periodos | Alta |

### Backtesting

1. Tomar datos históricos disponibles (2022-2024)
2. Proyectar el último año conocido (2025) con cada método
3. Comparar contra el valor real de 2025
4. Calcular MAPE (Mean Absolute Percentage Error)
5. El método con MAPE < 10% se aprueba

### Recomendación

Empezar con **YoY Growth Rate** por simplicidad. Hacer backtesting contra datos reales. Si MAPE > 10%, probar Moving Average 3yr.

---

## 5. Arquitectura de fases y trazabilidad

### Modelo de identificación

```
run_id:     script-consejo-{anio}-{correlativo}
            Ej: script-consejo-2026-001

attempt_id: {run_id}-{unix_timestamp}
            Ej: script-consejo-2026-001-1741824000
```

### Bundle canónico

Formato: JSON, UTF-8, claves ordenadas alfabéticamente, hash SHA-256 del contenido serializado.

```json
{
  "run_id": "script-consejo-2026-001",
  "attempt_id": "script-consejo-2026-001-1741824000",
  "estado": "extracted",
  "fuentes": [
    {"nombre": "postgresql", "hash": "sha256:abc...", "registros": 1500, "fresca": true},
    {"nombre": "mysql_carso", "hash": "sha256:def...", "registros": 300, "fresca": true},
    {"nombre": "manual_cpe", "responsable": "Juan Perez", "justificacion": "..."}
  ],
  "validacion": {"status": "passed", "errores": 0, "dqs": true},
  "sheet_id": "1abc...",
  "slides_copy_id": "1def...",
  "hash": "sha256:final..."
}
```

### Fases y gates

| Fase | Entrada | Salida | Gate |
|------|---------|--------|------|
| **extraccion** | Conexiones a fuentes | Datos normalizados + manifiestos por fuente | Todas las fuentes respondieron |
| **validacion** | Datos + catálogo de métricas | Bundle validado (DQS 5 obligaciones) | 0 errores críticos |
| **snapshot** | Bundle validado | Google Sheets poblado (hojas Control, Datos, Errores, Configuracion) | Sheet existe y tiene datos |
| **render** | Sheet + catálogo | Views ejecutivas en hoja Reporte | Tablas completas sin celdas vacías |
| **revision** | Sheet con Reporte | Aprobación maker-checker | Firma de aprobación registrada |
| **publicacion** | Aprobación + presentación original | Copia de Slides actualizada | Hash Sheet == Hash Slides |
| **verificacion** | Sheet vs Slides | Reporte de verificación | Discrepancia cero |

### Estados por intento

```
extracting → extracted → validating → ready_for_review → approved → publishing → published
                                                                                       
blocked ──┤  failed ──┤  superseded ──┤  (terminales)
```

---

## Riesgos identificados

1. **No hay test runner** — hay que bootstrap testing antes de implementar lógica.
2. **Sin dependencias instaladas** — el `pyproject.toml` no existe todavía.
3. **Mapping de Slides requiere acceso manual** — necesitamos la presentación original para extraer `objectId`s.
4. **Proyecciones sin backtesting** — pueden dar resultados incorrectos y no detectados.
5. **MySQL local puerto 8889** — puede no estar disponible en CI o en otra máquina.
6. **Entradas manuales** — crean dependencia externa que puede retrasar la corrida.
7. **Repo sin remoto ni commits** — no hay backup ni colaboración posible.

---

## Próximos pasos

1. ✅ Confirmar decisiones de stack y estructura (revisión de esta exploración)
2. ⬜ Crear el catálogo inicial de métricas en `data/catalogo-metricas.yaml`
3. ⬜ Obtener el mapping real de la presentación de Slides
4. ⬜ Armar propuesta formal de cambio con `/sdd-new`
