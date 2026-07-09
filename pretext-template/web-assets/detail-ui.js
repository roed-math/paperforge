/* PreTeXt spike: client-side UI layer.
   (1) A global detail slider that opens/closes born-hidden knowls by level.
   (2) Notation hovers that reveal a definition without a knowl underline. */
(function () {
  "use strict";

  // --- Notation registry. In the real tool this is generated from the
  //     document's <notation> list / a single source of truth. ---
  var NOTATION = {
    "Qp":  "The field \\(\\Qp\\) of \\(p\\)-adic numbers.",
    "Gq2": "The absolute Galois group \\(G_{\\mathbb{Q}_2}=\\operatorname{Gal}(\\overline{\\mathbb{Q}}_2/\\mathbb{Q}_2)\\)."
  };

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
    var hideTimer;

    function keyOf(el) {
      var m = /\bptxnotn-([A-Za-z0-9]+)\b/.exec(el.className);
      return m ? m[1] : null;
    }
    function show(el) {
      var k = keyOf(el);
      if (!k || !NOTATION[k]) return;
      clearTimeout(hideTimer);
      pop.innerHTML =
        '<span class="notation-popup-key">' + k + '</span>' + NOTATION[k];
      var r = el.getBoundingClientRect();
      // Place BELOW the symbol so the popup never covers the text being read.
      pop.style.top = (window.scrollY + r.bottom + 6) + "px";
      pop.style.left = (window.scrollX + r.left) + "px";
      pop.classList.add("show");
      if (window.MathJax && MathJax.typesetPromise) {
        MathJax.typesetPromise([pop]).catch(function () {});
      }
    }
    function hide() {
      hideTimer = setTimeout(function () { pop.classList.remove("show"); }, 80);
    }
    nodes.forEach(function (el) {
      el.setAttribute("tabindex", "0");        // keyboard-accessible
      el.addEventListener("mouseenter", function () { show(el); });
      el.addEventListener("mouseleave", hide);
      el.addEventListener("focus", function () { show(el); });
      el.addEventListener("blur", hide);
    });
  }

  ready(function () { buildSlider(); afterMathJax(wireNotation); });
})();
