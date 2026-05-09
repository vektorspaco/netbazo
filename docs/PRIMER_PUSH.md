# Primer push a GitHub — cheatsheet

La organización [`vektorspaco`](https://github.com/vektorspaco) ya está creada.
Estos son los pasos restantes para que `netbazo` quede público.

## 1) Crear el repo vacío en la org

En `https://github.com/vektorspaco`:

1. Click en *New repository*.
2. **Repository name**: `netbazo`
3. **Description** (suggestion):
   *Sysadmin script con vocación de álgebra lineal: toma un disco con backups solapados y devuelve la base — el conjunto mínimo sin clones que genera todo. Vibe coded con Claude Opus 4.7.*
4. Visibility: **Public**.
5. **Initialize this repository with**: ⚠️ **NO marcar nada** (ni README, ni .gitignore, ni LICENSE — los traemos del local).
6. Click *Create repository*.

## 2) Push del local al remoto

Desde PowerShell, parado en `F:\netbazo\`:

```powershell
cd F:\netbazo

# Configurar identidad para este repo (no afecta a otros)
git config user.name  "vektorspaco"
git config user.email "asimovcomputacion@gmail.com"

# Init y primer commit
git init
git branch -M main
git add .
git status              # revisar que NO entran cosas excluidas (state.json, ORGANIZADO/, etc.)
git commit -m "v0.1.0: Netbazo — clasificador anchor-walking + organize/dedupe en PowerShell"

# Conectar al remoto y subir
git remote add origin https://github.com/vektorspaco/netbazo.git
git push -u origin main
```

## 3) Tag de release

```powershell
git tag -a v0.1.0 -m "Validado en producción real: 51k archivos / 297 GiB / 0 errores"
git push origin v0.1.0
```

GitHub te detecta el tag y te ofrece convertirlo en un **Release** con notas.

## 4) Topics y descripción para SEO

En la página del repo en GitHub, click ⚙️ al lado de *About* y agregá:

- **Description**: misma que arriba.
- **Website**: `https://espaciovectorial.tech` cuando tengas la landing arriba; mientras tanto vacío.
- **Topics**: `powershell`, `python`, `backup`, `deduplication`, `file-management`, `windows`, `vibe-coding`, `linear-algebra`, `sha1`, `sysadmin`, `dedupe`, `disk-cleanup`, `claude`, `opus`.

## 5) Antes del primer push, sanity check

```powershell
# Que la identidad git sea la correcta para este repo
git config user.name
git config user.email

# Que .gitignore esté excluyendo todo lo que tiene que excluir
git status --ignored
```

`git status --ignored` debe listar como ignored: `state.json`, `done.txt`, `log_*.tsv`, `ORGANIZADO*/` si están — esos NO entran al repo.

## 6) Push del profile de la org (`.github` repo) — separado

El profile README de la organización vive en un repo aparte llamado `.github` adentro de la org. Hay material listo en `F:\vektorspaco-profile\`:

```powershell
# Crear el repo .github en https://github.com/vektorspaco (Public, sin initialize)
# Después:
cd F:\vektorspaco-profile
git init
git branch -M main
git config user.name  "vektorspaco"
git config user.email "asimovcomputacion@gmail.com"
git add .
git commit -m "Profile README inicial"
git remote add origin https://github.com/vektorspaco/.github.git
git push -u origin main
```

Una vez pusheado, `https://github.com/vektorspaco` muestra el banner "Espacio Vectorial · sysadmin tools con vocación de álgebra lineal" arriba del listado de repos.
