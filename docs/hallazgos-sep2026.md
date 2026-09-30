# Hallazgos — corrida septiembre 2026

Fuente de comparación: spreadsheet "Copia de Combatir la pobreza y pobreza extrema"
(`1nWDyUs-no4nfBE6-m1srnuV1vAntJPFfXeqkcdtOq7M`).
- Pestaña "Pobreza" (gid 1033433966) → Slide 2.
- Pestaña "Pobreza extrema" (gid 0) → Slides 1 y 12.

Catálogo comparado: `data/catalogo-metricas.yaml` (rama `feature/ajustes-presentaciones-sep2026`).
La pestaña "Pobreza extrema" no trae IDs; los nombres se resolvieron contra `public.course`.

## H1 — Nueva ruta "Compras y pagos digitales" (Slide 12, Habilidades digitales)

Cursos solicitados: 373, 100006, 380, 345, 100129, 320.
Cinco de seis ya pertenecen a otra ruta del catálogo:

| ID | Curso | Ruta actual en catálogo |
|---|---|---|
| 373 | Regulación de la interacción digital | Interacción con el mundo digital |
| 100006 | Compras y pagos seguros por internet | Interacción con el mundo digital |
| 380 | Operación de banca en línea | Interacción con el mundo digital |
| 345 | Transacciones electrónicas | Interacción con el mundo digital |
| 100129 | Manejo correcto de las tarjetas de crédito | (ninguna — nuevo) |
| 320 | Funcionamiento CoDi | Mi negocio en internet (Emprendimiento) |

Decisión de negocio (2026-09-18): los cursos **se repiten** entre rutas.
Impacto: rompe la regla vigente "un curso pertenece a una sola ruta" (caveat del curso 342);
el total global =SUM de Slide 12 contará dos veces sus inscripciones y certificados.

## H2 — Slide 2 vs pestaña "Pobreza"

Cinco de seis sectores coinciden exactamente. Única diferencia:

| Sector | Diferencia |
|---|---|
| Construcción y mantenimiento | Catálogo incluye 27 "Reparador de aire acondicionado"; la hoja no. |

## H3 — Slide 12 vs pestaña "Pobreza extrema"

Coinciden exactamente: ¿Cómo utilizar un celular?, ¿Cómo utilizar la computadora?,
Preparación para usar internet, Planea tu negocio, Planea los gastos y ganancias,
Servicio y ventas de tu negocio.

| Ruta | Solo en la hoja | Solo en el catálogo |
|---|---|---|
| Proyectos constructivos y mantenimiento | 205 Guía de autoconstrucción, 206 Guía de reparación vivienda rural | — |
| Seguridad, higiene y cuidado de la salud | — | 100900 Cuidados para el día a día |
| Uso eficiente de recursos | 387, 95, 354 (agua) | — |
| Entendiendo mi situación económica | — | 100861 Sal de tus deudas |
| Interacción con el mundo digital | 254 Seguridad en dispositivos móviles | 373 Regulación de la interacción digital, 100897 ¿Primero tú o el celular? |
| ¿Cómo mejorar mi entorno? | 100214 Controlador de plagas | 100918 Tu espacio, tu salud |
| Alimentos desde casa | 120 Manejo higiénico de alimentos, 281 Productor de traspatio | — |
| ¿Cómo preparar mis productos para venderlos? | Bodeguero (ID 77 según pestaña Pobreza) | — |
| Mi negocio en internet | 380 Banca en línea, 345 Transacciones electrónicas | — |
| Actuar en caso de desastres naturales | 100214 Controlador de plagas, 342 Primer respondiente | — |
| Conocimientos para autoempleo y emprendimiento | ruta completa (19 cursos) | ruta no existe |

Observaciones:
- La hoja **repite** cursos entre rutas (387/95/354, 120/281, 254, 380/345, 100214, 342);
  el catálogo los dejó en una sola ruta. Casi todo "solo en la hoja" se explica por eso.
- Lo "solo en catálogo" (100900, 100861, 100918, 100897) son cursos agregados en el catálogo
  que la hoja no refleja; 373 tampoco está en la hoja.
- La ruta "Conocimientos para autoempleo y emprendimiento" no tiene cifras en la hoja.

## H4 — Slide 1

Slide 1 agrupa las mismas rutas de Slide 12 (vivienda = ruta 1; digital = rutas 2–5 +
100212 IA + 366 blockchain; alimentos = rutas 6–10 sin 342; desastres = ruta 11 + 342;
empleo = rutas 12–16 sin 100327 Plan de negocios). Las diferencias de H3 aplican igual.
100212 y 366 no aparecen en la hoja.
Diferencias internas Slide 1 vs Slide 12: 342 va en la ruta "Seguridad, higiene" en Slide 12
pero en "desastres" en Slide 1; 100327 está en Slide 12 pero no en Slide 1.

## H5 — Cursos repetidos entre rutas: hoja vs proyecto

| Fuente | Rutas/grupos | Asignaciones | Cursos únicos | Cursos repetidos |
|---|---|---|---|---|
| Hoja "Pobreza extrema" (16 rutas de Slide 12) | 16 | 109 | 99 | **10** |
| Hoja "Pobreza extrema" + ruta Autoempleo | 17 | 128 | 114 | 14 |
| Hoja "Pobreza" (Slide 2) | 6 | 29 | 29 | 0 |
| Proyecto Slide 12 | 16 | 100 | 100 | **0** |
| Proyecto Slide 1 | 5 | 101 | 101 | 0 |
| Proyecto Slide 2 | 6 | 30 | 30 | 0 |

Los 10 repetidos de la hoja (cada uno en 2 rutas):
- Uso eficiente ↔ Desastres: 387 ahorro de agua, 95 cosecha de agua, 354 potabilización.
- Alimentos desde casa ↔ Desastres: 120 manejo higiénico, 281 traspatio.
- Seguridad, higiene ↔ Desastres: 342 primer respondiente.
- Mejorar mi entorno ↔ Desastres: 100214 controlador de plagas.
- Interacción digital ↔ Mi negocio en internet: 380 banca en línea, 345 transacciones.
- Celular ↔ Interacción digital: 254 seguridad en dispositivos móviles.

Slide 1 declara `compartidos` = 0/2/7/0/3 (vivienda/digital/alimentos/desastres/empleo).
Llevando la hoja a nivel categoría: digital↔empleo = 2 (380, 345) y alimentos↔desastres = 7,
que coinciden con digital=2 y alimentos=7. El 3 de empleo no se explica con esta hoja.

## H6 — Slide 12: cursos repetidos por ruta

"Repetido" = el curso también aparece en otra ruta de Slide 12.

| Ruta | Hoja: cursos | Hoja: repetidos | Repetidos con | Proyecto + nueva ruta: cursos | Proyecto + nueva ruta: repetidos |
|---|---|---|---|---|---|
| Proyectos constructivos y mantenimiento | 19 | 0 | — | 17 | 0 |
| Seguridad, higiene y cuidado de la salud | 6 | 1 | Desastres (342) | 7 | 0 |
| Uso eficiente de recursos | 8 | 3 | Desastres (387, 95, 354) | 5 | 0 |
| Entendiendo mi situación económica | 4 | 0 | — | 5 | 0 |
| ¿Cómo utilizar un celular? | 2 | 1 | Interacción (254) | 2 | 0 |
| ¿Cómo utilizar la computadora? | 4 | 0 | — | 4 | 0 |
| Preparación para usar internet | 5 | 0 | — | 5 | 0 |
| Interacción con el mundo digital | 8 | 3 | Celular (254); Mi negocio (380, 345) | 9 | 4 (373, 100006, 380, 345 → Compras y pagos) |
| ¿Cómo mejorar mi entorno? | 5 | 1 | Desastres (100214) | 5 | 0 |
| Alimentos desde casa | 6 | 2 | Desastres (120, 281) | 4 | 0 |
| Planea tu negocio | 7 | 0 | — | 7 | 0 |
| Planea los gastos y ganancias | 4 | 0 | — | 4 | 0 |
| ¿Cómo preparar mis productos? | 6 | 0 | — | 5 | 0 |
| Servicio y ventas de tu negocio | 6 | 0 | — | 6 | 0 |
| Mi negocio en internet | 7 | 2 | Interacción (380, 345) | 5 | 1 (320 → Compras y pagos) |
| Actuar en caso de desastres naturales | 12 | 7 | Uso eficiente (387, 95, 354); Alimentos (120, 281); Seguridad (342); Entorno (100214) | 10 | 0 |
| Compras y pagos digitales (nueva) | — | — | — | 6 | 5 (373, 100006, 380, 345, 320) |
| **Total** | **109** | **20 (10 cursos × 2)** | | **106** | **10 (5 cursos × 2)** |

## H7 — Reconciliación del 118 de la slide 12

Fuente: presentación `1Hz505EoUZg-ERfjfTnhvLfNryGXsORiJYrqdcvJjza8`, página
`g3761cbcde11_9_59`, columna "Cursos totales" = 118 (ya incluye "Compras y pagos
digitales" con 6, marcada P). Sin esa ruta: 112.

Los 3 cursos que faltaban identificarse salen de la pestaña "Hoja 2" del spreadsheet
de pobreza, que lista las rutas curso por curso:

| Ruta en la slide | Curso | ID | Dónde está en el proyecto |
|---|---|---|---|
| ¿Cómo utilizar un celular? (3) | Uso de aplicaciones de emergencia | 393 | Actuar en caso de desastres |
| Interacción con el mundo digital (11) | Seguridad en dispositivos móviles | 254 | ¿Cómo utilizar un celular? |
| Interacción con el mundo digital (11) | Funcionamiento CoDi | 320 | Mi negocio en internet |

Con eso el 118 cuadra exacto: 102 cursos distintos + 16 apariciones repetidas = 118.

### Cursos que aparecen en más de una ruta (13 cursos)

En 3 rutas:
- 320 Funcionamiento CoDi — Interacción / Mi negocio en internet / Compras y pagos (nueva)
- 345 Transacciones electrónicas — Interacción / Mi negocio en internet / Compras y pagos (nueva)
- 380 Operación de banca en línea — Interacción / Mi negocio en internet / Compras y pagos (nueva)

En 2 rutas:
- 387 Buenas prácticas para el ahorro de agua — Uso eficiente / Desastres
- 95 Cosecha y cultivo de agua — Uso eficiente / Desastres
- 354 Potabilización del agua — Uso eficiente / Desastres
- 120 Manejo higiénico de los alimentos — Alimentos desde casa / Desastres
- 281 Productor de traspatio para autoconsumo — Alimentos desde casa / Desastres
- 342 Introducción a Primer Respondiente — Seguridad, higiene / Desastres
- 393 Uso de aplicaciones de emergencia — Celular / Desastres
- 254 Seguridad en dispositivos móviles — Celular / Interacción
- 373 Regulación de la interacción digital — Interacción / Compras y pagos (nueva)
- 100006 Compras y pagos seguros por internet — Interacción / Compras y pagos (nueva)

Sin la ruta nueva: 10 cursos repetidos, 112 asignaciones, 101 distintos.

Pendiente de confirmar: la columna "Cursos compartidos" de la slide suma 15, contra las
16 apariciones repetidas que arroja este conteo.

## H8 — Decisión: "Compras y pagos digitales" (2026-09-18)

Alta de la ruta 6 en Slide 12, sección Habilidades digitales:

- Columna **Cursos = 6** (373, 100006, 380, 345, 100129, 320). Las 5 repeticiones
  quedan declaradas, no se mueven de sus rutas originales.
- **Inscripciones y certificados cuentan SOLO el curso que no se repite:** 100129
  "Manejo correcto de las tarjetas de crédito". Así el TOTAL de la slide no duplica.
- Implementación: nueva columna `curso_ids_conteo` en el CTE `rutas` del
  `db_mapping`. Las otras 16 rutas la llevan en NULL y cuentan todos sus cursos
  (`ANY(COALESCE(r.curso_ids_conteo, r.curso_ids))`).
- Valores contra PG (corte < 2026-08-01, México, plataformas 1 y 2):
  inscripciones 37,981 · certificados 5,986.

**Deuda técnica pendiente:** 320, 345 y 380 quedan declarados en 3 rutas, y 373 y
100006 en 2. Si más adelante se decide contarlos en todas, hay que revisar el TOTAL
de la slide y la columna "Cursos compartidos" (hoy suma 15 contra 16 apariciones).

## H9 — Rutas nuevas en Slide 12 (2026-09-28)

| Ruta | Sección | Cursos | Inscripciones | Certificados |
|---|---|---|---|---|
| Preparación para buscar trabajo | Emprendimiento | 7 (67, 212, 216, 227, 228, 100059, 100853) | 634,008 | 324,377 |
| Convive mejor con otros | Capacitación básica | 3 (100330, 100380, 100381) | 2,414 | 1,478 |

Ninguno de los 10 cursos pertenece a otra ruta de Slide 12, así que ambas cuentan
todos sus cursos (`curso_ids_conteo = NULL`). Las secciones son provisionales: las
rutas pueden moverse.

Cursos duplicados en la tabla `course` — se toma el ID vivo:

| Curso | ID elegido | Última inscripción | ID descartado | Última inscripción |
|---|---|---|---|---|
| Guía para entrevistas de trabajo | 67 | 2026-09-27 | 329 | 2025-10-31 |
| Disciplina en el trabajo | 212 | 2026-09-27 | 330 | 2026-01-27 |

Cruces con otras slides (no duplican el TOTAL de Slide 12, poblaciones distintas):
212 y 228 están en slide13 (penitenciarios, MySQL); 100330 está en slide20.

Slide 12 queda en 19 rutas y 116 cursos contados. La columna "Cursos totales" de la
slide, que cuenta los compartidos en cada ruta, pasaría de 118 a 128.

## H10 — Revertida la ruta "Compras y pagos digitales" (2026-09-30)

Se quitó del catálogo y del Excel de control. Motivo: se van a reajustar las rutas
de Slide 12 antes de definir dónde caen esos 6 cursos (373, 100006, 380, 345,
100129, 320).

Con eso se retiró también la columna `curso_ids_conteo` y el `COALESCE` del JOIN:
ninguna ruta los usaba, porque sin esa ruta ningún curso se repite. Si vuelve a
hacer falta contar solo parte de una ruta, el mecanismo está en el commit 84abb10.

Estado actual de Slide 12: **18 rutas, 110 cursos, 110 distintos, 0 repetidos.**
El curso 100129 "Manejo correcto de las tarjetas de crédito" queda fuera del
catálogo: era el único que solo existía en esa ruta.
