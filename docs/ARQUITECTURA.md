# Arquitectura de Netbazo

## Pipeline

```
┌─────────────┐    inventory.tsv    ┌─────────────┐  classification.csv  ┌─────────────┐
│  inventario ├───────────────────► │ classifier  ├────────────────────► │  organize   │
│ (find/sh)   │  size + path tsv    │  (Python)   │   src→dst rows       │ (PowerShell)│
└─────────────┘                     └─────────────┘                      └──────┬──────┘
                                                                                │
                                                                                │  copia con
                                                                                │  collision-
                                                                                │  dedup SHA1
                                                                                ▼
                                                                         ┌─────────────┐  log_dedupe.tsv
                                                                         │   dedupe    │
                                                                         │ (PowerShell)│ ◄── F:\ORGANIZADO\
                                                                         └─────────────┘
                                                                                │
                                                                                ▼
                                                                         F:\ORGANIZADO_PLAN\_DUPLICADOS\
```

## Componentes

### `scripts/python/inventory.sh`
Wrapper bash de `find` que recorre la raíz, excluye `$RECYCLE.BIN`, `System Volume Information` y carpetas previas (`ORGANIZADO/`, `ORGANIZADO_PLAN/`), y emite `size\tpath` por línea. Read-only, ~1 minuto para 57k archivos.

### `scripts/python/classify.py`
Lee `inventory.tsv` y produce `classification.csv` (`Size,Source,Dest`). **No toca el disco.** Aplica:
1. Pre-pass de detección de unidades atómicas (whitelist de nombres + auto-detección por marcadores `.exe/.dll/.git/index.html`).
2. Anchor walking sobre cada archivo no-atómico.
3. Fallback por extensión.

Configuración via constantes al tope del archivo: `EXT`, `HARD_ATOMIC`, `ANCHORS`, `MOBILE_ANCHORS`. Editables por usuario para casos específicos.

### `scripts/powershell/Organize.ps1`
Lee `classification.csv` y copia según las reglas. Estado en `done.txt` (append-only, una línea por archivo procesado) y `state.json` (contadores). Resumible. Política de colisiones por SHA-1.

API .NET directa para evitar parameter sets de cmdlets:
- `[System.IO.File]::Copy($src, $dst, $overwrite)`
- `[System.IO.Directory]::CreateDirectory($dir)`
- `[System.IO.File]::Exists($path)`
- `[System.Security.Cryptography.SHA1]::Create().ComputeHash($stream)`

### `scripts/powershell/Dedupe.ps1`
Walk completo de `F:\ORGANIZADO\`, agrupa por tamaño, hashea grupos con potencial duplicado, mueve los duplicados a `F:\ORGANIZADO_PLAN\_DUPLICADOS\` preservando un archivo "keeper" por grupo. Heurística de keeper: prefiere paths cortos, evita `Other/`, `Software/`, `Downloads/` y archivos con sufijo `__from-`.

## State files

| Archivo | Generador | Función |
|---|---|---|
| `inventory.tsv` | `inventory.sh` | Listado plano de todos los archivos fuente. Input del classifier. |
| `classification.csv` | `classify.py` | Plan: una fila por archivo, con su destino. Input del organize. |
| `done.txt` | `Organize.ps1` | Source paths ya procesados. Permite resume. Append-only. |
| `state.json` | `Organize.ps1` | Contadores agregados. Solo para reporting. |
| `log_skipped.tsv` | `Organize.ps1` | Source/dest de archivos skipped por hash idéntico. |
| `log_renamed.tsv` | `Organize.ps1` | Source/dest/dest-renamed de colisiones con contenido distinto. |
| `log_errors.tsv` | `Organize.ps1` | Errores no fatales. |
| `log_dedupe.tsv` | `Dedupe.ps1` | Archivos movidos a duplicados, con su keeper. |

## Política de colisiones — caso por caso

```
classification.csv tiene dos filas con dest = PC\Pictures\foo.jpg

Caso 1: el destino aún no existe (primera fila procesada)
  Copy → PC\Pictures\foo.jpg

Caso 2: el destino existe, hash igual
  Skip → log_skipped.tsv
  Source NO se duplica en destino.

Caso 3: el destino existe, hash distinto
  Origen tag = "80gb" / "ord" / "nc1" / "nc2" / "celu" / "pix" / "tk"
  Copy → PC\Pictures\foo__from-80gb.jpg
  Si ya existe ese tambien: PC\Pictures\foo__from-80gb-1.jpg (k++)
  Log → log_renamed.tsv
```

## Performance esperada

Disco mecánico 7200 RPM, NTFS local (sin virtualización):

| Operación | Throughput |
|---|---|
| Inventory (find) | ~30k files/seg |
| Classify (Python) | ~10k files/seg en RAM |
| Organize (copy + dedup hash on collision) | ~7-10 MB/s sostenido, ~5-15 files/seg en archivos chicos |
| Dedupe cross-tree (hash todo el árbol nuevo) | limitado por throughput de lectura, ~115 MB/s = 45 min para 300 GiB |

Total para 57k archivos / 303 GiB: ~30-90 minutos.
