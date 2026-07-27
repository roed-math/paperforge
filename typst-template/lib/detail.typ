// Detail tiers — the feature that motivated the Typst backend.
//
// PreTeXt needs TWO carriers for this (a `@component` for build-time exclusion
// from the PDF, plus a `@detail-level` attribute on a born-hidden knowl for the
// HTML slider), because `@component` never reaches the HTML. Typst needs one:
// the same `#detail(..)` call is a compile-time conditional in the paged target
// and a `<details data-detail-level>` element in the HTML target.
//
//   #detail(2)[The cocycle is the one from Lemma 3.4, transported along ...]
//
//   PDF   built with `--input detail=1` : absent
//         built with `--input detail=3` : present, inline, unmarked
//   HTML  always emitted; the reader's slider opens or collapses it.

#import "config.typ": detail-level, html-detail-default, draft

/// Human-readable name for a tier, used as the `<summary>` when the author does
/// not supply one.
#let tier-names = (
  "1": "details",
  "2": "more detail",
  "3": "full detail",
  "4": "computation",
)

#let _summary-for(level, summary) = {
  if summary != none { summary } else {
    tier-names.at(str(level), default: "details")
  }
}

/// A block of supplementary detail at `level`.
///
/// - level: 1 = expected in a normal read, higher = progressively more.
/// - summary: the `<summary>` text in HTML (ignored in PDF).
/// - open: force the HTML disclosure open regardless of the slider default.
#let detail(level, body, summary: none, open: auto) = context {
  if target() == "html" {
    let is-open = if open == auto { level <= html-detail-default } else { open }
    let attrs = (
      class: "pf-detail",
      "data-detail-level": str(level),
    )
    if is-open { attrs.insert("open", "open") }
    html.elem("details", attrs: attrs, {
      html.elem("summary", attrs: (class: "pf-detail-summary"),
        _summary-for(level, summary))
      html.elem("div", attrs: (class: "pf-detail-body"), body)
    })
  } else if level <= detail-level {
    if draft {
      block(
        width: 100%,
        stroke: (left: 1.5pt + rgb("#c0c0c0")),
        inset: (left: 8pt, y: 2pt),
        body,
      )
    } else { body }
  }
}

/// Inline detail: a phrase, clause or parenthetical rather than a block.
/// Renders as a `<span>` in HTML (an inline disclosure would break the
/// paragraph), toggled by the same slider.
#let detail-inline(level, body) = context {
  if target() == "html" {
    html.elem("span", attrs: (
      class: "pf-detail-inline",
      "data-detail-level": str(level),
    ), body)
  } else if level <= detail-level {
    body
  }
}

/// The complement: content that appears ONLY below a level — a one-line
/// summary that a reader who has expanded the full argument no longer needs.
/// In HTML it is tagged so the slider can retire it as the detail rises.
#let detail-upto(level, body) = context {
  if target() == "html" {
    html.elem("span", attrs: (
      class: "pf-detail-upto",
      "data-detail-upto": str(level),
    ), body)
  } else if detail-level <= level {
    body
  }
}
