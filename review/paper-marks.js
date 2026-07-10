// Click-to-mark review layer (injected by review_server on /paper/* pages).
// A margin palette selects what a click means; clicks register author
// intents into directives/marks.json via POST /api/mark. Existing open
// marks are re-displayed as colored dots at their anchors.
(function () {
  'use strict';

  const MODES = [
    { key: 'notation',    icon: '?',  label: 'Notation link',
      color: '#7c3aed',
      help: 'click a term or symbol that needs a hover definition' },
    { key: 'reference',   icon: '[ ]', label: 'Reference needed',
      color: '#b45309',
      help: 'click where a citation should be added' },
    { key: 'detail-high', icon: '▲', label: 'Too much detail',
      color: '#be123c',
      help: 'click prose that should move down to a higher detail level' },
    { key: 'detail-low',  icon: '▼', label: 'Needs more detail',
      color: '#0369a1',
      help: 'click where more explanation is wanted' },
  ];
  const BY_KEY = Object.fromEntries(MODES.map(m => [m.key, m]));
  const page = location.pathname.split('/').pop() || 'paper.html';
  let active = null;

  // ------------------------------------------------------------- styles
  const css = document.createElement('style');
  css.textContent = `
    #mark-palette { position: fixed; right: .6rem; top: 40%; z-index: 4000;
      display: flex; flex-direction: column; gap: .3rem; background: #fff;
      border: 1px solid #ccc; border-radius: 6px; padding: .35rem;
      box-shadow: 0 1px 4px rgba(0,0,0,.15); font-size: .8rem; }
    #mark-palette button { width: 2rem; height: 2rem; border: 1px solid #ddd;
      border-radius: 4px; background: #fafafa; cursor: pointer;
      font-size: .85rem; line-height: 1; padding: 0; }
    #mark-palette button.active { color: #fff; border-color: transparent; }
    #mark-palette .mark-count { text-align: center; color: #666;
      font-size: .7rem; }
    body.marking .ptx-content { cursor: crosshair; }
    body.marking .ptx-content a { cursor: crosshair; }
    .mark-dot { display: inline-block; width: .6em; height: .6em;
      border-radius: 50%; margin: 0 .1em; vertical-align: super;
      cursor: help; }
    #mark-toast { position: fixed; bottom: 1rem; right: 1rem; z-index: 4001;
      background: #333; color: #fff; padding: .4rem .8rem; border-radius: 4px;
      font-size: .85rem; opacity: 0; transition: opacity .3s; }
    #mark-toast.show { opacity: 1; }`;
  document.head.appendChild(css);

  // ------------------------------------------------------------- palette
  const pal = document.createElement('div');
  pal.id = 'mark-palette';
  pal.title = 'Review pens: pick what a click means, then click in the text';
  const offBtn = mkBtn('✕', 'Pen off', () => setMode(null));
  pal.appendChild(offBtn);
  const btns = {};
  for (const m of MODES) {
    btns[m.key] = mkBtn(m.icon, `${m.label} — ${m.help}`,
                        () => setMode(active === m.key ? null : m.key));
    pal.appendChild(btns[m.key]);
  }
  const count = document.createElement('div');
  count.className = 'mark-count';
  pal.appendChild(count);
  document.body.appendChild(pal);

  function mkBtn(txt, title, fn) {
    const b = document.createElement('button');
    b.textContent = txt;
    b.title = title;
    b.addEventListener('click', fn);
    return b;
  }

  function setMode(key) {
    active = key;
    document.body.classList.toggle('marking', !!key);
    for (const m of MODES) {
      const on = m.key === key;
      btns[m.key].classList.toggle('active', on);
      btns[m.key].style.background = on ? m.color : '';
    }
  }

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && active) setMode(null);
  });

  // ------------------------------------------------------------- capture
  document.addEventListener('click', ev => {
    if (!active) return;
    if (ev.target.closest('#mark-palette, #margin-strip, .margin-panel'))
      return;
    const content = ev.target.closest('.ptx-content');
    if (!content) return;
    ev.preventDefault();
    ev.stopPropagation();
    const info = capture(ev);
    fetch('/api/mark', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(Object.assign({ mode: active, page }, info)),
    }).then(r => r.json()).then(d => {
      placeDot(ev.target, active, info.text, d.id);
      toast(`${BY_KEY[active].label}: “${info.text || '(here)'}”`);
      refreshCount();
    });
  }, true);

  function capture(ev) {
    let text = String(window.getSelection() || '').trim();
    const mjx = ev.target.closest('mjx-container');
    if (!text && mjx) text = (mjx.textContent || '').trim().slice(0, 80);
    if (!text) {
      const r = document.caretRangeFromPoint
        ? document.caretRangeFromPoint(ev.clientX, ev.clientY) : null;
      if (r && r.startContainer.nodeType === 3) {
        const s = r.startContainer.textContent, i = r.startOffset;
        const a = s.slice(0, i).search(/\S+$/);
        const b = s.slice(i).search(/[\s.,;:)]|$/);
        text = s.slice(a < 0 ? i : a, i + (b < 0 ? 0 : b)).trim();
      }
    }
    let anchor = '', block = '';
    for (let el = ev.target; el; el = el.parentElement) {
      if (el.id) {
        if (!anchor) anchor = el.id;
        if (!/^p-/.test(el.id)) { block = el.id; break; }
      }
    }
    const para = ev.target.closest('p, li') || ev.target;
    const context = (para.textContent || '').replace(/\s+/g, ' ')
      .slice(0, 200);
    return { text, context, anchor, block };
  }

  // ------------------------------------------------------------- display
  function placeDot(target, mode, text, id) {
    const dot = document.createElement('span');
    dot.className = 'mark-dot';
    dot.style.background = (BY_KEY[mode] || {}).color || '#666';
    dot.title = `${(BY_KEY[mode] || {}).label || mode}: ${text} (${id})`;
    target.insertAdjacentElement('afterend', dot);
  }

  function toast(msg) {
    let t = document.getElementById('mark-toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'mark-toast';
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 1800);
  }

  function refreshCount() {
    fetch('/api/marks').then(r => r.json()).then(list => {
      count.textContent = list.length ? `${list.length}` : '';
      count.title = `${list.length} open mark(s) — manage in the ` +
                    `dashboard's Review marks tab`;
    });
  }

  // existing open marks on this page
  fetch(`/api/marks?page=${encodeURIComponent(page)}`)
    .then(r => r.json())
    .then(list => {
      for (const m of list) {
        const el = document.getElementById(m.anchor) ||
                   document.getElementById(m.block);
        if (el) placeDot(el.querySelector('.heading') || el,
                         m.mode, m.text, m.id);
      }
    });
  refreshCount();
})();
