// Explaining overlays and product-page parts for the screens layer (references/screens.md).
//
// Overlays sit over the whole stage on the ui layer: the definition card (in several variants), the
// progress strip and the checklist. Page parts draw inside a box in world pixels, from data, so a
// dashboard shown in three chapters is drawn from one file and stays the same dashboard: a product
// frame with its reconstruction label, a time series, a table, a trace waterfall, a point plot with a
// drag selection, and a ranked list whose rows reorder.

import { ease } from '../../shared/motion.js'
import { LOOK } from './screens-draw.js'

const clamp = x => Math.max(0, Math.min(1, x))

/** Greedy word wrap: lines of at most `chars` characters. */
export function wrap(text, chars) {
  const out = []
  let line = ''
  for (const w of String(text).split(' ')) {
    if (line && (line + ' ' + w).length > chars) { out.push(line); line = w } else line = line ? line + ' ' + w : w
  }
  if (line) out.push(line)
  return out
}
/** Wrap, then narrow the measure while the line count holds: even lines, no lone last word. */
export function balanced(text, chars) {
  const n = wrap(text, chars).length
  let best = wrap(text, chars)
  for (let w = chars - 1; w >= 20; w--) { const l = wrap(text, w); if (l.length > n) break; best = l }
  return best
}

// ── The definition card ─────────────────────────────────────────────────────────────────────────
const CARD_IN = .7, CARD_OUT = .5
/** The variants defCard draws; each names a core idea the same way every time it is used. */
export const CARD_VARIANTS = ['blur', 'side', 'lower', 'spotlight', 'type']

/** The scene behind softened: a blurred copy of the camera layer replaces it while `soft` > 0. */
function soften(c, soft, H) {
  const S = c.S
  if (!(S.camera && S.svg)) return
  if (S._cardT !== c.t) { S._cardT = c.t; S._cardSoft = 0 }
  S._cardSoft = Math.max(S._cardSoft, soft)
  if (!S._soft) {
    // A frame without a card never stays blurred: every frame starts sharp, whichever scene draws it.
    const hider = S.make('g', S.svg); S.svg.insertBefore(hider, S.camera); hider.appendChild(S.camera)
    S.camera.setAttribute('id', 'stage-camera')
    const defs = S.svg.querySelector('defs') ?? S.make('defs', S.svg)
    const cp = S.make('clipPath', defs); cp.setAttribute('id', 'card-clip')
    const r = S.make('rect', cp)
    for (const [k, v] of Object.entries({ x: 0, y: 0, width: c.W, height: H })) r.setAttribute(k, v)
    const copy = S.make('use', S.svg); S.svg.insertBefore(copy, hider.nextSibling)
    copy.setAttribute('href', '#stage-camera'); copy.setAttribute('clip-path', 'url(#card-clip)')
    S._soft = { hider, copy }
    const begin = S.begin.bind(S)
    S.begin = () => { begin(); hider.removeAttribute('opacity'); copy.setAttribute('display', 'none') }
  }
  const f = S.blur('card-soften', 18 * S._cardSoft)
  if (f) { S._soft.hider.setAttribute('opacity', 0); S._soft.copy.setAttribute('filter', f); S._soft.copy.removeAttribute('display') }
  else { S._soft.hider.removeAttribute('opacity'); S._soft.copy.setAttribute('display', 'none') }
}

/**
 * The definition card: when a core term first matters, the scene steps back and the term, a plain
 * one-line definition, a small diagram drawn from what is on screen, and an optional line of the tools
 * built for it take over, while the voice says the definition. t0: when it starts (in a pause, or on
 * the defining sentence's first word); t1: when it leaves (after the breath).
 *
 *   variant 'blur'       the scene blurs and dims; the card is a centred column over it (episode 1)
 *   variant 'side'       the scene stays sharp and dims; the card is a panel over the right third
 *   variant 'lower'      the scene stays; the term and definition sit in a strip above the captions
 *   variant 'spotlight'  everything dims but `focus` [x, y, w, h] (screen px); the card sits beside it
 *   variant 'type'       the scene gives way to the wall; the term is typed large, the definition under it
 *
 * diagram(c, box, op) draws at its natural size in box {x, y, w, h}; diagramH is that height.
 * Returns the card's box while it is visible, else null.
 */
export function defCard(c, key, { term, def, tools = '', toolsLabel = 'Built for it: ', t0, t1, diagram, diagramH = 0, variant = 'blur', focus, look = LOOK }) {
  const t = c.t, S = c.S, L = look, H = c.H, I = 'ui'
  const live = t >= t0 - .01 && t <= t1 + CARD_OUT
  const inP = live ? clamp((t - t0) / CARD_IN) : 0, outP = live ? clamp((t - t1) / CARD_OUT) : 0
  const soft = live ? ease.inOut(inP) * (1 - ease.inOut(outP)) : 0
  if (variant === 'blur') soften(c, soft, H)
  if (soft <= 0) return null
  const part = k => {
    const e = ease.out(clamp((t - t0 - .18 - k * .14) / .55))
    return { op: e * (1 - ease.inOut(outP)), dy: (1 - e) * 18 - ease.inOut(outP) * 10 }
  }
  const toolText = tools ? toolsLabel + tools : ''
  if (variant === 'blur' || variant === 'type') {
    const COL = 960, x0 = Math.round(c.W / 2 - COL / 2), SC = 1.45, dH = diagram && diagramH ? diagramH * SC : 0
    S.rect(key + ':dim', 0, 0, c.W, H, { fill: L.wall, r: 0, op: soft * (variant === 'type' ? 1 : .7), layer: I })
    const defLines = balanced(def, 50), toolLines = toolText ? wrap(toolText, 70) : []
    const h = 76 + 26 + defLines.length * 50 + (dH ? 44 + dH : 0) + (toolLines.length ? 40 + toolLines.length * 32 : 0)
    let y = Math.round(H / 2 - h / 2)
    const p0 = part(0)
    let shown = term
    if (variant === 'type') { // the term typed in the film's mono, a key every 70 ms, then the rest arrives
      const n = Math.max(0, Math.min(term.length, Math.floor((t - t0 - .1) / .07) + 1))
      shown = term.slice(0, n)
      S.text(key + ':term', x0, y + 52, shown, { size: 76, weight: 500, mono: true, fill: L.ink, op: 1 - ease.inOut(outP), layer: I, box: key + ' card' })
      if (n < term.length || Math.floor(t / .53) % 2 === 0) S.rect(key + ':caret', x0 + shown.length * 76 * .6 + 4, y + 52 - 40, 5, 80, { fill: L.accent, r: 0, op: 1 - ease.inOut(outP), layer: I })
    } else S.text(key + ':term', x0, y + 52 + p0.dy, term, { size: 68, weight: 600, fill: L.ink, op: p0.op, layer: I, box: key + ' card' })
    const typedDone = variant === 'type' ? t0 + .1 + term.length * .07 : t0
    const later = k => variant === 'type' ? (() => { const e = ease.out(clamp((t - typedDone - .1 - k * .14) / .5)); return { op: e * (1 - ease.inOut(outP)), dy: (1 - e) * 14 } })() : part(k)
    y += 102
    const p1 = later(1)
    defLines.forEach((l, k) => S.text(key + ':def' + k, x0, y + 36 + k * 50 + p1.dy, l, { size: 36, fill: L.ink, op: p1.op * .94, layer: I }))
    y += defLines.length * 50
    if (dH) {
      const p2 = later(2)
      S.group(key + ':diagram', { transform: `translate(${x0} ${y + 44 + p2.dy}) scale(${SC})` }, () => diagram(c, { x: 0, y: 0, w: 540, h: diagramH }, p2.op), I)
      y += 44 + dH
    }
    const p3 = later(3)
    toolLines.forEach((l, k) => S.text(key + ':tools' + k, x0, y + 40 + k * 32 + p3.dy, l, { size: 24, fill: L.dim, op: p3.op, layer: I }))
    return { x: x0, y: Math.round(H / 2 - h / 2), w: COL, h, op: soft }
  }
  if (variant === 'side') {
    const w = Math.round(c.W * .36), slide = (1 - ease.out(inP)) * 60 + ease.inOut(outP) * 40, x = c.W - w + slide
    S.rect(key + ':dim', 0, 0, c.W - w, H, { fill: L.wall, r: 0, op: soft * .45, layer: I })
    S.rect(key + ':panel', x, 0, w, H, { fill: L.wall, r: 0, op: soft * .96, layer: I })
    const x0 = x + 64, defLines = balanced(def, 30), toolLines = toolText ? wrap(toolText, 38) : []
    let y = 150
    const p0 = part(0), p1 = part(1), p2 = part(2), p3 = part(3)
    S.text(key + ':term', x0, y + p0.dy, term, { size: 54, weight: 600, fill: L.ink, op: p0.op, layer: I, box: key + ' card' })
    y += 70
    defLines.forEach((l, k) => S.text(key + ':def' + k, x0, y + k * 44 + p1.dy, l, { size: 31, fill: L.ink, op: p1.op * .94, layer: I }))
    y += defLines.length * 44 + 30
    if (diagram && diagramH) {
      const sc = Math.min(1.1, (w - 128) / 540)
      S.group(key + ':diagram', { transform: `translate(${x0} ${y + p2.dy}) scale(${sc})` }, () => diagram(c, { x: 0, y: 0, w: 540, h: diagramH }, p2.op), I)
      y += diagramH * sc + 30
    }
    toolLines.forEach((l, k) => S.text(key + ':tools' + k, x0, y + k * 30 + p3.dy, l, { size: 22, fill: L.dim, op: p3.op, layer: I }))
    return { x, y: 0, w, h: H, op: soft }
  }
  if (variant === 'lower') {
    const dw = diagram && diagramH ? 560 : 0, x0 = 128, room = c.W - 160 - 96 - dw
    const defLines = balanced(def, Math.floor(room / (28 * .52))), h = 84 + defLines.length * 38 + 24
    const y0 = H - h - 24, rise = (1 - ease.out(inP)) * 30
    S.rect(key + ':strip', 80, y0 + rise, c.W - 160, h, { fill: L.wall, r: 14, op: soft * .94, layer: I })
    const p0 = part(0), p1 = part(1), p2 = part(2)
    S.text(key + ':term', x0, y0 + 48 + rise + p0.dy, term, { size: 40, weight: 600, fill: L.ink, op: p0.op, layer: I, box: key + ' card' })
    defLines.forEach((l, k) => S.text(key + ':def' + k, x0, y0 + 98 + k * 38 + rise + p1.dy, l, { size: 28, fill: L.ink, op: p1.op * .94, layer: I }))
    if (dw) {
      const sc = Math.min(1.2, (h - 40) / diagramH, 520 / 540)
      S.group(key + ':diagram', { transform: `translate(${c.W - 160 - dw + 40} ${y0 + (h - diagramH * sc) / 2 + rise}) scale(${sc})` }, () => diagram(c, { x: 0, y: 0, w: 540, h: diagramH }, p2.op), I)
    }
    return { x: 80, y: y0, w: c.W - 160, h, op: soft }
  }
  if (variant === 'spotlight') {
    const [fx, fy, fw, fh] = focus ?? [c.W * .1, H * .25, c.W * .4, H * .5], pad = 18
    const d = `M0 0H${c.W}V${H}H0Z M${fx - pad} ${fy - pad}V${fy + fh + pad}H${fx + fw + pad}V${fy - pad}Z`
    S.el(key + ':dim', 'path', { d, fill: L.wall, 'fill-rule': 'evenodd', opacity: soft * .78 }, I)
    S.rect(key + ':ring', fx - pad, fy - pad, fw + 2 * pad, fh + 2 * pad, { stroke: L.dim, sw: 1.5, r: 12, op: soft * .6, layer: I })
    const right = fx + fw / 2 < c.W / 2, w = 640, x0 = right ? Math.min(c.W - w - 60, fx + fw + pad + 70) : Math.max(60, fx - pad - 70 - w)
    const p0 = part(0), p1 = part(1), p2 = part(2), p3 = part(3), defLines = balanced(def, 32), toolLines = toolText ? wrap(toolText, 44) : []
    let y = Math.max(80, Math.min(H - 380, fy + 30))
    S.text(key + ':term', x0, y + p0.dy, term, { size: 52, weight: 600, fill: L.ink, op: p0.op, layer: I, box: key + ' card' })
    y += 64
    defLines.forEach((l, k) => S.text(key + ':def' + k, x0, y + k * 42 + p1.dy, l, { size: 30, fill: L.ink, op: p1.op * .94, layer: I }))
    y += defLines.length * 42 + 24
    if (diagram && diagramH) {
      const sc = Math.min(1, w / 540)
      S.group(key + ':diagram', { transform: `translate(${x0} ${y + p2.dy}) scale(${sc})` }, () => diagram(c, { x: 0, y: 0, w: 540, h: diagramH }, p2.op), I)
      y += diagramH * sc + 24
    }
    toolLines.forEach((l, k) => S.text(key + ':tools' + k, x0, y + k * 30 + p3.dy, l, { size: 22, fill: L.dim, op: p3.op, layer: I }))
    return { x: x0, y: fy, w, h: fh, op: soft }
  }
  throw new Error(`defCard: variant must be one of ${CARD_VARIANTS.join(', ')} (got ${JSON.stringify(variant)})`)
}

// ── Small persistent guides ─────────────────────────────────────────────────────────────────────
/**
 * A quiet strip of stages, top right, the current one lit (briefly in the accent when it changes):
 * a film's spine kept in view without saying it again, as episode 1's "text → data → tools".
 */
export function progressStrip(c, stages, current, { changeAt = -1e9, op = 1, look = LOOK, x, y = 30 } = {}) {
  const S = c.S, L = look, I = 'ui', widths = stages.map(n => n.length * 12.5 + 18), arrows = (stages.length - 1) * 22
  const total = widths.reduce((a, b) => a + b, 0) + arrows + 16, x0 = x ?? c.W - total - 24
  S.rect('strip:bg', x0 - 16, y - 20, total + 16, 40, { fill: L.wall, stroke: L.line, sw: 1, r: 20, op, layer: I })
  let xx = x0
  stages.forEach((n, k) => {
    const on = k === current, flash = on ? Math.max(0, 1 - (c.t - changeAt) / 1.2) : 0
    S.text('strip:' + k, xx, y, n, { size: 22, weight: on ? 600 : 400, fill: on ? (flash > 0 ? L.accent : L.ink) : L.dim, op, layer: I })
    xx += widths[k]
    if (k < stages.length - 1) { S.text('strip:arrow' + k, xx - 4, y, '→', { size: 20, fill: L.dim, op, layer: I }); xx += 22 }
  })
}

/** A checklist of questions, each ticked at its time in `ticks` (clip seconds), top right by default. */
export function checklist(c, items, ticks, { x, y = 90, size = 22, op = 1, look = LOOK, width } = {}) {
  const S = c.S, L = look, I = 'ui', lh = size * 1.6, w = width ?? Math.max(...items.map(q => q.length)) * size * .55 + size * 2.4
  const x0 = x ?? c.W - w - 24
  S.rect('check:bg', x0 - 18, y - lh * .7, w + 18, lh * items.length + 14, { fill: L.wall, r: 12, op: op * .85, layer: I })
  items.forEach((q, k) => {
    const done = ticks[k] !== undefined && c.t >= ticks[k]
    S.text('check:box' + k, x0, y + k * lh, done ? '✓' : '○', { size, fill: done ? L.accent : L.faint, op, layer: I })
    S.text('check:q' + k, x0 + size * 1.3, y + k * lh, q, { size, fill: done ? L.ink : L.dim, op, layer: I })
  })
}

// ── Product pages ───────────────────────────────────────────────────────────────────────────────
/**
 * A product's own bar along the top of a page box, and the label every reconstruction carries,
 * bottom right, quiet: honest about what the viewer is looking at. Returns the box under the bar.
 */
export function productFrame(c, key, box, { product, title = '', mark = '#7b5cd6', recon, look = LOOK } = {}) {
  const S = c.S, L = look
  S.rect(key + ':bar', box.x, box.y, box.w, 56, { fill: '#162327', r: 0 })
  S.rect(key + ':mark', box.x + 20, box.y + 14, 28, 28, { fill: mark, r: 6 })
  S.text(key + ':name', box.x + 62, box.y + 28, product, { size: 22, weight: 600, fill: L.ink })
  if (title) S.text(key + ':title', box.x + 62 + product.length * 14 + 40, box.y + 28, title, { size: 22, fill: L.dim })
  const label = recon === false ? '' : recon ?? `Reconstruction from ${product} docs · not a live account`
  if (label) S.text(key + ':recon', box.x + box.w - 18, box.y + box.h - 16, label, { size: 18, anchor: 'end', fill: L.dim, op: .9 })
  return { x: box.x, y: box.y + 56, w: box.w, h: box.h - 56 - (label ? 30 : 0) }
}

function scale(min, max, a, b) { return v => a + (v - min) / (max - min || 1) * (b - a) }

/**
 * A time series: series [{name, points: [[x, y]…], colour, label}] on shared axes, x and y as
 * {min, max, ticks: [[value, label]…]}; `p` draws the lines on left to right (0..1); `threshold`
 * {value, label, colour} a dashed line. Returns the scales for annotation: {X, Y, plot}.
 */
export function timeSeries(c, key, box, { series, x, y, p = 1, threshold, look = LOOK, pad = [92, 30, 60, 50], labels = true } = {}) {
  const S = c.S, L = look, [pl, pt, pr, pb] = pad
  const plot = { x: box.x + pl, y: box.y + pt, w: box.w - pl - pr, h: box.h - pt - pb }
  const X = scale(x.min, x.max, plot.x, plot.x + plot.w), Y = scale(y.min, y.max, plot.y + plot.h, plot.y)
  for (const [v, lab] of y.ticks ?? []) {
    S.line(key + ':gy' + v, plot.x, Y(v), plot.x + plot.w, Y(v), { stroke: L.line, sw: 1 })
    S.text(key + ':ty' + v, plot.x - 14, Y(v), lab, { size: 20, anchor: 'end', fill: L.dim })
  }
  for (const [v, lab] of x.ticks ?? []) S.text(key + ':tx' + v, X(v), plot.y + plot.h + 32, lab, { size: 20, anchor: 'middle', fill: L.dim })
  if (threshold) {
    S.line(key + ':thr', plot.x, Y(threshold.value), plot.x + plot.w, Y(threshold.value), { stroke: threshold.colour ?? L.problem, sw: 2, dash: '8 8' })
    if (threshold.label) S.text(key + ':thrl', plot.x + plot.w, Y(threshold.value) - 16, threshold.label, { size: 20, anchor: 'end', fill: threshold.colour ?? L.problem })
  }
  series.forEach((s, k) => {
    const pts = s.points.filter(([px]) => px <= x.min + (x.max - x.min) * p)
    if (pts.length < 2) return
    S.path(key + ':s' + k, 'M' + pts.map(([px, py]) => `${X(px).toFixed(1)} ${Y(py).toFixed(1)}`).join(' L'), { stroke: s.colour ?? L.ink, sw: s.width ?? 3, means: s.means })
    if (labels && s.label !== false && p >= 1) {
      const top = s.points.reduce((m, q) => (q[1] > m[1] ? q : m), s.points[0])
      const [lx, ly] = s.labelAt ?? [top[0], top[1]]
      S.text(key + ':sl' + k, X(lx), Y(ly) - 24, s.label ?? s.name, { size: 24, anchor: 'middle', fill: s.colour ?? L.ink, weight: 600 })
    }
  })
  return { X, Y, plot }
}

/**
 * A table: columns [{name, width (fraction), align}], rows of cells (strings or {text, colour}); `lit`
 * row indexes are highlighted; `p` reveals rows top to bottom. Returns each row's box for annotation.
 */
export function table(c, key, box, { columns, rows, lit = [], p = 1, size = 24, look = LOOK, rowH } = {}) {
  const S = c.S, L = look, rh = rowH ?? size * 2, xs = []
  let acc = box.x + 24
  for (const col of columns) { xs.push(acc); acc += (col.width ?? 1 / columns.length) * (box.w - 48) }
  columns.forEach((col, k) => S.text(key + ':h' + k, xs[k] + (col.align === 'right' ? (col.width ?? 1 / columns.length) * (box.w - 48) - 16 : 0), box.y + rh / 2, col.name,
    { size: size * .8, fill: L.dim, anchor: col.align === 'right' ? 'end' : 'start', ls: 1 }))
  S.line(key + ':rule', box.x + 16, box.y + rh, box.x + box.w - 16, box.y + rh, { stroke: L.line, sw: 1.5 })
  const shown = Math.round(rows.length * clamp(p)), boxes = []
  rows.slice(0, shown).forEach((row, r) => {
    const yy = box.y + rh * (r + 1.5)
    if (lit.includes(r)) S.rect(key + ':lit' + r, box.x + 8, yy - rh / 2, box.w - 16, rh, { fill: L.lit, r: 6 })
    row.forEach((cell, k) => {
      const col = columns[k], o = typeof cell === 'object' ? cell : { text: String(cell) }
      S.text(key + ':c' + r + '-' + k, xs[k] + (col.align === 'right' ? (col.width ?? 1 / columns.length) * (box.w - 48) - 16 : 0), yy, o.text,
        { size, mono: col.mono, fill: o.colour ?? L.ink, anchor: col.align === 'right' ? 'end' : 'start' })
    })
    boxes.push([box.x + 8, yy - rh / 2, box.w - 16, rh])
  })
  return { rows: boxes }
}

/**
 * A trace as a waterfall: spans [{name, start, end, depth, colour}] in ms on one axis from 0 to
 * `total`; `p` grows the bars from their starts. Returns the scale and each span's box.
 */
export function waterfall(c, key, box, { spans, total, p = 1, look = LOOK, labelW = 300, size = 20, title } = {}) {
  const S = c.S, L = look, top = box.y + (title ? 56 : 16), rh = Math.min(46, (box.h - (top - box.y) - 16) / Math.max(1, spans.length))
  if (title) S.text(key + ':title', box.x + 24, box.y + 28, title, { size: 24, fill: L.dim })
  const X = scale(0, total, box.x + labelW + 24, box.x + box.w - 24), out = []
  spans.forEach((s, k) => {
    const yy = top + k * rh, w = (X(s.end) - X(s.start)) * clamp(p)
    S.text(key + ':n' + k, box.x + labelW + (s.depth ?? 0) * 0, yy + rh / 2, s.name, { size, mono: true, anchor: 'end', fill: L.dim })
    S.rect(key + ':b' + k, X(s.start), yy + rh * .2, Math.max(2, w), rh * .6, { fill: s.colour ?? L.keyword, r: 3, means: s.means })
    out.push([X(s.start), yy, X(s.end) - X(s.start), rh])
  })
  return { X, spans: out }
}

/**
 * A point plot (a latency scatter): points [[x, y]…] on axes {min, max, ticks}; a selection
 * {from: [fx, fy], to: [fx, fy]} as fractions of the plot, or the drag in progress from the browser's
 * ctx.drag, outlines a box and lights the points inside it. Returns {plot, inside: indexes}.
 */
export function pointPlot(c, key, box, { points, x, y, selection, drag, look = LOOK, r = 4, colour, hot } = {}) {
  const S = c.S, L = look, pl = 92, pb = 50
  const plot = { x: box.x + pl, y: box.y + 20, w: box.w - pl - 30, h: box.h - 20 - pb }
  const X = scale(x.min, x.max, plot.x, plot.x + plot.w), Y = scale(y.min, y.max, plot.y + plot.h, plot.y)
  for (const [v, lab] of y.ticks ?? []) { S.line(key + ':gy' + v, plot.x, Y(v), plot.x + plot.w, Y(v), { stroke: L.line, sw: 1 }); S.text(key + ':ty' + v, plot.x - 14, Y(v), lab, { size: 20, anchor: 'end', fill: L.dim }) }
  for (const [v, lab] of x.ticks ?? []) S.text(key + ':tx' + v, X(v), plot.y + plot.h + 32, lab, { size: 20, anchor: 'middle', fill: L.dim })
  let sel = selection
  if (drag && drag.p > 0) sel = { from: drag.from, to: [drag.from[0] + (drag.to[0] - drag.from[0]) * drag.p, drag.from[1] + (drag.to[1] - drag.from[1]) * drag.p] }
  let inside = []
  if (sel) {
    const ax = plot.x + plot.w * Math.min(sel.from[0], sel.to[0]), bx = plot.x + plot.w * Math.max(sel.from[0], sel.to[0])
    const ay = plot.y + plot.h * Math.min(sel.from[1], sel.to[1]), by = plot.y + plot.h * Math.max(sel.from[1], sel.to[1])
    S.rect(key + ':sel', ax, ay, bx - ax, by - ay, { fill: L.accent, op: .12, r: 2 })
    S.rect(key + ':selline', ax, ay, bx - ax, by - ay, { stroke: L.accent, sw: 1.5, r: 2 })
    inside = points.map(([px, py], k) => [X(px), Y(py), k]).filter(([px, py]) => px >= ax && px <= bx && py >= ay && py <= by).map(q => q[2])
  }
  const isIn = new Set(inside)
  points.forEach(([px, py], k) => S.circle(key + ':p' + k, X(px), Y(py), r, { fill: isIn.has(k) ? hot ?? L.problem : colour ?? L.keyword, op: isIn.has(k) ? 1 : .7 }))
  return { plot, inside, target: [plot.x, plot.y, plot.w, plot.h] }
}

/**
 * A ranked list of fields that reorders: items [{name, value, colour}] drawn in `order` (names),
 * moving from `before` to `order` over `dur` seconds from t0 (clip time); bars show value from 0 to 1.
 */
export function rankedList(c, key, box, { items, order, before, t0 = -1e9, dur = .6, look = LOOK, size = 24, rowH } = {}) {
  const S = c.S, L = look, rh = rowH ?? size * 2.2, p = ease.inOut(clamp((c.t - t0) / dur))
  const rank = names => Object.fromEntries((names ?? items.map(i => i.name)).map((n, k) => [n, k]))
  const a = rank(before ?? order), b = rank(order)
  items.forEach(it => {
    const k = (a[it.name] ?? 0) + ((b[it.name] ?? 0) - (a[it.name] ?? 0)) * p, yy = box.y + rh * (k + .5)
    S.text(key + ':' + it.name, box.x + 24, yy, it.name, { size, mono: true, fill: b[it.name] === 0 && p >= 1 ? L.ink : L.dim })
    S.rect(key + ':bar:' + it.name, box.x + box.w * .55, yy - size * .35, (box.w * .4) * clamp(it.value), size * .7, { fill: it.colour ?? (b[it.name] === 0 ? L.problem : L.line), r: 4 })
  })
}
