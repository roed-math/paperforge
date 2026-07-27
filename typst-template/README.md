# Typst backend (experimental)

An alternative to `pretext-template/`: the same paper, authored once in Typst,
built to an interactive HTML page **and** to a PDF per detail level.

    scripts/build.sh example/paper.typ output 1 2 3

Requires Typst 0.15+ (HTML export is behind `--features html`).

## Why

The detail-tier requirement is the reason. In the PreTeXt backend a tier needs
two independent carriers — a `@component` that excludes it from the PDF at build
time and a `@detail-level` attribute on a born-hidden knowl for the HTML slider —
because `@component` never reaches the HTML. In Typst one authored call

```typst
#detail(2)[The counting argument produces a surjection ...]
```

is a compile-time conditional in the paged target and a
`<details data-detail-level="2">` in the HTML target, from the same source.

Math needs no MathJax: Typst emits MathML and the browser lays it out.

## Layout

| path | what |
|---|---|
| `lib/paperforge.typ` | umbrella import + the `paper()` template |
| `lib/config.typ` | `--input` knobs (`detail`, `html-detail`, `lean-docs`, …) |
| `lib/detail.typ` | `#detail`, `#detail-inline`, `#detail-upto` |
| `lib/theorems.typ` | shared-counter statements, `#proof`, `show ref` |
| `lib/lean.typ` | formalization badges |
| `lib/notation.typ` | notation hover markers + registry |
| `lib/mathcompat.typ` | shims for constructs MathML export misses |
| `web-assets/` | the HTML book chrome (CSS + JS, no dependencies) |
| `scripts/postprocess.py` | lifts asset tags into `<head>` |
| `scripts/build.sh` | HTML once, PDF per tier |

See `docs/TYPST-BACKEND.md` for the feature-by-feature comparison with the
PreTeXt backend, the verified gaps, and the traps worth knowing.
