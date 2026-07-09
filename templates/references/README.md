# References

Local PDF copies of every cited work go here, plus the `.bib` (path in
`paper.toml`). Used by:

- `validators/references.py` (stage 1) — checks that specific pins ("[Author, Thm
  3.2]") actually resolve in the cited PDF.
- `validators/plagiarism.py` — these PDFs are plagiarism *sources*: generated prose
  must not overlap them verbatim.

Stage 2 of the reference check is a manual human double-check — the validator only
narrows what you must read. Do not commit copyrighted PDFs to a public repo; keep
this directory git-ignored in the instance.
