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

  // Jump to #frag WITHOUT engaging the browser's :target styling (the theme
  // flashes the whole target block for 10s), then paint the specific
  // referenced element — occEl when given, else the target's heading — and
  // fade it out over five seconds.
  function landingGo(frag, occEl) {
    var target = document.getElementById(frag);
    if (!target) return false;
    var hl = occEl || target.querySelector(".heading") || target;
    (occEl || target).scrollIntoView(occEl ? {block: "center"}
                                           : {block: "start"});
    if (window.history && history.pushState) {
      history.pushState(null, "", "#" + frag);
    }
    hl.classList.remove("pf-landing-fade");
    hl.classList.add("pf-landing-hl");
    void hl.offsetWidth;                      // commit the painted state
    hl.classList.add("pf-landing-fade");
    setTimeout(function () {
      hl.classList.remove("pf-landing-hl", "pf-landing-fade");
    }, 5200);
    return true;
  }

  // Reveal machinery: tier elements are either born-hidden <details> knowls
  // (opened directly) or inline blocks like <p detail-level="2"> (revealed by
  // a `show-dl-N` class on a container — body for the global slider, the
  // proof element for the local button; CSS does the rest).
  function setTierClasses(container, level) {
    for (var l = 1; l <= 9; l++) {
      container.classList.toggle("show-dl-" + l, l <= level);
    }
  }

  // Header controls, mounted in the sticky navbar:
  //   Detail [range] n/max [manual]   [?]
  // Level 0 = everything collapsed, terse statements; level 1 = proofs and
  // remark knowls open + statement detail tiers (detail-level="1");
  // level 2+ = woven proof detail-tier paragraphs. "manual" replays the
  // reader's own open/close choices (recorded continuously, in localStorage).
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

  // Statement-local details: a theorem-like block whose STATEMENT carries
  // tier paragraphs (detail-level="1") gets the same stepper as proofs,
  // placed just before the first hidden tier — the terse statement expands
  // in place. (PreTeXt emits no statement wrapper in HTML: statement
  // paragraphs are direct article children; proof tiers live inside the
  // reparented <details> and are excluded.)
  function wireStatementDetails() {
    var arts = Array.prototype.slice.call(
      document.querySelectorAll("article.theorem-like, " +
        "article.definition-like, article.remark-like"));
    arts.forEach(function (art) {
      var tiers = Array.prototype.slice.call(
        art.querySelectorAll('[class*="detail-level-"]')).filter(
          function (d) { return !d.closest("details"); });
      if (!tiers.length) return;
      var levels = [];
      tiers.forEach(function (d) {
        var l = levelOf(d);
        if (levels.indexOf(l) < 0) levels.push(l);
      });
      levels.sort(function (a, b) { return a - b; });
      var btn = document.createElement("button");
      btn.className = "detail-next-btn detail-stmt-btn";
      tiers[0].insertAdjacentElement("beforebegin", btn);
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
        e.preventDefault();
        e.stopPropagation();
        var nxt = nextLevel();
        cur = nxt !== null ? nxt : 0;
        setTierClasses(art, cur);
        label();
      });
      label();
    });
  }

  // Contents visible by default on wide screens (owner request 2026-07-27,
  // reversing the earlier hide-on-load): the default-open rule lives in
  // paper-style.css; the theme's toggle adds .hidden/.visible as before.

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

    // Following a context link: instead of the theme's whole-block :target
    // flash, jump there and paint ONLY the specific referenced text — the
    // defining occurrence of the term when the target block carries one,
    // else the target's heading (landingGo).
    pop.addEventListener("click", function (e) {
      var a = e.target.closest ? e.target.closest(".notation-ctx-link") : null;
      if (!a) return;
      if (e.metaKey || e.ctrlKey || e.shiftKey) return;   // allow new-tab
      var href = a.getAttribute("href") || "";
      var i = href.indexOf("#");
      if (i < 0) return;
      var page = href.slice(0, i).split("/").pop();
      if (page && page !== location.pathname.split("/").pop()) return;
      var occ = pop._entry ? defOccurrence(pop._entry, pop._key) : null;
      if (!landingGo(href.slice(i + 1), occ)) return;
      e.preventDefault();
      pop.classList.remove("show");
      clearMarks();
    });

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
      // prose/background entries carry a human heading; math keys ARE one
      var html = '<span class="notation-popup-key">' + (entry.label || k) +
                 '</span>' + entry.html;
      if (entry.href) {
        // terminology entries (entry.more) point at the background block
        // that reviews the notion; notation entries at the defining spot
        var label = entry.more ? "more details" : "see definition in context";
        html += '<a class="notation-ctx-link" href="' + entry.href +
                '">' + label + ' &#x2197;</a>';
      }
      pop.innerHTML = html;
      pop._key = k;                 // for the context-link landing highlight
      pop._entry = entry;
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
        // prose term links (.ptxbg) read like ordinary text, so they get
        // the far delay: no popup flicker while mousing across a paragraph
        var far = isFar(el) || (el.classList && el.classList.contains("ptxbg"));
        var delay = far ? FAR_DELAY_MS : NEAR_DELAY_MS;
        showTimer = setTimeout(function () { show(el); }, delay);
      } else if (hoverEl && !(e.target.closest &&
                              e.target.closest(".notation-popup"))) {
        hoverEl = null;
        scheduleHide();
      }
    });
  }

  // Equation ranges: "(1.1)–(1.3)" is authored as two equation xrefs around
  // an en dash, so only the endpoints open as knowls. Make the whole range
  // ONE click target that opens every equation in the range — endpoints and
  // middles alike — in a single stacked panel. Content is re-typeset from
  // MathJax's stored TeX (getMathItemsWithin), so it works even for middle
  // equations that were never cross-referenced (no knowl file) or not yet
  // lazily typeset; \notn wrappers survive, so notation hovers work inside.
  function wireEquationRanges() {
    function eqTarget(a) {
      var href = a.getAttribute("href") || "";
      if (href.charAt(0) !== "#") return null;
      var el = document.getElementById(href.slice(1));
      return el && el.classList.contains("displaymath") ? el : null;
    }
    function eqNum(a) {   // "(1.3)" -> {prefix: "1.", n: 3}
      var m = /^\((?:([0-9A-Za-z.]+)\.)?(\d+)\)$/.exec(a.textContent.trim());
      return m ? {prefix: m[1] ? m[1] + "." : "", n: +m[2]} : null;
    }
    var anchors = Array.prototype.slice.call(
      document.querySelectorAll('.ptx-content a[data-knowl][href^="#"]'));
    anchors.forEach(function (a1) {
      var dash = a1.nextSibling;
      if (!dash || dash.nodeType !== 3 ||
          dash.textContent.trim() !== "–") return;
      var a2 = dash.nextSibling;
      if (!a2 || a2.nodeType !== 1 ||
          !a2.matches('a[data-knowl][href^="#"]')) return;
      var e1 = eqTarget(a1), e2 = eqTarget(a2);
      var n1 = eqNum(a1), n2 = eqNum(a2);
      if (!e1 || !e2 || !n1 || !n2) return;
      if (n1.prefix !== n2.prefix || n2.n <= n1.n) return;
      var all = Array.prototype.slice.call(
        document.querySelectorAll("div.displaymath[id]"));
      var i1 = all.indexOf(e1), i2 = all.indexOf(e2);
      if (i1 < 0 || i2 <= i1) return;
      var eqs = all.slice(i1, i2 + 1);
      if (eqs.length !== n2.n - n1.n + 1) return;  // numbering mismatch: bail
      var span = document.createElement("span");
      span.className = "eqrange";
      span.title = "show equations " + a1.textContent + "–" +
                   a2.textContent;
      a1.parentNode.insertBefore(span, a1);
      span.appendChild(a1);
      span.appendChild(dash);
      span.appendChild(a2);
      span.addEventListener("click", function (e) {
        if (e.metaKey || e.ctrlKey || e.shiftKey) return;   // allow new-tab
        e.preventDefault();
        e.stopPropagation();
        if (span._panel && span._panel.isConnected) {
          span._panel.remove();
          span._panel = null;
          return;
        }
        var doc = window.MathJax && MathJax.startup && MathJax.startup.document;
        var parts = eqs.map(function (eq) {
          var tex = null;
          if (doc && doc.getMathItemsWithin) {
            var items = doc.getMathItemsWithin(eq);
            if (items.length === 1) tex = items[0].math;
          }
          if (tex == null) return null;
          // the stored TeX carries its own \tag{...} (the printed number);
          // strip only the environment and any \label (re-typesetting a
          // duplicate label is a MathJax error)
          tex = tex.replace(/\\begin\{equation\*?\}|\\end\{equation\*?\}/g, "")
                   .replace(/\\label\{[^{}]*\}/g, "");
          return "\\[" + tex + "\\]";
        });
        if (parts.indexOf(null) >= 0) {
          a1.click();          // stored TeX unavailable: at least open the
          a2.click();          // endpoint knowls the classical way
          return;
        }
        var panel = document.createElement("div");
        panel.className = "eqrange-knowl";
        panel.innerHTML = parts.join("\n");
        var foot = document.createElement("div");
        foot.className = "eqrange-knowl-foot";
        var ctx = document.createElement("a");
        ctx.href = "#" + e1.id;
        ctx.textContent = "view in context ↗";
        ctx.addEventListener("click", function (ev) {
          if (ev.metaKey || ev.ctrlKey || ev.shiftKey) return;
          ev.preventDefault();
          ev.stopPropagation();
          panel.remove();
          span._panel = null;
          landingGo(e1.id, e1);
        });
        foot.appendChild(ctx);
        panel.appendChild(foot);
        var host = span.closest(".para, li, .knowl__content") || span;
        host.insertAdjacentElement("afterend", panel);
        span._panel = panel;
        if (window.MathJax && MathJax.typesetPromise) {
          MathJax.typesetPromise([panel]).catch(function () {});
        }
      }, true);      // capture: beat the anchors' own knowl handlers
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
        a.setAttribute("aria-expanded", "false");
        return;
      }
      var panel = document.createElement("div");
      panel.className = "lean-knowl";
      panel.setAttribute("role", "region");
      panel.setAttribute("aria-label",
        "Lean declaration " + a.getAttribute("data-lean-ref"));
      panel.innerHTML = entry.html +
        '<div class="lean-knowl-foot"><a href="' + entry.href +
        '">full documentation ↗</a></div>';
      a.insertAdjacentElement("afterend", panel);
      a._leanKnowl = panel;
      a.setAttribute("aria-expanded", "true");
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
        a.setAttribute("aria-expanded", "false");
        return;
      }
      var panel = document.createElement("div");
      panel.className = "section-knowl";
      panel.setAttribute("role", "region");
      panel.setAttribute("aria-label", entry.label +
        (entry.title ? ": " + entry.title : ""));
      panel.innerHTML =
        '<div class="section-knowl-title">' + entry.label +
        (entry.title ? " · " + entry.title : "") + "</div>" +
        entry.html +
        '<div class="section-knowl-foot"><a href="#' + tag +
        '">view in context ↗</a></div>';
      var host = a.closest(".para, li, .knowl__content") || a;
      host.insertAdjacentElement("afterend", panel);
      a._secKnowl = panel;
      a.setAttribute("aria-expanded", "true");
      if (window.MathJax && MathJax.typesetPromise) {
        MathJax.typesetPromise([panel]).catch(function () {});
      }
    });
  }

  // Links back to the project homepage, top and bottom (the paper is the
  // one subpage PreTeXt generates, so they are injected rather than authored).
  function addHomeLinks() {
    var masthead = document.querySelector('.ptx-masthead');
    if (masthead && !masthead.querySelector('.site-home-link')) {
      var top = document.createElement('div');
      top.className = 'site-home-link';
      top.innerHTML = '<a href="../">← Project homepage</a>';
      masthead.insertBefore(top, masthead.firstChild);
    }
    var host = document.querySelector('.ptx-content-footer') ||
               document.querySelector('.ptx-main') || document.body;
    if (!host.querySelector('.site-home-return')) {
      var bottom = document.createElement('div');
      bottom.className = 'site-home-return';
      bottom.innerHTML = '<a href="../">Return to the project homepage</a>.';
      host.appendChild(bottom);
    }
  }

  ready(function () {
    buildHeaderControls();
    wireProofDetails();
    wireStatementDetails();
    wireNotation();
    wireEquationRanges();
    wireLeanKnowls();
    wireSectionSummaries();
    addHomeLinks();
  });
})();
