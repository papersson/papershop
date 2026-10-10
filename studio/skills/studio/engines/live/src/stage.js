// The live engine's stage: an immediate-mode SVG. A frame is a pure function of time: a scene calls
// the drawing helpers with the current time, and the stage creates, updates or hides keyed nodes to
// match. Nothing animates by itself, so any moment can be drawn directly (scrubbing, hot reload,
// stills, parallel render workers).
//
// Determinism: a node drawn in this frame has exactly the attributes this frame gave it (any left
// from an earlier frame are removed), and nodes stack in the order this frame drew them. So a frame
// drawn after any other frame is the same as the frame drawn alone.

export const NS = 'http://www.w3.org/2000/svg'

/** A node's colours for the legend check: fill and stroke, resolved, and its meaning tag. */
function paint(node) {
  const st = getComputedStyle(node), means = node.getAttribute('data-means')
  return { fill: st.fill, stroke: st.stroke, ...(means ? { means } : {}) }
}

export class Stage {
  /** svg: the <svg> element; width/height: the frame in pixels (the viewBox). */
  constructor(svg, { width = 1920, height = 1080 } = {}) {
    this.svg = svg
    this.width = width
    this.height = height
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`)
    // Layers, back to front: back (the background, which the camera never moves, so a push-in leaves
    // no seam), then bg, main and fx inside the camera, then over (overlays: a ladder, a clock, a
    // title card, the header's contents) and ui (the band), which the camera doesn't move either.
    this.layers = { back: this.make('g', svg) }
    this.camera = this.make('g', svg)
    for (const name of ['bg', 'main', 'fx']) this.layers[name] = this.make('g', this.camera)
    this.layers.over = this.make('g', svg)
    this.ui = this.make('g', svg)
    this.nodes = new Map()        // key -> {node, layer, attrs: Set}
    this.order = []               // keys in this frame's drawing order
  }

  make(tag, parent) {
    const n = document.createElementNS(NS, tag)
    parent.appendChild(n)
    return n
  }

  begin() {
    this.order = []
    this.drawn = new Set()
    this.cam(this.width / 2, this.height / 2, 1)
  }

  end() {
    for (const [key, rec] of this.nodes) rec.node.style.display = this.drawn.has(key) ? '' : 'none'
    // Stack the drawn nodes in this frame's order, layer by layer.
    for (const key of this.order) {
      const rec = this.nodes.get(key)
      rec.parent.appendChild(rec.node)
    }
  }

  /** Point the camera at (x, y) with zoom z: a push-in is z rising, a pan is (x, y) moving. */
  cam(x, y, z) {
    this.moved = z !== 1 || x !== this.width / 2 || y !== this.height / 2
    const tx = this.width / 2 - x * z, ty = this.height / 2 - y * z
    this.camera.setAttribute('transform', `translate(${tx} ${ty}) scale(${z})`)
  }

  /**
   * Create or update the keyed node with exactly these attributes. attrs.text sets its text;
   * attrs.box names it for the engine's boxes (the checks); text nodes are named by their key.
   * attrs.means tags it with a meaning from the video's colour legend (video.json legend), which
   * the legend check reads with its colours; any drawing call takes it as `means`.
   */
  el(key, tag, attrs = {}, layer = 'main') {
    let rec = this.nodes.get(key)
    if (!rec || rec.tag !== tag) {
      if (rec) rec.node.remove()
      const parent = layer === 'ui' ? this.ui : this.layers[layer] ?? this.layers.main
      rec = { node: this.make(tag, parent), parent, tag, attrs: new Set() }
      this.nodes.set(key, rec)
    }
    if (!this.drawn.has(key)) this.order.push(key)
    this.drawn.add(key)
    const now = new Set()
    for (const [k, v] of Object.entries(attrs)) {
      if (v === undefined || v === null) continue
      if (k === 'text') {
        if (rec.node.textContent !== String(v)) rec.node.textContent = v
        continue
      }
      const name = k === 'box' ? 'data-box' : k === 'means' ? 'data-means' : k
      now.add(name)
      rec.node.setAttribute(name, v)
    }
    for (const old of rec.attrs) if (!now.has(old)) rec.node.removeAttribute(old)
    rec.attrs = now
    return rec.node
  }

  rect(key, x, y, w, h, o = {}) {
    return this.el(key, 'rect', {
      x, y, width: Math.max(0, w), height: Math.max(0, h), rx: o.r ?? 10,
      fill: o.fill ?? 'none', stroke: o.stroke ?? 'none', 'stroke-width': o.sw ?? 3,
      opacity: o.op ?? 1, 'stroke-dasharray': o.dash, transform: o.transform, filter: o.filter, box: o.box, means: o.means,
    }, o.layer)
  }

  circle(key, cx, cy, r, o = {}) {
    return this.el(key, 'circle', {
      cx, cy, r: Math.max(0, r), fill: o.fill ?? 'none', stroke: o.stroke ?? 'none',
      'stroke-width': o.sw ?? 3, opacity: o.op ?? 1, box: o.box, means: o.means,
    }, o.layer)
  }

  text(key, x, y, str, o = {}) {
    return this.el(key, 'text', {
      x, y, text: str, fill: o.fill ?? 'var(--ink)', opacity: o.op ?? 1,
      'font-size': o.size ?? 32, 'font-weight': o.weight ?? 500,
      'text-anchor': o.anchor ?? 'start', 'dominant-baseline': 'middle',
      'font-family': o.mono ? 'var(--mono)' : 'var(--sans)', 'letter-spacing': o.ls,
      transform: o.transform, box: o.box ?? key, means: o.means, 'data-kind': 'text',
    }, o.layer)
  }

  /** A line that draws itself on as p goes 0 → 1 (a draw-on). */
  line(key, x1, y1, x2, y2, o = {}) {
    const p = o.p ?? 1
    return this.el(key, 'line', {
      x1, y1, x2: x1 + (x2 - x1) * p, y2: y1 + (y2 - y1) * p, stroke: o.stroke ?? 'var(--ink)',
      'stroke-width': o.sw ?? 3, opacity: p <= 0 ? 0 : o.op ?? 1, 'stroke-linecap': 'round',
      'stroke-dasharray': o.dash, 'marker-end': o.arrow && p > 0.05 ? 'url(#arrow)' : undefined, box: o.box, means: o.means,
    }, o.layer)
  }

  /** A path drawn on from 0 to p of its length. */
  path(key, d, o = {}) {
    const p = o.p ?? 1
    return this.el(key, 'path', {
      d, fill: o.fill ?? 'none', stroke: o.stroke ?? 'var(--ink)', 'stroke-width': o.sw ?? 3,
      opacity: p <= 0 ? 0 : o.op ?? 1, pathLength: o.p === undefined ? undefined : 1,
      'stroke-dasharray': o.p === undefined ? o.dash : `${p} 1`,
      'stroke-linecap': 'round', 'stroke-linejoin': 'round', filter: o.filter, box: o.box, means: o.means,
    }, o.layer)
  }

  /** A strike-through across [x1, x2] at height y, drawn on with p. */
  strike(key, x1, x2, y, p, o = {}) {
    return this.line(key, x1 - 6, y, x2 + 6, y, { p, stroke: o.stroke ?? 'var(--bad)', sw: o.sw ?? 4, layer: o.layer })
  }

  /** A label joined to its subject (tx, ty) by a thin leader line: a callout. */
  callout(key, x, y, tx, ty, str, p, o = {}) {
    const c = Math.min(1, Math.max(0, p))
    this.line(key + ':lead', x, y, tx, ty, { p: Math.min(1, c * 1.4), stroke: o.stroke ?? 'var(--dim)', sw: 2, layer: o.layer })
    this.text(key + ':txt', x + (o.dx ?? 0), y - 22, str, { ...o, op: Math.min(1, Math.max(0, c * 2 - 0.6)) })
  }

  /**
   * A close-up: one component or record, opened from its box. `open` runs 0 → 1: the box `from`
   * ([x, y, w, h]) grows into `area` (c.view, the stage below the header) less `pad`, then the header
   * (`name` only) and a corner minimap fade in. The minimap draws `map`, the map's boxes ([x, y, w, h]
   * each) without labels, and fills only the one at index `of`, in `accent`. The panel's outline (3)
   * is heavier than the minimap's (1.5). Returns the open panel {x, y, w, h} and `inner`, the opacity
   * the scene draws the contents with; contents may sit outside the panel, nothing clips them.
   * `means` tags the minimap's filled box with a legend meaning; untagged, the default accent's fill
   * is tagged "kit", the kit's own accent state, which the legend check leaves alone.
   */
  closeUp(key, area, { open = 1, from, name = '', map = [], of = -1, accent = 'var(--cold)', pad = 36, layer, means } = {}) {
    const [ax, ay, aw, ah] = area
    const x = ax + pad, y = ay + pad, w = aw - 2 * pad, h = ah - 2 * pad
    const inner = Math.min(1, Math.max(0, (open - 0.55) / 0.45))
    if (open <= 0) return { x, y, w, h, inner: 0 }
    const k = Math.min(1, open), [fx, fy, fw, fh] = from ?? [x, y, w, h]
    this.rect(key, fx + (x - fx) * k, fy + (y - fy) * k, fw + (w - fw) * k, fh + (h - fh) * k,
      { fill: 'var(--bg2)', stroke: 'var(--edge)', sw: 3, r: 18, op: Math.min(1, open * 3), box: 'close-up', layer })
    this.text(key + ':name', x + w / 2, y + 44, name, { size: 34, weight: 600, anchor: 'middle', op: inner, box: `close-up ${name}`, layer })
    if (map.length) {
      const x0 = Math.min(...map.map(b => b[0])), x1 = Math.max(...map.map(b => b[0] + b[2]))
      const y0 = Math.min(...map.map(b => b[1]))
      const mw = Math.min(368, w * 0.2), s = mw / Math.max(1, x1 - x0), ox = x + w - 24 - mw, oy = y + 24
      map.forEach(([mx, my, bw, bh], i) => this.rect(`${key}:mini${i}`, ox + (mx - x0) * s, oy + (my - y0) * s, bw * s, bh * s, {
        stroke: i === of ? accent : 'var(--dim)', fill: i === of ? accent : 'none', sw: 1.5, r: 3, op: inner, box: 'minimap', layer,
        means: i === of ? means ?? (accent === 'var(--cold)' ? 'kit' : undefined) : undefined,
      }))
    }
    return { x, y, w, h, inner }
  }

  /** A Gaussian blur of strength sd as a filter reference (blur together). */
  blur(id, sd) {
    let f = this.svg.querySelector(`#${id}`)
    if (!f) {
      const defs = this.svg.querySelector('defs') ?? this.make('defs', this.svg)
      f = this.make('filter', defs)
      f.setAttribute('id', id)
      for (const [k, v] of Object.entries({ x: '-20%', y: '-60%', width: '140%', height: '220%' })) f.setAttribute(k, v)
      this.make('feGaussianBlur', f)
    }
    f.firstChild.setAttribute('stdDeviation', sd)
    return sd > 0.05 ? `url(#${id})` : undefined
  }

  /**
   * Pixel boxes of every named node drawn this frame and visible (the engine's `boxes`), each with
   * its fill and stroke as the browser resolves them ("rgb(…)", "none") and its `means` tag, if any.
   */
  boxes() {
    const origin = this.svg.getBoundingClientRect()
    const sx = this.width / origin.width, sy = this.height / origin.height
    const out = []
    for (const key of this.order) {
      const { node } = this.nodes.get(key)
      const name = node.getAttribute('data-box')
      if (!name || Number(node.getAttribute('opacity') ?? 1) <= 0.001 || !node.textContent && node.tagName === 'text') continue
      const r = node.getBoundingClientRect()
      if (r.width <= 0 || r.height <= 0) continue
      // camera: drawn under a camera that has moved (not the ui layer), whose crop is the inframe check's, not bounds'
      out.push({ name, kind: node.getAttribute('data-kind') ?? '', x: (r.left - origin.left) * sx, y: (r.top - origin.top) * sy, w: r.width * sx, h: r.height * sy,
        opacity: Number(node.getAttribute('opacity') ?? 1), camera: !!this.moved && this.camera.contains(node),
        ...paint(node) })
    }
    return out
  }
}
