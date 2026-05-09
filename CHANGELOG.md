# Changelog

Todos los cambios notables a este proyecto se documentan acá.

Formato basado en [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versionado siguiendo [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — Netbazo

### Added
- Lanzamiento inicial pos-prueba real sobre disco de 303 GiB / 57.157 archivos.
- `inventory.sh` (bash) para inventariar la raíz.
- `classify.py` (Python 3) con detección de unidades atómicas + anchor walking + fallback por extensión.
- `Organize.ps1` con APIs .NET directas (no usa cmdlets de PowerShell con parameter sets ambiguos).
- `Dedupe.ps1` para pasada cruzada post-copia.
- `Organize.bat` y `Dedupe.bat` como lanzadores de doble click.
- Documentación en `docs/`: METODOLOGIA, LECCIONES, ARQUITECTURA.
- Sample real de 77 filas en `examples/classification_sample.csv`.

### Validado en producción real
- 51.091 archivos copiados, 5.995 skipped por hash idéntico, 66 renombrados por colisión con contenido distinto, 0 errores.
- 297.4 GiB copiados sobre NTFS local en una sola corrida.
- Resumibilidad probada: ejecutaron 2 corridas, la primera con un bug en `Copy-Item`, la segunda con APIs .NET. La segunda continuó desde el state de la primera sin perder progreso.
