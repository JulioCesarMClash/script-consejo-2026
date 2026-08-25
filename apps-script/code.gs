/**
 * Apps Script — Slide Painter (slide.replaceAllText)
 * Script Consejo 2026: pinta los KPIs del Sheet "Datos" sobre la copia
 * temporal de la presentación de Google Slides.
 *
 * Implementación: usa SlidesApp.openById() + slide.replaceAllText()
 * directamente (sin REST API). El scope 'presentations' en appsscript.json
 * autoriza estas operaciones automáticamente.
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
{
  'numero': 1,
  'page_id': 'g3948dc9dc6d_2_5',
  'objetos': [null, null, null, null, null, null, null, null, null, null, null],
},
{
  'numero': 2,
  'page_id': 'g3948dc9dc6d_0_3',
  'objetos': [null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null],
},
{
  'numero': 3,
  'page_id': 'g375ce6fdc96_0_0',
  'objetos': [null, null, null, null, null],
},
{
  'numero': 12,
  'page_id': 'g3761cbcde11_9_59',
  'objetos': [null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null, null],
},
{
  'numero': 4,
  'page_id': 'g375ce6fdc96_0_268',
  'objetos': [null, null, null, null],
},
{
  'numero': 7,
  'page_id': 'g375ce6fdc96_0_366',
  'objetos': [null, null, null, null, null, null],
},
{
  'numero': 8,
  'page_id': 'g375ce6fdc96_0_371',
  'objetos': [null, null, null, null, null],
},
{
  'numero': 11,
  'page_id': 'g375ce6fdc96_0_381',
  'objetos': [null],
},
{
  'numero': 13,
  'page_id': 'g3735641ff7a_1_115',
  'objetos': [null, null, null, null, null, null],
},
{
  'numero': 15,
  'page_id': 'g3735641ff7a_1_93',
  'objetos': [null, null],
},
{
  'numero': 19,
  'page_id': 'g3735641ff7a_1_161',
  'objetos': [null, null],
},
{
  'numero': 20,
  'page_id': 'g3752707f08b_0_37',
  'objetos': [null, null, null],
}
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

// === Entry point ===========================================================

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
  const slides = presentation.getSlides();

  // Crear mapa page_id -> Slide object
  const slideByPageId = {};
  for (const slide of slides) {
    slideByPageId[slide.getId()] = slide;
  }

  let paintedCount = 0;
  let skippedCount = 0;
  const skippedIds = [];

  for (const slideMap of MAPPING) {
    const pageId = slideMap.page_id;
    const slide = slideByPageId[pageId];
    if (!slide) {
      Logger.log('SKIP slide ' + slideMap.numero + ': page no encontrada (' + pageId + ')');
      skippedCount += slideMap.objetos.length;
      continue;
    }

    for (const obj of slideMap.objetos) {
      const value = resolveValue(obj, sheetIndex, allRows);
      if (value === null || value === '') {
        skippedCount++;
        skippedIds.push('slide' + slideMap.numero + ' / ' + obj.objectId + ' / rol=' + obj.rol);
        continue;
      }

      const newText = formatValue(value, obj.formato_texto);

      try {
        // Buscar el shape con este objectId en el slide
        const shape = findShapeById(slide, obj.objectId);
        if (!shape) {
          skippedCount++;
          skippedIds.push('slide' + slideMap.numero + ' / ' + obj.objectId + ' (shape no encontrado)');
          continue;
        }

        // Obtener el texto actual para decidir estrategia
        const oldText = shape.getText().asString();

        if (!oldText || oldText === newText) {
          // No hay cambio o el shape está vacío
          if (!oldText) {
            shape.getText().setText(newText);
          }
          paintedCount++;
          continue;
        }

        // Si el texto actual es multilínea o contiene el nuevo texto, usamos replaceAllText
        // sobre el número extraído al final
        const numberMatch = oldText.match(/[\d,]+(?:\.\d+)?$/);
        if (numberMatch && obj.formato_texto && numberMatch[0] !== newText) {
          // Reemplazar solo el número
          slide.replaceAllText(numberMatch[0], newText);
        } else {
          // Reemplazo completo (si no es multilínea) o primera ocurrencia
          slide.replaceAllText(oldText, newText);
        }
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

function findShapeById(slide, objectId) {
  // Busca un shape con el objectId dado recorriendo todos los pageElements.
  // No hay un método directo en SlidesApp para esto, así que usamos los shapes.
  try {
    for (const shape of slide.getShapes()) {
      if (shape.getId() === objectId) return shape;
    }
  } catch (e) {}
  return null;
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

  let painted = 0;
  let skipped = 0;
  for (const obj of slideMap.objetos) {
    const value = resolveValue(obj, sheetIndex, allRows);
    if (value === null || value === '') {
      Logger.log('SKIP ' + obj.objectId + ' rol=' + obj.rol);
      skipped++;
      continue;
    }
    const newText = formatValue(value, obj.formato_texto);
    const shape = findShapeById(slide, obj.objectId);
    if (!shape) {
      Logger.log('SKIP ' + obj.objectId + ' (shape no encontrado)');
      skipped++;
      continue;
    }
    const oldText = shape.getText().asString();
    Logger.log('OK   ' + obj.objectId + ' rol=' + obj.rol + ' ("' + oldText.substring(0, 40) + '") → "' + newText + '"');

    if (!oldText || oldText === newText) {
      if (!oldText) shape.getText().setText(newText);
    } else {
      const numberMatch = oldText.match(/[\d,]+(?:\.\d+)?$/);
      if (numberMatch && obj.formato_texto && numberMatch[0] !== newText) {
        slide.replaceAllText(numberMatch[0], newText);
      } else {
        slide.replaceAllText(oldText, newText);
      }
    }
    painted++;
  }

  Logger.log('Slide 1 — Pintados: ' + painted + ' | Saltados: ' + skipped);
}
