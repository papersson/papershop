// The look sheet's own page: rename to scenes/look.js and `studio look-sheet VIDEO` draws it after
// the kit's pages (colour and type, elements and states, close-up), into out/look/. Draw this
// video's own elements here, each in every state a scene will show it in, with the same helpers the
// scenes use, before the scenes are built: the motion review checks that drawings stay on this sheet.
// One function per element, imported by the scenes too, keeps the sheet and the scenes the same.
//
// `pages` names the pages (c.page is the index of the one being drawn). The context is a scene's at
// t = 0: S, W, H, unit, header, view, kit, C, frameOn and camAt; there are no sentence times.

export const pages = ['{{the protagonist}}']

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
