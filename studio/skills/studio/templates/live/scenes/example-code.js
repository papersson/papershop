// After the main session runs `studio typing VIDEO PLAN.json`, rename this chapter to s1.js.
// Keep the actual source versions and captured command output beside the typing plan.
const typing = await (await fetch(new URL('../data/typing.json', import.meta.url))).json()
// Optional: the teaching view's open intervals, folds, highlights, helpers and full-program payoff.
const view = await (await fetch(new URL('../data/codeview.json', import.meta.url))).json()

export default function draw(c) {
  const {kit} = c, ids = ['add'] // the burst ids from the plan
  // Code components use eight-unit, centre-origin coordinates (y up), like the boards.
  kit.Editor(c, {typing, ids, at: [-3.3, .5], w: 9, rows: 7, title: 'sum.js', view})
  kit.RunTerminal(c, {typing, ids, at: [-3.3, -2.7], w: 9, rows: 3})
  kit.ProgramWindow(c, {typing, ids, at: [4.4, .7], w: 5.8, h: 3.6,
    draw(id, pop, d) {
      const {x, y, w, h} = d.window // this callback draws in pixels; clipped and scaled with the window
      c.S.rect('application', x, y, w, h, {fill: kit.C.bg2, stroke: kit.C.edge})
      // Draw the actual program result for this run here, from captured output or its data.
    },
  })
  // kit.HelperCard(c, {view, id: 'prices', at: [4.4, -2], w: 5.8})
  // For recorded source or output without typing:
  // kit.CodePanel(c, {at: [0, 0], w: 10, source: {text, sha256}, current: 5, range: [1, 9]})
  // kit.Terminal(c, {at: [0, -2], w: 10, runs: [{argv, stdout, stderr, exit}], progress: 1})
}
