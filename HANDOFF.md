# Handoff — paperforge / gq2-paper

> **Maintainer notes, not documentation.** This file is the working state of
> paperforge's *maintainer* and its *first instance* (the G_Q2 paper), on one
> particular machine. If you are starting a paper with paperforge, nothing
> here applies to you: read [README.md](README.md) and
> [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md). Everything a second
> project needs is in `docs/`; no instance-specific behavior remains in the
> tool.

Started 2026-07-12; **last refreshed 2026-08-01** (the second-project
readiness pass — see the bottom section). Working dir is usually
`~/claude/lmfdb` but ALL work is in **`~/claude/paperforge`** (the general
tool) and **`~/claude/gq2-paper`** (the first instance). **Read the project
memory `paper-pipeline-pretext.md` first** — it carries the deep,
chronological design record; this file is the actionable orientation layer
on top of it.

## Orientation (how the pieces fit)

- **paperforge** = the tool: `ingest/` (LaTeX→PreTeXt converter +
  crosswalk/notation/lean/novelty generators + `trust_table.py`),
  `validators/` (8 checks incl. `artifact_drift`), `sitegen/` (version
  footers + drift gate, homepage bg knowls, favicon gen/stamp, preview
  watcher), `records/` (three optional config-gated pipelines: token
  ledger, sanitized session corpora, dashboard apply/check), `review/`
  (the review server + injected paper-view JS), `skills/` (SKILL.md specs),
  `templates/` + `pretext-template/` (instance scaffold, `@@PLACEHOLDER@@`
  params filled by paper-init; now incl. `content/authors.xml`,
  `apply-author-metadata.{sh,xsl}`, `publication/arxiv.ptx`), `docs/`
  (ARCHITECTURE, DIRECTIVES, PLAGIARISM, HTML-FEATURES, NOTATION,
  REFERENCES, NOVELTY, REVIEW, DEPLOYMENT, EDITOR, AI-POLICIES).
- **gq2-paper** = the instance: `source/` (generated PreTeXt — NEVER
  hand-edit), `content/` (insertions layer + `authors.xml` sidecar),
  `crosswalk/`, `notation/`, `references/`, `reviews/` (the 2026-07-26/27
  external-review documents + decision queue), `scripts/` (thin
  build/deploy wrappers calling `$PF` tools), `records-pipeline/`
  (config.json + exclusions + gq2's ground-truth
  `validate_formalization.py` + gitignored work/), `blueprint*/`,
  `docbuild*/`, `formalizations/` (two submodules), `web-assets/site/`
  (the hand-authored project site). Draft of record:
  `inputs/draft/gq2-paper.tex`.
- **Live site**: https://roed314.github.io/gq2/ — deployed by
  `gq2-paper/scripts/deploy.sh` (direct push to `roed314/gq2` via the
  `github-claude` ssh alias, NOT PRs; `--test` targets
  `roed-math/gq2-test` with an isolated clone). Check currency with
  `scripts/deploy.sh --dry-run` before assuming the live site matches HEAD.

## THE RENAME + SECOND FORMALIZATION (structural — know this)

`formalizations/gq2-lean` was renamed **`formalizations/gq2-claude`** and
joined by **`formalizations/gq2-gpt`** (Turturean's independent GPT
formalization, module `Q2Presentation`, toolchain v4.28.0 ≠ GQ2's
v4.31.0-rc2). Both are fully connected: green badges → `/lean/gq2-claude/`,
indigo → `/lean/gq2-gpt/`, both with inline knowls; two Verso blueprints
ship (`/blueprint/`, `/blueprint-gpt/` — the v4.28 branch lacks
`:::proposition`, mapped via `--kind-map`). The GPT repo **vendors copies
of the Claude files** under `Induction/Roe*.lean` — exclude them when
mining its declmap, else GQ2.* decls get mis-badged. **Regen commands live
in `crosswalk/CROSSWALK.md`**; the Claude map MUST use default
`--cite-styles name,docstring`, the GPT map all four styles + the exclude +
`--lean-badge-cap gq2-gpt=1`.

## Build / verify / deploy — READ THE INTERPRETER NOTE

**CRITICAL: use `~/miniforge3/bin/python3` (3.13, has `tomllib` + `lxml`).**
Plain `python3` on this machine is Xcode CLT 3.9. `pretext` (2.43.2) and
this python live in `~/miniforge3/bin`; `latexmk` in `/Library/TeX/texbin`:

```
export PATH=~/miniforge3/bin:$PATH        # do this first, every session
cd ~/claude/gq2-paper
scripts/build-web.sh                        # trust table -> ingest -> authors
                                            # -> census + drift gate -> build
paperforge check                            # = python3 -m paperforge_validators.run_all
paperforge build arxiv --pdf
scripts/build-leandocs.sh
scripts/build-site.sh && scripts/deploy.sh  # status stamp + bg knowls +
                                            # favicon + assemble + publish
```

The instance still runs its own `scripts/build-web.sh` / `build-site.sh`;
`paperforge build web` / `build site` now do the same work generically
(`build site` delegates to an instance script when one exists). Migrating
gq2 onto the CLI is pending a byte-diff of the outputs.

**Gate baseline (2026-07-27): 0 errors, 46 warnings** (all plagiarism-
overlap notes, inherited-from-draft or pipeline-added-with-attribution).
The two drift gates (`ingest/trust_table.py --check`,
`sitegen/gen_status.py --check`) ride in build scripts AND in `run_all`
via the `artifact_drift` validator. Three sections run without summaries
by recorded waiver (`[validators.section_summaries].exempt`).

**Review server**: `.claude/launch.json` config `gq2-review` (port 8773),
already pinned to `~/miniforge3/bin/python3`; start via the Browser pane's
`preview_start {name:"gq2-review"}`. **Run exactly ONE server per instance
root** (two servers once corrupted `directives/marks.json`; writes are
atomic + locked now, but a second server is still a second writer).

**VERIFY-IN-BROWSER GOTCHAS** (all confirmed the hard way):
- Always verify UI in the browser, never statically.
- The Browser pane starves lazy MathJax at depth: force
  `MathJax.startup.document.lazyTypesetAll()`, wait ~8s; stage deep
  elements by zeroing scroll + `translateY` on `.ptx-page`.
- **`getComputedStyle` LIES for `mjx-*` elements in this pane** — trust a
  probe `<span>` + a screenshot.
- After regenerating registries, re-cat the UI bundle and hard-reload with
  `?bust=` — the pane caches aggressively.

## The 2026-07-27 port-back (what moved where)

gq2's release-eve tooling is now paperforge's; the instance calls `$PF`:

- `pretext-template/web-assets/` byte-matches gq2 again (dark-mode keys on
  the theme's `.dark-mode` class, a11y ARIA on injected knowls, homepage
  links, ToC default-open); paper-style.css keeps the variables idiom with
  gq2's verified dark palette as values.
- Author-metadata sidecar (`content/authors.xml` +
  `apply-author-metadata.{sh,xsl}`, XSL hooks in all three conversions,
  N-author pdfauthor) — scaffolded, skip-guarded for fresh instances.
- `publication/arxiv.ptx` + component conventions (print = PDF-only
  notation index; details/background = HTML-only) + project.ptx wiring.
- `sitegen/` + `ingest/trust_table.py` absorbed the five release scripts,
  parameterized by paper.toml `[site]`/`[trust_table]`; byte-parity
  verified (only the stamp-note provenance strings changed, once).
- `records/` absorbed the seven records-pipeline scripts as optional
  pipelines; all identity/prose lives in the instance's records config;
  byte-parity verified end-to-end (only generated_utc differed).
- Validators: `artifact_drift` added; the shared decl scanner learned
  `axiom` (trust-base badges resolve); section-summary waivers are config.
  gq2's 12 red findings → 0.
- templates/, paper.toml examples, docs (HTML-FEATURES, DEPLOYMENT,
  REFERENCES locator pins), and five skills refreshed to match.

## Current state

_As of the 2026-08-01 refresh. Always `git status` + `git log --oneline`
before committing or pushing — you WILL see work you didn't make._

- **paperforge**: the port series plus the 2026-08-01 second-project
  readiness pass (below) are unpushed. Push when the user is ready.
- **gq2-paper**: the port-consumption series is unpushed. The instance keeps
  its own `scripts/build-web.sh` and `scripts/build-site.sh` and is
  unaffected by the tool-side script deletions — but the CLI now covers
  both, so migrating the instance to `paperforge build web` / `build site`
  (and deleting its copies) is the natural next step, done deliberately with
  a byte-diff of the output.
- The site's stamped version footers and favicon.svg restamped once with
  paperforge-named provenance notes — they ship on the next deploy.

## The 2026-08-01 second-project readiness pass (what changed)

Prompted by a second author adopting paperforge. Three categories:

- **Portability.** `templates/build-web.sh` and
  `templates/apply-author-metadata.sh` DELETED — both were superseded by
  `paperforge build web` (`postprocess/web.py` + `_stages.author_metadata`)
  and the former carried the last BSD-only `sed -i ''`.
  `templates/build-site.sh` deleted too: site assembly is now
  `paperforge/postprocess/site.py` (no rsync, no perl). `.DS_Store`
  untracked; `.gitignore` covers macOS litter. CI runs the *full* fixture
  build and `paperforge selftest` on macOS as well as Ubuntu.
- **Real bugs.** `paperforge init --site` wrote a `scripts/build-site.sh`
  that re-entered `paperforge build site` → fork bomb (193 processes in 12s
  when reproduced); the shim is gone and `build site` refuses re-entry. The
  validators read only the deprecated `[inputs] lean_project`, so
  `paperforge check` crashed on EVERY instance `init` creates and on every
  `--no-lean` paper (`formalization_roots()` now handles both shapes; same
  fix in `sitegen/_common.py`). `paper-style.css` imported a `fonts-cm.css`
  the template never shipped (404 per page). `paperforge review --port N`
  passed the port positionally and the server rejected it.
- **Genericity + onboarding.** gq2 defaults removed from
  `templates/paper.toml` (also rewritten in the new config shape),
  `detail-ui.css` (`lean-proj-gq2-gpt`), `lean_knowls.py`,
  `blueprint_gen.py` (`--project`/`--module` now required; title defaults to
  the paper's own), `lean_ledger.py`, `lean_axioms.py`, `tex2ptx.py`,
  `trust_table.py`, and five skills. `records/sanitize.py`'s capacity
  redaction no longer eats math prose ("Lemma 9.2 core") — set
  `sanitize.capacity_pattern = CAPACITY_PATTERN_LOOSE` in the records config
  to reproduce the published gq2 corpus byte-for-byte. New:
  `paperforge selftest` (fixture end-to-end in a scratch dir),
  `paperforge build print`, and a rewritten `docs/GETTING-STARTED.md`.
  `init` now also scaffolds `agents.toml`, the style-corpus/references
  guidance, a directive example, and `requirements.txt`.

## Provenance / commit conventions

One logical change per commit. Trailer `Co-Authored-By: Claude Fable 5
<noreply@anthropic.com>` for our edits; author-supplied changes carry
`Generated-by:` naming the model; proposal artifacts carry per-item
`generator` / top-level `_generator`. Deploy commits record source SHAs.
The review UI shows "proposed by" on every card.

Template/instance sync: `pretext-template/` and `templates/` track the gq2
instance across web-assets, xsl, publication and project.ptx (modulo
`@@PLACEHOLDERS@@`) — but **genericity now outranks byte-parity**. Where the
instance needs something named after itself (its second formalization's
badge color, its build scripts), the template carries the generic form and a
commented example, and the instance keeps its own copy.
