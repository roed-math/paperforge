/* PreTeXt spike: client-side UI layer.
   (1) A global detail slider that opens/closes born-hidden knowls by level.
   (2) Notation hovers that reveal a definition without a knowl underline. */
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

  // Notation lives inside math, which MathJax typesets asynchronously AFTER
  // DOMContentLoaded. Wait for MathJax's startup promise before wiring, else
  // the ptxnotn- nodes do not exist yet.
  function afterMathJax(fn) {
    var tries = 0;
    (function wait() {
      if (window.MathJax && MathJax.startup && MathJax.startup.promise) {
        MathJax.startup.promise.then(fn).catch(fn);
      } else if (tries++ < 200) {
        setTimeout(wait, 50);
      } else {
        fn(); // no MathJax on this page; run anyway (no-op if nothing to wire)
      }
    })();
  }

  function levelOf(el) {
    var m = /\bdetail-level-(\d+)\b/.exec(el.className);
    return m ? +m[1] : 0;
  }

  function buildSlider() {
    var items = Array.prototype.slice.call(
      document.querySelectorAll('details[class*="detail-level-"]'));
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
      items.forEach(function (d) { d.open = levelOf(d) <= t; });
    }
    range.addEventListener("input", apply);
    apply();
  }

  function wireNotation() {
    var nodes = Array.prototype.slice.call(
      document.querySelectorAll('[class*="ptxnotn-"]'));
    if (!nodes.length) return;

    var pop = document.createElement("div");
    pop.className = "notation-popup";
    document.body.appendChild(pop);
    var hideTimer, showTimer;

    // Moving the mouse INTO the popup keeps it open (it contains a link).
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
    nodes.forEach(function (el) {
      var delay = isFar(el) ? FAR_DELAY_MS : NEAR_DELAY_MS;
      el.setAttribute("tabindex", "0");        // keyboard-accessible
      el.addEventListener("mouseenter", function () {
        clearTimeout(hideTimer);
        clearTimeout(showTimer);
        showTimer = setTimeout(function () { show(el); }, delay);
      });
      el.addEventListener("mouseleave", scheduleHide);
      // keyboard focus: show promptly regardless of far/near (a11y)
      el.addEventListener("focus", function () { show(el); });
      el.addEventListener("blur", scheduleHide);
    });
  }

  // (3) Proof-local details tiers: when an open proof knowl contains
  //     higher-detail blocks, a button after its summary steps through the
  //     levels locally (independent of the global slider).
  function wireProofDetails() {
    var proofs = Array.prototype.slice.call(
      document.querySelectorAll("details.hiddenproof"));
    proofs.forEach(function (proof) {
      var tiers = Array.prototype.slice.call(
        proof.querySelectorAll('details[class*="detail-level-"]'));
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
      summary.insertAdjacentElement("afterend", btn);
      var cur = 0;
      function nextLevel() {
        for (var i = 0; i < levels.length; i++)
          if (levels[i] > cur) return levels[i];
        return null;
      }
      function label() {
        btn.textContent = nextLevel() ? "▸ details" : "▾ hide details";
      }
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        var nxt = nextLevel();
        if (nxt) {
          cur = nxt;
          tiers.forEach(function (d) { if (levelOf(d) <= cur) d.open = true; });
        } else {
          cur = 0;
          tiers.forEach(function (d) { d.open = false; });
        }
        label();
      });
      label();
    });
  }

  ready(function () {
    buildSlider();
    wireProofDetails();
    afterMathJax(wireNotation);
  });
})();
