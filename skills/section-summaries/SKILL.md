---
name: section-summaries
description: Write an <introduction> summary at the start of every section, with length/depth scaled to the section's difficulty.
---

# section-summaries

Requirement 6. Every section gets a summary; the `section_summaries` validator
enforces *presence*, this skill supplies *quality*.

## Behavior
- For each division lacking an `<introduction>`, write one.
- Scale depth to difficulty: a routine section gets a sentence or two; a hard/novel
  section gets a roadmap (what is proved, the key idea, dependencies).
- Difficulty signal: prefer an explicit `difficulty="1..3"` attribute on the
  division if present; else infer from proof length / dependency count and record
  the inferred level as that attribute so it is reviewable.
- Match the style corpus. Summaries are prose → subject to the plagiarism check.

## Interaction with detail tiers
The summary itself is core (always shown). A deeper "proof sketch" belongs in a
higher `@detail-level` block within the introduction, so it is collapsible in HTML.

## Contract

- **Reads:** divisions lacking an `<introduction>` (the worklist is exactly the
  `validators/section_summaries.py` error list); `style.corpus`/`style.advice`.
- **Writes:** an `<introduction>` per missing division plus a reviewable
  `difficulty` attribute — one commit per division.
- **Gate:** `section_summaries.py` reports zero errors; `plagiarism.py` clean on
  the new prose.
- **Provenance:** `Generated-by: <model-id>` trailer on every commit.
