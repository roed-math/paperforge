---
name: ingest-draft
description: Convert the AI-written LaTeX draft into PreTeXt source using the deterministic tex2ptx engine, then review its warnings and fix judgment cases.
---

# ingest-draft

Turns `inputs.ai_draft` (LaTeX) into PreTeXt `source/`. **Script-first**: the
deterministic converter does the mechanical conversion; Claude handles only the
residue. This matters because drafts are moving targets — re-ingestion must be
cheap, reproducible, and produce stable tags. Never hand-convert what the script
can do; improve the script instead (the improvement ports to every future paper).

## Procedure

1. Run the engine (one parse, two outputs):

       python3 <paperforge>/ingest/tex2ptx.py <draft.tex> \
           --out source/ --numbering crosswalk/numbering-current.json \
           --snapshot current

2. `xmllint --noout source/*.ptx`, then `pretext build web` must succeed.
3. **Validate the numbering simulation** the first time (and after big draft
   changes): compile the draft with pdflatex and diff the simulator against the
   `.aux` (`\newlabel` entries are ground truth). The gq2 paper validated
   300/300; a new paper's conventions (per-section equations, unshared counters)
   may need simulator tweaks in `Numbering`.
4. Triage the converter's warnings — these are the judgment cases for Claude:
   - `unlabeled <env>` / `unlabeled equation` — drift hazards. Add a `\label`
     upstream in the draft if possible; otherwise assign a semantic tag.
   - `unhandled macro in prose` — extend `convert_inline` (preferred) or fix by
     hand if truly one-off.
   - stray labels, tables (`@forge: verify table conversion` comments).
5. Re-run and confirm idempotency: a second run over the same draft must
   produce an identical tree (`git diff --stat` clean).

## What the engine guarantees

- Structure: sections/subsections (appendices → `<backmatter>`), theorem-like
  envs with shared-counter semantics, proofs reparented inside statements,
  display math inside `<p>`, bibliography → `<references>` in backmatter.
- Tags: xml:id = LaTeX label with `:` → `-`; these are the stable identity every
  other tool (crosswalk, lean ledgers, `<lean>` links, directives) keys on.
- Numbering map: tag → printed number for this snapshot, for the crosswalk.

## What Claude must NOT do here

- Do not invent mathematical content — gaps (bridging text, summaries) belong
  to later skills.
- Do not rename tags on re-ingestion; tag stability is the contract.

## Contract

- **Reads:** `inputs.ai_draft` (paper.toml) plus the sidecars merged at ingest
  (`notation/notation-map.json`, `notation/disambiguation.json`,
  `references/extra-biblio.xml`, `content/insertions/`).
- **Writes:** `source/*.ptx` and `crosswalk/numbering-<snapshot>.json` — via the
  deterministic engine only.
- **Gate:** `xmllint --noout source/*.ptx`; `pretext build web`; a second run is
  diff-clean (idempotency); `python -m paperforge_validators.run_all` introduces
  no new errors.
- **Provenance:** engine output is deterministic (no stamp). Judgment fixes for
  converter warnings are separate commits with a `Generated-by: <model-id>`
  trailer.
