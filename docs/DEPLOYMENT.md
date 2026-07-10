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

A local `deploy.sh` first (build → assemble the site tree → push the Pages
branch); promote to a GitHub Action once the pieces settle. The PreTeXt
publication file and asset URLs must respect the project-page base path.
