#!/bin/bash
# Deploy output/site/ to the public GitHub Pages repo.
#
#   scripts/deploy.sh              assemble (if needed) and push
#   scripts/deploy.sh --dry-run    show what would change; no push
#
# Deployment model (docs/DEPLOYMENT.md): a separate PUBLIC repo holds only
# the assembled site; this script pushes a single commit to its main branch,
# which GitHub Pages serves. Running this script IS the publish decision —
# review happens upstream (validators + the review dashboard), not in
# site-repo PRs. Each deploy commit records the source SHAs for provenance.
#
# One-time setup on GitHub:
#   1. create the public site repo
#   2. Settings -> Pages -> deploy from branch `main`, root

set -euo pipefail
cd "$(dirname "$0")/.."

SITE_REPO="${SITE_REPO:-@@SITE_REPO@@}"
SITE=output/site
CLONE=.cache/site-deploy
DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

[ -d "$SITE" ] || scripts/build-site.sh

if [ ! -d "$CLONE/.git" ]; then
    rm -rf "$CLONE"
    if ! git clone --depth 1 "$SITE_REPO" "$CLONE" 2>/dev/null; then
        echo "Could not clone $SITE_REPO — create the public repo first" >&2
        exit 1
    fi
fi

git -C "$CLONE" fetch -q origin && git -C "$CLONE" reset -q --hard origin/main 2>/dev/null || true
rsync -a --delete --exclude '.git' "$SITE/" "$CLONE/"
touch "$CLONE/.nojekyll"

PAPER_SHA=$(git rev-parse --short HEAD)
LEAN_SHA=$(git -C "@@LEAN_SUBMODULE@@" rev-parse --short HEAD 2>/dev/null || echo "-")

git -C "$CLONE" add -A
if git -C "$CLONE" diff --cached --quiet; then
    echo "site unchanged — nothing to deploy"
    exit 0
fi

if [ "$DRY_RUN" = 1 ]; then
    echo "--- dry run: would deploy ---"
    git -C "$CLONE" diff --cached --stat | tail -15
    git -C "$CLONE" reset -q
    exit 0
fi

git -C "$CLONE" commit -q -m "Deploy site

Source: paper@$PAPER_SHA, formalization@$LEAN_SHA"
git -C "$CLONE" push -q origin HEAD:main
echo "deployed: paper@$PAPER_SHA + formalization@$LEAN_SHA -> $SITE_REPO"
