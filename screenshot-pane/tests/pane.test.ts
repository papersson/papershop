import { expect, mock, test } from 'claude-code/testing'
import type { On } from 'claude-code'

import type { Shot } from '../types'
import { ago, fitWidth, pageLabel, parseCommand, pngSize, previousOf } from '../hooks/register'

// A PNG header whose IHDR says 640×400.
const PNG_640x400 = 'iVBORw0KGgoAAAANSUhEUgAAAoAAAAGQCAYAAAAAAAAA'
const SURFACES = ['terminal', 'desktop'] as const

const PANE = {
  plugin: 'screenshot-pane',
  component: 'Pane',
  requestId: 'screenshots',
  props: {
    title: 'Screenshots',
    isFocused: false,
    bodyColumns: 80,
    placement: 'dock',
    scroll: { offset: 0, bodyRows: 40 },
    view: {},
  },
} as const

/**
 * Stands in for the host: a PNG at every path whose mtime the test moves,
 * a Bash and a Read that succeed, and a log of what the mod ran and filled.
 */
function host(on: On) {
  const ran: string[][] = []
  const filled: string[] = []
  const toasts: string[] = []
  const clock = { mtime: 1000 }
  const panes: { id: string; title: string; isShown: boolean; isFocused: boolean; isPlaced: boolean }[] = []
  mock.env(on, { HOME: '/Users/p' })
  mock.clock(on)
  on('session.cwd', () => ({ value: '/w' }))
  on('session.id', () => ({ value: 'sess' }))
  on('fs.stat', () => ({ value: { kind: 'file', size: 10, mtimeMs: clock.mtime, isLink: false } }))
  on('fs.read', () => ({ value: { base64: PNG_640x400 } }))
  on('process.run', (_$, e) => {
    ran.push([...e.argv])
    return { value: { exitCode: 0, stdout: '', stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  on('ui.panes', () => ({ value: panes }))
  on('ui.open', (_$, e) => {
    if (!panes.some(p => p.id === e.id)) panes.push({ id: e.id, title: e.title ?? e.id, isShown: true, isFocused: false, isPlaced: true })
    return { value: { isPlaced: true } }
  })
  on('ui.toast', (_$, e) => {
    toasts.push(e.text)
    return { value: undefined }
  })
  on('prompt.fill', (_$, e) => {
    filled.push(e.text)
    return { isFilled: true }
  })
  on('tool.call', { tool: 'Bash' }, () => ({
    result: { stdout: '', stderr: '', interrupted: false },
    text: '',
  }))
  on('tool.call', { tool: 'Read' }, () => ({
    result: { type: 'image', file: { base64: PNG_640x400, type: 'image/png', originalSize: 10 } },
    text: '',
  }))
  return { ran, filled, toasts, clock, panes }
}

test('parses screenshot paths and the page the browser opened', () => {
  expect(parseCommand('agent-browser screenshot /tmp/a.png', '/w', '/Users/p').shots).toEqual([
    { path: '/tmp/a.png', source: 'agent-browser' },
  ])
  expect(parseCommand('cd sub && agent-browser screenshot --full shot.png', '/w', '/Users/p').shots).toEqual([
    { path: '/w/sub/shot.png', source: 'agent-browser' },
  ])
  expect(parseCommand('agent-browser --session s screenshot "#main" ~/x.png', '/w', '/Users/p').shots).toEqual([
    { path: '/Users/p/x.png', source: 'agent-browser' },
  ])
  expect(parseCommand('screencapture -x /tmp/s.png', '/w', '/Users/p').shots).toEqual([
    { path: '/tmp/s.png', source: 'screencapture' },
  ])
  expect(parseCommand('agent-browser screenshot --annotate', '/w', '/Users/p').shots).toEqual([])
  expect(parseCommand('agent-browser screenshot $SP/a.png', '/w', '/Users/p').shots).toEqual([])
  expect(parseCommand('agent-browser open https://example.com/a && agent-browser screenshot /tmp/b.png', '/w', '/h')).toEqual({
    shots: [{ path: '/tmp/b.png', source: 'agent-browser' }],
    page: 'https://example.com/a',
  })
  expect(parseCommand('ls -la', '/w', '/Users/p')).toEqual({ shots: [], page: undefined })
})

test('labels, sizes and times read well', () => {
  expect(pageLabel('file:///tmp/deck/index.html')).toBe('index.html')
  expect(pageLabel('https://example.com/docs/')).toBe('example.com/docs')
  expect(pngSize(PNG_640x400)).toEqual({ width: 640, height: 400 })
  expect(pngSize('not a png')).toBe(null)
  // 100 columns of a 640×400 picture, a cell 2.5 times as tall as wide: 25 rows
  expect(fitWidth(640, 400, 100, 2.5)).toEqual({ columns: 100, rows: 25 })
  // a very tall capture keeps to the 255-row limit and narrows
  expect(fitWidth(1000, 20000, 100, 2.5)).toEqual({ columns: 32, rows: 255 })
  expect(ago(5_000)).toBe('just now')
  expect(ago(125_000)).toBe('2m ago')
})

test('the "before" shot is the previous one of the same page, else of the same file', () => {
  const shot = (n: number, origin: string, page?: string): Shot => ({
    n, path: `/c/${n}`, origin, at: n, width: 1, height: 1, isPng: true, source: 'agent-browser',
    ...(page !== undefined ? { page } : {}),
  })
  const list = [shot(1, '/a.png', 'p1'), shot(2, '/b.png', 'p2'), shot(3, '/c.png', 'p1'), shot(4, '/x.png'), shot(5, '/x.png')]
  expect(previousOf(list, 2)).toBe(0)
  expect(previousOf(list, 1)).toBe(-1)
  expect(previousOf(list, 4)).toBe(3)
})

test('an empty pane says so on every surface', async $ => {
  for (const surface of SURFACES) {
    const ui = await $.ui.mount({ ...PANE, surface })
    expect(await ui.find({ type: 'Text', text: /No screenshots yet/ })).toBeDefined()
  }
})

test('a screenshot is copied into the cache and shown with its page', async ($, on) => {
  const h = host(on)
  await $.tool.call({ tool: 'Bash', command: 'agent-browser open file:///w/deck.html' })
  await $.tool.call({ tool: 'Bash', command: 'agent-browser screenshot /tmp/shot.png' })
  // the same file again, unchanged, is not listed twice
  await $.tool.call({ tool: 'Bash', command: 'agent-browser screenshot /tmp/shot.png' })

  expect(h.ran).toContainEqual(['cp', '/tmp/shot.png', '/Users/p/.cache/screenshot-pane/sess/1-shot.png'])
  expect(h.panes).toHaveLength(1)

  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: '1/1' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /deck\.html/ })).toBeDefined()
  expect(await ui.find({ type: 'Image' })).toBeDefined()

  const desktop = await $.ui.mount({ ...PANE, surface: 'desktop' })
  expect(await desktop.find({ type: 'Image' })).toBeUndefined()
  expect(await desktop.find({ type: 'Text', text: /o opens it/ })).toBeDefined()
})

test('b flips to the previous version of the same page and back', async ($, on) => {
  const h = host(on)
  await $.tool.call({ tool: 'Bash', command: 'agent-browser open https://example.com && agent-browser screenshot /tmp/s.png' })
  h.clock.mtime = 9_000_000_000_000
  await $.tool.call({ tool: 'Bash', command: 'agent-browser screenshot /tmp/s.png' })

  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: '2/2' })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: / before/ })).toBeUndefined()
  await ui.press({ key: 'before' })
  expect(await ui.find({ type: 'Text', text: ' before (#1)' })).toBeDefined()
  await ui.press({ key: 'before' })
  expect(await ui.find({ type: 'Text', text: / before/ })).toBeUndefined()
})

test('c puts a reference to the shot on screen into the prompt', async ($, on) => {
  const h = host(on)
  await $.tool.call({ tool: 'Read', file_path: '/tmp/r.png' })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  await ui.press({ key: 'comment' })
  expect(h.filled).toEqual(['[screenshot #1: /Users/p/.cache/screenshot-pane/sess/1-r.png] '])
})

test('with autoOpen off, new shots toast instead of opening the pane', { options: { autoOpen: false } }, async ($, on) => {
  const h = host(on)
  await $.tool.call({ tool: 'Bash', command: 'agent-browser screenshot /tmp/a.png' })
  expect(h.panes).toHaveLength(0)
  expect(h.toasts).toEqual(['screenshot 1 · /screenshots to view'])
})
