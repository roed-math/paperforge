# The paper view as the editor (design)

Status: design note, 2026-07-12. The review process has grown into a
specialized editor; this note reorients the tooling around that fact. The
**paper view is the primary surface**; the dashboard demotes to a project
drawer for things that are inherently list-shaped.

## What already lives in the paper view

Injected at serve time by the review server, today:

- **Decisions**: every artifact type's margin markers + in-place panels
  (status buttons with knowl-style option legends, autosaving notes,
  deep link to the dashboard card).
- **Marks**: the pen palette — notation / notation-remove / terminology /
  background / reference / detail-high / detail-low — with idempotent
  add/remove.
- **Tag discovery**: hover badges with `\cref`-ready copy.
- **Reader instruments** (also in the deployed paper): knowls, notation
  links with defsite affordances, section-summary popups, the detail
  slider with manual memory, the notation-links toggle.

Dashboard-only today: the Pipeline tab (agent dispatch, job logs,
validator runs, progress), bulk per-artifact card lists, the claim
statement editor with live LaTeX preview, the bibliography picker.

## What moves into the paper view

1. **The floating strip becomes the cockpit.** It already shows pending
   counts and prev/next. Add: a validator badge (green `0` / red `N`,
   click = last run's tail, button = run now), a dispatch control ("send
   the N open marks of mode X to <agent>" — agents.toml enumerates the
   choices), and a running-jobs chip with the live log behind a click.
   All of this is API-complete on the server already; it is strip UI work.
2. **Statement editing in the margin panels.** The dashboard's inline
   LaTeX editor + preview for novelty claims/followups mounts in the
   margin panel (the paper page typesets previews *better* — the paper's
   macros are already loaded). The bib picker mounts on demand inside the
   panel for claims carrying `new_refs`.
3. **What stays in the dashboard**: bulk triage across the whole paper,
   artifact-wide tables, job history, and anything else that is a list
   rather than a location.

## Manual editing (the LLM-assisted part)

The architectural constraint that shapes everything: **`source/*.ptx` is
generated and must never be hand-edited.** The durable substrate is the
draft LaTeX (`inputs/draft/*.tex`) plus the survives-reingestion content
layer (`content/insertions/*.ptx`) plus the maps. A paper-view editor
therefore never writes PreTeXt; it writes to the substrate and re-ingests.
"Translate the user's LaTeX into changes to the underlying PreTeXt" is,
precisely, "translate into changes to the *inputs that generate* the
PreTeXt" — which is what keeps idempotent re-ingestion, tag stability,
numbering simulation, and the plagiarism provenance story intact.

Three lanes, by increasing power:

### Lane 1 — deterministic in-block edits (no LLM)

Click "edit" on a paragraph/statement in review mode → the server returns
the block's **draft LaTeX slice** → the author edits LaTeX in an inline
editor → save splices the slice back into the draft, re-ingests, rebuilds.

Mechanism: tex2ptx emits a **source map** during ingest (block tag →
draft byte-span; the converter already walks the draft linearly, so spans
fall out of the existing parse — they must be computed against the
*uncommented original*, so `strip_comments` needs an offset map). For
content owned by an insertion fragment, the slice comes from the fragment
file instead — same UX, different write target. Staleness is detected by
hashing the slice at extract time.

UX affordance: optimistic preview — typeset the edited LaTeX client-side
immediately (the page's MathJax with the paper's macros), while the real
rebuild runs as a background job in the existing jobs machinery; swap the
block in when it lands. Rebuild-then-reload is ~40 s for the single-page
build; the optimistic preview hides nearly all of it.

### Lane 2 — structural edits (LLM briefed, deterministic gates)

New lemma, new labeled equation, splitting/moving content, changes that
touch numbering or cross-references. A blind splice cannot guarantee tag
stability, so these dispatch the configured headless agent (the
agents.toml machinery) with a precise briefing: the author's typed LaTeX,
the target anchor, and the invariants (stable xml:ids, numbering-drift
check, validator gate, one commit). The job shows in the strip; the
author reviews the rebuilt page and the git diff.

### Lane 3 — intent edits (no LaTeX typed)

Already shipped: mark a spot with a pen + note ("too terse", "needs
background", "rewrite this claim") and dispatch. The agent writes; the
validators and the author's review gate.

### Provenance

Lane-1 edits are the author's own words landing in the draft — the
plagiarism validator's baseline — and commit with the author as author.
Lane-2/3 commits carry `Generated-by:` as everywhere else. Nothing in any
lane bypasses validators.

## Build order

1. Strip cockpit (validators badge, dispatch, jobs) — small, API exists.
2. Margin statement editors + bib picker mount — small.
3. Source map in tex2ptx + `/api/edit` + inline editor — the real build,
   and the piece that makes "paper view = editor" true.
4. Lane-2 briefings ("apply this LaTeX at this anchor") — mostly prompt
   engineering on the dispatch layer.
