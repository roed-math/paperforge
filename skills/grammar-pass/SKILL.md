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

## Guardrails
- A grammar fix must not change meaning. If fixing a sentence requires a
  mathematical judgment, leave a marker for the author instead.
- This pass is the most mechanical; consider running it last, after content passes
  have settled, to avoid re-editing.
