// Narration times for every engine: a clip's sentence-time API (at, end, word, phrase, cue) and
// half-up frame rounding. The kit's timeline.phrase_start and timeline.half_up are their Python
// twins, and kit/tests checks phraseStart against phrase_start.

/** @typedef {{w: string, start: number, end: number}} Word */
/** @typedef {{id: string, clip?: string, start: number, end: number, caption?: string, text?: string, words?: Word[]}} Sentence */
/** @typedef {{tracks: {narration: Sentence[]}, cues?: Record<string, number>}} Timings */

/**
 * The frame a time falls on, rounding halves up like the kit's timeline.half_up (Python's round()
 * sends 436.5 to 436), so clip boundaries agree everywhere.
 * @param {number} t seconds @param {number} fps @returns {number}
 */
export const frameOf = (t, fps) => Math.floor(t * fps + 0.5)

const norm = w => w.toLowerCase().replace(/[^\p{L}\p{N}_]/gu, '')

/**
 * When a narration entry reaches a phrase, in timeline seconds: its words matched in the spoken
 * words, or, where a spoken rule rewrote them, its place in the caption. Same rule as
 * timeline.phrase_start.
 * @param {Sentence} s @param {string} phrase @returns {number}
 */
export function phraseStart(s, phrase) {
  const want = phrase.split(/\s+/).map(norm).filter(Boolean)
  const got = (s.words ?? []).map(w => norm(w.w))
  for (let i = 0; want.length && i + want.length <= got.length; i++) {
    if (want.every((w, j) => got[i + j] === w)) return /** @type {Word[]} */ (s.words)[i].start
  }
  const cap = s.caption ?? s.text ?? ''
  const k = cap.indexOf(phrase)
  if (k < 0) throw new Error(`sentence ${s.id} has no phrase "${phrase}"`)
  return s.start + (k / Math.max(1, cap.length)) * (s.end - s.start)
}

/**
 * A clip's narration times, in clip seconds from `start` (the clip's first frame, or its start on
 * the timeline). Sentence ids may be short ("03" is "<clip>_03"); every time takes an offset.
 * @param {Timings} T @param {string} clip @param {number} start
 */
export function clipTimes(T, clip, start) {
  /** @param {string} id @returns {Sentence} */
  const sentence = id => {
    const full = id.includes('_') ? id : `${clip}_${id}`
    const s = T.tracks.narration.find(n => n.id === full)
    if (!s) throw new Error(`no sentence ${full} in timeline.json`)
    return s
  }
  return {
    /** Start of a sentence. @type {(id: string, off?: number) => number} */
    at: (id, off = 0) => sentence(id).start - start + off,
    /** End of a sentence. @type {(id: string, off?: number) => number} */
    end: (id, off = 0) => sentence(id).end - start + off,
    /** Start of the i-th spoken word of a sentence (needs `studio align`). @type {(id: string, i: number, off?: number) => number} */
    word: (id, i, off = 0) => {
      const w = sentence(id).words?.[i]
      if (!w) throw new Error(`sentence ${id} has no word ${i}; run studio align`)
      return w.start - start + off
    },
    /** When the voice says a phrase of a sentence (phraseStart). @type {(id: string, text: string, off?: number) => number} */
    phrase: (id, text, off = 0) => phraseStart(sentence(id), text) - start + off,
    /** A timeline cue. @type {(name: string, off?: number) => number} */
    cue: (name, off = 0) => {
      if (!(name in (T.cues ?? {}))) throw new Error(`no cue ${name} in timeline.json`)
      return /** @type {Record<string, number>} */ (T.cues)[name] - start + off
    },
    /** The clip's sentences, their times in clip seconds. */
    get sentences() {
      return T.tracks.narration.filter(n => n.clip === clip).map(n => ({ ...n, start: n.start - start, end: n.end - start }))
    },
  }
}

/**
 * A caption chunk's lines in a layout's format: the kit wraps them for every format (`lines` are
 * the 16:9 ones, `wrapped` the rest), never the engine, so a format without them is an error.
 * @param {{lines: string[], wrapped?: Record<string, string[]>}} chunk @param {{format?: string}} layout @returns {string[]}
 */
export function captionLines(chunk, layout) {
  const fmt = layout.format ?? '16:9'
  const lines = fmt === '16:9' ? chunk.lines : chunk.wrapped?.[fmt]
  if (!lines) throw new Error(`timeline.json has no ${fmt} caption lines; \`studio timeline VIDEO\` rebuilds it`)
  return lines
}
