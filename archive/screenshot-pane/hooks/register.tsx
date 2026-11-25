import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Shot } from '../types'

const PANE = 'screenshots'
const IMAGE_EXT = /\.(png|jpe?g|webp|gif)$/i
const PNG_EXT = /\.png$/i
const ABSOLUTE_IMAGE = /(\/[^\s"'`]+\.(?:png|jpe?g))/g
const NO_IMAGES = "can't draw images here (needs Ghostty, kitty or WezTerm, outside tmux) · o opens it"
// agent-browser flags that take a value, so the parser skips it
const FLAGS_WITH_VALUE = new Set([
  '--session',
  '--screenshot-dir',
  '--screenshot-quality',
  '--screenshot-format',
])
const NAVIGATE = new Set(['open', 'goto', 'navigate'])

const shotsRef = { plugin: 'screenshot-pane', key: 'shots' } as const
const indexRef = { plugin: 'screenshot-pane', key: 'index' } as const
const dismissedRef = { plugin: 'screenshot-pane', key: 'dismissed' } as const
const compareRef = { plugin: 'screenshot-pane', key: 'compare' } as const
const shots = atom(shotsRef, [] as Shot[])
const index = atom(indexRef, -1)
const dismissed = atom(dismissedRef, false)
const compare = atom(compareRef, false)

export type Found = { path: string; source: Shot['source'] }
export type Parsed = { shots: Found[]; page?: string }

/** Splits one shell segment into words, honouring simple quotes. */
function words(segment: string): string[] {
  const out: string[] = []
  const re = /"([^"]*)"|'([^']*)'|(\S+)/g
  let m: RegExpExecArray | null
  while ((m = re.exec(segment)) !== null) out.push(m[1] ?? m[2] ?? m[3] ?? '')
  return out
}

function normalize(path: string): string {
  const parts: string[] = []
  for (const p of path.split('/')) {
    if (p === '' || p === '.') continue
    if (p === '..') parts.pop()
    else parts.push(p)
  }
  return '/' + parts.join('/')
}

function resolvePath(dir: string, home: string, p: string): string {
  if (p.startsWith('/')) return normalize(p)
  if (p === '~' || p.startsWith('~/')) return normalize(home + p.slice(1))
  return normalize(dir + '/' + p)
}

/** The positional words after an agent-browser subcommand, flags and their values skipped. */
function agentBrowserArgs(t: string[]): { sub: string; args: string[] } | null {
  const ab = t.indexOf('agent-browser')
  if (ab < 0) return null
  let i = ab + 1
  while (i < t.length && (t[i] ?? '').startsWith('-')) i += FLAGS_WITH_VALUE.has(t[i] ?? '') ? 2 : 1
  const sub = t[i]
  if (sub === undefined) return null
  const args: string[] = []
  for (let j = i + 1; j < t.length; j += 1) {
    const tok = t[j] ?? ''
    if (tok.startsWith('-')) {
      if (FLAGS_WITH_VALUE.has(tok)) j += 1
      continue
    }
    args.push(tok)
  }
  return { sub, args }
}

/**
 * What a Bash command does that this mod cares about: the image files it writes
 * (`agent-browser screenshot [sel] [path]`, `screencapture ... path`), resolved
 * against the cwd its own `cd`s lead to, and the last page it opens in the
 * browser. A path holding `$` cannot be resolved here and is skipped.
 */
export function parseCommand(command: string, cwd: string, home: string): Parsed {
  const found: Found[] = []
  let page: string | undefined
  let dir = cwd
  for (const raw of command.split(/&&|\|\||;|\n|\|/)) {
    const t = words(raw.trim())
    if (t.length === 0) continue
    if (t[0] === 'cd' && t[1] !== undefined && !t[1].includes('$')) {
      dir = resolvePath(dir, home, t[1])
      continue
    }
    const ab = agentBrowserArgs(t)
    if (ab !== null) {
      if (NAVIGATE.has(ab.sub) && ab.args[0] !== undefined) page = ab.args[0]
      if (ab.sub !== 'screenshot') continue
      const last = ab.args[ab.args.length - 1]
      if (last !== undefined && (IMAGE_EXT.test(last) || last.includes('/'))) {
        found.push({ path: resolvePath(dir, home, last), source: 'agent-browser' })
      }
      continue
    }
    if (t[0] === 'screencapture') {
      const last = t[t.length - 1]
      if (last !== undefined && IMAGE_EXT.test(last)) {
        found.push({ path: resolvePath(dir, home, last), source: 'screencapture' })
      }
    }
  }
  return { shots: found.filter(f => !f.path.includes('$')), page }
}

/** A page address short enough for a header: host and path for the web, the file name for file://. */
export function pageLabel(url: string): string {
  const file = url.match(/^file:\/\/(.*)$/)
  if (file) return (file[1] ?? '').split('/').pop() ?? url
  const web = url.match(/^https?:\/\/([^?#]*)/)
  const label = web ? (web[1] ?? url).replace(/\/$/, '') : url
  return label.length <= 40 ? label : label.slice(0, 39) + '…'
}

const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'

function decodeBase64(chars: string): number[] {
  const out: number[] = []
  let bits = 0
  let have = 0
  for (const c of chars) {
    const v = B64.indexOf(c)
    if (v < 0) break
    bits = (bits << 6) | v
    have += 6
    if (have >= 8) {
      have -= 8
      out.push((bits >> have) & 0xff)
    }
  }
  return out
}

/** Width and height from a PNG's IHDR chunk, read off the file's base64. */
export function pngSize(base64: string): { width: number; height: number } | null {
  if (!base64.startsWith('iVBOR')) return null
  // base64 chars 20..31 hold bytes 15..23; width is bytes 16..19, height 20..23
  const b = decodeBase64(base64.slice(20, 32))
  if (b.length < 9) return null
  const at = (i: number): number => b[i] ?? 0
  const width = ((at(1) << 24) | (at(2) << 16) | (at(3) << 8) | at(4)) >>> 0
  const height = ((at(5) << 24) | (at(6) << 16) | (at(7) << 8) | at(8)) >>> 0
  return width > 0 && height > 0 ? { width, height } : null
}

/**
 * Cells for a picture of w×h pixels across `columns` cells, a cell `ratio`
 * times as tall as wide. A tall picture keeps its width and the pane scrolls;
 * only the 255-row limit of one Image narrows it.
 */
export function fitWidth(w: number, h: number, columns: number, ratio: number) {
  let cols = Math.max(1, Math.min(255, Math.floor(columns)))
  let rows = Math.max(1, Math.round((cols * h) / w / ratio))
  if (rows > 255) {
    rows = 255
    cols = Math.max(1, Math.round((rows * ratio * w) / h))
  }
  return { columns: cols, rows }
}

/** The shot shown "before" this one: the latest earlier shot of the same page, else of the same file. */
export function previousOf(list: readonly Shot[], i: number): number {
  const cur = list[i]
  if (cur === undefined) return -1
  for (let j = i - 1; j >= 0; j -= 1) {
    const s = list[j]
    if (s === undefined) continue
    if (cur.page !== undefined ? s.page === cur.page : s.origin === cur.origin) return j
  }
  return -1
}

export function ago(ms: number): string {
  const s = Math.max(0, Math.round(ms / 1000))
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  return `${Math.floor(s / 3600)}h ago`
}

function shortPath(path: string, home: string): string {
  const p = home && path.startsWith(home) ? '~' + path.slice(home.length) : path
  return p.length <= 40 ? p : '…/' + p.split('/').slice(-2).join('/')
}

async function home($: EngineInterface): Promise<string> {
  return (await $.env.get('HOME')) ?? ''
}

async function cacheDir($: EngineInterface): Promise<string> {
  return `${await home($)}/.cache/screenshot-pane/${await $.session.id()}`
}

async function openFile($: EngineInterface, path: string): Promise<void> {
  const mac = await $.process.run(['open', path]).catch(() => ({ exitCode: 1 }))
  if (mac.exitCode !== 0) await $.process.run(['xdg-open', path]).catch(() => undefined)
}

type Options = { autoOpen: boolean; history: number; cellRatio: number }

/**
 * Records an image file the session just produced or looked at: copies it
 * into this session's cache so a later write to the same path can't change
 * it, then shows the pane, or toasts when the person closed it.
 */
async function addShot(
  $: EngineInterface,
  opts: Options,
  origin: string,
  source: Shot['source'],
  page: string | undefined,
  agent: string | undefined,
): Promise<void> {
  let stat
  try {
    stat = await $.fs.stat(origin)
  } catch {
    return
  }
  if (stat.kind !== 'file') return
  const generation = Math.floor(stat.mtimeMs)
  const { value: known = [] } = await $.state.get(shotsRef)
  if (known.some(s => s.origin === origin && s.at >= generation)) return

  const isPng = PNG_EXT.test(origin)
  let size: { width: number; height: number } | null = null
  if (isPng) {
    try {
      size = pngSize((await $.fs.read(origin, { as: 'bytes' })).base64)
    } catch {
      size = null
    }
  }
  const n = (known[known.length - 1]?.n ?? 0) + 1
  const dir = await cacheDir($)
  const copy = `${dir}/${n}-${origin.split('/').pop() ?? 'shot.png'}`
  const copied = await $.process
    .run(['mkdir', '-p', dir])
    .then(() => $.process.run(['cp', origin, copy]))
    .catch(() => ({ exitCode: 1 }))

  const shot: Shot = {
    n,
    path: copied.exitCode === 0 ? copy : origin,
    origin,
    at: Math.max(generation, await $.clock.now()),
    width: size?.width ?? 1600,
    height: size?.height ?? 1000,
    isPng,
    source,
    ...(page !== undefined ? { page } : {}),
    ...(agent !== undefined ? { agent } : {}),
  }
  await update($, shots, list => [...list, shot].slice(-Math.max(1, opts.history)))
  await update($, compare, () => false)

  const { value: isDismissed = false } = await $.state.get(dismissedRef)
  const pane = (await $.ui.panes()).find(p => p.id === PANE)
  if (pane === undefined && opts.autoOpen && !isDismissed) {
    void $.ui.open({ id: PANE, title: 'Screenshots' })
  } else if (pane?.isShown !== true) {
    $.ui.toast(`screenshot ${n}${page ? ` of ${pageLabel(page)}` : ''} · /screenshots to view`)
  }
}

export const register: Register = (on, options) => {
  const opts: Options = {
    autoOpen: options.autoOpen !== false,
    history: typeof options.history === 'number' ? options.history : 50,
    cellRatio: typeof options.cellRatio === 'number' && options.cellRatio > 0 ? options.cellRatio : 2.4,
  }
  // The page each agent's browser was last sent to; a reload forgets it.
  const pages = new Map<string, string>()

  on('session.start', async ($, e, next) => {
    await $.command.register({
      name: 'screenshots',
      description: 'Show the screenshots Claude took (`clear` empties the list)',
    })
    // Sessions older than a week leave their cached copies behind; sweep them.
    void $.process
      .run(['find', `${await home($)}/.cache/screenshot-pane`, '-mindepth', '1', '-maxdepth', '1', '-mtime', '+7', '-exec', 'rm', '-rf', '{}', '+'])
      .catch(() => undefined)
    return next(e)
  })

  on('command.run', { command: 'screenshots' }, async ($, e) => {
    if (e.args.trim() === 'clear') {
      await update($, shots, () => [])
      await update($, index, () => -1)
      await update($, compare, () => false)
      return { text: 'Screenshot list cleared.' }
    }
    await update($, dismissed, () => false)
    await $.ui.open({ id: PANE, title: 'Screenshots', focus: true })
    const { value: list = [] } = await $.state.get(shotsRef)
    return { text: `Screenshots pane opened (${list.length} so far).` }
  })

  on('ui.close', async ($, e, next) => {
    if (e.id === PANE && e.origin.kind === 'person') await update($, dismissed, () => true)
    return next(e)
  })

  on('tool.call', { tool: 'Bash' }, async ($, e, next) => {
    if (!/agent-browser|\bscreencapture\b/.test(e.command)) return next(e)
    const agent = e.agentId ?? ''
    const parsed = parseCommand(e.command, await $.session.cwd(), await home($))
    const ran = await next(e)
    if (ran.deny !== undefined || ran.isError === true) return ran
    if (parsed.page !== undefined) pages.set(agent, parsed.page)
    const paths = parsed.shots.map(s => s.path)
    if (paths.length === 0 && /\bscreenshot\b/.test(e.command) && ran.text !== undefined) {
      // `agent-browser screenshot` with no path prints where it saved the file
      for (const m of ran.text.matchAll(ABSOLUTE_IMAGE)) if (m[1] !== undefined) paths.push(m[1])
    }
    const source = parsed.shots[0]?.source ?? 'agent-browser'
    const page = source === 'agent-browser' ? pages.get(agent) : undefined
    for (const p of paths) await addShot($, opts, p, source, page, e.agentId)
    return ran
  }).catch(($, e, next) => next(e))

  on('tool.call', { tool: 'Read' }, async ($, e, next) => {
    if (!IMAGE_EXT.test(e.file_path)) return next(e)
    const ran = await next(e)
    if (ran.deny === undefined && ran.isError !== true) {
      const path = resolvePath(await $.session.cwd(), await home($), e.file_path)
      await addShot($, opts, path, 'read', undefined, e.agentId)
    }
    return ran
  }).catch(($, e, next) => next(e))

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const { Box, Text, Button } = $.ui.resolve(e)
    const list = await read($, shots)
    const pick = await read($, index)
    const isComparing = await read($, compare)
    const cur = pick < 0 ? list.length - 1 : Math.min(pick, list.length - 1)
    const before = isComparing ? previousOf(list, cur) : -1
    const shown = before >= 0 ? before : cur
    const shot = list[shown]

    if (shot === undefined) {
      return (
        <Box flexDirection="column">
          <Text dimColor>No screenshots yet.</Text>
          <Text dimColor>Screenshots Claude takes with agent-browser or screencapture, and images it reads, show up here.</Text>
        </Box>
      )
    }

    const now = await $.clock.now()
    const where = shot.page !== undefined ? pageLabel(shot.page) : shortPath(shot.origin, await home($))
    const who = shot.agent !== undefined ? ` · subagent ${shot.agent.slice(0, 6)}` : ''
    const hasBefore = previousOf(list, cur) >= 0
    const { columns, rows } = fitWidth(shot.width, shot.height, e.props.bodyColumns - 1, opts.cellRatio)

    // Handlers read the live values, never the ones captured while drawing.
    const position = async (): Promise<{ i: number; n: number }> => {
      const { value: all = [] } = await $.state.get(shotsRef)
      const { value: i = -1 } = await $.state.get(indexRef)
      return { i: i < 0 ? all.length - 1 : Math.min(i, all.length - 1), n: all.length }
    }
    // The shot on screen now: the "before" one while comparing.
    const onScreen = async (): Promise<Shot | undefined> => {
      const { value: all = [] } = await $.state.get(shotsRef)
      const { value: isBefore = false } = await $.state.get(compareRef)
      const { i } = await position()
      const j = isBefore ? previousOf(all, i) : -1
      return all[j >= 0 ? j : i]
    }

    const picture =
      e.surface === 'terminal' && shot.isPng ? (
        (() => {
          const { Image } = $.ui.resolve(e)
          return (
            <Image
              key="shot"
              source={{ file: shot.path, format: 'png', generation: shot.n }}
              columns={columns}
              rows={rows}
              alt={NO_IMAGES}
            />
          )
        })()
      ) : (
        <Text dimColor>{shot.isPng ? NO_IMAGES : `${shot.origin} · only PNG is drawn here · o opens it`}</Text>
      )

    return (
      <Box flexDirection="column">
        <Box>
          <Text bold>{`${cur + 1}/${list.length}`}</Text>
          {before >= 0 && <Text color="yellow">{` before (#${shot.n})`}</Text>}
          <Text>{`  ${where}`}</Text>
          <Text dimColor>{`  ${ago(now - shot.at)}${who}`}</Text>
        </Box>
        <Box>
          <Button
            plain
            dimColor
            key="prev"
            label="prev"
            hotkey="h"
            onPress={async () => {
              const { i } = await position()
              await update($, compare, () => false)
              await update($, index, () => Math.max(0, i - 1))
            }}
          />
          <Text dimColor>{'  '}</Text>
          <Button
            plain
            dimColor
            key="next"
            label="next"
            hotkey="l"
            onPress={async () => {
              const { i, n } = await position()
              await update($, compare, () => false)
              await update($, index, () => (i + 1 >= n - 1 ? -1 : i + 1))
            }}
          />
          <Text dimColor>{'  '}</Text>
          {hasBefore && (
            <Button
              plain
              dimColor
              key="before"
              label={isComparing ? 'after' : 'before'}
              hotkey="b"
              onPress={() => update($, compare, c => !c)}
            />
          )}
          {hasBefore && <Text dimColor>{'  '}</Text>}
          <Button
            plain
            dimColor
            key="comment"
            label="comment"
            hotkey="c"
            onPress={async () => {
              const s = await onScreen()
              if (s === undefined) return
              const label = s.page !== undefined ? ` of ${pageLabel(s.page)}` : ''
              const filled = await $.prompt.fill({ text: `[screenshot #${s.n}${label}: ${s.path}] `, mode: 'insert' })
              $.ui.toast(filled.isFilled ? 'Reference added to your prompt · Esc to type' : 'Could not reach the prompt box')
            }}
          />
          <Text dimColor>{'  '}</Text>
          <Button
            plain
            dimColor
            key="open"
            label="open"
            hotkey="o"
            onPress={async () => {
              const s = await onScreen()
              if (s !== undefined) await openFile($, s.path)
            }}
          />
        </Box>
        {picture}
      </Box>
    )
  })
}
