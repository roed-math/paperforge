#!/bin/bash
# Assemble the public site tree at output/site/ (docs/DEPLOYMENT.md layout):
#
#   /            landing page (web-assets/site/index.html)
#   /paper/      interactive paper (PreTeXt web build)
#   /paper.pdf   the arXiv PDF, when built
#   /blueprint/  Verso blueprint of the formalization (blueprint/_out/site)
#
# Assembles whatever has been built; run build-web.sh and
# blueprint/scripts/ci-pages.sh first for a complete site. Deployment uses
# CDN assets by construction (asset localization is a review-server
# serve-time concern and never appears in build output).

set -euo pipefail
cd "$(dirname "$0")/.."

SITE=output/site
rm -rf "$SITE"
mkdir -p "$SITE"

cp web-assets/site/index.html "$SITE/index.html"

if [ -f output/web/paper.html ] || [ -f output/web/index.html ]; then
    rsync -a --exclude '.DS_Store' output/web/ "$SITE/paper/"
else
    echo "WARN: output/web missing — run scripts/build-web.sh (site has no /paper/)" >&2
fi

if [ -f "@@PDF_PATH@@" ]; then
    cp "@@PDF_PATH@@" "$SITE/paper.pdf"
else
    echo "WARN: no PDF found (site has no /paper.pdf)" >&2
fi

if [ -f blueprint/_out/site/html-multi/index.html ]; then
    rsync -a blueprint/_out/site/html-multi/ "$SITE/blueprint/"
else
    echo "WARN: blueprint not rendered — run blueprint/scripts/ci-pages.sh (site has no /blueprint/)" >&2
fi

echo "site assembled: $SITE ($(du -sh "$SITE" | cut -f1))"
