// paperforge — Typst backend.
//
// One authored source, two targets:
//   typst compile paper.typ --input detail=2 paper.pdf
//   typst compile paper.typ --format html --features html --input detail=1 paper.html
//
// Import everything from here:
//   #import "@local/paperforge:0.1.0": *      (or a relative path)
//   #show: paper.with(title: [...], authors: (..))

// NB: a Typst import list does not continue across a line break — a wrapped
// list silently drops everything after the first line. Use `*` re-exports.
#import "config.typ": *
#import "detail.typ": *
#import "theorems.typ": *
#import "lean.typ": *
#import "notation.typ": *
#import "mathcompat.typ": *

// Strip markup for metadata fields (document title/author take strings).
#let to-plain(c) = {
  if type(c) == str { return c }
  if c.has("text") { return c.text }
  if c.has("children") { return c.children.map(to-plain).join("") }
  if c.has("body") { return to-plain(c.body) }
  " "
}

// ---------------------------------------------------------------------------
// Equations
// ---------------------------------------------------------------------------

// Typst's HTML export emits `<math display="block">` but does NOT render the
// equation number (the reference resolves to "Equation 3" while the equation
// itself shows nothing). Wrap block equations in a grid that carries the number
// on the right, matching the paged output.
#let _equation-rules(doc) = {
  show math.equation.where(block: true): it => context {
    if target() != "html" { return it }
    let num = if it.numbering != none {
      numbering(it.numbering, ..counter(math.equation).at(it.location()))
    } else { none }
    html.elem("div", attrs: (class: "pf-eq" + if num == none { " pf-eq-unnumbered" } else { "" }), {
      html.elem("div", attrs: (class: "pf-eq-body"), it)
      if num != none {
        html.elem("div", attrs: (class: "pf-eq-num"), num)
      }
    })
  }
  // Equation references print as "(4)", not "Equation 4" — the `\eqref`
  // convention every mathematics paper uses. A range then reads "(4)–(6)"
  // instead of "Equation 4–Equation 6".
  show ref: it => {
    let el = it.element
    if el != none and el.func() == math.equation and it.supplement == auto {
      link(el.location(), context {
        let n = counter(math.equation).at(el.location())
        if el.numbering != none { numbering(el.numbering, ..n) } else { it }
      })
    } else { it }
  }

  doc
}

// ---------------------------------------------------------------------------
// HTML chrome
// ---------------------------------------------------------------------------

#let _html-head(title, css, js) = {
  // Typst 0.15 has no way to write into the real <head>; these land at the top
  // of <body>, and `scripts/postprocess.py` lifts them. Emitting them here (as
  // opposed to only in the post-processor) keeps the asset list in the source.
  html.elem("template", attrs: (id: "pf-head-assets"), {
    for href in css {
      html.elem("link", attrs: (rel: "stylesheet", href: href))
    }
    for src in js {
      html.elem("script", attrs: (src: src, defer: "defer"))
    }
  })
}

#let _html-frontmatter(title, authors, abstract, date) = {
  html.elem("header", attrs: (class: "pf-titleblock"), {
    html.elem("h1", attrs: (class: "pf-title"), title)
    if authors.len() > 0 {
      html.elem("div", attrs: (class: "pf-authors"), {
        for (i, a) in authors.enumerate() {
          html.elem("span", attrs: (class: "pf-author"), {
            a.name
            if "affiliation" in a {
              html.elem("span", attrs: (class: "pf-affiliation"), a.affiliation)
            }
          })
        }
      })
    }
    if date != none {
      html.elem("div", attrs: (class: "pf-date"), date)
    }
    if abstract != none {
      html.elem("section", attrs: (class: "pf-abstract"), {
        html.elem("h2", attrs: (class: "pf-abstract-head"), "Abstract")
        abstract
      })
    }
  })
}

// ---------------------------------------------------------------------------
// The template
// ---------------------------------------------------------------------------

/// Document template. Apply with `#show: paper.with(..)`.
///
/// - title, authors, abstract, date: front matter. `authors` is an array of
///   dictionaries with `name` and optionally `affiliation`.
/// - css, js: asset paths for the HTML target (lifted into `<head>`).
/// - paper-size, font, font-size: paged-target layout.
#let paper(
  title: [Untitled],
  authors: (),
  abstract: none,
  date: none,
  css: ("paper.css",),
  js: ("paper.js",),
  paper-size: "us-letter",
  font: ("New Computer Modern",),
  font-size: 10.5pt,
  body,
) = {
  set document(title: to-plain(title), author: authors.map(a => to-plain(a.name)))
  set heading(numbering: "1.1")
  set math.equation(numbering: "(1)")
  set par(justify: true)
  set text(font: font, size: font-size)

  show: statement-rules
  show: _equation-rules

  // Reset the shared statement counter at each section.
  show heading.where(level: 1): it => { thm-counter.update(0); it }

  context if target() == "html" {
    _html-head(title, css, js)
    html.elem("div", attrs: (class: "pf-app"), {
      html.elem("aside", attrs: (class: "pf-sidebar"), {
        html.elem("nav", attrs: (class: "pf-toc", "aria-label": "Table of contents"), {
          html.elem("div", attrs: (class: "pf-toc-head"), "Contents")
          outline(title: none, depth: 3)
        })
      })
      html.elem("main", attrs: (class: "pf-main"), {
        _html-frontmatter(title, authors, abstract, date)
        html.elem("article", attrs: (class: "pf-content"), body)
      })
    })
  } else {
    set page(paper: paper-size, margin: (x: 1.5in, y: 1.2in), numbering: "1")
    align(center, {
      block(text(size: 1.6em, weight: "bold", title))
      v(0.6em)
      for a in authors {
        block(spacing: 0.5em, {
          text(size: 1.05em, a.name)
          if "affiliation" in a {
            linebreak()
            text(size: 0.85em, style: "italic", a.affiliation)
          }
        })
      }
      if date != none { v(0.4em); text(size: 0.9em, date) }
    })
    v(1em)
    if abstract != none {
      block(width: 100%, inset: (x: 2em), {
        align(center, text(weight: "bold", size: 0.9em, "Abstract"))
        v(0.3em)
        text(size: 0.95em, abstract)
      })
      v(1.2em)
    }
    body
  }
}
