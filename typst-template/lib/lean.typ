// Links from a statement to its formalization.
//
// The PreTeXt backend ships this as a custom `<lean>` element plus an XSL
// template. Here it is a function: a pill-styled anchor into the generated
// doc-gen4 tree in the HTML target, and nothing at all in the PDF (arXiv
// LaTeX drops the badges, same as the PreTeXt `arxiv` target).

#import "config.typ": lean-docs-root, lean-default-project

/// A formalization badge.
///
///   #lean("GQ2.Presentation.main")
///   #lean("Q2Presentation.thm_main", project: "gq2-gpt")
///
/// `project` selects both the docs subtree and the badge colour class, so a
/// paper with two independent formalizations shows which is which.
#let lean(decl, project: none, label: none) = context {
  if target() != "html" { return }
  let proj = if project != none { project } else { lean-default-project }
  let classes = "lean-link" + if proj != "" { " lean-proj-" + proj } else { "" }
  let attrs = (
    class: classes,
    "data-lean-ref": decl,
    title: "Formalized as " + decl,
  )
  if lean-docs-root != "" and proj != "" {
    attrs.insert("href", lean-docs-root + "/" + proj + "/find/?pattern=" + decl + "#doc")
  }
  html.elem("a", attrs: attrs, if label != none { label } else { "Lean" })
}

/// Several badges in a row, e.g. one statement formalized in two projects.
#let lean-badges(..decls) = {
  for d in decls.pos() {
    if type(d) == str { lean(d) } else { lean(..d) }
  }
}
