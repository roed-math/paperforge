---
name: apply-directives
description: Consume the directive queue — inline @forge markers and directives/*.md — applying each into the PreTeXt source, one git commit per directive.
---

# apply-directives

Requirement 11. The author's control surface. Full spec: ../../docs/DIRECTIVES.md.

## Behavior
1. Collect **inline** `@forge` XML-comment markers in `source/` and **sidecar**
   directives in `directives/*.md`.
2. For each directive, by `kind`:
   - `verbatim` — insert the supplied text essentially as-is (author's voice; skips
     generation; plagiarism-exempt).
   - `instruct` — generate the requested prose (style-corpus matched; will be
     plagiarism-checked).
3. Placement:
   - inline marker → at the marker's location.
   - sidecar with `target` xml:id → at/near that element.
   - sidecar without `target` → propose a placement and insert with a visible
     `<!-- @forge: placed here — relocate if wrong -->` marker.
4. Apply **one directive per commit**, message referencing the directive; remove
   the inline marker or move the sidecar file to `directives/applied/`.

## Guardrails
- Run `validators/directives.py` first; refuse directives whose `target` is stale.
- Never batch multiple directives into one commit — the per-commit trail is the
  audit mechanism.

## Contract

- **Reads:** `directives/*.md`, inline `@forge` markers in `source/`,
  `style.corpus`/`style.advice`.
- **Writes:** PreTeXt source edits — one commit per directive; consumed sidecars
  move to `directives/applied/`.
- **Gate:** `validators/directives.py` clean before starting (no stale targets);
  full `run_all` after.
- **Provenance:** each commit names the directive and carries a
  `Generated-by: <model-id>` trailer for `instruct` directives (`verbatim` text
  is the author's own voice — no stamp).
