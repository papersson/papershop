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
//   W, H, unit       the stage above the caption band, in pixels; unit = H / 8 (the other engines' unit)
//   header, view     the strip at the stage's top that framing keeps clear (layout.json header.height,
//                    0 by default), and the stage below it as [x, y, w, h]
//   camAt(keys, e)   point the camera along keys [time, {x, y, z}, ease?] at t, each key's point centred
//                    in the view; returns {x, y, z}. frameOn([x0, y0, x1, y1]) is a key that fits a region
//   at(id, off)      start of a sentence ("03" means "<clip>_03"); end(id, off) its end
//   word(id, i, off) the i-th spoken word; phrase(id, text, off) when the voice says that phrase
//   cue(name, off)   a timeline cue; P(t0, d, ease) progress of a movement; kit: the helpers
//   legend           the video's colour legend (video.json legend) as meaning -> CSS colour: draw a
//                    meaning with {stroke: c.legend.request, means: 'request'} and the legend check sees it
//   motion           'full' or 'reduced' (video.json motion): the feel helpers drop shake and hitstop
//                    when reduced (templates/live/scenes/example-feel.js)
//   clip, index, chapters, timeline, layout, asset(file)
//   plate(o)         draw the chapter's plate behind everything (video.json plates: Blender renders it,
//                    the kit's plates.py), filling the stage above the band; plate.at(name) is a projected
//                    object's point on the stage, [x, y], to put a label on; null when it is behind the camera

import { Stage } from './stage.js'
import { Stage3D } from './stage3d.js'
import * as kit from './kit.js'
import { PAGES, LEGEND_PAGE } from './look.js'
import { captionLines, clipTimes, frameOf } from '../../shared/timing.js'
import { flatShot, frameOn3, shotAt } from '../../shared/camera3d.js'

const DEFAULT_LAYOUT = { width: 1920, height: 1080, fps: 30, band: { height: 160, style: 'opaque' } }

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
  let T, L, scenes, overlay, boards, notes, legend, colours, motion, plates, platePoints, version = 0
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
    for (const c of T.tracks.scene) {
      const url = `${base}scenes/${c.id}.js?v=${version}`
      if (await exists(`${base}scenes/${c.id}.js`)) scenes[c.id] = (await importScene(`${c.id}.js`, url)).default
    }
    overlay = (await exists(`${base}scenes/overlay.js`)) ? (await importScene('overlay.js', `${base}scenes/overlay.js?v=${version}`)).default : null
  }
  await load()
  await Promise.all(['400 20px "IBM Plex Sans"', '500 20px "IBM Plex Sans"', '600 20px "IBM Plex Sans"',
    '700 20px "IBM Plex Sans"', '400 20px "IBM Plex Mono"', '500 20px "IBM Plex Mono"'].map(f => document.fonts.load(f)))

  const stage = new Stage(svg, { width: L.width, height: L.height })
  const bandTop = () => L.height - L.band.height
  const viewOf = () => [0, L.header?.height ?? 0, L.width, bandTop() - (L.header?.height ?? 0)]
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
    const H = bandTop(), header = L.header?.height ?? 0
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

  /** c.plate for a clip at frame f: draws the plate's frame behind the camera, above the band. */
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
      stage.el('plate', 'image', { href, x: 0, y: 0, width: L.width, height: bandTop(), preserveAspectRatio: 'none',
        opacity: o.opacity ?? 1, box: o.box }, 'back')
    }
    draw.at = name => {
      const p = plates[clip], pt = (platePoints[clip] ?? {})[f]?.[name]
      if (!p || !pt) return null
      return pt[2] ? [pt[0] * L.width / p.width, pt[1] * bandTop() / p.height] : null
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

  /** The caption band and the caption chunk spoken at absolute time `at` (Remotion's look), or the `given`
   * lines. A band of height 0 is a video without captions: nothing is drawn. */
  function band(at, withCaptions, given) {
    if (!(L.band.height > 0)) return
    const top = bandTop(), font = L.band.font ?? 38
    stage.rect('band', 0, top, L.width, L.band.height, { fill: 'var(--band)', r: 0, layer: 'ui' })
    const chunk = withCaptions && !given ? T.tracks.captions.find(x => x.start <= at && at < x.end) : null
    const lines = given ?? (chunk ? captionLines(chunk, L) : [])
    const lh = font * 1.3, y0 = top + L.band.height / 2 - (lines.length * lh) / 2 + lh / 2
    lines.forEach((line, i) => stage.el(`caption${i}`, 'text', {
      x: L.width / 2, y: y0 + i * lh, text: line, fill: 'var(--ink)', 'font-size': font, 'font-weight': 400,
      'text-anchor': 'middle', 'dominant-baseline': 'middle', 'font-family': 'var(--sans)', box: 'caption', 'data-kind': 'caption',
    }, 'ui'))
  }

  /**
   * Draw frame `f` of a clip (0-based within the clip) with the given layers:
   * all | no-captions (band, no caption text) | no-band (the scene alone) | background.
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
      try {
        if (scenes[clip] && (!available || available.has(clip))) scenes[clip](c)
        else board(c)
        if (overlay) overlay(c)
      } catch (e) {
        error = `${clip} at ${t.toFixed(3)} s: ${e && e.stack ? e.stack : e}`
      }
      if (layers !== 'no-band') band((first + frame) / T.fps, layers === 'all')
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

  /** Draw look-sheet page n (0-based) with the band showing `caption` (lines); {error} when it throws. */
  function look(n, caption = [], titles = []) {
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
    band(0, true, caption)
    // The page's name, in the band's corner: on the stage it would sit where a scene's header goes.
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
    boxes: () => ({ band: { y: bandTop(), h: L.band.height }, boxes: [...stage.boxes(), ...(stage3d?.boxes() ?? [])] }),
    /** The WebGL renderer this page uses (doctor prints it); makes the 3D stage if no scene has. */
    gl: () => G().info(),
    info: () => ({ fps: T.fps, width: L.width, height: L.height, duration: T.duration,
      clips: T.tracks.scene.map(c => ({ id: c.id, ...clipRange(c.id), c: undefined, hasScene: !!scenes[c.id] })) }),
    reload: load,
    get timeline() { return T },
  }
}
