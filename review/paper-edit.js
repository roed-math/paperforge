/* paperforge review mode: lane-1 manual editing (docs/EDITOR.md).
   For every statement/proof the tex2ptx source map covers, an ✎ button
   opens the block's DRAFT LaTeX in an editor panel. Saving splices the
   edit back into the draft and starts a rebuild+validate job; structural
   edits (labels, environments, sectioning) are deflected to lane 2 —
   dispatch to the configured agent with the typed LaTeX as briefing. */
(function () {
  "use strict";

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

  ready(async function () {
    let map, paras;
    try {
      const resp = await (await fetch("/api/edit-map")).json();
      map = resp.tags || {};
      paras = resp.paras || [];
    } catch (e) { return; }
    if (!Object.keys(map).length && !paras.length) return;

    const css = el("style");
    css.textContent = `
      .pfe-btn { border:1px solid #d8dce3; background:#fff; color:#5c6470;
        border-radius:6px; cursor:pointer; font:11px -apple-system,sans-serif;
        padding:.06rem .4rem; margin-left:.5rem; vertical-align:middle;
        opacity:.55 }
      .pfe-btn:hover { opacity:1; color:#2563eb; border-color:#2563eb }
      .pfe-panel { position:fixed; right:1rem; bottom:1rem; z-index:1200;
        width:min(46rem, 92vw); background:#fff; color:#16181d;
        border:1px solid #d8dce3; border-radius:10px;
        box-shadow:0 8px 30px rgba(0,0,0,.25); padding:.7rem .9rem;
        font:13px -apple-system,sans-serif }
      .pfe-panel textarea { width:100%; min-height:11rem; font:12px
        ui-monospace,monospace; border:1px solid #d8dce3; border-radius:6px;
        padding:.45rem; box-sizing:border-box; background:#fff; color:#16181d }
      .pfe-row { display:flex; gap:.5rem; align-items:center; flex-wrap:wrap;
        margin-top:.45rem }
      .pfe-row button { border:1px solid #d8dce3; background:#fff;
        color:#16181d; border-radius:6px; cursor:pointer;
        padding:.25rem .7rem; font-size:.82rem }
      .pfe-row button.primary { background:#1e5c3a; border-color:#1e5c3a;
        color:#fff }
      .pfe-status { font-size:.8rem; color:#5c6470 }
      .pfe-status.err { color:#b91c1c }
      .pfe-cite { max-width:15rem; font-size:.78rem; border:1px solid
        #d8dce3; border-radius:6px; background:#fff; color:#16181d;
        padding:.2rem }
      .pfe-preview { max-height:11rem; overflow:auto; margin-top:.45rem;
        background:rgba(128,128,128,.07); border-radius:6px;
        padding:.45rem .6rem; font-size:.92em }
      .pfe-head { font-weight:700; margin-bottom:.35rem }
      @media (prefers-color-scheme: dark) {
        .pfe-panel, .pfe-panel textarea, .pfe-row button, .pfe-btn {
          background:#1d2026; color:#e7e9ee; border-color:#33383f }
        .pfe-row button.primary { background:#2f7c52; border-color:#2f7c52 } }`;
    document.head.appendChild(css);

    let panel = null;
    function closePanel() { if (panel) { panel.remove(); panel = null; } }

    let _bib = null;
    async function fetchBib() {
      if (_bib === null) {
        try { _bib = await (await fetch("/api/bib")).json(); }
        catch (e) { _bib = {}; }
      }
      return _bib;
    }

    async function openEditor(tag, part) {
      closePanel();
      const data = await (await fetch(
        `/api/edit?tag=${encodeURIComponent(tag)}&part=${part}`)).json();
      panel = el("div", "pfe-panel");
      if (data.error) {
        panel.append(el("div", "pfe-status err", data.error));
        const row = el("div", "pfe-row");
        const close = el("button", null, "close");
        close.onclick = closePanel;
        row.append(close);
        panel.append(row);
        document.body.appendChild(panel);
        return;
      }
      panel.append(el("div", "pfe-head",
        (part === "paragraph" ? "paragraph — draft LaTeX"
                              : `${part} of ${tag} — draft LaTeX`) +
        (data.stale ? " (map was stale; showing the current draft)" : "")));
      const ta = document.createElement("textarea");
      ta.value = data.latex;
      const preview = el("div", "pfe-preview");
      const paintPreview = () => {
        preview.innerHTML = ta.value
          .replace(/&/g, "&amp;").replace(/</g, "&lt;")
          .replace(/\$([^$]+)\$/g, "\\($1\\)");
        if (window.MathJax && MathJax.typesetPromise)
          MathJax.typesetPromise([preview]).catch(() => {});
      };
      let pt = null;
      ta.addEventListener("input", () => {
        clearTimeout(pt); pt = setTimeout(paintPreview, 400);
      });
      const status = el("span", "pfe-status", "");
      const save = el("button", "primary", "save & rebuild");
      const cancel = el("button", null, "cancel");
      cancel.onclick = closePanel;
      save.onclick = async () => {
        save.disabled = true;
        status.className = "pfe-status";
        status.textContent = "saving…";
        const r = await fetch("/api/edit", { method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ tag, part, latex: ta.value,
                                 sha: data.sha }) });
        const j = await r.json();
        if (j.lane2) {
          status.className = "pfe-status err";
          status.textContent = j.reason;
          const send = el("button", null, "send to agent instead");
          send.onclick = async () => {
            send.disabled = true;
            const cfg = await (await fetch("/api/agents")).json();
            const where = part === "paragraph"
              ? "a prose paragraph outside any statement/proof, which " +
                "currently reads:\n\n" + data.latex + "\n"
              : `the ${part} of ${tag}.`;
            const extra =
              `Apply this manual edit to ${where}\n` +
              "Replace the draft LaTeX of that block with:\n\n" +
              ta.value + "\n\n" +
              "Keep every xml:id stable, keep the numbering simulation " +
              "clean (crosswalk/numbering-current.json), rebuild, and " +
              "leave validators at zero errors.";
            const rr = await fetch("/api/dispatch", { method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ task: "custom", agent: cfg.default,
                                     extra }) });
            const jj = await rr.json();
            status.textContent = rr.ok ? `agent started: ${jj.job.id}`
                                       : "✗ " + jj.error;
          };
          save.insertAdjacentElement("afterend", send);
          save.disabled = false;
          return;
        }
        if (!r.ok || j.error) {
          status.className = "pfe-status err";
          status.textContent = j.error || "save failed";
          save.disabled = false;
          return;
        }
        status.textContent = `rebuilding… (${j.job.id})`;
        const poll = setInterval(async () => {
          const jobs = await (await fetch("/api/jobs")).json();
          const jb = jobs.find(x => x.id === j.job.id);
          if (!jb || jb.status === "running") return;
          clearInterval(poll);
          if (jb.status === "done") {
            status.textContent = "rebuilt + validated ✓ — reload to see it";
            const rl = el("button", "primary", "reload");
            rl.onclick = () => location.reload();
            status.insertAdjacentElement("afterend", rl);
          } else {
            status.className = "pfe-status err";
            status.textContent =
              "rebuild failed — see the jobs chip for the log";
            save.disabled = false;
          }
        }, 2500);
      };
      // citation picker: inserts \cite{KEY} at the cursor (keys are the
      // bibliography ids minus the bib- prefix; hover any entry in the
      // References list, or any inline [KEY] citation, for its badge)
      const cite = document.createElement("select");
      cite.className = "pfe-cite";
      cite.title = "insert a citation at the cursor";
      cite.append(new Option("\\cite… (insert citation)", ""));
      fetchBib().then(b => {
        Object.keys(b).sort().forEach(k => {
          if (!k.startsWith("bib-")) return;
          cite.append(new Option(k.slice(4) + " — " + (b[k].short || ""),
                                 k.slice(4)));
        });
      });
      cite.onchange = () => {
        if (!cite.value) return;
        const ins = "\\cite{" + cite.value + "}";
        const s = ta.selectionStart, e2 = ta.selectionEnd;
        ta.value = ta.value.slice(0, s) + ins + ta.value.slice(e2);
        ta.selectionStart = ta.selectionEnd = s + ins.length;
        cite.value = "";
        ta.focus();
        ta.dispatchEvent(new Event("input"));
      };

      const row = el("div", "pfe-row");
      row.append(save, cancel, cite, status);
      panel.append(ta, row,
                   el("div", "pfe-status", "preview:"), preview);
      document.body.appendChild(panel);
      paintPreview();
      ta.focus();
    }

    /* wire ✎ buttons: statement on the block heading, proof on its
       summary line */
    for (const [tag, parts] of Object.entries(map)) {
      const art = document.getElementById(tag);
      if (!art) continue;
      if (parts.includes("statement")) {
        const h = art.querySelector(":scope > .heading");
        if (h) {
          const b = el("button", "pfe-btn", "✎");
          b.title = `edit the draft LaTeX of ${tag}`;
          b.onclick = (e) => { e.preventDefault(); e.stopPropagation();
                               openEditor(tag, "statement"); };
          h.appendChild(b);
        }
      }
      if (parts.includes("proof")) {
        // PreTeXt renders the proof as a SIBLING <details> after the
        // article, not inside it — walk forward to the next hiddenproof,
        // stopping at the next statement/division
        let n = art.nextElementSibling;
        while (n && !(n.tagName === "DETAILS" &&
                      n.classList.contains("hiddenproof"))) {
          if (n.tagName === "ARTICLE" || n.tagName === "SECTION" ||
              /^H[1-6]$/.test(n.tagName)) { n = null; break; }
          n = n.nextElementSibling;
        }
        const sum = n && n.querySelector(":scope > summary");
        if (sum) {
          const b = el("button", "pfe-btn", "✎");
          b.title = `edit the draft LaTeX of the proof of ${tag}`;
          b.onclick = (e) => { e.preventDefault(); e.stopPropagation();
                               openEditor(tag, "proof"); };
          sum.appendChild(b);
        }
      }
    }

    /* prose paragraphs (abstract + division-level text): no labels, no
       stable ids (insertion fragments shift PreTeXt's positional ids), so
       anchor by matching each mapped paragraph's prose words against the
       rendered candidates. Woven-in fragment paragraphs match nothing and
       simply get no button. */
    function domWords(p) {
      const clone = p.cloneNode(true);
      clone.querySelectorAll(
        ".displaymath, mjx-container, script, .pfe-btn, .mark-dot, " +
        ".knowl-output, .autopermalink")
        .forEach(n => n.remove());
      const t = (clone.textContent || "")
        .replace(/\\\([\s\S]*?\\\)/g, " ")
        .replace(/\\\[[\s\S]*?\\\]/g, " ")
        .replace(/\\begin\{[\s\S]*\\end\{[A-Za-z]+\*?\}/g, " ");
      return (t.match(/[A-Za-z]{3,}/g) || []).map(w => w.toLowerCase());
    }
    function jaccard(a, b) {
      let inter = 0;
      for (const w of a) if (b.has(w)) inter++;
      return inter / (a.size + b.size - inter || 1);
    }
    if (paras.length) {
      const cands = Array.from(document.querySelectorAll("div.para"))
        .filter(p => !p.closest("article, details, li, nav, table, figure")
                     && !(p.parentElement
                          && p.parentElement.closest(".para")))
        .map(p => ({ el: p, words: new Set(domWords(p)) }))
        .filter(c => c.words.size >= 4);
      const pairs = [];
      for (const m of paras) {
        const ws = new Set(m.words);
        for (let c = 0; c < cands.length; c++) {
          const s = jaccard(ws, cands[c].words);
          if (s >= 0.5) pairs.push({ tag: m.tag, c, s });
        }
      }
      pairs.sort((x, y) => y.s - x.s);
      const usedTag = new Set(), usedCand = new Set();
      for (const p of pairs) {
        if (usedTag.has(p.tag) || usedCand.has(p.c)) continue;
        usedTag.add(p.tag); usedCand.add(p.c);
        const b = el("button", "pfe-btn", "✎");
        b.title = "edit the draft LaTeX of this paragraph";
        b.onclick = (e) => { e.preventDefault(); e.stopPropagation();
                             openEditor(p.tag, "paragraph"); };
        cands[p.c].el.appendChild(b);
      }
    }
  });
})();
