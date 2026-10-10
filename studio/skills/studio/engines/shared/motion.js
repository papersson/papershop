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

/** @type {Ease} */
const inOut = x => (x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2)

/**
 * Easing curves: how a movement speeds up and slows down. Each runs 0 → 1 over 0..1; speeds below
 * are against the move's average speed.
 */
export const ease = {
  /** @type {Ease} */ linear: x => x,
  /** @type {Ease} */ in: x => x * x * x,
  /** @type {Ease} */ out: x => 1 - (1 - x) ** 3,
  inOut,
  /** Overshoots by 10% and comes back: snap and weight. @type {Ease} */ back: x => {
    const c = 1.70158, c3 = c + 1
    return 1 + c3 * (x - 1) ** 3 + c * (x - 1) ** 2
  },
  smooth,
  /**
   * Heavy: slow to get going, then decisive, with a short firm stop. inOut run on x^1.5, so the
   * move's middle comes at 63% of its time and its peak speed is about 3.6x: inertia overcome, then
   * mass arriving. For big things and conclusions. @type {Ease}
   */
  heavy: x => inOut(clamp(x) ** 1.5),
  /**
   * Float: half a cosine, the gentlest ease in and out (peak speed pi/2, about 1.6x), with no
   * corner anywhere. For drifting, breathing and ambient moves. @type {Ease}
   */
  float: x => (1 - Math.cos(Math.PI * clamp(x))) / 2,
  /**
   * Snap: arrives fast and stops hard. An exponential out: it leaves at about 7x speed, covers
   * 90% of the way in the first third, and the last 1% fades below a pixel, so it reads as a hard
   * stop without a jump. For things clicking into place. @type {Ease}
   */
  snap: x => (x >= 1 ? 1 : (1 - 2 ** (-10 * clamp(x))) / (1 - 2 ** -10)),
}

/** @typedef {number | number[]} Value */
/** @typedef {Ease | keyof typeof ease} EaseLike */

/** @type {(e: EaseLike | undefined, d: Ease) => Ease} */
const easeOf = (e, d) => (typeof e === 'function' ? e : e === undefined ? d : ease[e] ?? (() => { throw new Error(`no ease ${e}: ${Object.keys(ease).join(', ')}`) })())
/** @type {(a: Value, b: Value, p: number) => Value} */
const blend = (a, b, p) => (Array.isArray(a) ? mix(a, /** @type {number[]} */ (b), p) : lerp(a, /** @type {number} */ (b), p))

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

/**
 * Keyframes: keys are [time, value, ease?] sorted by time, a value a number or an array (a point, a
 * colour as [r, g, b]). The ease on a key shapes the move into it (a function or a name in `ease`;
 * `e` otherwise); before the first key the value is the first, after the last the last.
 * @param {number} t @param {[number, Value, EaseLike?][]} keys @param {Ease} [e] @returns {Value}
 */
export function keyed(t, keys, e = inOut) {
  if (!keys.length) throw new Error('keyed needs at least one key')
  if (t <= keys[0][0]) return keys[0][1]
  for (let i = 1; i < keys.length; i++) {
    const [t1, v1, e1] = keys[i], [t0, v0] = keys[i - 1]
    if (t < t1) return blend(v0, v1, easeOf(e1, e)(clamp((t - t0) / Math.max(t1 - t0, 1e-9))))
  }
  return keys[keys.length - 1][1]
}

const FOLLOW_STEP = 1 / 120  // seconds between the samples of the source follow weighs
const FOLLOW_SPAN = 10       // seconds of the source's past it weighs at most (a barely damped spring rings longer)

/**
 * Secondary motion: a value that trails fn(t) by `lag` seconds through a damped spring (stiffness k,
 * damping d), as a tail follows a body: it starts late, overshoots a little and settles. The spring's
 * response is weighed over the source's recent past, sampled on a fixed grid, so the result is a pure
 * function of t: no state, any frame alone. A step in fn gives exactly spring(t - lag - step time).
 * @template {Value} V @param {number} t @param {(t: number) => V} fn @param {number} [lag] @param {number} [k] @param {number} [d] @returns {V}
 */
export function follow(t, fn, lag = 0.1, k = 120, d = 14) {
  if (!(k > 0 && d > 0)) throw new Error(`follow needs a stiffness k and a damping d above 0 (got k=${k}, d=${d})`)
  const decay = Math.min(d / 2, Math.sqrt(k))              // how fast the spring's response dies away
  const n = Math.ceil(Math.min(FOLLOW_SPAN, Math.log(1e4) / decay) / FOLLOW_STEP)   // until it is below 1/10000
  const at = t - lag, now = /** @type {any} */ (fn(at))
  // Summed as differences from the source's value at t - lag, so a still source is followed exactly.
  let acc = Array.isArray(now) ? now.map(() => 0) : 0
  const add = (/** @type {any} */ v, /** @type {number} */ w) => {
    acc = Array.isArray(now) ? acc.map((/** @type {number} */ x, /** @type {number} */ j) => x + (v[j] - now[j]) * w) : acc + (v - now) * w
  }
  let prev = 0
  for (let i = 0; i < n; i++) {
    const next = spring((i + 1) * FOLLOW_STEP, k, d)        // the response's share over this step, exactly
    add(fn(at - (i + 0.5) * FOLLOW_STEP), next - prev)
    prev = next
  }
  add(fn(at - n * FOLLOW_STEP), 1 - prev)                     // the rest of it
  return Array.isArray(now) ? now.map((/** @type {number} */ x, /** @type {number} */ j) => x + acc[j]) : now + acc
}

/**
 * A decaying oscillation after a stop at t0: 0 before it, then amp · e^(-decay·s) · sin(2π·freq·s)
 * for s seconds after. It starts at 0, so it adds to a value that has just landed without a jump.
 * @param {number} t @param {number} t0 @param {number} [amp] @param {number} [freq] Hz @param {number} [decay] per second @returns {number}
 */
export function settle(t, t0, amp = 1, freq = 3, decay = 5) {
  const s = t - t0
  return s <= 0 ? 0 : amp * Math.exp(-decay * s) * Math.sin(2 * Math.PI * freq * s)
}

/**
 * Deterministic smooth noise in -amp..amp: random values at `freq` points a second, joined by a
 * quintic curve (no corner in speed or acceleration); a seed picks the sequence. For handheld drift,
 * idle life and jitter that never repeats visibly.
 * @param {number} t @param {number} [amp] @param {number} [freq] @param {number} [seed] @returns {number}
 */
export function wobble(t, amp = 1, freq = 1, seed = 0) {
  const x = t * freq, i = Math.floor(x), f = x - i
  const at = (/** @type {number} */ n) => rand(n + seed * 7919) * 2 - 1
  const w = f * f * f * (f * (f * 6 - 15) + 10)
  return amp * lerp(at(i), at(i + 1), w)
}
