#!/usr/bin/env bash
# Genera inventory.tsv desde una raíz dada.
# Uso: inventory.sh /path/al/disco [archivo_salida]
#
# Excluye: $RECYCLE.BIN, System Volume Information, ORGANIZADO/, ORGANIZADO_PLAN/, _DUPLICADOS/
# Output: size\tpath relativo a la raíz, una línea por archivo.

set -euo pipefail

ROOT="${1:?Usage: inventory.sh ROOT [OUTPUT]}"
OUTPUT="${2:-inventory.tsv}"

cd "$ROOT"

find . -mindepth 1 -type f \
  ! -path "./\$RECYCLE.BIN/*" \
  ! -path "./System Volume Information/*" \
  ! -path "./ORGANIZADO/*" \
  ! -path "./ORGANIZADO_PLAN/*" \
  ! -path "./_DUPLICADOS/*" \
  -printf '%s\t%p\n' > "$OUTPUT"

count=$(wc -l < "$OUTPUT")
total_bytes=$(awk -F'\t' '{s+=$1} END{print s}' "$OUTPUT")
gib=$(awk "BEGIN{printf \"%.2f\", $total_bytes/1073741824}")
echo "[ok] $count archivos, $gib GiB → $OUTPUT"
