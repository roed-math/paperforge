/* paperforge review mode: lane-1 manual editing (docs/EDITOR.md).
   For every statement/proof the tex2ptx source map covers, an ✎ button
   opens the block's DRAFT LaTeX in an editor panel. Saving splices the
   edit back into the draft and starts a rebuild+validate job; structural
   edits (labels, environments, sectioning) are deflected to lane 2 —
   dispatch to the configured agent with the typed LaTeX as briefing.
   Prose paragraphs woven in from insertion fragments are covered too
   (part=fragment: the slice is the fragment file's <p> XML).
   Every ✎ has a 🗑 twin: deletion removes the block from its source file
   WITHOUT rebuilding, shows an undo affordance (LIFO), and a floating
   pill offers "rebuild now" once you are sure. */
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
  function jpost(url, body) {
    return fetch(url, { method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body) }).then(r => r.json());
  }

  ready(async function () {
    let map, paras, frags, pending;
    try {
      const resp = await (await fetch("/api/edit-map")).json();
      map = resp.tags || {};
      paras = resp.paras || [];
      frags = resp.frags || [];
      pending = ((await (await fetch("/api/deletions")).json())
                 .pending || []).length;
    } catch (e) { return; }
    if (!Object.keys(map).length && !paras.length && !frags.length) return;

    const css = el("style");
    css.textContent = `
      .pfe-btn { border:1px solid #d8dce3; background:#fff; color:#5c6470;
        border-radius:6px; cursor:pointer; font:11px -apple-system,sans-serif;
        padding:.06rem .4rem; margin-left:.5rem; vertical-align:middle;
        opacity:.55 }
      .pfe-btn:hover { opacity:1; color:#2563eb; border-color:#2563eb }
      .pfe-btn.pfe-del:hover { color:#b91c1c; border-color:#b91c1c }
      .pfe-btn.pfe-undo { opacity:.9; color:#b45309; border-color:#b45309 }
      .pfe-deleted { opacity:.35; outline:2px dashed #b91c1c;
        outline-offset:2px }
      .pfe-pill { position:fixed; left:1rem; bottom:1rem; z-index:1200;
        display:flex; gap:.55rem; align-items:center; background:#fff;
        color:#16181d; border:1px solid #d8dce3; border-radius:999px;
        box-shadow:0 4px 16px rgba(0,0,0,.18); padding:.3rem .8rem;
        font:12px -apple-system,sans-serif }
      .pfe-pill button { border:1px solid #d8dce3; background:#fff;
        color:#16181d; border-radius:999px; cursor:pointer;
        padding:.12rem .6rem; font-size:.78rem }
      .pfe-pill button.primary { background:#1e5c3a; border-color:#1e5c3a;
        color:#fff }
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
        .pfe-panel, .pfe-panel textarea, .pfe-row button, .pfe-btn,
        .pfe-pill, .pfe-pill button {
          background:#1d2026; color:#e7e9ee; border-color:#33383f }
        .pfe-row button.primary, .pfe-pill button.primary {
          background:#2f7c52; border-color:#2f7c52 } }`;
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

    /* poll the jobs API until job `id` finishes; resolve true on done */
    function pollJob(id, cb) {
      const t = setInterval(async () => {
        let jb = null;
        try {
          const jobs = await (await fetch("/api/jobs")).json();
          jb = jobs.find(x => x.id === id);
        } catch (e) { return; }
        if (!jb || jb.status === "running") return;
        clearInterval(t);
        cb(jb.status === "done");
      }, 2500);
    }

    /* ------------------------------------------------ pending deletions */
    let pill = null, pillStatus = null;
    function refreshPill() {
      if (!pending) { if (pill) { pill.remove(); pill = null; } return; }
      if (!pill) {
        pill = el("div", "pfe-pill");
        pillStatus = el("span");
        const undo = el("button", null, "undo last");
        undo.onclick = async () => {
          const r = await jpost("/api/delete-undo", {});
          if (!r.ok) { alert(r.error || "undo failed"); return; }
          pending = r.pending;
          // the page still shows the block; just clear its overlay if here
          document.querySelectorAll(".pfe-deleted").forEach(n => {
            if (n.dataset.pfeDel === r.tag + "/" + r.part) {
              n.classList.remove("pfe-deleted");
              delete n.dataset.pfeDel;
            }
          });
          document.querySelectorAll(".pfe-undo").forEach(b => {
            if (b.dataset.pfeDel === r.tag + "/" + r.part && b._pfeArm)
              b._pfeArm();
          });
          refreshPill();
        };
        const rebuild = el("button", "primary", "rebuild now");
        rebuild.onclick = async () => {
          rebuild.disabled = true;
          rebuild.textContent = "rebuilding…";
          const j = await jpost("/api/rebuild", {});
          if (!j.ok) { alert(j.error || "rebuild failed"); return; }
          pollJob(j.job.id, ok => {
            if (ok) location.reload();
            else {
              rebuild.disabled = false;
              rebuild.textContent = "rebuild now";
              pillStatus.textContent =
                "rebuild FAILED — see the jobs chip";
            }
          });
        };
        pill.append(pillStatus, undo, rebuild);
        document.body.appendChild(pill);
      }
      pillStatus.textContent =
        `🗑 ${pending} deletion${pending > 1 ? "s" : ""} pending rebuild`;
    }
    refreshPill();

    /* delete a block; els = page elements to overlay while pending */
    async function doDelete(tag, part, els, btn, arm) {
      let j = await jpost("/api/delete", { tag, part });
      if (j.refs) {
        const ok = confirm(
          "This block defines labels that are referenced elsewhere:\n\n" +
          j.refs.join("\n") +
          "\n\nDelete anyway? (those references will dangle)");
        if (!ok) return;
        j = await jpost("/api/delete", { tag, part, force: true });
      }
      if (!j.ok) { alert(j.error || "delete failed"); return; }
      pending = j.pending;
      refreshPill();
      els.forEach(e => {
        if (!e) return;
        e.classList.add("pfe-deleted");
        e.dataset.pfeDel = tag + "/" + part;
      });
      btn.textContent = "undo";
      btn.title = "undo this deletion (before rebuilding)";
      btn.classList.add("pfe-undo");
      btn.dataset.pfeDel = tag + "/" + part;
      btn.onclick = async (ev) => {
        ev.preventDefault(); ev.stopPropagation();
        const r = await jpost("/api/delete-undo", { id: j.id });
        if (!r.ok) { alert(r.error || "undo failed"); return; }
        pending = r.pending;
        refreshPill();
        els.forEach(e => {
          if (!e) return;
          e.classList.remove("pfe-deleted");
          delete e.dataset.pfeDel;
        });
        arm();
      };
    }

    function delBtn(tag, part, els, what) {
      const b = el("button", "pfe-btn pfe-del", "🗑");
      const arm = () => {
        b.textContent = "🗑";
        b.className = "pfe-btn pfe-del";
        delete b.dataset.pfeDel;
        b.title = `delete ${what} (undoable until the next rebuild)`;
        b.onclick = (e) => { e.preventDefault(); e.stopPropagation();
                             doDelete(tag, part, els, b, arm); };
      };
      b._pfeArm = arm;
      arm();
      return b;
    }

    /* ----------------------------------------------------- edit panel */
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
         : part === "fragment" ? `fragment paragraph — PreTeXt XML (${data.file})`
                               : `${part} of ${tag} — draft LaTeX`) +
        (data.stale ? " (map was stale; showing the current draft)" : "")));
      const ta = document.createElement("textarea");
      ta.value = data.latex;
      const preview = el("div", "pfe-preview");
      const paintPreview = () => {
        let v = ta.value;
        if (part === "fragment") {
          // rough client-side view of the XML: math elements -> MathJax
          // delimiters, other tags stripped
          v = v.replace(/<!--[\s\S]*?-->/g, " ")
               .replace(/<m(?:\s[^>]*)?>/g, "\\(")
               .replace(/<\/m>/g, "\\)")
               .replace(/<(me|md)(?:\s[^>]*)?>/g, "\\[")
               .replace(/<\/(me|md)>/g, "\\]")
               .replace(/<mdash\s*\/>/g, "—")
               .replace(/<ndash\s*\/>/g, "–")
               .replace(/<[^>]+>/g, " ")
               .replace(/&amp;/g, "&");
          preview.innerHTML = v.replace(/</g, "&lt;");
        } else {
          preview.innerHTML = v
            .replace(/&/g, "&amp;").replace(/</g, "&lt;")
            .replace(/\$([^$]+)\$/g, "\\($1\\)");
        }
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
        pollJob(j.job.id, ok => {
          if (ok) {
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
        });
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
        const ins = part === "fragment"
          ? '<xref ref="bib-' + cite.value + '"/>'
          : "\\cite{" + cite.value + "}";
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

    /* wire ✎/🗑 buttons: statement on the block heading (articles AND
       born-hidden knowls, whose heading lives inside <summary>), proof on
       its summary line */
    for (const [tag, parts] of Object.entries(map)) {
      const art = document.getElementById(tag);
      if (!art) continue;
      // PreTeXt renders the proof as a SIBLING <details> after the
      // article, not inside it — walk forward to the next hiddenproof,
      // stopping at the next statement/division
      let proofEl = null;
      {
        let n = art.nextElementSibling;
        while (n && !(n.tagName === "DETAILS" &&
                      n.classList.contains("hiddenproof"))) {
          if (n.tagName === "ARTICLE" || n.tagName === "SECTION" ||
              /^H[1-6]$/.test(n.tagName)) { n = null; break; }
          n = n.nextElementSibling;
        }
        proofEl = n;
      }
      if (parts.includes("statement")) {
        const h = art.querySelector(":scope > .heading") ||
                  art.querySelector(":scope > summary > .heading");
        if (h) {
          const b = el("button", "pfe-btn", "✎");
          b.title = `edit the draft LaTeX of ${tag}`;
          b.onclick = (e) => { e.preventDefault(); e.stopPropagation();
                               openEditor(tag, "statement"); };
          h.appendChild(b);
          if (parts.includes("envelope"))
            h.appendChild(delBtn(tag, "statement", [art, proofEl],
                                 `${tag} (statement and proof)`));
        }
      }
      if (parts.includes("proof")) {
        const sum = proofEl && proofEl.querySelector(":scope > summary");
        if (sum) {
          const b = el("button", "pfe-btn", "✎");
          b.title = `edit the draft LaTeX of the proof of ${tag}`;
          b.onclick = (e) => { e.preventDefault(); e.stopPropagation();
                               openEditor(tag, "proof"); };
          sum.appendChild(b);
          if (parts.includes("proof_envelope"))
            sum.appendChild(delBtn(tag, "proof", [proofEl],
                                   `the proof of ${tag}`));
        }
      }
    }

    /* prose paragraphs: division-level text from the draft (paras) and
       woven-in insertion-fragment paragraphs (frags). Neither carries a
       label or stable id (PreTeXt paragraph ids are positional and
       fragments shift them), so anchor by matching each mapped
       paragraph's prose words against the rendered candidates. */
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
    const mapped = paras.map(m => ({ tag: m.tag, words: m.words,
                                     part: "paragraph" }))
      .concat(frags.map(m => ({ tag: m.tag, words: m.words,
                                part: "fragment" })));
    if (mapped.length) {
      const cands = Array.from(document.querySelectorAll("div.para"))
        .filter(p => !p.closest("article, details, li, nav, table, figure")
                     && !(p.parentElement
                          && p.parentElement.closest(".para")))
        .map(p => ({ el: p, words: new Set(domWords(p)) }))
        .filter(c => c.words.size >= 4);
      const pairs = [];
      for (let i = 0; i < mapped.length; i++) {
        const ws = new Set(mapped[i].words);
        for (let c = 0; c < cands.length; c++) {
          const s = jaccard(ws, cands[c].words);
          if (s >= 0.5) pairs.push({ i, c, s });
        }
      }
      pairs.sort((x, y) => y.s - x.s);
      const usedTag = new Set(), usedCand = new Set();
      for (const p of pairs) {
        if (usedTag.has(p.i) || usedCand.has(p.c)) continue;
        usedTag.add(p.i); usedCand.add(p.c);
        const m = mapped[p.i], target = cands[p.c].el;
        const b = el("button", "pfe-btn", "✎");
        b.title = m.part === "fragment"
          ? "edit this paragraph's insertion fragment (PreTeXt XML)"
          : "edit the draft LaTeX of this paragraph";
        b.onclick = (e) => { e.preventDefault(); e.stopPropagation();
                             openEditor(m.tag, m.part); };
        target.appendChild(b);
        target.appendChild(delBtn(m.tag, m.part, [target],
                                  "this paragraph"));
      }
    }
  });
})();
