#!/bin/bash
# Full HTML build for a paperforge instance. paper-init copies this to
# scripts/build-web.sh and fills the @@..@@ placeholders from paper.toml.
# Order matters: ingest (wraps notation, merges insertions/extra-biblio,
# inserts lean badges) -> axiom extraction -> far-marking -> pretext build ->
# registry -> asset concatenation (registry must precede detail-ui.js).
set -euo pipefail
cd "$(dirname "$0")/.."
PF=@@PAPERFORGE_ROOT@@

# --lean-map is repeatable: PROJECT=PATH gives each independent
# formalization its own badges (per-project colors + doc links);
# --lean-badge-cap PROJECT=N caps badges per statement for projects whose
# proofs decompose one statement into many declarations.
python3 $PF/ingest/tex2ptx.py @@AI_DRAFT@@ \
    --out source --numbering crosswalk/numbering-current.json --snapshot current \
    --lean-map @@LEAN_PROJECT_NAME@@=crosswalk/lean-decl-map.json \
    --lean-annotations crosswalk/lean-annotations.json \
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
# Lazy math typesetting (single-page documents): typeset near the viewport
# only. PreTeXt owns the MathJax config, so patch the emitted startup module;
# and because lazy never processes the hidden #latex-macros div, the paper's
# macros must move into the MathJax config (mathjax_macros.py).
for f in output/web/_static/pretext/js/mathjax_startup.js \
         output/web/_static/pretext/js/dist/mathjax_startup.js; do
    [ -f "$f" ] && sed -i '' 's|"input/asciimath",|"input/asciimath", "ui/lazy",|' "$f"
done
python3 $PF/ingest/mathjax_macros.py .
python3 $PF/ingest/notation_registry.py .
python3 $PF/ingest/section_summaries_registry.py .
cat web-assets/notation-registry.js > output/web/detail-ui.js
[ -f web-assets/lean-knowls.js ] && cat web-assets/lean-knowls.js >> output/web/detail-ui.js
[ -f web-assets/section-summaries.js ] && cat web-assets/section-summaries.js >> output/web/detail-ui.js
cat web-assets/detail-ui.js >> output/web/detail-ui.js
cp web-assets/detail-ui.css web-assets/paper-style.css web-assets/fonts-cm.css output/web/
cp -R web-assets/fonts output/web/fonts
echo "build-web complete"
