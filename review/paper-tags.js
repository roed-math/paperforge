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
        border-color:#15803d; opacity:1 }
      .ptx-tagbadge.cite { border-color:rgba(146,64,14,.5);
        background:rgba(217,119,6,.07); color:#92400e }
      .ptx-bibadd-btn { border:1px solid #d8dce3; background:#fff;
        color:#5c6470; border-radius:6px; cursor:pointer;
        font:12px -apple-system,sans-serif; padding:.1rem .5rem;
        margin-left:.6rem; vertical-align:middle; opacity:.6 }
      .ptx-bibadd-btn:hover { opacity:1; color:#92400e;
        border-color:#92400e }
      #pf-bibadd-panel { position:fixed; right:1rem; bottom:1rem;
        z-index:1300; width:min(40rem,92vw); background:#fff; color:#16181d;
        border:1px solid #d8dce3; border-radius:10px; padding:.7rem .9rem;
        box-shadow:0 8px 30px rgba(0,0,0,.25);
        font:13px -apple-system,sans-serif }
      #pf-bibadd-panel label { display:block; margin:.35rem 0;
        color:#5c6470 }
      #pf-bibadd-panel input, #pf-bibadd-panel textarea { width:100%;
        box-sizing:border-box; font:12px ui-monospace,monospace;
        border:1px solid #d8dce3; border-radius:6px; padding:.3rem;
        background:#fff; color:#16181d }
      .pf-bibadd-head { font-weight:700; margin-bottom:.25rem }
      .pf-bibadd-row { display:flex; gap:.5rem; align-items:center;
        margin-top:.45rem; flex-wrap:wrap }
      .pf-bibadd-row button { border:1px solid #d8dce3; background:#fff;
        color:#16181d; border-radius:6px; cursor:pointer;
        padding:.25rem .7rem; font-size:.82rem }
      .pf-bibadd-row button.primary { background:#92400e;
        border-color:#92400e; color:#fff }
      .pf-bibadd-status { font-size:.8rem; color:#5c6470 }
      .pf-bibadd-status.err { color:#b91c1c }
      @media (prefers-color-scheme: dark) {
        #pf-bibadd-panel, #pf-bibadd-panel input, #pf-bibadd-panel textarea,
        .pf-bibadd-row button, .ptx-bibadd-btn {
          background:#1d2026; color:#e7e9ee; border-color:#33383f }
        .pf-bibadd-row button.primary { background:#b45309;
          border-color:#b45309 } }`;
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

    /* ---- bibliography: \cite{KEY} discovery -------------------------- */
    let bib = {};
    try { bib = await (await fetch("/api/bib")).json(); } catch (e) {}

    function citeBadge(host, key) {
      const badge = document.createElement("span");
      badge.className = "ptx-tagbadge cite";
      badge.textContent = "\\cite{" + key + "}";
      badge.title = "click to copy — add a pin with \\cite[Theorem 1.2]{" +
                    key + "}";
      badge.addEventListener("click", async (ev) => {
        ev.stopPropagation(); ev.preventDefault();
        try { await navigator.clipboard.writeText("\\cite{" + key + "}"); }
        catch (e) { /* badge text is still visible to copy by hand */ }
        badge.classList.add("copied");
        const old = badge.textContent;
        badge.textContent = "copied ✓";
        setTimeout(() => { badge.classList.remove("copied");
                           badge.textContent = old; }, 900);
      });
      host.classList.add("ptx-tagged");
      host.appendChild(badge);
    }

    // the entries in the References list. Their rendered ids come from the
    // biblio serial number — with alphabetic labels (bib-labels.json +
    // the serial-number XSL override) that IS the label ("Asc", "NSW"), so
    // resolve key -> label first; fall back to key-shaped ids for
    // instances without labels.
    let bibLabels = {};
    try { bibLabels = await (await fetch("/references/bib-labels.json"))
                        .json(); } catch (e) {}
    for (const bkey of Object.keys(bib)) {
      if (!bkey.startsWith("bib-")) continue;
      const lab = bibLabels[bkey] && bibLabels[bkey].label;
      const entry = (lab && document.getElementById(lab)) ||
                    document.getElementById(bkey) ||
                    document.getElementById(bkey.slice(4));
      if (entry && entry.classList.contains("bib")) {
        citeBadge(entry, bkey.slice(4));
      }
    }
    // …and every inline citation [KEY, pin] (key from the knowl path — the
    // href carries the stripped id)
    document.querySelectorAll('.ptx-content a[data-knowl]').forEach(a => {
      const m = /\/bib-([A-Za-z0-9]+)\.html$/.exec(
        a.getAttribute("data-knowl") || "");
      if (m) citeBadge(a, m[1]);
    });

    /* ---- add a new reference (references/extra-biblio.xml) ----------- */
    const refsHead = (() => {
      const sec = document.getElementById("references");
      return sec && sec.querySelector(".heading");
    })();
    if (refsHead) {
      const add = document.createElement("button");
      add.className = "ptx-bibadd-btn";
      add.textContent = "+ reference";
      add.title = "add a bibliography entry (appends to " +
                  "references/extra-biblio.xml + bib-labels.json, then " +
                  "rebuilds)";
      add.addEventListener("click", (e) => {
        e.preventDefault(); e.stopPropagation(); openBibAdd();
      });
      refsHead.appendChild(add);
    }

    function openBibAdd() {
      const old = document.getElementById("pf-bibadd-panel");
      if (old) { old.remove(); return; }
      const p = document.createElement("div");
      p.id = "pf-bibadd-panel";
      p.innerHTML = `
        <div class="pf-bibadd-head">add a bibliography entry</div>
        <label>key (cite as \\cite{KEY})
          <input id="pfba-key" placeholder="Iwasawa86" spellcheck="false"></label>
        <label>label (bracket text, e.g. Iwa — year suffix only to break
          same-author collisions)
          <input id="pfba-label" placeholder="Iwa" spellcheck="false"></label>
        <label>sort (author-name order: surnames then year)
          <input id="pfba-sort" placeholder="iwasawa 1986" spellcheck="false"></label>
        <label>entry (inline LaTeX — same syntax as the draft bibliography)
          <textarea id="pfba-entry" rows="3"
            placeholder="K. Iwasawa, \\emph{Local Class Field Theory}, Oxford University Press, 1986."></textarea></label>
        <div class="pf-bibadd-row">
          <button class="primary" id="pfba-save">add + rebuild</button>
          <button id="pfba-cancel">cancel</button>
          <span class="pf-bibadd-status" id="pfba-status"></span>
        </div>`;
      document.body.appendChild(p);
      p.querySelector("#pfba-cancel").onclick = () => p.remove();
      const status = p.querySelector("#pfba-status");
      p.querySelector("#pfba-save").onclick = async () => {
        status.className = "pf-bibadd-status";
        status.textContent = "saving…";
        const body = {
          key: p.querySelector("#pfba-key").value,
          label: p.querySelector("#pfba-label").value,
          sort: p.querySelector("#pfba-sort").value,
          entry: p.querySelector("#pfba-entry").value,
        };
        const r = await fetch("/api/bib-add", { method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body) });
        const j = await r.json();
        if (!r.ok || j.error) {
          status.className = "pf-bibadd-status err";
          status.textContent = j.error || "save failed";
          return;
        }
        try { await navigator.clipboard.writeText(
          "\\cite{" + body.key.trim() + "}"); } catch (e) {}
        status.textContent = `${j.key} added, \\cite{${body.key.trim()}} ` +
          `copied — rebuilding (${j.job.id}); reload when it finishes ` +
          `(jobs chip)`;
      };
    }
  });
})();
