# Handoff — paperforge / gq2-paper session

Date: 2026-07-11. Working from `/Users/roed/claude/lmfdb` but all work is in
**`~/claude/paperforge`** (the general tool) and **`~/claude/gq2-paper`** (the
first instance; has `formalizations/gq2-lean` as a submodule). Deep background
lives in project memory `paper-pipeline-pretext.md` — read it first.

## Orientation (how the pieces fit)

- **paperforge** = the tool: `ingest/` (deterministic converters + generators),
  `validators/`, `review/` (the review server + injected JS), `skills/` (SKILL.md
  specs, harness-neutral), `templates/` + `pretext-template/` (instance scaffold).
- **gq2-paper** = the instance: `source/` (generated PreTeXt — NEVER hand-edit),
  `content/insertions/*.ptx` (the survives-reingestion content layer),
  `crosswalk/` (tag↔number, tag↔Lean-decl maps), `scripts/` (build-web,
  build-leandocs, build-site, deploy), `blueprint/` (Verso), `docbuild/`
  (doc-gen4). Draft of record: `inputs/draft/gq2-paper.tex`.
- **Live site**: https://roed314.github.io/gq2/ — deployed by
  `gq2-paper/scripts/deploy.sh` (direct push to `roed314/gq2`, NOT PRs) via the
  `github-claude` ssh alias. `scripts/build-site.sh` assembles
  `output/site/` (landing + /paper/ + paper.pdf + /blueprint/ + /lean/).
- **Git**: both repos on `roed-math` (paperforge) and via the alias. Commit
  style: one logical change per commit, trailer
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`. GPT is now also
  generating (its commits currently lack `Generated-by:` trailers — Roe is
  raising that with GPT). Provenance convention: proposal artifacts carry
  per-item `generator` or top-level `_generator`; the review UI shows it.

## Build / verify commands

```
cd ~/claude/gq2-paper
scripts/build-web.sh            # LaTeX draft -> source/ -> output/web (HTML)
pretext build arxiv             # -> output/arxiv/main.tex (then latexmk -pdf)
PYTHONPATH=~/claude/paperforge/validators python3 -m paperforge_validators.run_all
scripts/build-leandocs.sh       # doc-gen4 subset -> output/leandocs + lean-knowls registry
blueprint/scripts/ci-pages.sh   # Verso blueprint render (~20-30 min, imports all of GQ2)
scripts/build-site.sh && scripts/deploy.sh
```

Preview/verify HTML in a real browser via `.claude/launch.json` server
`gq2-review` (port 8773) + the `mcp__Claude_Preview__*` tools. **Always verify
UI changes in the browser** — a recent bug (red `\notn` everywhere) shipped
because I only checked config statically. Gate baseline: **0 errors**, ~8
plagiarism warnings (all inherited-from-draft stock phrases).

## Key gotchas already learned (don't rediscover)

- `html.js.extra` does NOT split on spaces (`html.css.extra` does). All JS must
  be ONE file — everything is concatenated into `output/web/detail-ui.js` by
  build-web.sh (order: notation-registry, lean-knowls, detail-ui).
- Lazy MathJax (`ui/lazy`) never processes the hidden `#latex-macros` div, so
  the paper's macros are injected into `tex.macros` by
  `ingest/mathjax_macros.py` (a build-web step). If macros render red, that step
  didn't run / the startup module changed shape.
- `lake update` in blueprint/ or docbuild/ rewrites `lean-toolchain` to the
  dependency's — restore GQ2's exact `v4.31.0-rc2` or the Mathlib cache breaks.
- Verso blueprint chapters MUST `import GQ2`; `:::lemma_` (trailing underscore,
  Lean keyword); `#doc` titles reject math; prose needs markdown escaping.
- The classic-LaTeX `\author` template has a blank-line bug (worked around in
  `xsl/arxiv-latex.xsl`) — candidate to upstream to PreTeXt.
- Deploy is heavy (143M with /lean/ + /blueprint/). Pages must be enabled by
  Roe manually (our token 404s on the Pages API).

## THE OPEN WORK — ALL FIVE RESOLVED (2026-07-11, deployed)

All five issues below were fixed, verified in-browser, gated (0 errors),
committed to both repos, pushed, and deployed (gq2-paper@72b5ffb).
Resolutions:

- **#0** `lean_declmap` records `private: true` (scanner yields a 5th
  field); tex2ptx emits `<lean nodocs="private">`; XSL renders a tooltip
  span (dashed pill) instead of a dead link; UI defensively unlinks any
  badge the registry lacks; lean_knowls reports 111/111 + 2 private.
- **#1** `ingest/section_summaries_registry.py` (37 divisions, from
  introductions/leading prose) + `wireSectionSummaries` in detail-ui.js:
  division xrefs open an in-place summary panel with view-in-context;
  TOC/popup links exempt. Bonus fix: bare-block `prepend` insertions now
  land INSIDE an existing `<introduction>` (sec-quadratic was degraded to
  unstructured HTML by the citation insertion sitting before its intro).
- **#2** tex2ptx converts `\subsubsection` inside a subsection to a real
  `<subsubsection>` division (intro-wrapped siblings); heading ladder in
  paper-style.css: section 1.3em > subsection 1.275em > subsubsection
  1.25em = theorem headings. LaTeX target emits real `\subsubsection`.
- **#3** adapters may expose `margin_anchor(item, tag, page)`: disambig
  anchors at the first paragraph whose math source carries the decided
  sense's \notn wrap; citations at the paragraph citing the works.
  Collapsed-proof paragraphs skipped; sense=none/unfixed stay at heading.
  20 of 76 division-grain markers moved to paragraphs.
- **#4** nested-knowl matrix in paper-style.css: any knowl surface inside
  another (xref-in-proof, lean-in-xref, section-knowl) steps to white
  with a #ddd hairline.

NB the review server needs a python with lxml — lmfdb/.claude/launch.json
now pins `~/miniforge3/bin/python3` (the bash -c env resolved python3 to
CLT 3.9, which broke /api/fragment//api/macros/margin refinement).

FOLLOW-UP ROUND (same day, deployed gq2-paper@ed4ee2f). Roe's term:
"notation link" = the hover popup with the ?-cursor tooltip. Fixes:
(1) ui/lazy regression — math in dynamically injected content (fetched
knowls, notation/section/Lean/margin panels) stayed as permanent
mjx-lazy placeholders: blank math, no notation links. mathjax_macros.py
now also injects options.lazyAlwaysTypeset for those containers.
VERIFY-GOTCHA: count mjx-lazy, not mjx-container — containers exist for
un-typeset placeholders. (2) private-decl badges dropped entirely
(tex2ptx filters them; XSL nodocs path kept as robust default).
(3) paper-margin.js: inline-layout (<1250px) markers sit at the END of
their host; the panel now opens at the clicked marker, not the heading.

Original briefing follows for reference:

### 0. Two Lean badges have no inline knowl (degrade to links)
`GQ2.SectionSeven.lam_comm_vanish` and `lam_sq_vanish` are **`private theorem`s**
(SectionSeven.lean:842, 2516). doc-gen4 does not emit doc pages for `private`
decls, so `lean_knowls.py` can't find them (111/113 covered) AND the find-
resolver badge links would 404 too.
**Fix options:** (a) ask the swarm to make these two non-private (formalization
change — cleanest, but coordinate); (b) in `ingest/lean_knowls.py` /
`tex2ptx.py`, detect decls absent from the docs and render those badges without
a link (plain text "Lean (…)" with a title tooltip) instead of a dead link.
Recommend (b) as the robust default + optionally (a). Check whether the crosswalk
should record a `private`/`no-docs` flag per decl.

### 1. Section xref links should pop up summary text (like knowls)
Currently an `<xref>` to a section is a plain navigation link; Roe wants it to
pop a summary + "view in context ↗", matching the knowl idiom. The section
summaries already exist as `<introduction>` blocks (GPT wrote all 6; that's why
the gate hit 0 errors). **Plan:** build a section-summary registry (like the
notation/lean-knowl registries) keyed by section tag → first paragraph(s) of its
`<introduction>`; in `detail-ui.js` intercept clicks on section xrefs
(distinguish them — they point at a division tag) and show a popup/knowl with
that summary + a link to the section. Extractor probably belongs in a new
`ingest/section_summaries_registry.py` run in build-web.sh.

### 2. "The Arf invariant of the candidate form" heading too small
It's a `\subsubsection` (draft line 2538). tex2ptx currently converts
`\subsubsection` to a run-in `<em class="alert">…</em>` inside a `<div class=
"para">` (verified in output/web/paper.html), so it renders italic/small instead
of as a heading larger-or-equal to the Lemmas around it. **Fix:** in
`ingest/tex2ptx.py`, convert `\subsubsection{...}` to a real PreTeXt
`<subsubsection><title>…</title>` (or at least a proper heading element), not an
alert em. Check the sectioning logic (search `subsubsection` / how
`\subsection` is handled) and mirror it. Rebuild and confirm the heading size.

### 3. Review margin: decisions at end of Section 5 pop up at section TOP
In review mode (`review/paper-margin.js`), decisions anchored at **division
grain** (a section tag) all cluster at the section heading, so a decision that's
really about the end of §5 appears at the top. Prior work already made division
anchors expand "below the heading". **Plan:** where a decision has a finer anchor
available (a specific block/paragraph id within the section), use it; only fall
back to the division heading when nothing finer exists. Check `/api/margin` in
`review_server.py` (it computes `anchors` from `it.links`) and the anchor→marker
placement in `paper-margin.js`. May need the adapters to expose a more specific
anchor for citation-needs / disambig items.

### 4. Nested knowls: grey-on-grey, need a boundary
A knowl opened inside another knowl (e.g. a `.lean-knowl` #f5f5f5 inside a proof
knowl, or PreTeXt's own nested knowls) has no visual separation. **Fix:** CSS in
`web-assets/detail-ui.css` (and/or paper-style.css) — give nested knowls a
border or a stepped background (e.g. `.lean-knowl` gets a subtle left border;
nested `.born-hidden-knowl` inside `.born-hidden-knowl` alternates shade). Verify
in-browser with a proof knowl containing a Lean knowl.

## Other threads in flight / pending (from memory, still open)

- **Blueprint backlinks**: DONE and deployed (nodes link back to paper
  statements). Blueprint = 64 nodes, 37 edges.
- **proof-details pass**: skill + briefing written
  (`gq2-paper/directives/proof-details-briefing.md`); Roe just refined the spec
  to scatter detail paragraphs after the step they elaborate via
  `position: proof-after-N` (N = 1-based authored-paragraph index). This IS
  implemented in `tex2ptx.apply_insertions` (positions handled: `after`,
  `prepend`, `proof-after-N` at line ~1077, `proof-append`, default `append`).
  So GPT can run the pass against the current briefing as-is.
- **background-sections skill**: spec'd; waiting on Roe's topic examples list.
- **marks review UI**: `paper-marks.js` (click-to-mark pens) + `directives/
  marks.json` + Marks dashboard tab — DONE. `detail-low` marks feed proof-details.
- **Still pending from Roe**: v428 tex from Turturean (for exact eq crosswalk);
  N2/N9 novelty discussion; intro-novelty render after review; enabling GitHub
  Pages; background topic list.
- **MathJax SSR prerender** offered as the next perf step if lazy isn't enough.

## Immediate next action

(Done — see the resolution list at the top.) Remaining open threads are in
"Other threads in flight": GPT's proof-details pass, background-sections
awaiting Roe's topic examples, v428 tex from Turturean, N2/N9 novelty
discussion + intro-novelty render, GitHub Pages enablement by Roe.
