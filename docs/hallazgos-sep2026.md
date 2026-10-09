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

## H15 — Segunda corrida de producción y separación del drift (2026-10-05)

`pipeline --cut 2026-10-01` tras alinear el corte de slide 20 (H14).
**37 métricas · 87 filas · DQS 0 issues.** `run_id 1c675c58` ·
`catalog_hash 4d8d7798` · `bundle_hash 912692a4`.

Entre las dos corridas de producción (2026-10-02 y 2026-10-05) la hoja cambió en
**41 filas**, pero solo una es por el ajuste. Verificado con `git`: entre los dos
commits de corrida los únicos `db_mapping` distintos son
`slide20_crecimiento_integral_personas_unicas_inscritas` y
`slide20_crecimiento_integral_cursos_ofertados`. Todo lo demás corrió con la query
byte a byte idéntica, así que su variación es de la fuente.

### El ajuste pedido

| Métrica | Antes | Ahora | Delta |
|---|---|---|---|
| Personas únicas inscritas | 17,372 | **19,361** | +1,989 (+11.4%) |

Período fin en la hoja: `2026-08-01` → `2026-10-01`. Los dos meses extra agregan 1,989
personas únicas.

### Drift de la fuente en 3 días: +4,315 / -1,229

Los incrementos son lo esperado en tablas acumulativas: slide 12 sube 744
inscripciones, slide 19 ocho, slide 15 dos.

**Los decrementos merecen atención.** 13 celdas bajaron, y una no es ruido:

| Métrica | Columna | Antes | Ahora | Delta |
|---|---|---|---|---|
| `slide4_cultura_salud_aprende` | acumulado | 1,544,218 | 1,543,790 | **-428** |
| `slide4_cultura_salud_aprende` | dic2026 (proyectado) | 135,136 | 134,717 | -419 |
| `slide4_cultura_salud_aprende` | sep2026 | 101,352 | 101,038 | **-314** |
| `slide4_cultura_salud_aprende` | 2025 | 133,536 | 133,485 | -51 |
| resto (slide 2, 12, 19) | certificados | — | — | -1 a -3 |

Son `COUNT(DISTINCT userId)` con `advance = 100`: un acumulado histórico no debería
bajar. -428 sobre 1.54M es 0.028%, compatible con depuración en la fuente (borrado de
cuentas, dedup de usuarios, o `advance` revertido por debajo de 100). Los -1 a -3 del
resto son del mismo orden y apuntan al mismo origen.

**No es nuestro código**: la query de `slide4_cultura_salud_aprende` es idéntica entre
las dos corridas. Queda anotado para vigilar si el decremento crece — una métrica
acumulada que baja es un síntoma que conviene poder explicar antes de presentarla.

## H16 — Sector "Convivir mejor con otros" en Slide 2 (2026-10-05)

Slide 2 pasa de **6 a 7 sectores** y de **30 a 38 cursos**.

| ID | Curso | ¿Lo teníamos? |
|---|---|---|
| 100330 | Actitud más humana | sí — slide 12 y slide 20 |
| 100380 | Momentos significativos | sí — slide 12 y slide 20 |
| 100381 | El arte de acompañar | sí — slide 12 y slide 20 |
| 305 | Prácticas de cortesía | sí — slide 12, slide 19, slide 4 |
| 100070 | Juego limpio | sí — slide 12 (desde el 2026-10-02) |
| 100063 | Solidaridad | sí — slide 12 (desde el 2026-10-02) |
| 299 | Cultura urbana | sí — slide 1 y slide 12 (en 2 rutas) |
| 348 | Seguridad para todas y todos | sí — slide 12, "¿Cómo mejorar mi entorno?" |

Los 7 primeros son los mismos de la ruta "Convive mejor con otros" de Slide 12. El 8vo
(348) ya estaba en Slide 12 pero en otra ruta. Ningún curso es nuevo para el catálogo.

### El nombre difiere entre slides, a propósito

Slide 2 usa **"ConvivIR mejor con otros"** (infinitivo) y Slide 12 **"ConvivE mejor con
otros"** (imperativo). Así los declaró el usuario en cada caso. No es un typo nuestro —
queda anotado para que nadie lo "corrija" después.

### Dos trampas de Slide 2 que hubo que verificar

**1. Agrupa por `c.name`, no por `courseId`.** El `GROUP BY grupo, curso` usa el nombre
del curso, así que dos IDs con el mismo nombre se fusionan en una sola fila sumando los
usuarios de ambos. Verificado: ninguno de los 8 cursos nuevos choca de nombre con los
30 previos ni entre sí.

Esto importaba porque **"Prácticas de cortesía" existe 6 veces** en `course`:

| ID | Inscripciones | Certificados | Última inscripción |
|---|---|---|---|
| **305** | **186,558** | **102,634** | 2026-10-03 |
| 100109 | 32,206 | 0 | 2026-10-03 |
| 331 | 10,911 | 5,801 | 2026-08-25 (muerto) |
| 297 | 9,911 | 4,209 | 2026-10-03 |
| 100711 | 39 | 0 | 2026-10-03 |
| 100907 | 0 | 0 | nunca |

Y "Solidaridad" dos veces: 100063 (43,920 / 28,794) contra 100704 (340 / 0). Se tomó el
ID dominante y vivo en los dos casos — **305 y 100063**, los mismos que slide 12.

**2. El `CASE` toma la primera rama que coincide.** Un curso en dos sectores se
asignaría en silencio al de arriba y desaparecería del otro. Nueva guarda
`test_slide2_assigns_each_course_to_one_sector`: 38 cursos en 7 sectores, todos
distintos.

El bloque de la hoja no necesitó cambios: `_build_slide2_block` detecta el cambio de
sector y arma el TOTAL desde la lista de subtotales que recolecta, así que soporta
cualquier cantidad de sectores. Por el `ORDER BY grupo, curso` el sector nuevo va a
aparecer entre "Construcción y mantenimiento" y "Educación financiera".

## H17 — Lista final de Slide 2: sale el curso 27 (2026-10-05)

El usuario fijó la lista definitiva: **37 cursos en 7 sectores**. Contra la versión
anterior hay una sola diferencia real.

**Sale el curso 27 "Reparador de aire acondicionado"** de "Construcción y
mantenimiento", que queda en 12 cursos.

No es limpieza de un curso muerto: el 27 tiene **254,823 inscripciones** y actividad al
2026-10-03. Es una decisión de negocio, y coincide con la pestaña "Pobreza" de la hoja
de control del usuario, que tampoco lo traía — lo mismo que ya había quedado anotado en
H3 como la única diferencia entre esa pestaña y el proyecto. Ahora el catálogo se
alinea.

### Consecuencia: las 3 slides de pobreza ya no comparten el universo de construcción

El 27 **sigue contándose** en Slide 1 (`slide1_vivienda`, 17 cursos) y en Slide 12
("Proyectos constructivos y mantenimiento", 17 cursos). Solo sale de Slide 2.

Eso es deliberado y quedó cubierto con `test_slide2_excludes_aire_acondicionado`, que
verifica las dos cosas a la vez: que el 27 no está en slide 2 y que **sí sigue** en
slides 1 y 12. Si alguien lo "arregla" en cualquiera de las dos direcciones, el test lo
caza.

### El orden del `IN` no importa

La lista del usuario trae "Limpieza y mantenimiento" en otro orden que el catálogo
(`6, 100214, 8, 57, 128` contra `6, 57, 8, 100214, 128`). No se tocó: la SQL cierra con
`ORDER BY grupo, curso ASC`, así que las filas de la hoja salen alfabéticas por nombre
de curso sin importar cómo esté escrito el `IN`.

### Nota de operación

La corrida de producción que estaba en vuelo cuando llegó esta lista se cortó antes de
escribir. El proceso carga el catálogo en memoria al arrancar, así que habría publicado
la versión de 38 cursos con el 27 adentro; editar el YAML a mitad de camino no la
afecta.

## H18 — BUG: la hoja `Datos` no limpiaba la columna I (2026-10-05)

Detectado al revisar la hoja después de agregar el sector a Slide 2: **26 filas tenían
restos de la corrida anterior** en la columna I — valores como `Fuente`, `mysql`,
`manual` y `fact_inscription` flotando en filas que ya no les correspondían.

### Causa

`_clear_sheet_if_exists` barría la hoja `Datos` con `endColumnIndex: 8`, o sea hasta la
columna **H**. Pero los bloques de **slides 3, 4 y 12 escriben 9 columnas** (la novena
es `Fuente`). La columna **I nunca se limpiaba**.

Mientras el layout no cambiaba de alto, el bug era invisible: cada corrida reescribía la
columna I con el mismo valor en la misma fila. Al agregar el sector "Convivir mejor con
otros", slide 2 creció 9 filas, **todos los bloques de abajo se corrieron**, y la
columna I quedó con los valores de las filas anteriores. Ejemplo: la fila 57 era
`slide3_capacitate_carso | ... | mysql`; ahora es una fila de slide 2 que arrastra el
`mysql`.

### Arreglo

El ancho ya no se hardcodea: se **deriva** de las constantes `*_TABLE_HEADERS` del
módulo con `_datos_block_width()`. Si mañana un bloque agrega columnas, la limpieza las
cubre sola. El test nuevo compara el `endColumnIndex` contra el máximo real de los
headers, así que el desfase no puede volver en silencio:

```
la limpieza barre 8 columnas pero el bloque más ancho escribe 9
```

### Por qué importaba más de lo que parecía

Era el tipo de bug que solo aparece cuando algo *arriba* cambia de tamaño — y la corrida
donde apareció es justo la que el usuario estaba revisando. Cualquiera leyendo la hoja
habría visto `mysql` en una fila de certificados por sector y, con razón, habría
desconfiado del resto de los números.

### Verificado: 14 celdas sucias -> 0

Corrida limpia tras el fix (`bundle_hash e16ddcf4`): **0 celdas con restos** en las 132
filas de `Datos`, y nada poblado de la columna J en adelante.

Nota sobre cómo medirlo: el primer chequeo reportó 18 restos que no existían. Resolvía
el ancho de cada fila por prefijo del `metric_id` con `startswith`, y
`"slide12_rutas_aprendizaje".startswith("slide1")` es `True` — las filas de slide 12 se
clasificaban como slide 1, y su novena columna legítima (`Fuente`) se contaba como
basura. Hay que resolver por el prefijo **más largo** que coincide, o usar `slide1_` con
guion bajo. Los prefijos `slide1`/`slide12`, `slide2`/`slide20` son ambiguos.

## H19 — El 299 sale de "Convive mejor con otros": el total real es 2,302,728 (2026-10-06)

El usuario preguntó si los certificados de pobreza extrema al corte de octubre eran
2,307,998. **No exactamente**, y la medición lo dejó claro:

| | Valor |
|---|---|
| TOTAL de la hoja (suma de subtotales por sección) | 2,307,998 |
| Certificaciones de los **113 cursos distintos** | **2,302,728** |
| El curso 299 contado dos veces | +5,270 |
| Personas distintas certificadas | 1,320,279 |

`2,302,728 + 5,270 = 2,307,998`, exacto.

El 299 ("Cultura urbana") estaba en dos rutas desde el 2026-10-02 (H11), cuando se
alineó el catálogo con la hoja de control. El TOTAL de la slide es la suma de los
subtotales por sección, así que sus certificaciones entraban dos veces.

**Decisión: el 299 queda solo en "¿Cómo mejorar mi entorno?".** "Convive mejor con
otros" baja de 7 a 6 cursos y el total de la hoja pasa a ser **2,302,728**, el real.

### Vuelve la invariante estricta

Reparto vigente: **113 asignaciones sobre 113 cursos distintos, cero compartidos.** Con
eso el TOTAL de la hoja es otra vez exactamente el total de los cursos de la slide.

La guarda `test_slide12_course_assignments_match_the_declared_sharing` — que llevaba una
allowlist de compartidos — se reemplazó por
`test_slide12_assigns_each_course_to_one_route`, que exige cero duplicados. Más un test
dedicado, `test_slide12_keeps_cultura_urbana_only_in_mi_entorno`, que fija que el 299
está en esa ruta **y en ninguna otra**.

### El 299 NO sale de las otras slides

Sigue contándose en **Slide 1** (`slide1_alimentos`) y en el sector **"Convivir mejor con
otros" de Slide 2**, que el usuario fijó el 2026-10-05 con sus 37 cursos. Son slides
distintas, no comparten total, y no hay doble conteo. El test verifica que siguen ahí,
para que un "arreglo" por simetría rompa.

### Advertencia que conviene repetir antes del deck

Los certificados de slide 12 son **CERTIFICACIONES**, no personas: `COUNT` sin
`DISTINCT`. Al corte `< 2026-10-01` son **2,302,728 certificaciones** sobre **1,320,279
personas distintas** — menos de la mitad. Slides 1 y 2 sí cuentan
`COUNT(DISTINCT userId)`, así que las cifras no son comparables entre slides sin
aclararlo.

## H20 — Auditoría de duplicados en Slides 1 y 2 (2026-10-06)

Pedido tras resolver el 299 en Slide 12. **Resultado: no hay cursos duplicados en
ninguna de las dos.**

| Slide | Asignaciones | Cursos distintos | En más de un grupo |
|---|---|---|---|
| Slide 1 (5 categorías) | 101 | 101 | **0** |
| Slide 2 (7 sectores) | 37 | 37 | **0** |

Tampoco hay repetidos dentro de un mismo array. No había nada que deduplicar.

### Los `compartidos` de Slide 1 NO están fabricados

Primera sospecha descartada: los literales `compartidos` (0, 2, 7, 0, 3 = 12) no
corresponden a cursos repetidos en los arrays, porque no hay ninguno. Pero no son un
invento: el caveat del curso **342** lo explica — *"pertenece SOLO a desastres para no
duplicar certificados; alimentos no lo incluye"*.

O sea que el solapamiento **ya se resolvió asignando cada curso a una sola categoría**, y
los `compartidos` son un conteo **editorial** de cuántos cursos de cada categoría
pertenecen conceptualmente a otra. `Cursos totales = 101 + 12 = 113`. Es el mismo modelo
que el deck usa para Slide 12 (102 + 16 = 118 en H7).

Quedó fijado en `test_slide1_shared_course_literals_are_editorial`, porque son números
que **no se pueden derivar del SQL**: si alguien los mueve, la columna "Cursos totales"
del deck cambia sin que ninguna query lo explique.

### Lo que SÍ encontré: el TOTAL infla personas en las dos slides

Esto no es un duplicado de cursos, es inherente a sumar `COUNT(DISTINCT userId)` por
grupo. Una persona certificada en dos categorías cuenta dos veces.

| Slide | TOTAL publicado | Personas reales | Inflado |
|---|---|---|---|
| Slide 1 | 237,691 | **208,815** | +28,876 (**13.8%**) |
| Slide 2 | 54,145 | **43,461** | +10,684 (**24.6%**) |

Medido en la ventana `2025-09-01 .. 2026-10-01` con los mismos filtros de la métrica.

Slide 2 se infla más porque su grano es **por curso**, no por sector: alguien certificado
en 3 cursos del mismo sector cuenta 3 veces. Slide 1 agrupa por categoría, así que solo
se duplica quien cruza categorías.

**No se cambió nada**: el grano por curso/categoría es el que pidió el deck y está
documentado en los caveats ("Grano por curso: una persona certificada en dos cursos del
mismo sector cuenta en ambos"). Pero si alguna de esas cifras se presenta como "personas
beneficiadas", el número correcto es el de la columna "Personas reales".

### Guardas nuevas

- `test_slide1_assigns_each_course_to_one_category` — 101/101, cero cruces, y el 342 solo
  en desastres.
- `test_slide1_shared_course_literals_are_editorial` — fija los 5 literales, su suma 12 y
  el 113 resultante.
- `test_slide2_assigns_each_course_to_one_sector` ya existía desde H16 (37/37).

## H21 — El 299 se reubica a "Convive mejor con otros" (2026-10-06)

Tercer y último estado del curso 299 (Cultura urbana) en Slide 12, por pedido del
usuario:

| Fecha | Estado | Total de la slide |
|---|---|---|
| 2026-10-02 | En **dos** rutas: "¿Cómo mejorar mi entorno?" y "Convive mejor con otros" | 2,307,998 (inflado) |
| 2026-10-06 | Solo en "¿Cómo mejorar mi entorno?" | 2,302,728 (real) |
| 2026-10-06 | **Solo en "Convive mejor con otros"** | **2,302,728** (sin cambio) |

**El total no se mueve.** Es una mudanza, no una duplicación: siguen siendo los mismos
113 cursos distintos. Y como las dos rutas pertenecen a **Capacitación básica**, tampoco
cambia el subtotal de la sección — solo se mueven ~5,270 certificaciones de una fila de
ruta a la otra.

Reparto resultante:

| Ruta | Antes | Ahora |
|---|---|---|
| ¿Cómo mejorar mi entorno? | 5 cursos | **4** (`142, 364, 348, 100918`) |
| Convive mejor con otros | 6 cursos | **7** (`100330, 100380, 100381, 305, 100070, 100063, 299`) |

Invariante intacta: **113 asignaciones / 113 distintos / cero compartidos.**

### Nota de nomenclatura

El usuario escribió "Convivir mejor con otros" al pedir el cambio, que es el nombre del
**sector de Slide 2**. En Slide 12 la ruta se llama "Convive mejor con otros" y así se
dejó — es el nombre que él mismo declaró para esa slide (ver H16). La diferencia
infinitivo/imperativo entre slides sigue siendo deliberada.

### El 299 ahora

| Slide | Grupo |
|---|---|
| Slide 1 | `slide1_alimentos` |
| Slide 2 | Convivir mejor con otros |
| Slide 12 | **Convive mejor con otros** |

Una vez en cada slide. El test
`test_slide12_keeps_cultura_urbana_only_in_convivencia` fija la ruta nueva, verifica que
"¿Cómo mejorar mi entorno?" quedó exactamente en `[142, 364, 348, 100918]`, y que el 299
**sigue** en slides 1 y 2.

## H22 — Slide 2 con los datos de verdad: 36 cursos (2026-10-06)

Lista definitiva del usuario. Dos cambios contra la versión anterior, los dos en el
sector de convivencia:

**1. Sale el curso 348 "Seguridad para todas y todos".** El sector baja de 8 a 7 cursos
y Slide 2 de 37 a **36**. No es un curso retirado — la exclusión es editorial y vale
solo para Slide 2.

**2. El sector se renombra de "ConvivIR" a "ConvivE mejor con otros"**, unificándose con
el nombre de la ruta de Slide 12. La diferencia infinitivo/imperativo que había quedado
anotada en H16 como deliberada se terminó resolviendo a favor del imperativo.

Reparto final:

| Sector | Cursos |
|---|---|
| Construcción y mantenimiento | 12 |
| Limpieza y mantenimiento | 5 |
| Servicios en transporte | 3 |
| Alimentos y atención | 4 |
| Actividades agropecuarias | 2 |
| Educación financiera | 3 |
| Convive mejor con otros | 7 |
| **TOTAL** | **36** |

Verificado: 36 asignaciones sobre 36 cursos distintos, cero repetidos.

### Los tests de Slide 2 se desacoplaron de las demás slides

Los primeros tests que escribí para los cursos excluidos (27 y 348) verificaban también
que **siguieran** en Slides 1 y 12, para que un "arreglo" por simetría rompiera. Buena
intención, mal lugar: el usuario avisó que las otras slides van a cambiar, así que esas
aserciones habrían roto los tests de Slide 2 por motivos ajenos a Slide 2.

Ahora los cuatro tests de Slide 2 leen **solo** `slide2_empleo_incluyente_por_sector`.
La exclusión editorial se documenta en el docstring y en los caveats, no con una
aserción sobre una lista que se mueve por su cuenta.

También se descartó `test_convivencia_sector_and_route_share_the_name`, que comparaba el
sector de Slide 2 contra la ruta de Slide 12. Antes de borrarlo dejó algo útil: la
escribí asumiendo que las dos listas diferían porque Slide 12 tenía el 348, y el test
falló — en Slide 12 el 348 está en "¿Cómo mejorar mi entorno?", no en convivencia. Tras
quitar el 348 de Slide 2 las dos listas quedaron **idénticas** (los mismos 7 cursos).
Coincidencia a tener en cuenta: mismo nombre y misma lista en dos slides distintas.

## H23 — Slide 1: distribución nueva de 6 categorías y 113 cursos (2026-10-06)

El usuario declaró la distribución definitiva. La vieja `slide1_empleo` se parte en dos
y la slide pasa de **5 categorías / 101 cursos** a **6 / 113**.

| # | Clave | Etiqueta del deck | Cursos | Certificados |
|---|---|---|---|---|
| 1 | `slide1_vivienda` | Formación para mejorar tu vivienda | 19 | 16,644 |
| 2 | `slide1_digital` | Desarrollo de habilidades digitales básicas | 21 | 52,903 |
| 3 | `slide1_alimentos` | Alimentos desde casa, seguridad e higiene elemental | 26 | 64,664 |
| 4 | `slide1_desastres` | Formación para actuar ante desastres naturales | 11 | 49,356 |
| 5 | `slide1_autoempleo` | Crea tu propio empleo | 28 | 56,411 |
| 6 | `slide1_buscar_trabajo` | Activate para buscar trabajo | 8 | 24,892 |
| | | **TOTAL** | **113** | **264,870** |

Verificado ejecutando la SQL nueva contra Postgres: 113 asignaciones sobre 113 cursos
distintos, cero compartidos entre categorías.

### Los `compartidos` pasaron a 0, y el 113 del deck no se mueve

Antes eran `0/2/7/0/3 = 12` sobre 101 cursos en los arrays, con
`Cursos totales = 101 + 12 = 113`: el solapamiento se resolvía asignando cada curso a
una categoría y los 12 restantes se declaraban como literal editorial (ver H20).

La distribución nueva trae los **113 cursos explícitos**, así que no queda nada que
declarar. Los literales quedaron en **0** y la columna "Cursos totales" del deck sigue
dando **113** — pero ahora respaldada por cursos reales en vez de un número que ninguna
query explicaba. La aritmética cierra exacto: `101 + 14 entran − 2 salen = 113`.

### Salen dos cursos activos

| ID | Curso | Inscripciones |
|---|---|---|
| 100212 | Fundamentos de inteligencia artificial | 87,133 |
| 366 | Fundamentos de blockchain | 25,499 |

Son los que un caveat anterior llamaba "cursos IA". **No son cursos retirados** — tienen
volumen real y actividad al 2026-10-03, así que la exclusión es editorial y conviene
poder explicarla.

### Entran 14

`67, 77, 205, 206, 212, 216, 227, 228, 100059, 100129, 100214, 100327, 100853, 100919`.

El **100129** (Manejo correcto de las tarjetas de crédito) **vuelve al catálogo**: había
quedado completamente afuera en el revert de la ruta "Compras y pagos digitales" (H10),
donde era el único curso que no pertenecía a ninguna otra ruta.

### Columna `orden` nueva

La SQL cerraba con `ORDER BY c.metric_id` y la hoja salía alfabética (alimentos,
desastres, digital, empleo, vivienda). Ahora hay una columna `orden` y
`ORDER BY c.orden`, así que las filas respetan el orden de la lista del usuario. El
bloque de la hoja no necesitó cambios: `_build_slide1_block` itera las filas del
manifest y compone el TOTAL con `=SUM`, sin asumir cuántas categorías hay.

### "Busca tu primer trabajo" no se cuenta

Aparece en la lista sin ID de curso y el usuario indicó no contarlo, así que "Activate
para buscar trabajo" queda en **8** cursos en vez de 9. Mismo caso que en Slide 12
(H11), donde también quedó fuera.

### El TOTAL sigue sin ser personas

264,870 es la suma de las 6 categorías. Las **personas únicas reales son 227,064**
(+16.6% de inflado), porque quien certifica en dos categorías cuenta en las dos. Con 6
categorías en vez de 5 el inflado subió: era 13.8% con la distribución anterior.

## H24 — Slide 12 con el layout del deck: 16 rutas, 103 cursos (2026-10-07)

El usuario pasó el layout real de la slide física, con sus 4 secciones y el orden de las
rutas. Slide 12 pasa de **18 rutas / 113 cursos** a **16 / 103**.

| Sección | Rutas | Cursos | Inscripciones | Certificados |
|---|---|---|---|---|
| Construcción | 1 | 19 | 1,452,710 | 175,116 |
| Habilidades digitales | 4 | 19 | 1,427,259 | 405,219 |
| Capacitación básica | 6 | 37 | 2,546,892 | 789,030 |
| Emprendimiento | 5 | 28 | 1,941,006 | 528,093 |
| **TOTAL** | **16** | **103** | **7,367,867** | **1,897,458** |

Verificado ejecutando la SQL contra Postgres. 103 asignaciones sobre 103 cursos
distintos, cero compartidos, y las 4 secciones ocupan órdenes consecutivos.

### Salen dos rutas completas

- **"Convive mejor con otros"** (6 cursos: 305, 100063, 100070, 100330, 100380, 100381).
  El 299 que vivía ahí se queda en "¿Cómo mejorar mi entorno?".
- **"Preparación para buscar trabajo"** (7 cursos: 67, 212, 216, 227, 228, 100059,
  100853).

### Dos rutas que el usuario pasó y NO entraron

**"Compras y pagos digitales"** figuraba en su lista de cursos (con 373 y 100129) **y en
el layout del deck**, pero al pasar el layout pidió explícitamente quitarla. Se siguió
esa instrucción, que es la más reciente. Consecuencia:

- El curso **373** (Regulación de la interacción digital) **sale de Slide 12** — estaba
  en "Interacción con el mundo digital", que baja de 9 a 8 cursos.
- El **100129** no entra.
- Los dos siguen contándose en Slide 1 (`slide1_digital`).

Es una línea revertirlo si la intención era otra.

**"Actívate para encontrar empleo"** venía con 9 cursos en la lista pero no figura en el
layout del deck, así que no entró. Por eso quedan fuera el 100919 y el **100928**.

### El 100928 existe: "Busca tu primer trabajo" ya tiene ID

Durante días figuró como el curso sin ID que bloqueaba el conteo (H11, y descartado en
su momento). Resuelto: **100928**, único con ese nombre en `course`, 51 inscripciones y
4 certificados al 2026-10-06 — un curso recién lanzado. No entra a Slide 12 porque su
ruta no está en el layout, pero el ID queda registrado.

### Entran 4 cursos

| ID | Curso | Ruta |
|---|---|---|
| 77 | Bodeguero (Restaurante) | ¿Cómo preparar mis productos para venderlos? |
| 205 | Guía de autoconstrucción | Proyectos constructivos y mantenimiento |
| 206 | Guía de reparación vivienda rural | Proyectos constructivos y mantenimiento |
| 100214 | Controlador de plagas en espacios urbanos | Actuar en caso de desastres naturales |

### El 118 del deck no es comparable

La slide física muestra `Total 118 / 7,117,053 / 1,850,389`. El 118 viene del modelo
viejo de 102 cursos distintos + 16 apariciones repetidas (H7). Con este layout son
**103 cursos sin repetir**, así que la cifra baja por definición, no porque falten
cursos. Las inscripciones y certificados suben porque el corte se movió a octubre.

### Redacción pendiente

El deck dice **"¿Cómo puedo mejorar mi entorno?"** y **"Planea los gastos y ganancia de
tu negocio"** (singular). El catálogo mantiene "¿Cómo mejorar mi entorno?" y
"...ganancias..." (plural), que es como el usuario las nombró al pasar los cursos con
sus IDs. Sin resolver.

## H25 — De dónde viene la baja de Slide 12 (2026-10-07)

Reconciliación de la caída del TOTAL tras aplicar el layout del deck.

| | Inscripciones | Certificados |
|---|---|---|
| TOTAL antes (18 rutas, 113 cursos) | 8,039,757 | 2,302,728 |
| − salen 14 cursos | −813,472 | −424,316 |
| + entran 4 cursos | +141,152 | +19,062 |
| = esperado | 7,367,437 | 1,897,474 |
| **TOTAL ahora (real)** | **7,367,867** | **1,897,458** |
| residuo | +430 | −16 |

El residuo es drift de la base entre las dos corridas (un día de diferencia), no un
error de reparto. **La baja está explicada al 100%.**

### Los 14 cursos que salieron

| ID | Curso | Inscripciones | Certificados | Ruta de origen |
|---|---|---|---|---|
| 212 | Disciplina en el trabajo | 224,266 | 144,271 | Preparación para buscar trabajo |
| 228 | Estructura de un CV | 140,338 | 63,743 | Preparación para buscar trabajo |
| 67 | Guía para entrevistas de trabajo | 119,151 | 50,640 | Preparación para buscar trabajo |
| 305 | Prácticas de cortesía | 101,724 | 59,557 | Convive mejor con otros |
| 227 | Razones por las que te elige o descarta una empresa | 61,568 | 31,664 | Preparación para buscar trabajo |
| 216 | Investigación empresarial | 51,353 | 17,616 | Preparación para buscar trabajo |
| 100059 | Responsabilidad social | 30,132 | 19,268 | Preparación para buscar trabajo |
| 100070 | Juego limpio | 26,976 | 13,377 | Convive mejor con otros |
| 100063 | Solidaridad | 26,161 | 17,105 | Convive mejor con otros |
| 100853 | Búsqueda de empleo en internet | 15,292 | 1,270 | Preparación para buscar trabajo |
| 373 | Regulación de la interacción digital | 13,631 | 4,105 | Interacción con el mundo digital |
| 100330 | Actitud más humana | 2,793 | 1,664 | Convive mejor con otros |
| 100381 | El arte de acompañar | 59 | 20 | Convive mejor con otros |
| 100380 | Momentos significativos | 28 | 16 | Convive mejor con otros |
| | **SUMA** | **813,472** | **424,316** |

Agrupados por ruta de origen:

| Ruta que salió | Inscripciones | Certificados |
|---|---|---|
| Preparación para buscar trabajo (7 cursos) | 642,100 | 328,472 |
| Convive mejor con otros (6 cursos) | 157,741 | 91,739 |
| Interacción con el mundo digital (solo el 373) | 13,631 | 4,105 |

**El 79% de la baja viene de "Preparación para buscar trabajo"**, y casi la mitad de eso
de un solo curso: el 212 "Disciplina en el trabajo", con 144,271 certificados.

Vale notar que esa ruta reaparecía como "Actívate para encontrar empleo" en la lista de
cursos del usuario, con esos mismos 7 cursos más el 100919 y el 100928. No entró porque
no figura en el layout del deck. **Si se agrega, el TOTAL recupera ~642,100
inscripciones y ~328,472 certificados**, más lo que aporten los dos cursos nuevos.

### Los 4 que entraron

| ID | Curso | Inscripciones | Certificados |
|---|---|---|---|
| 77 | Bodeguero (Restaurante) | 76,643 | 12,583 |
| 206 | Guía de reparación vivienda rural | 30,251 | 2,906 |
| 100214 | Controlador de plagas en espacios urbanos | 18,169 | 2,691 |
| 205 | Guía de autoconstrucción | 16,089 | 882 |
| | **SUMA** | **141,152** | **19,062** |

## H26 — Slide 12 recupera las 2 rutas faltantes: 18 rutas, 114 cursos (2026-10-07)

El usuario reenvió su lista completa y pidió revisar qué faltaba. **16 de las 18 rutas
estaban idénticas y no sobraba nada**; faltaban exactamente 2 rutas con 11 cursos.

| Ruta agregada | Sección | Cursos |
|---|---|---|
| Compras y pagos digitales | Habilidades digitales (orden 6) | `373`, `100129` |
| Actívate para encontrar empleo | Emprendimiento (orden 18) | `100928, 100853, 100919, 212, 228, 67, 216, 227, 100059` |

Las dos van en la sección que mantiene los bloques contiguos: Compras donde la ubica el
layout del deck, y Actívate al final de Emprendimiento.

### Resultado

| Sección | Rutas | Cursos | Inscripciones | Certificados |
|---|---|---|---|---|
| Construcción | 1 | 19 | 1,452,710 | 175,116 |
| Habilidades digitales | 5 | 21 | 1,479,759 | 415,467 |
| Capacitación básica | 6 | 37 | 2,546,892 | 789,030 |
| Emprendimiento | 6 | 37 | 2,586,883 | 856,805 |
| **TOTAL** | **18** | **114** | **8,066,244** | **2,236,418** |

Aporte de las dos rutas nuevas:

| Ruta | Inscripciones | Certificados |
|---|---|---|
| Actívate para encontrar empleo | 645,877 | 328,712 |
| Compras y pagos digitales | 52,500 | 10,248 |
| **suma** | **698,377** | **338,960** |

Coincide con lo proyectado en H25: ahí estimé que recuperar "Preparación para buscar
trabajo" devolvería ~642,100 / ~328,472, y la ruta renombrada con sus 2 cursos extra dio
645,877 / 328,712.

### Notas

- **"Actívate para encontrar empleo" reemplaza a "Preparación para buscar trabajo"**:
  conserva sus 7 cursos y suma el 100919 y el 100928.
- **El 100928 entra al catálogo por primera vez.** Es el "Busca tu primer trabajo" que
  figuró como ID faltante desde H11; aporta poco (51 inscripciones) porque es un curso
  recién lanzado, pero cierra el pendiente.
- **"Compras y pagos digitales" vuelve** tras el revert de H10. El 100129, que había
  quedado completamente fuera del catálogo en ese revert, vuelve a slide 12 y además
  sigue en slide 1.
- El 373 sale de "Interacción con el mundo digital", que queda en 8 cursos.
- Sigue fuera **"Convive mejor con otros"**; su curso 299 permanece en "¿Cómo mejorar mi
  entorno?".
- Reparto: 114 asignaciones sobre 114 cursos distintos, cero compartidos.

## H27 — Vuelve el curso 348 a Slide 2 (2026-10-07)

El usuario detectó que faltaba un curso en "Convive mejor con otros" y repuso el **348
(Seguridad para todas y todos)**. El sector vuelve a 8 cursos y Slide 2 a **37**.

Revierte el recorte del 2026-10-06 (H22), donde el 348 había salido con la "lista de
verdad" de 36 cursos. El renombre de "ConvivIR" a "ConvivE" de ese mismo día **se
mantiene**.

| | Antes de H22 | H22 | Ahora |
|---|---|---|---|
| Sector | 8 cursos | 7 | **8** |
| Slide 2 | 37 cursos | 36 | **37** |

Efecto esperado en la hoja: el subtotal del sector vuelve de 14,755 a **16,778**
certificados (los 2,023 del 348) y el TOTAL de Slide 2 de 52,122 a **54,145**.

### El 348 se cuenta en las tres slides de pobreza

| Slide | Grupo |
|---|---|
| Slide 1 | `slide1_alimentos` |
| Slide 2 | Convive mejor con otros |
| Slide 12 | ¿Cómo mejorar mi entorno? |

Son métricas separadas y no comparten total, así que no hay doble conteo.

### El test se invirtió, no se borró

`test_slide2_excludes_seguridad_para_todas` pasó a
`test_slide2_includes_seguridad_para_todas`. El 348 es el único curso que entró, salió y
volvió a entrar en esta corrida, así que conviene que un cambio accidental rompa en
cualquiera de las dos direcciones. El test también verifica que no aparezca en otro
sector.

### Nota de proceso: el splice casi se llevó los tests de Slide 12

Al reemplazar el test del 348 por posición de texto, el corte se comió el
`@staticmethod` de `_slide12_rutas` y la constante `SLIDE12_PLAN` completa, y rompió 3
tests de Slide 12 que no tenían nada que ver con el cambio. Se detectó porque la suite
los marcó en rojo y se restauraron antes de seguir.

Lección: editar tests por posición de texto es frágil cuando hay helpers compartidos
entre clases de tests. Conviene anclar en el contenido exacto del bloque a reemplazar, o
verificar qué más cayó antes de dar el cambio por bueno.

## H28 — Revisión de Slide 1 contra el deck y entrada del 100928 (2026-10-09)

Comparadas las cifras de la slide física contra lo publicado. **Los beneficiarios
coinciden al número en las 6 categorías y en el total (264,860).** Solo diferían dos
conteos de cursos, y por motivos opuestos.

| Categoría | Cursos deck | Cursos catálogo | Beneficiarios |
|---|---|---|---|
| Formación para mejorar tu vivienda | 19 | 19 ✓ | 16,644 ✓ |
| **Desarrollo de habilidades digitales básicas** | **19** | **21** | 52,901 ✓ |
| Alimentos desde casa, seguridad e higiene | 26 | 26 ✓ | 64,662 ✓ |
| Formación para actuar ante desastres naturales | 11 | 11 ✓ | 49,351 ✓ |
| **Actívate para encontrar empleo** | **9** | 8 → **9** | 24,891 ✓ |
| Crea tu propio empleo | 28 | 28 ✓ | 56,411 ✓ |
| **TOTAL** | **112** | **114** | **264,860 ✓** |

### El 19 de digitales es un error del deck, demostrado

Se midió el aporte de personas únicas de cada uno de los 21 cursos quitándolo de la
lista: **ninguno aporta cero**. El menor es `380` Operación de banca en línea con +159
y el mayor `213` Cómputo básico con +13,404.

Como todos aportan, **ninguna combinación de 19 cursos puede dar 52,901** — sacar
cualquiera baja la cifra. El 52,901 que el deck publica corresponde a los 21, así que el
conteo correcto es 21 y el total de la slide 114, no 112.

Los 2 de diferencia son probablemente `100129` (Manejo correcto de las tarjetas de
crédito, +1,635) y `373` (Regulación de la interacción digital, +510), que en Slide 12
forman la ruta "Compras y pagos digitales". Si se descontaran, la cifra caería ~2,145.

### El 9 de Actívate era correcto: entra el 100928

Acá el deck tenía razón. Cuando se armó la distribución (H23) el usuario listó "Busca tu
primer trabajo" **sin ID** y pidió no contarlo, así que la categoría quedó en 8. El ID se
resolvió después, al pasar el layout de Slide 12: es el **100928**.

**Verificado antes de agregarlo: no mueve ninguna cifra.** Con 8 o con 9 cursos la
categoría da los mismos **24,891** beneficiarios, porque los 4 certificados del 100928
caen fuera de la ventana o son de gente que ya certificó otro curso de la categoría.

Ejecutada la SQL nueva contra Postgres: 114 cursos y las 6 cifras de certificados
idénticas a las publicadas, incluido el total 264,860.
