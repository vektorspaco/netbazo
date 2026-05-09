# Netbazo

> Sysadmin script con vocación de álgebra lineal: toma tu disco hecho un quilombo de backups solapados y te devuelve la **base** — el conjunto mínimo de archivos linealmente independientes (sin clones exactos) que **generan** todo lo que tenías, ordenado en carpetas Windows-style.

**English summary** — `netbazo` ("net + *bazo*", *bazo* being Esperanto for *basis*) is a sysadmin tool with a linear-algebra heart: it takes a messy span of overlapping backups and reduces it to a minimal basis — the *net basis*, what's left after filtering linearly dependent vectors. It scans `F:\` (or any folder), classifies every file into a clean Windows-style tree (`PC\Documents`, `PC\Pictures`, `MOBILE\Camera`, etc.), copies them with on-collision SHA-1 dedup, and runs a final cross-tree dedup pass. Originals are never touched.

---

## ¿Qué hace?

Tomás tu disco con varios backups parciales encimados (un pendrive viejo, una carpeta `Nueva carpeta`, un `Takeout` de Google, un `(backup celu)`, otra `Nueva carpeta (2)`, etc.). El script:

1. **Inventaria** todo en un TSV.
2. **Clasifica** cada archivo a una estructura Windows-style unificada (mergeando las múltiples fuentes de PC en una sola jerarquía `Documents/`, `Downloads/`, `Pictures/`, etc.) con detección de **unidades atómicas** (carpetas tipo `PCSX2/`, `FalkonPortable/`, mirrors de sitio web) que viajan enteras.
3. **Copia** cada archivo a `F:\ORGANIZADO\` aplicando política de colisiones por SHA-1: si dos rutas fuente caen en el mismo destino y el contenido es idéntico, deja una sola; si difiere, le pone sufijo `__from-<origen>`.
4. **Deduplica** cruzado: pasada final que encuentra clones idénticos en distintas ramas del árbol nuevo (la misma foto en `MOBILE\Camera` y `PC\Pictures\Huawei\DCIM\Camera`) y los mueve a un staging.
5. **Originales jamás se tocan** — solo lectura. Si querés deshacer todo, borrás `F:\ORGANIZADO\` y listo.

## ¿Por qué este nombre?

Cuando tenés un conjunto de vectores que generan un espacio (un *spanning set*) y le sacás los linealmente dependientes hasta dejar lo mínimo necesario, el resultado es una **base**. La operación se llama "extraer una base" o "reducir a una base". Tu disco con 4 backups solapados es exactamente eso: un *spanning set* redundante. Este script te lo lleva a su base.

## Estructura objetivo

```
F:\ORGANIZADO\
├── MOBILE\
│   ├── Camera\, Pictures\, Videos\, Documents\, Downloads\
│   ├── WhatsApp\, AndroidData\, Audio\, Apps\, Other\
├── PC\
│   ├── Documents\, Downloads\, Desktop\, Pictures\, Videos\, Music\
│   ├── Games\           ← emuladores, ROMs, Saved Games
│   ├── Software\        ← portables, drivers, firmwares (como unidades atómicas)
│   ├── Code\, Books\, Sites\, Bitcoin\, Other\
└── ARCHIVOS\
    └── Takeout\         ← intacto, sin descomprimir
```

## Resultado esperado (caso real)

| Métrica | Valor |
|---|---|
| Archivos fuente | 57.157 |
| Carpetas raíz fuente | 5 |
| Tamaño total | 302.9 GiB |
| Archivos en árbol final | 54.268 |
| Espacio recuperado en colisiones | 1.5 GiB |
| Errores | 0 |
| Originales tocados | 0 |

Más con `Dedupe.ps1`: típicamente decenas de GiB adicionales por clones cruzados (fotos del celular replicadas en múltiples backups, etc.).

## Cómo usarlo

### Requisitos

- Windows 10/11 (PowerShell 5.1+)
- ~2× el tamaño de tus datos en espacio libre (originales + nuevo árbol)
- Python 3 (solo para generar la clasificación; el resto es PowerShell puro)

### Pasos

```powershell
# 1) Inventariar (Linux/WSL/Git Bash)
bash scripts/python/inventory.sh F:\

# 2) Clasificar (genera classification.csv)
python3 scripts/python/classify.py --inventory inventory.tsv --out classification.csv

# 3) Revisar la clasificación (opcional pero recomendado)
#    Mirá classification.csv en LibreOffice / Excel: cada fila es un archivo y dest.

# 4) Copiar (PowerShell)
PowerShell -ExecutionPolicy Bypass -File scripts\powershell\Organize.ps1

# 5) Dedup cruzado (PowerShell)
PowerShell -ExecutionPolicy Bypass -File scripts\powershell\Dedupe.ps1
```

Cada script es **resumible** — lo cortás con Ctrl+C, lo volvés a lanzar y continúa donde quedó (state.json + done.txt).

Si preferís doble-click, los `.bat` lanzadores envuelven los scripts.

## Garantías

- **Idempotente**: re-ejecutar produce el mismo resultado, sin duplicar trabajo.
- **Resumible**: corte de luz, Ctrl+C, kernel panic — al volver a lanzar, retoma.
- **Auditable**: cada decisión queda en `log_skipped.tsv` (clones), `log_renamed.tsv` (colisiones distintas), `log_errors.tsv`, `log_dedupe.tsv`.
- **Reversible**: borrás `ORGANIZADO\` y `ORGANIZADO_PLAN\` y volvés al estado inicial.

## Limitaciones conocidas

- La clasificación tiene reglas heurísticas (extensión + nombre de carpeta + detección de bundles atómicos). Casos raros caen a `PC\Other\`. Mirar el CSV antes de copiar y ajustar `classify.py` si hace falta.
- No detecta similitud, solo igualdad bit a bit (SHA-1). Una foto reescalada y la original son tratadas como archivos distintos.
- Pensado para Windows. La parte de inventario corre en Linux/WSL/Git Bash; la copia es PowerShell.

## Cómo se construyó

Esto es **vibe coding** — un product owner técnico iterando con un asistente AI sobre datos reales propios. Ver [docs/METODOLOGIA.md](docs/METODOLOGIA.md) para el camino completo: por qué se descartaron 3 versiones del clasificador, por qué hardlinks no funcionan en virtiofs→NTFS, por qué `Copy-Item` falló con 54.394 errores y la versión `[System.IO.File]::Copy` los curó, etc.

[docs/LECCIONES.md](docs/LECCIONES.md) tiene los aprendizajes generales aplicables a cualquier sysadmin script tipo "ordenar un quilombo masivo".

## Licencia

MIT. Ver [LICENSE](LICENSE).

---

<sub>**Vibe coded** · construido en diálogo iterativo con [Claude Opus 4.7](https://www.anthropic.com/claude) sobre el disco real del autor (303 GiB, 57.157 archivos, 5 backups solapados). Cada decisión técnica salió de evaluar output sobre datos concretos, no de prompts abstractos. Proceso completo en [docs/METODOLOGIA.md](docs/METODOLOGIA.md).</sub>

