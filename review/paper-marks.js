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
    { key: 'notation-remove', icon: '⊘', label: 'Remove notation link',
      color: '#64748b',
      help: 'click a notation link that should go away, or a previous ' +
            'notation mark (purple dot) to retract it' },
    { key: 'terminology', icon: 'T',  label: 'Terminology link',
      color: '#4338ca',
      help: 'select a phrase that should link to its background material ' +
            '(drag across it, even over line breaks)' },
    { key: 'background',  icon: '📖', label: 'Background needed',
      color: '#0f766e',
      help: 'click or select material that deserves a background ' +
            'write-up (global or section-local background)' },
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
  function submit(info, targetEl) {
    fetch('/api/mark', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(Object.assign({ mode: active, page }, info)),
    }).then(r => r.json()).then(d => {
      if (d.created === false) {
        toast(`already marked: “${info.text || '(here)'}”`);
        return;
      }
      placeDot(targetEl, active, info.text, d.id);
      toast(`${BY_KEY[active].label}: “${info.text || '(here)'}”`);
      refreshCount();
    });
  }

  function retract(dot) {
    const id = dot.dataset.markId;
    fetch('/api/mark-delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    }).then(r => r.json()).then(d => {
      if (d.ok) { dot.remove(); toast(`retracted ${id}`); refreshCount(); }
      else toast(`${id} is not open — manage it in the dashboard`);
    });
  }

  // phrase marks: releasing a selection while a pen is active marks the
  // selected phrase (works across line/element boundaries — the natural
  // gesture for terminology and background material)
  let selectionMark = false;
  document.addEventListener('mouseup', ev => {
    if (!active) return;
    if (ev.target.closest('#mark-palette, #margin-strip, .margin-panel'))
      return;
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed) return;
    const range = sel.getRangeAt(0);
    let node = range.commonAncestorContainer;
    if (node.nodeType === 3) node = node.parentElement;
    if (!node.closest('.ptx-content')) return;
    const text = String(sel).replace(/\s+/g, ' ').trim().slice(0, 200);
    if (!text) return;
    selectionMark = true;               // swallow the click that follows
    setTimeout(() => { selectionMark = false; }, 0);
    submit(Object.assign(anchorsOf(node), {
      text, context: contextOf(node),
    }), node);
  }, true);

  document.addEventListener('click', ev => {
    if (!active || selectionMark) return;
    if (ev.target.closest('#mark-palette, #margin-strip, .margin-panel'))
      return;
    const content = ev.target.closest('.ptx-content');
    if (!content) return;
    ev.preventDefault();
    ev.stopPropagation();

    const dot = ev.target.closest('.mark-dot');
    if (active === 'notation-remove') {
      // retract a previous notation suggestion, or request unwrapping of
      // an existing (rendered) notation link — idempotent otherwise
      if (dot && dot.dataset.mode === 'notation') return retract(dot);
      if (dot) return toast('that mark is not a notation mark');
      if (!ev.target.closest('[class*="ptxnotn-"]'))
        return toast('no notation link here to remove');
    } else if (dot) {
      return;                           // dots are never re-marked
    } else if (active === 'notation'
               && ev.target.closest('[class*="ptxnotn-"]')) {
      return toast('already has a notation link');
    }
    submit(capture(ev), ev.target);
  }, true);

  function anchorsOf(el) {
    let anchor = '', block = '';
    for (; el; el = el.parentElement) {
      if (el.id) {
        if (!anchor) anchor = el.id;
        if (!/^p-/.test(el.id)) { block = el.id; break; }
      }
    }
    return { anchor, block };
  }

  function contextOf(el) {
    const para = el.closest('p, li, .para') || el;
    return (para.textContent || '').replace(/\s+/g, ' ').slice(0, 200);
  }

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
    return Object.assign(anchorsOf(ev.target), {
      text, context: contextOf(ev.target),
    });
  }

  // ------------------------------------------------------------- display
  function placeDot(target, mode, text, id) {
    const dot = document.createElement('span');
    dot.className = 'mark-dot';
    dot.dataset.markId = id;
    dot.dataset.mode = mode;
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
