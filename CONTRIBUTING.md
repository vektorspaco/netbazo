# Contribuir

¿Te sirvió `netbazo`? ¿Tenés un caso que rompe la clasificación? ¿Querés mejorar el tooling? Son bienvenidos los issues y PRs.

## Cómo agregar reglas de clasificación

`scripts/python/classify.py` tiene varias estructuras editables al tope:

- **`HARD_ATOMIC`** (dict en `find_atomic_units`): nombres de carpeta exactos que viajan como unidades atómicas. Mapean nombre → bucket destino. Ejemplo: `'PCSX2': 'Games'` hace que cualquier carpeta llamada `PCSX2` (con todo su contenido) vaya a `PC\Games\PCSX2\`.
- **`ANCHORS`** y **`MOBILE_ANCHORS`**: nombres de carpeta Windows-style. Cuando un archivo tiene una de estas en su path, todo lo que está después se preserva tal cual en el destino.
- **`EXT`**: extensiones agrupadas por categoría (`pic`, `vid`, `mus`, `doc`, `inst`, `arch`, `rom`, `code`).
- **`SOFTWARE_FILES`**, **`CODE_DIRS`**, **`SITE_FILES`**: marcadores que activan auto-detección de unidades atómicas.

Si tu fuente tiene una carpeta peculiar (ej: `MiBackupRaroDe2017`), agregala a `HARD_ATOMIC` con el bucket que prefieras.

## Cómo agregar buckets nuevos

Si querés un bucket destino nuevo (ej: `PC\Trabajo\` o `PC\Recetas\`):

1. Definí qué archivos van ahí (por nombre de carpeta, por extensión, por hint en path).
2. Agregá la regla en `classify_loose` (loose files) o en `find_atomic_units` (folders enteras).
3. Asegurate de que el bucket aparece en algún ejemplo de `examples/classification_sample.csv` para que se vea en docs.

## Cómo testear sin tocar tus archivos

```powershell
PowerShell -ExecutionPolicy Bypass -File scripts\powershell\Organize.ps1 -DryRun -Limit 200
```

Imprime "[DRY] src -> dest" para las primeras 200 filas pendientes sin copiar nada.

## Reportar bug

Si `Organize.ps1` falla, mirá `log_errors.tsv` y abrí un issue con:

1. La fila exacta del CSV que rompe (size + source + dest).
2. El error message del log.
3. La versión de PowerShell: `$PSVersionTable.PSVersion`.

Casos sospechosos: paths con caracteres no-ASCII, paths >260 chars, archivos con permisos raros (Acceso denegado).
