#!/bin/bash
# Full HTML build for a paperforge instance. paper-init copies this to
# scripts/build-web.sh and fills the @@..@@ placeholders from paper.toml.
# Order matters: ingest (wraps notation, merges insertions/extra-biblio,
# inserts lean badges) -> axiom extraction -> far-marking -> pretext build ->
# registry -> asset concatenation (registry must precede detail-ui.js).
set -euo pipefail
cd "$(dirname "$0")/.."
PF=@@PAPERFORGE_ROOT@@

python3 $PF/ingest/tex2ptx.py @@AI_DRAFT@@ \
    --out source --numbering crosswalk/numbering-current.json --snapshot current \
    --lean-map crosswalk/lean-decl-map.json \
    --notation-map notation/notation-map.json \
    --mathbb @@MATHBB_LETTERS@@ \
    --disambig notation/disambiguation.json \
    --extra-biblio references/extra-biblio.xml \
    --insertions content/insertions
python3 $PF/ingest/lean_axioms.py @@LEAN_ROOT@@ \
    --current crosswalk/numbering-current.json \
    --old crosswalk/matched-old-snapshot.json \
    --out crosswalk/axiom-citations.json \
    --seed-aliases source/main.ptx --aliases-out references/bib-aliases.json
python3 $PF/ingest/notation_far.py .
pretext build web
python3 $PF/ingest/notation_registry.py .
cat web-assets/notation-registry.js web-assets/detail-ui.js > output/web/detail-ui.js
cp web-assets/detail-ui.css web-assets/paper-style.css output/web/
echo "build-web complete"
