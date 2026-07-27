# paperforge

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/paperforge-mark-dark.svg">
  <img src="assets/paperforge-mark.svg" alt="PaperForge: a dog-eared page being forged on an anvil" width="110" align="right">
</picture>

*(working name — rename freely)*

[![built with PaperForge](assets/paperforge-badge.svg)](https://github.com/roed-math/paperforge)

A framework for turning an **AI-written math paper** plus a **Lean
formalization** into two synchronized, verifiable outputs:

1. **LaTeX/PDF** for arXiv (generated from a PreTeXt source of truth);
2. **Structured HTML** with reader-controlled detail levels, notation
   hovers, and per-statement links into the formalization —
   optionally wrapped in a whole project site with API docs, Verso
   blueprints, and a public development record.

The **source of truth is PreTeXt** (XML), authored and maintained by an
agent — writing XML by hand is tedious for a human but natural for an LLM,
and math stays LaTeX inside `<m>`. The arXiv LaTeX is treated as generated
output. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the
requirement-by-requirement design.

The exercised instance is the G_Q2 paper:
**https://roed314.github.io/gq2/** — paper, PDF, two independent
formalizations with per-statement badges, blueprints, API docs, and the
full AI-development record with token accounting.

## What you get

- **A faithful converter** (`ingest/tex2ptx.py`): deterministic
  LaTeX→PreTeXt with a numbering simulator (validated against pdflatex's
  `.aux`), stable `xml:id` identity across renumberings, author metadata,
  alphabetic bibliography labels, and a byte-span source map that powers
  in-browser editing of the original draft.
- **The reading experience**: knowl proofs, a global detail slider with
  per-proof tiers, notation hovers with definition-site highlighting,
  section-summary popups, equation-range knowls, dark mode, print/HTML
  content splits.
- **Formalization linkage**: `<lean>` badges per statement (multiple
  independent formalizations, color-coded), inline doc knowls, doc-gen4
  subsets, Verso blueprints with Lean-derived dependency graphs, and an
  axiom census whose citations are validated like everything else.
- **Eight deterministic validators** (`paperforge-check`): Lean refs
  resolve, summaries present, directives fresh, notation
  defined-before-use, numbering drift, reference/citation coverage,
  plagiarism n-grams, artifact drift.
- **The author cockpit**: a local review dashboard + the paper view as
  editor — margin marks, decision cards, statement/proof/paragraph
  editing that splices the LaTeX draft and rebuilds, all autosaved into
  committed JSON artifacts.
- **Provenance throughout**: every generated item stamped with its
  generator, every applied change a discrete commit, and optional
  development-record pipelines (token ledger, sanitized session corpora,
  cost dashboard) for publishing how the paper was made.

## Two repositories

- **This repo (the tool):** converter + generators (`ingest/`), validators
  (`validators/`), site assembly (`sitegen/`), development-record
  pipelines (`records/`), the review server (`review/`), agent-executed
  skills (`skills/`), instance scaffolding (`pretext-template/`,
  `templates/`), and docs. No paper content lives here.
- **An instance repo (one per paper):** the PreTeXt source, `paper.toml`,
  the style corpus, reference PDFs, decision artifacts, and pointers to
  the Lean project(s). Scaffolded by the `paper-init` skill.

Lessons flow one way: instance-specific tooling gets generalized back into
the tool, parameterized by config, and the instance copy is deleted.

## The core split: validators vs skills

Every requirement is handled by exactly one of:

- **Validators** (`validators/`, Python) — *deterministic, objective,
  CI-gating.* They never write; a failure means a human or a skill must
  fix something.
- **Skills** (`skills/`, agent-executed instruction files) — *generative,
  subjective, re-runnable.* Draft ingestion, bridging text, summaries,
  novelty exposition, background sections, grammar. Each ends with a
  **Contract** block (reads/writes/gate/provenance) so any agent that
  honors it is a valid executor — acceptance is enforced by the
  validators and author review, never by trusting the generator.

If a check can be made objective, it is a validator. Everything else is a
skill.

## Quickstart

**[docs/GETTING-STARTED.md](docs/GETTING-STARTED.md)** is the real
walkthrough (host requirements, scaffolding, the loop, what's optional).
The shape of it:

```bash
pip install -e <paperforge>/validators      # once: the paperforge-check gate

# in a new empty instance repo, with an agent following skills/paper-init:
#   scaffold, fill paper.toml, drop in draft + style corpus + reference PDFs
# then iterate:
scripts/build-web.sh          # ingest -> census + drift gates -> HTML build
paperforge-check              # the eight validators
python3 <paperforge>/review/review_server.py    # the author cockpit
pretext build arxiv           # journal-style LaTeX when wanted
scripts/build-site.sh && scripts/deploy.sh      # the project site (optional)
```

## Layout

| dir | what |
|---|---|
| `ingest/` | LaTeX→PreTeXt converter; crosswalk, notation, axiom-census, trust-table, novelty, corpus tools |
| `validators/` | the `paperforge_validators` package (pip-installable; `paperforge-check`) |
| `sitegen/` | project-site assembly: version footers + drift gate, homepage knowls, favicon, preview watcher |
| `records/` | optional development-record pipelines: token ledger, sanitized corpora, dashboard apply/check |
| `review/` | the review server + the paper-view editor/margin/marks layers it injects |
| `skills/` | agent-executed passes, one SKILL.md each, Contract blocks throughout |
| `pretext-template/` | instance scaffold: XSL conversions, publication files, web-assets UI layer, authors sidecar |
| `templates/` | instance scaffold: `paper.toml`, build/deploy scripts, directive examples |
| `docs/` | see the index below |

## Documentation

| doc | covers |
|---|---|
| [GETTING-STARTED](docs/GETTING-STARTED.md) | starting a second instance: requirements, scaffolding, the loop |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | the design: requirement→mechanism map, moving-target strategy, agent-swap interface |
| [DIRECTIVES](docs/DIRECTIVES.md) | the human-in-the-loop control surface (inline markers + sidecar queue) |
| [NOTATION](docs/NOTATION.md) | the notation map, hovers, disambiguation, order checking |
| [REFERENCES](docs/REFERENCES.md) | citation completeness, axiom coverage, locator pins, bib labels |
| [PLAGIARISM](docs/PLAGIARISM.md) | the n-gram guard and its provenance labeling |
| [NOVELTY](docs/NOVELTY.md) | the claims dossier: five novelty classes and their evidence |
| [HTML-FEATURES](docs/HTML-FEATURES.md) | the interactive layer's feature contracts and gotchas |
| [REVIEW](docs/REVIEW.md) | the review dashboard and in-chat review |
| [EDITOR](docs/EDITOR.md) | the paper view as editor: lanes, source map, structural gates |
| [DEPLOYMENT](docs/DEPLOYMENT.md) | site structure, build/deploy scripts, version footers, records pipelines |
| [AI-POLICIES](docs/AI-POLICIES.md) | publisher policies on AI-assisted mathematical writing |

## Status and honest limitations

Everything above is implemented and running on the first instance; the
validators, converter, sitegen and records pipelines were all verified
byte-for-byte against it when generalized. Known rough edges for a second
project:

- **One exercised instance.** Instance-specific assumptions surely remain;
  the second paper will find them.
- **Skills are not installed commands.** They are instruction files an
  agent follows (Claude Code today); there is no `paperforge run <skill>`
  driver yet — deliberately deferred until a second harness is real.
- **The core-XSL import is an absolute path** (`paper.toml [build]`
  `pretext_core_xsl` + the two LaTeX siblings) — per-machine until the
  portable import is sorted.
- **PreTeXt 2.43.x is what's exercised**; the XSL overrides ride on core
  internals (and two upstream-bug workarounds) that may shift.
- **The records pipelines' worked example lives in the instance**
  (gq2-paper's `records-pipeline/`), not here.

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
