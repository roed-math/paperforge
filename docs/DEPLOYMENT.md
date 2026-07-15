# Deployment

The published artifact is more than the paper: a GitHub Pages site carrying
the interactive paper, ways of interacting with the formalization, and the
AI-development provenance. Design decisions recorded 2026-07-10; nothing here
is built yet except what the review server already provides locally.

## Site structure

```
/            landing page (hand-written): abstract, authors, links to all of it
/paper/      PreTeXt HTML — the interactive document (knowls, notation hovers,
             detail slider, lean badges, margin tags)
/paper.pdf   the arXiv PDF
/lean/       formalization docs (phase A: doc-gen4; phase B: Verso companion)
/provenance/ the AI-development record (three views, below)
```

One publishing repo (or a `gh-pages` branch of the instance repo); once the
paper is on arXiv, versioned snapshots (`/v1/`, `/v2/`, …) with `/` tracking
the latest.

## Asset policy (decision: CDN in deployment)

The build output already references the MathJax CDN — localization is a
**serve-time** rewrite in `review_server.py`, used only for local review, and
never touches `output/web`. So a deployed site uses the CDN by construction;
`vendor/` stays gitignored and unpublished. The Computer Modern *text* fonts
are different: they are committed instance assets (`web-assets/fonts/`) and
ship with the site.

`build-web.sh --deploy` is the placeholder for deployment deltas as they
appear — project-page base path (`user.github.io/repo/`), versioned snapshot
directory, any published-only toggles. Asset handling needs nothing from it
today.

## Formalization interaction (phase-gated)

**Wait**: the formalization is still being improved; build this when it
stabilizes.

- **Phase A — doc-gen4** API docs for the project modules, hosted under
  `/lean/`, so the paper's `<lean>` badges resolve. Size risk to verify at
  build time: full import-closure docs (Mathlib) run to several GB vs the
  Pages ~1 GB limit — mitigate with module-filtered generation plus
  cross-links to the hosted mathlib4_docs.
- **Phase B — Verso companion**: a guided walk of the proof structure with
  highlighted Lean code and paper↔Lean links in both directions, generated
  from the existing crosswalk + ledger data. A leanblueprint-style dependency
  graph page can be derived from the same ledger.

**Built 2026-07-10 (gq2):** the Verso blueprint uses the official
`leanprover/verso-blueprint` tooling and lives in the **instance repo** as a
`blueprint/` lake project that requires the formalization by path from its
`formalizations/<name>` git submodule. Rationale: isolates the Verso
dependency stack from the (active, swarm-driven) formalization workspace,
makes blueprint builds reproducible against the exact submodule pin the
paper ships with, and scales to multiple formalizations in `formalizations/`
(an independent GPT formalization is expected). The blueprint toolchain must
match the formalization's exactly; `VersoBlueprint` is required at the
matching release branch (`@"v4.31.0"` for a `v4.31.0-rc2` project).
`blueprint/scripts/ci-pages.sh` renders to `blueprint/_out/site/html-multi/`.
Node status (sorry-free vs in-progress) is computed from the Lean
declarations directly. Seed chapter: the presentation theorem + marked
Demushkin normalization; full authoring via the /blueprint skill once the
formalization stabilizes.

**Multiple formalizations** (gq2 has two, on different toolchains): one
docbuild-X + blueprint-X workspace pair per formalization, each pinned to
ITS toolchain with the matching doc-gen4 tag / VersoBlueprint branch (the
template conventions differ across branches — check `ProjectTemplateMain`
and `ci-pages.sh` on the branch you use). Badges carry
`project="<name>"`; docs deploy per-project under `/lean/<name>/`; the
lean-knowls registries are per-project files merged into the UI bundle
(`Object.assign` form). Submodule bumps follow
`skills/update-formalization` — including its doc-trace purge and
lakefile+manifest path rules.

Two gotchas of the split layout:

- `lake update` reconciles `lean-toolchain` to the VersoBlueprint branch's
  (e.g. rc2 → final), which silently breaks the Mathlib cache. Restore the
  formalization's exact toolchain after any `lake update`.
- Chapters live outside the formalization's lib, so each chapter file must
  `import <TheProject>` or its `(lean := "…")` names fail to resolve and
  every node renders as unformalized (the build only warns).

## Provenance: the AI-development record

Three views over the assistant chat logs. The unit of organization is the
**ticket, not the session**: sessions multiplexed several tickets, so raw
session flow is meaningless. A classification pass assigns each interaction
segment to the ticket it served, regardless of which session it ran in.

1. **Timeline view** — ticket-based. Per ticket: goal, its interaction
   segments in order (possibly spanning sessions), and the **model** that did
   the work (Fable vs Opus) visible per segment.
2. **Story view** — curated incidents worth a reader's time: obstacles
   discovered in the paper or in the plans, tickets that had to be split into
   subtickets, dead ends and recoveries. Hand-picked with LLM assistance;
   each incident links into the timeline.
3. **Statistics view** — the scope of the effort: real (wall-clock) time,
   lane-days used, tokens spent, Lean compilation time and run counts;
   per-model breakdowns where attributable.

Trimming rules (before anything is published):

- drop status-check interactions ("what tickets are open", progress queries);
- drop interactions unrelated to the formalization;
- redaction pass (paths, keys, personal noise);
- author review before publish — the same decision-artifact pattern as the
  rest of the framework (proposed segments → author approves/edits → render).

Pipeline sketch: session `.jsonl` transcripts → segment classifier (ticket id,
model, keep/trim) → ticket dossiers (JSON decision artifacts) → author review
→ static HTML render. Data sources to inventory when building: the Claude Code
session transcripts and the Lean swarm's ticket/lane records.

## Publishing mechanics

**Decision (2026-07-10): direct push to a separate public site repo, not
PRs.** The source repos stay private; a public repo (e.g.
`roed-math/gq2-site`) holds only the assembled site and GitHub Pages serves
its `main` branch. Deploys are single commits recording the source SHAs
(paper repo + formalization submodule) for provenance. PRs against the site
repo were considered and rejected: a diff of generated HTML is unreviewable,
so a PR adds ceremony without review value — the real review happens
upstream (validators + the author dashboards), and running `deploy.sh` *is*
the publish decision. If a co-author sign-off gate is ever wanted, the same
script can open a PR instead of pushing; revisit then.

Scripts (templates here; stamped per instance):

- `scripts/build-site.sh` — assemble `output/site/` from the landing page
  (`web-assets/site/index.html`), the PreTeXt web build (`/paper/`), the
  arXiv PDF (`/paper.pdf`), and the blueprint render (`/blueprint/`).
- `scripts/deploy.sh [--dry-run]` — rsync the tree into a shallow clone of
  the site repo, commit with source SHAs, push. One-time GitHub setup:
  create the public repo; Settings → Pages → deploy from `main`, root.

Promote to a GitHub Action once the pieces settle. The PreTeXt publication
file and asset URLs must respect the project-page base path.
