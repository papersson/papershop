// The live engine's scene kit: motion helpers that are pure functions of time, and the theme. A scene
// module imports what it needs from here (`import {prog, ease} from '/engine/src/kit.js'`), or uses
// the same functions on its context (`c.P`, `c.kit`).
//
// The motion glossary (src/glossary.js) names these helpers: a note like "stagger these" or "ease
// out" maps to exactly one helper here. The maths is the engines' shared module
// (engines/shared/motion.js); only the defaults that are this kit's own are set here.

import * as motion from '../../shared/motion.js'
import * as camera from '../../shared/camera.js'

export { clamp, lerp, mix, ease, stagger, spring, track, rand, rng, countUp, keyed, follow, settle, wobble } from '../../shared/motion.js'
export { phraseStart } from '../../shared/timing.js'

/** Progress 0..1 of a movement that starts at t0 and lasts d seconds. */
export const prog = (t, t0, d, e = motion.ease.inOut) => motion.prog(t, t0, d, e)

/** A quick rise and fall around t0: 0 → 1 → 0 over d seconds. */
export const pulse = (t, t0, d = 0.6) => motion.pulse(t, t0, d)

/**
 * The camera at time t from keys [time, {x, y, z}, ease?] in time order (pixels and a zoom, as S.cam
 * takes them): a key's ease shapes the move into it, `inOut` by default as in Remotion (the shared
 * camera's). The zoom moves in proportion and the centre in step with 1/zoom, so the subject travels
 * a straight line on screen. Returns {x, y, z}; c.camAt(keys) also points the stage's camera there.
 */
export function camAt(t, keys, e) {
  const c = camera.cameraAt(t, keys.map(([time, k, ease]) => [time, { x: k.x, y: k.y, zoom: k.z }, ease]), e)
  return { x: c.x, y: c.y, z: c.zoom }
}

/**
 * The camera {x, y, z} that fits a region [x0, y0, x1, y1] (pixels), with `margin` round it, into a
 * view w × h; c.frameOn(region) fits the stage below the header. A "frame on" key for camAt.
 */
export function frameOn(region, [w, h], { margin = 40, min = 0.25, max = 4 } = {}) {
  const c = camera.frameOn(region, [w, h], { margin, min, max })
  return { x: c.x, y: c.y, z: c.zoom }
}

/** The theme, as CSS variables the stage's SVG resolves (render.html defines them). */
export const C = {
  bg: 'var(--bg)', bg2: 'var(--bg2)', bg3: 'var(--bg3)', panel: 'var(--panel)', line: 'var(--line)',
  ink: 'var(--ink)', dim: 'var(--dim)', faint: 'var(--faint)', hot: 'var(--hot)', warm: 'var(--warm)',
  cold: 'var(--cold)', bad: 'var(--bad)', good: 'var(--good)', log: 'var(--log)', key: 'var(--key)', water: 'var(--water)',
  edge: 'var(--edge)', tray: 'var(--tray)',
}
