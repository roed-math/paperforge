# Notation as a single source of truth

The `\notn{key}{symbol}` macro (defined in `source/main.ptx`'s `<macros>`) is the
one place notation is tagged. From a single `<notation>` list in the document,
three things are (or should be) derived:

1. the printed **List of Notation** (PreTeXt native),
2. the HTML **hover definitions** (the registry `web-assets/detail-ui.js` consumes —
   TODO: generate this instead of hand-writing it),
3. the **`notation_order` validator**'s definition/use positions.

Keeping one source avoids the classic failure of a symbol defined in three places
with drifting meanings. When you add notation, add a `<notation>` entry and use
`\notn` at every occurrence.
