// The screens layer's model: a film's desktops and one log of what happens on them (data/screens.json),
// replayed to the state of every window at any time, and to the key and click sounds that go with it.
// Pure: no DOM, so `studio screens` runs the same code in node to write the sounds, and a frame's
// picture and its sound come from one schedule. The drawing is in screens-draw.js; references/screens.md
// has the file's format.
//
// The grammar it serves (references/taste.md, "Screens"): a desktop for a different kind of work, a
// tab for more of the same; a desktop switch slides, a tab switch snaps; a switch lands between
// sentences, never under a word.
//
// Times: actions name a timeline cue (`at`, plus `off` seconds). compile() resolves them against the
// timeline into film seconds; scenes ask state(screens, c.t + clip start), which screensAt(c) does.

const clamp = x => Math.max(0, Math.min(1, x))

/** Seconds a chord (Cmd-2, Ctrl-→) takes from the modifier going down to the key bottoming out. */
export const CHORD = 0.08
/** The eye needs about a third of a second to re-orient after a slide before it can listen hard. */
export const SETTLE = 0.3
/** How far a switch may move to find a gap between sentences, either way. */
export const SNAP = 1.5
/** Average keys a second above which typing reads as autotype; a burst faster than this is slowed. */
export const MAX_KEYS = 13
/** Seconds after Enter before a command's output appears, and between streamed output lines. */
export const BREATH = 0.15, LINE = 0.03
/** Seconds the pointer travels before a click lands. */
export const TRAVEL = 0.45
/**
 * Pointing at what the narrator names: the underline draws in over LEAD seconds and is whole on the
 * word (the cue), the rest of the window dims to DIM; it holds HOLD seconds unless `until` says, then
 * fades over FADE. An outcome mark (running, finished, failed, cancelled) is an act: it lands on its cue.
 */
export const LEAD = 0.2, HOLD = 2.5, FADE = 0.3, DIM = 0.55
export const MARKS = ['running', 'finished', 'failed', 'cancelled', 'none']

// ── Rhythm ──────────────────────────────────────────────────────────────────────────────────────
/** A small seeded generator (mulberry32 over a string's hash): the same seed, the same rhythm. */
export function rng(seed) {
  let a = 0
  for (const ch of String(seed)) a = (a * 31 + ch.charCodeAt(0)) >>> 0
  return () => {
    a |= 0; a = a + 0x6D2B79F5 | 0
    let t = Math.imul(a ^ a >>> 15, 1 | a)
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t
    return ((t ^ t >>> 14) >>> 0) / 4294967296
  }
}

/**
 * Seconds after a burst starts at which each character of `text` appears, in human bursts: faster
 * inside a word, a pause after punctuation and spaces (typecode.py's char_lead, seeded). `speed`
 * scales the rhythm; a result faster than `maxKeys` a second on average is slowed to it.
 */
export function keyTimes(text, seed, { speed = 1, maxKeys = MAX_KEYS } = {}) {
  const r = rng(seed), out = []
  let t = 0, prev = null
  for (const ch of text) {
    const u = r()
    const lead = prev === null ? .12 + .08 * u
      : ',;(){}"=!'.includes(prev) ? .08 + .06 * u
      : prev === ' ' || prev === '\n' ? .06 + .04 * u
      : '(),;{}'.includes(ch) ? [.04, .055, .07][Math.floor(u * 3)]
      : u < .2 ? .035 : u < .6 ? .05 : u < .9 ? .065 : .085
    t += lead / speed
    out.push(t)
    prev = ch
  }
  const n = out.length, span = n > 1 ? out[n - 1] - out[0] : 0
  if (n > 2 && (n - 1) / span > maxKeys) {
    const k = (n - 1) / span / maxKeys
    for (let i = 1; i < n; i++) out[i] = out[0] + (out[i] - out[0]) * k
  }
  return out.map(x => +x.toFixed(4))
}

// ── Compiling the log ───────────────────────────────────────────────────────────────────────────
const KINDS = ['type', 'edit', 'save', 'open', 'tab', 'switch', 'click', 'drag', 'clear', 'split', 'unsplit', 'page', 'output', 'close', 'show', 'point', 'mark']
/** The verb of an action: the one of KINDS it carries. */
export const verb = a => KINDS.find(k => k in a)

function cueTime(T, a, i) {
  if (typeof a.at === 'number') return a.at + (a.off ?? 0)
  if (!a.at) throw new Error(`screens action ${i + 1} (${verb(a)}): no \`at\` cue`)
  if (!(a.at in (T.cues ?? {}))) throw new Error(`screens action ${i + 1} (${verb(a)}): no cue ${a.at} in timeline.json`)
  return T.cues[a.at] + (a.off ?? 0)
}

/** Spoken spans [start, end] in film seconds: words where aligned, else whole sentences. */
export function spoken(T) {
  const out = []
  for (const s of T.tracks?.narration ?? []) {
    if (s.words?.length) for (const w of s.words) out.push([w.start, w.end])
    else out.push([s.start, s.end])
  }
  return out.sort((a, b) => a[0] - b[0])
}

/**
 * The start time nearest `t` (within SNAP) at which a slide of `ms` and the settle after it touch no
 * spoken word, and whether one was found: {t, ok}. Between sentences or in a hold, never on a word.
 */
export function snapSwitch(t, ms, spans, window = SNAP) {
  const busy = s => spans.some(([a, b]) => b > s - .02 && a < s + ms + SETTLE)
  if (!busy(t)) return { t, ok: true }
  const options = []
  for (const [, b] of spans) options.push(b + .03)
  for (const [a] of spans) options.push(a - ms - SETTLE - .03)
  const best = options.filter(s => s >= 0 && Math.abs(s - t) <= window && !busy(s)).sort((x, y) => Math.abs(x - t) - Math.abs(y - t))[0]
  return best === undefined ? { t, ok: false } : { t: +best.toFixed(4), ok: true }
}

function lines(text) {
  return text === undefined || text === null || text === '' ? [] : String(text).replace(/\r\n/g, '\n').replace(/\n$/, '').split('\n')
}

/** A captured run {argv, stdout, stderr, exit} as output lines, stderr marked. */
export function runLines(run) {
  return [...lines(run.stdout).map(text => ({ text })), ...lines(run.stderr).map(text => ({ text, err: true }))]
}

/**
 * The log resolved against a timeline: every action with its film time `t`, the time each of its
 * characters appears (`keys`), its Enter, its output's lines, and when it is done; every desktop
 * switch with its slide length and the gap it was moved to. `runs` maps a run name to its capture.
 * Throws on a name the log doesn't declare, so a typo stops the build instead of drawing nothing.
 */
export function compile(spec, T, runs = {}) {
  const desktops = spec.desktops ?? []
  if (!desktops.length) throw new Error('screens.json: no desktops')
  const ids = desktops.map(d => d.id)
  // a window shares a plate (one full-screen desktop) with others that name it; by default its own
  const plateOf = Object.fromEntries(desktops.map(d => [d.id, d.plate ?? d.id]))
  const plates = [...new Set(desktops.map(d => plateOf[d.id]))]
  const seed = spec.seed ?? 'screens', spans = spoken(T)
  const slide = { first: .32, last: .22, ...(spec.slide ?? {}) }
  const out = [], problems = []
  let nSwitch = (spec.actions ?? []).filter(a => 'switch' in a).length, kSwitch = 0
  const arrive = Object.fromEntries(desktops.map(d => [d.id, d.arrive === undefined ? -Infinity : typeof d.arrive === 'number' ? d.arrive : (() => {
    if (!(d.arrive in (T.cues ?? {}))) throw new Error(`screens.json: desktop ${d.id} arrives at cue ${d.arrive}, which timeline.json lacks`)
    return T.cues[d.arrive]
  })()]))
  for (const [i, a] of (spec.actions ?? []).entries()) {
    const kind = verb(a)
    if (!kind) throw new Error(`screens action ${i + 1}: none of ${KINDS.join(', ')}`)
    const on = kind === 'switch' ? plateOf[a.switch] ?? a.switch : kind === 'close' || kind === 'show' ? a[kind] : a.on
    if (kind === 'switch' ? !plates.includes(on) : !ids.includes(on))
      throw new Error(`screens action ${i + 1} (${kind}): no ${kind === 'switch' ? 'desktop' : 'window'} ${JSON.stringify(on)} (${kind === 'switch' ? plates : ids})`)
    const desk = desktops.find(d => d.id === on)
    const at = cueTime(T, a, i), x = { ...a, i, kind, on, cueAt: at, t: at, keys: [], sounds: [] }
    if (kind === 'switch') {
      const ms = +(nSwitch > 1 ? slide.first + (slide.last - slide.first) * kSwitch / (nSwitch - 1) : slide.first).toFixed(4)
      kSwitch++
      const s = a.snap === false ? { t: at, ok: !spans.some(([p, q]) => q > at && p < at + ms + SETTLE) } : snapSwitch(at, ms, spans)
      Object.assign(x, { t: s.t, ms, gap: s.ok, land: s.t + CHORD + ms })
      x.slideAt = s.t + CHORD
      x.sounds.push([s.t, 'key'], [s.t + CHORD, 'key'])
      x.done = x.land
      if (!s.ok) problems.push({ i, kind, t: s.t, why: `the switch to ${on} can't find a gap between sentences within ${SNAP} s of ${a.at}` })
    } else if (kind === 'tab') {
      // reached by the keyboard chord, or (chord: false) by a click action at the same moment, which sounds
      x.snapAt = a.chord === false ? at : at + CHORD
      if (a.chord !== false) x.sounds.push([at, 'key'], [at + CHORD, 'key'])
      x.done = x.snapAt
    } else if (kind === 'type' || kind === 'edit') {
      const text = kind === 'type' ? String(a.type) : String(a.edit.text ?? '')
      const lead = a.lead ?? 0
      x.keys = keyTimes(text, `${seed}:${i}:${text}`, { speed: a.speed ?? 1, maxKeys: spec.maxKeys ?? MAX_KEYS }).map(k => +(at + lead + k).toFixed(4))
      ;[...text].forEach((ch, k) => x.sounds.push([x.keys[k], ch === ' ' ? 'space' : ch === '\n' ? 'enter' : 'key']))
      const last = x.keys.at(-1) ?? at
      x.enter = kind === 'type' && a.enter !== false && desk.kind !== 'browser' || a.enter === true ? +(last + (a.pause ?? .22)).toFixed(4) : null
      if (x.enter !== null) x.sounds.push([x.enter, 'enter'])
      let out = []
      if (a.run) {
        if (!runs[a.run]) throw new Error(`screens action ${i + 1}: no captured run ${a.run} (screens.json runs)`)
        out = runLines(runs[a.run])
      } else if (a.output) out = (Array.isArray(a.output) ? a.output : lines(a.output)).map(l => typeof l === 'string' ? { text: l } : l)
      const start = (x.enter ?? last) + (a.breath ?? BREATH), every = a.stream ?? (out.length > 40 ? LINE : 0)
      x.output = out.map((l, k) => ({ ...l, at: +(start + every * k).toFixed(4) }))
      x.done = x.output.at(-1)?.at ?? x.enter ?? last
    } else if (kind === 'click') {
      x.press = at
      x.sounds.push([at, 'click'])
      x.done = at
    } else if (kind === 'drag') {
      const d = a.dur ?? .8
      Object.assign(x, { press: at, release: at + d, done: at + d })
      x.sounds.push([at, 'click'], [at + d, 'click'])
    } else if (kind === 'close') {
      x.sounds.push([at, 'key'], [at + CHORD, 'key'])
      x.done = at + CHORD
    } else if (kind === 'save') {
      x.sounds.push([at, 'key'], [at + CHORD, 'key'])
      x.done = at + CHORD
    } else if (kind === 'output') {
      const out = a.run ? runLines(runs[a.run] ?? (() => { throw new Error(`screens action ${i + 1}: no captured run ${a.run}`) })()) : (Array.isArray(a.output) ? a.output : lines(a.output)).map(l => typeof l === 'string' ? { text: l } : l)
      const every = a.stream ?? (out.length > 40 ? LINE : 0)
      x.output = out.map((l, k) => ({ ...l, at: +(at + every * k).toFixed(4) }))
      x.done = x.output.at(-1)?.at ?? at
    } else if (kind === 'point') {
      if (!a.point || !(typeof a.point === 'string' || a.point.text || a.point.line)) throw new Error(`screens action ${i + 1} (point): name a target: a page target, {text} or {line, text}`)
      const until = a.until === undefined ? at + (a.for ?? HOLD) : cueTime(T, { at: a.until }, i)
      if (until <= at) throw new Error(`screens action ${i + 1} (point): until (${a.until}) is not after at (${a.at})`)
      Object.assign(x, { from: +(at - (a.lead ?? LEAD)).toFixed(4), until, dim: a.dim ?? spec.dim ?? DIM, done: until })
    } else if (kind === 'mark') {
      if (!a.mark || !(typeof a.mark === 'string' || a.mark.text || a.mark.line)) throw new Error(`screens action ${i + 1} (mark): name a target: a page target, {text} or {line, text}`)
      if (!MARKS.includes(a.state)) throw new Error(`screens action ${i + 1} (mark): state must be one of ${MARKS.join(', ')} (got ${JSON.stringify(a.state)})`)
      // the two outcome sounds are a trial, off unless the log asks for them (references/taste.md, "Sound")
      if (spec.outcomeSounds === true && (a.state === 'finished' || a.state === 'failed') && a.sound !== false) x.sounds.push([at, a.state])
      x.done = at
    } else x.done = at
    if (kind !== 'switch' && x.t < arrive[on] - 1e-6) problems.push({ i, kind, t: x.t, why: `${kind} on ${on} before that desktop arrives` })
    out.push(x)
  }
  out.sort((p, q) => p.t - q.t || p.i - q.i)
  for (const p of plates) arrive[p] = Math.min(...desktops.filter(d => plateOf[d.id] === p).map(d => arrive[d.id]))
  for (const a of out) if (a.kind === 'switch' && a.t < arrive[a.on] - 1e-6) problems.push({ i: a.i, kind: 'switch', t: a.t, why: `switch to ${a.on} before it arrives` })
  return { spec, desktops, ids, plates, plateOf, arrive, actions: out, problems, start: plateOf[desktops[0].id] }
}

// ── State at a time ─────────────────────────────────────────────────────────────────────────────
function typedAt(keys, text, t) {
  let n = 0
  while (n < keys.length && t >= keys[n]) n++
  return [...text].slice(0, n).join('')
}

function fresh(d) {
  if (d.kind === 'terminal') return {
    kind: 'terminal', active: 0, split: null,
    tabs: (d.tabs ?? [{ id: 'main' }]).map(tb => ({ id: tb.id, title: tb.title ?? tb.id, prompt: tb.prompt ?? '$ ', lines: (tb.lines ?? []).map(l => typeof l === 'string' ? { text: l } : l), input: '' })),
  }
  if (d.kind === 'editor') {
    const files = Object.fromEntries(Object.entries(d.files ?? {}).map(([name, text]) => [name, lines(text)]))
    return {
      kind: 'editor', open: [d.open ?? Object.keys(files)[0]].filter(Boolean), active: d.open ?? Object.keys(files)[0], files,
      dirty: {}, caret: null, typing: false, lastKey: -1e9,
      panel: d.panel ? { title: d.panel.title ?? 'TERMINAL', name: d.panel.name ?? '', prompt: d.panel.prompt ?? '$ ', lines: (d.panel.lines ?? []).map(l => typeof l === 'string' ? { text: l } : l), input: '' } : null,
    }
  }
  if (d.kind === 'browser') return {
    kind: 'browser', active: 0, pointer: d.pointer ?? null, press: null, drag: null,
    tabs: (d.tabs ?? [{ id: 'main' }]).map(tb => ({ id: tb.id, title: tb.title ?? tb.id, url: tb.url ?? '', page: tb.page ?? tb.id, fields: {}, since: -1e9, clicked: [] })),
  }
  throw new Error(`desktop ${d.id}: kind must be editor, terminal or browser (got ${JSON.stringify(d.kind)})`)
}

function tabIndex(st, id, a) {
  const k = st.tabs.findIndex(tb => tb.id === id)
  if (k < 0) throw new Error(`screens action ${a.i + 1}: desktop ${a.on} has no tab ${JSON.stringify(id)}`)
  return k
}

function termTarget(st, a) {
  if (st.kind === 'editor') return st.panel ?? (() => { throw new Error(`screens action ${a.i + 1}: desktop ${a.on} has no terminal panel`) })()
  return st.tabs[a.tab !== undefined ? tabIndex(st, a.tab, a) : st.active]
}

/** One name for a point or mark target, so a later mark on the same thing replaces the earlier one. */
export const targetKey = g => typeof g === 'string' ? g : JSON.stringify([g.panel ?? false, g.line ?? null, g.text ?? null])

/** Apply action `a` to desktop state `st` as it stands at film time t (a may be in progress). */
function apply(st, a, t) {
  const kind = a.kind
  if (kind === 'type' && st.kind !== 'browser') {
    const target = termTarget(st, a), typed = typedAt(a.keys, String(a.type), t)
    if (st.kind === 'editor') st.panelActive = t
    if (a.enter !== null && t >= a.enter) {
      target.lines.push({ prompt: target.prompt, text: String(a.type), cmd: true })
      for (const l of a.output) if (t >= l.at) target.lines.push(l)
      target.input = ''
      // the next prompt waits for the command's last line, as a shell's does; a server or tail -f keeps it
      // away until cleared
      target.running = a.returns === false || t < a.done
    } else { target.input = typed; target.running = false }
    if (a.tab !== undefined && st.kind === 'terminal') st.active = tabIndex(st, a.tab, a)
  } else if (kind === 'type' && st.kind === 'browser') {
    const tb = st.tabs[a.tab !== undefined ? tabIndex(st, a.tab, a) : st.active]
    tb.fields = { ...tb.fields, [a.field ?? 'search']: typedAt(a.keys, String(a.type), t) }
    if (a.enter !== null && t >= a.enter) { tb.submitted = { ...(tb.submitted ?? {}), [a.field ?? 'search']: a.enter }; if (a.page) { tb.page = a.page; tb.since = a.enter } }
  } else if (kind === 'output') {
    const target = termTarget(st, a)
    for (const l of a.output) if (t >= l.at) target.lines.push(l)
  } else if (kind === 'edit') {
    const e = a.edit, file = e.file ?? st.active
    if (!st.files[file]) throw new Error(`screens action ${a.i + 1}: no file ${file} on ${a.on}`)
    if (!st.open.includes(file)) st.open.push(file)
    st.active = file
    const buf = [...st.files[file]], typed = typedAt(a.keys, String(e.text ?? ''), t), parts = typed.split('\n')
    const n = e.line ?? buf.length // 1-based line the edit is at
    if (e.mode === 'replace') {
      const keep = e.keep ?? 0 // characters of the old line kept before the typed text
      const old = buf[n - 1] ?? ''
      buf.splice(n - 1, 1, ...[old.slice(0, keep) + parts[0], ...parts.slice(1)])
      st.caret = { line: n + parts.length - 1, col: (parts.length > 1 ? 0 : keep) + parts.at(-1).length }
    } else if (e.mode === 'append') {
      buf[n - 1] = (buf[n - 1] ?? '') + parts[0]
      buf.splice(n, 0, ...parts.slice(1))
      st.caret = { line: n + parts.length - 1, col: (parts.length > 1 ? 0 : (st.files[file][n - 1] ?? '').length) + parts.at(-1).length }
    } else { // insert new line(s) below line n, indented by e.indent spaces
      const ind = ' '.repeat(e.indent ?? 0)
      buf.splice(n, 0, ...parts.map(p => ind + p))
      st.caret = { line: n + parts.length, col: ind.length + parts.at(-1).length }
    }
    if (a.keys.length && t >= a.keys[0]) { st.files[file] = buf; st.dirty = { ...st.dirty, [file]: true } }
    st.lastKey = Math.max(st.lastKey, a.keys.filter(k => k <= t).at(-1) ?? -1e9)
    st.focusLine = st.caret.line
  } else if (kind === 'save') {
    if (t >= a.t + CHORD) st.dirty = { ...st.dirty, [a.save === true ? st.active : a.save]: false }
  } else if (kind === 'open' && st.kind === 'editor') {
    if (!st.files[a.open]) throw new Error(`screens action ${a.i + 1}: no file ${a.open} on ${a.on}`)
    if (!st.open.includes(a.open)) st.open.push(a.open)
    st.active = a.open
    if (a.line) st.focusLine = a.line
  } else if (kind === 'open' && st.kind === 'browser') {
    const tb = st.tabs[st.active]
    Object.assign(tb, { url: a.open.url ?? tb.url, page: a.open.page ?? tb.page, title: a.open.title ?? tb.title, since: a.t, fields: {} })
  } else if (kind === 'tab') {
    if (t < a.snapAt) return
    if (a.new) {
      const tb = st.kind === 'terminal' ? { id: a.tab, title: a.new.title ?? a.tab, prompt: a.new.prompt ?? '$ ', lines: (a.new.lines ?? []).map(l => typeof l === 'string' ? { text: l } : l), input: '' }
        : { id: a.tab, title: a.new.title ?? a.tab, url: a.new.url ?? '', page: a.new.page ?? a.tab, fields: {}, since: a.snapAt, clicked: [] }
      if (!st.tabs.some(x => x.id === a.tab)) st.tabs.push(tb)
    }
    st.active = tabIndex(st, a.tab, a)
  } else if (kind === 'clear') {
    const target = termTarget(st, a)
    target.lines = []
    target.running = false
    target.input = ''
  } else if (kind === 'split') {
    st.split = a.split
  } else if (kind === 'unsplit') {
    st.split = null
  } else if (kind === 'page') {
    const tb = st.tabs[a.tab !== undefined ? tabIndex(st, a.tab, a) : st.active]
    tb.page = a.page; tb.since = a.t
    if (a.url) tb.url = a.url
  } else if (kind === 'click') {
    const tb = st.tabs?.[st.active]
    st.press = { target: a.click, at: a.press, from: st.pointer }
    st.pointer = a.click
    if (tb && t >= a.press) {
      tb.clicked = [...tb.clicked, a.click]
      if (a.page) { tb.page = a.page; tb.since = a.press }
      if (a.url) tb.url = a.url
    }
  } else if (kind === 'point') {
    // one point a window at a time: a newer one takes over; an ended one is gone once it has faded
    st.point = t < a.until + FADE ? { target: a.point, from: a.from, at: a.t, until: a.until, dim: a.dim } : null
  } else if (kind === 'mark') {
    const id = targetKey(a.mark), { [id]: _, ...rest } = st.marks
    st.marks = a.state === 'none' ? rest : { ...rest, [id]: { target: a.mark, state: a.state, at: a.t } }
  } else if (kind === 'drag') {
    const tb = st.tabs?.[st.active]
    st.drag = { target: a.drag, from: a.from ?? [.2, .2], to: a.to ?? [.8, .8], press: a.press, release: a.release, p: clamp((t - a.press) / (a.release - a.press)) }
    st.press = { target: a.drag, at: a.press, from: st.pointer, point: a.from ?? [.2, .2] }
    st.pointer = a.drag
    if (tb && t >= a.release) { tb.selected = { target: a.drag, from: a.from ?? [.2, .2], to: a.to ?? [.8, .8], at: a.release }; if (a.page) { tb.page = a.page; tb.since = a.release } }
  }
}

/**
 * Every desktop's state at film time t, and the desk's: which desktop is shown, a slide in progress
 * ({from, to, p}), and the switches and arrivals the indicator needs. Each action that has begun by t
 * is applied in order; one still in progress shows its typing so far.
 */
export function state(screens, t) {
  const { desktops, actions, arrive } = screens
  const desks = Object.fromEntries(desktops.map(d => [d.id, { ...fresh(d), id: d.id, spec: d, closed: !!d.hidden, point: null, marks: {} }]))
  let current = screens.start, slide = null
  const begun = a => a.kind === 'switch' ? t >= a.t : a.kind === 'click' || a.kind === 'drag' ? t >= a.press - TRAVEL : a.kind === 'point' ? t >= a.from : t >= a.t
  for (const a of actions) {
    if (!begun(a)) continue // a click or a point begins before its time, so a later one may have begun
    if (a.kind === 'switch') {
      const from = current, p = clamp((t - a.slideAt) / a.ms)
      if (t >= a.slideAt) { current = a.on; if (p < 1) slide = { from, to: a.on, p, at: a.slideAt, ms: a.ms } }
      continue
    }
    if (a.kind === 'close') { if (t >= a.t + CHORD) desks[a.on].closed = true; continue }
    if (a.kind === 'show') { desks[a.on].closed = false; desks[a.on].shownAt = a.t; continue }
    apply(desks[a.on], a, t)
  }
  const present = screens.plates.filter(p => t >= arrive[p])
  return { t, current, slide, present, desks }
}

/** The film's switches, for the indicator and the camera: [{t: slide start, ms, from, to, land}]. */
export function switches(screens) {
  let current = screens.start
  return screens.actions.filter(a => a.kind === 'switch').map(a => {
    const s = { t: a.slideAt, ms: a.ms, from: current, to: a.on, land: a.land, gap: a.gap, key: a.t }
    current = a.on
    return s
  })
}

// ── Sound ───────────────────────────────────────────────────────────────────────────────────────
/**
 * The stream's sounds by kind: the kit's typing take, its Enter, and a trackpad click; and the two
 * outcome sounds, generated, that a log turns on with `outcomeSounds` (sfx.py's finished and failed).
 */
export const SOUNDS = {
  key: 'grains:kit:keys-typing-cherry-blue', space: 'grains:kit:keys-typing-cherry-blue#low',
  enter: { sound: 'kit:keys-enter-press', gain: -14 }, click: { sound: 'kit:ui-mouseclick1', gain: -12 },
  finished: { sound: 'synth:finished', gain: -2 }, failed: { sound: 'synth:failed', gain: -4 },
}

/**
 * The log's sounds as audio/sfx.json streams: one per action that makes a sound, on the action's cue,
 * every event in seconds after it (each on the frame its picture changes: a key on its character, a
 * chord on the snap or slide it causes, a click on the press).
 */
export function streams(screens, sounds = SOUNDS) {
  return screens.actions.filter(a => a.sounds.length).map(a => {
    // the effect sits on the cue itself (sfx.json resolves the name); events count from there
    const events = a.sounds.map(([s, k]) => [+(s - a.cueAt + (a.off ?? 0)).toFixed(4), k]).sort((p, q) => p[0] - q[0])
    const kinds = [...new Set(events.map(e => e[1]))]
    return {
      t: typeof a.at === 'number' ? a.at - (a.off ?? 0) : a.at, type: 'key-tick', stream: `screens:${a.i + 1}-${a.kind}`, exact: true, source: 'screens',
      events,
      sounds: Object.fromEntries(kinds.map(k => [k, sounds[k] ?? sounds.key])),
    }
  })
}

/** Moments worth checking: each action's last character, Enter, output and landing, in film seconds. */
export function moments(screens) {
  const out = []
  for (const a of screens.actions) {
    if (a.keys.length) out.push({ t: a.keys.at(-1) + .05, on: a.on, why: `typed: ${(a.type ?? a.edit?.text ?? '').toString().slice(0, 40)}` })
    if (a.output?.length) out.push({ t: a.output.at(-1).at + .1, on: a.on, why: 'output shown' })
    if (a.kind === 'switch') out.push({ t: a.land + .1, on: a.on, why: `landed on ${a.on}` })
    if (a.kind === 'point') out.push({ t: a.t + .05, on: a.on, why: `pointing at ${targetKey(a.point)}` })
    if (a.kind === 'mark') out.push({ t: a.t + .25, on: a.on, why: `${a.state}: ${targetKey(a.mark)}` })
  }
  return out
}

/** Typing faster than the rhythm allows, per action: [{i, rate}] (keys a second over its span). */
export function rates(screens) {
  return screens.actions.filter(a => a.keys.length > 2).map(a => ({ i: a.i, on: a.on, t: a.t,
    rate: (a.keys.length - 1) / (a.keys.at(-1) - a.keys[0]) }))
}
