// A live chapter with a 3D moment: a flat diagram opens into depth on one cue and flattens back on
// another (copy to scenes/<clip>.js and name the cues in cues.json). Use 3D only when the viewer needs
// to see something the flat diagram hides (references/taste/look.md); everything else stays 2D.
//
// The bridge is c.flatShot(): the top-down shot under which a world point (x, 0, z) lands on stage
// pixel (x, z). So the SVG diagram and the 3D model are built in the same numbers, the model seen from
// above matches the diagram, and the hand-over on the cue doesn't show. Labels stay SVG text, placed
// at points on the model projected through the camera (c.G.project), so they ride with it and the
// checks read them. A 3D element named with `box` is reported to the checks too: its screen bounds,
// its colour and meaning, and how much of it shows (`studio check` warns when a narrated one is hidden).

export default function draw(c) {
  const { S, G, t, W, kit, view } = c
  const { C, keyed } = kit
  const open = c.cue('{{opens into depth}}'), close = c.cue('{{flattens again}}')
  const cy = view[1] + view[3] / 2                       // the middle of the stage below the header
  const flat = c.flatShot()
  const tilted = { target: [W / 2, -90, cy], az: -22, el: 32, span: 330, fov: 30 }
  c.shot([[open, flat], [open + 1.2, tilted, 'heavy'], [close, tilted], [close + 1.1, flat, 'heavy']])

  // The model at t: three layers 600 x 300 px, which come apart after the tilt and close before the return.
  const layers = ['{{top layer}}', '{{middle layer}}', '{{bottom layer}}']
  const gap = keyed(t, [[open + 1.7, 0], [open + 2.5, 90, 'heavy'], [close - 0.9, 90], [close - 0.1, 0, 'heavy']])
  const [x0, z0, w, d] = [W / 2 - 300, cy - 150, 600, 300]
  if (t >= open && t < close + 1.1) {
    layers.forEach((name, i) => G.mesh(`layer${i}`, 'box', { size: [w, 12, d] }, {
      at: [W / 2, -6 - i * gap, cy], color: i ? C.tray : C.bg3, edges: { width: i ? 2 : 3, color: C.edge }, box: `layer ${name}`,
    }))
  } else {
    S.rect('layer0', x0, z0, w, d, { fill: C.bg3, stroke: C.edge, sw: 3, r: 0, box: `layer ${layers[0]}` })
  }
  layers.forEach((name, i) => {
    const op = i === 0 ? 1 : kit.clamp(gap / 90)
    if (op <= 0.01) return
    const [ax, ay] = G.project([x0 + w, -i * gap, cy])
    S.callout(`label${i}`, ax + 70, ay + 6, ax, ay, name, op, { size: 28 })
  })
}
