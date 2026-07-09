# Interactive HTML features (proven)

All three were validated end-to-end in a headless browser during the de-risking
spike. The working assets live in `pretext-template/`. None require forking the
PreTeXt core — they are a custom XSL that *imports* the core plus a client-side
JS/CSS layer injected via the `html.js.extra` / `html.css.extra` params.

## 1. Formalization links — `<lean>`

A custom inline element:

```xml
<lean ref="Gq2.presentation">Gq2.presentation</lean>
```

`xsl/custom-html.xsl` renders it as
`<a class="lean-link" href="{lean_docs_base}/Gq2.presentation.html"
data-lean-ref="Gq2.presentation">`. The `data-lean-ref` is the hook for a future
hover/knowl enhancement. Validated by `validators/lean_links.py`.

Follow-ups: add `<lean>` to the RELAX NG schema (else it fails validation once
`jing` is installed); add a `custom-latex.xsl` template so it renders as a macro
(e.g. `\leanref`) in the PDF instead of bare text.

## 2. Detail tiers — two carriers

- **PDF / default level:** `@component="detail-N"` + a publication `<version
  include="..."/>` physically excludes higher tiers from the print build.
- **HTML interactive:** a `@detail-level="N"` attribute is stamped onto the
  born-hidden knowl's `<details>` (via a one-template `body-css-class` override),
  and `detail-ui.js` mounts a global slider that sets `details.open = (level <=
  threshold)`. Note: `@component` does **not** reach HTML, so the two carriers are
  intentionally separate.

## 3. Notation hovers without knowl underline

A `\notn{key}{symbol}` macro expands (via MathJax `\class`) to a `ptxnotn-<key>`
class on the rendered symbol; `detail-ui.js` shows a small definition popup on
hover/focus, positioned *below* the symbol so it never covers the equation. No
knowl underline. Definitions come from a registry that the real tool should
**generate from the document's notation list**, not hand-maintain.

**Critical timing note:** notation lives inside math, which MathJax typesets
*asynchronously after `DOMContentLoaded`*. Wiring must wait for
`MathJax.startup.promise` (see `afterMathJax` in `detail-ui.js`), or it finds zero
nodes. The slider needs no such wait — its `<details>` are static HTML.

## Integration follow-ups (from the spike)

- Widget placement: appending to `#ptx-masthead` is not visible (fixed layout).
  Spike uses a fixed floating control; production should override the masthead
  template for a real slot.
- Asset copying: `html.*.extra` only emit the tags; the JS/CSS files must be
  copied into the output dir. Needs a proper asset step.
- `custom-html.xsl` imports the core via an absolute path; find the portable
  import path before this is truly reusable across machines/versions.
