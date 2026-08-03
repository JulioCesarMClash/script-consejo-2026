# Especificación: Extracción Trazable de Métricas

## Propósito

Especificar la capacidad de extraer las 16 métricas desde `analisis_cpe_db` con manifiestos trazables por fuente, habilitando el entorno de pruebas y respetando la arquitectura limpia por capas.

---

## Requisitos

### Requisito: Habilitación del entorno de pruebas

El proyecto DEBE disponer de `pyproject.toml` con dependencias declaradas y `pytest` ejecutable antes de cualquier lógica de negocio.

#### Escenario: Instalación limpia

- GIVEN un entorno virtual vacío
- WHEN se ejecuta `pip install -e .[dev]`
- THEN `pytest` se ejecuta y reporta 0 tests sin error

#### Escenario: Sin credenciales en repo

- GIVEN el árbol del repositorio
- WHEN se ejecuta `git grep` buscando patrones de credencial
- THEN se obtienen cero coincidencias

---

### Requisito: Arquitectura limpia por capas

El código DEBE organizarse en `domain/`, `application/`, `adapters/`, `config/`. Regla de dependencias: dominio→ninguna; aplicación→dominio; adaptadores→dominio+aplicación.

#### Escenario: Violación de capas

- GIVEN un archivo en `domain/` que importa de `adapters/`
- WHEN se ejecuta el linter de arquitectura
- THEN falla con error de dependencia prohibida

---

### Requisito: Extracción de 16 métricas con manifiestos

El sistema DEBE extraer las 16 métricas desde `analisis_cpe_db` y generar un manifiesto por fuente con `source`, `cut` (fecha de corte), `fetched_at` (ISO 8601 UTC) y `freshness_hours`.

#### Escenario: Extracción exitosa

- GIVEN una conexión PostgreSQL válida
- WHEN se ejecuta el caso `extract`
- THEN se producen 16 manifiestos con métricas y metadatos

#### Escenario: Inscripciones y certificaciones

- GIVEN que se consultan métricas de inscripción
- WHEN se ejecuta la consulta
- THEN la consulta usa `fact_inscription` directamente, NO `agg_*`

#### Escenario: Certificación

- GIVEN que se evalúa certificación
- WHEN se aplica la regla
- THEN DEBE cumplir `advance = 100 AND certificationDate IS NOT NULL`

#### Escenario: Fuente vacía

- GIVEN que una fuente no devuelve filas
- WHEN se construye el manifiesto
- THEN el valor se marca como `empty`, NO se convierte en cero

#### Escenario: Plataforma 1 vs 2

- GIVEN que se extraen métricas
- WHEN se clasifica por plataforma
- THEN Plataforma 1 = Capacitate (CPE); Plataforma 2 = Aprende

---

### Requisito: Entradas manuales sin valores concretos

El sistema DEBE admitir `source: manual` con `responsable`, `corte`, `referencia` y `justificacion`. NO DEBE almacenar valores numéricos manuales en este alcance.

#### Escenario: Entrada manual registrada

- GIVEN que se declara una métrica manual
- WHEN se guarda el manifiesto
- THEN contiene metadata completa pero campo `value` ausente o nulo
