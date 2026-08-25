# Apps Script — Slide Painter

Pinta los KPIs del **Sheet "Datos"** sobre la copia temporal de la **presentación
de Google Slides** del Consejo 2026.

## ¿Qué hay en este directorio?

- **`code.gs`** — código Apps Script completo. Listo para copiar-pegar.
- **`appsscript.json`** — manifest del proyecto Apps Script.
- **`README.md`** — este archivo.

---

## Deployment paso a paso (5-10 minutos)

### Paso 1: Crear proyecto nuevo

1. Abrí **https://script.google.com** en el navegador.
2. Click en **"Nuevo proyecto"** (botón arriba a la izquierda).
3. En la esquina superior izquierda, click en el texto "Proyecto sin título" — renombralo a:
   > `Script Consejo 2026 - Slide Painter`
4. Click **Aceptar**.

---

### Paso 2: Pegar el manifest (appsscript.json)

1. En el panel **izquierdo** (junto al archivo `Code.gs`), click en **"Configuración del proyecto"** (ícono de engranaje ⚙️).
2. Marcá la casilla **"Mostrar el archivo de manifiesto 'appsscript.json' en el editor"**.
3. Ahora aparece `appsscript.json` en el panel izquierdo. Click ahí.
4. **Borrá todo** el contenido que tenga (Apps Script pone un JSON de ejemplo).
5. Abrí `apps-script/appsscript.json` de este repo en un editor de texto.
6. **Copiá todo** el contenido (son unas 11 líneas).
7. **Pegalo** en el editor de `appsscript.json` de Apps Script.
8. Click **Ctrl+S / Cmd+S** para guardar.

El manifest dice que:
- Timezone: America/Mexico_City
- Runtime: V8
- Scopes: lectura/escritura de Sheets + Slides

---

### Paso 3: Pegar el código principal

1. En el panel izquierdo, click en **"Code.gs"**.
2. **Borrá todo** el contenido que tenga (Apps Script pone una función `myFunction()` de ejemplo).
3. Abrí `apps-script/code.gs` de este repo en un editor de texto (NO se puede abrir directamente en script.google.com).
4. **Seleccioná TODO** el contenido (Ctrl+A / Cmd+A) y **copialo** (Ctrl+C / Cmd+C).
5. Volvé a script.google.com y **pegalo** (Ctrl+V / Cmd+V) en el editor `Code.gs`.
6. Click **Ctrl+S / Cmd+S** para guardar.

El código incluye:
- Configuración de Sheet + Presentación (IDs ya están).
- El **MAPPING** con 118 objetos de 12 slides (esto es lo más grande — unas 1500 líneas).
- Las funciones `paintSlides()`, `paintSlide1Only()`, `onOpen()`, y helpers.

---

### Paso 4: Autorizar acceso (SOLO la primera vez)

1. Arriba en el editor de Apps Script, hay un **dropdown** con `myFunction` seleccionado. Cambialo a **`paintSlide1Only`**.
2. Click en **▶ Run** (botón play).
3. **Aparece un popup** que dice "Autorización requerida". Click **"Revisar permisos"**.
4. **Elegí tu cuenta de Google**: `julio.mtz@capacitateparaelempleo.org` (o la que uses).
6. Puede aparecer una pantalla de "Google no verificó esta app" — click **"Avanzado"** → **"Ir a [proyecto] (no seguro)"**.
7. Click **"Permitir"** (autoriza acceso a Sheets y Slides).
8. La función corre. En la barra inferior dice "Ejecución completada" o muestra errores.

---

### Paso 5: Verificar Slide 1

1. Abrí una nueva pestaña y andá a la presentación:
   > https://docs.google.com/presentation/d/1uZC2RFa_PlKaTer4RXrRy4AoVGjcrJ8TG6p3GuctJVg/edit

2. Andá a la **Slide 1** (Pobreza extrema).
3. Verificá que los valores cambiaron:
   - Antes: "Total de beneficiarios 21,578"
   - Después: "13,572" (Certificados vivienda del Sheet)

#### ¿Qué valores esperás ver?

| Text box (objectId) | Label en Slide 1 | Valor pintado |
|---|---|---|
| `g3948dc9dc6d_2_29` | Cursos (header) | **108** |
| `g3948dc9dc6d_2_14` | Cursos vivienda | **16** |
| `g3948dc9dc6d_2_17` | Cursos digital | **23** |
| `g3948dc9dc6d_2_18` | Cursos empleo | **29** |
| `g3948dc9dc6d_2_24` | Cursos desastres | **11** |
| `g3948dc9dc6d_2_31` | Beneficiarios vivienda | **13,572** |
| `g3948dc9dc6d_2_37` | Beneficiarios digital | **48,101** |
| `g3948dc9dc6d_2_38` | Beneficiarios empleo | **48,751** |
| `g3948dc9dc6d_2_39` | Beneficiarios alimentos | **55,894** |
| `g3948dc9dc6d_2_40` | Beneficiarios desastres | **44,422** |
| `g3948dc9dc6d_17_326` | Total: 290,797 | **210,740** |

---

### Paso 6: Si Slide 1 quedó OK → pintar las 12 slides

1. Volvé al editor de Apps Script.
2. Cambiá el dropdown de `paintSlide1Only` a **`paintSlides`**.
3. Click ▶ Run.
4. Cuando termine, andá a **Ver → Logs** (o `Ctrl+Enter`).
5. Deberías ver algo como: `"Pintados: 67 | Saltados: 9"` y la lista de IDs saltados.

---

### Paso 7: Verificar las 12 slides en la presentación

| Slide | Esperado |
|---|---|
| 1 | 11 KPIs pintados (Certificados por categoría) |
| 2 | 19 KPIs pintados (sectores construcción, alimentos, ed financiera, transporte, limpieza, agropecuarias + total) |
| 3 | 4 columnas de valores (2025, sep2026, dic2026, Acumulado) |
| 4 | 4 columnas de valores (2024, sep2025, dic2025, Acumulado) |
| 7 | 2 KPIs (Académica + Capacítate Carso). Los otros 4 sin match (métricas externas eliminadas del pipeline) |
| 8 | 1 KPI (Cultura y Salud Aprende). Los otros 4 sin match |
| 11 | 0 KPIs pintados (métrica externa `redes_comunidad_aprende` no computada) |
| 12 | 16 label_ruta pintados (nombres de las rutas) |
| 13 | 6 KPIs (Centros, Certificados, Usuarios, Cursos, Inscripciones, Cursos por persona) |
| 15 | 2 KPIs (Inscripciones + Consultas) |
| 19 | 0 KPIs pintados (métricas externas academica/carso/pabellon/redes) |
| 20 | 2 KPIs (Inscripciones + Personas únicas inscritas). El 3ro (Contenido 89) queda con su valor actual. |

---

## Troubleshooting

### Error: "You do not have permission"

La cuenta que usaste para autorizar no tiene acceso al Sheet/Presentación. Verificá que estás usando la cuenta correcta:
- Sheet `1AI7nEsWPoXsu43AilsGYFVfbiOeNUQm7Kk4PVIMmqog` (Datos)
- Presentación `1uZC2RFa_PlKaTer4RXrRy4AoVGjcrJ8TG6p3GuctJVg`

### Error: "Sheet 'Datos' not found"

El Sheet no tiene una hoja llamada `Datos`. Verificá el nombre de la hoja (`SHEET_NAME` al inicio de code.gs, por defecto `Datos`).

### Error: "Page not found"

La presentación no tiene una página con el `pageId` esperado. Posiblemente alguien editó la presentación y los IDs cambiaron. Regenerá el mapping con `regen-mapping.md` abajo.

### Algunos IDs quedan con texto viejo

Esos son los IDs sin match legítimos (métricas externas eliminadas). El Apps Script los salta con warning en logs.

---

## Regenerar el código cuando cambie el YAML

Si cambia `data/mapping-slides.yaml`, regenerá `apps-script/code.gs` con:

```bash
.venv/bin/python -c "
import yaml, json
y = yaml.safe_load(open('data/mapping-slides.yaml'))
print(json.dumps([
    {'numero': s['numero'], 'page_id': s['page_id'],
     'objetos': [{
        'objectId': o['id'],
        'rol': o.get('rol', ''),
        'metrica': o.get('metrica'),
        'formato_texto': o.get('formato_texto'),
        'sheet_lookup': o.get('sheet_lookup'),
     } for o in s.get('objetos', [])]
  } for s in y['slides']], indent=2, ensure_ascii=False))
" > /tmp/mapping_inline.json
```

Y luego en `code.gs`, reemplazar `const MAPPING = [...];` por `const MAPPING = [...contenido de /tmp/mapping_inline.json...];`.

---

## Output esperado

- **Pintados**: 67 / 118 IDs (56.8%).
- **Saltados intencionales**: 42 (labels/narrativa sin formato numérico).
- **Skip legítimos**: 9 (métricas externas sin automatización).

Si todo sale bien, el Sheet y la Slide quedan alineados (con la advertencia de que slide20 tiene una divergencia adicional que se documenta en el catálogo).