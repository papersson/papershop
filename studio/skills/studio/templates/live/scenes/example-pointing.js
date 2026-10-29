// Pointing at what the narrator names, and outcome marks, on the screens layer (references/screens.md,
// "Pointing and outcome marks"). The log says when; the page only says where things are. Rename this
// chapter to s1.js. Its data/screens.json, with cues on the words ("phrase") and in the pauses ("end"):
//
//   {"desktops": [{"id": "apm", "kind": "browser", "tabs": [{"id": "trace", "title": "Trace", "url": "apm.example/trace/1004", "page": "trace"}]}],
//    "outcomeSounds": true,
//    "actions": [
//      {"at": "s1-calls", "on": "apm", "mark": "stock", "state": "running"},
//      {"at": "s1-basket", "on": "apm", "point": "basket", "until": "s1-basket-done"},
//      {"at": "s1-basket-done", "on": "apm", "mark": "basket", "state": "finished"},
//      {"at": "s1-fails", "on": "apm", "mark": "payment", "state": "failed"}]}
import { loadScreens, screensAt, screensCamera, drawScreens } from '@studio/screens-draw.js'
import { productFrame, waterfall } from '@studio/pages.js'

const scr = await loadScreens(import.meta.url)

// One checkout request and the calls it made, in seconds from its start.
const SPANS = [
  { id: 'checkout', name: 'checkout', start: 0, end: 4.1 },
  { id: 'basket', name: 'load basket', start: .04, end: .3 },
  { id: 'stock', name: 'check stock', start: .34, end: .62 },
  { id: 'payment', name: 'payment', start: .68, end: 3.85 },
  { id: 'receipt', name: 'send receipt', start: 3.88, end: 4.06 },
]

// The trace page: a waterfall whose rows are the targets points and marks name. A row's box runs from
// its label to its bar's end, so both stay lit; the underline goes under the bar alone (`line`). A row
// marked failed turns the problem colour, so the bar says it too.
function trace(c, box, tab, ctx) {
  const L = ctx.look, size = 30, labelW = 330
  const inner = productFrame(c, 'apm', box, { product: 'APM', title: 'checkout · trace 1004', look: L, recon: 'A mock trace view, for the trial' })
  const failed = id => Object.values(ctx.marks).some(m => m.target === id && m.state === 'failed')
  const spans = SPANS.map(s => ({ ...s, colour: failed(s.id) ? L.problem : L.keyword }))
  const area = { x: inner.x + 40, y: inner.y + 60, w: inner.w - 200, h: Math.min(inner.h - 120, SPANS.length * 80 + 80) }
  const { spans: bars } = waterfall(c, 'apm:wf', area, { spans, total: 4.2, look: L, labelW, size, title: '0 s ─────────── 4.2 s' })
  const targets = {}
  SPANS.forEach((s, k) => {
    const [x, y, w, h] = bars[k], left = area.x + labelW - s.name.length * size * .6
    targets[s.id] = { box: [left, y + h * .2, x + w - left, h * .6], line: [x, x + w] }
  })
  return { targets }
}

export default function draw(c) {
  const s = screensAt(c, scr)
  screensCamera(c, scr, s)
  drawScreens(c, scr, s, { pages: { trace } })
}
