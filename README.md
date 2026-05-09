# Netbazo

> Sysadmin script con vocación de álgebra lineal: toma tu disco hecho un quilombo de backups solapados y te devuelve la **base** — el conjunto mínimo de archivos linealmente independientes (sin clones exactos) que **generan** todo lo que tenías, ordenado en carpetas Windows-style.

**English summary** — `netbazo` ("net + *bazo*", *bazo* being Esperanto for *basis*) is a sysadmin tool with a linear-algebra heart: it takes a messy span of overlapping backups and reduces it to a minimal basis — the *net basis*, what's left after filtering linearly dependent vectors. It scans a chosen root, classifies every file into a clean Windows-style tree, copies them with on-collision SHA-1 dedup, and runs a final cross-tree dedup pass. Originals are never touched.

---

## ¿Qué hace?

Tomás un disco con varios backups parciales encimados (un pendrive viejo, una carpeta `Nueva carpeta`, un `Takeout` de Google, un `(backup celu)`, otra `Nueva carpeta (2)`, etc.). El script:

1. **Inventaria** todo en un TSV.
2. **Clasifica** cada archivo a una estructura Windows-style unificada (mergeando las múltiples fuentes de PC en una sola jerarquía `Documents`, `Downloads`, `Pictures`, etc.) con detección de **unidades atómicas** (carpetas tipo `PCSX2`, `FalkonPortable`, mirrors de sitio web) que viajan enteras.
3. **Copia** cada archivo al árbol nuevo aplicando política de colisiones por SHA-1: si dos rutas fuente caen en el mismo destino y el contenido es idéntico, deja una sola; si difiere, le pone sufijo `__from-<origen>`.
4. **Deduplica** cruzado: pasada final que encuentra clones idénticos en distintas ramas del árbol nuevo (la misma foto en `MOBILE/Camera` y `PC/Pictures/Huawei/DCIM/Camera`) y los mueve a un staging.
5. **Originales jamás se tocan** — solo lectura. Si querés deshacer todo, borrás la carpeta nueva y listo.

## ¿Por qué este nombre?

Cuando tenés un conjunto de vectores que generan un espacio (un *spanning set*) y le sacás los linealmente dependientes hasta dejar lo mínimo necesario, el resultado es una **base**. Tu disco con 4 backups solapados es exactamente eso: un *spanning set* redundante. Netbazo te lo lleva a su **base neta** — net + *bazo* (esperanto por base).

## Estructura objetivo

```text
<RAÍZ>/ORGANIZADO/
├── MOBILE/
│   ├── Camera/, Pictures/, Videos/, Documents/, Downloads/
│   └── WhatsApp/, AndroidData/, Audio/, Apps/, Other/
├── PC/
│   ├── Documents/, Downloads/, Desktop/, Pictures/, Videos/, Music/
│   ├── Games/        ← emuladores, ROMs, Saved Games
│   ├── Software/     ← portables, drivers, firmwares (unidades atómicas)
│   └── Code/, Books/, Sites/, Bitcoin/, Other/
└── ARCHIVOS/
    └── Takeout/      ← intacto, sin descomprimir
```

## Resultado esperado (caso real)

| Métrica | Valor |
|---|---|
| Archivos fuente | 57.157 |
| Carpetas raíz fuente | 5 |
| Tamaño total | 302,9 GiB |
| Archivos en árbol final | 54.268 |
| Espacio recuperado en colisiones | 1,5 GiB |
| Errores | 0 |
| Originales tocados | 0 |

Más con `Dedupe.ps1`: típicamente decenas de GiB adicionales por clones cruzados (fotos del celular replicadas en múltiples backups, etc.).

## Versión actual: 0.1 — rutas originales hardcodeadas

> ⚠️ **Importante para v0.1**: esta versión mantiene las rutas del autor hardcodeadas en los scripts.

Concretamente:

- La raíz por defecto es `F:\` (donde el autor tiene los backups).
- Los nombres de carpeta fuente esperados son los del autor: `80gb sata`, `Nueva Carpeta (C)`, `ORDENAR`, `Takeout`, `Pixel 7 Stock (julio 24)`.
- El destino se crea como `F:\ORGANIZADO\` y la carpeta de control como `F:\ORGANIZADO_PLAN\`.

**Para usar Netbazo v0.1 en otro disco**, dos opciones:

1. **Adaptar manualmente**: editar las constantes al tope de `scripts/python/classify.py` (mapeo de nombres de carpeta fuente, anchors Windows-style, whitelist de unidades atómicas) y pasar los parámetros `-Root` / `-PlanDir` correctos a los scripts PowerShell.

2. **Esperar v0.2** (próxima versión), que va a:
   - **Preguntar la letra de la unidad** y la carpeta raíz al inicio (no asume `F:\`).
   - **Auto-discovery de fuentes**: en vez de carpetas hardcodeadas, escanea la raíz y propone candidatos, vos confirmás cuáles incluir.
   - **Auto-discovery de patrones**: reconoce automáticamente "Backup celu", "Pixel*", "Takeout*", "Nueva carpeta*", etc., y te muestra el plan antes de ejecutar.
   - **Prompts interactivos** para estructura de salida, categorías, política de colisiones, idioma de los buckets.
   - **Cero hardcoded paths**: nada referenciado por nombre específico del disco del autor.

La idea de v0.2 es que cualquier persona con un disco lleno de backups solapados pueda correr Netbazo sin tocar el código.

## Estado · vibe coded, probado, sin auditar

Netbazo es **vibe-coded software**: construido en diálogo iterativo con AI sobre datos reales del autor. **Probado** en una corrida end-to-end (51.091 archivos / 297 GiB / 0 errores). **No auditado** profesionalmente. **Sin garantía**.

Detalle completo en [ESTADO.md](ESTADO.md): qué se probó, qué no se probó, safety net del invariante "originales solo-lectura", invitación a peer review, y estado por componente.

## Cómo usarlo (v0.1)

### Requisitos

- Windows 10/11 con PowerShell 5.1+
- Espacio libre ~ 2× el tamaño de tus datos (originales + nuevo árbol)
- Python 3 (solo para clasificar; el resto es PowerShell)
- Bash (Git Bash o WSL) para el inventario inicial

### Pasos

```bash
# 1) Inventariar (Linux / WSL / Git Bash)
bash scripts/python/inventory.sh "/path/a/tu/disco" inventory.tsv
```

```bash
# 2) Clasificar (genera classification.csv)
python3 scripts/python/classify.py --inventory inventory.tsv --out classification.csv
```

> Antes del paso 3, conviene revisar `classification.csv` en LibreOffice / Excel: cada fila es un archivo y su destino. Si hay reglas que rompen, ajustar las constantes al tope de `classify.py` y volver a correr el paso 2.

```powershell
# 3) Copiar (PowerShell, ajustar -Root y -PlanDir a tu disco)
PowerShell -ExecutionPolicy Bypass -File scripts\powershell\Organize.ps1 `
  -Root "X:" -PlanDir "X:\ORGANIZADO_PLAN"
```

```powershell
# 4) Dedup cruzado (PowerShell, mismos parámetros)
PowerShell -ExecutionPolicy Bypass -File scripts\powershell\Dedupe.ps1 `
  -Root "X:" -PlanDir "X:\ORGANIZADO_PLAN"
```

Cada script es **resumible**: lo cortás con `Ctrl+C` y al volver a lanzarlo continúa donde quedó (`state.json` + `done.txt`).

Si preferís doble-click, los `.bat` lanzadores asumen `F:\` como en el caso del autor; para otra letra de unidad, editar el `.bat` o usar PowerShell directo con `-Root`.

## Roadmap

| Versión | Estado | Cambios principales |
|---|---|---|
| **v0.1** | ✅ released | Vibe-coded en una corrida real. Rutas hardcodeadas a `F:\` y nombres de carpeta del autor. PowerShell + Python. |
| **v0.2** | 🔜 próxima | Auto-discovery de raíz y carpetas fuente. Prompts interactivos. Cero hardcoded paths. |
| v0.3 | 💭 idea | Tests sobre datos sintéticos. CI con GitHub Actions. Cobertura de edge cases (>260 chars, OneDrive, BitLocker). |
| v1.0 | 💭 idea | UI gráfica (web local o nativa). Versión Linux/macOS del flow de copia. |

## Garantías

- **Idempotente**: re-ejecutar produce el mismo resultado, sin duplicar trabajo.
- **Resumible**: corte de luz, `Ctrl+C`, kernel panic — al volver a lanzar, retoma.
- **Auditable**: cada decisión queda en `log_skipped.tsv` (clones), `log_renamed.tsv` (colisiones distintas), `log_errors.tsv`, `log_dedupe.tsv`.
- **Reversible**: borrás la carpeta nueva y volvés al estado inicial.

## Limitaciones conocidas

- v0.1 asume rutas y nombres de carpeta del autor. Ver "Versión actual" arriba.
- La clasificación tiene reglas heurísticas (extensión + nombre de carpeta + detección de bundles atómicos). Casos raros caen a `Other/`. Mirar el CSV antes de copiar y ajustar `classify.py` si hace falta.
- No detecta similitud, solo igualdad bit a bit (SHA-1). Una foto reescalada y la original se tratan como archivos distintos.
- Pensado para Windows. La parte de inventario corre en Linux / WSL / Git Bash; la copia es PowerShell.

## Cómo se construyó

Esto es **vibe coding** — un product owner técnico iterando con un asistente AI sobre datos reales propios. Ver [docs/METODOLOGIA.md](docs/METODOLOGIA.md) para el camino completo: por qué se descartaron 3 versiones del clasificador, por qué los hardlinks no funcionan en virtiofs→NTFS, por qué `Copy-Item` falló con 54.394 errores y la versión `[System.IO.File]::Copy` los curó, etc.

[docs/LECCIONES.md](docs/LECCIONES.md) tiene los aprendizajes generales aplicables a cualquier sysadmin script tipo "ordenar un quilombo masivo".

## Licencia

MIT. Ver [LICENSE](LICENSE).

---

<sub>**Vibe coded** · construido en diálogo iterativo con <a href="https://www.anthropic.com/claude">Claude Opus 4.7</a> sobre el disco real del autor (303 GiB, 57.157 archivos, 5 backups solapados). Cada decisión técnica salió de evaluar output sobre datos concretos, no de prompts abstractos. Proceso completo en <a href="docs/METODOLOGIA.md">docs/METODOLOGIA.md</a>.</sub>
