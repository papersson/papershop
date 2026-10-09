// Camera maths for the live and Remotion kits: a camera is the point it centres and a zoom, in the
// kit's own units (live: pixels, Remotion: stage units). Pure functions of time, like motion.js, so a
// camera move is one declaration and any frame of it renders alone. Each kit adds the header inset
// and its own names ({x, y, z} for S.cam, {cx, cy, zoom} for <Camera>).

import { clamp, keyed } from './motion.js'

/** @typedef {{x: number, y: number, zoom: number}} Shot */
/** @typedef {import('./motion.js').EaseLike} EaseLike */

/**
 * The camera at time t from keys [time, {x, y, zoom}, ease?] sorted by time, through `keyed`: a key's
 * ease shapes the move into it (`e` otherwise). The zoom moves in proportion (its logarithm is what
 * is interpolated), so a push-in from 1 to 4 looks as fast near its end as near its start.
 * @param {number} t @param {[number, Shot, EaseLike?][]} keys @param {import('./motion.js').Ease} [e] @returns {Shot}
 */
export function cameraAt(t, keys, e) {
  if (!keys.length) throw new Error('a camera needs at least one key')
  for (const [, k] of keys) if (!(k.zoom > 0)) throw new Error(`a camera key needs a zoom above 0, not ${k.zoom}`)
  const at = /** @type {number[]} */ (keyed(t, keys.map(([time, k, ease]) => [time, [k.x, k.y, Math.log(k.zoom)], ease]), e))
  return { x: at[0], y: at[1], zoom: Math.exp(at[2]) }
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
