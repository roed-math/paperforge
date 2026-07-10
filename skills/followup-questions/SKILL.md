---
name: followup-questions
description: Propose typed follow-up questions (natural next steps) from the paper + formalization into a reviewable dossier; render author-approved ones into a "Further questions" section or website-only.
---

# followup-questions

Open questions are the part of a closing section a referee actually reads —
and this pipeline holds seeds no human collects by hand. Like intro-novelty,
this skill does NOT write prose directly: it maintains the **dossier**
(`followups/questions.json`), the third decision-artifact species after
novelty claims and citation needs.

## Taxonomy (one primary class per question)

`extension` (same theorem, wider scope) | `sharpness` (minimality, converses,
no-go statements) | `application` (what the result unlocks) | `method-export`
(the technique elsewhere) | `formalization` (Lean-side continuations,
re-verification) | `data` (databases, tables, machine-readable artifacts).

## Deterministic seeds (check each on every run)

- undischarged census axioms (`crosswalk/axiom-citations.json`) — each is a
  "formalize X" candidate;
- hedges on approved novelty claims — a hedge marks a knowledge boundary;
- scope restrictions in theorem statements (hypotheses naming the specific
  field / prime / rank);
- `needs-discussion` decisions across the review artifacts;
- independence / "not used as an input" remarks — invitations to re-verify.

## Rules

- Statements are inline LaTeX (claim_inline conventions: `$math$` with the
  paper's macros, `\cite[pin]{KEY}`, `\cref{label}`, `\emph`). What the
  author approves is what typesets.
- Literature-check every question; one already answered in print is demoted
  to a citation (record the demotion), never proposed as open.
- `new_refs` = `{bib key: LaTeX entry}`, materialized into extra-biblio only
  on approval (`claim_inline.py --biblio`) — the no-orphan gate stays green
  while pending.
- Never re-propose an `author-rejected` question. Human questions coexist in
  the same file (`generator: "<author>"`).
- Rendering approved questions (a "Further questions" closing section via
  `content/insertions/`, or website-only per question) mirrors intro-novelty:
  approved items only, question-id traceability comments, plagiarism-checked.

## Contract

- **Reads:** the assembled document; `crosswalk/axiom-citations.json`; the
  other decision artifacts (hedges, needs-discussion items); the existing
  `followups/questions.json` (incremental — reviewed decisions immutable).
- **Writes:** new `proposed` items in `followups/questions.json`; at render
  time, fragments in `content/insertions/` plus new bib entries.
- **Gate:** `references.py` (no dangling or unused entries after render);
  `plagiarism.py` on rendered prose; author review in the dashboard.
- **Provenance:** every proposed item carries `"generator": "<model-id>"`;
  re-runs never modify `status`/`author_note`/`statement` on existing items.
