// A chapter on the screens layer (references/screens.md): desktops, editors, terminals and browsers
// replayed from the film's one log, data/screens.json. Rename this chapter to s1.js; after changing the
// log or the timeline, the main session runs `studio screens VIDEO` for the key and click sounds.
import { loadScreens, screensAt, screensCamera, drawScreens } from '@studio/screens-draw.js'
import { defCard } from '@studio/pages.js'

const scr = await loadScreens(import.meta.url) // data/screens.json, with the files and runs it names

// A browser page draws inside its box in world pixels and says where its click targets are.
function basket(c, box, tab, ctx) {
  const L = ctx.look
  c.S.text('shop:title', box.x + 36, box.y + 48, tab.page === 'placed' ? 'Order placed' : 'Basket', { size: 30, fill: L.paperInk })
  const button = [box.x + 36, box.y + 120, box.w - 72, 64]
  c.S.rect('shop:checkout', ...button, { fill: '#2f7a69', r: 8, box: 'checkout button' })
  return { targets: { checkout: button } }
}

export default function draw(c) {
  const s = screensAt(c, scr) // every window's state at this frame
  // Camera keys in clip seconds: the whole desktop, a window up close, then every desktop at once.
  // Around each switch the camera goes out, across and in by itself.
  screensCamera(c, scr, s, [[0, 'whole'], [4, { window: 'laptop', pad: 20 }], [12, 'all']])
  drawScreens(c, scr, s, { pages: { basket, placed: basket } })
  // When a core term first matters: the definition card, in one of CARD_VARIANTS.
  // defCard(c, 'log', { term: 'Log', def: 'A record a program writes as it runs.', t0: 6.1, t1: 9.4 })
}
