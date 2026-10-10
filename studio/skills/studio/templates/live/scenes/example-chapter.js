// A live chapter: copy this to scenes/<clip>.js (s1.js for chapter s1) and it replaces the
// chapter's board in every cut and on the desk. Everything derives from c.t, so any frame draws
// alone; sentence times come from the timeline. Coordinates are pixels on the stage above the
// caption band (c.W × c.H); c.unit is c.H / 8, the other engines' stage unit.
//
// Cue on what the voice says: c.phrase('02', 'the whole state') is when those words are spoken,
// and survives edits elsewhere in the sentence. c.at('02') / c.end('02') are a sentence's ends.
// The motion helpers are the glossary's words: c.P(t0, d, ease) for a movement, c.kit.stagger,
// c.kit.pulse, c.kit.countUp, c.kit.ease.back (overshoot), c.S.path(..., {p}) (draw-on) and so on.

export default function draw(c) {
  const { S, t, W, H, P, kit } = c
  const { C, ease, stagger } = kit
  // A title that reveals, then three boxes that stagger in as the first sentence lands.
  S.text('title', W / 2, H * 0.22, '{{the question this chapter answers}}', {
    size: 52, weight: 700, anchor: 'middle', op: P(c.at('01'), 0.6),
  })
  ;['{{one}}', '{{two}}', '{{three}}'].forEach((label, i) => {
    const p = P(stagger(c.phrase('01', '{{a phrase in sentence 1}}'), i, 0.2), 0.5, ease.back)
    const x = W / 2 + (i - 1) * 360
    S.rect(`box${i}`, x - 140, H * 0.45 + 30 * (1 - p), 280, 140, { fill: C.bg2, stroke: C.edge, op: p, box: `box ${label}` })
    S.text(`box${i}:t`, x, H * 0.45 + 70, label, { size: 30, anchor: 'middle', op: p })
  })
}
