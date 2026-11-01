// The live engine's player: loads a video's timeline, layout, scenes and boards, and draws any frame.
// The engine CLI drives it headless (still, render, boxes); the desk drives it live, in step with
// the narration, and reloads the scenes in place when they change.
//
// A video's live scenes are plain ES modules, one per chapter: scenes/<clip>.js exports
// `default function draw(c)`. An optional scenes/overlay.js exports `default function overlay(c)`,
// drawn over every chapter (a ladder, a clock, title cards). A chapter with no scene file shows its
// board (boards/boards.json and the screen notes), so a cut always plays the whole video.
//
// The context `c` a scene gets, all times in clip seconds:
//   S                the stage (rect, circle, text, line, path, strike, callout, blur, el, cam)
//   G                the 3D stage under it (stage3d.js), made the first time a scene asks for it
//   shot(keys, e)    point G's camera along 3D shot keys [time, {target, az, el, span, fov}, ease?] at t,
//                    centred in the view; flatShot() is the top-down shot that matches the 2D stage, and
//                    frameOn3(points, {az, el, fov}) a shot that fits world points (shared/camera3d.js)
//   t, dur           time in the clip and the clip's length
//   W, H, unit       the stage (the whole frame), in pixels; unit = H / 8 (the other engines' unit)
//   header, view     the strip at the stage's top that framing keeps clear (layout.json header.height,
//                    0 by default), and the stage below it as [x, y, w, h]
//   camAt(keys, e)   point the camera along keys [time, {x, y, z}, ease?] at t, each key's point centred
//                    in the view; returns {x, y, z}. frameOn([x0, y0, x1, y1]) is a key that fits a region
//   at(id, off)      start of a sentence ("03" means "<clip>_03"); end(id, off) its end
//   word(id, i, off) word i of the sentence, as a cue's {word: i}; phrase(id, text, off) when the voice says that phrase
//   cue(name, off)   a timeline cue; P(t0, d, ease) progress of a movement; kit: the helpers
//   legend           the video's colour legend (video.json legend) as meaning -> CSS colour: draw a
//                    meaning with {stroke: c.legend.request, means: 'request'} and the legend check sees it
//   motion           'full' or 'reduced' (video.json motion): the feel helpers drop shake and hitstop
//                    when reduced (templates/live/scenes/example-feel.js)
//   clip, index, chapters, timeline, layout, asset(file)
//   plate(o)         draw the chapter's plate behind everything (video.json plates: Blender renders it,
//                    the kit's plates.py), filling the stage; plate.at(name) is a projected
//                    object's point on the stage, [x, y], to put a label on; null when it is behind the camera

import { Stage } from './stage.js'
import { Stage3D } from './stage3d.js'
import * as kit from './kit.js'
import { PAGES, LEGEND_PAGE } from './look.js'
import { clipTimes, frameOf } from '../../shared/timing.js'
import { flatShot, frameOn3, shotAt } from '../../shared/camera3d.js'

// Film grammar defaults (references/kit.md, "Joins, shots, focus and callbacks").
const SHOT_MOVE = 1.1          // seconds a shot change takes
const FOCUS_IN = 0.35, FOCUS_OUT = 0.5
const JOIN_MAX = 0.6, JOIN_MIN = 0.2, JOIN_CLEAR = 0.1   // a join's length, and the quiet it leaves after the last word
const DEFAULT_LAYOUT = { width: 1920, height: 1080, fps: 30 }

async function json(url, fallback) {
  const r = await fetch(url, { cache: 'no-store' })
  if (!r.ok) {
    if (fallback !== undefined) return fallback
    throw new Error(`could not load ${url} (${r.status})`)
  }
  return r.json()
}

/** A scene module, its import errors naming the file: a syntax error says only "Unexpected end of input". */
async function importScene(name, url) {
  try {
    return await import(url)
  } catch (e) {
    throw new Error(`scenes/${name}: ${e && e.message ? e.message : e}`)
  }
}

/**
 * video.json's legend as meaning -> CSS colour: a theme name (any case, _ or -) as its var, #rrggbb as
 * itself. A name the theme lacks throws, so a typo fails every still instead of drawing nothing.
 */
function legendColours(legend) {
  const root = getComputedStyle(document.documentElement)
  return Object.fromEntries(Object.entries(legend).map(([meaning, v]) => {
    if (/^#[0-9a-f]{6}$/i.test(String(v))) return [meaning, v]
    const name = String(v).trim().toLowerCase().replace(/_/g, '-')
    if (!root.getPropertyValue(`--${name}`).trim()) throw new Error(`video.json legend ${JSON.stringify(meaning)}: ${JSON.stringify(v)} is not a theme colour (src/theme.css) or #rrggbb`)
    return [meaning, `var(--${name})`]
  }))
}

async function exists(url) {
  const r = await fetch(url, { method: 'HEAD', cache: 'no-store' })
  return r.ok
}

export async function boot({ svg, canvas, video, layout: layoutUrl }) {
  const base = video.endsWith('/') ? video : video + '/'
  let T, L, scenes, joins, overlay, boards, notes, legend, colours, motion, plates, platePoints, version = 0
  // Images a frame draws (a plate) are decoded before the frame counts as drawn, so a still never
  // catches a plate half loaded: draw() returns a promise while any is pending.
  const decoded = new Map()
  let pending = []

  async function load() {
    version += 1
    T = await json(base + 'timeline.json')
    L = layoutUrl ? await json(layoutUrl, DEFAULT_LAYOUT) : DEFAULT_LAYOUT
    boards = await json(base + 'boards/boards.json', {})
    notes = await json(base + 'boards/notes.json', {})
    const video = await json(base + 'video.json', {})
    legend = video.legend ?? {}
    motion = video.motion ?? 'full'
    colours = legendColours(legend)
    plates = await json(base + '.cache/plates/index.json', {})
    platePoints = {}
    for (const [clip, p] of Object.entries(plates)) {
      const r = await fetch(`${base}${p.dir}/frames.jsonl`, { cache: 'no-store' })
      platePoints[clip] = r.ok ? Object.fromEntries((await r.text()).split('\n').filter(Boolean)
        .map(line => JSON.parse(line)).map(e => [e.frame, e.points])) : {}
    }
    scenes = {}
    joins = {}
    for (const c of T.tracks.scene) {
      const url = `${base}scenes/${c.id}.js?v=${version}`
      if (await exists(`${base}scenes/${c.id}.js`)) {
        const mod = await importScene(`${c.id}.js`, url)
        scenes[c.id] = mod.default
        if (mod.join !== undefined) joins[c.id] = mod.join
      }
    }
    overlay = (await exists(`${base}scenes/overlay.js`)) ? (await importScene('overlay.js', `${base}scenes/overlay.js?v=${version}`)).default : null
  }
  await load()
  await Promise.all(['400 20px "IBM Plex Sans"', '500 20px "IBM Plex Sans"', '600 20px "IBM Plex Sans"',
    '700 20px "IBM Plex Sans"', '400 20px "IBM Plex Mono"', '500 20px "IBM Plex Mono"'].map(f => document.fonts.load(f)))

  const stage = new Stage(svg, { width: L.width, height: L.height })
  const viewOf = () => [0, L.header?.height ?? 0, L.width, L.height - (L.header?.height ?? 0)]
  // The 3D stage is made on first use, so a video that draws nothing in 3D never makes a WebGL context.
  let stage3d = null
  const G = () => {
    if (!stage3d) (stage3d = new Stage3D(canvas, { width: L.width, height: L.height })).begin(viewOf())
    return stage3d
  }
  /** Every stage runs the same frame: begin before the scene draws, end after (end renders the 3D stage). */
  function begin() {
    stage.begin()
    stage3d?.begin(viewOf())
  }
  function end() {
    stage3d?.end()
    stage.end()
  }

  /** What scenes and look pages share: the stage, its size, the header and the camera helpers, at clip time t. */
  function frameContext(t) {
    const H = L.height, header = L.header?.height ?? 0
    return {
      S: stage, t, W: L.width, H, unit: H / 8, kit, header, view: viewOf(), layout: L,
      legend: colours, motion,
      // S.cam centres the whole frame; a key's point goes to the middle of the view instead.
      camAt: (keys, e) => {
        const k = kit.camAt(t, keys, e)
        stage.cam(k.x, k.y + (L.height / 2 - (header + H) / 2) / k.z, k.z)
        return k
      },
      frameOn: (region, o) => kit.frameOn(region, [L.width, H - header], o),
      get G() { return G() },
      shot: (keys, e) => G().camera(shotAt(t, keys, e)),
      flatShot: (cam2d = { x: L.width / 2, y: (header + H) / 2, z: 1 }, o) => flatShot(cam2d, H - header, o),
      frameOn3: (points, o) => frameOn3(points, [L.width, L.height], viewOf(), o),
      asset: file => `${base}assets/${file}`,
    }
  }

  function clipRange(id) {
    const c = T.tracks.scene.find(x => x.id === id)
    if (!c) throw new Error(`no clip ${id} in timeline.json`)
    const first = frameOf(c.start, T.fps)
    return { c, first, frames: frameOf(c.end, T.fps) - first }
  }

  /** c.plate for a clip at frame f: draws the plate's frame behind the camera, filling the stage. */
  function plateOf(clip, f) {
    const draw = (o = {}) => {
      const p = plates[clip]
      if (!p) throw new Error(`no plate for ${clip}: name it in video.json plates (studio plate renders it)`)
      const href = `${base}${p.dir}/f${String(f).padStart(5, '0')}.png`
      if (!decoded.has(href)) {
        const img = new Image()
        img.src = href
        decoded.set(href, img.decode().catch(() => { throw new Error(`plate frame missing: ${p.dir}/f${String(f).padStart(5, '0')}.png`) }))
        if (decoded.size > 240) decoded.delete(decoded.keys().next().value)
      }
      pending.push(decoded.get(href))
      stage.el('plate', 'image', { href, x: 0, y: 0, width: L.width, height: L.height, preserveAspectRatio: 'none',
        opacity: o.opacity ?? 1, box: o.box }, 'back')
    }
    draw.at = name => {
      const p = plates[clip], pt = (platePoints[clip] ?? {})[f]?.[name]
      if (!p || !pt) return null
      return pt[2] ? [pt[0] * L.width / p.width, pt[1] * L.height / p.height] : null
    }
    return draw
  }

  function context(clip, t) {
    const { c, first, frames } = clipRange(clip)
    const { at, end, word, phrase, cue, sentences } = clipTimes(T, clip, first / T.fps)
    return {
      ...frameContext(t), dur: frames / T.fps, plate: plateOf(clip, Math.round(t * T.fps)),
      clip, index: T.tracks.scene.indexOf(c), title: c.title, chapters: T.tracks.scene, timeline: T,
      at, end, word, phrase, cue, sentences,
      P: (t0, d, e) => kit.prog(t, t0, d, e),
      focus: (names, from, o = {}) => asked.focus.push({ names: [].concat(names), from, ...o, sentences }),
      shots: (keys, o = {}) => { asked.shots = { keys, ...o } },
      scene: (other, at, o = {}) => nestScene(other, at, o),
      recall: (other, at = 'end', o = {}) => nestScene(other, at, { layer: 'over', ...o }),
    }
  }

  // What a scene asked of this frame (`asked`), resolved after it has drawn: focus calls and shots.
  let asked = { focus: [], shots: null }
  let depth = 0

  /** Draw chapter `other` at its time `at` (seconds, or 'end') inside this frame: fitted into `into`
   * [x, y, w, h] when given (a callback's inset), at opacity `op`. */
  function nestScene(other, at, { into, op = 1, layer = 'main', key } = {}) {
    if (!scenes[other]) throw new Error(`no scene ${other} to draw`)
    if (depth > 1) throw new Error(`scene ${other}: scenes nest at most two deep`)
    const { frames } = clipRange(other)
    const t = at === 'end' ? (frames - 1) / T.fps : Math.max(0, Math.min((frames - 1) / T.fps, at))
    const H = L.height
    const transform = into ? `translate(${into[0]} ${into[1]}) scale(${into[2] / L.width} ${into[3] / H})` : undefined
    const saved = asked, focusing = stage.focusing
    asked = { focus: [], shots: null }
    depth += 1
    try {
      return stage.nest(key ?? `${other}@${t.toFixed(3)}`, { opacity: op, transform }, () => {
        const c = context(other, t)
        scenes[other](c)
        resolveFrame(c)
      }, layer)
    } finally { depth -= 1; asked = saved; stage.focusing = focusing }
  }

  /** Box [x0, y0, x1, y1] round every node drawn this frame whose name mentions `name`, in world pixels. */
  function boxOf(name) {
    const want = String(name).toLowerCase().split(/[^a-z0-9]+/).filter(Boolean)
    const inv = stage.camera.getCTM()?.inverse()
    let box = null
    for (const key of stage.order) {
      const { node } = stage.nodes.get(key)
      if (node.tagName === 'g' || !stage.camera.contains(node)) continue
      const own = new Set(String(node.getAttribute('data-box') ?? '').toLowerCase().split(/[^a-z0-9]+/))
      if (!want.every(w => own.has(w))) continue
      const b = node.getBBox(), m = inv && node.getCTM() ? inv.multiply(node.getCTM()) : null
      for (const [x, y] of [[b.x, b.y], [b.x + b.width, b.y + b.height], [b.x, b.y + b.height], [b.x + b.width, b.y]]) {
        const p = m ? { x: m.a * x + m.c * y + m.e, y: m.b * x + m.d * y + m.f } : { x, y }
        box = box ? [Math.min(box[0], p.x), Math.min(box[1], p.y), Math.max(box[2], p.x), Math.max(box[3], p.y)] : [p.x, p.y, p.x, p.y]
      }
    }
    if (!box) throw new Error(`nothing named ${JSON.stringify(name)} is drawn for the camera to frame`)
    return box
  }

  /** Focus and shots, now that the scene has drawn (shots frame named boxes as drawn). */
  function resolveFrame(c) {
    const { t } = c
    if (asked.shots) {
      const { keys, move = SHOT_MOVE, margin = 80 } = asked.shots
      const wide = { x: L.width / 2, y: (c.header + c.H) / 2, z: 1 }
      const shotOf = (spec, back) => spec === 'wide' ? wide : spec === 'back' ? back
        : Array.isArray(spec) && spec[0] === 'close' ? c.frameOn(boxOf(spec[1]), { margin, ...(spec[2] ?? {}) })
        : spec
      const ks = []
      let before = wide, current = wide
      for (const [kt, spec, e] of keys) {
        const next = shotOf(spec, before)
        if (!(Array.isArray(spec) && spec[0] === 'close')) before = next
        if (!ks.length) ks.push([kt, next])
        else ks.push([kt, current], [kt + move, next, e ?? 'inOut'])
        current = next
      }
      c.camAt(ks)
    }
    if (asked.focus.length) {
      // The newest focus that has started takes over; each lifts at the end of its sentence (or `until`).
      const weights = new Map()
      let amount = 0, dim, blur
      const started = asked.focus.filter(f => t >= f.from - FOCUS_IN).sort((a, b) => a.from - b.from)
      started.forEach((f, i) => {
        const s = f.sentences.find(x => x.start <= f.from + 0.01 && f.from <= x.end + 0.6)
        const until = f.until ?? (s ? s.end + 0.3 : f.from + 2.5)
        const on = kit.prog(t, f.from - FOCUS_IN, FOCUS_IN) * (1 - kit.prog(t, until, FOCUS_OUT))
        const next = started[i + 1]
        const handed = next ? kit.prog(t, next.from - FOCUS_IN, FOCUS_IN) : 0
        for (const n of f.names) weights.set(n, Math.max(weights.get(n) ?? 0, on * (1 - handed)))
        amount = Math.max(amount, on)
        dim = f.dim ?? dim; blur = f.blur ?? blur
      })
      if (amount > 0) stage.focusing = { weights, amount, dim, blur }
    }
  }

  /** A board: the frame in force (rough outlines in stage units) and the screen note being spoken. */
  function board(c) {
    const { S, t, W, H, unit, sentences } = c
    const px = ([x, y]) => [W / 2 + x * unit, H / 2 - y * unit]
    const startOf = id => sentences.find(n => n.id === id)?.start ?? 0
    const frame = [...(boards[c.clip] ?? [])].sort((a, b) => startOf(a.from) - startOf(b.from)).filter(f => startOf(f.from) <= t).pop()
    S.text('board:tag', W - 40, 40, 'BOARD', { size: 18, fill: 'var(--faint)', anchor: 'end', weight: 600, box: 'board tag' })
    ;(frame?.elements ?? []).forEach((e, i) => {
      const k = `board:${i}`
      if ('box' in e) {
        const [x, y] = px(e.at), w = (e.w ?? 2.4) * unit, h = (e.h ?? 0.9) * unit
        S.rect(k, x - w / 2, y - h / 2, w, h, { stroke: 'var(--dim)', sw: 2, dash: '8 8', r: 0.08 * unit })
        if (e.box) S.text(k + ':t', x, y, e.box, { size: 22, anchor: 'middle', box: `board box ${e.box}` })
      } else if ('text' in e) {
        const [x, y] = px(e.at)
        // Board geometry and type share stage units; retain explicit pixel sizes from older boards.
        const size = e.size === undefined ? 32 : e.size <= 8 ? e.size * unit : e.size
        S.text(k, x, y, e.text, { size, anchor: 'middle', box: `board text ${e.text}` })
      } else if ('arrow' in e || 'line' in e) {
        const [a, b] = e.arrow ?? e.line, [x1, y1] = px(a), [x2, y2] = px(b)
        S.line(k, x1, y1, x2, y2, { stroke: 'var(--dim)', sw: 2, dash: '6 6', arrow: 'arrow' in e })
      } else if ('dot' in e) {
        const [x, y] = px(e.dot)
        S.circle(k, x, y, (e.r ?? 0.18) * unit, { stroke: 'var(--dim)', sw: 2 })
      }
    })
    const noted = [...sentences].reverse().find(n => n.start <= t && notes[n.id])
    if (noted) {
      const alone = !frame
      const text = alone ? notes[noted.id] : `${noted.id}  ${notes[noted.id]}`
      const size = alone ? 34 : 26, max = Math.floor(W * .84 / (size * .56))
      const lines = ['']
      for (const word of text.split(/\s+/)) {
        if (lines.at(-1).length + word.length + 1 > max) lines.push('')
        lines[lines.length - 1] += (lines.at(-1) ? ' ' : '') + word
      }
      lines.slice(0, 3).forEach((line, i) => S.text(`board:note:${i}`, alone ? W / 2 : W * .08,
        (alone ? H * .42 : H - 105) + i * 32, line + (i === 2 && lines.length > 3 ? '…' : ''),
        { size, anchor: alone ? 'middle' : 'start', fill: alone ? 'var(--ink)' : 'var(--dim)', box: `board note ${i}` }))
    }
  }

  /**
   * Draw frame `f` of a clip (0-based within the clip) with the given layers:
   * all (the scene) | background (the bare background).
   * Returns {error} when the scene throws: the CLI reports it as an engine error.
   */
  let available = null // desk replay: boards remain until an actual scene-save event
  function draw(clip, f, layers = 'all') {
    const { first, frames } = clipRange(clip)
    const frame = Math.min(frames - 1, Math.max(0, f))
    const t = frame / T.fps
    begin()
    pending = []
    let error = null
    if (layers !== 'background') {
      const c = context(clip, t)
      asked = { focus: [], shots: null }
      try {
        if (scenes[clip] && (!available || available.has(clip))) {
          scenes[clip](c)
          resolveFrame(c)
          joinOut(clip, c)
        } else board(c)
        if (overlay) overlay(c)
      } catch (e) {
        error = `${clip} at ${t.toFixed(3)} s: ${e && e.stack ? e.stack : e}`
      }
    }
    try {
      end()
    } catch (e) {
      error ??= `${clip} at ${t.toFixed(3)} s (3D): ${e && e.stack ? e.stack : e}`
      stage.end()
    }
    if (error) return { error }
    const done = { clip, frame, t }
    return pending.length ? Promise.all(pending).then(() => done, e => ({ error: `${clip} at ${t.toFixed(3)} s: ${e.message}` })) : done
  }

  /**
   * The join into the next chapter, drawn in this chapter's quiet tail (the cut itself stays a cut
   * between two rendered clips, so each clip still renders alone). The incoming chapter says how
   * it wants to be joined with `export const join`:
   *   'dissolve' (the default)  the next chapter's first frame fades in over this one's last moments
   *   {match: 'name'}           a match cut: this chapter's camera carries the named thing to where
   *                             the next chapter first draws it, while the dissolve runs
   *   'hard'                    no join: a straight cut
   * A join only uses the silence after this chapter's last word; with less than JOIN_MIN of it, the
   * cut is hard.
   */
  function joinSpan(clip) {
    const i = T.tracks.scene.findIndex(x => x.id === clip), next = T.tracks.scene[i + 1]
    if (!next || !scenes[next.id] || (available && !available.has(next.id))) return null
    const how = joins[next.id] ?? 'dissolve'
    if (how === 'hard') return null
    const { c: cl, frames } = clipRange(clip)
    const dur = frames / T.fps
    const last = Math.max(0, ...T.tracks.narration.filter(n => n.clip === clip).map(n => n.end - cl.start))
    const span = Math.min(JOIN_MAX, dur - last - JOIN_CLEAR)
    if (span < JOIN_MIN) return null
    return { next: next.id, how, from: dur - span, span, dur }
  }

  function joinOut(clip, c) {
    const j = joinSpan(clip)
    if (!j || c.t < j.from) return
    // Reaches 1 on the clip's last frame, so the next clip's first frame continues it exactly.
    const k = kit.ease.inOut(Math.min(1, (c.t - j.from) / Math.max(1 / T.fps, j.span - 1 / T.fps)))
    if (j.how && typeof j.how === 'object' && j.how.match) {
      // Where the thing is now (world) and where the next chapter first shows it (its own world, at
      // its own camera); move this chapter's camera so the first lands on the second.
      const here = boxOf(j.how.match)
      const there = measureIn(j.next, j.how.match)
      const cam = currentCam()
      const sx = (there[2] - there[0]) / Math.max(1, here[2] - here[0])
      const zEnd = cam.z * sx
      // Screen position of `here`'s centre must become `there`'s centre on screen.
      const hc = [(here[0] + here[2]) / 2, (here[1] + here[3]) / 2], tc = [(there[0] + there[2]) / 2, (there[1] + there[3]) / 2]
      const W = L.width, Hh = L.height
      const end = { x: hc[0] - (tc[0] - W / 2) / zEnd, y: hc[1] - (tc[1] - Hh / 2) / zEnd, z: zEnd }
      const z = cam.z * (zEnd / cam.z) ** k
      stage.cam(cam.x + (end.x - cam.x) * k, cam.y + (end.y - cam.y) * k, z)
    }
    // A dissolve: this chapter fades as the next one's first frame comes up over it.
    for (const g of [stage.layers.back, stage.camera, stage.layers.over]) g.setAttribute('opacity', 1 - k)
    nestScene(j.next, 0, { op: k, layer: 'ui', key: `join:${j.next}` })
  }

  /** The camera the scene left this frame: centre and zoom, read back from the camera group. */
  function currentCam() {
    const m = stage.camera.transform.baseVal.consolidate()?.matrix
    const z = m ? m.a : 1, tx = m ? m.e : 0, ty = m ? m.f : 0
    return { x: (L.width / 2 - tx) / z, y: (L.height / 2 - ty) / z, z }
  }

  /** Where chapter `other` first draws `name`, on screen: drawn hidden, measured, then removed. */
  function measureIn(other, name) {
    const g = nestScene(other, 0, { op: 0, layer: 'ui', key: `measure:${other}` })
    const want = String(name).toLowerCase().split(/[^a-z0-9]+/).filter(Boolean)
    let box = null
    for (const n of g.querySelectorAll('[data-box]')) {
      const own = new Set(n.getAttribute('data-box').toLowerCase().split(/[^a-z0-9]+/))
      if (!want.every(w => own.has(w)) || n.tagName === 'g') continue
      const r = n.getBoundingClientRect(), o = stage.svg.getBoundingClientRect()
      const sx = L.width / o.width, sy = L.height / o.height
      const b = [(r.left - o.left) * sx, (r.top - o.top) * sy, (r.right - o.left) * sx, (r.bottom - o.top) * sy]
      box = box ? [Math.min(box[0], b[0]), Math.min(box[1], b[1]), Math.max(box[2], b[2]), Math.max(box[3], b[3])] : b
    }
    if (!box) throw new Error(`join: the next chapter ${other} draws nothing named ${JSON.stringify(name)} on its first frame`)
    return box
  }

  /** Draw the frame at absolute time `at` (the desk's live playback). */
  function drawAt(at, layers = 'all') {
    const f = frameOf(at, T.fps)
    const c = T.tracks.scene.find(x => frameOf(x.start, T.fps) <= f && f < frameOf(x.end, T.fps)) ?? T.tracks.scene[T.tracks.scene.length - 1]
    return draw(c.id, f - frameOf(c.start, T.fps), layers)
  }

  // The look sheet: the built-in pages (look.js), the colour legend's when video.json declares one, then
  // the video's own from scenes/look.js, which exports `default function look(c)` and optionally `pages`,
  // its pages' titles (c.page is the page's index).
  let own = null
  const builtIn = () => (Object.keys(legend).length ? [...PAGES, LEGEND_PAGE] : PAGES)
  /** The look sheet's page titles; loads scenes/look.js afresh. */
  async function lookPages() {
    const file = `${base}scenes/look.js`
    own = (await exists(file)) ? await importScene('look.js', `${file}?v=${version}.${Date.now()}`) : null
    if (own && typeof own.default !== 'function') throw new Error('scenes/look.js must export default function look(c)')
    return [...builtIn().map(p => p.title), ...(own ? own.pages ?? ["the video's own elements"] : [])]
  }

  /** Draw look-sheet page n (0-based); {error} when it throws. */
  function look(n, titles = []) {
    begin()
    const pages = builtIn()
    const c = { ...frameContext(0), dur: 0, C: kit.C, page: n - pages.length, declared: legend }
    let error = null
    try {
      if (n < pages.length) pages[n].draw(c)
      else own.default(c)
    } catch (e) {
      error = `look page ${n + 1}: ${e && e.stack ? e.stack : e}`
    }
    // The page's name, in the bottom corner: at the top it would sit where a scene's header goes.
    stage.text('look:tag', L.width - 24, L.height - 26, `LOOK ${n + 1}/${titles.length || n + 1}  ${titles[n] ?? ''}`.trim(),
      { size: 18, fill: 'var(--faint)', anchor: 'end', weight: 600, box: 'look tag', layer: 'ui' })
    try {
      end()
    } catch (e) {
      error ??= `look page ${n + 1} (3D): ${e && e.stack ? e.stack : e}`
      stage.end()
    }
    return error ? { error } : { page: n + 1 }
  }

  return {
    draw, drawAt, lookPages, look,
    setAvailable: clips => { available = clips == null ? null : new Set(clips) },
    boxes: () => ({ boxes: [...stage.boxes(), ...(stage3d?.boxes() ?? [])] }),
    /** The WebGL renderer this page uses (doctor prints it); makes the 3D stage if no scene has. */
    gl: () => G().info(),
    info: () => ({ fps: T.fps, width: L.width, height: L.height, duration: T.duration,
      clips: T.tracks.scene.map(c => ({ id: c.id, ...clipRange(c.id), c: undefined, hasScene: !!scenes[c.id] })) }),
    reload: load,
    get timeline() { return T },
  }
}
