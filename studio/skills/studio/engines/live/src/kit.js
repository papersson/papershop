// The live engine's scene kit: motion helpers that are pure functions of time, and the theme. A scene
// module imports what it needs from here (`import {prog, ease} from '/engine/src/kit.js'`), or uses
// the same functions on its context (`c.P`, `c.kit`).
//
// The motion glossary (src/glossary.js) names these helpers: a note like "stagger these" or "ease
// out" maps to exactly one helper here. The maths is the engines' shared module
// (engines/shared/motion.js); only the defaults that are this kit's own are set here.

import * as motion from '../../shared/motion.js'

export { clamp, lerp, mix, ease, stagger, spring, track, rand, countUp } from '../../shared/motion.js'
export { phraseStart } from '../../shared/timing.js'

/** Progress 0..1 of a movement that starts at t0 and lasts d seconds. */
export const prog = (t, t0, d, e = motion.ease.inOut) => motion.prog(t, t0, d, e)

/** A quick rise and fall around t0: 0 → 1 → 0 over d seconds. */
export const pulse = (t, t0, d = 0.6) => motion.pulse(t, t0, d)

/** The theme, as CSS variables the stage's SVG resolves (render.html defines them). */
export const C = {
  bg: 'var(--bg)', bg2: 'var(--bg2)', bg3: 'var(--bg3)', panel: 'var(--panel)', line: 'var(--line)',
  ink: 'var(--ink)', dim: 'var(--dim)', faint: 'var(--faint)', hot: 'var(--hot)', warm: 'var(--warm)',
  cold: 'var(--cold)', bad: 'var(--bad)', good: 'var(--good)', log: 'var(--log)', key: 'var(--key)', water: 'var(--water)',
}
