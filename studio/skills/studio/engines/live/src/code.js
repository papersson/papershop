// Code performed from studio typing's recorded key stream. These components retain the
// eight-unit, centre-origin layout of the original code kit so an existing composition ports
// directly. Call Editor(c, props), not JSX. Other live drawing helpers still use pixels.
const INK = '#E6EBF0', MUTED = '#8C97A4', FAINT = '#56606B', ICE = '#8FD3FF';
const AMBER = '#F2A93B', CORAL = '#E4715F', PANEL = '#151B22', EDGE = '#C9D3DD';
const NS = 'http://www.w3.org/2000/svg';
const clamp = n => Math.max(0, Math.min(1, n));
const mix = (a, b, k) => '#' + [0, 1, 2].map(i => Math.round(parseInt(a.slice(1 + i * 2, 3 + i * 2), 16) * (1 - clamp(k)) + parseInt(b.slice(1 + i * 2, 3 + i * 2), 16) * clamp(k)).toString(16).padStart(2, '0')).join('');
const pt = (c, size) => size * c.unit * (1.82 / 135);
const point = (c, [x, y]) => [c.W / 2 + x * c.unit, c.H / 2 - y * c.unit];
const meansFor = (means, lit) => means ?? (lit ? 'kit' : undefined);
const whenAt = (w, cue) => w === undefined ? null : typeof w === 'string' ? cue(w) : cue(w[0]) + w[1];
const framesSince = (t, cue, fps, burst) => Math.round((t - cue(burst.cue)) * fps + 1e-6);

function rect(c, name, at, w, h, {fill = 'none', stroke = 'none', sw = 0, opacity = 1, radius = 0, means} = {}) {
  if (opacity <= 0) return;
  const [x, y] = point(c, at), width = w * c.unit, height = h * c.unit;
  c.S.rect(name, x - width / 2 + sw / 2, y - height / 2 + sw / 2, width - sw, height - sw,
    {fill, stroke, sw, r: radius * c.unit, op: opacity, box: name, means});
}
function panel(c, name, at, w, h, opacity) {
  rect(c, name, at, w, h, {fill: PANEL, stroke: EDGE, sw: 2, radius: .16, opacity});
}
function text(c, name, at, parts, {size = 20, color = INK, opacity = 1, anchor = 'left', means} = {}) {
  if (opacity <= 0) return;
  const [x, y] = point(c, at);
  const node = c.S.el(name, 'text', {x, y, fill: color, opacity, 'font-size': pt(c, size),
    'font-family': 'var(--mono)', 'font-weight': 400, 'text-anchor': {left: 'start', center: 'middle', right: 'end'}[anchor],
    'dominant-baseline': 'central', 'xml:space': 'preserve', style: 'white-space:pre', box: name, means, 'data-kind': 'text'});
  const spans = typeof parts === 'string' ? [{text: parts, color}] : parts;
  const signature = JSON.stringify(spans);
  if (node._codeText !== signature) {
    node.replaceChildren(...spans.map(p => {
      const span = document.createElementNS(NS, 'tspan');
      span.textContent = p.text.replace(/\t/g, '        '); span.setAttribute('fill', p.color ?? color); return span;
    }));
    node._codeText = signature;
  }
}
export function legibleSize(c, size, chars = 0, width = Infinity) {
  const px = pt(c, 1), fit = chars > 0 ? width * c.unit / (chars * .6 * px) : Infinity;
  return Math.max(18 / px, Math.min(size, fit));
}
const columns = s => s.replace(/\t/g, '        ').length;

/** Recorded source, with 1-based inclusive ranges, current line, plumbing and token markers. */
export function CodePanel(c, {at, w, source, range, current, plumbing = [], markers = {}, tokens = [], opacity = 1, size = 20, name = 'code', means}) {
  const lines = source.text.replace(/\r\n/g, '\n').split('\n');
  if (lines.at(-1) === '') lines.pop();
  const first = range?.[0] ?? 1, last = range?.[1] ?? lines.length, shown = lines.slice(first - 1, last);
  const sz = legibleSize(c, size, Math.max(0, ...shown.map(columns)), w - 1.2), lh = sz * .031;
  panel(c, name, at, w, shown.length * lh + .6, opacity);
  shown.forEach((line, i) => {
    const n = first + i, y = at[1] + (shown.length - 1) * lh / 2 - i * lh;
    const color = current === n ? ICE : plumbing.includes(n) ? MUTED : INK, parts = [];
    let offset = 0;
    for (const cue of tokens.filter(t => t.line === n && t.progress > 0)) {
      const pos = line.indexOf(cue.text, offset);
      if (pos < 0) continue;
      parts.push({text: line.slice(offset, pos), color}, {text: cue.text, color: mix(color, AMBER, cue.progress)});
      offset = pos + cue.text.length;
    }
    parts.push({text: line.slice(offset), color});
    text(c, name + ' line number ' + n, [at[0] - w / 2 + .2, y], markers[n] ?? String(n), {size: sz, color: current === n ? ICE : MUTED, opacity, means: meansFor(means, current === n)});
    text(c, name + ' line ' + n, [at[0] - w / 2 + 1, y], parts, {size: sz, color, opacity, means: meansFor(means, current === n)});
  });
}
const outputLines = s => s === '' ? [] : s.replace(/\r\n/g, '\n').replace(/\n$/, '').split('\n');
/** Captured argv/stdout/stderr/exit, revealed and scrolled without changing text size. */
export function Terminal(c, {at, w, runs, progress = 1, maxLines = 9, opacity = 1, size = 20, name = 'terminal', means}) {
  const lines = runs.flatMap(r => [{text: '$ ' + r.argv.join(' '), color: MUTED}, ...outputLines(r.stdout).map(text => ({text, color: INK})), ...outputLines(r.stderr).map(text => ({text, color: r.exit ? CORAL : MUTED}))]);
  const shown = lines.slice(0, Math.floor(lines.length * clamp(progress))).slice(-maxLines);
  const sz = legibleSize(c, size, Math.max(0, ...lines.map(l => columns(l.text))), w - .6), lh = sz * .031;
  panel(c, name, at, w, Math.max(1, shown.length) * lh + .6, opacity);
  shown.forEach((l, i) => text(c, name + ' row ' + i, [at[0] - w / 2 + .3, at[1] + (shown.length - 1) * lh / 2 - i * lh], l.text,
    {size: sz, color: l.color, opacity, means: meansFor(means, l.color === CORAL)}));
}

/** Pure replay: same burst, same frame, same buffer and caret, including the wrong text. */
export function editorAt(typing, ids, t, cue, fps) {
  if (!ids.length) throw new Error('Editor needs at least one typing burst');
  let pick = -1;
  ids.forEach((id, i) => {
    if (!typing[id]) throw new Error(`no burst ${id} in data/typing.json (studio typing writes it)`);
    if (framesSince(t, cue, fps, typing[id]) >= 0) pick = i;
  });
  const burst = typing[ids[Math.max(0, pick)]], started = pick >= 0, now = started ? framesSince(t, cue, fps, burst) : -1;
  const lines = burst.before.map(text => ({text, born: -1e6}));
  let caret = [Math.max(0, lines.length - 1), 0], mode = 'NORMAL', modeAt = -1e6, lastKey = -1e6;
  if (started) for (const [f, , fx] of burst.steps) {
    if (f > now) break;
    lastKey = f;
    for (const [k, a, b] of fx) {
      if (k === 'ins') lines.splice(a, 0, ...b.map(text => ({text, born: f})));
      else if (k === 'set') lines[a] = {...lines[a], text: b};
      else if (k === 'del') lines.splice(a, 1);
      else if (k === 'caret') caret = [a, b];
      else if (k === 'mode') {mode = a; modeAt = f;}
    }
  }
  if (!lines.length) lines.push({text: '', born: -1e6});
  return {lines, caret, mode, modeAt, lastKey, now, burst, started};
}
const KEYWORDS = 'int|float|double|char|bool|void|return|if|else|while|for|const|static|struct|true|false|def|fn|let|var|function|import|from|class|pub|use';
const TOKEN = new RegExp(`("[^"\\n]*"|'[^'\\n]*'|\\b(?:${KEYWORDS})\\b|\\b\\d+(?:\\.\\d+)?f?\\b|//.*$|#.*$)`, 'g');
function colour(part) {
  if (part.startsWith('//') || part.startsWith('#')) return FAINT;
  if (part.startsWith('"') || part.startsWith("'")) return mix(INK, AMBER, .45);
  if (/^\d/.test(part)) return AMBER;
  return new RegExp(`^(${KEYWORDS})$`).test(part) ? ICE : INK;
}
const syntax = line => line.split(TOKEN).filter(Boolean).map(part => ({text: part, color: colour(part)}));
function typedLine(line, col) {
  if (col === null || col !== line.length) return syntax(line || ' ');
  let s = col;
  while (s > 0 && /[\w."]/.test(line[s - 1])) s--;
  if ((line.slice(0, col).match(/"/g) ?? []).length % 2 === 1) s = Math.min(s, line.lastIndexOf('"', col - 1));
  return [...syntax(line.slice(0, s)), {text: line.slice(s, col), color: INK}];
}
/** The teaching view: collapsed intervals, folds, active line highlights and complete payoff. */
export function codeViewAt(lines, view = {}, t, cue, base = 0) {
  const open = !view.open?.length || view.open.some(([a, b]) => t >= whenAt(a, cue) && t < whenAt(b, cue));
  const complete = view.payoff !== undefined && t >= whenAt(view.payoff, cue);
  const folds = complete ? [] : (view.folds ?? []).filter(f => (f.from === undefined || t >= whenAt(f.from, cue)) && (f.to === undefined || t < whenAt(f.to, cue)));
  const lit = new Set();
  if (!complete) for (const h of view.highlights ?? []) if (t >= whenAt(h.from, cue) && (h.to === undefined || t < whenAt(h.to, cue))) for (let n = h.lines[0]; n <= h.lines[1]; n++) lit.add(n);
  const rows = [];
  for (let i = 0; i < lines.length; i++) {
    const fold = folds.find(f => f.lines[0] === i + 1 + base);
    rows.push({idx: i, text: fold ? fold.label : lines[i].text, fold: Boolean(fold)});
    if (fold) i += fold.lines[1] - fold.lines[0];
  }
  return {open, complete, rows, lit};
}
export function Editor(c, {typing, ids, at, w, rows = 14, size = 22, from = [], focus = [], title, opacity = 1, name = 'editor', means, view}) {
  const {t, cue} = c, fps = c.layout.fps ?? 30;
  const st = editorAt(typing, ids, t, cue, fps), base = (st.burst.first ?? 1) - 1;
  const projected = codeViewAt(st.lines, view, t, cue, base);
  if (!projected.open) {
    panel(c, name + ' collapsed', at, w, .6, opacity * .8);
    text(c, name + ' file', [at[0] - w / 2 + .3, at[1]], title || st.burst.file, {size: 16, color: MUTED, opacity: opacity * .8});
    return st;
  }
  const longest = Math.max(20, ...ids.flatMap(id => [...typing[id].after, ...typing[id].before]).map(columns));
  const sz = legibleSize(c, size, longest, w - 1.4), em = pt(c, sz) / c.unit, adv = em * .6, lh = em * 1.6;
  const bar = .55, h = rows * lh + bar * 2 + .2, top = at[1] + h / 2 - bar - .1, left = at[0] - w / 2;
  let first = 0;
  for (const needle of from) {const i = st.lines.findIndex(l => l.text.includes(needle)); if (i >= 0) {first = i; break;}}
  if (st.caret && st.caret[0] > first + rows - 2) first = st.caret[0] - rows + 2;
  first = Math.max(0, Math.min(first, st.lines.length - 1));
  const typingNow = st.started && st.now - st.lastKey < Math.round(.6 * fps) && st.now <= st.burst.end + 4;
  const insert = st.mode === 'INSERT', blink = typingNow ? 1 : Math.floor(t / .53) % 2 === 0 ? 1 : 0;
  const cmd = st.mode.startsWith('CMD:') ? st.mode.slice(4) : null, age = st.now - st.modeAt;
  const msg = /^(WRITTEN|MSG):/.test(st.mode) && age < 2.5 * fps ? st.mode.replace(/^(WRITTEN|MSG):/, '') : null;
  const written = st.mode.startsWith('WRITTEN:') ? clamp(1 - age / 8) : 0;
  const firstRow = Math.max(0, projected.rows.findIndex(r => r.idx >= first));
  panel(c, name, at, w, h, opacity);
  if (title !== undefined) text(c, name + ' file', [left + .3, at[1] + h / 2 - bar / 2], title || st.burst.file, {size: 16, color: MUTED, opacity});
  projected.rows.slice(firstRow, firstRow + rows).forEach((row, i) => {
    const n = row.idx, line = row.fold ? {text: row.text, born: -1e6} : st.lines[n], y = top - (i + .5) * lh;
    const caretHere = st.caret !== null && st.caret[0] === n && !cmd && !row.fold;
    const lit = typingNow && caretHere || !typingNow && (projected.lit.has(n + 1 + base) || focus.some(f => line.text.includes(f)));
    const grow = line.born > -1e5 ? clamp((st.now - line.born + 1) / 3) : 1;
    if (lit) rect(c, name + ' current line ' + n, [at[0], y], w - .1, lh, {fill: mix(PANEL, ICE, .12), opacity});
    text(c, name + ' line number ' + (n + 1 + base), [left + .85, y], String(n + 1 + base), {anchor: 'right', size: sz * .8, color: caretHere ? MUTED : FAINT, opacity: opacity * grow});
    text(c, name + ' line ' + (n + 1 + base), [left + 1.1, y], row.fold ? [{text: '\u25b8 ' + row.text + ' \u2026', color: MUTED}] : typedLine(line.text, insert && caretHere ? st.caret[1] : null),
      {size: sz, opacity: opacity * grow * ((focus.length || projected.lit.size) && !lit && !typingNow ? .62 : 1) * (row.fold ? .7 : 1), means: meansFor(means, lit)});
    if (caretHere) rect(c, name + ' caret', [left + 1.1 + st.caret[1] * adv + (insert ? .01 : adv / 2), y], insert ? .03 : adv, lh * .72, {fill: INK, opacity: opacity * blink * (insert ? .95 : .7)});
  });
  rect(c, name + ' mode line', [at[0], at[1] - h / 2 + bar / 2 + .05], w - .16, bar - .08, {radius: .08, fill: mix(PANEL, '#7FD18B', written * .25), opacity});
  text(c, name + ' mode', [left + .3, at[1] - h / 2 + bar / 2], cmd !== null ? cmd : msg ?? (insert ? '-- INSERT --' : 'NORMAL'), {size: 16, opacity, color: cmd !== null ? INK : msg ? '#7FD18B' : insert ? AMBER : MUTED});
  return st;
}
export function HelperCard(c, {view, id, at, w, opacity = 1, name = 'helper'}) {
  const h = view.helpers?.find(x => x.id === id);
  if (!h) throw new Error(`no helper ${id} in data/codeview.json`);
  const a = whenAt(h.from, c.cue), b = whenAt(h.to, c.cue), o = clamp((c.t - a) / .25) * clamp((b - c.t) / .25);
  if (o <= 0) return;
  panel(c, name, at, w, 1.5, opacity * o);
  text(c, name + ' title', [at[0] - w / 2 + .3, at[1] + .4], h.title, {size: 20, color: ICE, opacity: opacity * o});
  text(c, name + ' text', [at[0] - w / 2 + .3, at[1] - .2], h.text, {size: 18, opacity: opacity * o});
}
export function runAt(typing, ids, t, cue, fps) {
  let out = null;
  for (const id of ids) {
    const run = typing[id].run;
    if (!run) continue;
    const t0 = cue(typing[id].cue);
    if (t >= t0 + run.up / fps) out = {id, up: t0 + run.up / fps, enter: t0 + run.enter / fps, pop: t0 + run.pop / fps};
  }
  return out;
}
export function RunTerminal(c, {typing, ids, at, w, rows = 5, size = 17, opacity = 1, name = 'terminal'}) {
  const {t, cue} = c, fps = c.layout.fps ?? 30;
  let lines = [];
  for (const id of ids) {
    const b = typing[id]; if (!b.run) continue;
    const now = framesSince(t, cue, fps, b); if (now < b.run.up) continue;
    lines = [...lines.slice(-1), {text: b.run.cmd, color: INK}, ...b.run.log.filter(([f]) => now >= f).map(([, l]) => ({text: l, color: MUTED}))];
  }
  const r = runAt(typing, ids, t, cue, fps), tail = lines.slice(-rows), em = pt(c, size) / c.unit, lh = em * 1.5, h = rows * lh + .5;
  const blink = Math.floor(t / .53) % 2 === 0;
  panel(c, name, at, w, h, opacity);
  (tail.length ? tail : [{text: '$ ', color: INK}]).forEach((l, i) => text(c, name + ' row ' + i, [at[0] - w / 2 + .3, at[1] + h / 2 - .25 - (i + .5) * lh],
    l.text + (((r && t < r.enter && i === tail.length - 1) || !tail.length) && blink ? '\u258d' : ''), {size, color: l.color, opacity}));
}
export function windowMotion(t, enter, pop) {
  if (pop !== null && t >= pop) {
    const u = t - pop, scale = u < .1 ? .9 + .125 * Math.sin(u / .1 * Math.PI / 2) : 1 + .025 * Math.exp(-(u - .1) / .09) * Math.cos((u - .1) / .2 * Math.PI * 1.5);
    return {scale, opacity: clamp(u / .07)};
  }
  if (enter !== null && t >= enter) {const u = clamp((t - enter) / .13); return {scale: 1 - .04 * u, opacity: 1 - u};}
  return {scale: 1, opacity: 1};
}
/** draw(id, pop, context) paints the application's real result. context.window is its pixel box. */
export function ProgramWindow(c, {typing, ids, at, w, h, draw, children, name = 'program window'}) {
  const r = runAt(typing, ids, c.t, c.cue, c.layout.fps ?? 30);
  if (!r) return null;
  const opened = c.t >= r.pop, prev = ids.slice(0, ids.indexOf(r.id)).reverse().find(id => typing[id].run), id = opened ? r.id : prev;
  if (!id) return null;
  const m = opened ? windowMotion(c.t, null, r.pop) : windowMotion(c.t, r.enter, null);
  if (m.opacity <= 0) return null;
  const pop = opened ? r.pop : c.cue(typing[id].cue) + typing[id].run.pop / (c.layout.fps ?? 30);
  const [x, y] = point(c, [at[0] - w / 2, at[1] + h / 2]), width = w * c.unit, height = h * c.unit;
  const clipId = 'window-' + name.replace(/[^a-zA-Z0-9_-]/g, '-');
  let clip = c.S.svg.querySelector('#' + clipId);
  if (!clip) {clip = document.createElementNS(NS, 'clipPath'); clip.id = clipId; clip.appendChild(document.createElementNS(NS, 'rect')); c.S.svg.querySelector('defs').appendChild(clip);}
  for (const [k, v] of Object.entries({x, y, width, height})) clip.firstChild.setAttribute(k, v);
  const ox = x + width / 2, oy = y + height * .6;
  c.S.group(name, {opacity: m.opacity, transform: `translate(${ox} ${oy}) scale(${m.scale}) translate(${-ox} ${-oy})`, 'clip-path': `url(#${clipId})`, box: name},
    () => (draw ?? children)?.(id, pop, {...c, window: {x, y, w: width, h: height}}));
  return {id, pop, ...m};
}
