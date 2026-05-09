# Metodología — cómo se construyó Netbazo

> Bitácora honesta de iteraciones. La idea es que sirva para entender no solo *qué* hace el script, sino *cómo se llegó* a esta forma — incluyendo callejones sin salida y bugs que aparecieron en el camino. Útil como caso de estudio de **vibe coding** (product owner técnico + asistente AI iterando sobre datos reales).

## El problema real

Disco F:\ con 5 carpetas raíz, sumando ~57k archivos / 303 GiB:

| Fuente | Archivos | Tamaño | Comentario |
|---|---:|---:|---|
| `80gb sata\` | 43.016 | 94 GiB | Backup de un disco SATA viejo. Tiene Downloads, Temp, UPLOADS, Mis lugares Web. |
| `Nueva Carpeta (C)\(backup celu)\` | 3.127 | 44 GiB | Backup del celular Pixel 7. DCIM, Movies, WhatsApp, Android/data. |
| `Nueva Carpeta (C)\Nueva carpeta\` | 1.605 | 74 GiB | Perfil completo de Windows User (Desktop, Documents, Pictures, Music, etc.). |
| `Nueva Carpeta (C)\Nueva carpeta (2)\` | 1.011 | 18 GiB | Otra capa: 120gb / 2021 / CAMPAÑA ROL. |
| `ORDENAR\` | 8.390 | 33 GiB | Carpeta de "ya ordeno mañana". ROMs, software, otro perfil User, mails, peliculas. |
| `Takeout\` | 9 | 39 GiB | Google Takeout (zips/tgz). |

Diagnóstico: hay **mucho contenido duplicado** entre fuentes (los `Nueva carpeta` son backups iterativos del mismo perfil), y dentro de cada fuente la organización es heterogénea (algunos bundles atómicos como `PCSX2/`, otros loose files sueltos).

Objetivo: árbol único `MOBILE\ / PC\ / ARCHIVOS\` con la estructura típica de Windows User dentro de PC, sin tocar originales.

## Iteraciones del clasificador

### v1 — extensión pura (descartado)

Mirar la extensión de cada archivo y rutearlo: `.jpg → Pictures, .mp4 → Videos, .exe → Downloads`. **Problema:** un mirror HTTrack de un sitio web (`80gb sata\Mis lugares Web\donjon.bin.sh\`) explotaba en miles de archivos rutados a Pictures, Code, Documents, Downloads — perdiendo la unidad del mirror. Idem para PCSX2 (emulador) cuyo `.exe` lo mandaba a Software pero los `.dll` quedaban regados.

### v2 — extensión + nombre de carpeta de primer nivel

Si el archivo está adentro de una carpeta llamada `Pictures/` ruteo a `PC\Pictures\`. **Problemas:**
- `MapTool/runtime/legal/java.desktop/COPYRIGHT` — el "java.desktop" matcheó `Desktop` aunque era un módulo Java.
- `Downloads/cencon-software-reference-manual.pdf` — el substring "software" en el nombre del archivo matcheó la regla `SOFT_DIR_HINTS`.
- Carpeta `User/` (perfil Windows) viajaba como una unidad cuando en realidad debía descender y mergear cada subcarpeta con su par del árbol final.

### v3 — caminata por anchors + unidades atómicas (la actual)

Algoritmo final, dos pasadas:

1. **Pre-pass: detectar unidades atómicas**. Carpetas en niveles 1-3 que contienen marcadores de software (`.exe/.dll/.sys`), código (`.git/`, `node_modules/`), o sitio web (`index.html`) se marcan como **atómicas**: viajan enteras a `PC\Software\`, `PC\Code\`, `PC\Sites\`. Plus una whitelist de nombres conocidos (`PCSX2`, `FalkonPortable`, `electrum_data`, `CAMPAÑA ROL`, `UPLOADS`, etc.).

2. **Main pass: anchor walking**. Para cada archivo:
   - Si tiene un ancestro en la lista de atómicas → se va con esa unidad.
   - Sino, recorre los componentes del path buscando un "anchor" Windows-style (`Desktop`, `Documents`, `Pictures`, `Videos`, `Music`, `Downloads`, `DCIM`, `Movies`, etc.). El primer anchor que encuentra define el bucket; lo que viene después es el path relativo en el destino.
   - Si tampoco hay anchor → fallback por extensión.

Ejemplos:

```
80gb sata\Temp\Huawei\DCIM\Camera\foo.mp4
→ anchor "DCIM" en pos 3
→ PC\Pictures\Camera\foo.mp4

ORDENAR\User\Desktop\notes.txt
→ anchor "Desktop" en pos 2
→ PC\Desktop\notes.txt

80gb sata\PCSX2\plugins\GSdx32-AVX2.dll
→ atómico (PCSX2 tiene .dll)
→ PC\Games\PCSX2\plugins\GSdx32-AVX2.dll
```

**Mobile** tiene anchors propios (`DCIM → Camera`, `Movies → Videos`, `Android → AndroidData`).

Sigue habiendo casos a `PC\Other\` (catch-all) — son ~5% del total. La forma de mejorar es añadir reglas a `classify.py`.

## Iteraciones del copiador

### Intento 1 — Python serial sandbox (descartado)

Copier en Python con `shutil.copy2` corriendo en sandbox Linux con virtiofs hacia NTFS. **Resultado:** ~10 archivos/segundo, ~7 MB/s. A ese ritmo, 303 GiB tomaba 12+ horas y la sandbox tiene budget de 45s por llamada — había que hacer cientos de chunks.

### Intento 2 — Python paralelo (parcial)

`ThreadPoolExecutor(max_workers=16)` con cooperative scheduling y resume vía `done.txt`. Subió a ~30-100 archivos/segundo en files chicos, pero seguía limitado por virtiofs. Plus aparecieron archivos individuales >4 GiB (Takeout 16 GB, videos 7/6.5/5.5 GB) que ya no entraban en un solo budget de 45s.

### Intento 3 — Hardlinks (no permitido)

`ln` falla con `Operation not permitted` en este mount. El virtiofs hacia el filesystem del host no expone la operación de hardlink. Idem `ln -s` (symlinks). Idem `rm` y `rmdir`.

### Intento 4 — PowerShell con cmdlets nativos (bug encontrado)

Reescritura limpia: el usuario corre `Organize.ps1` en su Windows (NTFS local, sin virtiofs). Velocidad esperada nativa.

```powershell
Copy-Item -LiteralPath $srcAbs -Destination $dstAbs -Force
```

**Resultado real:** 54.394 errores idénticos `"No se puede resolver el conjunto de parámetros usando los parámetros con nombre especificados."` en cada fila. Issue clásico de parameter set ambiguity en `Copy-Item` cuando se mezcla `-LiteralPath` con ciertos contextos. No falló durante pruebas porque las pruebas eran sobre paths simples.

### Intento 5 — PowerShell con APIs .NET (la actual)

Reescritura usando `[System.IO.File]::Copy`, `[System.IO.Directory]::CreateDirectory`, `[System.IO.File]::Exists`, y `[System.Security.Cryptography.SHA1]` directos. **Resultado:** 51.091 archivos copiados, 5.995 skipped por hash, 66 renombrados, **0 errores**, 297 GiB en total. Velocidad nativa NTFS, ~7-10 MB/s sostenido (limitado por el disco mecánico, no por software).

## Lecciones que cristalizaron

Ver [LECCIONES.md](LECCIONES.md).


## Proceso: vibe coding con Claude Opus 4.7

Este proyecto es una corrida de **vibe coding** real — diálogo iterativo entre un product owner técnico y un asistente AI sobre datos reales del propio usuario, no fixtures sintéticos.

**Modelo usado**: [Claude Opus 4.7](https://www.anthropic.com/claude) (2026), via la app Cowork (research preview).

**Flujo seguido**:

1. **Briefing**: el usuario describe el problema concreto ("ordená este disco de 303 GiB con 5 backups solapados, sin tocar originales") y restricciones ("no quiero perder ningún archivo que no sea clon exacto").
2. **Inventario y análisis** del modelo sobre los datos reales (`find`, conteos, distribuciones de tamaño, exploración de subcarpetas representativas).
3. **Propuesta de plan** del modelo, con números concretos de qué iría a dónde, presentada al usuario para validar antes de tocar nada.
4. **Iteración del clasificador** sobre samples reales — el usuario ve "PC/Software/UPLOADS 4.816 archivos" y dice "UPLOADS no son software, son fotos de Facebook", el modelo refina las reglas, vuelve a correr, vuelve a presentar.
5. **Generación de scripts** — bash, Python, PowerShell. El usuario ejecuta sobre su máquina, reporta errores reales (los 54.394 errores de `Copy-Item`), el modelo diagnostica el bug de parameter set y reescribe con APIs .NET directas.
6. **Documentación post-hoc** del journey honesto, incluyendo intentos descartados.

**Lo que el modelo hizo bien**:

- Mantener originales intactos como invariante a pesar de varias tentaciones de "optimizar" con hardlinks o moves.
- Detectar que la primera versión del clasificador rompía el mirror HTTrack y rediseñar con detección de unidades atómicas.
- Cambiar de estrategia cuando virtiofs se mostró lento (de Python serial → Python paralelo → eventualmente PowerShell nativo en la máquina del usuario).
- No reemplazar archivos que no fueran clones exactos por hash (la regla central del usuario, sostenida en cada iteración).

**Lo que el modelo hizo mal y se corrigió**:

- Primera versión de `Organize.ps1` con `Copy-Item` falló en 54.394 archivos por parameter set ambiguity. Se reescribió con `[System.IO.File]::Copy` y otros .NET APIs.
- Tendencia a brainstormear sin permiso cuando el usuario quería conversar — corregido tras feedback explícito.
- Estimaciones de performance optimistas cuando había virtualización de por medio (virtiofs hacia NTFS).

**Lo que requirió juicio humano**:

- Decisión sobre estructura raíz (MOBILE/PC/SHARED vs por tipo de contenido vs por origen).
- Política de colisiones (skip vs sufijo, qué tag de origen usar).
- Idioma de los buckets (Windows-style en inglés, decidido por el usuario).
- Cuándo aceptar que la sandbox no escalaba y pivotar a script para correr nativo.
- Aprobación explícita antes de cada destrucción de progreso parcial o cambio de plan.

**Outcome real**: 51.091 archivos copiados, 5.995 skipped por hash idéntico, 66 renombrados por colisión con contenido distinto, **0 errores**, 297 GiB en una sola corrida. Los originales siguen intactos.

Esta carpeta `docs/` es parte del entregable porque el journey es valioso para otros que estén explorando vibe coding aplicado a problemas reales: las iteraciones descartadas, los bugs encontrados, y los puntos donde el juicio humano fue irreemplazable.

