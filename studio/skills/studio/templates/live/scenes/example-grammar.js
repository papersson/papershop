// Film grammar (references/kit.md, "Film grammar"): a wide shot, focus on what the voice names, a
// close shot on one part with labels that keep their size, and back out. Rename this chapter to s1.js;
// its narration, as sentences 01-03:
//   01 "Every order goes from checkout, to payment, to the bank."
//   02 "When the bank is slow, payment waits."
//   03 "The setting that decides how long sits inside payment. Step back, and checkout waits too."
// The next chapter opens inside payment; it says so with `export const join = { match: 'payment' }`.
const PARTS = [['checkout', 260], ['payment', 810], ['bank', 1360]]

export default function draw(c) {
  const { S, H } = c
  const y = H / 2 - 90
  for (const [name, x] of PARTS) {
    S.rect(name, x, y, 300, 180, { fill: 'var(--bg2)', stroke: 'var(--edge)', sw: 3, r: 18, box: name })
    S.text(`name-${name}`, x + 150, y - 40, name, { size: 40, anchor: 'middle', weight: 600, keep: true })
  }
  S.text('payment-timeout', 960, y + 90, 'timeout = 1 s', { size: 20, anchor: 'middle', mono: true, fill: 'var(--warm)' })

  c.focus('bank', c.phrase('02', 'the bank'))
  c.focus('payment', c.phrase('02', 'payment waits'))
  c.shots([[0, 'wide'], [c.at('03'), ['close', 'payment']], [c.phrase('03', 'Step back'), 'back']])
}
