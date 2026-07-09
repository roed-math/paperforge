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

The interactive HTML layer (detail slider, notation hovers, `<lean>` links) is
**proven** — see `pretext-template/` (ported from the de-risking spike) and
[docs/HTML-FEATURES.md](docs/HTML-FEATURES.md). The skills and most validators are
currently **specified stubs**; the reference implementation pattern is shown in
`validators/paperforge_validators/lean_links.py`.
