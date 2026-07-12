# paperforge

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/paperforge-mark-dark.svg">
  <img src="assets/paperforge-mark.svg" alt="PaperForge: a dog-eared page being forged on an anvil" width="110" align="right">
</picture>

*(working name — rename freely)*

[![built with PaperForge](assets/paperforge-badge.svg)](https://github.com/roed-math/paperforge)

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

## AI and mathematical writing

paperforge produces AI-assisted mathematics, so its design answers to an
active community conversation and a fast-moving policy landscape.

**Publisher policies.** [docs/AI-POLICIES.md](docs/AI-POLICIES.md) surveys
how mathematics publishers (AMS, SIAM, Elsevier, Springer, Wiley,
Taylor & Francis, Cambridge, arXiv, …) treat AI-assisted writing — what must
be disclosed, in what form, and what is prohibited — and how paperforge's
provenance record is designed to generate the required disclosures
mechanically.

**Discussions worth reading.**

- Terence Tao, [*Machine-Assisted Proof*](https://www.ams.org/notices/202501/rnoti-p6.pdf),
  Notices of the AMS, January 2025 — the standard survey of how proof
  assistants, ML, and LLMs are entering research practice; see also his
  running [machine-assisted proof posts](https://terrytao.wordpress.com/tag/machine-assisted-proof/).
- The Bulletin of the AMS double special issue
  [*Will machines change mathematics?*](https://www.ams.org/journals/bull/2024-61-02/S0273-0979-2024-01836-9/viewer/)
  (April and July 2024) — perspectives from Avigad
  ([*Mathematics and the formal turn*](https://arxiv.org/abs/2311.00007)),
  Venkatesh, Granville, Cheng, Harris, and the Buzzard–Commelin–Topaz and
  Shulman formalization essays.
- AMS white paper,
  [*Artificial Intelligence: Publishing in Mathematics*](https://www.ams.org/about-us/CPub_AI-WhitePaper.pdf)
  — the society's own analysis of what AI assistance means for its journals.
- Steinberger et al.,
  [*Using Generative AI for Literature Searches and Scholarly Writing*](https://www.ams.org/notices/202401/rnoti-p93.pdf),
  Notices of the AMS, January 2024 — the integrity risks (hallucinated
  citations above all) that several of paperforge's validators exist to
  counter.
- Michael Harris's [Silicon Reckoner](https://siliconreckoner.substack.com/)
  — a sustained critical counterpoint on the automation of mathematics.
- Empirics on the policy gap:
  [*Academic journals' AI policies fail to curb the surge in AI-assisted academic writing*](https://arxiv.org/abs/2512.06705)
  and [Academ-AI](https://arxiv.org/abs/2411.15218), documenting undisclosed
  use — the failure mode paperforge's write-time provenance is built to make
  impossible.

## License

GPL v3 or (at your option) any later version — see [LICENSE](LICENSE).
