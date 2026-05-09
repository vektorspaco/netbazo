# Netbazo

> Repo bajo la organización [`vektorspaco`](https://github.com/vektorspaco) — tools de sysadmin con vocación de álgebra lineal.

> Sysadmin script con vocación de álgebra lineal: toma tu disco hecho un quilombo de backups solapados y te devuelve la **base** — el conjunto mínimo de archivos linealmente independientes (sin clones exactos) que **generan** todo lo que tenías, ordenado en carpetas Windows-style.

**English summary** — `netbazo` ("net + *bazo*", *bazo* being Esperanto for *basis*) is a sysadmin tool with a linear-algebra heart: it takes a messy span of overlapping backups and reduces it to a minimal basis — the *net basis*, what's left after filtering linearly dependent vectors. It scans a chosen root, classifies every file into a clean Windows-style tree (`PC\Documents`, `PC\Pictures`, `MOBILE\Camera`, etc.), copies them with on-collision SHA-1 dedup, and runs a final cross-tree dedup pass. Originals are never touched.

---

## ¿Qué hace?

Tomás un disco con varios backups parciales encimados (un pendrive viejo, una carpeta `Nueva carpeta`, un `Takeout` de Google, un `(backup celu)`, otra `Nueva carpeta (2)`, etc.). El script:

1. **Inventaria** todo en un TSV.
2. **Clasifica** cada archivo a una estructura Windows-style unificada (mergeando las múltiples fuentes de PC en una sola jerarquía `Documents/`, `Downloads/`, `Pictures/`, etc.) con detección de **unidades atómicas** (carpetas tipo `PCSX2/`, `FalkonPortable/`, mirrors de sitio web) que viajan enteras.
3. **Copia** cada archivo al árbol nuevo aplicando política de colisiones por SHA-1: si dos rutas fuente caen en el mismo destino y el contenido es idéntico, deja una sola; si difiere, le pone sufijo `__from-<origen>`.
4. **Deduplica** cruzado: pasada final que encuentra clones idénticos en distintas ramas del árbol nuevo (la misma foto en `MOBILE\Camera` y `PC\Pictures\Huawei\DCIM\Camera`) y los mueve a un staging.
5. **Originales jamás se tocan** — solo lectura. Si querés deshacer todo, borrás la carpeta nueva y listo.

## ¿Por qué este nombre?

Cuando tenés un conjunto de vectores que generan un espacio (un *spanning set*) y le sacás los linealmente dependientes hasta dejar lo mínimo necesario, el resultado es una **base**. Tu disco con 4 backups solapados es exactamente eso: un *spanning set* redundante. Netbazo te lo lleva a su **base neta** — net + *bazo* (esperanto por base).

## Estructura objetivo<RAÍZ>\ORGANIZADO
├── MOBILE
│   ├── Camera, Pictures, Videos, Documents, Downloads
│   ├── WhatsApp, AndroidData, Audio, Apps, Other
├── PC
│   ├── Documents, Downloads, Desktop, Pictures, Videos, Music
│   ├── Games\           ← emuladores, ROMs, Saved Games
│   ├── Software\        ← portables, drivers, firmwares (como unidades atómicas)
│   ├── Code, Books, Sites, Bitcoin, Other
└── ARCHIVOS
└── Takeout\         ← intacto, sin descomprimir

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

## Versión actual: 0.1 — rutas originales hardcodeadas

⚠️ **Importante para v0.1**: esta versión mantiene las **rutas del autor hardcodeadas en los scripts**. Concretamente:

- La raíz por defecto es `F:\` (donde el autor tiene los backups).
- Los nombres de carpeta fuente esperados son los del autor: `80gb sata\`, `Nueva Carpeta (C)\`, `ORDENAR\`, `Takeout\`, `Pixel 7 Stock (julio 24)\`.
- El destino se crea como `F:\ORGANIZADO\` y la carpeta de control como `F:\ORGANIZADO_PLAN\`.

**Para usar Netbazo v0.1 en otro disco**, tenés dos opciones:

1. **Adaptar** las constantes al tope de `scripts/python/classify.py` (mapeo de nombres de carpeta fuente, anchors Windows-style, whitelist de unidades atómicas) y los parámetros `-Root` / `-PlanDir` de los scripts PowerShell.

2. **Esperar v0.2** (próxima versión) que va a:
   - **Preguntarte la letra de la unidad** y la carpeta raíz al inicio (no asume `F:\`).
   - **Auto-discovery de fuentes**: en vez de listar carpetas hardcodeadas, escanea la raíz y propone candidatos de carpetas fuente, vos confirmás cuáles incluir.
   - **Auto-discovery de patrones de nombre**: reconoce automáticamente "Backup celu", "Pixel*", "Takeout*", "Nueva carpeta*", etc., y te muestra el plan antes de ejecutar.
   - **Configuración interactiva**: prompts para elegir la estructura de salida, las categorías a usar, política de colisiones, idioma de los buckets.
   - **Cero hardcoded paths**: nada referenciado por nombre específico del disco del autor.

La idea de v0.2 es que cualquier persona con un disco lleno de backups solapados pueda correr Netbazo sin tocar el código.

## Estado · vibe coded, probado, sin auditar

Netbazo es **vibe-coded software**: construido en diálogo iterativo con AI sobre datos reales del autor. **Probado** en una corrida end-to-end (51.091 archivos / 297 GiB / 0 errores). **No auditado** profesionalmente. **Sin garantía**.

Detalle completo en [ESTADO.md](ESTADO.md): qué se probó, qué no se probó, safety net del invariante "originales solo-lectura", invitación a peer review, y estado por componente.

## Cómo usarlo

### Requisitos

- Windows 10/11 (PowerShell 5.1+)
- ~2× el tamaño de tus datos en espacio libre (originales + nuevo árbol)
- Python 3 (solo para generar la clasificación; el resto es PowerShell puro)
- Bash (Git Bash / WSL) para el inventario inicial

### Pasos (v0.1, con adaptación manual de paths)

```powershell
