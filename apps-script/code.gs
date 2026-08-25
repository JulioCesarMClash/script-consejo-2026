/**
 * Apps Script — Slide Painter (REST API)
 * Script Consejo 2026: pinta los KPIs del Sheet "Datos" sobre la copia
 * temporal de la presentación de Google Slides.
 *
 * Implementación: usa el endpoint REST slides.presentations.batchUpdate
 * directamente vía UrlFetchApp (SlidesApp no expone getPageById).
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

// === REST API: slides.presentations.batchUpdate ============================

function executeBatchUpdate(requests) {
  const url = 'https://slides.googleapis.com/v1/presentations/' + PRESENTATION_ID + ':batchUpdate';
  const payload = JSON.stringify({ requests: requests });
  const options = {
    method: 'post',
    contentType: 'application/json',
    payload: payload,
    headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() },
    muteHttpExceptions: true,
  };
  const response = UrlFetchApp.fetch(url, options);
  const code = response.getResponseCode();
  if (code !== 200) {
    Logger.log('batchUpdate HTTP ' + code + ': ' + response.getContentText());
    throw new Error('batchUpdate failed: HTTP ' + code);
  }
  return JSON.parse(response.getContentText());
}

function makeReplaceAllTextRequest(pageId, objectId, searchText, replaceText) {
  return {
    replaceAllText: {
      objectId: objectId,
      pageObjectIds: [pageId],
      replaceText: replaceText,
      containsText: { text: searchText, matchCase: false },
    },
  };
}

function makeDeleteTextRequest(objectId, textToDelete) {
  return {
    deleteText: {
      objectId: objectId,
      textRange: {
        type: 'FIXED_RANGE',
        startIndex: 0,
        endIndex: textToDelete.length,
      },
    },
  };
}

function makeInsertTextRequest(objectId, text, index) {
  return {
    insertText: {
      objectId: objectId,
      text: text,
      insertionIndex: index,
    },
  };
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

  // Obtenemos la presentación para leer los text_boxes actuales
  const presUrl = 'https://slides.googleapis.com/v1/presentations/' + PRESENTATION_ID;
  const presOptions = {
    method: 'get',
    headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() },
    muteHttpExceptions: true,
  };
  const presResponse = UrlFetchApp.fetch(presUrl, presOptions);
  if (presResponse.getResponseCode() !== 200) {
    Logger.log('GET presentation failed: HTTP ' + presResponse.getResponseCode());
    return;
  }
  const presentation = JSON.parse(presResponse.getContentText());

  // Construir un mapa objectId -> texto actual
  const currentText = {};
  for (const slide of presentation.slides) {
    for (const pe of slide.pageElements) {
      if (pe.objectId) {
        if (pe.shape && pe.shape.text && pe.shape.text.textElements) {
          let txt = '';
          for (const te of pe.shape.text.textElements) {
            if (te.textRun) txt += te.textRun.content;
          }
          currentText[pe.objectId] = txt;
        }
      }
    }
  }

  // Para cada objeto del mapping, construir request de actualización
  const requests = [];
  let paintedCount = 0;
  let skippedCount = 0;
  const skippedIds = [];

  for (const slideMap of MAPPING) {
    const pageId = slideMap.page_id;
    for (const obj of slideMap.objetos) {
      const value = resolveValue(obj, sheetIndex, allRows);
      if (value === null || value === '') {
        skippedCount++;
        skippedIds.push('slide' + slideMap.numero + ' / ' + obj.objectId + ' / rol=' + obj.rol);
        continue;
      }

      const newText = formatValue(value, obj.formato_texto);
      const oldText = currentText[obj.objectId] || '';

      if (!oldText) {
        // Text box vacío: usamos insertText
        requests.push(makeInsertTextRequest(obj.objectId, newText, 0));
        paintedCount++;
        continue;
      }

      // Si el text actual es multilínea (lista de cursos/valores) o texto largo,
      // usamos deleteText + insertText para reemplazo completo.
      if (oldText.includes(String.fromCharCode(10))) {
        requests.push(makeDeleteTextRequest(obj.objectId, oldText));
        requests.push(makeInsertTextRequest(obj.objectId, newText, 0));
        paintedCount++;
        continue;
      }

      // Text simple (un solo número/label): replaceAllText buscando el texto actual
      if (oldText !== newText) {
        // Para valores numéricos, buscamos solo el número (sin prefix/suffix)
        // Si oldText es 'Total de beneficiarios 21,578', buscamos '21,578'
        let searchText = oldText;
        const numberMatch = oldText.match(/[\d,]+(?:\.\d+)?$/);
        if (numberMatch && obj.formato_texto) {
          searchText = numberMatch[0];
        }
        requests.push(makeReplaceAllTextRequest(pageId, obj.objectId, searchText, newText));
        paintedCount++;
      }
    }
  }

  // Ejecutar batchUpdate (en lotes de 100 requests para evitar límites)
  const BATCH_SIZE = 100;
  for (let i = 0; i < requests.length; i += BATCH_SIZE) {
    const batch = requests.slice(i, i + BATCH_SIZE);
    try {
      executeBatchUpdate(batch);
    } catch (e) {
      Logger.log('ERROR batch ' + i + ': ' + e.message);
    }
  }

  Logger.log('Pintados: ' + paintedCount + ' | Saltados: ' + skippedCount);
  if (skippedIds.length > 0) {
    Logger.log('IDs saltados:');
    for (const id of skippedIds) Logger.log('  - ' + id);
  }

  return { painted: paintedCount, skipped: skippedCount };
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

  // Get presentation
  const presUrl = 'https://slides.googleapis.com/v1/presentations/' + PRESENTATION_ID;
  const presOptions = {
    method: 'get',
    headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() },
    muteHttpExceptions: true,
  };
  const presResponse = UrlFetchApp.fetch(presUrl, presOptions);
  if (presResponse.getResponseCode() !== 200) {
    Logger.log('GET failed: HTTP ' + presResponse.getResponseCode());
    return;
  }
  const presentation = JSON.parse(presResponse.getContentText());

  // Build currentText map
  const currentText = {};
  for (const slide of presentation.slides) {
    for (const pe of slide.pageElements) {
      if (pe.objectId && pe.shape && pe.shape.text && pe.shape.text.textElements) {
        let txt = '';
        for (const te of pe.shape.text.textElements) {
          if (te.textRun) txt += te.textRun.content;
        }
        currentText[pe.objectId] = txt;
      }
    }
  }

  let painted = 0;
  let skipped = 0;
  const requests = [];
  for (const obj of slideMap.objetos) {
    const value = resolveValue(obj, sheetIndex, allRows);
    if (value === null || value === '') {
      Logger.log('SKIP ' + obj.objectId + ' rol=' + obj.rol);
      skipped++;
      continue;
    }
    const newText = formatValue(value, obj.formato_texto);
    const oldText = currentText[obj.objectId] || '';
    Logger.log('OK   ' + obj.objectId + ' rol=' + obj.rol + ' (' + oldText.substring(0, 30) + ') → "' + newText + '"');

    if (!oldText) {
      requests.push(makeInsertTextRequest(obj.objectId, newText, 0));
    } else if (oldText.includes(String.fromCharCode(10))) {
      requests.push(makeDeleteTextRequest(obj.objectId, oldText));
      requests.push(makeInsertTextRequest(obj.objectId, newText, 0));
    } else if (oldText !== newText) {
      let searchText = oldText;
      const numberMatch = oldText.match(/[\d,]+(?:\.\d+)?$/);
      if (numberMatch && obj.formato_texto) searchText = numberMatch[0];
      requests.push(makeReplaceAllTextRequest(slideMap.page_id, obj.objectId, searchText, newText));
    }
    painted++;
  }

  // Execute
  try {
    executeBatchUpdate(requests);
    Logger.log('Slide 1 batchUpdate OK');
  } catch (e) {
    Logger.log('ERROR batchUpdate: ' + e.message);
  }
  Logger.log('Slide 1 — Pintados: ' + painted + ' | Saltados: ' + skipped);
}
