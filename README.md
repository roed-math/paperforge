# paperforge

*(working name — rename freely)*

A Claude Code framework for turning an **AI-written math paper** plus a **Lean
formalization** into two synchronized outputs:

1. **LaTeX/PDF** for arXiv (generated from a PreTeXt source of truth).
2. **Structured HTML** with reader-controlled detail levels, notation hovers, and
   links into the formalization.

The **source of truth is PreTeXt** (XML), authored by Claude. Writing XML by hand
is tedious for a human but natural for an LLM; math stays LaTeX inside `<m>`. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for why, and the requirement-by-
requirement design.

## Two repositories

- **This repo (the tool):** reusable skills, validators, PreTeXt scaffolding, and
  docs. No paper content lives here.
- **An instance repo (one per paper):** the actual PreTeXt source, the config
  (`paper.toml`), the style corpus, the reference PDFs, and a pointer to the Lean
  project. Created by the `paper-init` skill, which copies `pretext-template/` and
  `templates/` into place.

The first instance is the G_Q2 paper (Lean project `~/claude/gq2-lean`).

## Two kinds of work (the core split)

Every requirement is handled by exactly one of:

- **Validators** (`validators/`, Python) — *deterministic, objective, CI-gating.*
  Notation-defined-before-use, reference correctness, `<lean>`-refs-exist,
  stale-directive detection, plagiarism n-gram overlap, section-summary presence.
  These give regression safety as the paper and formalization drift.
- **Skills** (`skills/`, Claude passes) — *generative, subjective, re-runnable.*
  Draft ingestion, bridging text, section summaries, intro novelty language,
  grammar, directive application.

If a check can be made objective, it is a validator. Everything else is a skill.

## Quickstart

```bash
# In a new empty instance repo:
/paper-init                      # scaffold from templates, write paper.toml
# ... point paper.toml at the AI draft + Lean project, drop style corpus + PDFs ...
/ingest-draft                    # AI LaTeX draft -> PreTeXt source
/bridge-text /section-summaries /intro-novelty /grammar-pass   # generative passes
python -m paperforge_validators.run_all   # gate: notation, refs, lean links, ...
pretext build web && pretext build print  # HTML + arXiv LaTeX
```

## Status

All seven validators are implemented and running on the first instance
(gq2-paper): `lean_links`, `section_summaries`, `directives`,
`numbering_drift`, `notation_order`, `plagiarism`, `references` (incl. axiom
coverage with citation-preserving discharge). The ingest toolchain
(`ingest/`) covers conversion (`tex2ptx`), Lean crosswalks (`lean_ledger`,
`lean_declmap`, `lean_axioms`, `lean_citable`), notation (`notation_far`,
`notation_registry`), corpus fetching (`fetch_arxiv_corpus`), and novelty
evidence (`novelty_evidence`). Docs: ARCHITECTURE, DIRECTIVES, PLAGIARISM,
HTML-FEATURES, NOTATION, REFERENCES, NOVELTY, REVIEW. Author review UI:
`review/review_server.py` (see docs/REVIEW.md).

Known not-yet-a-tool: the one-off matcher that recovered statement numbering
from a PDF-only old snapshot (gq2's `crosswalk/matched-v428pdf.json`) was
ad-hoc session work; when an old snapshot exists as .tex, `tex2ptx
--numbering` replaces it. Skills are SKILL.md specs consumed by Claude in
session (not yet installed as slash commands).
