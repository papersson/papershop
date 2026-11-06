// A live chapter drawn in light: one click fans out into dozens of requests to many servers, each a
// light going out along a curve and an answer streaming back, with the page's own answer the one warm
// thing (copy to scenes/<clip>.js and name the cue in cues.json). Use the light layer for a picture of
// scale (traffic, a whole network, many requests at once) where a few SVG shapes would not show how
// much there is; one request between two boxes stays SVG.
//
// c.L draws in the SVG's world coordinates through the same camera, so the SVG labels below sit on the
// lights and a push-in moves both. Light adds up, so crowded places glow. The layer paints the
// background itself: draw nothing opaque in the SVG's back layer. Everything comes from t and fixed
// seeds (kit.rand), never Math.random, so any frame draws alone.

const SERVERS = [['{{the shop}}', 980, 540], ['images', 1260, 330], ['images', 1330, 780], ['scripts', 1180, 200],
  ['fonts', 1420, 150], ['prices', 1120, 880], ['reviews', 1560, 940], ['analytics', 1640, 520], ['ads', 1700, 190],
  ['ads', 1840, 300], ['chat', 1500, 640], ['maps', 1800, 760]]
const FROM = [480, 540]                               // where the browser's requests leave

export default function draw(c) {
  const { S, L, t, kit } = c
  const { rand, clamp, ease } = kit
  const click = c.cue('{{the click}}')
  // The requests: the page first, then three waves (what the page names, what its scripts ask for, the ads).
  const reqs = [[0, click + 0.1, 0.9]]
  ;[[1.1, [1, 2, 3, 4, 0]], [2.2, [5, 6, 7, 10, 11]], [3.2, [8, 9, 7]]].forEach(([dt, list], w) =>
    list.forEach((s, k) => { for (let i = 0; i < 4; i++) reqs.push([s, click + dt + rand(w * 97 + k * 13 + i) * 0.5, 0.6 + rand(500 + w * 97 + k * 13 + i) * 0.5]) }))

  reqs.forEach(([s, t0, d], i) => {
    if (t < t0) return
    const [, x, y] = SERVERS[s], bow = (rand(900 + i) - 0.5) * 0.5
    const mid = [(FROM[0] + x) / 2 - (y - FROM[1]) * bow, (FROM[1] + y) / 2 + (x - FROM[0]) * bow]
    const at = k => { const u = 1 - k; return [u * u * FROM[0] + 2 * u * k * mid[0] + k * k * x, u * u * FROM[1] + 2 * u * k * mid[1] + k * k * y] }
    const k = (t - t0) / d, go = clamp(k / 0.45), back = (k - 0.5) / 0.5
    // the trace the trip leaves, fading after it
    const trace = 0.08 + 0.25 * Math.exp(-Math.max(0, t - t0 - d) / 1.2)
    for (let j = 1; j <= 24 * go; j++) { const a = at((j - 1) / 24), b = at(j / 24); L.line(a[0], a[1], b[0], b[1], 1.1, 'cold', trace) }
    if (go < 1) { const [px, py] = at(ease.inOut(go)); L.point(px, py, 5, 'ink', 0.25); L.point(px, py, 1.6, 'ink') }
    // the answer streams back: the page's own answer is the one warm thing
    if (back > 0 && back < 1.25) for (let p = 0; p < 8; p++) {
      const q = ease.inOut(clamp(back - p * 0.03))
      if (q <= 0 || q >= 1) continue
      const [px, py] = at(1 - q)
      if (s === 0) L.point(px, py, 9, 'hot', 0.18)
      L.point(px, py, s === 0 ? 3 : 2, s === 0 ? 'hot' : 'ink', 0.9)
    }
  })
  SERVERS.forEach(([name, x, y], s) => {
    const used = reqs.some(([q, t0]) => q === s && t >= t0)
    L.point(x, y, 3.2, 'ink', used ? 0.95 : 0.35)
    S.text(`server${s}`, x, y + 30, name, { size: 20, anchor: 'middle', fill: used ? 'var(--ink)' : 'var(--dim)', box: `server ${name}` })
  })
  L.point(FROM[0], FROM[1], 4, 'warm', 0.5 + 0.5 * Math.exp(-Math.max(0, t - click) / 0.3) * (t > click ? 1 : 0))
  const sent = reqs.filter(([, t0]) => t >= t0).length
  S.text('count', 120, 160, `${sent} ${sent === 1 ? 'request' : 'requests'}`, { size: 40, box: 'request count' })
  L.look({ bloom: 1.5 })
}
