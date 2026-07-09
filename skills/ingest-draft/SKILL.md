---
name: ingest-draft
description: Convert the AI-written LaTeX draft into PreTeXt source, preserving structure and math, tagging notation and formalization links.
---

# ingest-draft

Turns `inputs.ai_draft` (LaTeX) into PreTeXt `source/`.

## Behavior
- Map LaTeX sectioning → PreTeXt `<chapter>/<section>/<subsection>`, each with an
  `xml:id` (needed for directives, cross-refs, and knowls).
- Map theorem-like environments → `<theorem>/<lemma>/<definition>/<proof>` etc.
- Keep math verbatim inside `<m>`/`<me>`/`<md>`; move `\newcommand`s into
  `docinfo/macros`.
- Where the draft references a formalized result, insert a `<lean ref="...">`
  (leave `ref` as a best guess for the author/`lean_links` validator to confirm).
- Where notation is introduced, wrap it with the `\notn{key}{symbol}` convention
  and add a `<notation>` list entry (single source of truth for the hover + the
  `notation_order` validator).
- Do **not** invent mathematical content. This is a *structural* conversion; gaps
  (missing bridging text, summaries) are filled by later skills, not here.

## Output
PreTeXt source that builds, plus a report of: unmapped environments, guessed
`<lean>` refs, and notation it could not classify.

## Plagiarism note
The AI draft is a plagiarism *source* (see docs/PLAGIARISM.md). Ingestion is
structural, but any prose it rewrites is subject to the plagiarism validator.
