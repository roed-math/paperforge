#!/bin/bash
# Vendor the review server's CDN dependencies for offline / low-latency use.
# Fonts (Computer Modern woffs) are small and committed in web-assets/fonts;
# MathJax (~19MB) is fetched here and gitignored. The review server uses the
# local copy automatically when vendor/node_modules/mathjax exists; without
# it, pages fall back to the CDN.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p vendor && cd vendor
[ -f package.json ] || npm init -y >/dev/null
npm install --silent mathjax@4 @mathjax/mathjax-newcm-font
echo "vendored: $(du -sh node_modules/mathjax | cut -f1) mathjax"
