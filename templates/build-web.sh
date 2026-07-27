#!/bin/bash
# Full HTML build for a paperforge instance. paper-init copies this to
# scripts/build-web.sh and fills the @@..@@ placeholders from paper.toml.
# Order matters: trust table -> ingest (wraps notation, merges
# insertions/extra-biblio, inserts lean badges) -> author metadata ->
# axiom extraction (+ trust-table drift gate) -> far-marking -> prose terms
# -> pretext build -> registries -> asset concatenation (registries must
# precede detail-ui.js).
set -euo pipefail
cd "$(dirname "$0")/.."
PF=@@PAPERFORGE_ROOT@@

# Trust-base table: regenerate from the committed axiom census + annotations
# before ingest consumes the insertion (no-op without [trust_table]).
python3 $PF/ingest/trust_table.py

# --lean-map is repeatable: PROJECT=PATH gives each independent
# formalization its own badges (per-project colors + doc links);
# --lean-badge-cap PROJECT=N caps badges per statement for projects whose
# proofs decompose one statement into many declarations.
# --author is repeatable ('Name|Affiliation line|...'); @draft appends the
# draft's own author block after the explicit ones.
python3 $PF/ingest/tex2ptx.py @@AI_DRAFT@@ \
    --out source --numbering crosswalk/numbering-current.json --snapshot current \
    --source-map crosswalk/source-map.json \
    --lean-map @@LEAN_PROJECT_NAME@@=crosswalk/lean-decl-map.json \
    --lean-annotations crosswalk/lean-annotations.json \
    --notation-map notation/notation-map.json \
    --mathbb @@MATHBB_LETTERS@@ \
    --disambig notation/disambiguation.json \
    --extra-biblio references/extra-biblio.xml \
    --bib-labels references/bib-labels.json \
    --insertions content/insertions
# Canonical author records (emails, status footnotes) from content/authors.xml;
# skips quietly while the sidecar declares no records.
scripts/apply-author-metadata.sh
python3 $PF/ingest/lean_axioms.py @@LEAN_ROOT@@ \
    --current crosswalk/numbering-current.json \
    --old crosswalk/matched-old-snapshot.json \
    --old-numbering crosswalk/numbering-old-snapshot.json \
    --out crosswalk/axiom-citations.json \
    --seed-aliases source/main.ptx --aliases-out references/bib-aliases.json
# Drift gate: fail the build if the freshly extracted census no longer
# matches the trust-base table baked into the intro (rerun the build after
# updating the trust annotations to clear it).
python3 $PF/ingest/trust_table.py --check
python3 $PF/ingest/notation_far.py .
# Prose term links (hover popups on prose terms): wraps <termref> in the
# generated tree AFTER far-marking (word counts must see unwrapped text);
# no-op without a prose map.
python3 $PF/ingest/prose_terms.py . --report crosswalk/prose-terms-report.json
pretext build web
# Lazy math typesetting (single-page documents): typeset near the viewport
# only. PreTeXt owns the MathJax config, so patch the emitted startup module;
# and because lazy never processes the hidden #latex-macros div, the paper's
# macros must move into the MathJax config (mathjax_macros.py).
for f in output/web/_static/pretext/js/mathjax_startup.js \
         output/web/_static/pretext/js/dist/mathjax_startup.js; do
    if [ -f "$f" ]; then
        sed -i '' 's|"input/asciimath",|"input/asciimath", "ui/lazy",|' "$f"
    fi
done
# ToC visible by default: PreTeXt bakes the sidebar closed
# (class="ptx-sidebar hidden"); strip the class so the wide-screen
# default-open rule in paper-style.css applies. The toggle's open/close
# behavior is unchanged (it re-adds .hidden on close).
sed -i '' 's/class="ptx-sidebar hidden"/class="ptx-sidebar"/' output/web/*.html
python3 $PF/ingest/mathjax_macros.py .
python3 $PF/ingest/notation_registry.py .
python3 $PF/ingest/section_summaries_registry.py .
# single UI bundle: registries first, wiring last. NB html.js.extra does NOT
# split on spaces (unlike html.css.extra) — everything must be one file.
cat web-assets/notation-registry.js > output/web/detail-ui.js
for f in web-assets/lean-knowls-*.js; do    # one registry per formalization
    if [ -f "$f" ]; then cat "$f" >> output/web/detail-ui.js; fi
done
if [ -f web-assets/section-summaries.js ]; then
    cat web-assets/section-summaries.js >> output/web/detail-ui.js
fi
cat web-assets/detail-ui.js >> output/web/detail-ui.js
cp web-assets/detail-ui.css web-assets/paper-style.css web-assets/fonts-cm.css output/web/
cp -R web-assets/fonts output/web/fonts
echo "build-web complete"
