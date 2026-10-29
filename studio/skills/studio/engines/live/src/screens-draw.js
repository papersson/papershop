// The screens layer's picture: desktops side by side on one wide stage, the editor, terminal and
// browser windows on them, the desktop indicator, the pointer, and a camera that goes out, across and
// in at every switch. It draws the state screens.js replays from data/screens.json, so a chapter only
// says where to look and what its pages show. references/screens.md has the whole API.
//
//   const scr = await loadScreens(import.meta.url)          // data/screens.json, its files and runs
//   export default function draw(c) {
//     const s = screensAt(c, scr)                            // every window's state at this frame
//     screensCamera(c, scr, s, [[2, {on: 'servers', region: [0, 0, 1200, 500]}]])
//     drawScreens(c, scr, s, {pages: {logs: (c, box, tab) => …}})
//   }

import { compile, state, switches, targetKey, TRAVEL, CHORD, FADE } from './screens.js'
import { cameraAt } from '../../shared/camera.js'
import { ease } from '../../shared/motion.js'

const clamp = x => Math.max(0, Math.min(1, x))

/**
 * The default look: a dark desk with one meaning per colour, as observability episode 1 had it.
 * screens.json `look` (or drawScreens' `look`) overrides any of these.
 */
export const LOOK = {
  wall: '#070d0f', win: '#131f23', bar: '#1b2a2f', bar2: '#22343a', line: '#2e4248',
  ink: '#e7dfcf', dim: '#9caaa8', faint: '#5e7072', accent: '#65c9b0', problem: '#ec8d76',
  keyword: '#93b7e8', literal: '#e9c47b', current: '#26403f', lit: '#1d3236',
  paper: '#f1ece2', paperBar: '#e2dbcd', paperEdge: '#cfc7b8', paperInk: '#1d2a2d', paperDim: '#6d7a7a',
}
export const GAP = 24, INSET = 24, BAR = 44

/** data/screens.json with its files and runs, from a scene module's URL (scenes/<clip>.js). */
export async function loadScreens(sceneUrl, file = '../data/screens.json') {
  const url = new URL(file, sceneUrl), base = new URL('../', url) // the video folder: files and runs are named from it
  const load = async p => {
    const r = await fetch(new URL(p, base))
    if (!r.ok) throw new Error(`screens.json: could not load ${p} (${r.status})`)
    return r
  }
  const r = await fetch(url)
  if (!r.ok) throw new Error(`could not load ${file} (${r.status})`)
  const spec = await r.json()
  // a file named by its path (one line ending in an extension) is loaded; anything else is the text itself
  for (const d of spec.desktops ?? []) for (const [name, p] of Object.entries(d.files ?? {}))
    if (typeof p === 'string' && !p.includes('\n') && /\.[a-z0-9]+$/i.test(p)) d.files[name] = await (await load(p)).text()
  const runs = {}
  for (const [name, p] of Object.entries(spec.runs ?? {})) runs[name] = typeof p === 'string' ? await (await load(p)).json() : p
  return { spec, runs, compiled: null, timeline: null }
}

/** The compiled log for this timeline (compiled once per timeline), and the clip's start in film seconds. */
function compiled(c, scr) {
  if (scr.timeline !== c.timeline) { scr.compiled = compile(scr.spec, c.timeline, scr.runs); scr.timeline = c.timeline; scr.switches = switches(scr.compiled) }
  const clip = c.timeline.tracks.scene.find(x => x.id === c.clip)
  return { k: scr.compiled, f0: clip ? clip.start : 0 }
}

/** Every window's state at this frame (screens.js state), with the clip's start for clip-time maths. */
export function screensAt(c, scr) {
  const { k, f0 } = compiled(c, scr)
  return { ...state(k, c.t + f0), f0, look: { ...LOOK, ...(scr.spec.look ?? {}) } }
}

// ── Geometry ────────────────────────────────────────────────────────────────────────────────────
/** World x of plate k's left edge: plates sit left to right with a strip of wallpaper between. */
export const plateX = (c, k) => k * (c.W + GAP)
const plateIndex = (scr, plate) => scr.compiled.plates.indexOf(plate)
/** Camera key framing the whole of a desktop (a plate). */
export const whole = (c, scr, plate) => ({ x: plateX(c, plateIndex(scr, plate)) + c.W / 2, y: c.H / 2, z: 1 })

/**
 * Camera key framing a region of a desktop, in that desktop's own pixels [x0, y0, x1, y1], never
 * wider than the desktop and kept inside it, so no wallpaper shows except in a slide or a pull-back.
 */
export function onPlate(c, scr, plate, [x0, y0, x1, y1], o = {}) {
  const X = plateX(c, plateIndex(scr, plate)), k = c.frameOn([X + x0, y0, X + x1, y1], { margin: 0, ...o }), z = Math.max(1, k.z)
  const hw = c.W / 2 / z, hh = c.H / 2 / z
  return { x: Math.min(X + c.W - hw, Math.max(X + hw, k.x)), y: Math.min(c.H - hh, Math.max(hh, k.y)), z }
}

/** A window's box on its plate, in desktop pixels: its frame, or the whole plate when it is alone and grows. */
export function windowBox(c, scr, s, id) {
  const d = scr.compiled.desktops.find(x => x.id === id), plate = scr.compiled.plateOf[id]
  const mates = scr.compiled.desktops.filter(x => scr.compiled.plateOf[x.id] === plate && !s.desks[x.id].closed)
  const [fx, fy, fw, fh] = d.grow && mates.length === 1 ? [0, 0, 1, 1] : d.frame ?? [0, 0, 1, 1]
  const iw = c.W - 2 * INSET, ih = c.H - 2 * INSET
  let x = INSET + fx * iw, y = INSET + fy * ih, w = fw * iw, h = fh * ih
  if (fx > 0) { x += GAP / 2; w -= GAP / 2 }
  if (fx + fw < 1) w -= GAP / 2
  if (fy > 0) { y += GAP / 2; h -= GAP / 2 }
  if (fy + fh < 1) h -= GAP / 2
  return { x, y, w, h, X: plateX(c, plateIndex(scr, plate)) + x }
}

// ── Camera ──────────────────────────────────────────────────────────────────────────────────────
function resolveKey(c, scr, s, key, plateAtT) {
  if (key === 'whole' || key?.whole) return whole(c, scr, key?.whole ?? plateAtT)
  if (key === 'all' || key?.all) {
    const ps = s.present.length ? s.present : scr.compiled.plates
    const k0 = Math.min(...ps.map(p => plateIndex(scr, p))), k1 = Math.max(...ps.map(p => plateIndex(scr, p)))
    return c.frameOn([plateX(c, k0), 0, plateX(c, k1) + c.W, c.H], { margin: key?.margin ?? 60, min: .1 })
  }
  if (key?.region) return onPlate(c, scr, key.on ?? plateAtT, key.region, key)
  if (key?.window) {
    const b = windowBox(c, scr, s, key.window), pad = key.pad ?? 0
    return onPlate(c, scr, scr.compiled.plateOf[key.window], [b.x - pad, b.y - pad, b.x + b.w + pad, b.y + b.h + pad], key)
  }
  return key
}

/**
 * Point the camera for this frame. keys: [clip seconds, target, ease?] where a target is 'whole' (the
 * desktop shown then), 'all' (every desktop present: the pull-back), {on, region: [x0, y0, x1, y1]},
 * {window: id, pad}, or a plain {x, y, z}. With no keys the camera holds the whole current desktop.
 * Around every switch it eases out to the whole desktop, slides rigidly across with ease out, and
 * eases back in to the keys: out, across, in. The viewer always sees the whole plate move.
 */
export function screensCamera(c, scr, s, keys = [], { out = .35, inn = .4 } = {}) {
  const sw = scr.switches.map(x => ({ ...x, t: x.t - s.f0 }))
  const plateAt = t => { let p = scr.compiled.start; for (const x of sw) if (t >= x.t) p = x.to; return p }
  const user = t => {
    if (!keys.length) return whole(c, scr, plateAt(t))
    const ks = keys.map(([kt, target, e]) => [kt, resolveKey(c, scr, s, target, plateAt(kt)), e])
    const k = cameraAt(t, ks.map(([kt, v, e]) => [kt, { x: v.x, y: v.y, zoom: v.z }, e]))
    return { x: k.x, y: k.y, z: k.zoom }
  }
  const lerp = (a, b, p) => ({ x: a.x + (b.x - a.x) * p, y: a.y + (b.y - a.y) * p, z: a.z + (b.z - a.z) * p })
  let k = null
  for (const x of sw) {
    const A = whole(c, scr, x.from), B = whole(c, scr, x.to), t = c.t
    if (t >= x.t - out && t < x.t) k = lerp(user(x.t - out), A, ease.inOut(clamp((t - (x.t - out)) / out)))
    else if (t >= x.t && t < x.t + x.ms) k = lerp(A, B, ease.out(clamp((t - x.t) / x.ms)))
    else if (t >= x.t + x.ms && t < x.t + x.ms + inn) k = lerp(B, user(x.t + x.ms + inn), ease.inOut(clamp((t - x.t - x.ms) / inn)))
    if (k) break
  }
  k ??= user(c.t)
  c.camAt([[c.t, k]])
  return k
}

// ── Drawing ─────────────────────────────────────────────────────────────────────────────────────
/** Window chrome at world (X, y, w, h): body, title bar, the three lights, a title. Returns the content box. */
export function chrome(c, key, X, y, w, h, { title = '', light = false, look = LOOK, op = 1 } = {}) {
  const S = c.S, L = look
  S.rect(key + ':body', X, y, w, h, { fill: light ? L.paper : L.win, stroke: light ? L.paperEdge : L.line, sw: 1.5, r: 10, op, box: key })
  S.rect(key + ':bar', X + 1, y + 1, w - 2, BAR, { fill: light ? L.paperBar : L.bar, r: 9, op })
  ;['#ec8d76', '#e9c47b', '#65c9b0'].forEach((fill, k) => S.circle(key + ':light' + k, X + 22 + k * 22, y + BAR / 2 + 1, 6, { fill, op: op * .85 }))
  if (title) S.text(key + ':title', X + w / 2, y + BAR / 2 + 1, title, { size: 20, anchor: 'middle', fill: light ? L.paperDim : L.dim, op })
  return { x: X, y: y + BAR, w, h: h - BAR }
}

/** A tab strip at world (x, y): the active tab lit with an underline; tabs snap, they never slide. */
export function tabStrip(c, key, x, y, w, names, active, { light = false, h = 40, look = LOOK, mono = true, op = 1 } = {}) {
  const S = c.S, L = look, tw = Math.min(300, w / Math.max(1, names.length))
  S.rect(key + ':strip', x, y, w, h, { fill: light ? '#e8e2d6' : L.bar2, r: 0, op })
  names.forEach((n, k) => {
    const on = k === active
    if (on) S.rect(key + ':tab' + k, x + k * tw, y, tw, h, { fill: light ? L.paper : L.win, r: 0, op })
    S.text(key + ':tabt' + k, x + k * tw + 18, y + h / 2, n, { size: 19, mono, fill: on ? (light ? L.paperInk : L.ink) : (light ? L.paperDim : L.faint), op })
    if (on) S.rect(key + ':hl' + k, x + k * tw, y + h - 3, tw, 3, { fill: L.accent, r: 0, op })
  })
  return y + h
}

const KEYWORDS = 'def|for|in|import|from|return|if|elif|else|while|with|as|class|not|and|or|True|False|None|try|except|raise|lambda|yield|async|await|const|let|var|function|new|this|null|true|false|export|default|fn|pub|use|struct|int|void|char'
const TOKEN = new RegExp(`("[^"]*"|'[^']*'|#.*$|//.*$|\\b(?:${KEYWORDS})\\b|\\b\\d+(?:\\.\\d+)?\\b)`, 'g')
/** A line of code as coloured parts: keywords, literals and comments in the look's colours. */
export function syntax(line, look = LOOK) {
  const kw = new RegExp(`^(${KEYWORDS})$`)
  return line.split(TOKEN).filter(Boolean).map(p => ({ text: p,
    fill: p.startsWith('#') || p.startsWith('//') ? look.faint : /^["'\d]/.test(p) ? look.literal : kw.test(p) ? look.keyword : look.ink }))
}

/** One line of mono text from coloured parts at world (x, y); each part its own keyed node. */
export function monoLine(c, key, x, y, parts, { size = 24, op = 1, layer } = {}) {
  const adv = size * .6
  let col = 0
  parts.forEach((p, k) => {
    if (p.text) c.S.text(key + ':' + k, x + col * adv, y, p.text.replace(/ /g, ' '), { size, mono: true, fill: p.fill, op, layer })
    col += p.text.length
  })
}

/**
 * A long terminal line broken to `cols` columns at a token boundary where it can be (a space, a pipe, a
 * slash, a comma); `midToken` says a break had to fall inside a token (a number or a name).
 */
export function wrapLine(text, cols) {
  const out = []
  let rest = text, midToken = false
  while (rest.length > cols) {
    let cut = -1
    for (let k = cols; k > cols * .5; k--) if (' |/,'.includes(rest[k - 1])) { cut = k; break }
    if (cut < 0) { cut = cols; midToken = true }
    out.push(rest.slice(0, cut))
    rest = rest.slice(cut)
  }
  out.push(rest)
  return { lines: out, midToken }
}

/** Columns a terminal window holds at its type size (for checks and for wrapping). */
export const terminalCols = (w, size) => Math.floor((w - 2 * 36) / (size * .6))

function termRows(c, key, look, box, src, { size, lh, rows, input, caret, t }) {
  const L = look, step = size * lh, cols = terminalCols(box.w, size)
  const out = []
  for (const l of src.lines) {
    const text = (l.cmd ? (l.prompt ?? '') : '') + l.text
    const { lines } = wrapLine(text, cols)
    lines.forEach((piece, k) => {
      if (l.cmd && k === 0) out.push([{ text: piece.slice(0, (l.prompt ?? '').length), fill: L.accent }, { text: piece.slice((l.prompt ?? '').length), fill: L.ink }])
      else out.push([{ text: piece, fill: l.fill ?? (l.err ? L.problem : l.cmd ? L.ink : L.ink) }])
    })
  }
  if (input !== null) {
    const { lines } = wrapLine(src.prompt + input, cols)
    lines.forEach((piece, k) => out.push(k === 0 ? [{ text: piece.slice(0, src.prompt.length), fill: L.accent }, { text: piece.slice(src.prompt.length), fill: L.ink }] : [{ text: piece, fill: L.ink }]))
  }
  const shown = out.slice(-rows), x0 = box.x + 36, rowY = r => box.y + 24 + (r + .5) * step
  shown.forEach((parts, r) => monoLine(c, key + ':r' + r, x0, rowY(r), parts, { size }))
  if (input !== null && caret) {
    const lastLen = shown.at(-1).reduce((n, p) => n + p.text.length, 0)
    const blink = caret === 'solid' || Math.floor(t / .53) % 2 === 0
    if (blink) c.S.rect(key + ':caret', box.x + 36 + lastLen * size * .6, box.y + 24 + (shown.length - .5) * step - size * .6, size * .58, size * 1.2, { fill: L.ink, r: 0, op: .75 })
  }
  // the last row showing `text` (output scrolls up, so the newest is the one meant)
  const find = text => {
    for (let r = shown.length - 1; r >= 0; r--) {
      const k = shown[r].map(p => p.text).join('').indexOf(text)
      if (k >= 0) return textBox(x0 + k * size * .6, rowY(r), text.length * size * .6, step, size)
    }
    return null
  }
  return { step, cols, rows: shown.length, find }
}

/** A piece of monospace text's box for pointing: centre y, the underline just below its letters. */
const textBox = (x, y, w, h, size) => ({ x, y, w, h, base: y + size * .62, size })

/** A terminal window: tabs when there are several, scrollback, the line being typed, an optional split. */
export function terminalWindow(c, key, scr, s, id, o = {}) {
  const st = s.desks[id], d = st.spec, L = s.look, b = windowBox(c, scr, s, id)
  const tab = st.tabs[st.active]
  const box = chrome(c, key, b.X, b.y, b.w, b.h, { title: d.title ?? `${tab.title}${d.subtitle ? ' — ' + d.subtitle : ''}`, look: L })
  let y = box.y
  if (st.tabs.length > 1 || d.tabsAlways) y = tabStrip(c, key + ':tabs', box.x, box.y, box.w, st.tabs.map(x => x.title), st.active, { look: L })
  const size = o.size ?? d.size ?? 30, lh = d.lh ?? 1.45, area = { x: box.x, y, w: box.w, h: box.y + box.h - y }
  const typing = a => a !== undefined
  const fit = h => Math.max(1, Math.floor((h - 36) / (size * lh)))
  let finds = []
  if (st.split) {
    const other = st.tabs.find(x => x.id === st.split) ?? (() => { throw new Error(`desktop ${id}: no tab ${st.split} to split with`) })()
    const top = { ...area, h: area.h / 2 }, bottom = { ...area, y: area.y + area.h / 2, h: area.h / 2 }
    const up = termRows(c, key + ':top', L, top, other, { size, lh, rows: fit(top.h), input: null, t: c.t })
    c.S.line(key + ':splitrule', area.x + 1, bottom.y, area.x + area.w - 1, bottom.y, { stroke: L.line, sw: 1.5 })
    finds = [termRows(c, key + ':bottom', L, bottom, tab, { size, lh, rows: fit(bottom.h), input: tab.running ? null : tab.input, caret: true, t: c.t }).find, up.find]
  } else finds = [termRows(c, key + ':text', L, area, tab, { size, lh, rows: fit(area.h), input: typing(tab.input) && !tab.running ? tab.input : null, caret: true, t: c.t }).find]
  const locate = g => g?.text ? finds.reduce((got, f) => got ?? f(g.text), null) : null
  return { box: area, size, lh, cols: terminalCols(area.w, size), locate, bg: L.win }
}

/**
 * An editor window, VS Code-like: file tabs (an unsaved one marked), line numbers, syntax colour, the
 * caret while typing, and a terminal panel along the bottom that may stay open all film. It scrolls
 * so the line being edited sits above the panel; o.first, o.lit (lines to highlight) and o.focus
 * (a line to keep in view) steer it. Returns the code geometry for annotations: lineY(n).
 */
export function editorWindow(c, key, scr, s, id, o = {}) {
  const st = s.desks[id], d = st.spec, L = s.look, b = windowBox(c, scr, s, id), S = c.S
  const box = chrome(c, key, b.X, b.y, b.w, b.h, { title: d.title ?? 'Editor', look: L })
  const top = tabStrip(c, key + ':tabs', box.x, box.y, box.w, st.open.map(f => f + (st.dirty[f] ? '  ●' : '')), Math.max(0, st.open.indexOf(st.active)), { look: L })
  const P = st.panel, PS = d.panel?.size ?? 22, PL = 1.3, prow = d.panel?.rows ?? 6
  const py = P ? box.y + box.h - (prow * PS * PL + 52) : box.y + box.h
  const CS = o.size ?? d.size ?? 26, CL = d.lh ?? 1.5, step = CS * CL, rows = Math.max(1, Math.floor((py - top - 16) / step))
  const src = st.files[st.active] ?? []
  const focus = o.focus ?? st.focusLine ?? d.focus ?? 1
  const first = o.first ?? (focus > rows - 2 ? Math.max(1, Math.min(focus - Math.floor(rows * .6), src.length - rows + 2)) : 1)
  const typing = c.t + s.f0 - st.lastKey < .6
  const lit = new Set(o.lit ?? [])
  for (let r = 0; r < rows && first - 1 + r < src.length; r++) {
    const n = first + r, yy = top + 8 + (r + .5) * step, here = st.caret && st.caret.line === n && typing
    if (here || o.current === n) S.rect(key + ':cur', box.x, yy - step / 2, box.w, step, { fill: L.current, r: 0 })
    else if (lit.has(n)) S.rect(key + ':lit' + n, box.x, yy - step / 2, box.w, step, { fill: L.lit, r: 0 })
    S.text(key + ':n' + n, box.x + 62, yy, String(n), { size: CS * .8, mono: true, anchor: 'end', fill: here ? L.ink : L.faint })
    monoLine(c, key + ':l' + n, box.x + 86, yy, syntax(src[n - 1], L), { size: CS })
    if (st.caret && st.caret.line === n && (typing || o.caret)) {
      const blink = typing || Math.floor(c.t / .53) % 2 === 0
      if (blink) S.rect(key + ':caret', box.x + 86 + st.caret.col * CS * .6, yy - CS * .6, 2.5, CS * 1.2, { fill: L.ink, r: 0 })
    }
  }
  let panel = null, panelFind = () => null
  if (P) {
    S.line(key + ':panelrule', box.x + 1, py, box.x + box.w - 1, py, { stroke: L.line, sw: 1.5 })
    S.text(key + ':paneltitle', box.x + 24, py + 20, P.title, { size: 16, fill: L.dim, ls: 1.5 })
    if (P.name) S.text(key + ':panelname', box.x + 24 + P.title.length * 11 + 20, py + 20, P.name, { size: 16, fill: L.faint })
    const area = { x: box.x - 12, y: py + 22, w: box.w, h: box.y + box.h - py - 22 }
    panelFind = termRows(c, key + ':panel', L, area, P, { size: PS, lh: PL, rows: prow, input: !P.running && (P.input || st.panelActive) ? P.input : null, caret: !!P.input, t: c.t }).find
    panel = { x: box.x, y: py, w: box.w, h: box.y + box.h - py }
  }
  const lineY = n => top + 8 + (n - first + .5) * step, codeX = box.x + 86
  // a line ({line}), a piece of one ({line, text}) or the first line showing a piece ({text}), or a
  // piece of the terminal panel ({panel: true, text}); null when it is scrolled out of view
  const locate = g => {
    if (!g || typeof g !== 'object') return null
    if (g.panel) return g.text ? panelFind(g.text) : null
    const n = g.line ?? src.findIndex(l => l.includes(g.text)) + 1
    if (n < first || n >= first + rows || n > src.length) return null
    const l = src[n - 1], k = g.text ? l.indexOf(g.text) : l.length - l.trimStart().length
    if (k < 0) return null
    return textBox(codeX + k * CS * .6, lineY(n), (g.text ?? l.trim()).length * CS * .6, step, CS)
  }
  return { box, first, rows, step, size: CS, panel, lineY, codeX, locate, bg: L.win }
}

/** The mouse pointer at world (x, y); `pressed` 0..1 draws the ring of a press fading out. */
export function pointer(c, key, x, y, { pressed = 0, op = 1, look = LOOK } = {}) {
  c.S.path(key, `M ${x} ${y} l 0 30 l 7.5 -7 l 8 16.5 l 7 -3.5 l -8 -15.5 l 11 -1.5 Z`, { fill: look.ink, stroke: '#0b1416', sw: 2, op })
  if (pressed > 0 && pressed < 1) c.S.circle(key + ':ring', x, y, 14 + 10 * pressed, { stroke: look.accent, sw: 2, op: op * (1 - pressed) })
}

/**
 * A browser window: tabs in the title bar, the address bar (the url, or a url being typed), and the
 * page, drawn by pages[tab.page](c, box, tab, ctx) in world pixels. A page returns {targets: {name:
 * [x, y, w, h]}} so clicks, drags, points and marks in the log know where to go; ctx carries the drag
 * in progress, the look, and the window's outcome marks by target (so a failed row can turn red). A page the film doesn't draw shows its name, quietly, as a placeholder.
 */
export function browserWindow(c, key, scr, s, id, o = {}) {
  const st = s.desks[id], d = st.spec, L = s.look, b = windowBox(c, scr, s, id), S = c.S
  const tab = st.tabs[st.active], light = d.light ?? false
  const box = chrome(c, key, b.X, b.y, b.w, b.h, { title: '', light, look: L })
  if (st.tabs.length) tabStrip(c, key + ':tabs', box.x + 90, box.y - BAR + 4, Math.min(box.w - 120, 300 * st.tabs.length), st.tabs.map(x => x.title), st.active, { light, mono: false, look: L })
  S.rect(key + ':addr', box.x + 16, box.y + 8, box.w - 32, 36, { fill: light ? '#e6e0d4' : L.bar, r: 18 })
  S.text(key + ':url', box.x + 40, box.y + 26, tab.fields.url ?? tab.url, { size: 19, mono: true, fill: light ? L.paperDim : L.dim })
  const page = { x: box.x, y: box.y + 52, w: box.w, h: box.h - 52 }
  const fn = (o.pages ?? {})[tab.page]
  const ctx = { look: L, light, t: c.t, film: c.t + s.f0, drag: st.drag?.target ? st.drag : null, tab, since: tab.since - s.f0, marks: st.marks }
  const got = fn ? fn(c, page, tab, ctx) ?? {} : (S.text(key + ':page', page.x + page.w / 2, page.y + page.h / 2, tab.page, { size: 22, anchor: 'middle', fill: light ? L.paperDim : L.faint }), {})
  const targets = got.targets ?? {}, rectOf = r => Array.isArray(r) ? r : r?.box
  if (st.pointer) {
    const centre = (name, at) => {
      const r = rectOf(targets[name])
      if (!r) return null
      return at ? [r[0] + r[2] * at[0], r[1] + r[3] * at[1]] : [r[0] + r[2] * .5, r[1] + r[3] * .55]
    }
    const film = c.t + s.f0, pr = st.press
    let p = centre(st.pointer, st.drag?.target === st.pointer ? st.drag.from : null) ?? [page.x + page.w * .7, page.y + page.h * .8]
    if (pr) {
      const to = centre(pr.target, pr.point) ?? p, from = centre(pr.from) ?? [to[0] + 160, to[1] + 120]
      const k = ease.inOut(clamp((film - (pr.at - TRAVEL)) / TRAVEL))
      p = [from[0] + (to[0] - from[0]) * k, from[1] + (to[1] - from[1]) * k]
    }
    if (st.drag?.target && film >= st.drag.press) {
      const a = centre(st.drag.target, st.drag.from), z = centre(st.drag.target, st.drag.to)
      if (a && z) p = [a[0] + (z[0] - a[0]) * ease.inOut(st.drag.p), a[1] + (z[1] - a[1]) * ease.inOut(st.drag.p)]
    }
    const since = pr ? film - pr.at : 99, up = st.drag ? film - st.drag.release : 99
    pointer(c, key + ':pointer', p[0], p[1], { pressed: since >= 0 && since < .3 ? since / .3 : up >= 0 && up < .3 ? up / .3 : 0, look: L })
  }
  // a target is [x, y, w, h], or {box, line: [x0, x1]} when the underline should run under part of it
  // (a trace row: its label and bar stay lit, the underline goes under the bar)
  const locate = g => {
    const t = typeof g === 'string' ? targets[g] : null, r = rectOf(t)
    if (!r) return null
    const box = { x: r[0], y: r[1] + r[3] / 2, w: r[2], h: r[3], base: r[1] + r[3] + 6, size: Math.min(24, r[3] * .5) }
    return t.line ? { ...box, line: t.line } : box
  }
  return { box: page, targets, tab, locate, bg: light ? L.paper : L.win }
}

/**
 * The desktop indicator: a dot per desktop present at the top centre, the current one a short pill.
 * It shows only from a slide's start until 0.6 s after it lands, and while a new desktop's dot grows
 * the first time it arrives. Drawn on the ui layer, which the camera never moves.
 */
export function indicator(c, scr, s) {
  const S = c.S, L = s.look, film = c.t + s.f0, plates = scr.compiled.plates
  let vis = 0, pos = null
  for (const x of scr.switches) {
    const a = x.t, b = x.t + x.ms
    if (film >= a - .15 && film <= b + .85) {
      const e = ease.out(clamp((film - a) / x.ms))
      pos = plateIndex(scr, x.from) + (plateIndex(scr, x.to) - plateIndex(scr, x.from)) * e
      vis = Math.max(vis, clamp((film - (a - .15)) / .15) * clamp((b + .85 - film) / .25))
    }
  }
  const grows = plates.map(p => scr.compiled.arrive[p]).map(at => isFinite(at) ? clamp((film - at) / .35) : 1)
  for (const [k, at] of plates.map(p => scr.compiled.arrive[p]).entries()) if (isFinite(at) && film > at - .2 && film < at + 2.2) {
    vis = Math.max(vis, clamp((film - at + .2) / .2) * clamp((at + 2.2 - film) / .3)); pos ??= plateIndex(scr, s.current); void k
  }
  if (vis <= 0 || pos === null) return
  const shown = plates.filter((p, k) => film >= scr.compiled.arrive[p] - .2 || grows[k] > 0), n = shown.length, gap = 44, cx = c.W / 2, y = 30
  S.rect('screens:dotsbg', cx - (n - 1) / 2 * gap - 36, y - 18, (n - 1) * gap + 72, 36, { fill: L.wall, r: 18, op: vis * .85, layer: 'ui' })
  shown.forEach((p, k) => S.circle('screens:dot' + k, cx + (k - (n - 1) / 2) * gap, y, 9 * grows[plates.indexOf(p)], { fill: L.dim, op: vis * .8, layer: 'ui' }))
  S.rect('screens:pill', cx + (pos - (n - 1) / 2) * gap - 20, y - 9, 40, 18, { fill: L.ink, r: 9, op: vis, layer: 'ui' })
}

// ── Pointing and outcome marks ──────────────────────────────────────────────────────────────────
/** A point's progress at film time: the underline's draw-in `p` (whole on the word) and its fade `vis`. */
export function pointAt(pt, film) {
  const p = clamp((film - pt.from) / Math.max(1e-6, pt.at - pt.from))
  return { p: ease.out(p), vis: p > 0 ? Math.min(clamp(p * 2), clamp((pt.until + FADE - film) / FADE)) : 0 }
}

/**
 * The point on a window: everything but the target dims (a veil in the window's own background, so
 * text loses contrast and empty space looks the same), and an underline in the ink (the subject's colour) draws in under
 * the target, whole on the word the narrator says. Not a hand cursor: a pointer means someone is
 * operating the screen, an underline means the film is showing you (references/taste.md, "Pointing").
 */
export function drawPoint(c, key, g, pt, film, look, bg, { extra = 0 } = {}) {
  const r = g.locate?.(pt.target)
  if (!r) return null
  const { p, vis } = pointAt(pt, film), S = c.S, b = g.box
  if (vis <= 0) return r
  const pad = 8, x0 = Math.max(b.x, r.x - pad), x1 = Math.min(b.x + b.w, r.x + r.w + pad + extra)
  const y0 = Math.max(b.y, r.y - r.h / 2), y1 = Math.min(b.y + b.h, r.y + r.h / 2 + 4), op = pt.dim * vis
  S.rect(key + ':veil-t', b.x, b.y, b.w, y0 - b.y, { fill: bg, r: 0, op })
  S.rect(key + ':veil-b', b.x, y1, b.w, b.y + b.h - y1, { fill: bg, r: 0, op })
  S.rect(key + ':veil-l', b.x, y0, x0 - b.x, y1 - y0, { fill: bg, r: 0, op })
  S.rect(key + ':veil-r', x1, y0, b.x + b.w - x1, y1 - y0, { fill: bg, r: 0, op })
  const th = Math.max(3, r.size * .11), [u0, u1] = r.line ?? [r.x - 2, r.x + r.w + 2]
  S.rect(key + ':underline', u0, r.base - th / 2, (u1 - u0) * p, th, { fill: look.ink, r: th / 2, op: vis, box: key + ':underline' })
  return r
}

const markR = r => Math.max(9, r.size * .36)
/** The width a mark takes after its target. */
export const markGap = r => 2 * markR(r) + 18

/** Seconds a mark takes to arrive: the tick or cross draws on, the spinner fades in. */
export const MARK_IN = .25

/**
 * An outcome mark just after its target (markGap(r) wide): running spins (muted), finished is a tick (accent), failed a
 * cross (problem), cancelled a dash (faint). One meaning per colour, as the rest of the desk.
 */
export function drawMark(c, key, g, m, film, look) {
  const r = g.locate?.(m.target)
  if (!r) return
  const S = c.S, k = clamp((film - m.at) / MARK_IN), e = ease.out(k), R = markR(r)
  const x = r.x + r.w + R + 14, y = r.y, sw = Math.max(2.5, R * .28)
  if (m.state === 'running') {
    const a = film * Math.PI * 2 * 1.1, a2 = a + Math.PI * 1.5
    S.circle(key + ':track', x, y, R, { stroke: look.line, sw, op: k })
    S.path(key + ':spin', `M ${x + R * Math.cos(a)} ${y + R * Math.sin(a)} A ${R} ${R} 0 0 1 ${x + R * Math.cos(a2)} ${y + R * Math.sin(a2)}`, { stroke: look.dim, sw, op: k, box: key })
  } else if (m.state === 'finished') {
    S.path(key + ':tick', `M ${x - R * .8} ${y + R * .05} L ${x - R * .2} ${y + R * .65} L ${x + R * .9} ${y - R * .6}`, { stroke: look.accent, sw: sw * 1.2, p: e, box: key })
  } else if (m.state === 'failed') {
    S.path(key + ':cross', `M ${x - R * .7} ${y - R * .7} L ${x + R * .7} ${y + R * .7} M ${x + R * .7} ${y - R * .7} L ${x - R * .7} ${y + R * .7}`, { stroke: look.problem, sw: sw * 1.2, p: e, box: key })
  } else if (m.state === 'cancelled') {
    S.line(key + ':dash', x - R * .7, y, x + R * .7, y, { stroke: look.faint, sw: sw * 1.2, p: e, box: key })
  }
}

/** A window's point and marks, over its drawing; returns the box pointed at, if any. */
function annotate(c, key, s, st, g) {
  const film = c.t + s.f0, marks = Object.values(st.marks)
  marks.forEach((m, k) => drawMark(c, key + ':mark' + k, g, m, film, s.look))
  if (!st.point) return null
  // the veil goes over the marks too, except the pointed target's own mark
  const own = marks.some(m => targetKey(m.target) === targetKey(st.point.target)), r = own ? g.locate?.(st.point.target) : null
  return drawPoint(c, key + ':point', g, st.point, film, s.look, g.bg, { extra: r ? markGap(r) : 0 })
}

/**
 * Draw every window on every desktop present (the camera shows the ones in view), then the indicator.
 * o.pages: browser pages by name; o.windows: per window id, options for its drawing ({first, lit,
 * focus, current, size}). Returns each window's geometry by id, for annotations on top.
 */
export function drawScreens(c, scr, s, o = {}) {
  c.S.rect('screens:wall', 0, 0, c.W, c.H, { fill: s.look.wall, r: 0, layer: 'back' })
  const out = {}
  for (const d of scr.compiled.desktops) {
    const st = s.desks[d.id], plate = scr.compiled.plateOf[d.id]
    if (st.closed || !s.present.includes(plate)) continue
    const opts = { ...(o.windows?.[d.id] ?? {}), pages: o.pages }
    out[d.id] = d.kind === 'editor' ? editorWindow(c, 'scr:' + d.id, scr, s, d.id, opts)
      : d.kind === 'terminal' ? terminalWindow(c, 'scr:' + d.id, scr, s, d.id, opts)
        : browserWindow(c, 'scr:' + d.id, scr, s, d.id, opts)
    out[d.id].pointed = annotate(c, 'scr:' + d.id, s, st, out[d.id])
  }
  if (o.indicator !== false) indicator(c, scr, s)
  return out
}

export { CHORD }
