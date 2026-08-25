/**
 * Apps Script — Slide Painter (Slide-by-slide)
 * Script Consejo 2026: pinta los KPIs del Sheet "Datos" sobre la copia
 * temporal de la presentación de Google Slides.
 *
 * Estrategia: por cada slide del MAPPING, lee el texto actual de CADA shape
 * del slide y construye un mapa (shape_id → texto_actual). Para cada objeto
 * del MAPPING, busca el shape por ID y hace replaceAllText sobre el número
 * (extraído del oldText con regex).
 *
 * Configuración: SPREADSHEET_ID + PRESENTATION_ID abajo.
 * Para correr: seleccionar función y ▶ Run.
 */

// === Configuración =========================================================
const SPREADSHEET_ID = '1AI7nEsWPoXsu43AilsGYFVfbiOeNUQm7Kk4PVIMmqog';
const PRESENTATION_ID = '1uZC2RFa_PlKaTer4RXrRy4AoVGjcrJ8TG6p3GuctJVg';
const SHEET_NAME = 'Datos';

// === Mapeo (extraído de data/mapping-slides.yaml v2) =======================
const MAPPING =
[
{'numero': 1, 'page_id': 'g3948dc9dc6d_2_5', 'objetos': [{'objectId': 'g3948dc9dc6d_2_29', 'rol': 'total_cursos_unicos', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'TOTAL', 'columna': 3}}, {'objectId': 'g3948dc9dc6d_2_14', 'rol': 'cursos_vivienda', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide1_vivienda', 'columna': 3}}, {'objectId': 'g3948dc9dc6d_2_17', 'rol': 'cursos_digital', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide1_digital', 'columna': 3}}, {'objectId': 'g3948dc9dc6d_2_18', 'rol': 'cursos_empleo', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide1_empleo', 'columna': 3}}, {'objectId': 'g3948dc9dc6d_2_24', 'rol': 'cursos_desastres', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide1_desastres', 'columna': 3}}, {'objectId': 'g3948dc9dc6d_2_31', 'rol': 'cert_vivienda', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide1_vivienda', 'columna': 4}}, {'objectId': 'g3948dc9dc6d_2_37', 'rol': 'cert_digital', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide1_digital', 'columna': 4}}, {'objectId': 'g3948dc9dc6d_2_38', 'rol': 'cert_empleo', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide1_empleo', 'columna': 4}}, {'objectId': 'g3948dc9dc6d_2_39', 'rol': 'cert_alimentos', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide1_alimentos', 'columna': 4}}, {'objectId': 'g3948dc9dc6d_2_40', 'rol': 'cert_desastres', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide1_desastres', 'columna': 4}}, {'objectId': 'g3948dc9dc6d_17_326', 'rol': 'total_certificados', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'TOTAL', 'columna': 4}}]},
{'numero': 2, 'page_id': 'g3948dc9dc6d_0_3', 'objetos': [{'objectId': 'g3948dc9dc6d_17_253', 'rol': 'label_sector', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3948dc9dc6d_17_255', 'rol': 'lista_cursos', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide2_empleo_incluyente_por_sector', 'sector': 'Construcción y mantenimiento', 'columna': 2, 'modo': 'list_cursos'}}, {'objectId': 'g3948dc9dc6d_17_256', 'rol': 'valores_cursos', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide2_empleo_incluyente_por_sector', 'sector': 'Construcción y mantenimiento', 'columna': 3, 'modo': 'list_certificados'}}, {'objectId': 'g3948dc9dc6d_17_258', 'rol': 'subtotal', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide2_empleo_incluyente_por_sector', 'sector': 'Subtotal Construcción y mantenimiento', 'columna': 3, 'modo': 'value'}}, {'objectId': 'g3948dc9dc6d_17_278', 'rol': 'label_sector', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3948dc9dc6d_17_279', 'rol': 'lista_cursos', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide2_empleo_incluyente_por_sector', 'sector': 'Alimentos y atención', 'columna': 2, 'modo': 'list_cursos'}}, {'objectId': 'g3948dc9dc6d_17_280', 'rol': 'valores_cursos', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide2_empleo_incluyente_por_sector', 'sector': 'Alimentos y atención', 'columna': 3, 'modo': 'list_certificados'}}, {'objectId': 'g3948dc9dc6d_17_282', 'rol': 'subtotal', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide2_empleo_incluyente_por_sector', 'sector': 'Subtotal Alimentos y atención', 'columna': 3, 'modo': 'value'}}, {'objectId': 'g3948dc9dc6d_17_296', 'rol': 'label_sector', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3948dc9dc6d_17_297', 'rol': 'lista_cursos', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide2_empleo_incluyente_por_sector', 'sector': 'Educación financiera', 'columna': 2, 'modo': 'list_cursos'}}, {'objectId': 'g3948dc9dc6d_17_298', 'rol': 'valores_cursos', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide2_empleo_incluyente_por_sector', 'sector': 'Educación financiera', 'columna': 3, 'modo': 'list_certificados'}}, {'objectId': 'g3948dc9dc6d_17_300', 'rol': 'subtotal', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide2_empleo_incluyente_por_sector', 'sector': 'Subtotal Educación financiera', 'columna': 3, 'modo': 'value'}}, {'objectId': 'g3948dc9dc6d_17_270', 'rol': 'label_sector', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3948dc9dc6d_17_271', 'rol': 'lista_cursos', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide2_empleo_incluyente_por_sector', 'sector': 'Servicios en transporte', 'columna': 2, 'modo': 'list_cursos'}}, {'objectId': 'g3948dc9dc6d_17_272', 'rol': 'valores_cursos', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide2_empleo_incluyente_por_sector', 'sector': 'Servicios en transporte', 'columna': 3, 'modo': 'list_certificados'}}, {'objectId': 'g3948dc9dc6d_17_274', 'rol': 'subtotal', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide2_empleo_incluyente_por_sector', 'sector': 'Subtotal Servicios en transporte', 'columna': 3, 'modo': 'value'}}, {'objectId': 'g3948dc9dc6d_17_262', 'rol': 'label_sector', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3948dc9dc6d_17_263', 'rol': 'lista_cursos', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide2_empleo_incluyente_por_sector', 'sector': 'Limpieza y mantenimiento', 'columna': 2, 'modo': 'list_cursos'}}, {'objectId': 'g3948dc9dc6d_17_264', 'rol': 'valores_cursos', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide2_empleo_incluyente_por_sector', 'sector': 'Limpieza y mantenimiento', 'columna': 3, 'modo': 'list_certificados'}}, {'objectId': 'g3948dc9dc6d_17_266', 'rol': 'subtotal', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide2_empleo_incluyente_por_sector', 'sector': 'Subtotal Limpieza y mantenimiento', 'columna': 3, 'modo': 'value'}}, {'objectId': 'g3948dc9dc6d_17_287', 'rol': 'label_sector', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3948dc9dc6d_17_288', 'rol': 'lista_cursos', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide2_empleo_incluyente_por_sector', 'sector': 'Actividades agropecuarias', 'columna': 2, 'modo': 'list_cursos'}}, {'objectId': 'g3948dc9dc6d_17_289', 'rol': 'valores_cursos', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide2_empleo_incluyente_por_sector', 'sector': 'Actividades agropecuarias', 'columna': 3, 'modo': 'list_certificados'}}, {'objectId': 'g3948dc9dc6d_17_291', 'rol': 'subtotal', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide2_empleo_incluyente_por_sector', 'sector': 'Subtotal Actividades agropecuarias', 'columna': 3, 'modo': 'value'}}, {'objectId': 'g3948dc9dc6d_17_320', 'rol': 'total_general', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide2_empleo_incluyente_por_sector', 'sector': 'TOTAL', 'columna': 3, 'modo': 'value'}}, {'objectId': 'g3948dc9dc6d_17_305', 'rol': 'label_columna', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3948dc9dc6d_17_307', 'rol': 'label_columna', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3948dc9dc6d_17_311', 'rol': 'label_columna', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3948dc9dc6d_17_314', 'rol': 'label_columna', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3948dc9dc6d_17_317', 'rol': 'label_columna', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3948dc9dc6d_0_5', 'rol': 'titulo', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3948dc9dc6d_0_8', 'rol': 'label', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3948dc9dc6d_0_17', 'rol': 'label', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3948dc9dc6d_0_18', 'rol': 'lista', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3948dc9dc6d_0_19', 'rol': 'label', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3948dc9dc6d_0_20', 'rol': 'label', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3948dc9dc6d_0_26', 'rol': 'narrativa', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3948dc9dc6d_0_291', 'rol': 'header_periodo', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3948dc9dc6d_15_2', 'rol': 'lista_narrativa', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3948dc9dc6d_15_3', 'rol': 'label', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}]},
{'numero': 3, 'page_id': 'g375ce6fdc96_0_0', 'objetos': [{'objectId': 'g375ce6fdc96_0_263', 'rol': 'etiqueta_filas', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': null}, {'objectId': 'g375ce6fdc96_0_264', 'rol': 'valor_columna_2025', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide3_*', 'columna': 2, 'modo': 'lista_valores', 'filtro_orden': ['slide3_capacitate_empleo', 'slide3_capacitate_carso', 'slide3_academica_labs']}}, {'objectId': 'g375ce6fdc96_0_265', 'rol': 'valor_columna_sep2026', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide3_*', 'columna': 3, 'modo': 'lista_valores', 'filtro_orden': ['slide3_capacitate_empleo', 'slide3_capacitate_carso', 'slide3_academica_labs']}}, {'objectId': 'g375ce6fdc96_0_266', 'rol': 'valor_columna_dic2026', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide3_*', 'columna': 4, 'modo': 'lista_valores', 'filtro_orden': ['slide3_capacitate_empleo', 'slide3_capacitate_carso', 'slide3_academica_labs']}}, {'objectId': 'g375ce6fdc96_0_267', 'rol': 'valor_columna_acumulado', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide3_*', 'columna': 5, 'modo': 'lista_valores', 'filtro_orden': ['slide3_capacitate_empleo', 'slide3_capacitate_carso', 'slide3_academica_labs']}}]},
{'numero': 12, 'page_id': 'g3761cbcde11_9_59', 'objetos': [{'objectId': 'g3761cbcde11_9_127', 'rol': 'titulo', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3761cbcde11_9_149', 'rol': 'header', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3761cbcde11_9_70', 'rol': 'label_ruta', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide12_rutas_aprendizaje', 'seccion': 'Construcción', 'ruta': 'Proyectos constructivos y mantenimiento', 'columna': 2, 'modo': 'value'}}, {'objectId': 'g3761cbcde11_9_71', 'rol': 'label_seccion', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3761cbcde11_9_82', 'rol': 'orden_seccion', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3761cbcde11_9_86', 'rol': 'total_cursos_seccion', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': null}, {'objectId': 'g3761cbcde11_9_72', 'rol': 'label_ruta', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide12_rutas_aprendizaje', 'seccion': 'Habilidades digitales', 'ruta': '¿Cómo utilizar un celular?', 'columna': 2, 'modo': 'value'}}, {'objectId': 'g3761cbcde11_9_73', 'rol': 'label_ruta', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide12_rutas_aprendizaje', 'seccion': 'Habilidades digitales', 'ruta': '¿Cómo utilizar la computadora?', 'columna': 2, 'modo': 'value'}}, {'objectId': 'g3761cbcde11_9_74', 'rol': 'label_ruta', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide12_rutas_aprendizaje', 'seccion': 'Habilidades digitales', 'ruta': 'Preparación para usar internet', 'columna': 2, 'modo': 'value'}}, {'objectId': 'g3761cbcde11_9_76', 'rol': 'label_ruta', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide12_rutas_aprendizaje', 'seccion': 'Habilidades digitales', 'ruta': 'Interacción con el mundo digital', 'columna': 2, 'modo': 'value'}}, {'objectId': 'g3761cbcde11_9_77', 'rol': 'label_seccion', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3761cbcde11_9_103', 'rol': 'orden_seccion', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3761cbcde11_9_117', 'rol': 'orden', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3761cbcde11_9_111', 'rol': 'label_ruta', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide12_rutas_aprendizaje', 'seccion': 'Capacitación básica', 'ruta': 'Seguridad, higiene y cuidado de la salud', 'columna': 2, 'modo': 'value'}}, {'objectId': 'g3761cbcde11_9_112', 'rol': 'label_ruta', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide12_rutas_aprendizaje', 'seccion': 'Capacitación básica', 'ruta': 'Uso eficiente de recursos', 'columna': 2, 'modo': 'value'}}, {'objectId': 'g3761cbcde11_9_113', 'rol': 'label_ruta', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide12_rutas_aprendizaje', 'seccion': 'Capacitación básica', 'ruta': 'Entendiendo mi situación económica', 'columna': 2, 'modo': 'value'}}, {'objectId': 'g3761cbcde11_9_114', 'rol': 'label_ruta', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide12_rutas_aprendizaje', 'seccion': 'Capacitación básica', 'ruta': '¿Cómo mejorar mi entorno?', 'columna': 2, 'modo': 'value'}}, {'objectId': 'g3761cbcde11_9_115', 'rol': 'label_ruta', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide12_rutas_aprendizaje', 'seccion': 'Capacitación básica', 'ruta': 'Alimentos desde casa', 'columna': 2, 'modo': 'value'}}, {'objectId': 'g3761cbcde11_9_91', 'rol': 'label_ruta', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide12_rutas_aprendizaje', 'seccion': 'Capacitación básica', 'ruta': 'Actuar en caso de desastres naturales', 'columna': 2, 'modo': 'value'}}, {'objectId': 'g3761cbcde11_9_93', 'rol': 'label_ruta', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide12_rutas_aprendizaje', 'seccion': 'Emprendimiento', 'ruta': 'Planea tu negocio', 'columna': 2, 'modo': 'value'}}, {'objectId': 'g3761cbcde11_9_94', 'rol': 'label_ruta', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide12_rutas_aprendizaje', 'seccion': 'Emprendimiento', 'ruta': 'Planea los gastos y ganancias de tu negocio', 'columna': 2, 'modo': 'value'}}, {'objectId': 'g3761cbcde11_9_95', 'rol': 'label_ruta', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide12_rutas_aprendizaje', 'seccion': 'Emprendimiento', 'ruta': '¿Cómo preparar mis productos para venderlos?', 'columna': 2, 'modo': 'value'}}, {'objectId': 'g3761cbcde11_9_96', 'rol': 'label_ruta', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide12_rutas_aprendizaje', 'seccion': 'Emprendimiento', 'ruta': 'Servicio y ventas de tu negocio', 'columna': 2, 'modo': 'value'}}, {'objectId': 'g3761cbcde11_9_97', 'rol': 'label_ruta', 'metrica': null, 'formato_texto': null, 'sheet_lookup': {'categoria': 'slide12_rutas_aprendizaje', 'seccion': 'Emprendimiento', 'ruta': 'Mi negocio en internet', 'columna': 2, 'modo': 'value'}}, {'objectId': 'g3761cbcde11_9_98', 'rol': 'label_seccion', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3761cbcde11_9_153', 'rol': 'label_bloque', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3761cbcde11_9_155', 'rol': 'cursos_competencia', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3761cbcde11_9_162', 'rol': 'valor_competencia', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': null}, {'objectId': 'g3761cbcde11_9_164', 'rol': 'cursos_competencia', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g3761cbcde11_9_165', 'rol': 'valor_competencia', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': null}, {'objectId': 'g37831eb95d4_7_*', 'rol': 'tabla_adicional', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g37b66e555cc_5_*', 'rol': 'tabla_adicional', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}, {'objectId': 'g37b66e555cc_7_*', 'rol': 'tabla_adicional', 'metrica': null, 'formato_texto': null, 'sheet_lookup': null}]},
{'numero': 4, 'page_id': 'g375ce6fdc96_0_268', 'objetos': [{'objectId': 'g375ce6fdc96_0_530', 'rol': 'valor_columna_2024', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide4_*', 'columna': 2, 'modo': 'lista_valores', 'filtro_orden': ['slide4_pilotos_seguridad_vial', 'slide4_aprende_seguridad_vial', 'slide4_cultura_salud_aprende']}}, {'objectId': 'g375ce6fdc96_0_531', 'rol': 'valor_columna_sep2025', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide4_*', 'columna': 3, 'modo': 'lista_valores', 'filtro_orden': ['slide4_pilotos_seguridad_vial', 'slide4_aprende_seguridad_vial', 'slide4_cultura_salud_aprende']}}, {'objectId': 'g375ce6fdc96_0_532', 'rol': 'valor_columna_dic2025', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide4_*', 'columna': 4, 'modo': 'lista_valores', 'filtro_orden': ['slide4_pilotos_seguridad_vial', 'slide4_aprende_seguridad_vial', 'slide4_cultura_salud_aprende']}}, {'objectId': 'g375ce6fdc96_0_533', 'rol': 'valor_columna_acumulado', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide4_*', 'columna': 5, 'modo': 'lista_valores', 'filtro_orden': ['slide4_pilotos_seguridad_vial', 'slide4_aprende_seguridad_vial', 'slide4_cultura_salud_aprende']}}]},
{'numero': 7, 'page_id': 'g375ce6fdc96_0_366', 'objetos': [{'objectId': 'g3735641ff7a_1_55', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide7_capacitate_empleo', 'columna': 2}}, {'objectId': 'g3735641ff7a_1_66', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide7_pruebat', 'columna': 2}}, {'objectId': 'g3735641ff7a_1_69', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide7_khan', 'columna': 2}}, {'objectId': 'g3735641ff7a_1_72', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide7_academica_labs', 'columna': 2}}, {'objectId': 'g3735641ff7a_1_76', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide7_capacitate_carso', 'columna': 2}}, {'objectId': 'g3735641ff7a_1_79', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide7_capacitate_empleo', 'columna': 2}}]},
{'numero': 8, 'page_id': 'g375ce6fdc96_0_371', 'objetos': [{'objectId': 'g375d3d93919_0_94', 'rol': 'valor_card', 'metrica': 'pabellon_visitantes', 'formato_texto': '{valor:,.0f}', 'sheet_lookup': null}, {'objectId': 'g375d3d93919_0_105', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide8_biblioteca_digital', 'columna': 2}}, {'objectId': 'g375d3d93919_0_110', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide8_la_merced', 'columna': 2}}, {'objectId': 'g375d3d93919_0_120', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide8_centro_estudios', 'columna': 2}}, {'objectId': 'g375d3d93919_0_125', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide8_cultura_salud_aprende', 'columna': 2}}]},
{'numero': 11, 'page_id': 'g375ce6fdc96_0_381', 'objetos': [{'objectId': 'g3735641ff7a_1_315', 'rol': 'valor_total', 'metrica': 'redes_comunidad_aprende', 'formato_texto': '{valor:,.0f}', 'sheet_lookup': null}]},
{'numero': 13, 'page_id': 'g3735641ff7a_1_115', 'objetos': [{'objectId': 'g3735641ff7a_1_133', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide13_penitenciarios', 'sheet_orden': 6, 'columna': 2}}, {'objectId': 'g3735641ff7a_1_137', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide13_penitenciarios', 'sheet_orden': 2, 'columna': 2}}, {'objectId': 'g3735641ff7a_1_141', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide13_penitenciarios', 'sheet_orden': 3, 'columna': 2}}, {'objectId': 'g3735641ff7a_1_145', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide13_penitenciarios', 'sheet_orden': 5, 'columna': 2}}, {'objectId': 'g3735641ff7a_1_149', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide13_penitenciarios', 'sheet_orden': 1, 'columna': 2}}, {'objectId': 'g3735641ff7a_1_153', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:.2f}', 'sheet_lookup': {'categoria': 'slide13_penitenciarios', 'sheet_orden': 4, 'columna': 2}}]},
{'numero': 15, 'page_id': 'g3735641ff7a_1_93', 'objetos': [{'objectId': 'g3735641ff7a_1_99', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide15_mario_molina', 'sheet_orden': 2, 'columna': 2}}, {'objectId': 'g374967fdf7d_0_5', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide15_mario_molina', 'sheet_orden': 1, 'columna': 2}}]},
{'numero': 19, 'page_id': 'g3735641ff7a_1_161', 'objetos': [{'objectId': 'g3735641ff7a_1_173', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': null}, {'objectId': 'g3735641ff7a_1_222', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': null}]},
{'numero': 20, 'page_id': 'g3752707f08b_0_37', 'objetos': [{'objectId': 'g3752707f08b_0_52', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide20_crecimiento_integral', 'sheet_orden': 1, 'columna': 2}}, {'objectId': 'g3752707f08b_0_43', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': {'categoria': 'slide20_crecimiento_integral', 'sheet_orden': 2, 'columna': 2}}, {'objectId': 'g3752707f08b_0_60', 'rol': 'valor_card', 'metrica': null, 'formato_texto': '{valor:,.0f}', 'sheet_lookup': null}]}
];

// === Helpers ================================================================

function formatValue(value, formatoTexto) {
  if (value === null || value === undefined || value === '') return '';
  const num = Number(value);
  if (isNaN(num)) return String(value);

  if (formatoTexto === '{valor:,.0f}') {
    return num.toLocaleString('en-US', { maximumFractionDigits: 0 });
  }
  if (formatoTexto === '{valor:.2f}') {
    return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  return String(value);
}

function resolveValue(obj, sheetIndex, sheetRows) {
  if (obj.metrica) {
    const row = sheetIndex[obj.metrica];
    return row ? row[2] : null;
  }

  if (obj.sheet_lookup) {
    const lookup = obj.sheet_lookup;
    const cat = lookup.categoria;
    const colIdx = lookup.columna;

    if (lookup.sector) {
      const lines = [];
      let lastSector = '';
      let inTarget = false;
      for (let i = 0; i < sheetRows.length; i++) {
        const row = sheetRows[i];
        if (row[0] !== cat) continue;
        const rowSector = (row[1] || '').trim();
        const rowCurso = (row[2] || '').trim();
        if (rowSector) {
          lastSector = rowSector;
          inTarget = (lastSector === lookup.sector);
          if (inTarget && lookup.modo !== 'list_cursos' && lookup.modo !== 'list_certificados') {
            if (colIdx < row.length) {
              const v = String(row[colIdx]);
              if (v.trim()) lines.push(v);
            }
          }
          continue;
        }
        if (!inTarget) continue;
        if (lookup.modo === 'list_cursos') {
          if (rowCurso) lines.push(rowCurso);
        } else if (lookup.modo === 'list_certificados') {
          if (colIdx < row.length) {
            const v = String(row[colIdx]);
            if (v.trim()) lines.push(v);
          }
        } else {
          if (!rowCurso && colIdx < row.length) {
            const v = String(row[colIdx]);
            if (v.trim()) lines.push(v);
          }
        }
      }
      if (lookup.modo === 'list_cursos' || lookup.modo === 'list_certificados') {
        return lines.length ? lines.join(String.fromCharCode(10)) : null;
      }
      return lines.length ? lines[lines.length - 1] : null;
    }

    if (lookup.sheet_orden !== undefined) {
      let count = 0;
      for (let i = 0; i < sheetRows.length; i++) {
        if (sheetRows[i][0] === cat) {
          count++;
          if (count === lookup.sheet_orden) {
            const row = sheetRows[i];
            return colIdx < row.length ? row[colIdx] : null;
          }
        }
      }
    }

    if (lookup.seccion && lookup.ruta) {
      for (let i = 0; i < sheetRows.length; i++) {
        const row = sheetRows[i];
        if (row[0] === cat &&
            (row[1] || '').trim() === lookup.seccion &&
            (row[2] || '').trim() === lookup.ruta) {
          return colIdx < row.length ? row[colIdx] : null;
        }
      }
    }

    if (lookup.modo === 'lista_valores' && lookup.filtro_orden) {
      const lines = [];
      for (const catName of lookup.filtro_orden) {
        for (let i = 0; i < sheetRows.length; i++) {
          if (sheetRows[i][0] === catName) {
            const row = sheetRows[i];
            if (colIdx < row.length) {
              const v = String(row[colIdx]);
              if (v.trim()) lines.push(v);
            }
            break;
          }
        }
      }
      if (lines.length) return lines.join(String.fromCharCode(10));
    } else {
      const row = sheetIndex[cat];
      if (row && colIdx < row.length) return row[colIdx];
    }
  }

  return null;
}

function buildSheetIndex(rows) {
  const idx = {};
  for (let i = 0; i < rows.length; i++) {
    const cat = String(rows[i][0] || '').trim();
    if (cat && !cat.startsWith('Categoría')) {
      if (!idx[cat]) {
        idx[cat] = rows[i];
      }
    }
  }
  return idx;
}

// Busca un shape por objectId iterando slide.getShapes(). Equivalente a
// slide.getShapeById(objectId) que no existe en Apps Script.
function findShapeByObjectId(slide, objectId) {
  try {
    const shapes = slide.getShapes();
    for (let i = 0; i < shapes.length; i++) {
      if (shapes[i].getObjectId() === objectId) return shapes[i];
    }
  } catch (e) {}
  return null;
}


// Construye un nuevo texto preservando el prefix del oldText (label)
// y reemplazando el número (searchText) por newText.
// Si oldText es "Total de beneficiarios\n         21,578" y searchText es "21,578",
// devuelve "Total de beneficiarios\n         13,572".
function constructReplace(oldText, searchText, newText) {
  if (!searchText) return newText;
  const idx = oldText.lastIndexOf(searchText);
  if (idx === -1) return newText;
  return oldText.substring(0, idx) + newText + oldText.substring(idx + searchText.length);
}

// Construye un mapa {objectId: texto_actual} para todos los shapes del slide.
// Como Apps Script SlidesApp no expone pageElements directamente, usamos
// getShapes() + iteramos para cada shape.
function buildShapeTextMap(slide) {
  const map = {};
  let shapeCount = 0;
  let textSuccess = 0;
  let textFail = 0;
  try {
    const shapes = slide.getShapes();
    Logger.log('  [debug] shapes.length=' + shapes.length);
    for (let i = 0; i < shapes.length; i++) {
      const shape = shapes[i];
      shapeCount++;
      let id = null;
      try { id = shape.getObjectId(); } catch(e) { Logger.log('  [debug] shape[' + i + '].getId() failed: ' + e.message); }
      let txt = '';
      try {
        txt = shape.getText().asString();
        textSuccess++;
      } catch(e) {
        textFail++;
        Logger.log('  [debug] shape[' + i + '].getText() failed: ' + e.message);
      }
      if (id) map[id] = txt;
    }
    Logger.log('  [debug] shapeCount=' + shapeCount + ' textSuccess=' + textSuccess + ' textFail=' + textFail);
  } catch (e) {
    Logger.log('  [debug] getShapes() failed: ' + e.message);
  }
  Logger.log('  [debug] map keys (' + Object.keys(map).length + '): ' + JSON.stringify(Object.keys(map).slice(0, 5)));
  return map;
}

// === Entry point ===========================================================

function paintSlide(slide, slideMap, sheetIndex, sheetRows) {
  let painted = 0;
  let skipped = 0;
  const skippedIds = [];

  const shapeMap = buildShapeTextMap(slide);

  for (const obj of slideMap.objetos) {
    const value = resolveValue(obj, sheetIndex, sheetRows);
    if (value === null || value === '') {
      skipped++;
      continue;
    }

    const newText = formatValue(value, obj.formato_texto);
    const oldText = shapeMap[obj.objectId];

    if (oldText === undefined) {
      // Shape no encontrado — el ID no corresponde a un shape de este slide.
      // Puede ser una imagen, línea, tabla, o ID incorrecto. Skip.
      skippedIds.push(obj.objectId + ' (shape no encontrado)');
      skipped++;
      continue;
    }

    if (!oldText || oldText === newText) {
      if (!oldText) {
        // Shape vacío — usar setText
        const shape = findShapeByObjectId(slide, obj.objectId);
        if (shape) shape.getText().setText(newText);
      }
      painted++;
      continue;
    }

    // Buscar el shape específico por objectId (NO usar slide.replaceAllText
    // porque afecta todo el slide).
    const shape = findShapeByObjectId(slide, obj.objectId);
    if (!shape) {
      skippedIds.push(obj.objectId + ' (shape no encontrado)');
      skipped++;
      continue;
    }

    // Si oldText es multilínea (lista de cursos/valores), replaceText exacto
    // sobre el texto completo. Si es texto simple (un número/label), extraemos el número.
    if (oldText.indexOf(String.fromCharCode(10)) >= 0 || oldText.length > 50) {
      // Texto largo o multilínea: replaceText exacto
      shape.getText().setText(constructReplace(oldText, newText));
    } else {
      // Texto simple: extraer número al final y reemplazar solo ese número
      const numberMatch = oldText.match(/[\d,]+(?:\.\d+)?$/);
      if (numberMatch && obj.formato_texto && numberMatch[0] !== newText) {
        shape.getText().setText(constructReplace(numberMatch[0], newText));
      } else {
        shape.getText().setText(constructReplace(oldText, newText));
      }
    }
    painted++;
  }

  return { painted, skipped, skippedIds };
}

function paintSlides() {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  const sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    SpreadsheetApp.getUi().alert('Hoja "' + SHEET_NAME + '" no encontrada.');
    return;
  }

  const allRows = sheet.getDataRange().getValues();
  const sheetIndex = buildSheetIndex(allRows);
  Logger.log('Sheet index: ' + Object.keys(sheetIndex).length + ' categorias');

  const presentation = SlidesApp.openById(PRESENTATION_ID);

  let totalPainted = 0;
  let totalSkipped = 0;
  const allSkippedIds = [];

  for (const slideMap of MAPPING) {
    const slide = presentation.getSlideById(slideMap.page_id);
    if (!slide) {
      Logger.log('SKIP slide ' + slideMap.numero + ': page no encontrada');
      totalSkipped += slideMap.objetos.length;
      continue;
    }

    const result = paintSlide(slide, slideMap, sheetIndex, allRows);
    totalPainted += result.painted;
    totalSkipped += result.skipped;
    for (const id of result.skippedIds) {
      allSkippedIds.push('slide' + slideMap.numero + ' / ' + id);
    }

    Logger.log('Slide ' + slideMap.numero + ': pintados=' + result.painted + ' saltados=' + result.skipped);
  }

  Logger.log('TOTAL: Pintados=' + totalPainted + ' | Saltados=' + totalSkipped);
  if (allSkippedIds.length > 0) {
    Logger.log('IDs saltados:');
    for (const id of allSkippedIds) Logger.log('  - ' + id);
  }

  return { painted: totalPainted, skipped: totalSkipped };
}

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('🎨 Slide Painter')
    .addItem('Pintar Slide desde Sheet', 'paintSlides')
    .addToUi();
}

function paintSlide1Only() {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  const sheet = ss.getSheetByName(SHEET_NAME);
  const allRows = sheet.getDataRange().getValues();
  const sheetIndex = buildSheetIndex(allRows);

  const slideMap = MAPPING.find(s => s.numero === 1);
  if (!slideMap) {
    Logger.log('Slide 1 no encontrada en mapping');
    return;
  }

  const presentation = SlidesApp.openById(PRESENTATION_ID);
  const slide = presentation.getSlideById(slideMap.page_id);
  if (!slide) {
    Logger.log('Slide 1 no encontrada: ' + slideMap.page_id);
    return;
  }

  const shapeMap = buildShapeTextMap(slide);
  Logger.log('Shapes en slide 1: ' + Object.keys(shapeMap).length);
  Logger.log('Shape IDs encontrados: ' + JSON.stringify(Object.keys(shapeMap)));
  Logger.log('Mapping IDs esperados: ' + JSON.stringify(slideMap.objetos.map(o => o.objectId)));

  // Verificar si getShapes() funciona diferente
  let allShapes = [];
  try { allShapes = slide.getShapes(); } catch(e) {}
  Logger.log('slide.getShapes() retorna: ' + allShapes.length + ' shapes');
  if (allShapes.length > 0 && allShapes.length < 5) {
    for (let s of allShapes) {
      try { Logger.log('  shape id=' + s.getObjectId() + ' tipo=' + (s.getShapeType ? s.getShapeType() : '?')); } catch(e) {}
    }
  }

  let painted = 0;
  let skipped = 0;
  for (const obj of slideMap.objetos) {
    const value = resolveValue(obj, sheetIndex, allRows);
    if (value === null || value === '') {
      Logger.log('SKIP (no value) ' + obj.objectId + ' rol=' + obj.rol);
      skipped++;
      continue;
    }
    const newText = formatValue(value, obj.formato_texto);
    const oldText = shapeMap[obj.objectId];
    Logger.log('Intentando ' + obj.objectId + ' rol=' + obj.rol + ' value=' + value + ' newText="' + newText + '" oldText=' + (oldText !== undefined ? '"' + oldText.substring(0, 50) + '"' : 'UNDEFINED'));

    if (oldText === undefined) {
      Logger.log('  SKIP (shape no encontrado)');
      skipped++;
      continue;
    }
    const shape = findShapeByObjectId(slide, obj.objectId);
    if (!shape) {
      Logger.log('  SKIP (shape no encontrado en iteration): ' + obj.objectId);
      skipped++;
      continue;
    }
    if (!oldText || oldText === newText) {
      if (!oldText) shape.getText().setText(newText);
      painted++;
      continue;
    }
    if (oldText.indexOf(String.fromCharCode(10)) >= 0 || oldText.length > 50) {
      shape.getText().setText(constructReplace(oldText, newText));
    } else {
      const numberMatch = oldText.match(/[\d,]+(?:\.\d+)?$/);
      if (numberMatch && obj.formato_texto && numberMatch[0] !== newText) {
        shape.getText().setText(constructReplace(numberMatch[0], newText));
      } else {
        shape.getText().setText(constructReplace(oldText, newText));
      }
    }
    painted++;
  }

  Logger.log('Slide 1 — Pintados: ' + painted + ' | Saltados: ' + skipped);
}
