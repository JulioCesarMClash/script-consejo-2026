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

## H11 — Slide 12 alineada con la hoja de control (2026-10-02)

Fuente: pestaña `Slide12_Sep2025 - Sep2026` del spreadsheet
`1K6aej9AFJGBkttvqYWuGVoDqFlJa1mbo7fm1uk6NY0w` (gid 1763924154).

**El orden ya coincidía.** Las 18 rutas de la hoja están en el mismo orden que el
catálogo, y 17 de 18 traen exactamente los mismos cursos en la misma secuencia. No
hubo nada que reordenar.

**El único cambio: "Convive mejor con otros", de 3 a 7 cursos.** Entran cuatro:

| ID | Curso |
|---|---|
| 305 | Prácticas de cortesía |
| 100070 | Juego limpio |
| 100063 | Solidaridad |
| 299 | Cultura urbana |

### Tres cosas que la hoja traía y hay que saber

**1. La ruta está escrita dos veces.** Filas 76-78 tienen los 3 cursos originales en
su posición; filas 114-120, al final y después de "Preparación para buscar trabajo",
repiten esos 3 y agregan los 4 nuevos. Son 3 filas duplicadas exactas (100330,
100380, 100381).

El usuario confirmó que el bloque de abajo era un **agregado, no un reordenamiento**:
la ruta se queda en el orden 12 dentro de Capacitación básica. La razón es
estructural, no cosmética — `_build_slide12_block` emite un subtotal cada vez que
cambia la sección, así que cada sección tiene que ocupar órdenes consecutivos. Si
Convive se moviera al final, después de "Preparación para buscar trabajo" que es
Emprendimiento, Capacitación básica quedaría partida en dos y la hoja emitiría dos
subtotales de la misma sección, inflando el TOTAL.

**2. El curso 299 queda en dos rutas.** Ya estaba en "¿Cómo mejorar mi entorno?" y
ahora entra también en Convive. Es el **primer curso compartido del catálogo de
Slide 12**. Sus inscripciones y certificados se cuentan una vez por ruta, así que el
TOTAL de la hoja lo incluye dos veces.

La guarda `test_slide12_has_no_duplicated_courses` (que exigía cero repetidos) se
reemplazó por `test_slide12_course_assignments_match_the_declared_sharing`, que fija
el reparto exacto: 114 asignaciones, 113 cursos distintos y una allowlist explícita
de compartidos. Un duplicado accidental sigue rompiendo el test.

**3. "Busca tu primer trabajo" no tiene ID** (fila 113, en "Preparación para buscar
trabajo"). Es la diferencia entre las 118 filas de la hoja y los 117 IDs.
**Descartado por el usuario el 2026-10-02**: queda fuera por ahora, así que
"Preparación para buscar trabajo" se mantiene en 7 cursos y Slide 12 cierra en 114
asignaciones / 113 distintos.

### Números

| | Apariciones | Distintos | Compartidos |
|---|---|---|---|
| Catálogo antes | 110 | 110 | 0 |
| Catálogo ahora | **114** | **113** | 1 (299) |
| Con el ID pendiente | 115 | 114 | 1 |

Las 118 filas de la hoja = 114 reales + 3 duplicadas + 1 sin ID.

### Las 3 filas duplicadas no traían cursos nuevos

Verificado contra `62b8180^`: los 3 IDs que la hoja repite (100330, 100380, 100381)
ya estaban en el catálogo desde que se creó la ruta (commit f9bfdd4). La repetición
de la hoja es cosmética — los mismos 3 cursos escritos dos veces, no cursos extra.

De los 4 que sí entraron hoy, solo 2 eran nuevos para el catálogo completo:

| ID | ¿Estaba antes? | Dónde |
|---|---|---|
| 305 | sí | slide19 seguridad vial, slide4 |
| 299 | sí | slide1 herramientas pobreza, slide12 "¿Cómo mejorar mi entorno?" |
| 100070 | no | solo slide12 |
| 100063 | no | solo slide12 |

305 y 299 cruzan con otras slides, pero esas miden poblaciones distintas: no inflan
el TOTAL de Slide 12. El único cruce que sí lo infla es 299 dentro de la propia
Slide 12.

## H12 — Corrida de prueba del cierre Sep 2026 (2026-10-02)

`pipeline --cut 2026-10-01 --dry-run` contra las bases reales. Datos reales, sin
escribir en Sheets.

**37 manifiestos extraídos. DQS: 0 issues. Bundle hash `a1c55192ab3de961`.**

Las ventanas salieron como se definieron: slides 1 y 2 en `2025-09-01 -> 2026-10-01`,
los acumulados en `Acumulado -> 2026-10-01`, y slide 20 con sus tres períodos
divergentes a propósito.

### Slide 12 — 18 rutas, 114 cursos

| Sección | Rutas | Cursos |
|---|---|---|
| Construcción | 1 | 17 |
| Habilidades digitales | 4 | 20 |
| Capacitación básica | 7 | 43 |
| Emprendimiento | 6 | 34 |
| **TOTAL** | **18** | **114** |

Inscripciones 8,067,045 · Certificados 2,307,986. "Convive mejor con otros" ya
reporta sus 7 cursos (185,745 inscripciones / 97,008 certificados).

### Slide 20 — los tres períodos divergentes, confirmados en vivo

| Métrica | Valor | Ventana |
|---|---|---|
| Inscripciones | 38,795 | 2025-04-03 -> 2026-10-01 |
| Personas únicas inscritas | 17,372 | 2025-04-03 -> **2026-08-01** |
| Cursos ofertados | 77 | 2025-04-03 -> **2026-08-01** |

Cursos ofertados da 77 sobre los 85 de la lista: **8 cursos no registraron ninguna
inscripción** en la ventana.

### El 352,206 de slide 1 era sin el filtro de México

La corrida dio TOTAL=237,683 personas únicas certificadas, contra el `TOTAL=352,206`
que había registrado un caveat. La diferencia no es la ventana — se midió el efecto
de cada variable:

| Variante | Meses | TOTAL |
|---|---|---|
| `2025-09-01 -> 2026-08-01` (ventana del caveat) | 11 | 213,344 |
| `2025-09-01 -> 2026-10-01` (**corrida nueva**) | 13 | **237,683** |
| `2025-07-01 -> 2026-08-01` (ventana del `.env` anterior) | 13 | 245,896 |
| `2025-09-01 -> 2026-08-01` **sin filtro de México** | 11 | 356,657 |

El caveat venía del commit `3e1c62e` (2026-08-17), donde la query **todavía no tenía
`l."countryName" = 'México'`** y las categorías sumaban 96 cursos en vez de 101.
Reproducida sin ese filtro en su misma ventana da 356,657, a 1.3% del valor
registrado — la diferencia restante son los 5 cursos nuevos y el backfill de
certificaciones con fecha retroactiva.

El caveat quedó marcado como OBSOLETO en el catálogo y se agregó el resultado de esta
corrida al lado. La métrica es monótona en la ventana, que era lo que había que
descartar.

### Nota: `base_dic2026` de slide 3 ahora da 0

Su ventana es `[corte, 2027-01-01)`, o sea `[2026-10-01, 2027-01-01)`, y la corrida se
hizo el 2026-10-02. No afecta nada: `base_dic2026` nunca se escribe en la hoja (la
columna dic2026 se calcula con `_project_dic2026` sobre `sep2026`).

La proyección ahora se apoya en 9 meses reales en vez de 7: Carso proyecta
`round(30,953 × 12/9) = 41,271` para dic 2026.

## H13 — Corrida de producción del cierre Sep 2026 (2026-10-02)

`pipeline --cut 2026-10-01` con escritura real. Destino: spreadsheet
`1AI7nEsWPoXsu43AilsGYFVfbiOeNUQm7Kk4PVIMmqog` — "Consejo 2026 - Snapshot Técnico",
el spreadsheet dedicado del snapshot (5 hojas: Control, Datos, Reporte, Errores,
Configuracion). No es la hoja de control del usuario ni el deck.

**37 métricas · 87 filas · DQS 0 issues · hoja `Errores` vacía.**
`run_id 298f5fff` · `catalog_hash 925e62f7` · `bundle_hash d56df02b`.

### El bundle_hash NO sirve para comparar dos corridas

El hash de producción (`d56df02b`) difiere del dry run (`a1c55192`), pero eso es por
construcción, no por drift de datos: `Bundle._canonical_dict` incluye `run_id` y el
`fetched_at` de cada manifiesto, y los dos cambian en cada ejecución. **Dos corridas
nunca van a producir el mismo hash, ni con datos idénticos.**

El hash sirve para lo que fue hecho — detectar que un snapshot ya escrito fue
alterado después — no para reconciliar corridas. Para eso hay que comparar valores.

### Verificación por valores: 0 diferencias

Comparadas las 123 filas de la hoja `Datos` contra el JSON del dry run: **todos los
valores comparables coinciden exactamente** (slide 1 por categoría, las 18 rutas de
slide 12 en cursos/inscripciones/certificados, y los KPIs de slide 20). No hubo drift
entre las dos corridas, separadas por unos 40 minutos.

Los subtotales por sección de slide 12 cierran: 17 + 20 + 43 + 34 = **114 cursos**,
8,067,045 inscripciones, 2,307,986 certificados.

Slide 20 quedó escrita con sus tres períodos divergentes visibles en la hoja, que era
el punto de darle su propia constante:

| Métrica | Valor | Período fin en la hoja |
|---|---|---|
| Inscripciones a cursos | 38,795 | 2026-10-01 |
| Personas únicas inscritas | 17,372 | **2026-08-01** |
| Contenido (hardcoded) | 73 | 2026-10-01 |

## H14 — Slide 20 personas únicas alineada al corte de la corrida (2026-10-05)

Revisando la hoja del snapshot, el usuario vio el `2026-08-01` en la fila "Personas
únicas inscritas" y pidió moverlo a `2026-10-01`. Revierte la decisión del 2026-10-02
de tomar la query al pie de la letra (ver H13), y deja a las tres métricas de slide 20
cerrando en el mismo corte.

**Lo que cambió es el número, no la etiqueta.** La ventana de la query pasa de
`[2025-04-03, 2026-08-01)` a `[2025-04-03, 2026-10-01)`, así que personas únicas y
cursos ofertados suben.

Se movieron las dos: `personas_unicas_inscritas` y `cursos_ofertados` comparten
ventana y universo por diseño, y dejar la segunda en agosto habría reintroducido la
misma divergencia desde otro lado. Cursos ofertados no se pinta en la slide, así que
no era visible en la hoja.

**Lo que NO cambió**: la estructura. Personas únicas sigue usando UNA sola ventana con
los 85 cursos originales, no las dos cohortes de inscripciones. Esa sigue siendo la
diferencia de fondo entre las métricas — personas únicas incluye los 32 cursos
retirados el 2026-06-01, inscripciones no. La fecha nunca fue la diferencia real.

### Consecuencias en el código

- `SLIDE20_PERIODO_FIN_UNICAS` se eliminó. Existía solo para que la hoja no publicara
  una ventana que la query no había usado; sin divergencia es peso muerto.
- `test_no_metric_keeps_the_previous_run_cutoff` vuelve a exigir el conjunto vacío, en
  vez de la allowlist de 2 métricas.
- `test_accumulated_metrics_share_the_oct2026_cutoff` vuelve de 17 a **19** métricas, y
  ahora verifica que las 3 de slide 20 comparten el corte.
- `test_unicas_row_reports_its_own_cutoff` pasó a
  `test_all_rows_share_the_run_cutoff`.

Ningún `db_mapping` conserva `2026-08-01`. Los literales que quedan en el catálogo son
prosa: los resultados históricos de slide 1 y slide 15, y la explicación de este mismo
cambio.
