#!/bin/bash
# Reconcile tex2ptx's generated frontmatter with canonical instance metadata.
set -euo pipefail
cd "$(dirname "$0")/.."

SOURCE=source/main.ptx

# No author records -> tex2ptx's generated frontmatter stands (a fresh
# instance ships content/authors.xml with the records commented out).
RECORDS=$(xmllint --xpath 'count(/author-metadata/record)' content/authors.xml 2>/dev/null || echo 0)
if [ "${RECORDS%%.*}" = "0" ]; then
    echo "apply-author-metadata: no author records; skipping"
    exit 0
fi

TMP=$(mktemp "${TMPDIR:-/tmp}/main-authors.XXXXXX")
NORMALIZED=$(mktemp "${TMPDIR:-/tmp}/main-authors-normalized.XXXXXX")
trap 'rm -f "$TMP" "$NORMALIZED"' EXIT

xsltproc --nonet xsl/apply-author-metadata.xsl "$SOURCE" > "$TMP"

# libxslt canonicalizes the XML declaration and root-attribute order.  Those
# bytes are unrelated to author metadata, so retain tex2ptx's original first
# two lines and use the transform only for the document body.
test "$(sed -n '1p' "$SOURCE")" = '<?xml version="1.0" encoding="utf-8"?>'
grep -q '^<pretext ' "$SOURCE"
grep -q '^<pretext ' "$TMP"
{
    sed -n '1,2p' "$SOURCE"
    tail -n +3 "$TMP"
    printf '\n'
} > "$NORMALIZED"
xmllint --noout "$NORMALIZED"

if ! cmp -s "$NORMALIZED" "$SOURCE"; then
    mv "$NORMALIZED" "$SOURCE"
fi
