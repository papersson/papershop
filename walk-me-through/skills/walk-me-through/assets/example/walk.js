/* walk.js: the walk-me-through engine. One file, no dependencies, opens from disk.
 * Every page keeps its own copy, so a page goes on working when the skill changes.
 *
 * THE PAGE FORMAT (the contract). A page loads walk.css and walk.js, then calls Walk.page(def) once:
 *
 *   { title, chapters: [string], objects: { id: object }, clicks: [click],
 *     cover?: bool | string, notes?: [string per chapter] }
 *
 *   object: { piece: 'text' | 'chip' | 'card' | 'tree' | 'code' | <custom>, ...piece data,
 *             states: { name: { x, y, s, o, cls: [class] } }, start?: name, ch?: [chapters] }
 *   click:  { chapter, caption?, object, state, highlight?: selector | false, settle?: ms }
 *        or { chapter, caption?, clear: true, keep?: [ids] }
 *
 * Chapters are numbered from 1. x and y place an object's top left corner on a fixed 1600 by 900
 * stage (s scales it from that corner, o is opacity); cls are classes its piece's CSS reacts to.
 *
 * The model: the state at click N is the start state plus clicks 1 to N applied in order. It is
 * computed once, so #7 opens click 7 finished, Next animates one change and Back plays it in reverse.
 * - An object without `start` begins hidden at the position of its first click's state, so that
 *   click fades it in place.
 * - An object with `ch` is hidden outside those chapters without spending a click. Objects that
 *   appear as a chapter opens wait for the old ones to fade.
 * - A `clear` click hides every object not in `keep`. A later click on one shows it again.
 * - The highlight ring goes on the changed object, or on `highlight` (looked up inside the object,
 *   then on the whole stage), after `settle` ms. `highlight: false` skips it.
 * - Backticks in captions and labels become monospace. Everything else is escaped.
 *
 * Moving: arrow keys, space, Page Up and Down, Home, End, or a click on the stage (shift-click goes
 * back). C hides captions, N shows the chapter's speaker notes.
 *
 * Query modes for the scripts: ?check writes a JSON report into <pre id="walk-report">; ?mid=N&at=ms
 * plays click N and freezes every animation at `at` ms; ?strip lays every click out as small
 * multiples; ?still turns motion off. A page error lands on the screen, and in the report.
 *
 * A custom piece: Walk.piece(name, (el, object, page) => { render once into el; optionally return
 * update(cls) }). It then reacts only to state classes, so it stays one object for the one-change rule.
 */
(function () {
  'use strict';
  const W = 1600, H = 900, MOVE = 900, FADE = 500, TURN = 500, CAPTION_FADE = 180;
  const pieces = {};
  const query = new URLSearchParams(location.search);
  const mode = query.has('check') ? 'check' : query.has('mid') ? 'mid' : query.has('strip') ? 'strip' : 'live';
  const errors = [];
  let called = false;

  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const fmt = s => String(s == null ? '' : s).split('`').map((part, i) => i % 2 ? '<code>' + esc(part) + '</code>' : esc(part)).join('');
  const make = (tag, cls, parent, html) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    if (parent) parent.appendChild(e);
    return e;
  };

  function report(data) {
    let pre = document.getElementById('walk-report');
    if (!pre) { pre = make('pre', '', document.body); pre.id = 'walk-report'; pre.hidden = true; }
    pre.textContent = JSON.stringify(data);
  }
  function showError(message) {
    errors.push(message);
    if (mode === 'check') { report({ errors }); return; }
    const box = document.getElementById('walk-error') || make('div', '', document.body);
    box.id = 'walk-error';
    box.textContent = errors.join('\n');
  }
  window.addEventListener('error', e => showError(e.message || String(e.error)));
  window.addEventListener('unhandledrejection', e => showError(String(e.reason)));
  window.addEventListener('load', () => setTimeout(() => {
    if (!called && !errors.length) showError('Walk.page was never called: check the page script.');
  }, 0));

  function page(def) {
    called = true;
    try { build(def); } catch (e) { showError(e.message); }
  }

  // Validate the definition and compute every click's finished state.
  function plan(def) {
    const fail = m => { throw new Error(m); };
    if (!def || !Array.isArray(def.chapters) || !def.chapters.length) fail('page needs chapters: [string, ...]');
    if (!Array.isArray(def.clicks) || !def.clicks.length) fail('page needs clicks: [click, ...]');
    const objects = def.objects || {}, ids = Object.keys(objects), nch = def.chapters.length;
    const inRange = c => Number.isInteger(c) && c >= 1 && c <= nch;
    const known = `known objects: ${ids.join(', ') || 'none'}`;
    ids.forEach(id => {
      const o = objects[id];
      if (!pieces[o.piece]) fail(`object '${id}' uses unknown piece '${o.piece}'; pieces: ${Object.keys(pieces).join(', ')}`);
      if (!o.states || !Object.keys(o.states).length) fail(`object '${id}' has no states`);
      if (o.start != null && !o.states[o.start]) fail(`object '${id}' starts in unknown state '${o.start}'`);
      (o.ch || []).forEach(c => inRange(c) || fail(`object '${id}' names chapter ${c}, but there are ${nch}`));
    });
    let last = 0;
    def.clicks.forEach((c, i) => {
      const n = i + 1;
      if (!inRange(c.chapter)) fail(`click ${n} has chapter ${c.chapter}; chapters run from 1 to ${nch}`);
      if (c.chapter < last) fail(`click ${n} goes back from chapter ${last} to ${c.chapter}`);
      last = c.chapter;
      if (c.clear) {
        (c.keep || []).forEach(k => objects[k] || fail(`click ${n} keeps unknown object '${k}'; ${known}`));
        return;
      }
      const o = objects[c.object];
      if (!o) fail(`click ${n} names unknown object '${c.object}'; ${known}`);
      if (!o.states[c.state]) fail(`click ${n}: object '${c.object}' has no state '${c.state}'; its states: ${Object.keys(o.states).join(', ')}`);
    });
    for (let ch = 1; ch <= nch; ch++) if (!def.clicks.some(c => c.chapter === ch)) fail(`chapter ${ch} has no clicks`);

    const full = (o, name) => Object.assign({ x: 0, y: 0, s: 1, o: 1, cls: [] }, o.states[name]);
    const cur = {};
    ids.forEach(id => {
      const o = objects[id];
      if (o.start != null) cur[id] = { state: o.start, shown: true };
      else {
        const first = def.clicks.find(c => c.object === id);
        cur[id] = { state: first ? first.state : Object.keys(o.states)[0], shown: false };
      }
    });
    const snap = (chapter, cause) => {
      const out = {};
      ids.forEach(id => {
        const o = objects[id], st = full(o, cur[id].state);
        const inCh = chapter > 0 && (!o.ch || o.ch.includes(chapter));
        out[id] = { x: st.x, y: st.y, s: st.s, cls: st.cls, o: cur[id].shown && inCh ? st.o : 0 };
      });
      return Object.assign({ chapter, objects: out }, cause);
    };
    const frames = [snap(def.cover ? 0 : def.clicks[0].chapter, { caption: '' })];
    def.clicks.forEach((c, i) => {
      if (c.clear) ids.forEach(id => { if (!(c.keep || []).includes(id)) cur[id].shown = false; });
      else cur[c.object] = { state: c.state, shown: true };
      frames.push(snap(c.chapter, { caption: c.caption || '', click: c, n: i + 1 }));
    });
    // What each click changed, apart from what its chapter turn or a clear hid for free.
    frames.forEach((f, p) => {
      if (!p) return;
      const prev = frames[p - 1].objects;
      f.changed = []; f.hidden = [];
      ids.forEach(id => {
        const a = prev[id], b = f.objects[id];
        if (a.o === 0 && b.o === 0) return;
        const same = a.x === b.x && a.y === b.y && a.s === b.s && a.o === b.o && a.cls.join(' ') === b.cls.join(' ');
        if (same) return;
        const freeHide = b.o === 0 && a.o > 0 && (f.click.clear || (objects[id].ch && !objects[id].ch.includes(f.chapter)));
        (freeHide ? f.hidden : f.changed).push(id);
      });
    });
    return frames;
  }

  function build(def) {
    const frames = plan(def), N = def.clicks.length, first = def.cover ? 0 : 1;
    document.title = def.title || document.title;
    const root = make('div', 'walk', document.body);
    const reduced = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)');
    const alwaysStill = () => mode !== 'live' || query.has('still') || (reduced && reduced.matches);
    if (mode !== 'mid' && alwaysStill()) root.classList.add('w-still');
    const stage = make('div', 'w-stage', root);
    const title = make('div', 'w-title', stage);
    const cover = make('div', 'w-cover', stage, fmt(typeof def.cover === 'string' ? def.cover : def.title));
    const ring = make('div', 'w-ring', stage);
    const caption = make('div', 'w-caption', stage);
    const count = make('div', 'w-count', stage);
    const notes = make('aside', 'w-notes', root);
    const api = { def, stage, fmt, esc, make, W, H };

    const els = {}, updates = {}, base = {};
    Object.keys(def.objects || {}).forEach(id => {
      const o = def.objects[id];
      const el = make('div', `w-obj w-${o.piece}`, stage);
      el.dataset.id = id;
      const upd = pieces[o.piece](el, o, api);
      els[id] = el; base[id] = el.className;
      if (typeof upd === 'function') {
        updates[id] = upd;
        // Try every state now, so a bad path or token fails on load instead of at click 17.
        Object.keys(o.states).forEach(s => upd(o.states[s].cls || []));
      }
    });

    let pos = first, captionsOn = true, notesOn = false, ringTimer = 0, captionTimer = 0, titleTimer = 0;

    function fit() {
      const side = notesOn ? notes.offsetWidth : 0;
      const w = innerWidth - side, h = innerHeight, k = Math.min(w / W, h / H);
      stage.style.transform = `translate(${(w - W * k) / 2}px, ${(h - H * k) / 2}px) scale(${k})`;
      api.scale = k;
    }

    function ringTarget(f) {
      const c = f.click;
      if (!c || c.clear || c.highlight === false) return null;
      const el = els[c.object];
      if (!c.highlight) return el;
      return el.querySelector(c.highlight) || stage.querySelector(c.highlight);
    }
    function placeRing(f) {
      const t = ringTarget(f);
      if (!t || f.objects[f.click.object].o === 0) { ring.classList.remove('on'); return; }
      // Snug vertically, so a ring on one row of a tree or code does not cover the next.
      const s = stage.getBoundingClientRect(), r = t.getBoundingClientRect(), k = api.scale || 1, px = 10, py = 5;
      Object.assign(ring.style, {
        left: (r.left - s.left) / k - px + 'px', top: (r.top - s.top) / k - py + 'px',
        width: r.width / k + 2 * px + 'px', height: r.height / k + 2 * py + 'px',
      });
      ring.classList.add('on');
    }

    function swap(el, html, animate, timer) {
      if (el.dataset.html === html) return timer;
      el.dataset.html = html;
      clearTimeout(timer);
      if (!animate) { el.innerHTML = html; el.classList.remove('out'); return 0; }
      el.classList.add('out');
      return setTimeout(() => { el.innerHTML = html; el.classList.toggle('out', !html); }, CAPTION_FADE);
    }

    // Put frame p on the stage. `from` is the frame it moves from when animating.
    function show(p, from, animate) {
      const f = frames[p], prev = from == null ? null : frames[from];
      const turn = animate && prev && prev.chapter !== f.chapter;
      Object.keys(els).forEach(id => {
        const el = els[id], st = f.objects[id];
        const appearing = prev && prev.objects[id].o === 0 && st.o > 0;
        el.style.transitionDelay = turn && appearing ? TURN + 'ms' : '0ms';
        el.style.transform = `translate(${st.x}px, ${st.y}px) scale(${st.s})`;
        el.style.opacity = st.o;
        el.className = base[id] + (st.cls.length ? ' ' + st.cls.join(' ') : '') + (st.o === 0 ? ' w-gone' : '');
        if (updates[id]) updates[id](st.cls);
      });
      stage.classList.toggle('on-cover', f.chapter === 0);
      titleTimer = swap(title, f.chapter ? fmt(def.chapters[f.chapter - 1]) : '', animate && turn, titleTimer);
      captionTimer = swap(caption, fmt(f.caption), animate, captionTimer);
      count.textContent = p ? `${p}/${N}` : '';
      notes.innerHTML = notesFor(f.chapter);
      clearTimeout(ringTimer);
      ring.classList.remove('on');
      if (!animate) { placeRing(f); return; }
      const settle = f.click && f.click.settle != null ? f.click.settle : MOVE + (turn ? TURN : 0) + 80;
      ringTimer = setTimeout(() => placeRing(f), settle);
    }
    function notesFor(ch) {
      const text = ch && def.notes && def.notes[ch - 1];
      return text ? String(text).split(/\n\s*\n/).map(t => `<p>${fmt(t)}</p>`).join('') : '<p class="w-none">No notes for this chapter.</p>';
    }
    function jump(p) {
      root.classList.add('w-still');
      show(p, null, false);
      void stage.offsetHeight;
      if (!alwaysStill()) root.classList.remove('w-still');
    }
    function go(p) {
      p = Math.max(first, Math.min(N, p));
      if (p === pos) return;
      const from = pos;
      pos = p;
      if (Math.abs(p - from) === 1 && !alwaysStill()) show(p, from, true); else jump(p);
      history.replaceState(null, '', '#' + p);
    }
    const fromHash = () => { const n = parseInt(location.hash.slice(1), 10); return Number.isFinite(n) ? n : first; };

    if (mode === 'check') return runCheck(def, frames, { root, stage, title, caption, count, cover, ring, els, show, fit, ringTarget });
    if (mode === 'strip') return runStrip(def, frames, { root, stage, caption, show, first });

    fit();
    addEventListener('resize', fit);
    if (mode === 'mid') {
      const n = Math.max(1, Math.min(N, parseInt(query.get('mid'), 10) || 1)), at = parseFloat(query.get('at')) || MOVE / 2;
      root.classList.add('w-still');
      show(n - 1, null, false);
      void stage.offsetHeight;
      root.classList.remove('w-still');
      show(n, n - 1, true);
      clearTimeout(captionTimer); clearTimeout(ringTimer);
      caption.innerHTML = fmt(frames[n].caption); caption.classList.toggle('out', at < CAPTION_FADE);
      document.getAnimations().forEach(a => { a.pause(); a.currentTime = at; });
      const turn = frames[n - 1].chapter !== frames[n].chapter;
      const c = frames[n].click, settle = c.settle != null ? c.settle : MOVE + (turn ? TURN : 0) + 80;
      if (at >= settle) placeRing(frames[n]);
      return;
    }
    pos = Math.max(first, Math.min(N, fromHash()));
    jump(pos);
    addEventListener('hashchange', () => go(fromHash()));
    addEventListener('keydown', e => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const k = e.key;
      if (k === 'ArrowRight' || k === 'ArrowDown' || k === 'PageDown' || (k === ' ' && !e.shiftKey)) go(pos + 1);
      else if (k === 'ArrowLeft' || k === 'ArrowUp' || k === 'PageUp' || (k === ' ' && e.shiftKey)) go(pos - 1);
      else if (k === 'Home') go(first);
      else if (k === 'End') go(N);
      else if (k === 'c' || k === 'C') { captionsOn = !captionsOn; root.classList.toggle('no-captions', !captionsOn); return; }
      else if (k === 'n' || k === 'N') { notesOn = !notesOn; root.classList.toggle('notes-on', notesOn); fit(); return; }
      else return;
      e.preventDefault();
    });
    root.addEventListener('click', e => { if (!notes.contains(e.target)) go(pos + (e.shiftKey ? -1 : 1)); });
    if (reduced && reduced.addEventListener) reduced.addEventListener('change', () => root.classList.toggle('w-still', alwaysStill()));
  }

  // ?check: walk every click finished, measure the text on the stage, write the report.
  function runCheck(def, frames, v) {
    const N = def.clicks.length, first = def.cover ? 0 : 1;
    v.fit();
    const k = 1 / (v.stage.getBoundingClientRect().width / W);
    const sr = v.stage.getBoundingClientRect();
    const out = {
      title: def.title, clicks: N, cover: !!def.cover, chapters: def.chapters,
      viewport: [innerWidth, innerHeight], stageBox: [sr.left, sr.top, sr.width, sr.height],
      errors, frames: [], placeholders: Object.values(def.objects || {}).filter(o => o.placeholder).length,
      prose: [def.title, ...def.chapters, ...(def.notes || [])].filter(Boolean).map(String),
    };
    const visible = (el, stop) => {
      for (let e = el; e && e !== stop.parentNode; e = e.parentElement) {
        const cs = getComputedStyle(e);
        if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.05) return false;
      }
      return true;
    };
    const boxOf = node => {
      const range = document.createRange();
      range.selectNodeContents(node);
      const rs = [...range.getClientRects()].filter(r => r.width > 0 && r.height > 0);
      if (!rs.length) return null;
      const l = Math.min(...rs.map(r => r.left)), t = Math.min(...rs.map(r => r.top));
      const r = Math.max(...rs.map(r => r.right)), b = Math.max(...rs.map(r => r.bottom));
      return { x: (l - sr.left) * k, y: (t - sr.top) * k, w: (r - l) * k, h: (b - t) * k, lines: rs.length };
    };
    const textsIn = (el, owner) => {
      const found = [], walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      for (let n = walker.nextNode(); n; n = walker.nextNode()) {
        if (!n.nodeValue.trim() || !visible(n.parentElement, el)) continue;
        const box = boxOf(n);
        if (box) found.push(Object.assign(box, { owner, text: n.nodeValue.trim().slice(0, 40), code: !!n.parentElement.closest('code, .w-code, .w-mono, .w-chip-value, .w-tree-row') }));
      }
      return found;
    };
    const seen = new Set();
    for (let p = first; p <= N; p++) {
      v.show(p, null, false);
      void v.stage.offsetHeight;
      const f = frames[p], c = f.click || {};
      const texts = [];
      Object.keys(v.els).forEach(id => { if (f.objects[id].o > 0) texts.push(...textsIn(v.els[id], id)); });
      const chrome = [['title', v.title], ['caption', v.caption], ['count', v.count]];
      if (p === 0) chrome.push(['cover', v.cover]);
      chrome.forEach(([name, el]) => texts.push(...textsIn(el, name)));
      texts.forEach(t => { if (!t.code && t.owner !== 'count') seen.add(t.text); });
      const overlaps = [], outside = [], band = [];
      for (let i = 0; i < texts.length; i++) {
        const a = texts[i];
        if (a.owner !== 'caption' && (a.x < -1 || a.y < -1 || a.x + a.w > W + 1 || a.y + a.h > H + 1)) outside.push(`${a.owner} "${a.text}"`);
        const isObj = !['title', 'caption', 'count', 'cover'].includes(a.owner);
        if (isObj && a.y + a.h > 756 && a.y < 836) band.push(`${a.owner} "${a.text}"`);
        for (let j = i + 1; j < texts.length; j++) {
          const b = texts[j];
          const ix = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x), iy = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
          if (ix > 2 && iy > 2) overlaps.push(`${a.owner} "${a.text}" and ${b.owner} "${b.text}"`);
        }
      }
      const capBox = texts.find(t => t.owner === 'caption');
      const entry = {
        n: p, chapter: f.chapter, caption: f.caption, clear: !!c.clear, object: c.object || null, state: c.state || null,
        changed: f.changed || [], hidden: f.hidden || [], overlaps, outside, band,
        captionWidth: capBox ? Math.round(capBox.w) : 0,
      };
      if (p > 0 && !c.clear && c.highlight !== false && f.objects[c.object].o > 0) {
        const t = v.ringTarget(f);
        entry.ring = { selector: c.highlight || null, found: !!t, visible: !!t && visible(t, v.stage) };
      }
      out.frames.push(entry);
      if (f.caption) out.prose.push(String(f.caption));
    }
    out.prose.push(...seen);
    report(out);
  }

  // ?strip: every click's finished state as small multiples, captions underneath.
  function runStrip(def, frames, v) {
    const N = def.clicks.length;
    v.root.classList.add('w-strip-mode');
    const grid = make('div', 'w-strip', document.body);
    make('h1', 'w-strip-title', grid, fmt(def.title));
    const cells = make('div', 'w-strip-cells', grid);
    for (let p = v.first; p <= N; p++) {
      v.show(p, null, false);
      void v.stage.offsetHeight;
      const cell = make('figure', 'w-strip-cell', cells);
      const frame = make('div', 'w-strip-frame', cell);
      const clone = v.stage.cloneNode(true);
      clone.style.transform = 'scale(0.25)';
      clone.querySelectorAll('.w-caption, .w-count').forEach(e => e.remove());
      frame.appendChild(clone);
      make('figcaption', '', cell, `<b>${p ? p + '/' + N : 'cover'}</b> ${fmt(frames[p].caption)}`);
    }
    v.root.style.display = 'none';
  }

  /* ---------------- pieces ---------------- */

  // text: { text | html, size?, width?, align?, tone?: 'a'|'b'|'c'|'dim', verdict?: 'yes'|'no', mono? }
  pieces.text = (el, o) => {
    el.innerHTML = o.html != null ? o.html : fmt(o.text);
    if (o.size) el.style.fontSize = o.size + 'px';
    if (o.width) { el.style.width = o.width + 'px'; el.style.whiteSpace = 'normal'; }
    if (o.align) el.style.textAlign = o.align;
    if (o.tone) el.classList.add('tone-' + o.tone);
    if (o.verdict) el.classList.add('is-' + o.verdict);
    if (o.mono) el.classList.add('w-mono');
    if (o.placeholder) el.classList.add('is-placeholder');
  };

  // chip: { value, label?, tone? } one small named value that travels. Class 'no-label' fades its
  // label, for a chip that has docked in a card field that already names it.
  pieces.chip = (el, o) => {
    el.innerHTML = (o.label ? `<span class="w-chip-label">${fmt(o.label)}</span>` : '') +
      `<span class="w-chip-value">${fmt(o.value)}</span>`;
    if (o.tone) el.classList.add('tone-' + o.tone);
  };

  // card: { title, fields: [name], w?, labelWidth? } a named container. Objects move into a field by
  // taking the position Walk.slot(card, cardState, field) gives.
  const CARD = { head: 64, row: 56, pad: 24 };
  pieces.card = (el, o) => {
    const fields = o.fields || [], lw = o.labelWidth || 150;
    el.style.width = (o.w || 520) + 'px';
    el.style.height = CARD.head + fields.length * CARD.row + CARD.pad + 'px';
    make('div', 'w-card-title', el, fmt(o.title || ''));
    fields.forEach((f, i) => {
      const row = make('div', 'w-card-field', el);
      row.dataset.field = f;
      Object.assign(row.style, { top: CARD.head + i * CARD.row + 'px', width: lw + 'px' });
      make('span', '', row, fmt(f));
    });
  };
  const slot = (card, state, field) => {
    const st = card.states[state], i = (card.fields || []).indexOf(field);
    if (!st || i < 0) throw new Error(`Walk.slot: card has no state '${state}' or no field '${field}'`);
    return { x: (st.x || 0) + (card.labelWidth || 150) + 32, y: (st.y || 0) + CARD.head + i * CARD.row + 4 };
  };

  // tree: { data } (JSON) or { text } (protobuf text format), row?, indent?. Rows are addressed by
  // paths like order.item[1].qty. Classes: 'lit:PATH' lights a row, 'box:PATH' draws a dashed box,
  // 'at:PATH' puts the marker beside it (it glides from row to row).
  function protoText(src) {
    const toks = src.replace(/#[^\n]*/g, '').match(/"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|[{}<>:]|[^\s{}<>:]+/g) || [];
    let i = 0;
    const add = (obj, k, v) => {
      if (!(k in obj)) obj[k] = v;
      else { if (!Array.isArray(obj[k]) || !obj[k].__rep) { obj[k] = [obj[k]]; obj[k].__rep = true; } obj[k].push(v); }
    };
    const scalar = t => /^["']/.test(t) ? t.slice(1, -1) : /^-?\d+(\.\d+)?$/.test(t) ? Number(t) : t === 'true' ? true : t === 'false' ? false : t;
    const block = close => {
      const obj = {};
      while (i < toks.length && toks[i] !== close) {
        const key = toks[i++];
        if (toks[i] === ':') i++;
        if (toks[i] === '{' || toks[i] === '<') { const c = toks[i++] === '{' ? '}' : '>'; add(obj, key, block(c)); i++; }
        else add(obj, key, scalar(toks[i++]));
      }
      return obj;
    };
    return block(undefined);
  }
  pieces.tree = (el, o) => {
    const data = o.text != null ? protoText(o.text) : o.data, rowH = o.row || 40, ind = o.indent || 30;
    const rows = [];
    const walk = (val, path, label, depth, parent) => {
      if (Array.isArray(val)) { val.forEach((v, i) => walk(v, `${path}[${i}]`, `${label}[${i}]`, depth, parent)); return; }
      const me = rows.length;
      const isObj = val !== null && typeof val === 'object';
      rows.push({ path, label, depth, parent, value: isObj ? undefined : val });
      if (isObj) Object.keys(val).forEach(k => walk(val[k], path ? `${path}.${k}` : k, k, depth + 1, me));
    };
    Object.keys(data || {}).forEach(k => walk(data[k], k, k, 0, -1));
    const width = o.w || 520;
    Object.assign(el.style, { width: width + 'px', height: rows.length * rowH + 'px' });
    const svgNS = 'http://www.w3.org/2000/svg', svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('class', 'w-tree-lines');
    svg.setAttribute('width', width); svg.setAttribute('height', rows.length * rowH);
    let d = '';
    const byPath = {};
    rows.forEach((r, i) => {
      const left = 26 + r.depth * ind, row = make('div', 'w-tree-row', el);
      row.dataset.path = r.path;
      Object.assign(row.style, { top: i * rowH + 'px', left: left + 'px', height: rowH + 'px' });
      const v = r.value;
      const val = v === undefined ? '' : typeof v === 'string' ? `<span class="w-tree-v is-str">"${esc(v)}"</span>` : `<span class="w-tree-v">${esc(v)}</span>`;
      row.innerHTML = `<span class="w-tree-k">${esc(r.label)}</span>${v === undefined ? '' : '<span class="w-tree-p">:</span> ' + val}`;
      byPath[r.path] = { row, i };
      if (r.parent >= 0) {
        const px = 26 + rows[r.parent].depth * ind + 8, py = r.parent * rowH + rowH * 0.78, cy = i * rowH + rowH / 2;
        d += `M${px} ${py}V${cy}H${left - 6}`;
      }
    });
    const path = document.createElementNS(svgNS, 'path');
    path.setAttribute('d', d);
    svg.appendChild(path);
    el.insertBefore(svg, el.firstChild);
    const marker = make('div', 'w-tree-marker', el, '▸');
    return cls => {
      const pick = pre => cls.filter(c => c.startsWith(pre)).map(c => {
        const p = c.slice(pre.length);
        if (!byPath[p]) throw new Error(`tree: no row at '${p}'; rows: ${Object.keys(byPath).join(', ')}`);
        return p;
      });
      const lit = pick('lit:'), box = pick('box:'), at = pick('at:');
      Object.keys(byPath).forEach(p => {
        byPath[p].row.classList.toggle('is-lit', lit.includes(p));
        byPath[p].row.classList.toggle('is-box', box.includes(p));
      });
      if (at.length) {
        const r = byPath[at[0]];
        marker.style.transform = `translate(${parseFloat(r.row.style.left) - 24}px, ${r.i * rowH}px)`;
        marker.style.lineHeight = rowH + 'px';
      }
      marker.classList.toggle('on', at.length > 0);
    };
  };

  // code: { lines: [string | [mark, string]] } with marks in the margin. Classes 'lit:3' or 'lit:3-5'
  // light lines (counted from 1) and dim the rest.
  pieces.code = (el, o) => {
    const lines = (o.lines || []).map(l => Array.isArray(l) ? l : ['', l]);
    const rows = lines.map(([mark, text], i) => {
      const row = make('div', 'w-code-line', el);
      const hash = text.search(/(^|\s)(#|\/\/)/);
      const body = hash < 0 ? esc(text) : esc(text.slice(0, hash)) + `<span class="w-code-c">${esc(text.slice(hash))}</span>`;
      row.innerHTML = `<span class="w-code-m">${esc(mark)}</span><code>${body || ' '}</code>`;
      row.dataset.line = i + 1;
      return row;
    });
    el.classList.add('w-code');
    return cls => {
      const on = new Set();
      cls.filter(c => c.startsWith('lit:')).forEach(c => {
        const [a, b] = c.slice(4).split('-').map(Number);
        if (!(a >= 1 && (b || a) <= rows.length)) throw new Error(`code: no line ${c.slice(4)}; lines run 1 to ${rows.length}`);
        for (let n = a; n <= (b || a); n++) on.add(n);
      });
      rows.forEach((r, i) => r.classList.toggle('is-lit', on.has(i + 1)));
      el.classList.toggle('has-lit', on.size > 0);
    };
  };

  window.Walk = { page, piece: (name, render) => { pieces[name] = render; }, slot, fmt, esc, W, H };
})();
