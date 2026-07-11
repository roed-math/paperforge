/* PreTeXt UI layer.
   (1) A global detail slider that reveals detail tiers by level.
   (2) Notation hovers that reveal a definition without a knowl underline
       (event-delegated, so lazily-typeset math is covered).
   (3) Proof-local "details" button that expands the proof text in place.
   (4) Contents sidebar hidden on page load. */
(function () {
  "use strict";

  // --- Notation registry. Generated per-instance from the document's
  //     <notation> list (single source of truth). Entry formats:
  //       key: "definition html"                          (no context link)
  //       key: {html: "...", href: "sec-x.html#def-id"}   (with context link)
  var NOTATION = window.PAPERFORGE_NOTATION || {};

  // Hover delays (ms). A far-marked symbol (.ptxfar wrapper, see
  // ingest/notation_far.py) waits FAR_DELAY before showing its definition;
  // near symbols show promptly. Override via window.paperforgeNotation.
  var CFG = window.paperforgeNotation || {};
  var FAR_DELAY_MS = CFG.farDelayMs != null ? CFG.farDelayMs : 1000;
  var NEAR_DELAY_MS = CFG.nearDelayMs != null ? CFG.nearDelayMs : 150;

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  function levelOf(el) {
    var m = /\bdetail-level-(\d+)\b/.exec(el.className);
    return m ? +m[1] : 0;
  }

  // Reveal machinery: tier elements are either born-hidden <details> knowls
  // (opened directly) or inline blocks like <p detail-level="2"> (revealed by
  // a `show-dl-N` class on a container — body for the global slider, the
  // proof element for the local button; CSS does the rest).
  function setTierClasses(container, level) {
    for (var l = 2; l <= 9; l++) {
      container.classList.toggle("show-dl-" + l, l <= level);
    }
  }

  // Header controls, mounted in the sticky navbar:
  //   Detail [range] n/max [manual]   [?]
  // Level 0 = everything collapsed; level 1 = proofs/remark knowls open;
  // level 2+ = woven detail-tier paragraphs. "manual" replays the reader's
  // own open/close choices (recorded continuously, kept in localStorage).
  // [?] toggles notation links for readers who find the hovers distracting.
  var LS = {
    mode: "pf-detail-mode",            // "manual" | "0".."9"
    manual: "pf-detail-manual",        // {elementId: open?}
    notn: "pf-notation-off",           // "1" | absent
  };
  function lsGet(k, dflt) {
    try { var v = localStorage.getItem(k); return v === null ? dflt : v; }
    catch (e) { return dflt; }
  }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }

  function buildHeaderControls() {
    var tiers = Array.prototype.slice.call(
      document.querySelectorAll('[class*="detail-level-"]'));
    var knowls = Array.prototype.slice.call(
      document.querySelectorAll("details.born-hidden-knowl"));
    if (!tiers.length && !knowls.length) return;
    var max = tiers.reduce(function (a, d) { return Math.max(a, levelOf(d)); },
                           knowls.length ? 1 : 0);

    var bar = document.querySelector(".ptx-navbar-contents") ||
              document.querySelector("#ptx-navbar") || document.body;
    var wrap = document.createElement("div");
    wrap.className = "detail-ctl";
    wrap.innerHTML =
      '<label for="detail-range">Detail</label>' +
      '<input id="detail-range" type="range" min="0" max="' + max +
      '" value="0" step="1" title="0 = collapsed, 1 = proofs, higher = more">' +
      '<span class="detail-val">0/' + max + '</span>' +
      '<button type="button" class="detail-manual" title="replay your own ' +
      'open/close choices (remembered between visits)">manual</button>' +
      '<button type="button" class="notn-toggle" title="notation links ' +
      'on/off">?</button>';
    bar.appendChild(wrap);

    var range = wrap.querySelector("input");
    var out = wrap.querySelector(".detail-val");
    var manualBtn = wrap.querySelector(".detail-manual");
    var notnBtn = wrap.querySelector(".notn-toggle");

    var memory = {};
    try { memory = JSON.parse(lsGet(LS.manual, "{}")); } catch (e) {}

    function applyLevel(t) {
      out.textContent = t + "/" + max;
      knowls.forEach(function (d) { d.open = t >= 1; });
      tiers.forEach(function (d) {
        if (d.tagName === "DETAILS") d.open = levelOf(d) <= t;
      });
      setTierClasses(document.body, t);
    }
    function applyManual() {
      out.textContent = "–/" + max;
      Object.keys(memory).forEach(function (id) {
        var el = document.getElementById(id);
        if (el && el.tagName === "DETAILS") el.open = !!memory[id];
      });
    }
    function setMode(mode) {
      lsSet(LS.mode, mode);
      manualBtn.classList.toggle("active", mode === "manual");
      if (mode === "manual") applyManual();
      else { range.value = mode; applyLevel(+mode); }
    }

    // reader open/close choices are remembered — recorded from the actual
    // gesture (a click on a <summary>), because 'toggle' events also fire,
    // on an unpredictable schedule, for the slider's programmatic sweeps
    document.addEventListener("click", function (e) {
      var sum = e.target.closest && e.target.closest("summary");
      if (!sum || e.target.closest(".detail-next-btn")) return;
      var d = sum.parentElement;
      if (!d || d.tagName !== "DETAILS" || !d.id) return;
      setTimeout(function () {         // after the default toggle applied
        memory[d.id] = d.open;
        lsSet(LS.manual, JSON.stringify(memory));
      }, 0);
    });

    range.addEventListener("input", function () { setMode(range.value); });
    manualBtn.addEventListener("click", function () { setMode("manual"); });

    function setNotn(off) {
      document.body.classList.toggle("notation-links-off", off);
      notnBtn.classList.toggle("off", off);
      notnBtn.title = "notation links " + (off ? "off — click to enable"
                                               : "on — click to disable");
      lsSet(LS.notn, off ? "1" : "");
    }
    notnBtn.addEventListener("click", function () {
      setNotn(!document.body.classList.contains("notation-links-off"));
    });

    setNotn(lsGet(LS.notn, "") === "1");
    setMode(lsGet(LS.mode, "0"));
  }

  // Proof-local details: a small button on the "Proof" line (visible only
  // while the proof is open) steps the proof's own tiers up and back down —
  // the proof text expands in place.
  function wireProofDetails() {
    var proofs = Array.prototype.slice.call(
      document.querySelectorAll("details.hiddenproof"));
    proofs.forEach(function (proof) {
      var tiers = Array.prototype.slice.call(
        proof.querySelectorAll('[class*="detail-level-"]'));
      if (!tiers.length) return;
      var levels = [];
      tiers.forEach(function (d) {
        var l = levelOf(d);
        if (levels.indexOf(l) < 0) levels.push(l);
      });
      levels.sort(function (a, b) { return a - b; });
      var summary = proof.querySelector("summary");
      if (!summary) return;
      var btn = document.createElement("button");
      btn.className = "detail-next-btn";
      summary.appendChild(btn);
      var cur = 0;
      function nextLevel() {
        for (var i = 0; i < levels.length; i++)
          if (levels[i] > cur) return levels[i];
        return null;
      }
      function label() {
        btn.textContent = nextLevel() ? "▸ details" : "▾ less";
      }
      btn.addEventListener("click", function (e) {
        e.preventDefault();      // do not toggle the enclosing summary
        e.stopPropagation();
        var nxt = nextLevel();
        cur = nxt !== null ? nxt : 0;
        setTierClasses(proof, cur);
        tiers.forEach(function (d) {
          if (d.tagName === "DETAILS") d.open = levelOf(d) <= cur;
        });
        label();
      });
      label();
    });
  }

  // Contents hidden on page load (the theme's toggle still works).
  function hideTocOnLoad() {
    var sb = document.getElementById("ptx-sidebar");
    if (!sb) return;
    sb.classList.add("hidden");
    sb.classList.remove("visible");
    var btn = document.getElementById("ptx-toc-toggle");
    if (btn) btn.setAttribute("aria-expanded", "false");
  }

  // Notation hovers, event-delegated: works regardless of when MathJax
  // typesets a given expression (required for lazy typesetting, where math
  // renders as it scrolls into view).
  function wireNotation() {
    var pop = document.createElement("div");
    pop.className = "notation-popup";
    document.body.appendChild(pop);
    var hideTimer, showTimer, hlTimer, hoverEl = null, hlTarget = null;
    var DEFSITE_HL_MS = CFG.defsiteHlDelayMs != null ? CFG.defsiteHlDelayMs : 120;

    pop.addEventListener("mouseenter", function () { clearTimeout(hideTimer); });
    pop.addEventListener("mouseleave", scheduleHide);

    function keyOf(el) {
      var m = /\bptxnotn-([A-Za-z0-9]+)\b/.exec(el.className);
      return m ? m[1] : null;
    }
    function entryFor(k) {
      var v = NOTATION[k];
      if (!v) return null;
      return typeof v === "string" ? { html: v, href: null } : v;
    }
    function isFar(el) {
      return !!(el.closest && el.closest(".ptxfar"));
    }
    function defsiteEl(entry) {
      if (!entry || !entry.href) return null;
      var i = entry.href.indexOf("#");
      return i >= 0 ? document.getElementById(entry.href.slice(i + 1)) : null;
    }
    // The DEFINING OCCURRENCE of a key: the first wrapped occurrence of
    // exactly this key inside its defsite block. This is what hovering
    // elsewhere highlights (a symbol-sized area, never a whole block),
    // and hovering it is what flips the cursor to the ≝ affordance.
    function defOccurrence(entry, k) {
      var target = defsiteEl(entry);
      if (!target) return null;
      var cands = target.querySelectorAll('[class*="ptxnotn-"]');
      for (var i = 0; i < cands.length; i++) {
        if (keyOf(cands[i]) === k) return cands[i];
      }
      return null;
    }
    function show(el) {
      var k = keyOf(el);
      var entry = k && entryFor(k);
      if (!entry) return;
      clearTimeout(hideTimer);
      var html = '<span class="notation-popup-key">' + k + '</span>' + entry.html;
      if (entry.href) {
        // terminology entries (entry.more) point at the background block
        // that reviews the notion; notation entries at the defining spot
        var label = entry.more ? "more details" : "see definition in context";
        html += '<a class="notation-ctx-link" href="' + entry.href +
                '">' + label + ' &#x2197;</a>';
      }
      pop.innerHTML = html;
      var r = el.getBoundingClientRect();
      // Place BELOW the symbol so the popup never covers the text being read.
      pop.style.top = (window.scrollY + r.bottom + 6) + "px";
      pop.style.left = (window.scrollX + r.left) + "px";
      pop.classList.add("show");
      if (window.MathJax && MathJax.typesetPromise) {
        MathJax.typesetPromise([pop]).catch(function () {});
      }
    }
    function clearMarks() {
      clearTimeout(hlTimer);
      if (hlTarget) { hlTarget.classList.remove("notation-defsite-hl"); hlTarget = null; }
    }
    function scheduleHide() {
      clearTimeout(showTimer);
      hideTimer = setTimeout(function () {
        pop.classList.remove("show");
        clearMarks();
      }, 180);
    }

    document.addEventListener("mouseover", function (e) {
      if (document.body.classList.contains("notation-links-off")) return;
      var el = e.target.closest
        ? e.target.closest('[class*="ptxnotn-"]') : null;
      if (el === hoverEl) return;
      if (el) {
        hoverEl = el;
        clearTimeout(hideTimer);
        clearTimeout(showTimer);
        clearMarks();
        var k = keyOf(el);
        var entry = k && entryFor(k);
        var defEl = defOccurrence(entry, k);
        var atDef = !!(defEl && (defEl === el || defEl.contains(el) ||
                                 el.contains(defEl)));
        if (atDef) {
          // this IS the definition: no popup, no highlight — the cursor
          // itself becomes the "source of the notation" affordance
          el.classList.add("notation-defcursor");
          el.title = "this defines " + k;
          return;
        }
        // the defining occurrence (a symbol-sized area) lights up a beat
        // before the popup — just enough delay to skip a passing mouse
        hlTimer = setTimeout(function () {
          if (defEl) {
            defEl.classList.add("notation-defsite-hl");
            hlTarget = defEl;
          }
        }, DEFSITE_HL_MS);
        var delay = isFar(el) ? FAR_DELAY_MS : NEAR_DELAY_MS;
        showTimer = setTimeout(function () { show(el); }, delay);
      } else if (hoverEl && !(e.target.closest &&
                              e.target.closest(".notation-popup"))) {
        hoverEl = null;
        scheduleHide();
      }
    });
  }

  // Lean badges open the declaration's doc entry inline, knowl-style, when
  // the build-time registry (lean-knowls.js) has it; otherwise (or on
  // modified click) they navigate to the docs as plain links.
  function wireLeanKnowls() {
    var REG = window.PAPERFORGE_LEAN_KNOWLS || {};
    // The registry is generated FROM the built docs, so when it is present
    // a badge it lacks has no doc page (private decl, doc-gen4 gap): its
    // find-resolver link would 404. Degrade those to inert pills. Without
    // a registry we cannot tell, so links are left alone.
    if (window.PAPERFORGE_LEAN_KNOWLS) {
      document.querySelectorAll("a.lean-link").forEach(function (a) {
        if (REG[a.getAttribute("data-lean-ref")]) return;
        a.removeAttribute("href");
        a.classList.add("lean-nolink");
        a.title += " (no documentation page)";
      });
    }
    document.addEventListener("click", function (e) {
      var a = e.target.closest ? e.target.closest("a.lean-link") : null;
      if (!a) return;
      var entry = REG[a.getAttribute("data-lean-ref")];
      if (!entry) return;
      if (e.metaKey || e.ctrlKey || e.shiftKey) return;   // allow new-tab
      e.preventDefault();
      if (a._leanKnowl) {
        a._leanKnowl.remove();
        a._leanKnowl = null;
        return;
      }
      var panel = document.createElement("div");
      panel.className = "lean-knowl";
      panel.innerHTML = entry.html +
        '<div class="lean-knowl-foot"><a href="' + entry.href +
        '">full documentation ↗</a></div>';
      a.insertAdjacentElement("afterend", panel);
      a._leanKnowl = panel;
      if (window.MathJax && MathJax.typesetPromise) {
        MathJax.typesetPromise([panel]).catch(function () {});
      }
    });
  }

  // Cross-references to divisions (Section 5, Subsection A.4, ...) open the
  // division's summary in place, knowl-style, from the build-time registry
  // (section-summaries.js): leading prose + a view-in-context link. TOC and
  // in-popup navigation links keep navigating; so do divisions the registry
  // lacks (no leading prose) and modified clicks.
  function wireSectionSummaries() {
    var REG = window.PAPERFORGE_SECTION_SUMMARIES;
    if (!REG) return;
    document.addEventListener("click", function (e) {
      if (e.target.closest && e.target.closest(".section-knowl-foot")) {
        e.target.closest(".section-knowl").remove();   // navigate + tidy up
        return;
      }
      var a = e.target.closest ? e.target.closest('a.internal[href^="#"]') : null;
      if (!a || a.hasAttribute("data-knowl")) return;
      if (!a.closest(".ptx-content")) return;          // TOC, masthead
      if (a.closest(".section-knowl, .notation-popup")) return;
      var tag = a.getAttribute("href").slice(1);
      var entry = REG[tag];
      if (!entry) return;
      if (e.metaKey || e.ctrlKey || e.shiftKey) return;   // allow new-tab
      e.preventDefault();
      if (a._secKnowl && a._secKnowl.isConnected) {
        a._secKnowl.remove();
        a._secKnowl = null;
        return;
      }
      var panel = document.createElement("div");
      panel.className = "section-knowl";
      panel.innerHTML =
        '<div class="section-knowl-title">' + entry.label +
        (entry.title ? " · " + entry.title : "") + "</div>" +
        entry.html +
        '<div class="section-knowl-foot"><a href="#' + tag +
        '">view in context ↗</a></div>';
      var host = a.closest(".para, li, .knowl__content") || a;
      host.insertAdjacentElement("afterend", panel);
      a._secKnowl = panel;
      if (window.MathJax && MathJax.typesetPromise) {
        MathJax.typesetPromise([panel]).catch(function () {});
      }
    });
  }

  ready(function () {
    hideTocOnLoad();
    buildHeaderControls();
    wireProofDetails();
    wireNotation();
    wireLeanKnowls();
    wireSectionSummaries();
  });
})();
