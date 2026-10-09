// Motion maths for every engine: pure functions of time, so any frame renders alone. Plain ES
// modules with JSDoc types: the live engine serves this file as it is, and the Remotion and Motion
// Canvas kits import it through their bundlers. A default the engines disagree on (pulse's length,
// prog's and ramp's ease) is the engine kit's, so the functions here take those arguments.

/** @type {(x: number, a?: number, b?: number) => number} */
export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x))
/** @type {(a: number, b: number, p: number) => number} */
export const lerp = (a, b, p) => a + (b - a) * p
/** Element-wise lerp of two arrays (points, colours as [r, g, b]). @type {(a: number[], b: number[], p: number) => number[]} */
export const mix = (a, b, p) => a.map((v, i) => lerp(v, b[i], p))

/** @typedef {(x: number) => number} Ease */

/** Manim's default "smooth": a sigmoid rescaled to run exactly 0 → 1. @type {Ease} */
export const smooth = x => {
  const c = clamp(x), s = v => 1 / (1 + Math.exp(-v))
  return (s(10 * (c - 0.5)) - s(-5)) / (s(5) - s(-5))
}

/** Easing curves: how a movement speeds up and slows down. */
export const ease = {
  /** @type {Ease} */ linear: x => x,
  /** @type {Ease} */ in: x => x * x * x,
  /** @type {Ease} */ out: x => 1 - (1 - x) ** 3,
  /** @type {Ease} */ inOut: x => (x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2),
  /** @type {Ease} */ back: x => {
    const c = 1.70158, c3 = c + 1
    return 1 + c3 * (x - 1) ** 3 + c * (x - 1) ** 2
  },
  smooth,
}

/** Progress 0..1 of a movement that starts at t0 and lasts d seconds, through ease e. @type {(t: number, t0: number, d: number, e: Ease) => number} */
export const prog = (t, t0, d, e) => e(clamp((t - t0) / Math.max(d, 1e-6)))

/** 0 before `start`, 1 after `start + dur`, eased in between (e clamps its input). @type {(t: number, start: number, dur: number, e: Ease) => number} */
export const ramp = (t, start, dur, e) => (dur <= 0 ? (t >= start ? 1 : 0) : e((t - start) / dur))

/** Start of item i when items enter one after another, `gap` seconds apart. @type {(t0: number, i: number, gap?: number) => number} */
export const stagger = (t0, i, gap = 0.12) => t0 + i * gap

/** A quick rise and fall: 0 → 1 → 0 over d seconds from t0. @type {(t: number, t0: number, d: number) => number} */
export const pulse = (t, t0, d) => {
  const x = (t - t0) / d
  return x <= 0 || x >= 1 ? 0 : Math.sin(Math.PI * x)
}

/**
 * Closed-form damped spring from 0 to 1 (stiffness k, damping d): a pure function of time.
 * @param {number} t @param {number} [k] @param {number} [d] @returns {number}
 */
export function spring(t, k = 170, d = 26) {
  if (t <= 0) return 0
  const w0 = Math.sqrt(k)
  const z = d / (2 * w0)
  if (z < 1) {
    const wd = w0 * Math.sqrt(1 - z * z)
    return 1 - Math.exp(-z * w0 * t) * (Math.cos(wd * t) + ((z * w0) / wd) * Math.sin(wd * t))
  }
  return 1 - Math.exp(-w0 * t) * (1 + w0 * t)
}

/**
 * A value that changes target several times: keys are [time, value] sorted by time, and each change
 * adds one spring starting at its own time, so the motion stays continuous and any frame still
 * renders alone (no simulating frames 0..n-1).
 * @param {number} t @param {[number, number][]} keys @param {number} [k] @param {number} [d] @returns {number}
 */
export function track(t, keys, k = 170, d = 26) {
  let v = keys[0][1]
  for (let i = 1; i < keys.length; i++) v += (keys[i][1] - keys[i - 1][1]) * spring(t - keys[i][0], k, d)
  return v
}

/** Text inside a morphing container: in just after the morph starts, out just before the next one. @type {(t: number, tIn: number, tOut: number) => number} */
export const swapAlpha = (t, tIn, tOut) => Math.min(clamp((t - tIn - 0.08) / 0.12), clamp((tOut - 0.1 - t) / 0.1))

/** Wrap time so a piece loops seamlessly: pin the last frame's state to the first's. @type {(t: number, dur: number) => number} */
export const loopT = (t, dur) => ((t % dur) + dur) % dur

/** Deterministic pseudo-random in 0..1 for an integer seed (never Math.random: renders must repeat). @type {(n: number) => number} */
export const rand = n => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453
  return x - Math.floor(x)
}

/**
 * Seeded noise (mulberry32), never Math.random: a render must be identical every run.
 * @param {number} seed @returns {() => number}
 */
export function rng(seed) {
  return () => {
    seed |= 0
    seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/**
 * A number counting from a to b over [t0, t0+d] (a count-up), formatted by fmt.
 * @template [R=number] @param {number} t @param {number} t0 @param {number} d @param {number} a @param {number} b
 * @param {(v: number) => R} [fmt] @returns {R}
 */
export const countUp = (t, t0, d, a, b, fmt = v => Math.round(v)) => fmt(lerp(a, b, prog(t, t0, d, ease.out)))
