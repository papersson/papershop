// Camera maths for the live and Remotion kits: a camera is the point it centres and a zoom, in the
// kit's own units (live: pixels, Remotion: stage units). Pure functions of time, like motion.js, so a
// camera move is one declaration and any frame of it renders alone. Each kit adds the header inset
// and its own names ({x, y, z} for S.cam, {cx, cy, zoom} for <Camera>); both resolve keys here, with
// the same default ease, so the same keys give the same camera in either engine.

import { clamp, ease } from './motion.js'

/** @typedef {{x: number, y: number, zoom: number}} Shot */
/** @typedef {import('./motion.js').Ease} Ease */
/** @typedef {import('./motion.js').EaseLike} EaseLike */

/** The ease of a camera key that names none, in every engine (whatever the kit's `keyed` defaults to). */
export const CAMERA_EASE = 'inOut'

/** @type {(e: EaseLike | undefined, i: number) => Ease} */
function easeOf(e, i) {
  const f = typeof e === 'function' ? e : ease[/** @type {keyof typeof ease} */ (e ?? CAMERA_EASE)]
  if (typeof f !== 'function') throw new Error(`camera key ${i}: no ease ${e}; known: ${Object.keys(ease).join(', ')}`)
  return f
}

/**
 * Checks every key before any frame is drawn, so a mistake fails at once rather than when its move
 * plays: times finite and in order (equal times are a cut), x, y finite, zoom finite and above 0, each
 * ease a function or a name in `ease`.
 * @param {[number, Shot, EaseLike?][]} keys
 */
export function checkKeys(keys) {
  if (!Array.isArray(keys) || !keys.length) throw new Error('a camera needs at least one key')
  keys.forEach(([time, k, e], i) => {
    if (!Number.isFinite(time)) throw new Error(`camera key ${i}: time ${time} is not a number`)
    if (i && time < keys[i - 1][0]) throw new Error(`camera key ${i}: time ${time} comes before the previous key's ${keys[i - 1][0]}; keys go in time order`)
    if (!k || !Number.isFinite(k.x) || !Number.isFinite(k.y)) throw new Error(`camera key ${i}: x and y must be numbers`)
    if (!Number.isFinite(k.zoom) || k.zoom <= 0) throw new Error(`camera key ${i}: a zoom above 0, not ${k.zoom}`)
    easeOf(e, i)
  })
}

/**
 * The camera at time t from keys [time, {x, y, zoom}, ease?] in time order. A key's ease (a function
 * or a name in `ease`, `e` otherwise, CAMERA_EASE by default) shapes the move into it. Between two
 * keys the zoom moves in proportion (its logarithm is interpolated), and the centre moves in step
 * with 1/zoom, so the move is a zoom about one fixed point: every point, the new subject included,
 * travels a straight line on screen and never swings out of frame on the way. At equal zooms (a pan)
 * that is a plain glide. Before the first key the camera is the first, after the last the last.
 * @param {number} t @param {[number, Shot, EaseLike?][]} keys @param {EaseLike} [e] @returns {Shot}
 */
export function cameraAt(t, keys, e) {
  checkKeys(keys)
  const first = keys[0][1]
  if (t <= keys[0][0]) return { x: first.x, y: first.y, zoom: first.zoom }
  for (let i = 1; i < keys.length; i++) {
    const [t1, b, e1] = keys[i], [t0, a] = keys[i - 1]
    if (t >= t1) continue
    const u = easeOf(e1 ?? e, i)(clamp((t - t0) / (t1 - t0)))
    const zoom = a.zoom * (b.zoom / a.zoom) ** u
    const span = 1 / a.zoom - 1 / b.zoom
    const w = Math.abs(span) < 1e-12 ? u : (1 / a.zoom - 1 / zoom) / span
    return { x: a.x + (b.x - a.x) * w, y: a.y + (b.y - a.y) * w, zoom }
  }
  const last = keys[keys.length - 1][1]
  return { x: last.x, y: last.y, zoom: last.zoom }
}

/**
 * The camera that fits a region [x0, y0, x1, y1] (any corner order), with `margin` round it, into a
 * view `w` × `h`: its centre, and the largest zoom that fits, clamped to [min, max].
 * @param {[number, number, number, number]} region @param {[number, number]} view
 * @param {{margin?: number, min?: number, max?: number}} [o] @returns {Shot}
 */
export function frameOn([ax, ay, bx, by], [w, h], { margin = 0, min = 0, max = Infinity } = {}) {
  const x0 = Math.min(ax, bx), x1 = Math.max(ax, bx), y0 = Math.min(ay, by), y1 = Math.max(ay, by)
  const zoom = clamp(Math.min(w / (x1 - x0 + 2 * margin), h / (y1 - y0 + 2 * margin)), min, max)
  return { x: (x0 + x1) / 2, y: (y0 + y1) / 2, zoom }
}
