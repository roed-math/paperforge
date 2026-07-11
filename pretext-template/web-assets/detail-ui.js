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

  function buildSlider() {
    var items = Array.prototype.slice.call(
      document.querySelectorAll('[class*="detail-level-"]'));
    if (!items.length) return;
    var max = items.reduce(function (a, d) { return Math.max(a, levelOf(d)); }, 1);

    var wrap = document.createElement("div");
    wrap.className = "detail-slider";
    wrap.innerHTML =
      '<label for="detail-range">Detail</label>' +
      '<input id="detail-range" type="range" min="0" max="' + max + '" value="0" step="1">' +
      '<span class="detail-val">0/' + max + '</span>';

    var host = document.querySelector("#ptx-masthead") || document.body;
    host.appendChild(wrap);

    var range = wrap.querySelector("input");
    var out = wrap.querySelector(".detail-val");
    function apply() {
      var t = +range.value;
      out.textContent = t + "/" + max;
      items.forEach(function (d) {
        if (d.tagName === "DETAILS") d.open = levelOf(d) <= t;
      });
      setTierClasses(document.body, t);
    }
    range.addEventListener("input", apply);
    apply();
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
    var hideTimer, showTimer, hoverEl = null;

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
    function show(el) {
      var k = keyOf(el);
      var entry = k && entryFor(k);
      if (!entry) return;
      clearTimeout(hideTimer);
      var html = '<span class="notation-popup-key">' + k + '</span>' + entry.html;
      if (entry.href) {
        html += '<a class="notation-ctx-link" href="' + entry.href +
                '">see definition in context &#x2197;</a>';
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
    function scheduleHide() {
      clearTimeout(showTimer);
      hideTimer = setTimeout(function () { pop.classList.remove("show"); }, 180);
    }

    document.addEventListener("mouseover", function (e) {
      var el = e.target.closest
        ? e.target.closest('[class*="ptxnotn-"]') : null;
      if (el === hoverEl) return;
      if (el) {
        hoverEl = el;
        clearTimeout(hideTimer);
        clearTimeout(showTimer);
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

  ready(function () {
    hideTocOnLoad();
    buildSlider();
    wireProofDetails();
    wireNotation();
    wireLeanKnowls();
  });
})();
