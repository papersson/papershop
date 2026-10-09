// The live engine's scene kit: motion helpers that are pure functions of time, and the theme. A scene
// module imports what it needs from here (`import {prog, ease} from '/engine/src/kit.js'`), or uses
// the same functions on its context (`c.P`, `c.kit`).
//
// The motion glossary (src/glossary.js) names these helpers: a note like "stagger these" or "ease
// out" maps to exactly one function below.

export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x))
export const lerp = (a, b, p) => a + (b - a) * p
export const mix = (a, b, p) => a.map((v, i) => lerp(v, b[i], p))

/** Easing curves: how a movement speeds up and slows down. */
export const ease = {
  linear: x => x,
  in: x => x * x * x,
  out: x => 1 - (1 - x) ** 3,
  inOut: x => (x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2),
  back: x => {
    const c = 1.70158, c3 = c + 1
    return 1 + c3 * (x - 1) ** 3 + c * (x - 1) ** 2
  },
  /** Manim's default "smooth": a sigmoid rescaled to run exactly 0 → 1 (the Remotion kit's `smooth`). */
  smooth: x => {
    const c = clamp(x), s = v => 1 / (1 + Math.exp(-v))
    return (s(10 * (c - 0.5)) - s(-5)) / (s(5) - s(-5))
  },
}

/** Progress 0..1 of a movement that starts at t0 and lasts d seconds. */
export const prog = (t, t0, d, e = ease.inOut) => e(clamp((t - t0) / Math.max(d, 1e-6)))

/** Start time of item i when items enter one after another, `gap` seconds apart. */
export const stagger = (t0, i, gap = 0.12) => t0 + i * gap

/** A quick rise and fall around t0: 0 → 1 → 0 over d seconds. */
export const pulse = (t, t0, d = 0.6) => {
  const x = clamp((t - t0) / d)
  return x <= 0 || x >= 1 ? 0 : Math.sin(x * Math.PI)
}

/** Closed-form damped spring from 0 to 1 (stiffness k, damping d): a pure function of time. */
export function spring(t, k = 170, d = 26) {
  if (t <= 0) return 0
  const w0 = Math.sqrt(k), z = d / (2 * w0)
  if (z < 1) {
    const wd = w0 * Math.sqrt(1 - z * z)
    return 1 - Math.exp(-z * w0 * t) * (Math.cos(wd * t) + ((z * w0) / wd) * Math.sin(wd * t))
  }
  return 1 - Math.exp(-w0 * t) * (1 + w0 * t)
}

/** Deterministic pseudo-random in 0..1 for an integer seed (never Math.random: renders must repeat). */
export const rand = n => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453
  return x - Math.floor(x)
}

/** A number counting from a to b over [t0, t0+d] (a count-up), formatted by fmt. */
export const countUp = (t, t0, d, a, b, fmt = v => Math.round(v)) => fmt(lerp(a, b, prog(t, t0, d, ease.out)))

/** The theme, as CSS variables the stage's SVG resolves (render.html defines them). */
export const C = {
  bg: 'var(--bg)', bg2: 'var(--bg2)', bg3: 'var(--bg3)', panel: 'var(--panel)', line: 'var(--line)',
  ink: 'var(--ink)', dim: 'var(--dim)', faint: 'var(--faint)', hot: 'var(--hot)', warm: 'var(--warm)',
  cold: 'var(--cold)', bad: 'var(--bad)', good: 'var(--good)', log: 'var(--log)', key: 'var(--key)', water: 'var(--water)',
}

const norm = w => w.toLowerCase().replace(/[^\p{L}\p{N}_]/gu, '')

/**
 * When a narration entry reaches a phrase, in timeline seconds: its words matched in the spoken
 * words, or, where a spoken rule rewrote them, its place in the caption. Same rule as
 * timeline.phrase_start in the kit and phraseStart in the other engines.
 */
export function phraseStart(s, phrase) {
  const want = phrase.split(/\s+/).map(norm).filter(Boolean)
  const got = (s.words ?? []).map(w => norm(w.w))
  for (let i = 0; want.length && i + want.length <= got.length; i++) {
    if (want.every((w, j) => got[i + j] === w)) return s.words[i].start
  }
  const cap = s.caption ?? s.text ?? ''
  const k = cap.indexOf(phrase)
  if (k < 0) throw new Error(`sentence ${s.id} has no phrase "${phrase}"`)
  return s.start + (k / Math.max(1, cap.length)) * (s.end - s.start)
}

const NO_BREAK_AFTER = new Set(['the', 'a', 'an', 'of', 'to'])

/** Greedy caption lines of at most `chars` characters that never end on an article (as Remotion's). */
export function wrapCaption(text, chars) {
  const lines = []
  let cur = []
  for (const word of text.split(/\s+/).filter(Boolean)) {
    if (cur.length && [...cur, word].join(' ').length > chars) {
      const carry = []
      while (cur.length > 1 && NO_BREAK_AFTER.has(cur[cur.length - 1].toLowerCase())) carry.unshift(cur.pop())
      lines.push(cur.join(' '))
      cur = carry
    }
    cur.push(word)
  }
  if (cur.length) lines.push(cur.join(' '))
  return lines
}
