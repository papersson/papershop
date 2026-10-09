// The motion glossary's demos: one short loop per term in glossary.json, drawn with the same stage
// and helpers scenes use, so a term means exactly what a scene can do. glossary.html shows them all
// (or ?term=<term> alone); the desk links to it next to the note box.

import { clamp, ease, lerp, prog, pulse, stagger, countUp, keyed, follow, settle, wobble, camAt, frameOn } from './kit.js'

export const LOOP = 3.6 // seconds per demo loop
export const W = 480, H = 270
const hot = 'var(--hot)', cold = 'var(--cold)', dim = 'var(--dim)', log = 'var(--log)', bad = 'var(--bad)', good = 'var(--good)'

/** Two dots crossing the card, one linear and one with curve e: the difference is the term. */
function versus(S, t, e, name) {
  const p = prog(t, 0.4, 1.6, e), q = prog(t, 0.4, 1.6, ease.linear)
  S.text('l1', 24, 70, 'linear', { size: 18, fill: dim, mono: true })
  S.circle('a', lerp(130, 440, q), 70, 14, { fill: dim })
  S.text('l2', 24, 140, name, { size: 18, fill: hot, mono: true })
  S.circle('b', lerp(130, 440, p), 140, 14, { fill: hot })
  const pts = [...Array(31).keys()].map(i => `${i ? 'L' : 'M'} ${130 + i * 10} ${245 - e(i / 30) * 60}`).join(' ')
  S.path('curve', pts, { stroke: 'var(--line)', sw: 2 })
  S.circle('cd', 130 + clamp((t - 0.4) / 1.6) * 300, 245 - p * 60, 5, { fill: hot })
}

export const DEMOS = {
  'ease out': (S, t) => versus(S, t, ease.out, 'ease out'),
  'ease in': (S, t) => versus(S, t, ease.in, 'ease in'),
  'overshoot': (S, t) => versus(S, t, ease.back, 'overshoot'),
  'stagger': (S, t) => { for (let i = 0; i < 6; i++) S.rect(`s${i}`, 40 + i * 70, lerp(170, 100, prog(t, stagger(0.3, i, 0.18), 0.5, ease.back)), 50, 70, { fill: hot, r: 8, op: prog(t, stagger(0.3, i, 0.18), 0.3) }) },
  'pop': (S, t) => { for (let i = 0; i < 8; i++) { const p = ease.back(clamp((t - 0.3 - i * 0.25) / 0.35)); S.rect(`p${i}`, 40 + i * 52, 135 - 35 * p, 44, 70 * p, { fill: log, r: 5 }) } },
  'hold': (S, t) => { const x = t < 1.2 ? lerp(60, 240, prog(t, 0.2, 1)) : t < 2.6 ? 240 : lerp(240, 420, prog(t, 2.6, 0.8)); S.circle('d', x, 135, 18, { fill: hot }); S.text('h', 240, 190, t > 1.2 && t < 2.6 ? 'hold' : '', { size: 22, fill: dim, anchor: 'middle', mono: true }) },
  'reveal': (S, t) => { S.text('r1', 240, lerp(130, 110, prog(t, 0.3, 0.7)), 'The seven stages', { size: 34, weight: 700, anchor: 'middle', op: prog(t, 0.3, 0.7) }); S.text('r2', 240, lerp(180, 160, prog(t, 1.0, 0.7)), 'of survivability', { size: 28, fill: hot, anchor: 'middle', op: prog(t, 1.0, 0.7) }) },
  'draw-on': (S, t) => S.path('berg', 'M 140 140 L 190 60 L 290 60 L 340 140 L 420 240 L 60 240 Z', { p: prog(t, 0.3, 2), stroke: cold, sw: 4 }),
  'wipe': (S, t) => ['var(--key)', cold, 'var(--warm)', hot].forEach((c, i) => S.rect(`w${i}`, 40, 60 + i * 44, 400 * prog(t, stagger(0.3, i, 0.25), 1), 30, { fill: c, r: 15 })),
  'morph': (S, t) => { const p = prog(t, 0.6, 1.2, ease.back); [-1, 0, 1].forEach((d, i) => S.rect(`m${i}`, lerp(170, 205 + d * 140, p), lerp(70, 95, p), lerp(140, 70, p), lerp(140, 90, p), { fill: 'var(--bg3)', stroke: hot, sw: 3, r: 12, op: i === 1 ? 1 : clamp(p) })) },
  'match cut': (S, t) => { const p = prog(t, 1.2, 0.8); S.rect('mc', lerp(60, 300, p), lerp(60, 150, p), lerp(240, 120, p), lerp(120, 70, p), { fill: 'var(--bg3)', stroke: p > 0.5 ? cold : hot, sw: 3, r: 10 }); S.text('mt', lerp(180, 360, p), lerp(120, 185, p), p > 0.5 ? 'snapshot' : 'memory', { size: 20, mono: true, fill: p > 0.5 ? cold : hot, anchor: 'middle' }) },
  'push-in': (S, t) => { const z = lerp(1, 2.2, prog(t, 0.5, 1.6)); S.cam(lerp(240, 330, prog(t, 0.5, 1.6)), 135, z); for (let i = 0; i < 4; i++) S.rect(`c${i}`, 60 + i * 100, 100, 80, 70, { fill: i === 3 ? hot : 'var(--bg3)', stroke: 'var(--line)', sw: 2, r: 8 }) },
  'pull back': (S, t) => { const k = camAt(t, [[0.5, { x: 390, y: 135, z: 2.4 }], [2.1, { x: 240, y: 135, z: 1 }, 'heavy']]); S.cam(k.x, k.y, k.z); for (let i = 0; i < 4; i++) S.rect(`c${i}`, 60 + i * 100, 100, 80, 70, { fill: i === 3 ? hot : 'var(--bg3)', stroke: 'var(--line)', sw: 2, r: 8 }) },
  'pan': (S, t) => { const k = camAt(t, [[0.5, { x: 120, y: 135, z: 1.8 }], [2.3, { x: 360, y: 135, z: 1.8 }]]); S.cam(k.x, k.y, k.z); S.line('pl', 120, 135, 340, 135, { stroke: dim, sw: 3, arrow: true }); S.rect('pa', 70, 110, 100, 50, { fill: 'var(--bg3)', stroke: 'var(--line)', sw: 2, r: 8 }); S.rect('pb', 350, 110, 100, 50, { fill: 'var(--bg3)', stroke: cold, sw: 2, r: 8 }) },
  'frame on': (S, t) => { const group = [[40, 40], [150, 60], [90, 120]]; const k = camAt(t, [[0.5, { x: 240, y: 135, z: 1 }], [2.1, frameOn([30, 30, 200, 170], [480, 270], { margin: 20 }), 'heavy']]); S.cam(k.x, k.y, k.z); group.forEach(([x, y], i) => S.rect(`f${i}`, x, y, 50, 40, { fill: cold, r: 6 })); for (let i = 0; i < 3; i++) S.rect(`o${i}`, 280 + i * 60, 180, 40, 40, { fill: 'var(--bg3)', stroke: 'var(--line)', sw: 2, r: 6 }) },
  'callout': (S, t) => { S.rect('cb', 60, 150, 180, 60, { fill: 'var(--bg3)', stroke: hot, sw: 3, r: 8 }); S.callout('co', 300, 80, 240, 160, 'hot · near the CPU', prog(t, 0.4, 1), { fill: hot, size: 20 }) },
  'strike-through': (S, t) => ['replay grows', 'capped by memory', 'one machine'].forEach((x, i) => { S.text(`st${i}`, 60, 70 + i * 60, `✗ ${x}`, { size: 24, mono: true, fill: bad }); S.strike(`sl${i}`, 60, 60 + 14.5 * (x.length + 2), 70 + i * 60, prog(t, stagger(0.4, i, 0.6), 0.4), { stroke: good }) }),
  'pulse': (S, t) => S.circle('pl', 240, 135, 40 + 18 * pulse(t % 1.2, 0.2, 0.6), { fill: log }),
  'flash': (S, t) => { S.rect('fb', 80, 60, 320, 150, { fill: 'var(--bg3)', stroke: 'var(--line)', sw: 2, r: 10 }); S.rect('ff', 80, 60, 320, 150, { fill: '#fff', r: 10, op: pulse(t, 1.0, 0.5) * 0.85 }) },
  'shake': (S, t) => { const d = Math.sin(t * 60) * 8 * pulse(t, 1.0, 0.8); S.rect('sk', 160 + d, 80, 160, 110, { fill: 'var(--bg3)', stroke: t > 1 ? bad : 'var(--line)', sw: 3, r: 12 }) },
  'count-up': (S, t) => S.text('cu', 240, 140, countUp(t, 0.3, 2, 0, 6, v => `${v.toFixed(1)} h`), { size: 64, weight: 700, anchor: 'middle', mono: true, fill: bad }),
  'dim the rest': (S, t) => [0, 1, 2].forEach(i => S.rect(`dr${i}`, 60 + i * 140, 90, 110, 90, { fill: 'var(--bg3)', stroke: i === 1 ? hot : 'var(--line)', sw: 3, r: 10, op: i === 1 ? 1 : lerp(1, 0.2, prog(t, 0.6, 0.8)) })),
  'keyframe': (S, t) => {
    const keys = [[0.3, [70, 200]], [1.1, [200, 70], 'out'], [1.9, [330, 70], 'linear'], [2.8, [420, 200], 'heavy']]
    keys.forEach(([, [x, y]], i) => S.circle(`kk${i}`, x, y, 5, { fill: 'var(--line)' }))
    const [x, y] = keyed(t, keys)
    S.rect('kb', x - 22, y - 22, 44, 44, { fill: hot, r: 6 })
  },
  'heavy': (S, t) => versus(S, t, ease.heavy, 'heavy'),
  'float': (S, t) => versus(S, t, ease.float, 'float'),
  'snap': (S, t) => versus(S, t, ease.snap, 'snap'),
  'follow-through': (S, t) => {
    const x = s => keyed(s, [[0.3, 110], [1.1, 370, 'snap'], [2.2, 370], [3.0, 110, 'snap']])
    const tag = follow(t, x, 0.06, 90, 7)
    S.line('fl', x(t), 110, tag, 185, { stroke: 'var(--line)', sw: 2 })
    S.rect('fb', x(t) - 50, 70, 100, 50, { fill: 'var(--bg3)', stroke: hot, sw: 3, r: 8 })
    S.circle('ft', tag, 195, 14, { fill: cold })
  },
  'settle': (S, t) => {
    const y = lerp(30, 170, prog(t, 0.4, 0.5, ease.in)) + settle(t, 0.9, -18, 2.5, 4)
    S.line('sg', 120, 201, 360, 201, { stroke: 'var(--line)', sw: 3 })
    S.rect('sb', 170, y - 30, 140, 60, { fill: 'var(--bg3)', stroke: hot, sw: 3, r: 8 })
  },
  'wobble': (S, t) => {
    for (let i = 0; i < 3; i++) {
      const x = 120 + i * 120 + wobble(t, 10, 1.2, i + 1), y = 135 + wobble(t, 7, 0.9, i + 11)
      S.line(`wl${i}`, 120 + i * 120, 0, x, y - 18, { stroke: 'var(--line)', sw: 2 })
      S.circle(`wc${i}`, x, y, 18, { fill: i === 1 ? log : 'var(--bg3)', stroke: log, sw: 2 })
    }
  },
  'blur together': (S, t) => { const m = prog(t, 1.4, 1.4); const f = S.blur('gblur', 8 * m); ['var(--key)', cold, 'var(--warm)', hot].forEach((c, i) => S.rect(`bt${i}`, 40, lerp(50 + i * 48, 92 + i * 17, m), 400 * prog(t, stagger(0.2, i, 0.2), 0.8), lerp(30, 22, m), { fill: c, r: 15, filter: f })) },
}

/** Draw one term's demo at loop time t. */
export function drawTerm(S, term, time) {
  S.begin()
  DEMOS[term]?.(S, time % LOOP)
  S.end()
}
