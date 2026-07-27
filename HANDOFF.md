# Handoff — paperforge / gq2-paper

Started 2026-07-12; **last refreshed 2026-07-27** (the port-back session:
gq2's release-eve tooling absorbed into the tool; historical session
narratives trimmed — git history and docs/ carry them). Working dir is
usually `~/claude/lmfdb` but ALL work is in **`~/claude/paperforge`** (the
general tool) and **`~/claude/gq2-paper`** (the first instance). **Read the
project memory `paper-pipeline-pretext.md` first** — it carries the deep,
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
PYTHONPATH=~/claude/paperforge/validators python3 -m paperforge_validators.run_all
pretext build arxiv && (cd output/arxiv && \
  PATH=/Library/TeX/texbin:$PATH latexmk -pdf -interaction=nonstopmode main.tex)
scripts/build-leandocs.sh
scripts/build-site.sh && scripts/deploy.sh  # status stamp + bg knowls +
                                            # favicon + assemble + publish
```

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

## Current state — parallel sessions are ACTIVE

_As of the 2026-07-27 refresh. Always `git status` + `git log --oneline`
before committing or pushing — you WILL see work you didn't make._

- **paperforge**: 19 commits unpushed (the port series + the older
  editor/knowl work). Working tree clean. Push when the user is ready.
- **gq2-paper**: 5 commits unpushed (the port-consumption series).
  **Uncommitted, ANOTHER SESSION'S live work — do not touch or commit:**
  `scripts/build-web.sh` gained a title-metadata Unicode sed
  (\mathbb{Q}_2 → ℚ₂ in `<title>`/OG tags, 05:27). Once that session
  commits, port the step to `templates/build-web.sh`.
- The author's emacs still holds an open buffer on the (now moved) review
  queue; its unsaved inline answers were recovered from the autosave and
  committed in `reviews/gq2-review-queue-2026-07-26.md`.
- The site's stamped version footers and favicon.svg restamped once with
  paperforge-named provenance notes — they ship on the next deploy.

## Open work / next actions

- **Push both repos** when the user is ready; **check deploy currency**
  (`deploy.sh --dry-run`) — the restamped footers are undeployed.
- **Records config decision**: `roe_squarecommutator` sessions are in the
  ledger totals but not the per-session rows (matching the published
  state) — adding the category to `apply_site.ledger_categories` (+ label
  + name prefix) is now a one-line config choice.
- **Review-queue answers**: the author's inline answers ("Approved", "list
  format needs readability work", …) are committed; verify each was
  actually followed through.
- **Editor follow-ups** (docs/EDITOR.md): Lane-2 briefing refinement;
  optimistic in-place block swap after rebuilds.
- **Standing author items**: v4.28 tex from Turturean (exact eq
  crosswalk); N9 novelty discussion; GitHub Pages enabling is manual
  (our token 404s on the Pages API).
- **MathJax SSR prerender** remains the next perf step if lazy isn't enough.

## Provenance / commit conventions

One logical change per commit. Trailer `Co-Authored-By: Claude Fable 5
<noreply@anthropic.com>` for our edits; author-supplied changes carry
`Generated-by:` naming the model; proposal artifacts carry per-item
`generator` / top-level `_generator`. Deploy commits record source SHAs.
The review UI shows "proposed by" on every card. Keep the template copies
in `paperforge/pretext-template/` and `templates/` in sync with the gq2
instance — the synced surface now spans web-assets, xsl, publication,
project.ptx, and the build/deploy scripts (modulo `@@PLACEHOLDERS@@`).
