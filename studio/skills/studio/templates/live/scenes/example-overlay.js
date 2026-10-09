// An overlay drawn over every chapter: rename to scenes/overlay.js to use it. Good for what carries
// across the whole video (a ladder of stages, a running clock, a title card as each chapter begins).

export default function overlay(c) {
  const { S, t, kit } = c
  const card = kit.prog(t, -0.6, 0.5, kit.ease.out) * (1 - kit.prog(t, 2.6, 0.6))
  S.text('card', c.W / 2, 70, c.title, { size: 40, weight: 700, anchor: 'middle', op: card, layer: 'over' })
  S.line('card:rule', c.W / 2 - 120 * card, 102, c.W / 2 + 120 * card, 102, { stroke: kit.C.hot, sw: 3, op: card, layer: 'over' })
}
