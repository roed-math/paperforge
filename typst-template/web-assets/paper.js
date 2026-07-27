/* paperforge — Typst HTML backend behaviour.
 *
 * Everything here reads data attributes that the Typst library stamped at
 * compile time. The one authored `#detail(2)[..]` call became
 * `<details data-detail-level="2">`; this file is the other half of the
 * bargain the PDF side settles with `--input detail=2`.
 *
 * No dependencies, no build step, no MathJax: Typst emits MathML and the
 * browser lays the math out.
 */
(function () {
  "use strict";

  var STORE = "paperforge:prefs";

  function prefs() {
    try { return JSON.parse(localStorage.getItem(STORE)) || {}; } catch (e) { return {}; }
  }
  function savePref(key, value) {
    var p = prefs();
    p[key] = value;
    try { localStorage.setItem(STORE, JSON.stringify(p)); } catch (e) { /* private mode */ }
  }

  /* ------------------------------------------------------------------ */
  /* Detail tiers                                                        */
  /* ------------------------------------------------------------------ */

  var MAX_TIER = 1;

  function tierNodes() {
    return document.querySelectorAll("[data-detail-level]");
  }

  /* Apply a threshold: disclosures at or below it open, above it collapse.
   * Nothing is ever removed — a reader can always open a deeper tier by hand,
   * which is the whole advantage the HTML has over any single PDF. */
  function applyDetail(level) {
    tierNodes().forEach(function (el) {
      var tier = parseInt(el.getAttribute("data-detail-level"), 10);
      if (isNaN(tier)) return;
      if (el.tagName === "DETAILS") {
        el.open = tier <= level;
      } else {
        // Inline asides: hide rather than collapse.
        if (tier <= level) { el.removeAttribute("hidden"); }
        else { el.setAttribute("hidden", ""); }
      }
    });
    // `detail-upto` content is the complement: a summary that a reader who has
    // expanded the argument no longer needs.
    document.querySelectorAll("[data-detail-upto]").forEach(function (el) {
      var cap = parseInt(el.getAttribute("data-detail-upto"), 10);
      if (level <= cap) { el.removeAttribute("hidden"); }
      else { el.setAttribute("hidden", ""); }
    });
    var out = document.querySelector(".pf-detail-count");
    if (out) { out.textContent = level + " / " + MAX_TIER; }
    document.documentElement.setAttribute("data-detail-level", String(level));
  }

  function initDetail(toolbar) {
    var nodes = tierNodes();
    if (!nodes.length) return;
    nodes.forEach(function (el) {
      var t = parseInt(el.getAttribute("data-detail-level"), 10);
      if (!isNaN(t) && t > MAX_TIER) MAX_TIER = t;
      // Mirror the tier onto the <summary>: a CSS attr() in a ::after reads the
      // pseudo-element's OWN element, so putting it on the <details> renders
      // an empty badge.
      var summary = el.tagName === "DETAILS" ? el.querySelector(":scope > summary") : null;
      if (summary) summary.setAttribute("data-level", el.getAttribute("data-detail-level"));
    });

    // The preference is shared across papers, so a level saved on a document
    // with deeper tiers must be clamped or the slider reads "3 / 2".
    var saved = prefs().detail;
    var start = typeof saved === "number" ? saved : initialLevel();
    start = Math.max(0, Math.min(MAX_TIER, start));

    var label = document.createElement("label");
    label.innerHTML = '<span>detail</span>';
    var slider = document.createElement("input");
    slider.type = "range";
    slider.min = "0";
    slider.max = String(MAX_TIER);
    slider.step = "1";
    slider.value = String(start);
    slider.setAttribute("aria-label", "Detail level");
    var count = document.createElement("span");
    count.className = "pf-detail-count";
    label.appendChild(slider);
    label.appendChild(count);
    toolbar.appendChild(label);

    slider.addEventListener("input", function () {
      var v = parseInt(slider.value, 10);
      applyDetail(v);
      savePref("detail", v);
    });
    applyDetail(start);
  }

  /* The document's shipped default: whatever the Typst build marked open. */
  function initialLevel() {
    var open = 0;
    document.querySelectorAll("details[data-detail-level][open]").forEach(function (el) {
      var t = parseInt(el.getAttribute("data-detail-level"), 10);
      if (!isNaN(t) && t > open) open = t;
    });
    return open;
  }

  /* ------------------------------------------------------------------ */
  /* Notation hovers                                                     */
  /* ------------------------------------------------------------------ */

  function loadRegistry() {
    var node = document.getElementById("pf-notation-registry");
    if (!node) return {};
    try { return JSON.parse(node.textContent) || {}; } catch (e) { return {}; }
  }

  function initNotation() {
    var registry = loadRegistry();
    if (!Object.keys(registry).length) return;

    var popup = document.createElement("div");
    popup.className = "pf-notn-popup";
    popup.setAttribute("role", "tooltip");
    document.body.appendChild(popup);

    var timer = null, current = null;

    function hide() {
      window.clearTimeout(timer);
      popup.classList.remove("show");
      current = null;
    }

    function show(target) {
      var key = target.getAttribute("data-notn");
      var entry = registry[key];
      if (!entry) return;
      popup.innerHTML = entry.html || "";
      if (entry.href) {
        var a = document.createElement("a");
        a.href = entry.href;
        a.className = "pf-notn-context";
        a.textContent = "see definition in context ↗";
        popup.appendChild(document.createElement("br"));
        popup.appendChild(a);
      }
      // Position BELOW the symbol so it never covers the equation being read.
      var r = target.getBoundingClientRect();
      popup.style.left = Math.max(8, Math.min(
        window.innerWidth - popup.offsetWidth - 8,
        r.left + window.scrollX)) + "px";
      popup.style.top = (r.bottom + window.scrollY + 6) + "px";
      popup.classList.add("show");
      current = target;
    }

    /* Event delegation: markers live inside <details> that may not exist in the
     * DOM yet when a reader raises the detail level. */
    document.addEventListener("mouseover", function (ev) {
      var t = ev.target.closest ? ev.target.closest("[data-notn]") : null;
      if (!t || t === current) return;
      var far = t.classList.contains("pf-notn-far");
      window.clearTimeout(timer);
      timer = window.setTimeout(function () { show(t); }, far ? 500 : 200);
    });
    document.addEventListener("mouseout", function (ev) {
      var t = ev.target.closest ? ev.target.closest("[data-notn]") : null;
      if (t) hide();
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") hide();
    });
    window.addEventListener("scroll", hide, { passive: true });
  }

  /* ------------------------------------------------------------------ */
  /* Table of contents: scroll-spy                                       */
  /* ------------------------------------------------------------------ */

  function initToc() {
    var links = Array.prototype.slice.call(
      document.querySelectorAll(".pf-toc a[href^='#']"));
    if (!links.length) return;
    var byId = {};
    var targets = [];
    links.forEach(function (a) {
      var id = decodeURIComponent(a.getAttribute("href").slice(1));
      var el = document.getElementById(id);
      if (el) { byId[id] = a; targets.push(el); }
    });
    if (!targets.length) return;

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        var a = byId[e.target.id];
        if (!a) return;
        if (e.isIntersecting) {
          links.forEach(function (l) { l.classList.remove("pf-toc-current"); });
          a.classList.add("pf-toc-current");
        }
      });
    }, { rootMargin: "0px 0px -75% 0px", threshold: 0 });
    targets.forEach(function (t) { observer.observe(t); });
  }

  /* ------------------------------------------------------------------ */
  /* Theme                                                               */
  /* ------------------------------------------------------------------ */

  function initTheme(toolbar) {
    var saved = prefs().theme;
    if (saved) document.documentElement.setAttribute("data-theme", saved);
    var btn = document.createElement("button");
    btn.type = "button";
    btn.setAttribute("aria-label", "Toggle dark mode");
    function paint() {
      var dark = document.documentElement.getAttribute("data-theme") === "dark" ||
        (!document.documentElement.getAttribute("data-theme") &&
          window.matchMedia("(prefers-color-scheme: dark)").matches);
      btn.textContent = dark ? "☀" : "☽";
    }
    btn.addEventListener("click", function () {
      var dark = document.documentElement.getAttribute("data-theme") === "dark" ||
        (!document.documentElement.getAttribute("data-theme") &&
          window.matchMedia("(prefers-color-scheme: dark)").matches);
      var next = dark ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      savePref("theme", next);
      paint();
    });
    paint();
    toolbar.appendChild(btn);
  }

  /* ------------------------------------------------------------------ */

  function init() {
    var toolbar = document.createElement("div");
    toolbar.className = "pf-toolbar";
    document.body.appendChild(toolbar);

    initDetail(toolbar);
    initTheme(toolbar);
    initNotation();
    initToc();

    if (!toolbar.children.length) toolbar.remove();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
