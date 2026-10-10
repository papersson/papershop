// The live engine's side of the studio's engine interface (the same operations and JSON as the
// Remotion and Motion Canvas engines). It serves the engine and the video folder over a local
// static server (no bundler: scenes are plain ES modules), opens render.html in a headless browser,
// and draws exactly the frames it needs.
//
//   node cli.mjs still    --video DIR --clip ID --t SEC --out PNG [--layers L] [--scale S]
//   node cli.mjs stills   --video DIR --requests JSON
//   node cli.mjs render   --video DIR --clip ID --out MP4 [--quality draft|final] [--range A B]
//   node cli.mjs boxes    --video DIR --clip ID --t SEC
//   node cli.mjs boxesAt  --video DIR --requests JSON
//   node cli.mjs duration --video DIR --clip ID
//   node cli.mjs look     --video DIR --out DIR [--caption JSON]   the look sheet: look-<n>.png per page, with its boxes
//
// A scene that throws fails the call with the clip, the time and the error (the kit's EngineError).
import { chromium } from 'playwright-core'
import { spawn, spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync, createReadStream } from 'node:fs'
import { createServer } from 'node:http'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { frameOf } from '../shared/timing.js'

const ENGINE = path.dirname(fileURLToPath(import.meta.url))
const SHARED = path.join(ENGINE, '..', 'shared') // the engines' shared modules, which the kit imports as ../../shared/
const QUALITY = { draft: { scale: 0.5, crf: 26 }, final: { scale: 1, crf: 18 } }
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json',
  '.css': 'text/css', '.woff2': 'font/woff2', '.woff': 'font/woff', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.webp': 'image/webp' }
const DEFAULT_LAYOUT = { width: 1920, height: 1080, fps: 30, band: { height: 160, style: 'opaque' } }

const [op, ...rest] = process.argv.slice(2)
const opt = {}
for (let i = 0; i < rest.length; i++) {
  if (!rest[i].startsWith('--')) continue
  const key = rest[i].slice(2)
  if (key === 'range') opt.range = [Number(rest[++i]), Number(rest[++i])]
  else opt[key] = rest[i + 1] && !rest[i + 1].startsWith('--') ? rest[++i] : true
}
const log = (...a) => console.error(...a)

const timeline = video => JSON.parse(readFileSync(path.join(video, 'timeline.json'), 'utf8'))
function layoutOf(video) {
  const f = opt.layout ? path.resolve(opt.layout) : path.join(video, 'layout.json')
  return existsSync(f) ? JSON.parse(readFileSync(f, 'utf8')) : DEFAULT_LAYOUT
}
function clipRange(t, id) {
  const c = t.tracks.scene.find(x => x.id === id)
  if (!c) throw new Error(`no clip ${id} in timeline.json`)
  const first = frameOf(c.start, t.fps)
  return { first, frames: frameOf(c.end, t.fps) - first }
}
const frameIn = (t, clip, sec) => Math.min(clipRange(t, clip).frames - 1, Math.max(0, frameOf(Number(sec), t.fps)))

/** A static server for the engine (/engine/), the engines' shared modules (/shared/) and the video folder (/video/); nothing outside them. */
function serve(video) {
  const layoutFile = opt.layout ? path.resolve(opt.layout) : path.join(video, 'layout.json')
  const server = createServer((req, res) => {
    const url = decodeURIComponent(req.url.split('?')[0])
    let file = null
    if (url === '/layout.json') file = existsSync(layoutFile) ? layoutFile : null
    else if (url.startsWith('/engine/')) file = path.join(ENGINE, url.slice(8))
    else if (url.startsWith('/shared/')) file = path.join(SHARED, url.slice(8))
    else if (url.startsWith('/video/')) file = path.join(video, url.slice(7))
    const inside = file && ([ENGINE, SHARED, video].some(dir => file.startsWith(dir + path.sep)) || file === layoutFile)
    if (!file || !inside || !existsSync(file) || !statSync(file).isFile()) {
      res.writeHead(url === '/layout.json' ? 404 : 404, { 'Cache-Control': 'no-store' })
      return res.end(url === '/layout.json' ? JSON.stringify(DEFAULT_LAYOUT) : 'not found')
    }
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] ?? 'application/octet-stream', 'Cache-Control': 'no-store' })
    if (req.method === 'HEAD') return res.end()
    createReadStream(file).pipe(res)
  })
  return new Promise(ok => server.listen(0, '127.0.0.1', () => ok(server)))
}

async function withPage(video, fn) {
  const server = await serve(video)
  const port = server.address().port
  const lay = layoutOf(video)
  const browser = await chromium.launch({ executablePath: opt.browser || undefined, args: ['--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1'] })
  try {
    const page = await browser.newPage({ viewport: { width: lay.width, height: lay.height }, deviceScaleFactor: 1 })
    page.on('console', m => (process.env.STUDIO_DEBUG || m.type() === 'error') && log('page', m.type() + ':', m.text()))
    page.on('pageerror', e => log('page error:', e.message))
    await page.goto(`http://127.0.0.1:${port}/engine/render.html?video=/video/&layout=/layout.json`)
    await page.waitForFunction(() => window.studioReady || window.studioError, null, { timeout: 120_000 })
    const err = await page.evaluate(() => window.studioError)
    if (err) throw new Error(err)
    return await fn(page)
  } finally {
    await browser.close()
    server.close()
  }
}

async function drawn(page, clip, frame, layers = 'all') {
  const r = await page.evaluate(([c, f, l]) => window.studio.draw(c, f, l), [clip, frame, layers])
  if (r.error) throw new Error(`scene error in ${r.error}`)
  return r
}

function scaled(buf, scale, out) {
  if (Number(scale) === 1) return writeFileSync(out, buf)
  const r = spawnSync('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-i', '-', '-vf', `scale=iw*${scale}:-2`, out], { input: buf })
  if (r.status !== 0) throw new Error(`could not scale a still to ${out}`)
}

async function stills(video, requests) {
  const t = timeline(video)
  const done = []
  await withPage(video, async page => {
    for (const r of requests) {
      const frame = frameIn(t, r.clip, r.t)
      await drawn(page, r.clip, frame, r.layers ?? 'all')
      const jpeg = /\.jpe?g$/i.test(r.out)
      mkdirSync(path.dirname(r.out), { recursive: true })
      scaled(await page.screenshot(jpeg ? { type: 'jpeg', quality: 85 } : { type: 'png' }), r.scale ?? 1, r.out)
      done.push({ clip: r.clip, t: Number(r.t), frame: clipRange(t, r.clip).first + frame, out: r.out })
    }
  })
  return { stills: done }
}

async function boxesAt(video, requests) {
  const t = timeline(video)
  const frames = await withPage(video, async page => {
    const out = []
    for (const r of requests) {
      await drawn(page, r.clip, frameIn(t, r.clip, r.t))
      const b = await page.evaluate(() => window.studio.boxes())
      out.push({ clip: r.clip, t: Number(r.t), band: b.band, boxes: b.boxes })
    }
    return out
  })
  return { frames }
}

async function render(video, clip, out, quality, range) {
  const q = QUALITY[quality ?? 'draft']
  if (!q) throw new Error(`unknown quality ${quality}`)
  const t = timeline(video)
  const { frames } = clipRange(t, clip)
  const [a, b] = range ? [frameOf(range[0], t.fps), Math.min(frames - 1, frameOf(range[1], t.fps))] : [0, frames - 1]
  mkdirSync(path.dirname(out), { recursive: true })
  const started = Date.now()
  await withPage(video, async page => {
    const scale = q.scale === 1 ? [] : ['-vf', `scale=iw*${q.scale}:-2`]
    const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(t.fps), '-c:v', 'mjpeg', '-i', '-', ...scale,
      '-c:v', 'libx264', '-crf', String(q.crf), '-pix_fmt', 'yuv420p', '-r', String(t.fps), out], { stdio: ['pipe', 'inherit', 'inherit'] })
    const closed = new Promise((ok, fail) => ff.on('close', code => (code === 0 ? ok() : fail(new Error(`ffmpeg exited ${code}`)))))
    for (let f = a; f <= b; f++) {
      await drawn(page, clip, f)
      const jpg = await page.screenshot({ type: 'jpeg', quality: 92 })
      if (!ff.stdin.write(jpg)) await new Promise(r => ff.stdin.once('drain', r))
    }
    ff.stdin.end()
    await closed
  })
  return { clip, out, quality: quality ?? 'draft', frames: b - a + 1, seconds: (Date.now() - started) / 1000 }
}

async function look(video, outDir, caption) {
  const lines = caption ? JSON.parse(caption) : []
  const pages = await withPage(video, async page => {
    const titles = await page.evaluate(() => window.studio.lookPages())
    const done = []
    mkdirSync(outDir, { recursive: true })
    for (let i = 0; i < titles.length; i++) {
      const r = await page.evaluate(([n, l, all]) => window.studio.look(n, l, all), [i, lines, titles])
      if (r.error) throw new Error(`look sheet error in ${r.error}`)
      const out = path.join(outDir, `look-${i + 1}.png`)
      writeFileSync(out, await page.screenshot({ type: 'png' }))
      done.push({ page: i + 1, title: titles[i], out, boxes: (await page.evaluate(() => window.studio.boxes())).boxes })
    }
    return done
  })
  return { pages }
}

function duration(video, clip) {
  const t = timeline(video)
  const { frames } = clipRange(t, clip)
  return { clip, frames, fps: t.fps, seconds: frames / t.fps }
}

const ops = {
  still: () => stills(opt.video, [{ clip: opt.clip, t: opt.t, out: opt.out, layers: opt.layers, scale: opt.scale }]),
  stills: () => stills(opt.video, JSON.parse(readFileSync(opt.requests, 'utf8'))),
  render: () => render(opt.video, opt.clip, opt.out, opt.quality, opt.range),
  boxes: async () => {
    const { frames } = await boxesAt(opt.video, [{ clip: opt.clip, t: opt.t }])
    return { clip: opt.clip, t: Number(opt.t), boxes: { band: frames[0].band, boxes: frames[0].boxes } }
  },
  boxesAt: () => boxesAt(opt.video, JSON.parse(readFileSync(opt.requests, 'utf8'))),
  duration: async () => duration(opt.video, opt.clip),
  look: () => look(opt.video, path.resolve(opt.out), opt.caption),
}
if (!ops[op]) {
  log(`unknown op ${op}; expected one of ${Object.keys(ops).join(', ')}`)
  process.exit(2)
}
opt.video = path.resolve(opt.video)
ops[op]().then(
  r => {
    console.log(JSON.stringify(r))
    process.exit(0)
  },
  e => {
    log(e.stack || String(e))
    process.exit(1)
  },
)
