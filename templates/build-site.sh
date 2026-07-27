#!/bin/bash
# Assemble the public site tree at output/site/ (docs/DEPLOYMENT.md layout):
#
#   /            hand-authored site pages (web-assets/site/, rsynced whole)
#   /paper/      interactive paper (PreTeXt web build)
#   /paper.pdf   the arXiv PDF, when built
#   /blueprint*/ Verso blueprint(s) of the formalization(s)
#   /lean/       doc-gen4 subsets, one per formalization
#
# Assembles whatever has been built; run scripts/build-web.sh and the
# blueprint ci-pages script first for a complete site. Deployment uses
# CDN assets by construction (asset localization is a review-server
# serve-time concern and never appears in build output).

set -euo pipefail
cd "$(dirname "$0")/.."
PF=@@PAPERFORGE_ROOT@@

# Version identifiers: refresh the stamped blocks in the source tree from
# status.json and the live artifacts (formalization pins, declared checks,
# PDF checksum). Fails the build when a hand-edited count has drifted from
# the artifact it duplicates. Skips without a status.json.
python3 $PF/sitegen/gen_status.py
# Homepage background knowls: first paragraphs of the linked background
# clusters, extracted from the built web paper (requires build-web).
# Skips without [site.bg_knowls].clusters.
python3 $PF/sitegen/gen_bg_knowls.py

SITE=output/site
rm -rf "$SITE"
mkdir -p "$SITE"

# macOS AppleDouble sidecars (._foo) ride along in extracted assets and are
# useless on a web server; keep them out of every copied tree.
EXCL=(--exclude '.DS_Store' --exclude '._*' --exclude '*~')

rsync -a "${EXCL[@]}" web-assets/site/ "$SITE/"

if [ -f output/web/paper.html ]; then
    rsync -a "${EXCL[@]}" output/web/ "$SITE/paper/"
else
    echo "WARN: output/web missing — run scripts/build-web.sh (site has no /paper/)" >&2
fi

if [ -f "@@PDF_PATH@@" ]; then
    cp "@@PDF_PATH@@" "$SITE/paper.pdf"
else
    echo "WARN: no PDF found (site has no /paper.pdf)" >&2
fi

# Verso blueprints: blueprint/ for the primary formalization, and any
# sibling blueprint-<name>/ trees for additional ones.
for bpdir in blueprint*/; do
    name=${bpdir%/}
    [ -d "$name" ] || continue
    if [ -f "$name/_out/site/html-multi/index.html" ]; then
        rsync -a "${EXCL[@]}" "$name/_out/site/html-multi/" "$SITE/$name/"
    else
        echo "WARN: $name not rendered — run $name/scripts/ci-pages.sh (site has no /$name/)" >&2
    fi
done

if [ -f "output/leandocs/@@LEAN_PROJECT_NAME@@/index.html" ]; then
    rsync -a "${EXCL[@]}" output/leandocs/ "$SITE/lean/"
else
    echo "WARN: lean docs not assembled — run scripts/build-leandocs.sh (site has no /lean/)" >&2
fi

# Dependency-graph legibility: VersoBlueprint's DOT header hardcodes small
# edge arrows (arrowsize 0.6/penwidth 1; 0.5/0.9 compact) that are hard to
# follow on the large graphs, and the style is not configurable upstream
# (GraphDotStyle defaults in VersoBlueprint/src/VersoBlueprint/Graph.lean).
# Bump them post-render in the copied blueprint trees.
for bp in "$SITE"/blueprint*/; do
    [ -d "$bp" ] || continue
    find "$bp" \( -name '*.html' -o -name 'blueprint-manifest.json' \) -print0 |
      xargs -0 perl -pi -e '
        s/arrowhead=vee, arrowsize=0\.6, penwidth=1\]/arrowhead=vee, arrowsize=1.05, penwidth=1.25]/g;
        s/arrowhead=vee, arrowsize=0\.5, penwidth=0\.9\]/arrowhead=vee, arrowsize=0.9, penwidth=1.1]/g'
done

# Favicon: the hand-authored pages carry the links themselves, but PreTeXt,
# Verso and doc-gen do not know about them, so stamp the generated trees.
# Skips when the site tree ships no favicon.svg.
python3 $PF/sitegen/apply_favicon.py "$SITE"

echo "site assembled: $SITE ($(du -sh "$SITE" | cut -f1))"
