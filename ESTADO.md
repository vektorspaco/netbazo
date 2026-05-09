# Estado del proyecto

> Honestidad upfront para que sepas dónde estás parado antes de correr Netbazo sobre tus datos.

## Cómo se construyó

**Vibe coding sobre datos reales**, en diálogo iterativo con [Claude Opus 4.7](https://www.anthropic.com/claude). El detalle completo del proceso — iteraciones descartadas, bugs encontrados, decisiones que requirieron juicio humano — está documentado en [docs/METODOLOGIA.md](docs/METODOLOGIA.md).

No es un script profesionalmente auditado. Es código generado en colaboración AI + product owner técnico, probado contra el disco real del autor.

## Qué se probó

Una corrida end-to-end sobre el disco del autor:

- **303 GiB** totales
- **57.157 archivos**
- **5 backups solapados** de orígenes distintos (PC viejo, celular Pixel 7, ordenamientos parciales previos, Google Takeout)
- **Paths reales**: con tildes, espacios, `[`, `;`, caracteres Unicode varios, nombres largos
- **Resultado**:
  - 51.091 archivos copiados
  - 5.995 dedupeados por hash en colisión
  - 66 colisiones con contenido distinto, resueltas con sufijo `__from-<origen>`
  - **0 errores**
  - 297 GiB en destino

Andó. Sirvió. El autor recuperó orden sobre su disco.

## Qué NO se probó

Las siguientes situaciones **no fueron probadas** y podrían exponer bugs:

- Paths de más de 260 caracteres (límite tradicional de Windows)
- OneDrive con sincronización activa sobre los archivos
- Volúmenes BitLocker activos
- NTFS con compresión de archivos
- Sistemas de archivos FAT32 / exFAT / ReFS
- Sistemas multi-user con permisos especiales (ACLs custom, archivos con `Deny` explícito)
- Filesystems remotos (SMB / NFS / WebDAV)
- Sistemas no-Windows (la copia es PowerShell-only)
- Volúmenes con menos de 2× el espacio de los datos a copiar

Si tu setup incluye alguno de estos, andá con `-DryRun -Limit 100` primero para ver el plan sin tocar nada.

## Safety net real

El invariante de diseño **"originales solo-lectura"** hace que probar Netbazo sea de bajo riesgo:

- Los archivos en las carpetas fuente (`80gb sata\`, `Nueva Carpeta (C)\`, etc.) **nunca** se modifican, mueven, ni borran.
- Si Netbazo se rompe a mitad de camino, el peor escenario es: tenés una copia parcial en `F:\ORGANIZADO\`. Borrás esa carpeta, volvés al estado inicial.
- Si Netbazo termina pero el resultado no te gusta: borrás `F:\ORGANIZADO\`, queda como si no hubieras corrido nada.

Esto significa que **la única forma de perder datos es si tu disco físico falla durante la corrida**. Eso pasaría con o sin Netbazo, así que no es responsabilidad del software.

## Sin garantía

Aplica la cláusula de la licencia [MIT](LICENSE):

> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND...

Traducido a humano: **si Netbazo te come datos por un bug que mi corrida no descubrió, no tengo cómo restituirlos**. No es maldad, es realidad — el software se distribuye como una contribución gratuita "tal cual está", sin contrato de soporte ni SLA.

**Recomendación práctica**: probá Netbazo sobre una copia de tus datos, no sobre el master. Si querés ir directo sobre tus archivos, asegurate de tener un backup actualizado en otro disco / cloud antes de empezar.

## Se buscan reviewers

Este código necesita ojos. Si lo usás y querés contribuir:

**Issues bienvenidos**:
- Casos donde la clasificación rompe (un archivo terminó en una categoría rara). Mandá la fila exacta del CSV (size, source, dest) o el path problemático.
- Edge cases del dedup que detectás manualmente (clones que el script no detectó, o falsos positivos).
- Errores en cualquier corrida (incluso si tu setup tiene algo de la lista de "no probado").
- Sugerencias de mejor approach a cualquier parte del pipeline.

**PRs especialmente bienvenidos**:
- Tests sobre datos sintéticos (fixtures generables) para que la próxima corrida no dependa de un solo disco real.
- Mejor heurística para clasificar archivos que hoy caen a `Other/`.
- Soporte para casos no probados (paths >260, OneDrive, BitLocker).
- Versión Linux/macOS del flujo de copia.
- Reducción de la duplicación entre `Organize.ps1` y `Dedupe.ps1` (hash, logging).

## Estado por componente

| Componente | Estado |
|---|---|
| `inventory.sh` | ✅ Probado, simple, robusto |
| `classify.py` | ⚠️ Probado en un disco; reglas heurísticas — falsos negativos posibles en paths exóticos |
| `Organize.ps1` | ✅ Probado en producción real, 0 errores en 57k archivos |
| `Dedupe.ps1` | 🟡 Probado parcialmente (sobre el árbol generado por Organize.ps1, pero menor variedad de casos) |
| Tests automatizados | ❌ No existen aún |
| CI / GitHub Actions | ❌ No configurado |

Si vas a usarlo en datos críticos, el mínimo razonable es: backup previo + `-DryRun` + revisar logs de la primera corrida real antes de tirar más volumen.
