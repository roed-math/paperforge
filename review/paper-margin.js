/* paperforge review mode: margin-driven review inside the paper.
   Injected by review_server.py into /paper/*.html. Every pipeline decision
   anchored to a block on this page gets a status-colored MARGIN MARKER at
   that block; clicking it expands an inline decision panel (status buttons,
   autosaving note, link to the full dashboard card). A floating strip shows
   the page's pending count with prev/next navigation — so a straight
   readthrough of the paper doubles as the review pass. */
(function () {
  "use strict";

  const COLORS = {
    "proposed": "#b45309", "needs-discussion": "#7c3aed", "?": "#b45309",
    "author-approved": "#15803d", "author-rejected": "#b91c1c",
    "needs-citation": "#b45309", "cited-nearby": "#15803d",
    "common-knowledge": "#15803d",
  };
  const PENDING = new Set(["proposed", "needs-discussion", "needs-citation", "?"]);
  const isPending = it =>
    PENDING.has(it.status) ||
    (it.artifact === "disambig" && false);   // sense decisions count as done

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }

  async function decide(payload) {
    const r = await fetch("/api/decide", { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload) });
    return r.ok;
  }

  /* claim-LaTeX -> displayable html (math via the page's own MathJax) */
  function esc(s) { return (s || "").replace(/&/g, "&amp;")
    .replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
  function latexPreview(src) {
    let h = esc(src);
    h = h.replace(/\\cite(?:\[([^\]]*)\])?\{([^}]*)\}/g, (m0, pin, keys) =>
      "[" + keys.split(",").map(k => k.trim()).join(", ")
          + (pin ? ", " + pin : "") + "]");
    h = h.replace(/\\(?:[cC]ref|ref|eqref)\{([^}]*)\}/g,
                  '<span class="pfm-ref">$1</span>');
    h = h.replace(/\$([^$]+)\$/g, "\\($1\\)");
    h = h.replace(/\\emph\{([^}]*)\}/g, "<em>$1</em>")
         .replace(/\\texttt\{([^}]*)\}/g,
                  (m0, c) => "<code>" + c.replace(/\\_/g, "_") + "</code>");
    return h.replace(/---/g, "—").replace(/--/g, "–");
  }

  ready(async function () {
    const page = location.pathname.split("/").pop();
    let items;
    try {
      items = await (await fetch(
        `/api/margin?page=${encodeURIComponent(page)}`)).json();
    } catch (e) { return; }
    if (!Array.isArray(items) || !items.length) return;

    const css = el("style");
    css.textContent = `
      .pfm-marker { position:absolute; right:-10.5rem; width:9.5rem;
        font:11px -apple-system,sans-serif; padding:.18rem .5rem;
        border-radius:6px; border:1px solid; background:#fff; cursor:pointer;
        overflow:hidden; text-overflow:ellipsis; white-space:nowrap;
        opacity:.92; z-index:800 }
      @media (max-width: 1250px) {
        .pfm-marker { position:static; display:inline-block; width:auto;
          max-width:100%; margin:.2rem .3rem .2rem 0 } }
      .pfm-host { position:relative }
      .pfm-panel { border-left:3px solid; background:#fafafa; color:#16181d;
        margin:.6rem 0; padding:.6rem .8rem; border-radius:0 8px 8px 0;
        font:14px -apple-system,sans-serif }
      .pfm-panel .pfm-stmt { font-size:.92rem; margin:.25rem 0 .45rem }
      .pfm-panel .pfm-sum { color:#5c6470; font-size:.8rem; margin:.15rem 0 }
      .pfm-row { display:flex; gap:.35rem; flex-wrap:wrap; align-items:center;
        margin-top:.45rem }
      .pfm-row button { border:1px solid #d8dce3; background:#fff;
        color:#16181d; border-radius:6px; padding:.2rem .55rem;
        cursor:pointer; font-size:.8rem }
      .pfm-row button.sel { font-weight:700; border-width:2px }
      .pfm-note { flex:1; min-width:10rem; padding:.25rem .45rem;
        font:inherit; font-size:.8rem; border:1px solid #d8dce3;
        border-radius:6px }
      .pfm-saved { color:#15803d; font-size:.78rem; opacity:0;
        transition:opacity .25s }
      .pfm-saved.show { opacity:1 }
      .pfm-q { width:1.5rem; border-radius:999px !important; font-weight:700;
        color:#5c6470 }
      .pfm-q.open { border-color:#2563eb; color:#2563eb }
      .pfm-help { background:rgba(128,128,128,.08); border-radius:6px;
        padding:.45rem .6rem; margin-top:.4rem; font-size:.8rem;
        line-height:1.45 }
      .pfm-help-row { margin:.15rem 0 }
      .pfm-help-row b { font-weight:700 }
      .pfm-ref { color:#2563eb; border-bottom:1px dotted #2563eb }
      .pfm-strip { position:fixed; bottom:1rem; left:1rem; z-index:1100;
        display:flex; gap:.5rem; align-items:center; background:#fff;
        color:#16181d; border:1px solid #d8dce3; border-radius:8px;
        box-shadow:0 4px 14px rgba(0,0,0,.18); padding:.4rem .7rem;
        font:13px -apple-system,sans-serif }
      .pfm-strip button { border:1px solid #d8dce3; background:#fff;
        border-radius:6px; cursor:pointer; padding:.15rem .5rem }
      .pfm-strip a { color:#2563eb; text-decoration:none; font-size:.85rem }
      @media (prefers-color-scheme: dark) {
        .pfm-marker, .pfm-panel, .pfm-strip, .pfm-row button, .pfm-note,
        .pfm-strip button { background:#1d2026; color:#e7e9ee;
          border-color:#33383f } }`;
    document.head.appendChild(css);

    const markers = [];
    for (const it of items) {
      for (const tag of it.anchors) {
        const host = document.getElementById(tag);
        if (!host) continue;
        host.classList.add("pfm-host");
        const stack = host.querySelectorAll(":scope > .pfm-marker").length;
        const color = COLORS[it.status] || "#5c6470";
        const m = el("span", "pfm-marker",
                     `${it.status} · ${it.title}`);
        m.style.borderColor = color; m.style.color = color;
        m.style.top = (stack * 1.7) + "rem";
        m.title = `${it.artifact_label}: ${it.title} — click to decide here`;
        let panel = null;
        m.onclick = () => {
          if (panel) { panel.remove(); panel = null; return; }
          panel = buildPanel(it, m, color);
          if (getComputedStyle(m).position !== "absolute") {
            // inline layout (<1250px): the marker sits in the text flow at
            // the END of its host element — the panel must open at the
            // marker, not pages away at the division heading
            m.insertAdjacentElement("afterend", panel);
          } else {
            // margin layout: block-level anchors put the panel right after
            // the block; division-level anchors (whole sections) right
            // after the division heading, where the marker is shown — not
            // after the entire division
            const isDivision = /^(SECTION|ARTICLE)$/.test(host.tagName)
              && host.querySelector(":scope > h1, :scope > h2, :scope > h3");
            if (isDivision && host.children.length > 3) {
              const head = host.querySelector(":scope > h1, :scope > h2, :scope > h3");
              head.insertAdjacentElement("afterend", panel);
            } else {
              host.insertAdjacentElement("afterend", panel);
            }
          }
          panel.scrollIntoView({ block: "nearest" });
          if (window.MathJax && MathJax.typesetPromise)
            MathJax.typesetPromise([panel]).catch(() => {});
        };
        markers.push({ marker: m, item: it });
        host.appendChild(m);
      }
    }
    if (!markers.length) return;

    function buildPanel(it, marker, color) {
      const p = el("div", "pfm-panel");
      p.style.borderColor = color;
      p.appendChild(el("b", null,
        `${it.artifact_label} — ${it.title}`));
      if (it.text) {
        const s = el("div", "pfm-stmt");
        s.innerHTML = latexPreview(it.text);
        p.appendChild(s);
      }
      if (it.summary) p.appendChild(el("div", "pfm-sum", it.summary));
      const row = el("div", "pfm-row");
      for (const c of it.choices) {
        const b = el("button", null, c);
        if (c === it.status) b.classList.add("sel");
        if (it.choice_help && it.choice_help[c]) b.title = it.choice_help[c];
        b.onclick = async () => {
          if (!await decide({ artifact: it.artifact, id: it.id, status: c }))
            return;
          it.status = c;
          row.querySelectorAll("button:not(.pfm-q)").forEach(x =>
            x.classList.remove("sel"));
          b.classList.add("sel");
          const nc = COLORS[c] || "#5c6470";
          marker.style.borderColor = nc; marker.style.color = nc;
          marker.textContent = `${c} · ${it.title}`;
          p.style.borderColor = nc;
          flash(p);
          updateStrip();
        };
        row.appendChild(b);
      }
      // knowl-style legend: a ? on the choice row expands, in place, what
      // each option means (title tooltips alone are too easy to miss)
      const helps = it.choices.filter(c => it.choice_help &&
                                           it.choice_help[c]);
      if (helps.length) {
        const q = el("button", "pfm-q", "?");
        q.title = "what do these options mean?";
        let legend = null;
        q.onclick = () => {
          if (legend) { legend.remove(); legend = null;
                        q.classList.remove("open"); return; }
          legend = el("div", "pfm-help");
          for (const c of helps) {
            const d = el("div", "pfm-help-row");
            d.appendChild(el("b", null, c));
            d.appendChild(el("span", null, " — " + it.choice_help[c]));
            legend.appendChild(d);
          }
          row.insertAdjacentElement("afterend", legend);
          q.classList.add("open");
        };
        row.appendChild(q);
      }
      p.appendChild(row);
      const nrow = el("div", "pfm-row");
      const note = el("input", "pfm-note");
      note.placeholder = "note to the pipeline (autosaves)";
      note.value = it.note || "";
      let t = null;
      const save = async () => {
        if (await decide({ artifact: it.artifact, id: it.id,
                           note: note.value })) { it.note = note.value; flash(p); }
      };
      note.addEventListener("input", () => {
        clearTimeout(t); t = setTimeout(save, 700); });
      note.addEventListener("blur", () => { clearTimeout(t); save(); });
      const saved = el("span", "pfm-saved", "saved ✓");
      const full = el("a", null, "full details ↗");
      full.href = `/review#${it.artifact}/${encodeURIComponent(it.id)}`;
      full.target = "review";
      full.style.cssText = "font-size:.78rem;color:#2563eb;text-decoration:none";
      nrow.appendChild(note); nrow.appendChild(saved); nrow.appendChild(full);
      p.appendChild(nrow);
      return p;
    }
    function flash(p) {
      const s = p.querySelector(".pfm-saved");
      s.classList.add("show");
      setTimeout(() => s.classList.remove("show"), 1000);
    }

    /* floating strip: pending count + prev/next navigation */
    const strip = el("div", "pfm-strip");
    const label = el("span");
    const prev = el("button", null, "↑");
    const next = el("button", null, "↓");
    const dash = el("a", null, "dashboard ↗");
    dash.href = "/review"; dash.target = "review";
    strip.append(prev, label, next, dash);
    document.body.appendChild(strip);
    let cursor = -1;
    function pendings() {
      return markers.filter(m => PENDING.has(m.item.status));
    }
    function updateStrip() {
      const pend = pendings();
      label.textContent =
        `${pend.length} pending / ${markers.length} decisions on this page`;
    }
    function go(dir) {
      const pend = pendings();
      if (!pend.length) return;
      cursor = (cursor + dir + pend.length) % pend.length;
      const m = pend[cursor].marker;
      m.scrollIntoView({ block: "center", behavior: "smooth" });
      m.style.outline = "2px solid #2563eb";
      setTimeout(() => { m.style.outline = ""; }, 900);
    }
    prev.onclick = () => go(-1);
    next.onclick = () => go(1);
    updateStrip();
  });
})();
