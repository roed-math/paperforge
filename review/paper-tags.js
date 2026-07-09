/* paperforge review mode: tag discovery inside the served paper.
   Injected by review_server.py into /paper/*.html (the standalone build is
   untouched). Every element whose id is a crosswalk tag gets a hover badge
   showing its \cref{...} form; clicking copies it to the clipboard, ready to
   paste into a claim statement, directive, or note. */
(function () {
  "use strict";

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  ready(async function () {
    let tags;
    try {
      tags = await (await fetch("/api/tags")).json();
    } catch (e) { return; }

    // tag -> label (the LaTeX-side name; falls back to the tag itself, which
    // \cref also accepts — claim_inline validates both)
    const byTag = {};
    for (const [key, rec] of Object.entries(tags)) {
      if (key === rec.tag) byTag[key] = rec;
    }
    for (const [key, rec] of Object.entries(tags)) {
      if (key !== rec.tag) byTag[rec.tag].label = key;
    }

    const css = document.createElement("style");
    css.textContent = `
      .ptx-tagbadge { position:absolute; top:-1.5rem; right:0; z-index:900;
        font:11px ui-monospace,monospace; padding:.1rem .45rem;
        border:1px solid rgba(37,99,235,.5); border-radius:999px;
        background:rgba(37,99,235,.06); color:#2563eb; cursor:copy;
        opacity:0; transition:opacity .12s; user-select:none;
        white-space:nowrap }
      .ptx-tagged { position:relative }
      .ptx-tagged:hover > .ptx-tagbadge { opacity:1 }
      .ptx-tagbadge.copied { background:#15803d; color:#fff;
        border-color:#15803d; opacity:1 }`;
    document.head.appendChild(css);

    let n = 0;
    for (const [tag, rec] of Object.entries(byTag)) {
      const el = document.getElementById(tag);
      if (!el) continue;
      const name = rec.label || tag;
      const badge = document.createElement("span");
      badge.className = "ptx-tagbadge";
      badge.textContent = "\\cref{" + name + "}";
      badge.title = `${rec.kind} ${rec.number} — click to copy for a claim ` +
                    `statement or directive`;
      badge.addEventListener("click", async (ev) => {
        ev.stopPropagation(); ev.preventDefault();
        try { await navigator.clipboard.writeText("\\cref{" + name + "}"); }
        catch (e) { /* clipboard may be unavailable; badge still shows text */ }
        badge.classList.add("copied");
        const old = badge.textContent;
        badge.textContent = "copied ✓";
        setTimeout(() => { badge.classList.remove("copied");
                           badge.textContent = old; }, 900);
      });
      el.classList.add("ptx-tagged");
      el.appendChild(badge);
      n++;
    }
  });
})();
