# Lecciones

Aprendizajes extraídos del proceso. Aplicables a cualquier sysadmin script que tenga que **ordenar un quilombo masivo** sin perder datos.

## 1. Originales sagrados, copia organizada

No mover, no renombrar, no borrar nada del usuario. Construir una vista nueva (`F:\ORGANIZADO\`) y dejar que el usuario decida cuándo soltar los originales. El costo es 2× el espacio temporalmente; el beneficio es **reversibilidad total** (borro la nueva carpeta y vuelvo al estado inicial).

## 2. La clasificación necesita reglas explícitas, no inferencia mágica

Estas son las reglas que terminaron funcionando:

1. **Detección de unidades atómicas primero**. Una carpeta con un `.exe` adentro = software bundle (no se descompone).
2. **Anchor walking**: caminar el path buscando el primer nombre Windows-style (`Desktop`, `Documents`, `Pictures`, etc.). Lo que está después define el sub-path del destino.
3. **Whitelist explícita** de bundles con nombre conocido (`PCSX2`, `FalkonPortable`, etc.). El algoritmo automático tiene falsos positivos.
4. **Fallback por extensión** solo para archivos sueltos a la raíz de la fuente.
5. **Catch-all explícito** (`Other/`). Mejor un 5% de archivos en `Other/` para revisión manual que perder cosas en clasificaciones agresivas.

Sub-aprendizaje: **no usar substring matching** para detectar tipos de carpeta. `if 'software' in path.lower()` parece simple pero rompe con archivos llamados "cencon-software-reference-manual.pdf". Matchear por **componente exacto del path** (`/Software/` con slashes o nombre exacto del segmento).

## 3. Política de colisiones explícita

Cuando dos archivos fuente caen en el mismo destino, hay que decidir antes:

- ¿Mismo SHA-1? → uno solo gana, log de "skipped".
- ¿Distinto SHA-1? → segundo va a `nombre__from-<origen>.ext`, log de "renamed".

Sin política, terminás con `cp -f` (sobreescribe — perdés data) o `cp -n` (no sobreescribe — perdés la versión nueva, sin saberlo). Ambos son malos. La política con hash es la única que **garantiza no perder bytes**.

## 4. Resumibilidad = state mínimo

Archivo `done.txt` con un path por línea, append-only. Cada vez que se procesa un archivo (copiado, skipped, renombrado, error), se hace `WriteLine` y `Flush()` inmediato. Re-ejecutar el script:
1. Lee `done.txt` a un `HashSet<string>` en memoria.
2. Skipea cualquier fila ya en el set.
3. El loop continúa donde quedó.

State adicional (`state.json`): contadores de copied/skipped/renamed/errors/bytes. Sirve solo para reportar progreso; **no es la fuente de verdad** (esa es done.txt).

**Trampa**: en mi versión inicial, el script PowerShell con `Copy-Item` falló pero NO agregó las filas a `done.txt` (porque la excepción saltó al catch antes del `WriteLine`). Re-ejecutar reintentó automáticamente — eso fue afortunado y por diseño. Si hubiera marcado todo como done en el path de error, el bug habría dejado el árbol corrupto.

## 5. Hashes solo cuando hay duda

SHA-1 cuesta tiempo: ~115 MB/s sostenido en mi disco. 303 GiB → ~45 minutos. NO hashear todo upfront. **Solo hashear cuando hay colisión real** (dos archivos llegan al mismo destino, entonces sí: hash de ambos para decidir si es el mismo o no).

Esto reduce el costo de hashing del 100% al ~10% — solo los ~6k archivos en colisión se hashean, no los 57k.

## 6. PowerShell — preferir APIs .NET cuando algo es performance-sensitive o tiene paths raros

`Copy-Item`, `Get-FileHash`, `New-Item` tienen parameter sets que se pueden ambiguar con paths conteniendo `[`, `]`, `;`, espacios, caracteres no-ASCII. Las APIs `.NET` directas (`[System.IO.File]::Copy`, `[System.Security.Cryptography.SHA1]`) trabajan con strings literales, son más rápidas y no tienen ese problema.

Trade-off: pierde idiomas PowerShell-style (pipelines), pero es 5-10× más rápido y **no falla con paths raros** que abundan en disco real (anime: `[Anime Time] Steins;Gate ... [BD]`, fotos con `;`, paths con tildes, etc.).

## 7. Virtualización limita

Si el script va a correr atravesando virtualización (virtiofs, NFS lento, SMB), los costos se multiplican por 5-10×. Mover el script al lado del filesystem real es la diferencia entre 12 horas y 30 minutos.

Plus: **algunos mounts no soportan operaciones que el filesystem nativo sí**. virtiofs hacia NTFS bloquea hardlink, symlink, rmdir de directorios vacíos, rm. No hay forma de saber sin probar.

## 8. Logs separados por categoría

Tener un solo log mezclado vuelve imposible ver "qué cosas se descartaron por dedup". Mejor:

- `log_skipped.tsv` — clones detectados (uno está en destino, log el otro)
- `log_renamed.tsv` — colisión con contenido distinto
- `log_errors.tsv` — fallas (esperablemente vacío)
- `log_dedupe.tsv` — duplicados cruzados que la pasada Dedupe.ps1 movió

Cada log es **auditable independientemente** (`grep`, `wc -l`, abrir en LibreOffice).

## 9. Pre-pass + main pass + post-pass

Tres pasadas separadas con responsabilidades claras:

1. **Inventory**: `find` de todo + tamaños. Read-only, idempotente.
2. **Classify**: lee inventario, produce `classification.csv` (src→dst). Reglas puramente. **No I/O sobre el disco real**, solo string-processing.
3. **Copy with collision-dedup**: pasada principal, copia + decide colisiones.
4. **Cross-tree dedup**: post-pass, encuentra clones en el árbol final que las distintas reglas mandaron a lugares distintos.

Cada pasada se puede inspeccionar y corregir antes de la siguiente. Si la classify.csv te da mal, la mirás y corregís reglas sin haber tocado el disco.

## 10. AskUserQuestion temprano y seguido

El "vibe coding" funciona porque hay **diálogo iterativo** sobre datos reales. Las decisiones críticas (estructura raíz, política de colisiones, qué hacer con archivos comprimidos, idioma de los buckets) son del usuario, no del asistente. Un asistente que decide unilateralmente termina mal en algún recoveco. Preguntar concretamente con opciones cerradas y esperar respuesta acelera, no frena.
