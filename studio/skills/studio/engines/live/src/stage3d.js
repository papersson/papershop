// The live engine's 3D stage (c.G): an immediate-mode three.js scene on a canvas under the SVG stage.
// Like stage.js, a frame is whatever this frame drew: every call names its node by a key and sets all
// of its state from t, and a node not drawn this frame is hidden, so any frame draws alone. One
// renderer and one canvas per page, created the first time a scene asks for c.G.
//
// The look is the house style's, not a film's: no scene lights. A face's tone comes from its normal
// against one fixed house light, in three steps (1, 0.8, 0.62 of its colour), so a face lit from above
// shows the palette colour exactly and a flat top view matches the SVG diagram of the same thing.
// Outlines are screen-space lines in pixels, so an outer contour can be 3 px over 1.5 px inner detail,
// as in 2D. A scene that calls G.lit() opts into the lit look instead, for a physical object the
// viewer should feel: physically based materials (roughness, metalness), a key light with soft
// shadows, a fill and a sky light, the same outlines. It costs more a frame and moves colours off the
// legend's exact values, so it is for the chapter that needs it (references/taste.md). The camera is shared/camera3d.js's: its matrices are loaded as they are, so SVG projected
// through camera3d.project lands on the pixels WebGL draws.

import * as THREE from 'three'
import { LineSegments2 } from 'three/addons/lines/LineSegments2.js'
import { LineSegmentsGeometry } from 'three/addons/lines/LineSegmentsGeometry.js'
import { LineMaterial } from 'three/addons/lines/LineMaterial.js'
import { SVGLoader } from 'three/addons/loaders/SVGLoader.js'
import { camera as cameraFor, project, scaleAt } from '../../shared/camera3d.js'

const D = Math.PI / 180
/** The house light a face's tone is measured against: from above, a little to the front and right. */
export const HOUSE_LIGHT = [0.35, 1, 0.55]
const LIGHT = new THREE.Vector3(...HOUSE_LIGHT).normalize()
/** The tones a face takes, brightest first, and the light's dot product each starts at. */
export const TONES = [[0.75, 1], [0.2, 0.8], [-Infinity, 0.62]]

const TONE_VERT = `
varying vec3 vN;
void main() {
  vN = normalize(mat3(modelMatrix) * normal);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`
const TONE_FRAG = `
uniform vec3 color; uniform float opacity; uniform vec3 light;
varying vec3 vN;
void main() {
  vec3 n = normalize(vN);
  if (!gl_FrontFacing) n = -n;
  float d = dot(n, light);
  float k = d > ${TONES[0][0].toFixed(2)} ? ${TONES[0][1].toFixed(2)} : (d > ${TONES[1][0].toFixed(2)} ? ${TONES[1][1].toFixed(2)} : ${TONES[2][1].toFixed(2)});
  gl_FragColor = vec4(color * k, opacity);
  #include <colorspace_fragment>
}`

const cssCache = new Map()
/** A theme colour (var(--cold), a theme name such as 'cold', or #rrggbb) as a THREE.Color. */
function colourOf(c) {
  if (!cssCache.has(c)) {
    let v = String(c)
    const m = v.match(/^var\((--[\w-]+)\)$/) ?? (/^[a-z][\w-]*$/.test(v) ? [null, `--${v}`] : null)
    if (m) v = getComputedStyle(document.documentElement).getPropertyValue(m[1]).trim()
    if (!v) throw new Error(`G: no colour ${c} (a theme colour, var(--name) or #rrggbb)`)
    cssCache.set(c, new THREE.Color(v))
  }
  return cssCache.get(c)
}

/** A colour as the browser reports an SVG node's ("rgb(r, g, b)", sRGB), so 2D and 3D boxes compare. */
function cssRgb(c) {
  const hex = colourOf(c).getHexString()
  return `rgb(${[0, 2, 4].map(i => parseInt(hex.slice(i, i + 2), 16)).join(', ')})`
}

/** The geometry of a solid; see mesh(). */
function geometryOf(kind, p) {
  if (kind === 'box') return new THREE.BoxGeometry(...p.size)
  if (kind === 'cylinder') return new THREE.CylinderGeometry(p.r, p.r, p.h, p.seg ?? 96)
  if (kind === 'tube') return new THREE.CylinderGeometry(p.r, p.r, p.h, p.seg ?? 96, 1, true)
  if (kind === 'sphere') return new THREE.SphereGeometry(p.r, p.seg ?? 48, Math.ceil((p.seg ?? 48) / 2))
  if (kind === 'ring') {
    const g = new THREE.RingGeometry(p.r0, p.r1, p.seg ?? 128)
    g.rotateX(-Math.PI / 2)
    return g
  }
  if (kind === 'extrude') {
    // An SVG path (stage pixels: x right, y down) as a slab: its outline lies in the world's x-z plane
    // (SVG y is world z) and it rises from y = 0 to y = depth, so the flat shot sees the path exactly.
    const svg = new SVGLoader().parse(`<svg xmlns="http://www.w3.org/2000/svg"><path d="${p.d}"/></svg>`)
    const shapes = svg.paths.flatMap(path => SVGLoader.createShapes(path))
    if (!shapes.length) throw new Error(`G.mesh extrude: the path ${JSON.stringify(p.d).slice(0, 60)} has no closed shape`)
    const g = new THREE.ExtrudeGeometry(shapes, { depth: p.depth, bevelEnabled: false, curveSegments: p.seg ?? 24 })
    g.rotateX(Math.PI / 2)
    g.translate(0, p.depth, 0)
    return g
  }
  throw new Error(`G.mesh: no kind ${kind} (box, cylinder, tube, sphere, ring, extrude)`)
}

export class Stage3D {
  /** canvas: the page's <canvas> under the SVG; width/height: the frame in pixels. */
  constructor(canvas, { width = 1920, height = 1080, antialias = true } = {}) {
    this.canvas = canvas
    this.W = width
    this.H = height
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias, preserveDrawingBuffer: true, powerPreference: 'high-performance' })
    this.renderer.setPixelRatio(1)
    this.renderer.setSize(width, height, false)
    this.renderer.autoClear = false
    this.scene = new THREE.Scene()
    this.cam = new THREE.PerspectiveCamera()
    this.cam.matrixAutoUpdate = false
    this.cam.matrixWorldAutoUpdate = false
    this.nodes = new Map()      // key -> {sig, obj, info}
    this.views = new Map()      // name -> {shot, rect, cam}
    this.drawn = new Set()
    this.area = [0, 0, width, height]
    this.lights = null          // the lit look's lights, made the first time a scene asks for them
    this.litMode = false
  }

  /** A new frame: nothing drawn yet. `area` is where the main view centres its shots (c.view). */
  begin(area) {
    this.drawn = new Set()
    this.views = new Map()
    this.litMode = false
    if (this.lights) for (const l of this.lights.all) l.visible = false
    if (area) this.area = area
  }

  /**
   * The lit look for this frame's solids (call it before drawing them): a key light from `key`
   * (a direction, default above, front and right) casting soft shadows, a fill from the other side
   * and a sky light, at `intensity` (1 is the default balance). Solids drawn after it take their
   * `roughness` (0.45) and `metalness` (0) from their options.
   */
  lit({ key = [0.6, 1, 0.8], intensity = 1, shadows = true } = {}) {
    if (!this.lights) {
      const keyLight = new THREE.DirectionalLight(0xffffff, 1)
      keyLight.shadow.mapSize.set(2048, 2048)
      keyLight.shadow.bias = -0.0005
      keyLight.shadow.radius = 4
      const fill = new THREE.DirectionalLight(0xffffff, 1)
      const sky = new THREE.HemisphereLight(0xffffff, 0x404850, 1)
      this.scene.add(keyLight, keyLight.target, fill, fill.target, sky)
      this.renderer.shadowMap.type = THREE.PCFSoftShadowMap
      this.lights = { key: keyLight, fill, sky, all: [keyLight, fill, sky] }
    }
    const L = this.lights
    L.key.intensity = 2.2 * intensity
    L.fill.intensity = 0.6 * intensity
    L.sky.intensity = 0.9 * intensity
    L.key.castShadow = shadows
    L.dir = new THREE.Vector3(...key).normalize()
    for (const l of L.all) l.visible = true
    this.renderer.shadowMap.enabled = shadows
    this.litMode = true
  }

  /**
   * Point a view's camera: a shot {target, az, el, span, fov} (shared/camera3d.js). The main view
   * covers the canvas and centres its shot in the stage below the header and above the band; another
   * view (`view: 'name'`, with `rect` [x, y, w, h] in pixels) is a panel of its own, for drawing two
   * things side by side without one camera stretching both (a look sheet's items). Returns the shot.
   */
  camera(shot, { view = 'main', rect, depth } = {}) {
    const full = view === 'main' && !rect
    const r = rect ?? [0, 0, this.W, this.H]
    const cam = full ? cameraFor(shot, [this.W, this.H], this.area, { depth }) : cameraFor(shot, [r[2], r[3]], [0, 0, r[2], r[3]], { depth })
    this.views.set(view, { shot, rect: r, cam })
    return shot
  }

  /** The view a node is drawn in, its camera set. */
  view(name = 'main') {
    const v = this.views.get(name)
    if (!v) throw new Error(`G: no camera for the view ${JSON.stringify(name)}: call c.shot(keys) or G.camera(shot${name === 'main' ? '' : `, {view: '${name}', rect}`}) first`)
    return v
  }

  /** Screen pixels [x, y, inFront] of a world point in a view (for SVG labels and diagrams drawn to match). */
  project(p, view = 'main') {
    const v = this.view(view), [x, y, front] = project(v.cam, p)
    return [x + v.rect[0], y + v.rect[1], front]
  }

  /** Screen pixels per world unit at a world point, along the screen's x. */
  scaleAt(p, view = 'main') {
    return scaleAt(this.view(view).cam, p)
  }

  /** A circle of radius r in the plane y = c[1] round (c[0], c[2]), as world points. */
  circle([cx, cy, cz], r, n = 128) {
    return Array.from({ length: n }, (_, i) => [cx + r * Math.cos((i / n) * 2 * Math.PI), cy, cz + r * Math.sin((i / n) * 2 * Math.PI)])
  }

  node(key, sig, make) {
    let rec = this.nodes.get(key)
    if (!rec || rec.sig !== sig) {
      if (rec) this.dispose(rec)
      rec = { sig, obj: make() }
      this.scene.add(rec.obj)
      this.nodes.set(key, rec)
    }
    this.drawn.add(key)
    return rec
  }

  dispose(rec) {
    this.scene.remove(rec.obj)
    rec.obj.traverse(o => { o.geometry?.dispose(); o.material?.dispose?.() })
  }

  /**
   * A solid. kind and its params: box {size: [w, h, d]}, cylinder {r, h}, tube {r, h} (open, both
   * sides), sphere {r}, ring {r0, r1} (flat, facing up), extrude {d, depth} (an SVG path in stage
   * pixels, rising from y = 0). Options: at [x, y, z], rot [x, y, z] in degrees, scale (a number or
   * [x, y, z]), color (a theme colour; default the tray), op, edges {width, color} (outlines at its
   * creases, in pixels), view, box (a name for the checks), means (a legend meaning). Geometry is
   * built again only when the kind, params or edge width change; everything else is set every frame.
   */
  mesh(key, kind, params, o = {}) {
    const lit = this.litMode
    const rec = this.node(key, `${kind}:${JSON.stringify(params)}:${o.edges ? o.edges.width : ''}:${lit}`, () => {
      const geo = geometryOf(kind, params)
      // Faces sit a little behind their own outlines, or a face wins the depth test against the line on its edge.
      const offset = { polygonOffset: true, polygonOffsetFactor: 2, polygonOffsetUnits: 8 }
      const mat = lit ? new THREE.MeshStandardMaterial(offset) : new THREE.ShaderMaterial({ vertexShader: TONE_VERT,
        fragmentShader: TONE_FRAG, uniforms: { color: { value: new THREE.Color() }, opacity: { value: 1 }, light: { value: LIGHT } },
        ...offset })
      const m = new THREE.Mesh(geo, mat)
      m.castShadow = m.receiveShadow = lit
      if (o.edges) {
        const lg = new LineSegmentsGeometry().fromEdgesGeometry(new THREE.EdgesGeometry(geo, 30))
        const line = new LineSegments2(lg, new LineMaterial({ linewidth: o.edges.width, worldUnits: false }))
        line.material.resolution.set(this.W, this.H)
        m.add(line)
      }
      return m
    })
    const m = rec.obj, op = o.op ?? 1
    m.position.set(...(o.at ?? [0, 0, 0]))
    m.rotation.set(...(o.rot ?? [0, 0, 0]).map(a => a * D))
    const s = o.scale ?? 1
    Array.isArray(s) ? m.scale.set(...s) : m.scale.setScalar(s)
    const color = o.color ?? 'var(--tray)'
    const mat = m.material
    if (mat.uniforms) {
      mat.uniforms.color.value.copy(colourOf(color))
      mat.uniforms.opacity.value = op
    } else {
      mat.color.copy(colourOf(color))
      mat.opacity = op
      mat.roughness = o.roughness ?? 0.45
      mat.metalness = o.metalness ?? 0
    }
    mat.transparent = op < 1
    mat.depthWrite = op >= 1
    mat.side = kind === 'tube' || kind === 'ring' ? THREE.DoubleSide : THREE.FrontSide
    for (const line of m.children) {
      line.material.color.copy(colourOf(o.edges?.color ?? 'var(--edge)'))
      line.material.opacity = op
      line.material.transparent = op < 1
      line.visible = op > 0.001
    }
    m.visible = op > 0.001
    rec.info = { kind: 'mesh', view: o.view ?? 'main', name: o.box, means: o.means, color, stroke: o.edges?.color, op }
    return m
  }

  /** A polyline through world points, `width` px wide whatever its distance (loop closes it). Options as mesh's. */
  line(key, points, o = {}) {
    const n = points.length, segs = o.loop ? n : n - 1
    const rec = this.node(key, `line:${segs}`, () => {
      const l = new LineSegments2(new LineSegmentsGeometry(), new LineMaterial({ worldUnits: false }))
      l.material.resolution.set(this.W, this.H)
      return l
    })
    const pos = []
    for (let i = 0; i < segs; i++) pos.push(...points[i], ...points[(i + 1) % n])
    rec.obj.geometry.setPositions(pos)
    const mat = rec.obj.material, op = o.op ?? 1, color = o.color ?? 'var(--edge)'
    mat.linewidth = o.width ?? 2
    mat.color.copy(colourOf(color))
    mat.opacity = op
    mat.transparent = op < 1
    rec.obj.visible = op > 0.001
    rec.info = { kind: 'line', view: o.view ?? 'main', name: o.box, means: o.means, color, op, points }
    return rec.obj
  }

  /** Hide what this frame didn't draw and render each view; with nothing drawn, hide the canvas. Returns whether it drew. */
  end() {
    for (const [key, rec] of this.nodes) if (!this.drawn.has(key)) rec.obj.visible = false
    const used = new Set([...this.drawn].map(k => this.nodes.get(k).info?.view ?? 'main'))
    for (const name of used) this.view(name)         // a node in a view with no camera fails, naming the view
    this.active = used.size > 0
    this.canvas.style.display = this.active ? 'block' : 'none'
    if (!this.active) return false
    if (this.litMode) this.aimLights()
    const r = this.renderer
    r.setRenderTarget(null)
    r.setScissorTest(false)
    r.setViewport(0, 0, this.W, this.H)
    r.setClearColor(colourOf('var(--bg)'), 1)
    r.clear()
    for (const name of used) this.renderView(name, null)
    r.getContext().finish()
    return true
  }

  /** Point the lit look's lights at what this frame drew, the key's shadow camera fitted around it. */
  aimLights() {
    const box = new THREE.Box3()
    for (const key of this.drawn) {
      const rec = this.nodes.get(key)
      if (rec.obj.isMesh && rec.obj.visible) box.expandByObject(rec.obj)
    }
    if (box.isEmpty()) return
    const centre = box.getCenter(new THREE.Vector3()), r = Math.max(1, box.getSize(new THREE.Vector3()).length() / 2)
    const L = this.lights, sc = L.key.shadow.camera
    L.key.position.copy(centre).addScaledVector(L.dir, r * 3)
    L.key.target.position.copy(centre)
    L.fill.position.copy(centre).add(new THREE.Vector3(-L.dir.x, L.dir.y * 0.5, -L.dir.z).multiplyScalar(r * 3))
    L.fill.target.position.copy(centre)
    Object.assign(sc, { left: -r * 1.2, right: r * 1.2, top: r * 1.2, bottom: -r * 1.2, near: r * 0.5, far: r * 6 })
    sc.updateProjectionMatrix()
    L.key.target.updateMatrixWorld()
    L.fill.target.updateMatrixWorld()
  }

  /** Load a view's camera into three's, and show only that view's drawn nodes. */
  useView(name, only) {
    const v = this.view(name)
    this.cam.matrix.fromArray(v.cam.world)
    this.cam.matrixWorld.fromArray(v.cam.world)
    this.cam.matrixWorldInverse.fromArray(v.cam.view)
    this.cam.projectionMatrix.fromArray(v.cam.proj)
    this.cam.projectionMatrixInverse.fromArray(v.cam.proj).invert()
    for (const [key, rec] of this.nodes) {
      const mine = this.drawn.has(key) && (rec.info?.view ?? 'main') === name
      rec.obj.visible = mine && (only ? only(rec) : rec.info.op > 0.001)
    }
    // A line's width is in pixels of the viewport it is drawn into.
    this.scene.traverse(o => { if (o.isLineSegments2) o.material.resolution.set(v.rect[2], v.rect[3]) })
    return v
  }

  renderView(name, target, scale = 1) {
    const r = this.renderer, v = this.useView(name)
    const [x, y, w, h] = v.rect.map(n => n * scale), H = this.H * scale
    r.setViewport(x, H - y - h, w, h)
    r.setScissor(x, H - y - h, w, h)
    r.setScissorTest(true)
    r.clearDepth()
    r.render(this.scene, this.cam)
    r.setScissorTest(false)
    for (const [key, rec] of this.nodes) rec.obj.visible = this.drawn.has(key) && rec.info.op > 0.001
  }

  /**
   * The engine's boxes for named 3D nodes: projected geometry bounds in output pixels (clipped at the
   * camera's near plane: `behind` says some of it is behind the camera; and to the view's rect, which
   * crops it on screen: `clipped` says the box is the part inside, or, wholly outside, the unclipped
   * bounds the checks report as out of frame), the legend's fill, stroke and
   * means, `camera` while the view's shot is moving (as a moving 2D camera's boxes are marked), and
   * `visible`, the share of its pixels no opaque node covers, from object masks (a quarter-resolution
   * pass of the node alone, and one with every opaque node of its view in front of it). The masks cost
   * two small renders a node, so boxes are for the checks; a render never asks for them.
   */
  boxes({ masks = true } = {}) {
    if (!this.active) return []
    const out = []
    for (const [key, rec] of this.nodes) {
      if (!this.drawn.has(key) || !rec.info?.name || rec.info.op <= 0.001) continue
      const v = this.view(rec.info.view), b = this.bounds(rec, v)
      if (!b) continue
      const [, , rw, rh] = v.rect, c = { x0: Math.max(b.x0, 0), y0: Math.max(b.y0, 0), x1: Math.min(b.x1, rw), y1: Math.min(b.y1, rh) }
      const inside = c.x1 > c.x0 && c.y1 > c.y0, clipped = !inside || c.x0 > b.x0 || c.y0 > b.y0 || c.x1 < b.x1 || c.y1 < b.y1
      const k = inside ? c : b
      const col = cssRgb(rec.info.color)
      out.push({ name: rec.info.name, kind: '3d', x: k.x0 + v.rect[0], y: k.y0 + v.rect[1], w: k.x1 - k.x0, h: k.y1 - k.y0,
        opacity: rec.info.op, camera: !!v.shot.moving, fill: rec.info.kind === 'line' ? 'none' : col,
        stroke: rec.info.kind === 'line' ? col : rec.info.stroke ? cssRgb(rec.info.stroke) : 'none',
        ...(rec.info.means ? { means: rec.info.means } : {}), ...(b.behind ? { behind: true } : {}), ...(clipped ? { clipped: true } : {}), rec })
    }
    if (masks) this.visibility(out)
    return out.map(({ rec, ...b }) => b)
  }

  /** A node's projected bounds in its view: every vertex in front of the near plane, and where its edges cross it. */
  bounds(rec, v) {
    const o = rec.obj
    o.updateMatrixWorld(true)
    const m = o.matrixWorld.elements, V = v.cam.view, P = v.cam.proj, [W, H] = v.cam.size
    const toClip = ([x, y, z]) => {
      const w = [0, 1, 2].map(r => m[r] * x + m[4 + r] * y + m[8 + r] * z + m[12 + r])
      const e = [0, 1, 2, 3].map(r => V[r] * w[0] + V[4 + r] * w[1] + V[8 + r] * w[2] + V[12 + r])
      return [0, 1, 2, 3].map(r => P[r] * e[0] + P[4 + r] * e[1] + P[8 + r] * e[2] + P[12 + r] * e[3])
    }
    let pts, edges
    if (rec.info.kind === 'line') {
      pts = rec.info.points.map(p => toClip(p))
      edges = pts.map((_, i) => [i, (i + 1) % pts.length])
    } else {
      const pos = o.geometry.attributes.position, idx = o.geometry.index
      pts = Array.from({ length: pos.count }, (_, i) => toClip([pos.getX(i), pos.getY(i), pos.getZ(i)]))
      edges = []
      const n = idx ? idx.count : pos.count, at = i => (idx ? idx.getX(i) : i)
      for (let i = 0; i + 2 < n; i += 3) edges.push([at(i), at(i + 1)], [at(i + 1), at(i + 2)], [at(i + 2), at(i)])
    }
    const EPS = 1e-6
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity, behind = false
    const add = c => {
      const sx = (c[0] / c[3] + 1) / 2 * W, sy = (1 - c[1] / c[3]) / 2 * H
      x0 = Math.min(x0, sx); y0 = Math.min(y0, sy); x1 = Math.max(x1, sx); y1 = Math.max(y1, sy)
    }
    // A point in front of the near plane has clip z above -w; one behind it is replaced by where its edges cross.
    const front = c => c[2] > -c[3] + EPS
    pts.forEach(c => (front(c) ? add(c) : (behind = true)))
    if (behind) for (const [a, b] of edges) {
      const A = pts[a], B = pts[b]
      if (front(A) === front(B)) continue
      const da = A[2] + A[3], db = B[2] + B[3], u = da / (da - db)
      add(A.map((v, j) => v + (B[j] - v) * u))
    }
    return x1 > x0 ? { x0, y0, x1, y1, behind } : null
  }

  visibility(boxes) {
    const s = 0.25, w = Math.round(this.W * s), h = Math.round(this.H * s)
    this.rt ??= new THREE.WebGLRenderTarget(w, h)
    const white = new THREE.MeshBasicMaterial({ color: 0xffffff, side: THREE.DoubleSide })
    const black = new THREE.MeshBasicMaterial({ color: 0x000000, side: THREE.DoubleSide })
    const buf = new Uint8Array(w * h * 4)
    const meshes = [...this.nodes.values()].filter(r => r.obj.isMesh && !r.obj.isLineSegments2)
    const saved = meshes.map(r => [r, r.obj.material])
    const edges = []
    this.scene.traverse(o => { if (o.isLineSegments2 && o.parent?.isMesh) edges.push([o, o.visible]) })
    const r = this.renderer
    const count = (view, only) => {
      r.setRenderTarget(this.rt)
      r.setClearColor(0x000000, 1)
      r.setViewport(0, 0, w, h)
      r.clear()
      this.useView(view, only)
      for (const [e] of edges) e.visible = false
      const v = this.view(view), [x, y, vw, vh] = v.rect.map(n => n * s)
      r.setViewport(x, h - y - vh, vw, vh)
      r.render(this.scene, this.cam)
      r.readRenderTargetPixels(this.rt, 0, 0, w, h, buf)
      let n = 0
      for (let i = 0; i < buf.length; i += 4) if (buf[i] > 127) n++
      return n
    }
    try {
      for (const b of boxes) {
        const target = b.rec
        if (target.info.kind === 'line') continue
        for (const [m] of saved) m.obj.material = m === target ? white : black
        const alone = count(target.info.view, rec => rec === target)
        const seen = count(target.info.view, rec => rec === target || (rec.obj.isMesh && !rec.obj.isLineSegments2 && rec.info.op >= 0.5))
        b.visible = alone ? +(seen / alone).toFixed(3) : 0
      }
    } finally {
      for (const [m, mat] of saved) m.obj.material = mat
      for (const [e, vis] of edges) e.visible = vis
      for (const [key, rec] of this.nodes) rec.obj.visible = this.drawn.has(key) && rec.info.op > 0.001
      r.setRenderTarget(null)
      r.setViewport(0, 0, this.W, this.H)
      white.dispose()
      black.dispose()
    }
  }

  /** The renderer and context the page is using, for the record (doctor prints it). */
  info() {
    const gl = this.renderer.getContext(), ext = gl.getExtension('WEBGL_debug_renderer_info')
    return { renderer: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
      version: gl.getParameter(gl.VERSION), samples: gl.getParameter(gl.SAMPLES), three: THREE.REVISION }
  }
}
