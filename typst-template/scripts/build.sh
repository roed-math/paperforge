#!/bin/bash
# Build a paperforge Typst instance: the interactive HTML plus one PDF per
# detail level.
#
#   scripts/build.sh <source.typ> [output-dir] [detail-levels...]
#
# The HTML is built once and carries every tier (the reader's slider chooses);
# the PDFs are built once per tier, because a PDF cannot change its mind.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_ROOT="$(dirname "$HERE")"

SRC="${1:?usage: build.sh <source.typ> [output-dir] [detail-levels...]}"
OUT="${2:-output}"
shift 2 || shift 1 || true
LEVELS=("$@")
if [ ${#LEVELS[@]} -eq 0 ]; then LEVELS=(1 2 3); fi

# `--root` must cover both the source and the library it imports.
ROOT="${PAPERFORGE_TYPST_ROOT:-$(dirname "$SRC")}"

mkdir -p "$OUT"

echo "==> HTML (all tiers, slider-controlled)"
typst compile --root "$ROOT" "$SRC" \
    --format html --features html \
    --input html-detail=1 \
    "$OUT/paper.html"

python3 "$HERE/postprocess.py" "$OUT/paper.html" --assets "$TEMPLATE_ROOT/web-assets"

for level in "${LEVELS[@]}"; do
    echo "==> PDF detail=$level"
    typst compile --root "$ROOT" "$SRC" \
        --input detail="$level" \
        "$OUT/paper-detail$level.pdf"
done

echo
echo "built:"
ls -la "$OUT" | sed 's/^/  /'
