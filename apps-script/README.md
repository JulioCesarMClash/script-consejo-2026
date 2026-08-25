# Apps Script — Slide Painter

Pinta los KPIs del **Sheet "Datos"** sobre la copia temporal de la **presentación
de Google Slides** del Consejo 2026, usando el mapping embebidoado en
`code.gs` (generado a partir de `data/mapping-slides.yaml`).

## Estructura

- **`code.gs`** — código Apps Script con el mapping completo embebido.
- **`README.md`** — este archivo (instrucciones de deployment).

## Deployment manual (1 vez)

1. **Abrir script.google.com** y crear un proyecto nuevo (o usar uno existente).

2. **Pegar `code.gs`** en el editor de Apps Script (borrar el `function myFunction() {}` por defecto).

3. **Autorizar acceso**:
   - Click en `▶ Run` para ejecutar `onOpen` (autoriza acceso a Sheets + Slides).
   - Aceptar los scopes pedidos (Sheets lectura/escritura, Slides lectura/escritura, ScriptApp).

4. **(Opcional) Vincular al Sheet "Datos"**:
   - El trigger `onOpen()` agrega un menú "🎨 Slide Painter" cuando se abre el Sheet vinculado.
   - Sin vinculación, ejecutar `paintSlides()` desde el editor.

## Ejecución

### Opción 1: menú en el Sheet

1. Abrir el Sheet `Datos` (`1AI7nEsWPoXsu43AilsGYFVfbiOeNUQm7Kk4PVIMmqog`).
2. Click en **🎨 Slide Painter → Pintar Slide desde Sheet**.

### Opción 2: editor de Apps Script

1. Abrir el proyecto Apps Script en script.google.com.
2. Seleccionar función `paintSlides` en el dropdown.
3. Click en `▶ Run`.

### Opción 3: trigger programático

Configurar trigger via `script.google.com → Triggers`:

| Función | Origen del evento | Tipo |
|---|---|---|
| `paintSlides` | Desde el spreadsheet | Al abrir |

## Validación previa

Antes de pintar **toda** la presentación, probar con **una sola slide**:

1. En el editor Apps Script, seleccionar `paintSlide1Only` en el dropdown.
2. Click en `▶ Run`.
3. Revisar `View → Logs` para ver qué IDs se pintaron y cuáles se saltaron.
4. Abrir la presentación `1uZC2RFa_PlKaTer4RXrRy4AoVGjcrJ8TG6p3GuctJVg`, copiar temporal.
5. Validar visualmente que slide 1 quedó como se espera.

Si todo OK, correr `paintSlides()` para pintar todas las 12 slides mapeadas.

## Limitaciones actuales

- **IDs con `metrica: null`** (slide1, slide2, slide12, slide19, slide3, slide4, slide7, slide8, slide11, slide13): el Apps Script usa heurística por `rol` para resolver el valor. Algunas se saltean si la heurística no encuentra match.
- **IDs sin `formato_texto`** (labels, headers, narrativa): se saltean automáticamente — Apps Script solo pinta text_boxes con formato numérico.
- **slide2 valores_cursos, slide12 rutas**: requieren lógica custom (lista de cursos por sector) — están documentadas con `sheetIndex` lookup pero pueden necesitar extensión del mapping con `sheet_seccion` o `sheet_categoria` explícito.

## Regenerar el código cuando cambie el YAML

```bash
# (pendiente crear scripts/regen_mapping_inline.py)
# Por ahora, regenerar manualmente:
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
    } for o in s.get('objetos', [])]
} for s in y['slides']]
print(json.dumps(mapping, indent=2, ensure_ascii=False))
" > /tmp/mapping_inline.json

# Luego reemplazar el bloque const MAPPING = ...; en code.gs
```

## Configuración

Al inicio de `code.gs`:

```javascript
const SPREADSHEET_ID = '1AI7nEsWPoXsu43AilsGYFVfbiOeNUQm7Kk4PVIMmqog';
const PRESENTATION_ID = '1uZC2RFa_PlKaTer4RXrRy4AoVGjcrJ8TG6p3GuctJVg';
const SHEET_NAME = 'Datos';
```

Estos IDs ya están configurados. Para otras hojas o presentaciones, cambiar acá.

## Output esperado

Al correr `paintSlides()`:

- **Logs**: `"Pintados: N | Saltados: M"` + lista de IDs saltados.
- **Slide física**: text_boxes actualizados con valores del Sheet (formato español, separador de miles con coma).

Si hay slides con `metrica: null` que no se pueden resolver automáticamente, el
Apps Script los saltea con warning en logs — esos requieren intervención manual.