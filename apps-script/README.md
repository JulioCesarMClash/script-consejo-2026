# Apps Script — Slide Painter

Pinta los KPIs del **Sheet "Datos"** sobre la copia temporal de la **presentación
de Google Slides** del Consejo 2026, usando el mapping embebido en `code.gs`
(generado a partir de `data/mapping-slides.yaml`).

## Estructura del directorio

- **`code.gs`** — código Apps Script con el mapping completo embebido.
- **`appsscript.json`** — manifest del proyecto Apps Script (configuración).
- **`README.md`** — este archivo.

## Deployment paso-a-paso

### 1. Crear proyecto en script.google.com

1. Abrir **https://script.google.com**.
2. Click en **"Nuevo proyecto"** (botón arriba izquierda).
3. Renombrarlo a `Script Consejo 2026 - Slide Painter`.

### 2. Pegar el manifest

1. En el panel izquierdo, click en **"Configuración del proyecto"** (ícono de engranaje).
2. Marcar **"Mostrar el archivo de manifiesto 'appsscript.json' en el editor"**.
3. Click en **"Editar código"** junto al archivo `appsscript.json`.
4. Borrar el contenido y pegar el de `appsscript.json` de este repo.
5. Guardar (Ctrl+S / Cmd+S).

### 3. Pegar el código principal

1. Click en el archivo **`Code.gs`** del panel izquierdo.
2. **Borrar todo** el contenido de ejemplo.
3. Abrir `apps-script/code.gs` de este repo, copiar TODO el contenido y pegarlo.
4. Guardar (Ctrl+S / Cmd+S).

### 4. Autorizar acceso (1ª ejecución)

1. Seleccionar la función **`paintSlide1Only`** en el dropdown (arriba).
2. Click en **▶ Run**.
3. En el popup de "Permisos requeridos", click **"Revisar permisos"**.
4. Elegir la cuenta `julio.mtz@capacitateparaelempleo.org`.
5. Click **"Permitir"** (autoriza acceso a Sheets y Slides).
6. La función corre. **Abrir** la presentación `1uZC2RFa_PlKaTer4RXrRy4AoVGjcrJ8TG6p3GuctJVg` (o su copia temporal) y revisar slide 1.

### 5. Si slide 1 quedó como esperado → pintar todo

1. Seleccionar **`paintSlides`** en el dropdown.
2. Click en **▶ Run**.
3. Ver logs (View → Logs) para ver el resumen de pintados vs saltados.

### 6. (Opcional) Agregar menú al Sheet vinculado

1. Vincular el proyecto al Sheet `Datos` (`Extensiones → Apps Script`).
2. Al abrir el Sheet, el menú 🎨 Slide Painter aparecerá automáticamente (gracias a `onOpen()`).

---

## Validación previa

Antes de pintar **toda** la presentación, probar con **una sola slide**:

1. Abrir el Sheet `Datos` (`1AI7nEsWPoXsu43AilsGYFVfbiOeNUQm7Kk4PVIMmqog`) en otra pestaña.
2. En el editor Apps Script, seleccionar `paintSlide1Only` en el dropdown.
3. Click en `▶ Run`.
4. Revisar logs con `View → Logs` (debería decir `"Slide 1 — Pintados: N | Saltados: M"`).
5. Abrir la presentación `1uZC2RFa_PlKaTer4RXrRy4AoVGjcrJ8TG6p3GuctJVg` (o copia temporal), revisar slide 1.

Si OK, correr `paintSlides()` para pintar todas las 12 slides mapeadas.

---

## Configuración

Al inicio de `code.gs`:

```javascript
const SPREADSHEET_ID = '1AI7nEsWPoXsu43AilsGYFVfbiOeNUQm7Kk4PVIMmqog';
const PRESENTATION_ID = '1uZC2RFa_PlKaTer4RXrRy4AoVGjcrJ8TG6p3GuctJVg';
const SHEET_NAME = 'Datos';
```

Estos IDs ya están configurados.

---

## Limitaciones actuales (esperadas)

- **IDs con `metrica: null`** sin `sheet_lookup`: el Apps Script los marca como **skip** en logs (no rompe la corrida).
- **9 IDs legítimamente sin match** — métricas externas (academica_usuarios, capacitarte_carso_usuarios, pabellon_visitantes, redes_comunidad_aprende) que el pipeline actual no computa. Sus valores no se pintan (queda el texto actual de la Slide).
- **Labels/narrativa** (42 IDs): no numéricos, no se pintan.

## Simulación local (referencia)

| Slide | Pintados | Detalle |
|---|---|---|
| 1 | 11/11 | 5 categorías × (Cursos + Certificados) + TOTAL ×2 |
| 2 | 19/19 | 6 sectores × (lista_cursos + valores_cursos + subtotal) + total |
| 3 | 4/4 | lista_valores 4 columnas |
| 4 | 4/4 | lista_valores 4 columnas |
| 7 | 2/6 | sheet_lookup solo Académica + Capacítate Carso |
| 8 | 1/5 | sheet_lookup solo Cultura y Salud Aprende |
| 11 | 0/1 | sin match (métrica externa) |
| 12 | 16/16 | label_ruta (sección+ruta) |
| 13 | 6/6 | sheet_orden 1-6 |
| 15 | 2/2 | sheet_orden 1-2 |
| 19 | 0/2 | sin match (métricas externas) |
| 20 | 2/2 | sheet_orden 1-2 (Contenido 89 hardcoded en sheet repo) |
| **TOTAL** | **67/118 (56.8%)** | |

---

## Regenerar el código cuando cambie el YAML

```bash
.venv/bin/python -c "
import yaml, json
y = yaml.safe_load(open('data/mapping-slides.yaml'))
mapping = [{
    'numero': s['numero'],
    'page_id': s['page_id'],
    'objetos': [{
        'objectId': o['id'],
        'rol': o.get('rol', ''),
        'metrica': o.get('metrica'),
        'formato_texto': o.get('formato_texto'),
        'sheet_lookup': o.get('sheet_lookup'),
    } for o in s.get('objetos', [])]
} for s in y['slides']]
print(json.dumps(mapping, indent=2, ensure_ascii=False))
" > /tmp/mapping_inline.json
```

Luego reemplazar el bloque `const MAPPING = [...];` en `code.gs`.

## Output esperado

Al correr `paintSlides()`:

- **Logs**: `"Pintados: N | Saltados: M"` + lista de IDs saltados.
- **Slide física**: text_boxes actualizados con valores del Sheet (formato español, separador de miles con coma).

Si hay slides con `metrica: null` que no se pueden resolver automáticamente, el Apps Script los saltea con warning en logs — esos requieren intervención manual.