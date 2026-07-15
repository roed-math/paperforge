# PaperForge visual identity

A dog-eared page over a plain, ruler-drawn anvil, its last line closed with a
QED square (`∎`). Ink is the paper template's `#111111`; ember is `#EA580C`
(`#F97316` on dark grounds), used only on the page fold.

Presentation / rationale: the mark survives grayscale print, degrades to the
anvil glyph below 20 px, and every "built with" form links back to this repo.

## Files

| file | use |
|---|---|
| `paperforge-mark.svg` | primary mark, light backgrounds |
| `paperforge-mark-dark.svg` | mark for dark backgrounds |
| `paperforge-mark-mono.svg` | one-color mark; inherits `currentColor`, fold becomes a punched notch |
| `paperforge-logo.svg` | horizontal lockup with wordmark (serif system stack, `textLength`-pinned) |
| `paperforge-icon.svg` / `paperforge-icon-512.png` | GitHub avatar / social preview |
| `paperforge-glyph.svg` | anvil-only glyph for ≤20 px (favicon, badge icon) |
| `paperforge-badge.svg` | "built with PaperForge" badge, 162×20, shields-style |
| `paperforge.tex` | TikZ mark + `\PaperForgeColophon` for LaTeX/arXiv — no image files needed |

## Attaching to a paper

**README of an instance repo** (or any markdown):

```markdown
[![built with PaperForge](https://raw.githubusercontent.com/roed-math/paperforge/main/assets/paperforge-badge.svg)](https://github.com/roed-math/paperforge)
```

**arXiv / print PDF** — copy `paperforge.tex` into the instance (a `paper-init`
job), then:

```latex
\usepackage{tikz}      % preamble
\input{paperforge.tex}
...
\PaperForgeColophon    % end of paper: mark + "Built with PaperForge", hyperlinked
```

For a grayscale print run: `\colorlet{pfink}{black}\colorlet{pfember}{black!45}`.
The mark alone is `\PaperForgeMark[<height>]` (default 1em, baseline-aligned).

**HTML paper footer** (PreTeXt web output):

```html
<a href="https://github.com/roed-math/paperforge">
  <img src="paperforge-badge.svg" alt="built with PaperForge" height="20">
</a>
```

**Dark-mode-aware embed** (GitHub READMEs):

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/paperforge-mark-dark.svg">
  <img src="assets/paperforge-mark.svg" alt="PaperForge" width="120">
</picture>
```

## Anatomy

- **Page** — dog-eared sheet, ember fold: the PreTeXt source being worked. Its
  last text line ends in a punched-out QED square.
- **Anvil** — the toolchain, straight lines only: a slab, a wedge of a horn,
  one trapezoid.
- **The two squares** — the page's QED tombstone and the anvil's hardy hole
  (the real square socket in an anvil's heel): a socket exactly the shape of a
  finished proof.

All geometry is hand-drawn vector on a 100×100 grid, holes punched with
`fill-rule="evenodd"` so every variant works on any background. The TikZ
version mirrors the same coordinates.
