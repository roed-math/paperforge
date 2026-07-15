---
name: update-formalization
description: Bump a formalization submodule to a new upstream state and regenerate everything the paper derives from it — crosswalk, census, annotations, docs, knowls, blueprint — with the gotchas that bite pre-listed.
---

# update-formalization

Formalizations are moving targets (requirement 1). This skill is the
checklist for absorbing an upstream change — a cleanup, a rename pass, an
axiom discharge — so the paper tracks it without drift. Everything derived
is regenerated; everything authored is orphan-checked. Distilled from the
gq2-claude 02155b3→91e1918 bump (56 commits, ±40k lines, module splits).

## Procedure

1. **Compare before touching.** In the submodule: `git fetch`, then
   `git log --oneline HEAD..origin/<branch>` and `git diff --stat` — split
   the commits into mechanical cleanup vs semantic changes (axiom statement
   edits, API closures, renames). Diff `lean-toolchain`, `lakefile*`,
   `lake-manifest.json` specifically: a toolchain or Mathlib-pin change
   invalidates every cache downstream.
2. **Snapshot the old derived artifacts** (decl-map, axiom census) to a
   scratch dir — the honest "what changed for the paper" report is a diff of
   regenerated artifacts, not a reading of upstream commit messages.
3. **Update the pin**: `git checkout origin/<branch>` in the submodule.
4. **Reuse build artifacts when possible.** If a sibling clone at the same
   commit has a built `.lake`, APFS-clone it (`cp -Rc`) instead of
   rebuilding (~9G, copy-on-write, minutes). Then `lake build <Lib>` must
   be a fast all-replay — if it compiles things, the clone was stale.
5. **Regenerate the crosswalk**: `lean_declmap.py` (decl-map),
   `lean_axioms.py` (census — usually via build-web). Diff against the
   snapshots: decls gone / new / tags that gained or lost anchors.
6. **Orphan-check the authored sidecars** — these are keyed by decl name
   and silently rot on renames:
   - `crosswalk/lean-annotations.json` (badge labels): author annotations
     for NEW multi-decl entries; stale keys are harmless.
   - `references/formalized-known.json` (decisions): keys must still exist.
   - Beware false orphans from crude greps: apostrophes in names
     (`foo'`), explicitly-dotted declarations, multi-line signatures.
7. **Refresh the atlas export** if the instance uses Lean-derived blueprint
   edges: `lake exe atlas graph-data -o …` in the submodule, copy to
   `crosswalk/atlas-graph.json`. The dep graph silently goes stale
   otherwise.
8. **Rebuild + gate**: `build-web.sh` then the full validator run.
   `lean_links` is the net — every badge must resolve in the new tree.
9. **Rebuild the API docs.** GOTCHA: doc-gen4's facet traces ride along
   with a cloned `.lake` and lake will *replay* the docs step, reporting
   success while writing nothing — module pages keep the OLD tree's layout
   (check mtimes!). Purge before building:
   `docbuild/.lake/build/{doc/<Lib>,api-docs.db,doc-manifest.json}` and
   `doc-data/<Lib>*`. Then `lake build <Lib>:docs`, re-assemble the subset
   (build-leandocs), which refreshes the lean-knowls registry.
10. **Regenerate + rebuild the blueprint** (blueprint_gen + ci-pages).
    Statuses recompute from the new Lean state automatically.
11. **Deploy; commit the bump as ONE logical change** whose message carries
    the comparison (upstream summary + paper-side artifact deltas + gate
    state).

## Standing gotchas (learned the hard way)

- `lake update` in any doc/blueprint workspace REWRITES `lean-toolchain`
  to the dependency's; restore the formalization's exact toolchain or the
  Mathlib cache breaks. Never run it casually after the initial setup.
- The submodule's path is recorded in BOTH each workspace's lakefile AND
  its root `lake-manifest.json` — on a rename, fix both (editing the
  manifest by hand avoids `lake update`).
- Multiple formalizations = one workspace pair (docbuild-X, blueprint-X)
  PER formalization when toolchains differ; they usually do.
- Renames upstream should preserve the docstring paper-tag anchors (the
  ledger discipline); decl-name patterns alone are not stable identity.
- Pin the interpreter: non-interactive shells may resolve a different
  `python3` than the one with the toolchain (conda/homebrew/system split).
  Scripts that spawn subprocesses should lead PATH with
  `Path(sys.executable).parent`.

## Contract

- **Reads:** the submodule (old pin + fetched upstream); the derived
  crosswalk artifacts; the authored sidecars.
- **Writes:** the new pin; regenerated `crosswalk/*` + docs/knowls/
  blueprint outputs; annotation additions for new multi-decl entries.
- **Gate:** `lake build <Lib>` replays clean; `run_all` at baseline;
  doc pages carry NEW mtimes; blueprint renders; deploy provenance
  records the new SHA.
- **Provenance:** one commit per bump, message = the comparison;
  `Generated-by:`/`Co-Authored-By:` trailer as usual.
