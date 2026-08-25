/**
 * Apps Script — Slide painter
 * ---------------------------------------------------------------------------
 * Script Consejo 2026: pinta los KPIs del Sheet "Datos" sobre la copia
 * temporal de la presentación de Google Slides.
 *
 * Flujo:
 *   1. Lee el Sheet activo (hoja `Datos`) como matriz.
 *   2. Construye un índice por Categoría (columna A).
 *   3. Para cada slide mapeada y cada objeto, resuelve el valor del Sheet
 *      usando el `rol` y/o `metrica` del mapping, y lo escribe sobre el
 *      text_box correspondiente en la Slide (vía `SlidesApp`).
 *.
 * Decisión 2026-08-19: la Slide física es la "salida" — los valores
 * actuales se sobrescriben con los del Sheet. Para IDs con `metrica: null`,
 * se usa la heurística por `rol` (sheetCategory + columna).
 *
 * IDs sin Sheet → se saltean con warning (no rompe la corrida).
 *
 * Mapeo generado a partir de data/mapping-slides.yaml v2 (12 slides).
 * Para regenerar este código cuando cambie el YAML, correr:
 *   .venv/bin/python scripts/regen_mapping_inline.py > apps-script/code.gs
 * (TODO: crear script).
 *
 * Deployment:
 *   1. Crear nuevo Apps Script en script.google.com (o vía clasp).
 *   2. Pegar este archivo en Code.gs.
 *   3. Autorizar acceso a Sheets + Slides.
 *   4. Crear trigger manual (menú personalizado "Pintar Slide") o ejecutar
 *      `paintSlides()` desde el editor.
 */

// === Configuración =========================================================
const SPREADSHEET_ID = '1AI7nEsWPoXsu43AilsGYFVfbiOeNUQm7Kk4PVIMmqog';
const PRESENTATION_ID = '1uZC2RFa_PlKaTer4RXrRy4AoVGjcrJ8TG6p3GuctJVg';
const SHEET_NAME = 'Datos';

// === Mapeo (extraído de data/mapping-slides.yaml v2) =======================
// Formato: cada slide es { numero, page_id, objetos: [{ objectId, rol, metrica, formato_texto }] }
const MAPPING =

[
  {
    "numero": 1,
    "page_id": "g3948dc9dc6d_2_5",
    "objetos": [
      {
        "objectId": "g3948dc9dc6d_2_29",
        "rol": "total_cursos_unicos",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_2_14",
        "rol": "cursos_vivienda",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_2_17",
        "rol": "cursos_digital",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_2_18",
        "rol": "cursos_empleo",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_2_24",
        "rol": "cursos_desastres",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_2_31",
        "rol": "cert_vivienda",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_2_37",
        "rol": "cert_digital",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_2_38",
        "rol": "cert_empleo",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_2_39",
        "rol": "cert_alimentos",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_2_40",
        "rol": "cert_desastres",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_17_326",
        "rol": "total_certificados",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      }
    ]
  },
  {
    "numero": 2,
    "page_id": "g3948dc9dc6d_0_3",
    "objetos": [
      {
        "objectId": "g3948dc9dc6d_17_253",
        "rol": "label_sector",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_17_255",
        "rol": "lista_cursos",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_17_256",
        "rol": "valores_cursos",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_17_258",
        "rol": "subtotal",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_17_278",
        "rol": "label_sector",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_17_279",
        "rol": "lista_cursos",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_17_280",
        "rol": "valores_cursos",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_17_282",
        "rol": "subtotal",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_17_296",
        "rol": "label_sector",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_17_297",
        "rol": "lista_cursos",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_17_298",
        "rol": "valores_cursos",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_17_300",
        "rol": "subtotal",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_17_270",
        "rol": "label_sector",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_17_271",
        "rol": "lista_cursos",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_17_272",
        "rol": "valores_cursos",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_17_274",
        "rol": "subtotal",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_17_262",
        "rol": "label_sector",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_17_263",
        "rol": "lista_cursos",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_17_264",
        "rol": "valores_cursos",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_17_266",
        "rol": "subtotal",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_17_287",
        "rol": "label_sector",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_17_288",
        "rol": "lista_cursos",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_17_289",
        "rol": "valores_cursos",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_17_291",
        "rol": "subtotal",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_17_320",
        "rol": "total_general",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3948dc9dc6d_17_305",
        "rol": "label_columna",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_17_307",
        "rol": "label_columna",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_17_311",
        "rol": "label_columna",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_17_314",
        "rol": "label_columna",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_17_317",
        "rol": "label_columna",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_0_5",
        "rol": "titulo",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_0_8",
        "rol": "label",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_0_17",
        "rol": "label",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_0_18",
        "rol": "lista",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_0_19",
        "rol": "label",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_0_20",
        "rol": "label",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_0_26",
        "rol": "narrativa",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_0_291",
        "rol": "header_periodo",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_15_2",
        "rol": "lista_narrativa",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3948dc9dc6d_15_3",
        "rol": "label",
        "metrica": null,
        "formato_texto": null
      }
    ]
  },
  {
    "numero": 3,
    "page_id": "g375ce6fdc96_0_0",
    "objetos": [
      {
        "objectId": "g375ce6fdc96_0_263",
        "rol": "etiqueta_filas",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g375ce6fdc96_0_264",
        "rol": "valor_columna_2025",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g375ce6fdc96_0_265",
        "rol": "valor_columna_sep2026",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g375ce6fdc96_0_266",
        "rol": "valor_columna_dic2026",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g375ce6fdc96_0_267",
        "rol": "valor_columna_acumulado",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      }
    ]
  },
  {
    "numero": 12,
    "page_id": "g3761cbcde11_9_59",
    "objetos": [
      {
        "objectId": "g3761cbcde11_9_127",
        "rol": "titulo",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_149",
        "rol": "header",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_70",
        "rol": "label_ruta",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_71",
        "rol": "label_seccion",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_82",
        "rol": "orden_seccion",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_86",
        "rol": "total_cursos_seccion",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3761cbcde11_9_72",
        "rol": "label_ruta",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_73",
        "rol": "label_ruta",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_74",
        "rol": "label_ruta",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_76",
        "rol": "label_ruta",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_77",
        "rol": "label_seccion",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_103",
        "rol": "orden_seccion",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_117",
        "rol": "orden",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_111",
        "rol": "label_ruta",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_112",
        "rol": "label_ruta",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_113",
        "rol": "label_ruta",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_114",
        "rol": "label_ruta",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_115",
        "rol": "label_ruta",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_91",
        "rol": "label_ruta",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_93",
        "rol": "label_ruta",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_94",
        "rol": "label_ruta",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_95",
        "rol": "label_ruta",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_96",
        "rol": "label_ruta",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_97",
        "rol": "label_ruta",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_98",
        "rol": "label_seccion",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_153",
        "rol": "label_bloque",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_155",
        "rol": "cursos_competencia",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_162",
        "rol": "valor_competencia",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3761cbcde11_9_164",
        "rol": "cursos_competencia",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g3761cbcde11_9_165",
        "rol": "valor_competencia",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g37831eb95d4_7_*",
        "rol": "tabla_adicional",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g37b66e555cc_5_*",
        "rol": "tabla_adicional",
        "metrica": null,
        "formato_texto": null
      },
      {
        "objectId": "g37b66e555cc_7_*",
        "rol": "tabla_adicional",
        "metrica": null,
        "formato_texto": null
      }
    ]
  },
  {
    "numero": 4,
    "page_id": "g375ce6fdc96_0_268",
    "objetos": [
      {
        "objectId": "g375ce6fdc96_0_530",
        "rol": "valor_columna_2024",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g375ce6fdc96_0_531",
        "rol": "valor_columna_sep2025",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g375ce6fdc96_0_532",
        "rol": "valor_columna_dic2025",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g375ce6fdc96_0_533",
        "rol": "valor_columna_acumulado",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      }
    ]
  },
  {
    "numero": 7,
    "page_id": "g375ce6fdc96_0_366",
    "objetos": [
      {
        "objectId": "g3735641ff7a_1_55",
        "rol": "valor_card",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3735641ff7a_1_66",
        "rol": "valor_card",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3735641ff7a_1_69",
        "rol": "valor_card",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3735641ff7a_1_72",
        "rol": "valor_card",
        "metrica": "academica_usuarios",
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3735641ff7a_1_76",
        "rol": "valor_card",
        "metrica": "capacitarte_carso_usuarios",
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3735641ff7a_1_79",
        "rol": "valor_card",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      }
    ]
  },
  {
    "numero": 8,
    "page_id": "g375ce6fdc96_0_371",
    "objetos": [
      {
        "objectId": "g375d3d93919_0_94",
        "rol": "valor_card",
        "metrica": "pabellon_visitantes",
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g375d3d93919_0_105",
        "rol": "valor_card",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g375d3d93919_0_110",
        "rol": "valor_card",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g375d3d93919_0_120",
        "rol": "valor_card",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g375d3d93919_0_125",
        "rol": "valor_card",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      }
    ]
  },
  {
    "numero": 11,
    "page_id": "g375ce6fdc96_0_381",
    "objetos": [
      {
        "objectId": "g3735641ff7a_1_315",
        "rol": "valor_total",
        "metrica": "redes_comunidad_aprende",
        "formato_texto": "{valor:,.0f}"
      }
    ]
  },
  {
    "numero": 13,
    "page_id": "g3735641ff7a_1_115",
    "objetos": [
      {
        "objectId": "g3735641ff7a_1_133",
        "rol": "valor_card",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3735641ff7a_1_137",
        "rol": "valor_card",
        "metrica": "slide13_penitenciarios_certificados",
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3735641ff7a_1_141",
        "rol": "valor_card",
        "metrica": "slide13_penitenciarios_usuarios_registrados",
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3735641ff7a_1_145",
        "rol": "valor_card",
        "metrica": "slide13_penitenciarios_cursos_ofertados",
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3735641ff7a_1_149",
        "rol": "valor_card",
        "metrica": "slide13_penitenciarios_inscripciones",
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3735641ff7a_1_153",
        "rol": "valor_card",
        "metrica": null,
        "formato_texto": "{valor:.2f}"
      }
    ]
  },
  {
    "numero": 15,
    "page_id": "g3735641ff7a_1_93",
    "objetos": [
      {
        "objectId": "g3735641ff7a_1_99",
        "rol": "valor_card",
        "metrica": "slide15_mario_molina_vistas",
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g374967fdf7d_0_5",
        "rol": "valor_card",
        "metrica": "slide15_mario_molina_inscripciones",
        "formato_texto": "{valor:,.0f}"
      }
    ]
  },
  {
    "numero": 19,
    "page_id": "g3735641ff7a_1_161",
    "objetos": [
      {
        "objectId": "g3735641ff7a_1_173",
        "rol": "valor_card",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3735641ff7a_1_222",
        "rol": "valor_card",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      }
    ]
  },
  {
    "numero": 20,
    "page_id": "g3752707f08b_0_37",
    "objetos": [
      {
        "objectId": "g3752707f08b_0_52",
        "rol": "valor_card",
        "metrica": "slide20_crecimiento_integral_inscripciones",
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3752707f08b_0_43",
        "rol": "valor_card",
        "metrica": "slide20_crecimiento_integral_personas_unicas_inscritas",
        "formato_texto": "{valor:,.0f}"
      },
      {
        "objectId": "g3752707f08b_0_60",
        "rol": "valor_card",
        "metrica": null,
        "formato_texto": "{valor:,.0f}"
      }
    ]
  }
];

// === Helpers ================================================================

/**
 * Formatea un valor numérico según el patrón `formato_texto`.
 * Soporta:
 *   "{valor:,.0f}" → 13,572 (entero con separador de miles)
 *   "{valor:.2f}"  → 13,57.20 (2 decimales)
 */
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
  // Fallback: stringify
  return String(value);
}

/**
 * Busca en el Sheet el valor correspondiente al objeto del mapping.
 * Reglas:
 *   - Si `metrica` está definida: busca fila con Categoría == metrica y devuelve Valor (col 3).
 *   - Si `metrica: null` y `rol` empieza con `<sheetCategory>_`: busca fila con Categoría == sheetCategory, devuelve la columna según el sufijo (cursos_totales→col4, certificados→col5).
 *   - Si `rol: "X_Y"`: heurística por Categoría prefix X + columna Y.
 */
function resolveValue(obj, sheetIndex, sheetRows) {
  const rol = obj.rol || '';
  const metrica = obj.metrica;
  
  // Caso 1: metrica explícita — buscar fila por Categoría
  if (metrica) {
    const row = sheetIndex[metrica];
    if (!row) return null;
    // La columna 'Valor' es la 3ra (índice 2)
    return row[2];
  }
  
  // Caso 2: metrica null pero con formato numérico — usar heurística por rol
  if (!obj.formato_texto) return null; // es un label, no numérico
  
  // slide1_* — Categorías slide1_X con Cursos totales (col 4) y Certificados (col 5)
  const m1 = rol.match(/^(slide1)_([a-z]+)$/);
  if (m1) {
    const cat = m1[1] + '_' + m1[2];
    const row = sheetIndex[cat];
    if (!row) return null;
    if (rol === 'total_cursos_unicos') return row[3]; // TOTAL Cursos totales col 4
    if (rol === 'total_certificados') return row[4]; // TOTAL Certificados col 5
    if (rol.startsWith('cursos_')) return row[3]; // Cursos totales col 4
    if (rol.startsWith('cert_')) return row[4]; // Certificados col 5
    return null;
  }
  
  // slide2_empleo_incluyente_por_sector — buscar por Sector
  if (rol === 'valores_cursos' || rol === 'subtotal' || rol === 'total_general') {
    // Por ahora, los IDs de slide2 son demasiado custom para resolver sin un campo
    // "sheet_sector" explícito. Devolver null y log warning.
    // TODO: agregar campo `sheet_sector` al mapping para slide2.
    return null;
  }
  
  // slide12_rutas_aprendizaje — buscar por Sección+Ruta
  if (rol === 'total_cursos_seccion') {
    // Total cursos por sección: depende de la sección adyacente
    // TODO: agregar campo `sheet_seccion` al mapping.
    return null;
  }
  
  return null;
}

/**
 * Construye índice del Sheet por Categoría (columna A, índice 0).
 * Devuelve { categoria: row[], ... }
 */
function buildSheetIndex(rows) {
  const idx = {};
  for (let i = 0; i < rows.length; i++) {
    const cat = String(rows[i][0] || '').trim();
    if (cat && !cat.startsWith('Categoría') && cat !== 'TOTAL') {
      // Si ya existe, acumular (no debería pasar, pero por las dudas)
      if (!idx[cat]) {
        idx[cat] = rows[i];
      }
    }
  }
  return idx;
}

// === Entry point ===========================================================

/**
 * Función principal — pintar todos los text_boxes mapeados en la Slide
 * usando los valores del Sheet.
 */
function paintSlides() {
  const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
  const sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    SpreadsheetApp.getUi().alert('Hoja "' + SHEET_NAME + '" no encontrada.');
    return;
  }
  
  // 1. Leer el Sheet como matriz de filas
  const allRows = sheet.getDataRange().getValues();
  const sheetIndex = buildSheetIndex(allRows);
  Logger.log('Sheet index: ' + Object.keys(sheetIndex).length + ' categorias');
  
  // 2. Abrir la presentación de Slides
  const presentation = SlidesApp.openById(PRESENTATION_ID);
  
  // 3. Para cada slide mapeada, abrir el page y los shapes
  let paintedCount = 0;
  let skippedCount = 0;
  const skippedIds = [];
  
  for (const slideMap of MAPPING) {
    const pageId = slideMap.page_id;
    let page;
    try {
      page = presentation.getPageById(pageId);
    } catch (e) {
      Logger.log('SKIP slide ' + slideMap.numero + ': page no encontrada (' + pageId + ')');
      skippedCount += slideMap.objetos.length;
      continue;
    }
    
    for (const obj of slideMap.objetos) {
      const value = resolveValue(obj, sheetIndex, allRows);
      if (value === null || value === '') {
        skippedCount++;
        skippedIds.push(`slide${slideMap.numero} / ${obj.objectId} / rol=${obj.rol}`);
        continue;
      }
      
      const newText = formatValue(value, obj.formato_texto);
      
      try {
        const shape = page.getShapeById(obj.objectId);
        if (!shape) {
          skippedCount++;
          skippedIds.push(`slide${slideMap.numero} / ${obj.objectId} (shape no encontrado)`);
          continue;
        }
        shape.getText().setText(newText);
        paintedCount++;
      } catch (e) {
        Logger.log('ERROR pintando ' + obj.objectId + ': ' + e.message);
        skippedCount++;
      }
    }
  }
  
  Logger.log('Pintados: ' + paintedCount + ' | Saltados: ' + skippedCount);
  if (skippedIds.length > 0) {
    Logger.log('IDs saltados:');
    for (const id of skippedIds) Logger.log('  - ' + id);
  }
  
  return { painted: paintedCount, skipped: skippedCount };
}

/**
 * Trigger manual — agrega menú personalizado al abrir el Sheet.
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('🎨 Slide Painter')
    .addItem('Pintar Slide desde Sheet', 'paintSlides')
    .addToUi();
}

/**
 * Función de test — pinta SOLO slide 1 (para verificar antes de pintar todo).
 */
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
  const page = presentation.getPageById(slideMap.page_id);
  
  let painted = 0;
  let skipped = 0;
  for (const obj of slideMap.objetos) {
    const value = resolveValue(obj, sheetIndex, allRows);
    if (value === null || value === '') {
      Logger.log(`SKIP ${obj.objectId} rol=${obj.rol}`);
      skipped++;
      continue;
    }
    const newText = formatValue(value, obj.formato_texto);
    const shape = page.getShapeById(obj.objectId);
    shape.getText().setText(newText);
    Logger.log(`OK   ${obj.objectId} rol=${obj.rol} → "${newText}"`);
    painted++;
  }
  Logger.log(`Slide 1 — Pintados: ${painted} | Saltados: ${skipped}`);
}
