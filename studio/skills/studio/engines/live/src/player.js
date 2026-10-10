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
//   t, dur           time in the clip and the clip's length
//   W, H, unit       the stage above the caption band, in pixels; unit = H / 8 (the other engines' unit)
//   header, view     the strip at the stage's top that framing keeps clear (layout.json header.height,
//                    0 by default), and the stage below it as [x, y, w, h]
//   camAt(keys, e)   point the camera along keys [time, {x, y, z}, ease?] at t, each key's point centred
//                    in the view; returns {x, y, z}. frameOn([x0, y0, x1, y1]) is a key that fits a region
//   at(id, off)      start of a sentence ("03" means "<clip>_03"); end(id, off) its end
//   word(id, i, off) the i-th spoken word; phrase(id, text, off) when the voice says that phrase
//   cue(name, off)   a timeline cue; P(t0, d, ease) progress of a movement; kit: the helpers
//   clip, index, chapters, timeline, layout, asset(file)

import { Stage } from './stage.js'
import * as kit from './kit.js'
import { PAGES } from './look.js'
import { captionLines, clipTimes, frameOf } from '../../shared/timing.js'

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

async function exists(url) {
  const r = await fetch(url, { method: 'HEAD', cache: 'no-store' })
  return r.ok
}

export async function boot({ svg, video, layout: layoutUrl }) {
  const base = video.endsWith('/') ? video : video + '/'
  let T, L, scenes, overlay, boards, notes, version = 0

  async function load() {
    version += 1
    T = await json(base + 'timeline.json')
    L = layoutUrl ? await json(layoutUrl, DEFAULT_LAYOUT) : DEFAULT_LAYOUT
    boards = await json(base + 'boards/boards.json', {})
    notes = await json(base + 'boards/notes.json', {})
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

  /** What scenes and look pages share: the stage, its size, the header and the camera helpers, at clip time t. */
  function frameContext(t) {
    const H = bandTop(), header = L.header?.height ?? 0
    return {
      S: stage, t, W: L.width, H, unit: H / 8, kit, header, view: [0, header, L.width, H - header], layout: L,
      // S.cam centres the whole frame; a key's point goes to the middle of the view instead.
      camAt: (keys, e) => {
        const k = kit.camAt(t, keys, e)
        stage.cam(k.x, k.y + (L.height / 2 - (header + H) / 2) / k.z, k.z)
        return k
      },
      frameOn: (region, o) => kit.frameOn(region, [L.width, H - header], o),
      asset: file => `${base}assets/${file}`,
    }
  }

  function clipRange(id) {
    const c = T.tracks.scene.find(x => x.id === id)
    if (!c) throw new Error(`no clip ${id} in timeline.json`)
    const first = frameOf(c.start, T.fps)
    return { c, first, frames: frameOf(c.end, T.fps) - first }
  }

  function context(clip, t) {
    const { c, first, frames } = clipRange(clip)
    const { at, end, word, phrase, cue, sentences } = clipTimes(T, clip, first / T.fps)
    return {
      ...frameContext(t), dur: frames / T.fps,
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
        S.text(k, x, y, e.text, { size: e.size ?? 24, anchor: 'middle', box: `board text ${e.text}` })
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
      S.text('board:note', alone ? W / 2 : W * 0.08, alone ? H * 0.45 : H - unit * 0.8, alone ? notes[noted.id] : `${noted.id}  ${notes[noted.id]}`,
        { size: alone ? 34 : 26, anchor: alone ? 'middle' : 'start', fill: alone ? 'var(--ink)' : 'var(--dim)', box: 'board note' })
    }
  }

  /** The caption band and the caption chunk spoken at absolute time `at` (Remotion's look), or the `given` lines. */
  function band(at, withCaptions, given) {
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
  function draw(clip, f, layers = 'all') {
    const { first, frames } = clipRange(clip)
    const frame = Math.min(frames - 1, Math.max(0, f))
    const t = frame / T.fps
    stage.begin()
    stage.rect('background', 0, 0, L.width, L.height, { fill: 'var(--bg)', r: 0, layer: 'back' })
    let error = null
    if (layers !== 'background') {
      const c = context(clip, t)
      try {
        if (scenes[clip]) scenes[clip](c)
        else board(c)
        if (overlay) overlay(c)
      } catch (e) {
        error = `${clip} at ${t.toFixed(3)} s: ${e && e.stack ? e.stack : e}`
      }
      if (layers !== 'no-band') band((first + frame) / T.fps, layers === 'all')
    }
    stage.end()
    return error ? { error } : { clip, frame, t }
  }

  /** Draw the frame at absolute time `at` (the desk's live playback). */
  function drawAt(at, layers = 'all') {
    const f = frameOf(at, T.fps)
    const c = T.tracks.scene.find(x => frameOf(x.start, T.fps) <= f && f < frameOf(x.end, T.fps)) ?? T.tracks.scene[T.tracks.scene.length - 1]
    return draw(c.id, f - frameOf(c.start, T.fps), layers)
  }

  // The look sheet: the built-in pages (look.js), then the video's own from scenes/look.js, which exports
  // `default function look(c)` and optionally `pages`, its pages' titles (c.page is the page's index).
  let own = null
  /** The look sheet's page titles; loads scenes/look.js afresh. */
  async function lookPages() {
    const file = `${base}scenes/look.js`
    own = (await exists(file)) ? await importScene('look.js', `${file}?v=${version}.${Date.now()}`) : null
    if (own && typeof own.default !== 'function') throw new Error('scenes/look.js must export default function look(c)')
    return [...PAGES.map(p => p.title), ...(own ? own.pages ?? ["the video's own elements"] : [])]
  }

  /** Draw look-sheet page n (0-based) with the band showing `caption` (lines); {error} when it throws. */
  function look(n, caption = [], titles = []) {
    stage.begin()
    stage.rect('background', 0, 0, L.width, L.height, { fill: 'var(--bg)', r: 0, layer: 'back' })
    const c = { ...frameContext(0), dur: 0, C: kit.C, page: n - PAGES.length }
    let error = null
    try {
      if (n < PAGES.length) PAGES[n].draw(c)
      else own.default(c)
    } catch (e) {
      error = `look page ${n + 1}: ${e && e.stack ? e.stack : e}`
    }
    band(0, true, caption)
    // The page's name, in the band's corner: on the stage it would sit where a scene's header goes.
    stage.text('look:tag', L.width - 24, L.height - 26, `LOOK ${n + 1}/${titles.length || n + 1}  ${titles[n] ?? ''}`.trim(),
      { size: 18, fill: 'var(--faint)', anchor: 'end', weight: 600, box: 'look tag', layer: 'ui' })
    stage.end()
    return error ? { error } : { page: n + 1 }
  }

  return {
    draw, drawAt, lookPages, look,
    boxes: () => ({ band: { y: bandTop(), h: L.band.height }, boxes: stage.boxes() }),
    info: () => ({ fps: T.fps, width: L.width, height: L.height, duration: T.duration,
      clips: T.tracks.scene.map(c => ({ id: c.id, ...clipRange(c.id), c: undefined, hasScene: !!scenes[c.id] })) }),
    reload: load,
    get timeline() { return T },
  }
}
