// A code tour: real source files, read at a pinned commit, shown the way a reader looks at them.
//
// `studio source VIDEO REPO PATH...` copies files from a git checkout at one commit into
// data/source/ and lists them, with their sha256, in data/source.json. A tour file (data/tour.json,
// or a chapter's data/CLIP/tour.json) names views of those files, each a list of stops:
//
//   {"views": {"assert": {"file": "src/vsr/replica.zig", "cols": 84, "stops": [
//     {"at": "s2-open",   "show": [[646, 662]]},
//     {"at": "s2-checks", "show": [[646, 662]], "focus": [[654, 661]]},
//     {"at": "s2-split",  "show": [[646, 662]], "focus": [[654, 655]], "point": {"line": 655, "text": "sector_size"}},
//     {"at": "s2-switch", "show": [[646, 653], [738, 739]], "focus": [[738, 739]]}]}}}
//
// A stop is where the view arrives at its time (`at`: a cue name, [cue, seconds after] or clip
// seconds). `show` lists line ranges, 1-based and inclusive; a fold row (… N lines) joins two.
// `focus` lines are at full ink and the rest step down; `point` underlines one token, whole on the
// cue. `file` on a stop changes the file: the page slides. Between stops every line that is shown
// in both moves to its new row, so a scroll, a fold or an unfold is one continuous move, and a line
// keeps its identity. The tour check (`studio check --only source`) verifies every file against its
// sha256 and every range and pointed token against the file, so a citation cannot be wrong.
const INK = '#E6EBF0', DIM = '#8C97A4', FAINT = '#56606B', COLD = '#8FD3FF', WARM = '#F5CF7A'
const HOT = '#F2A93B', KEY = '#C3A6F2', LINE = '#2B333C'
const NS = 'http://www.w3.org/2000/svg'
const clamp = n => Math.max(0, Math.min(1, n))
const smooth = u => { u = clamp(u); return u * u * (3 - 2 * u) }
const heavy = u => { u = clamp(u); return u < .5 ? 4 * u ** 3 : 1 - (-2 * u + 2) ** 3 / 2 }
const mix = (a, b, k) => '#' + [0, 1, 2].map(i => Math.round(parseInt(a.slice(1 + i * 2, 3 + i * 2), 16) * (1 - clamp(k)) + parseInt(b.slice(1 + i * 2, 3 + i * 2), 16) * clamp(k)).toString(16).padStart(2, '0')).join('')

export const MOVE = 1.0         // a scroll, fold or unfold, seconds (staging.md: travel 0.7 to 1.2)
export const STEP = 0.45        // focus stepping up or down
export const SLIDE = 0.9        // a change of file
export const ADV = 0.6          // IBM Plex Mono's advance, in ems

const LANG = {
  zig: {keywords: 'const|var|fn|pub|return|if|else|while|for|switch|try|catch|comptime|inline|unreachable|defer|errdefer|break|continue|test|struct|enum|union|and|or|orelse|error|extern|packed|undefined|null|true|false|usize|u8|u16|u32|u63|u64|u128|i64|bool|void|anytype|type', comment: '//'},
  c: {keywords: 'int|char|void|return|if|else|while|for|const|static|struct|sizeof|unsigned|long|switch|case|break', comment: '//'},
  py: {keywords: 'def|return|if|elif|else|while|for|in|import|from|class|with|as|None|True|False|and|or|not|assert', comment: '#'},
}
const langOf = file => ({zig: 'zig', c: 'c', h: 'c', py: 'py', md: 'text', txt: 'text'})[file.split('.').pop()] ?? 'text'

/** One line's coloured parts: comments faint, keywords cold, strings warm, builtins and numbers. */
export function syntax(line, lang = 'zig') {
  if (!LANG[lang]) return [{text: line, kind: 'plain'}]   // prose and unknown languages: no colouring
  const {keywords, comment} = LANG[lang]
  const at = line.indexOf(comment), code = at >= 0 && !inString(line, at) ? line.slice(0, at) : line
  const rest = code.length < line.length ? line.slice(code.length) : ''
  const re = new RegExp(`("(?:[^"\\\\]|\\\\.)*"|'(?:[^'\\\\]|\\\\.)*'|@\\w+|\\b(?:${keywords})\\b|\\b\\d[\\d_]*(?:\\.\\d+)?\\b)`, 'g')
  const parts = code.split(re).filter(Boolean).map(text => ({
    text, kind: /^["']/.test(text) ? 'string' : text.startsWith('@') ? 'builtin' : /^\d/.test(text) ? 'number'
      : new RegExp(`^(?:${keywords})$`).test(text) ? 'keyword' : 'plain',
  }))
  if (rest) parts.push({text: rest, kind: 'comment'})
  return parts
}
const inString = (line, at) => (line.slice(0, at).match(/"/g) ?? []).length % 2 === 1
const TONE = {plain: INK, keyword: COLD, string: WARM, builtin: KEY, number: WARM, comment: DIM}

async function json(url) {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${url}: ${r.status} (run \`studio source\` and write data/tour.json)`)
  return r.json()
}

/** data/source.json, a tour file and every source file, for a chapter at `base` (import.meta.url).
 *  `tour` is the views file inside the video: data/tour.json by default, or a chapter's own
 *  (data/s2/tour.json), so parallel chapter agents never share one file. */
export async function loadTour(base, {tour: tourFile = 'data/tour.json'} = {}) {
  const root = new URL('../', base)
  const source = await json(new URL('data/source.json', root)), tour = await json(new URL(tourFile, root))
  const files = {}
  await Promise.all(Object.entries(source.files).map(async ([path, f]) => {
    const text = await (await fetch(new URL(f.file, root))).text()
    files[path] = text.replace(/\r\n/g, '\n').split('\n')
  }))
  return {source, tour, files}
}

const when = (c, at) => typeof at === 'number' ? at : typeof at === 'string' ? c.cue(at) : c.cue(at[0]) + at[1]
const inRanges = (n, ranges) => (ranges ?? []).some(([a, b]) => n >= a && n <= b)

/** The rows a stop lays out: its lines, with a fold row between ranges that do not touch. */
function rowsOf(stop) {
  const rows = []
  stop.show.forEach(([a, b], i) => {
    if (i) {
      const prev = stop.show[i - 1][1]
      if (a > prev + 1) rows.push({fold: `${prev}-${a}`, n: a - prev - 1})
    }
    for (let n = a; n <= b; n++) rows.push({line: n})
  })
  return rows
}

/** Row positions keyed by line (or fold), centred on the focus, or on the whole when none. */
function layoutOf(stop, rowsVisible) {
  const rows = rowsOf(stop), at = new Map()
  rows.forEach((r, i) => at.set(r.line ?? 'fold ' + r.fold, i))
  const lit = rows.map((r, i) => r.line && inRanges(r.line, stop.focus) ? i : -1).filter(i => i >= 0)
  const mid = lit.length ? (lit[0] + lit.at(-1)) / 2 : (rows.length - 1) / 2
  const half = (rowsVisible - 1) / 2
  // Keep the block inside the page when it fits; otherwise centre the focus.
  let centre = mid
  if (rows.length <= rowsVisible) centre = (rows.length - 1) / 2
  else centre = Math.max(half, Math.min(rows.length - 1 - half, mid))
  return {rows, at, centre}
}

const same = (a, b) => JSON.stringify(a ?? null) === JSON.stringify(b ?? null)

/** The stop showing at time t. A stop takes over only as early as its change needs: a scroll or
 * fold MOVE before it, a new file SLIDE, a focus step STEP, a new pointed token its 0.25 s draw-in,
 * so a token pointed at shortly before the next stop is still drawn. Stops carry t and file. */
export function stopAt(stops, t) {
  const lead = (s, p) => !p ? 0 : s.file !== p.file ? SLIDE : !same(s.show, p.show) ? MOVE : !same(s.focus, p.focus) ? STEP : .25
  let i = 0
  stops.forEach((s, k) => { if (t >= s.t - lead(s, stops[k - 1])) i = k })
  return i
}

/**
 * Draw a view of the tour at the current time inside box [x, y, w, h] (stage pixels).
 * Options: size (type px, the largest that fits `cols` is used, never above it), name, op,
 * header (the file path above the code; default true), commit (show the short hash; default true).
 * Returns {lines: {n: [x, y, w, h]}, size, box} for annotations drawn on top.
 */
export function SourceView(c, tourData, viewName, {box, size = 34, name = viewName, op = 1, header = true, commit = true, layer} = {}) {
  const view = tourData.tour.views[viewName]
  if (!view) throw new Error(`no view ${viewName} in data/tour.json`)
  const [bx, by, bw, bh] = box
  const cols = view.cols ?? 90
  const sz = Math.min(size, bw / ((cols + 6) * ADV)), lh = sz * 1.55, adv = sz * ADV
  const headH = header ? sz * 2.6 : 0
  const top = by + headH, areaH = bh - headH, rowsVisible = Math.floor(areaH / lh)
  const gx = bx + 4.5 * adv, tx = bx + 6 * adv
  const out = {lines: {}, size: sz, box}
  if (op <= 0) return out
  const stops = view.stops.map((s, i) => ({...s, file: s.file ?? view.stops.slice(0, i + 1).reverse().find(x => x.file)?.file ?? view.file, t: when(c, s.at)}))
  const i = stopAt(stops, c.t)
  const cur = stops[i], prev = stops[i - 1] ?? cur
  const moving = cur.file === prev.file && !same(cur.show, prev.show) ? heavy((c.t - (cur.t - MOVE)) / MOVE) : 1
  const slide = cur.file !== prev.file ? heavy((c.t - (cur.t - SLIDE)) / SLIDE) : 1
  const centreY = top + areaH / 2

  const drawPage = (stop, from, u, dx, pageOp, tag) => {
    const lines = tourData.files[stop.file]
    if (!lines) throw new Error(`${stop.file} is not in data/source.json (run studio source)`)
    const lang = langOf(stop.file), A = layoutOf(stop, rowsVisible), B = from && from.file === stop.file ? layoutOf(from, rowsVisible) : null
    const lit = (st, n) => !st.focus?.length || inRanges(n, st.focus)
    const keys = new Set([...A.at.keys(), ...(B ? B.at.keys() : [])])
    for (const k of keys) {
      const inA = A.at.has(k), inB = B?.at.has(k)
      const rowA = inA ? A.at.get(k) - A.centre : null, rowB = inB ? B.at.get(k) - B.centre : null
      const row = inA && inB ? rowB + (rowA - rowB) * u : inA ? rowA : rowB
      const appear = inA && !inB && B ? smooth((u - .35) / .65) : inA ? 1 : 1 - smooth(u / .5)
      const y = centreY + row * lh
      const edge = clamp(Math.min(y - (top + lh * .3), top + areaH - lh * .3 - y) / (lh * 1.2))
      const o = pageOp * appear * edge * op
      if (o <= 0.01) continue
      const key = `${name}:${tag}:${typeof k === 'number' ? k : k.replace(/\s/g, '-')}`
      if (typeof k !== 'number') {
        const n = (A.rows.find(r => 'fold ' + r.fold === k) ?? B.rows.find(r => 'fold ' + r.fold === k)).n
        c.S.text(key, tx + dx, y, `⋯ ${n} line${n === 1 ? '' : 's'}`, {size: sz * .82, fill: FAINT, op: o, mono: true, weight: 400, box: key, layer})
        continue
      }
      // Focus steps up or down over STEP seconds after its stop, and never mid-scroll.
      const was = B ? lit(from, k) : lit(stop, k), is = lit(stop, k)
      const fu = was === is ? 1 : smooth((c.t - (stop.t - STEP)) / STEP)
      const tone = was === is ? (is ? 1 : 0) : is ? fu : 1 - fu
      const text = lines[k - 1] ?? ''
      c.S.text(`${key}:n`, gx + dx, y, String(k), {size: sz * .8, fill: mix(FAINT, DIM, tone), op: o, mono: true, weight: 400, anchor: 'end', box: `${name} line number ${k}`, layer})
      const node = c.S.el(key, 'text', {x: tx + dx, y, opacity: o, 'font-size': sz, 'font-family': 'var(--mono)', 'font-weight': 400,
        'dominant-baseline': 'middle', 'xml:space': 'preserve', style: 'white-space:pre', box: `${name} line ${k}`, 'data-kind': 'text'}, layer)
      const parts = syntax(text, lang).map(p => ({text: p.text.replace(/\t/g, '    '), fill: mix(mix(TONE[p.kind], FAINT, .72), TONE[p.kind], tone)}))
      const sig = JSON.stringify(parts)
      if (node && node._tourText !== sig) {
        node.replaceChildren(...parts.map(p => { const s = document.createElementNS(NS, 'tspan'); s.textContent = p.text; s.setAttribute('fill', p.fill); return s }))
        node._tourText = sig
      }
      if (tag === 'a') out.lines[k] = [tx + dx, y - lh / 2, text.length * adv, lh]
    }
    // The pointed token: underlined in HOT, drawn in over the 0.25 s before its cue, whole on it,
    // and gone when the view moves on.
    if (stop.point && tag === 'a') {
      const {line, text} = stop.point, src = lines[line - 1] ?? '', col = src.indexOf(text)
      const p = smooth((c.t - (stop.t - .25)) / .25)
      const row = A.at.get(line)
      if (col >= 0 && row !== undefined && p > 0) {
        const y = centreY + (row - A.centre) * lh + sz * .62, x0 = tx + dx + col * adv
        c.S.line(`${name}:point`, x0, y, x0 + text.length * adv, y, {p, stroke: HOT, sw: Math.max(3, sz * .1), op: op * pageOp, box: `${name} point`, layer})
      }
    }
  }

  if (slide < 1) {
    drawPage(prev, stops[i - 2] && stops[i - 2].file === prev.file ? stops[i - 2] : null, 1, -slide * bw * .35, 1 - smooth(slide / .6), 'b')
    drawPage(cur, null, 1, (1 - slide) * bw * .35, smooth((slide - .3) / .7), 'a')
  } else {
    drawPage(cur, moving < 1 || (c.t < cur.t && cur.file === prev.file) ? prev : null, moving, 0, 1, 'a')
  }
  if (header) {
    const hy = by + sz * 1.1
    const f = slide < 1 ? (slide < .5 ? prev.file : cur.file) : cur.file
    const ho = op * (slide < 1 ? Math.abs(slide - .5) * 2 : 1)
    c.S.text(`${name}:path`, tx, hy, f, {size: sz * .82, fill: DIM, op: ho, mono: true, weight: 500, box: `${name} path`, layer})
    if (commit && tourData.source.commit) {
      c.S.text(`${name}:commit`, bx + bw, hy, tourData.source.commit.slice(0, 7), {size: sz * .7, fill: FAINT, op, mono: true, weight: 400, anchor: 'end', box: `${name} commit`, layer})
    }
    c.S.line(`${name}:rule`, tx, by + sz * 2.05, bx + bw, by + sz * 2.05, {stroke: LINE, sw: 2, op, layer})
  }
  return out
}
