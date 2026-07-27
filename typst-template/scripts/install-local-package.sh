#!/bin/bash
# Make the backend importable from any instance as `@local/paperforge:0.1.0`.
#
# A symlink rather than a copy, so editing the template takes effect in every
# instance immediately — the tool/instance split paperforge already uses for the
# PreTeXt template, expressed in Typst's own package mechanism.
set -euo pipefail

TEMPLATE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(sed -n 's/^version *= *"\(.*\)"/\1/p' "$TEMPLATE_ROOT/typst.toml")"

case "$(uname -s)" in
    Darwin) BASE="$HOME/Library/Application Support/typst/packages/local" ;;
    *)      BASE="${XDG_DATA_HOME:-$HOME/.local/share}/typst/packages/local" ;;
esac

DEST="$BASE/paperforge/$VERSION"
mkdir -p "$(dirname "$DEST")"

if [ -L "$DEST" ]; then
    rm "$DEST"
elif [ -e "$DEST" ]; then
    echo "refusing to replace non-symlink $DEST" >&2
    exit 1
fi

ln -s "$TEMPLATE_ROOT" "$DEST"
echo "linked $DEST -> $TEMPLATE_ROOT"
echo "instances can now use: #import \"@local/paperforge:$VERSION\": *"
