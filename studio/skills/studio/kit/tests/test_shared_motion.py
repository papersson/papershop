"""engines/shared/motion.js under node: the motion helpers are pure functions of time (a value never
depends on what was computed before it) and give the values their definitions promise."""
import json
import math
import shutil
import subprocess

import pytest

from studio_kit.env import engine_dir

pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")

SCRIPT = """
import * as m from %s
const cases = {
  ease: x => ['heavy', 'float', 'snap', 'back'].map(k => m.ease[k](x)),
  keyed: t => [m.keyed(t, [[1, 0], [2, 10, 'heavy'], [3, 4, m.ease.linear]]), m.keyed(t, [[1, [0, 100]], [2, [10, 50], 'snap']])],
  follow: t => [m.follow(t, s => (s >= 1 ? 1 : 0)), m.follow(t, () => 7.5), m.follow(t, s => [s >= 1 ? 2 : 0, 3], 0.2, 170, 26)],
  settle: t => [m.settle(t, 1, 10), m.settle(t, 1, 4, 2, 3)],
  wobble: t => [m.wobble(t), m.wobble(t, 5, 2, 3), m.wobble(t, 5, 2, 4)],
  spring: t => [m.spring(t), m.spring(t, 120, 14)],
}
const { inputs, order } = JSON.parse(process.argv[2])
const out = {}
for (const i of order) {               // in the order given, with unrelated calls in between
  const [name, x] = inputs[i]
  m.wobble(Math.random() * 100); m.follow(Math.random(), s => s)
  out[i] = cases[name](x)
}
console.log(JSON.stringify(inputs.map((_, i) => out[i])))
"""


def run(tmp_path, inputs, order):
    script = tmp_path / "motion.mjs"
    script.write_text(SCRIPT % json.dumps((engine_dir("shared") / "motion.js").as_uri()))
    done = subprocess.run(["node", str(script), json.dumps({"inputs": inputs, "order": order})], capture_output=True, text=True, check=True)
    return json.loads(done.stdout)


def inout(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def spring(t, k=170, d=26):
    if t <= 0:
        return 0
    w0, z = math.sqrt(k), d / (2 * math.sqrt(k))
    wd = w0 * math.sqrt(1 - z * z)
    return 1 - math.exp(-z * w0 * t) * (math.cos(wd * t) + z * w0 / wd * math.sin(wd * t))


def test_the_helpers_are_pure_functions_of_time_and_give_their_defined_values(tmp_path):
    grid = [i / 40 for i in range(41)]
    times = [round(0.5 + i / 30, 4) for i in range(120)]
    inputs = [["ease", x] for x in grid] + [[name, t] for name in ("keyed", "follow", "settle", "wobble", "spring") for t in times]
    forward = run(tmp_path, inputs, list(range(len(inputs))))
    backward = run(tmp_path, inputs, list(reversed(range(len(inputs)))))
    assert forward == backward                                  # no history, no call order
    got = dict(zip(map(lambda x: (x[0], x[1]), map(tuple, inputs)), forward))

    eases = [got[("ease", x)] for x in grid]
    heavy, flt, snap, back = zip(*eases)
    for curve in (heavy, flt, snap, back):
        assert curve[0] == pytest.approx(0, abs=1e-12) and curve[-1] == pytest.approx(1, abs=1e-12)
    for curve in (heavy, flt, snap):
        assert all(a <= b for a, b in zip(curve, curve[1:]))    # never back up
    assert [h for x, h in zip(grid, heavy)] == pytest.approx([inout(x ** 1.5) for x in grid])
    assert flt == pytest.approx([(1 - math.cos(math.pi * x)) / 2 for x in grid])
    assert snap == pytest.approx([(1 - 2 ** (-10 * x)) / (1 - 2 ** -10) for x in grid])
    assert max(back) == pytest.approx(1.1, abs=0.01)            # the 10% overshoot
    assert heavy[grid.index(0.25)] < 0.01 and snap[grid.index(0.25)] > 0.8   # heavy has barely started when snap is nearly there

    for t in times:
        a, v = got[("keyed", t)]
        want = 0 if t <= 1 else 10 * inout(min(1, t - 1) ** 1.5) if t < 2 else 10 - 6 * (t - 2) if t < 3 else 4
        assert a == pytest.approx(want)
        s = (1 - 2 ** (-10 * min(1, t - 1))) / (1 - 2 ** -10) if t > 1 else 0
        assert v == pytest.approx([10 * s, 100 - 50 * s])
        step, still, vec = got[("follow", t)]
        assert still == 7.5                                      # a still source is followed exactly
        assert step == pytest.approx(spring(t - 1.1, 120, 14), abs=0.02)   # a step, 0.1 s late, through the spring
        assert vec == pytest.approx([2 * spring(t - 1.2), 3], abs=0.03)
        s1, s2 = got[("settle", t)]
        assert s1 == pytest.approx(0 if t <= 1 else 10 * math.exp(-5 * (t - 1)) * math.sin(2 * math.pi * 3 * (t - 1)))
        assert s2 == pytest.approx(0 if t <= 1 else 4 * math.exp(-3 * (t - 1)) * math.sin(2 * math.pi * 2 * (t - 1)))
        w1, w2, w3 = got[("wobble", t)]
        assert -1 <= w1 <= 1 and -5 <= w2 <= 5 and w2 != w3     # a seed picks another sequence
        assert got[("spring", t)] == pytest.approx([spring(t), spring(t, 120, 14)])
    follow = [got[("follow", t)][0] for t in times]
    assert max(follow) > 1.03                                    # it swings past, then settles
    assert follow[-1] == pytest.approx(1, abs=0.01)
    wob = [got[("wobble", t)][1] for t in times]
    assert max(abs(a - b) for a, b in zip(wob, wob[1:])) <= 2 * 5 * 1.875 * 2 / 30   # smooth: at most the quintic's peak speed between two values


def test_every_engine_kit_offers_the_helpers(tmp_path):
    """The live kit as scenes import it; Remotion's and Motion Canvas's kits re-export the same."""
    script = tmp_path / "kit.mjs"
    script.write_text(f"import * as k from {json.dumps((engine_dir('live') / 'src' / 'kit.js').as_uri())}\n"
                      "console.log(JSON.stringify([k.keyed(1.5, [[1, 0], [2, 1, 'float']]), typeof k.follow, typeof k.settle, typeof k.wobble, typeof k.ease.snap]))")
    out = json.loads(subprocess.run(["node", str(script)], capture_output=True, text=True, check=True).stdout)
    assert out[0] == pytest.approx(0.5) and out[1:] == ["function"] * 4
    for f in (engine_dir("remotion") / "src" / "kit" / "time.ts", engine_dir("motion-canvas") / "src" / "base.ts"):
        text = f.read_text()
        assert all(f" {name}," in text or f" {name}}}" in text or f"function {name}" in text
                   for name in ("ease", "keyed", "follow", "settle", "wobble")), f
