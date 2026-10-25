// Draw the same element functions here and in the scenes so style changes stay visible together.
// Copy this file to scenes/look.js; studio look-sheet draws its pages at time zero.
// The context has no sentence times because a look sheet belongs to the whole video.

export const pages = ['{{the protagonist}}']

// What each element is made of, so everything it does agrees: how it springs and settles when it
// lands, and what it sounds like (references/taste.md). Scenes pass these to the kit's
// motion helpers, kit.spring(t, ...m.spring) and kit.settle(t, t0, ...m.settle), and effects take
// the pool, instead of each scene choosing its own numbers.
export const materials = {
  token: { spring: [170, 26], settle: [6, 3, 5], sound: [] },   // {{material and weight; silent unless a permitted touch}}
}

/** {{The thing the video follows}}, in one state: a box with a glyph. Scenes import this. */
export function drawToken(c, key, x, y, state) {
  const { S, C } = c
  const [glyph, color] = { idle: ['○', C.dim], ok: ['✓', C.cold], bad: ['✕', C.bad], wait: ['…', C.hot] }[state]
  S.rect(key, x - 60, y - 60, 120, 120, { stroke: color, fill: C.bg2, sw: 3, r: 16, box: `token ${state}` })
  S.text(key + ':g', x, y, glyph, { size: 52, anchor: 'middle', fill: color, weight: 600 })
}

export default function look(c) {
  const { S, W, H, header } = c
  const y = header + (H - header) / 2
  ;['idle', 'ok', 'bad', 'wait'].forEach((state, i) => {
    const x = W * (0.2 + i * 0.2)
    drawToken(c, `own:${state}`, x, y, state)
    S.text(`own:${state}:t`, x, y + 100, state, { size: 22, anchor: 'middle', fill: c.C.dim, mono: true })
  })
}
