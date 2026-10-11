// Camera maths for a 3D shot, as camera.js is for the 2D camera: pure functions of time, so a camera
// move is one declaration of keys [time, shot, ease?] and any frame of it renders alone. The live
// engine's 3D stage loads these matrices into its renderer, and SVG drawn to match a 3D model (a flat
// diagram, a label on a 3D point) projects through the same numbers, so the two agree by construction.
//
// A shot is what a director names, not a matrix (world units, y up):
//   target [x, y, z]   the point the camera looks at
//   az, el             degrees round the target: az 0 looks along -z, el 90 looks straight down
//   span               half the view's height, in world units, at the target's depth (2D's zoom, inverted)
//   fov                vertical field of view in degrees; a small one (1) is orthographic in all but name
// Holding span while fov changes is a dolly zoom: the target's plane keeps its size on screen, so a
// flat diagram seen at fov 1 opens into perspective without a jump ("open into depth"), and back
// ("flatten").

import { clamp, ease } from './motion.js'

/** @typedef {{target: number[], az: number, el: number, span: number, fov: number, moving?: boolean}} Shot */
/** @typedef {import('./motion.js').EaseLike} EaseLike */

/** The ease of a shot key that names none, as the 2D camera's. */
export const SHOT_EASE = 'inOut'
/** World units in front of and behind the target that the depth buffer covers, unless a shot says otherwise. */
export const DEPTH = 4000
const D = Math.PI / 180

/** @type {(e: EaseLike | undefined, i: number) => (x: number) => number} */
function easeOf(e, i) {
  const f = typeof e === 'function' ? e : ease[/** @type {keyof typeof ease} */ (e ?? SHOT_EASE)]
  if (typeof f !== 'function') throw new Error(`shot key ${i}: no ease ${e}; known: ${Object.keys(ease).join(', ')}`)
  return f
}

/**
 * Checks every key before any frame is drawn, so a mistake fails at once rather than when its move
 * plays: times finite and in order (equal times are a cut), a target of three numbers, az, el, span
 * and fov numbers, span above 0 and fov in (0, 170).
 * @param {[number, Shot, EaseLike?][]} keys
 */
export function checkShots(keys) {
  if (!Array.isArray(keys) || !keys.length) throw new Error('a 3D camera needs at least one key')
  keys.forEach(([time, s, e], i) => {
    if (!Number.isFinite(time)) throw new Error(`shot key ${i}: time ${time} is not a number`)
    if (i && time < keys[i - 1][0]) throw new Error(`shot key ${i}: time ${time} comes before the previous key's ${keys[i - 1][0]}; keys go in time order`)
    checkShot(s, `shot key ${i}`)
    easeOf(e, i)
  })
}

/** @param {Shot} s @param {string} [where] */
export function checkShot(s, where = 'shot') {
  if (!s || !Array.isArray(s.target) || s.target.length !== 3 || !s.target.every(Number.isFinite)) throw new Error(`${where}: target must be [x, y, z]`)
  for (const k of ['az', 'el', 'span', 'fov']) if (!Number.isFinite(s[k])) throw new Error(`${where}: ${k} must be a number`)
  if (s.span <= 0) throw new Error(`${where}: span must be above 0, not ${s.span}`)
  if (s.fov <= 0 || s.fov >= 170) throw new Error(`${where}: fov must be in (0, 170), not ${s.fov}`)
}

/**
 * The shot at t from keys [time, shot, ease?] in time order. A key's ease shapes the move into it.
 * Target, az and el move linearly through the ease; span and fov move in proportion (their logs),
 * as the 2D camera's zoom does. Before the first key the shot is the first, after the last the last.
 * Between keys the result carries `moving: true`, which the checks read as "the camera is moving".
 * @param {number} t @param {[number, Shot, EaseLike?][]} keys @param {EaseLike} [e] @returns {Shot}
 */
export function shotAt(t, keys, e) {
  checkShots(keys)
  const plain = s => ({ target: [...s.target], az: s.az, el: s.el, span: s.span, fov: s.fov })
  if (t <= keys[0][0]) return plain(keys[0][1])
  for (let i = 1; i < keys.length; i++) {
    const [t1, b, e1] = keys[i], [t0, a] = keys[i - 1]
    if (t >= t1) continue
    if (JSON.stringify(plain(a)) === JSON.stringify(plain(b))) return plain(a)     // a hold, not a move
    const u = easeOf(e1 ?? e, i)(clamp((t - t0) / Math.max(t1 - t0, 1e-9)))
    const lin = (x, y) => x + (y - x) * u, log = (x, y) => x * (y / x) ** u
    return { target: a.target.map((v, j) => lin(v, b.target[j])), az: lin(a.az, b.az), el: lin(a.el, b.el),
      span: log(a.span, b.span), fov: log(a.fov, b.fov), moving: true }
  }
  return plain(keys[keys.length - 1][1])
}

/**
 * Where the camera sits for a shot: its position, its distance from the target (so the target's
 * plane shows exactly `span` above and below the view's centre) and its up vector. At el 90 up is
 * the az direction, so a top view keeps its orientation instead of spinning.
 * @param {Shot} shot
 */
export function placement({ target, az, el, span, fov }) {
  const a = az * D, e = el * D
  const dist = span / Math.tan((fov * D) / 2)
  const back = [Math.sin(a) * Math.cos(e), Math.sin(e), Math.cos(a) * Math.cos(e)]   // target -> camera
  const up = [-Math.sin(a) * Math.sin(e), Math.cos(e), -Math.cos(a) * Math.sin(e)]
  return { position: target.map((v, j) => v + back[j] * dist), dist, up, back }
}

const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
const unit = a => { const n = Math.hypot(...a); return a.map(v => v / n) }

/**
 * The camera for a shot on a canvas `size` [W, H], centred in `view` [x, y, w, h] (the stage below the
 * header and above the caption band): column-major view and projection matrices (as WebGL and
 * three.js take them), the camera's world matrix, its position and its near and far planes. `span`
 * fills half the view's height; the principal point moves from the canvas's centre to the view's.
 * @param {Shot} shot @param {[number, number]} size @param {number[]} [view] @param {{depth?: number}} [o]
 */
export function camera(shot, [W, H], view = [0, 0, W, H], { depth = DEPTH } = {}) {
  checkShot(shot)
  const [vx, vy, vw, vh] = view
  const { position: p, dist, up, back } = placement(shot)
  const z = unit(back), x = unit(cross(up, z)), y = cross(z, x)
  const world = [...x, 0, ...y, 0, ...z, 0, ...p, 1]
  const viewM = [x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -dot(x, p), -dot(y, p), -dot(z, p), 1]
  const near = Math.max(0.5, dist - depth), far = dist + depth
  const f = dist / (shot.span * H / vh)                        // 1 / tan(half the canvas's vertical fov)
  const dx = (vx + vw / 2 - W / 2) / (W / 2), dy = (H / 2 - (vy + vh / 2)) / (H / 2)
  const proj = [f / (W / H), 0, 0, 0, 0, f, 0, 0, -dx, -dy, (far + near) / (near - far), -1, 0, 0, (2 * far * near) / (near - far), 0]
  return { view: viewM, proj, world, position: p, near, far, size: [W, H] }
}

/** A column-major 4×4 times [x, y, z, 1]. */
function apply(m, [x, y, z]) {
  return [0, 1, 2, 3].map(r => m[r] * x + m[4 + r] * y + m[8 + r] * z + m[12 + r])
}

/**
 * Screen pixels of a world point under a camera (from `camera`): [x, y, inFront], inFront false for a
 * point behind the camera or outside the depth range.
 * @param {{view: number[], proj: number[], size: number[]}} cam @param {number[]} point
 */
export function project(cam, point) {
  const [cx, cy, cz, cw] = apply(cam.proj, apply(cam.view, point))
  const [W, H] = cam.size
  if (cw <= 0) return [NaN, NaN, false]
  return [(cx / cw + 1) / 2 * W, (1 - cy / cw) / 2 * H, cz / cw >= -1 && cz / cw <= 1]
}

/** Screen pixels per world unit at a world point, along the screen's x (for SVG circles drawn to match). */
export function scaleAt(cam, point) {
  const a = project(cam, point), right = [cam.view[0], cam.view[4], cam.view[8]]
  const b = project(cam, point.map((v, j) => v + right[j]))
  return Math.hypot(b[0] - a[0], b[1] - a[1])
}

/**
 * The top-down shot under which world (x, z) at height `y` falls exactly where the 2D stage puts
 * pixel (x, y): with the 2D camera at rest ({x: W / 2, y: the view's middle, z: 1}) a world unit is a
 * pixel, so a flat SVG diagram and a 3D model built in the same coordinates coincide. `cam2d` follows
 * a moved 2D camera ({x, y, z} as camAt returns it). This is the shot a scene opens into depth from.
 * @param {{x: number, y: number, z: number}} cam2d @param {number} viewHeight @param {{y?: number, fov?: number}} [o]
 */
export function flatShot(cam2d, viewHeight, { y = 0, fov = 1 } = {}) {
  return { target: [cam2d.x, y, cam2d.y], az: 0, el: 90, span: viewHeight / 2 / cam2d.z, fov }
}

/**
 * "Frame on" in 3D: the shot at a given az, el and fov whose target and span fit world `points` in the
 * view with `margin` (a share of the view kept free on each side). Found by projecting, as the
 * perspective of a box's near and far corners differ: a few rounds settle it.
 * @param {number[][]} points @param {[number, number]} size @param {number[]} view
 * @param {{az?: number, el?: number, fov?: number, margin?: number}} [o] @returns {Shot}
 */
export function frameOn3(points, size, view, { az = 0, el = 30, fov = 30, margin = 0.08 } = {}) {
  if (!points.length) throw new Error('frameOn3 needs at least one point')
  const lo = [0, 1, 2].map(j => Math.min(...points.map(p => p[j]))), hi = [0, 1, 2].map(j => Math.max(...points.map(p => p[j])))
  let target = lo.map((v, j) => (v + hi[j]) / 2)
  let span = Math.max(1, Math.hypot(...hi.map((v, j) => v - lo[j])) / 2)
  const [vx, vy, vw, vh] = view
  for (let round = 0; round < 6; round++) {
    const cam = camera({ target, az, el, span, fov }, size, view)
    const pts = points.map(p => project(cam, p))
    const xs = pts.map(p => p[0]), ys = pts.map(p => p[1])
    const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)]
    const need = Math.max((x1 - x0) / (vw * (1 - 2 * margin)), (y1 - y0) / (vh * (1 - 2 * margin)))
    // Move the target so the projected box centres in the view, at the target's depth.
    const right = [cam.view[0], cam.view[4], cam.view[8]], up = [cam.view[1], cam.view[5], cam.view[9]]
    const perPx = (2 * span) / vh
    const ox = ((x0 + x1) / 2 - (vx + vw / 2)) * perPx, oy = ((y0 + y1) / 2 - (vy + vh / 2)) * perPx
    target = target.map((v, j) => v + right[j] * ox - up[j] * oy)
    span *= need
  }
  return { target, az, el, span, fov }
}
