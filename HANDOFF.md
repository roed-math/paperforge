# Handoff — paperforge / gq2-paper

Started 2026-07-12; **last refreshed 2026-07-19**. This file spans several work
sessions — "this session" inside the historical sections refers to the session
that wrote them (dated headings mark which). Working dir is usually
`~/claude/lmfdb` but ALL work is in **`~/claude/paperforge`** (the general tool)
and **`~/claude/gq2-paper`** (the first instance). **Read the project memory
`paper-pipeline-pretext.md` first** — it carries the deep, chronological design
record; this file is the actionable orientation layer on top of it. A parallel
snapshot handoff also lives at
`~/claude/handoffs/paperforge-gq2-paper-2026-07-19.md`.

## Orientation (how the pieces fit)

- **paperforge** = the tool: `ingest/` (deterministic LaTeX→PreTeXt converter +
  crosswalk/notation/lean/novelty generators), `validators/` (7 real checks),
  `review/` (the review server + injected paper-view JS), `skills/` (SKILL.md
  specs, harness-neutral), `templates/` + `pretext-template/` (instance
  scaffold, with `@@PLACEHOLDER@@` params filled by paper-init), `docs/`
  (ARCHITECTURE, NOTATION, REFERENCES, NOVELTY, REVIEW, DEPLOYMENT, HTML-FEATURES,
  AI-POLICIES, **EDITOR**).
- **gq2-paper** = the instance: `source/` (generated PreTeXt — NEVER hand-edit),
  `content/insertions/*.ptx` (the survives-reingestion content layer),
  `crosswalk/` (numbering + tag↔Lean maps + **source-map.json**), `notation/`
  (notation-map, disambiguation), `scripts/` (build-web, build-leandocs,
  build-site, deploy), `blueprint/` (Verso), `docbuild/` (doc-gen4),
  `formalizations/` (**two** git submodules — see below). Draft of record:
  `inputs/draft/gq2-paper.tex`.
- **Live site**: https://roed314.github.io/gq2/ — deployed by
  `gq2-paper/scripts/deploy.sh` (direct push to `roed314/gq2` via the
  `github-claude` ssh alias, NOT PRs). **Deploy currency is uncertain**: the last
  SHA recorded here was `489cf51`, which predates the GPT end-to-end connection
  and later content passes. Run `scripts/deploy.sh --dry-run` and eyeball the live
  site before assuming it's current; redeploy if behind.

## THE RENAME + SECOND FORMALIZATION (structural — know this)

`formalizations/gq2-lean` was renamed **`formalizations/gq2-claude`** and joined
by **`formalizations/gq2-gpt`** (David Turturean's independent GPT formalization,
module `Q2Presentation`, toolchain v4.28.0 ≠ GQ2's v4.31.0-rc2). Consequences:
- Every statement can carry badges from BOTH formalizations: **green =
  gq2-claude** (default project), **indigo = gq2-gpt**. Tooltips name the project.
- `<lean project="...">` selects the docs subset + CSS class `lean-proj-<name>`.
- **Both formalizations are now fully connected** (GPT end-to-end connection,
  gq2-paper `774c4f9`): green badges → `/lean/gq2-claude/`, indigo →
  `/lean/gq2-gpt/`, both with inline knowls (gq2-claude 111/111 decls; gq2-gpt
  351/352 — 2 private + 1 known-missing `sec7_shearEquivariantSection`). Two Verso
  blueprints ship too: `/blueprint/` (Claude, v4.31.0 API) and `/blueprint-gpt/`
  (GPT, v4.28.0 branch, which lacks `:::proposition` — generator maps
  `proposition→theorem` via `--kind-map`).
- The correct GPT repo is **`davidturturean/gq2-lean-turturean`** @ `e868b9e`
  (it previously — wrongly — pointed at `…-turturean-complete`). Submodule SHAs at
  refresh: gq2-claude @ `91e1918` (v4.31.0-rc2), gq2-gpt @ `e868b9e` (v4.28.0).
- The GPT decl map (`crosswalk/lean-decl-map-gpt.json`, 91 tags / 354 decls) is
  mined from ITS citation discipline: backtick labels (`` `thm:main` ``) and
  "manuscript Lemma 2.2" phrases. **Gotcha**: the GPT repo *vendors copies of the
  Claude files* under `Induction/Roe*.lean` in `namespace GQ2` — excluded via
  `--exclude 'Induction/Roe*.lean'`, else GQ2.* decls get mis-badged as GPT.
- **Regen commands are in `crosswalk/CROSSWALK.md`.** The Claude map MUST use
  default `--cite-styles name,docstring` (adding label/manuscript pulls in 4
  spurious support-lemma badges); the GPT map uses all four styles + the exclude
  + `--lean-badge-cap gq2-gpt=1` (its proofs decompose one statement into ~40
  decls). Paths in `paper.toml [inputs.formalizations.gq2-gpt]`.

## Build / verify / deploy — READ THE INTERPRETER NOTE

**CRITICAL: use `~/miniforge3/bin/python3` (3.13, has `tomllib` + `lxml`).**
Plain `python3` on this machine is Xcode CLT 3.9 and breaks `notation_far.py`
(tomllib) and `lean_knowls.py` (lxml). `pretext` (2.43.2) and this python both
live in `~/miniforge3/bin`; `latexmk` is in `/Library/TeX/texbin`. So:

```
export PATH=~/miniforge3/bin:$PATH        # do this first, every session
cd ~/claude/gq2-paper
scripts/build-web.sh                        # LaTeX draft -> source/ -> output/web
                                            # (also emits crosswalk/source-map.json)
PYTHONPATH=~/claude/paperforge/validators python3 -m paperforge_validators.run_all
pretext build arxiv && (cd output/arxiv && \
  PATH=/Library/TeX/texbin:$PATH latexmk -pdf -interaction=nonstopmode main.tex)
scripts/build-leandocs.sh                   # doc-gen4 subsets -> /lean/gq2-claude/ + /lean/gq2-gpt/
scripts/build-site.sh && scripts/deploy.sh  # assemble output/site (+ both blueprints) + publish
```

**Gate baseline: 0 errors, ~12 warnings** (all inherited-from-draft or the
scanned-Milne-PDF caveat — see the validator tail; none are actionable).

**Review server**: `.claude/launch.json` config `gq2-review` (port 8773) is
already pinned to `~/miniforge3/bin/python3`. Start it with the
`mcp__Claude_Browser__preview_start {name:"gq2-review"}` tool. It injects the
review layer at serve time (paper-tags/margin/marks/**edit** JS) and sends
`no-cache` on js/css/html. **Run exactly ONE server per instance root**: two
servers writing `directives/marks.json` concurrently truncated it mid-write on
2026-07-16 and 500'd every adapter-loading endpoint. Writes now go through
`atomic_dump` (tmp + `os.replace`) under a module `_WRITE_LOCK` held across the
read-modify-write in the POST handlers, and `/api/artifacts|items|margin` +
`progress_snapshot` degrade per-adapter instead of dying — but a second server is
still a second writer, so don't start one while another is up
(`lsof -ti tcp:PORT | xargs kill` clears a stray one).

**VERIFY-IN-BROWSER GOTCHAS** (cost me real time this session, all confirmed):
- Always verify UI in the browser, never statically — a red `\notn` bug once
  shipped from a static-only check.
- This Browser pane **starves lazy MathJax** at depth (blank screenshots deep in
  the page). Force typesetting: `MathJax.startup.document.lazyTypesetAll()`, wait
  ~8s. To stage a deep element for a screenshot, zero the scroll then
  `translateY` the `.ptx-page` — iterate against the element's live
  `getBoundingClientRect().top` because page height shifts as math renders.
- **`getComputedStyle` LIES for `mjx-*` elements in this pane** (reports
  transparent even with inline styles set). Trust a probe `<span>` + an actual
  screenshot, not computed values, when checking notation/math styling.
- **Bundle staleness**: after regenerating registries, re-cat the UI bundle
  (`cat notation-registry.js lean-knowls.js section-summaries.js detail-ui.js >
  output/web/detail-ui.js`) AND hard-reload with a `?bust=` query — the pane
  caches aggressively.

## Current state — unpushed + uncommitted (don't clobber)

_As of 2026-07-19. Parallel sessions (other Claude windows + the user running GPT)
commit to these repos too, so always `git status` + `git log --oneline` before you
commit or push — you WILL see commits you didn't make._

- **paperforge @ `dd6fce9`** — **3 commits unpushed**: `fece8e3` (atomic locked
  artifact writes + fault isolation), `53202f2` (margin coverage for
  paragraph-anchored marks — parallel session), `dd6fce9` (word-snap + click-dot
  retract). Working tree clean. Push when the user is ready.
- **gq2-paper @ `3af539f`** — **2 commits unpushed**: `80bd185` (marks.json base
  repair — parallel session), `3af539f` (extend 10 mid-word-clipped mark texts).
  **Uncommitted: `directives/marks.json` — 11 NEW real marks `mk-469..mk-480`
  (479 total).** These are **the user's own in-flight `background` requests**
  (all `generator: roed`, `created: 2026-07-18`); the live server is actively
  writing this file. **Leave uncommitted; do NOT clobber. Commit only when the
  user says the review pass is done.**

## Session 2026-07-19 — review-server hardening, marks repair, mark UX

- **marks.json corruption + repair.** Two review servers against one instance
  root + threaded writes + a truncate-then-write `json.dump` left `marks.json`
  half-written (partial `mk-468`), which 500'd every adapter-loading endpoint.
  Fixed the write path (see the Review-server note above); reconstructed `mk-468`
  from the built paper (`80bd185`) and extended 10 mid-word-clipped mark texts to
  full words (`3af539f`, e.g. "inite intersection property" → "finite …").
- **Word-snap + cancel-by-dot (`dd6fce9`).** Drag-selections that start/end
  mid-word snap outward to whole words in `paper-marks.js` before recording (the
  source of the clipped texts). Mark dots are clickable everywhere now: first
  click arms (red outline + toast), a second within 2.5s retracts via
  `/api/mark-delete`; the notation-remove pen keeps its one-click retract of
  purple notation dots. Both verified live in the browser.
- **Fault isolation.** A single corrupt artifact now shows an error chip / is
  skipped rather than taking down the whole dashboard.

## Major systems built (session ending 2026-07-12; all deployed unless noted)

1. **The original 5 issues** (subsubsection headings, section-summary xref
   popups, finest-grain margin anchoring, nested-knowl boundaries, private-decl
   Lean badges) — done, then the badge one superseded: **private decls now
   carry NO badge at all** (tex2ptx filters them; XSL `nodocs` path kept as the
   robust default for other doc gaps).
2. **Notation engine, heavily reworked** (Roe's term: a **"notation link"** = the
   ?-cursor hover popup):
   - Lazy-typesetting regression fixed: math in dynamically-injected content
     (knowls, notation/section/Lean/margin panels) was rendering blank + carrying
     no `ptxnotn` classes. Fix = `options.lazyAlwaysTypeset` injected by
     `ingest/mathjax_macros.py` for those container selectors.
   - **Defsite affordance**: hovering the *defining occurrence* of a symbol shows
     no popup — the cursor becomes a **black disc / white `=`** (mirrors the ? help
     cursor); hovering elsewhere pops the definition AND highlights just the
     defining symbol in **amber** (`rgba(255,196,0,.4)` + 5px box-shadow halo).
     Hover delays halved (near 200ms / far 500ms in `paper.toml`).
   - New pens: **notation-remove** (⊘) and **background**; **terminology** links
     (summary + "more details ↗" into background material); phrase-range
     selection for marks that cross element boundaries; idempotent add/remove.
   - **R3 subscript-of-name guard**: `G_{Q_2}` links to the Galois group, not to
     Q_2 (sub/superscripts that are part of a symbol's name don't get their own
     links).
   - Notation coverage extended through the whole paper (map now 95 keys, 326
     block sense decisions); 309 flight-review marks applied.
3. **Statement detail tiers (levels 0/1)**: `detail-level="1"` is a revealable
   tier for terse-vs-full *statements* (proofs use 2+). New insertion positions
   `statement-after-N` / `statement-append`; per-statement ▸ details stepper. No
   content authored to it yet — capability is ready.
4. **Accent normalization**: `tex2ptx.fold_accents` turns `\'e` etc. into Unicode
   in prose + bibliography (Lemma 5.11 "dévissage" was rendering as literal
   `d\'evissage`); single-letter `<foreign>` splices in insertions/extra-biblio
   replaced with plain Unicode. Verified through the arXiv PDF.
5. **Knowl double-underline fix**: knowl links now carry only the theme's dotted
   affordance (the quiet-links underline was doubling + flickering with focus).
6. **Licenses**: GPL v3+ (LICENSE + README notices) on both paperforge and
   gq2-lean/gq2-claude. NOTE the Lean-ecosystem-convention caveat (Mathlib is
   Apache-2.0) — flagged to Roe, fine legally.
7. **AI-in-math docs**: README "AI and mathematical writing" section + new
   `docs/AI-POLICIES.md` (publisher-policy survey, dated 2026-07-11, moving
   target).
8. **Agent dispatch + Pipeline**: `agents.toml` enumerates dispatchable headless
   CLI agents (claude -p, codex exec; author owns permission flags). The review
   server spawns them on open marks with self-contained briefings, tracks jobs,
   runs validators on demand. Surfaced in the dashboard Pipeline tab AND the
   paper-view strip cockpit.
9. **THE PAPER-VIEW EDITOR (design + build, `docs/EDITOR.md`)** — the big one,
   see next section.
10. **Landing page redesign** (hero, action buttons, audience-labelled resource
    cards, dark mode, two-formalization cards, "Built with paperforge" footer).
11. **Margin decision panels**: knowl-style **?** legend expands every choice's
    meaning in place (was title-tooltip-only).

## The paper-view editor (built through phase 3; `docs/EDITOR.md`)

Premise Roe endorsed: the review process is a specialized editor; **the paper
view is the primary surface**, dashboard demotes to a list-shaped drawer.

- **Phase 1 — strip cockpit**: the floating strip has a validator badge (run +
  last result + tail), an agent-dispatch popover (tasks × agents, live open
  counts), a jobs chip (status + logs). All API-complete.
- **Phase 2 — margin statement editors**: novelty/followups panels get an inline
  LaTeX editor with live typeset preview + insert-citation picker, autosaving via
  `/api/decide`.
- **Phase 3 — Lane-1 block editing**: `tex2ptx --source-map` records draft
  byte-spans per labeled statement + proof (`crosswalk/source-map.json`, 87
  statements / 75 proofs). `paper-edit.js` puts **✎** on every mapped statement
  heading and proof summary (NB: PreTeXt renders proofs as SIBLING `<details>`
  after the article, not inside). `/api/edit` extract returns the block's draft
  LaTeX + a slice hash; save verifies the hash (staleness is structural — any
  splice invalidates later spans until rebuild), **rejects label/env/sectioning
  deltas toward Lane 2** (one-click send-to-agent with the typed LaTeX +
  invariants as briefing), splices the draft, and starts a tracked
  rebuild+validate job. Edits are **UNCOMMITTED by design** — the author commits
  when happy (`git diff inputs/draft` = the edit session).
- **Architectural invariant honored throughout**: `source/*.ptx` is generated and
  never hand-edited; the editor writes to the draft/insertions substrate and
  re-ingests.
- **Gotcha fixed**: job subprocesses must lead `PATH` with
  `Path(sys.executable).parent` (`_job_env`), else the build script's `python3`
  falls back to system 3.9 and dies on `tomllib`.

## Open work / next actions

- **Push the unpushed commits** in both repos (see Current state) once the user is
  ready; **confirm deploy currency and redeploy** if the live site is behind HEAD.
- **Background-sections pass** awaits the user's signal that the review is done +
  their examples/references — they've been entering `background` marks
  (`mk-469..480` and earlier). Draft global + section-local background write-ups
  **only from author-supplied references**.
- **Editor follow-ups** (from EDITOR.md): Lane-2 briefing refinement;
  **paragraph-grain editing** (prose paragraphs, not just labeled blocks — needs
  stable `p` ids from the converter); **optimistic in-place block swap** instead
  of the current reload-after-rebuild button.
- **Standing author items** (from memory, verify still open): v4.28 tex from
  Turturean (exact eq crosswalk); N9 novelty discussion; a Development-record /
  provenance page (landing shows "coming soon" — ticket-based timeline showing
  model Fable-vs-Opus, hiding status-checks; plus a story view of incidents and a
  statistics view: wall time, lane-days, tokens, Lean compile counts); GitHub
  Pages must be enabled by the user manually (our token 404s on the Pages API).
- **MathJax SSR prerender** remains offered as the next perf step if lazy isn't
  enough.

## Provenance / commit conventions

One logical change per commit. Trailer `Co-Authored-By: Claude Fable 5
<noreply@anthropic.com>` for our edits; author-supplied changes carry
`Generated-by:` naming the model, and proposal artifacts carry per-item
`generator` / top-level `_generator`. Deploy commits record source SHAs. The
review UI shows "proposed by" on every card. Keep the template copies in
`paperforge/pretext-template/web-assets/` in sync with the gq2 `web-assets/`
(they were verified in sync at handoff time).
