---
name: grammar-pass
description: Fix grammar, article usage, and awkward phrasing across the PreTeXt prose without altering mathematical meaning or notation.
---

# grammar-pass

Requirement 9. The AI draft has grammar problems; this cleans them.

## Behavior
- Correct grammar, articles, agreement, and awkward constructions in prose only.
- Never touch content inside `<m>/<me>/<md>`, code, or `verbatim` directive text.
- Preserve technical terms and the author's stylistic choices (don't "correct"
  deliberate conventions found in the style corpus).
- Prefer minimal edits; each is a discrete commit.

## House style
- **No em-dashes in manuscript prose** (gq2 release-eve rule, 2026-07-27):
  rewrite an em-dash construction as a comma clause, parenthetical, colon,
  or a new sentence, across the manuscript, insertions, background drafts,
  and popup definitions alike. En dashes in ranges ("(1.1)–(1.3)", page
  spans) are unaffected.

## Guardrails
- A grammar fix must not change meaning. If fixing a sentence requires a
  mathematical judgment, leave a marker for the author instead.
- This pass is the most mechanical; consider running it last, after content passes
  have settled, to avoid re-editing.

## Contract

- **Reads:** prose in `source/` (never math or `verbatim` directive text);
  `style.corpus` for deliberate conventions.
- **Writes:** minimal prose edits — discrete commits.
- **Gate:** `run_all` stays clean; meaning preservation is reviewed by the author
  on the diffs.
- **Provenance:** `Generated-by: <model-id>` trailer on every commit.
