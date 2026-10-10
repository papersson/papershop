// The look sheet's built-in pages (`studio look-sheet VIDEO`): the model sheet a live video's scenes
// are drawn to, in the video's own theme and layout. Every element is shown in each of its states,
// drawn with the conventions a scene should copy: a box's outline (sw 3) is heavier than the
// dividers inside it (sw 1.5), an idle arrow is dim, an active one ice, a muted one faded; amber is a
// number to watch, ice the thing being explained, coral failure. The video's own elements come after
// these, from scenes/look.js (templates/live/scenes/example-look.js). A video that declares a colour
// legend (video.json legend) gets a page of it after the built-in ones.
//
// A page draws one still from its context, as a scene does at t = 0: S, W, H (the stage above the
// band), unit, header, view, kit, C, legend (meaning -> CSS colour) and declared (video.json's legend).

const ROLES = [
  ['bg', 'background'], ['band', 'caption band'], ['bg2', 'panel, close-up'], ['tray', 'box fill'],
  ['edge', 'box outline'], ['line', 'guide line'], ['ink', 'text'], ['dim', 'idle arrow, secondary text'],
  ['faint', 'guide text'], ['cold', 'the thing explained, selection'], ['hot', 'cost, a number to watch'],
  ['bad', 'failure'], ['good', 'success'], ['warm', 'warm highlight'], ['log', 'log entry'], ['key', 'key'],
]
const SIZES = [[52, 'title'], [40, 'heading'], [34, 'close-up header'], [30, 'box label'], [26, 'label'], [22, 'small label'], [18, 'the floor: nothing smaller']]

const css = name => getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim()

/** A column of things across the stage: x positions for n items between fractions a and b of W. */
const across = (W, n, a = 0.12, b = 0.88) => [...Array(n).keys()].map(i => W * (n === 1 ? (a + b) / 2 : a + ((b - a) * i) / (n - 1)))

function caption(c, x, y, str) {
  c.S.text(`cap:${str}:${x}`, x, y, str, { size: 18, fill: c.C.dim, anchor: 'middle', mono: true, box: `look caption ${str}` })
}

/** Colour and type: every theme colour with its role, and the type sizes with theirs. */
function palette(c) {
  const { S, W, H, header, unit } = c
  const narrow = W < H
  const top = header + unit * 0.9, rows = narrow ? 16 : 8, colW = narrow ? W * 0.9 : W * 0.3
  const step = Math.min(64, (H - top - unit * 0.4) / (narrow ? rows + SIZES.length + 1 : rows))
  ROLES.forEach(([name, role], i) => {
    const col = narrow ? 0 : Math.floor(i / rows), row = narrow ? i : i % rows
    const x = W * 0.05 + col * colW, y = top + row * step
    S.rect(`sw:${name}`, x, y - step * 0.36, step * 0.72, step * 0.72, { fill: `var(--${name})`, stroke: 'var(--line)', sw: 1.5, r: 6 })
    S.text(`sw:${name}:t`, x + step, y, `${name}  ${css(name)}  ${role}`, { size: 18, fill: 'var(--ink)', mono: true, box: `colour ${name}` })
  })
  const x0 = narrow ? W * 0.05 : W * 0.66
  let y = narrow ? top + (rows + 0.6) * step : top
  for (const [size, role] of SIZES) {
    S.text(`ty:${size}`, x0, y, `${size} px ${role}`, { size, weight: size >= 34 ? 700 : 500, box: `type ${size}` })
    y += Math.max(step * (narrow ? 1 : 0.9), size * 1.45)
  }
}

/** Boxes, arrows, tokens, a card, highlights: each element in each of its states. */
function elements(c) {
  const { S, W, H, header, unit, C } = c
  const rowH = (H - header) / 4, y = i => header + rowH * (i + 0.55)
  const bw = Math.min(260, W * 0.2), bh = Math.min(100, rowH * 0.5)
  // Boxes: idle, lit (the thing explained), failed; and a record whose fields are divided inside it.
  const xs = across(W, 4)
  ;[['idle', C.edge, C.tray, C.ink], ['lit', C.cold, '#1D3242', C.cold], ['failed', C.bad, C.tray, C.bad]].forEach(([state, stroke, fill, ink], i) => {
    S.rect(`box:${state}`, xs[i] - bw / 2, y(0) - bh / 2, bw, bh, { stroke, fill, sw: 3, r: 10, box: `box ${state}` })
    S.text(`box:${state}:t`, xs[i], y(0), 'server', { size: 30, anchor: 'middle', fill: ink })
    caption(c, xs[i], y(0) + bh / 2 + 22, state)
  })
  S.rect('box:record', xs[3] - bw / 2, y(0) - bh / 2, bw, bh, { stroke: C.edge, fill: C.tray, sw: 3, r: 10, box: 'box record' })
  S.line('box:record:div', xs[3], y(0) - bh / 2 + 3, xs[3], y(0) + bh / 2 - 3, { stroke: C.edge, sw: 1.5 })
  S.text('box:record:a', xs[3] - bw / 4, y(0), 'id', { size: 26, anchor: 'middle', mono: true })
  S.text('box:record:b', xs[3] + bw / 4, y(0), '42', { size: 26, anchor: 'middle', mono: true, fill: C.hot })
  caption(c, xs[3], y(0) + bh / 2 + 22, 'outline 3 > divider 1.5')
  // Arrows: idle, active, muted (the rest dimmed).
  const ax = across(W, 3, 0.18, 0.82), half = Math.min(150, W * 0.12)
  ;[['idle', C.dim, 3, 1], ['active', C.cold, 4, 1], ['muted', C.dim, 3, 0.3]].forEach(([state, stroke, sw, op], i) => {
    S.line(`arrow:${state}`, ax[i] - half, y(1), ax[i] + half, y(1), { stroke, sw, op, arrow: true, box: `arrow ${state}` })
    caption(c, ax[i], y(1) + 30, state)
  })
  // The token and its glyph states.
  const tx = across(W, 4, 0.2, 0.8), r = Math.min(26, rowH * 0.18)
  ;[['idle', '○', C.dim], ['ok', '✓', C.cold], ['failed', '✕', C.bad], ['waiting', '…', C.hot]].forEach(([state, glyph, color], i) => {
    S.circle(`token:${state}`, tx[i], y(2) - 8, r, { stroke: color, fill: C.bg2, sw: 3, box: `token ${state}` })
    S.text(`token:${state}:g`, tx[i], y(2) - 8, glyph, { size: 26, anchor: 'middle', fill: color, weight: 600 })
    caption(c, tx[i], y(2) + r + 14, state)
  })
  // A card of lines (one lit, one failed), a proposed change as a ghost, a callout and a strike-through.
  const cx = across(W, 3, 0.18, 0.82), cw = Math.min(360, W * 0.26), lh = 30
  S.rect('card', cx[0] - cw / 2, y(3) - lh * 1.8, cw, lh * 3.6, { stroke: C.edge, fill: C.tray, sw: 3, r: 12, box: 'card' })
  ;[['key: "a1"', C.dim], ['state: open', C.cold], ['retries: 3', C.bad]].forEach(([line, fill], i) =>
    S.text(`card:${i}`, cx[0] - cw / 2 + 24, y(3) + (i - 1) * lh, line, { size: 22, mono: true, fill }))
  S.rect('ghost', cx[1] - cw / 2, y(3) - lh * 1.2, cw, lh * 2.4, { stroke: C.cold, fill: 'rgba(143, 211, 255, 0.10)', sw: 2, r: 12, box: 'ghost' })
  S.text('ghost:t', cx[1], y(3), 'proposed', { size: 26, anchor: 'middle', fill: C.cold })
  S.text('strike', cx[2] - cw / 2 + 10, y(3) - lh * 0.6, 'one machine', { size: 26, mono: true, fill: C.bad })
  S.strike('strike:l', cx[2] - cw / 2 + 10, cx[2] - cw / 2 + 10 + 15.6 * 11, y(3) - lh * 0.6, 1)
  S.callout('callout', cx[2] - cw * 0.1, y(3) + lh * 2, cx[2] - cw * 0.3, y(3) - lh * 0.2, 'a callout', 1, { size: 22, fill: C.hot, dx: 10 })
}

/** The close-up, fully open from a map box, with its minimap. */
function closeUp(c) {
  const { S, W, view } = c
  const map = [[W * 0.2, 0, 220, 90], [W * 0.5 - 110, 0, 220, 90], [W * 0.8 - 220, 0, 220, 90]]
  const p = S.closeUp('closeup', view, { open: 1, from: map[1], name: 'server', map, of: 1 })
  S.rect('closeup:record', p.x + p.w / 2 - 300, p.y + p.h / 2 - 70, 600, 140, { stroke: 'var(--cold)', fill: 'rgba(143, 211, 255, 0.10)', sw: 2, r: 12, op: p.inner, box: 'ghost' })
  S.text('closeup:record:t', p.x + p.w / 2, p.y + p.h / 2, 'the record this chapter is about', { size: 30, anchor: 'middle', fill: 'var(--cold)', mono: true, op: p.inner })
  S.text('closeup:detail', p.x + p.w / 2, p.y + p.h / 2 + 130, 'a detail only this close-up needs', { size: 22, anchor: 'middle', fill: 'var(--dim)', mono: true, op: p.inner })
}

/** The video's colour legend: each meaning in its colour, as a swatch and a label, with the colour's name. */
function legendPage(c) {
  const { S, W, H, header, unit, legend, declared } = c
  const entries = Object.entries(legend), top = header + unit * 0.9
  const step = Math.min(84, (H - top - unit * 0.4) / Math.max(1, entries.length))
  entries.forEach(([meaning, colour], i) => {
    const x = W * 0.08, y = top + i * step, size = Math.min(30, step * 0.5)
    const name = String(declared[meaning]), hex = name.startsWith('#') ? '' : `  ${css(name)}`
    S.rect(`legend:${i}`, x, y - step * 0.32, step * 0.64, step * 0.64, { fill: colour, stroke: 'var(--line)', sw: 1.5, r: 6, box: `legend swatch ${meaning}`, means: meaning })
    S.text(`legend:${i}:t`, x + step, y, meaning, { size, weight: 600, fill: colour, box: `legend ${meaning}`, means: meaning })
    S.text(`legend:${i}:c`, x + step + Math.min(W * 0.3, 420), y, `${name}${hex}`, { size: Math.max(18, size * 0.75), fill: 'var(--dim)', mono: true, box: `legend colour ${meaning}` })
  })
}

export const LEGEND_PAGE = { title: 'colour legend', draw: legendPage }

export const PAGES = [
  { title: 'colour and type', draw: palette },
  { title: 'elements and states', draw: elements },
  { title: 'close-up', draw: closeUp },
]
