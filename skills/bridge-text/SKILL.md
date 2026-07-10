---
name: bridge-text
description: Insert connective/bridging prose between results so the argument flows, matching the author's style corpus and the configured detail level.
---

# bridge-text

Requirement 5. The AI draft tends to jump between results; this adds the
transitions.

## Behavior
- Read `style.corpus` + `style.advice` first; match register, sentence length,
  and idiom. Do not import phrasing from the *sources* (plagiarism risk) — imitate
  the author's *own* corpus.
- Insert transitions at the configured `detail.default_level`; deeper elaboration
  goes in a higher-tier `@detail-level` block so it is optional in HTML and
  excluded from the default PDF.
- Add bridging text only where the logical gap is real; do not pad.
- Each insertion is a discrete edit (one commit) so provenance is preserved.

## Guardrails
- New prose is generated content → will be checked by `plagiarism.py`.
- Never assert a mathematical connection the author has not made; if a bridge
  requires a claim, leave a `<!-- @forge: needs author confirmation -->` marker
  instead of inventing it.

## Contract

- **Reads:** the assembled source; `style.corpus` + `style.advice` (paper.toml).
- **Writes:** transition prose in `source/` — one commit per insertion point.
- **Gate:** `run_all` — in particular `plagiarism.py` over the new prose.
- **Provenance:** `Generated-by: <model-id>` trailer on every commit.
