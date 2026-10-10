"""Camera keys and framing (engines/shared/camera.js, the live kit's camAt and frameOn) under node: a
camera move is one declaration that gives any frame alone, its zoom moving in proportion."""
import json
import shutil
import subprocess

import pytest

from studio_kit.env import engine_dir

pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")


def run(tmp_path, body):
    script = tmp_path / "camera.mjs"
    script.write_text(f"import * as cam from {json.dumps((engine_dir('shared') / 'camera.js').as_uri())}\n"
                      f"import * as kit from {json.dumps((engine_dir('live') / 'src' / 'kit.js').as_uri())}\n"
                      f"console.log(JSON.stringify({body}))")
    return json.loads(subprocess.run(["node", str(script)], capture_output=True, text=True, check=True).stdout)


def test_a_camera_passes_its_keys_and_zooms_in_proportion(tmp_path):
    keys = "[[1, {x: 0, y: 0, zoom: 1}], [3, {x: 10, y: -4, zoom: 4}, 'linear'], [4, {x: 10, y: -4, zoom: 4}]]"
    out = run(tmp_path, f"[0, 1, 2, 3, 3.5, 9].map(t => cam.cameraAt(t, {keys}))")
    assert out[0] == out[1] == {"x": 0, "y": 0, "zoom": 1}
    assert out[2]["zoom"] == pytest.approx(2)                  # halfway in time: the geometric mean, not 2.5
    # the centre moves in step with 1/zoom: (1 - 1/2) / (1 - 1/4) of the way
    assert out[2]["x"] == pytest.approx(10 * 2 / 3) and out[2]["y"] == pytest.approx(-4 * 2 / 3)
    assert out[3] == out[4] == out[5] == {"x": 10, "y": -4, "zoom": pytest.approx(4)}


def test_a_frame_is_the_same_in_any_order(tmp_path):
    keys = "[[0, {x: 0, y: 0, zoom: 1}], [2, {x: 3, y: 1, zoom: 2}, 'heavy']]"
    out = run(tmp_path, f"(() => {{ const a = cam.cameraAt(1.3, {keys}); [0.2, 1.9, 0.7].forEach(t => cam.cameraAt(t, {keys})); return [a, cam.cameraAt(1.3, {keys})] }})()")
    assert out[0] == out[1]


def test_frame_on_fits_a_region_and_the_live_kit_names_it_for_s_cam(tmp_path):
    out = run(tmp_path, "[cam.frameOn([4, 2, 0, 0], [16, 8], {margin: 1}), cam.frameOn([0, 0, 100, 1], [16, 8], {max: 1}),"
                        " kit.frameOn([100, 100, 300, 200], [1920, 800], {margin: 0}),"
                        " kit.camAt(1, [[0, {x: 0, y: 0, z: 1}], [2, {x: 100, y: 50, z: 1}, 'linear']])]")
    assert out[0] == {"x": 2, "y": 1, "zoom": 2}                # 6 x 4 with its margin, in 16 x 8
    assert out[1]["zoom"] == pytest.approx(0.16)
    assert out[2] == {"x": 200, "y": 150, "z": 4}                 # 9.6 to fit, clamped to the kit's max
    assert out[3]["x"] == pytest.approx(50) and out[3]["y"] == pytest.approx(25) and out[3]["z"] == pytest.approx(1)


@pytest.mark.parametrize("keys,error", [
    ("[[0, {x: 0, y: 0, zoom: 0}]]", "zoom above 0"),
    ("[[0, {x: 0, y: 0, zoom: 1}], [1, {x: 0, y: 0, zoom: Infinity}]]", "zoom above 0"),
    ("[[0, {x: 0, y: 0, zoom: 1}], [1, {x: NaN, y: 0, zoom: 1}]]", "x and y must be numbers"),
    ("[[2, {x: 0, y: 0, zoom: 1}], [1, {x: 5, y: 0, zoom: 1}]]", "keys go in time order"),
    ("[[0, {x: 0, y: 0, zoom: 1}], [5, {x: 1, y: 0, zoom: 1}], [9, {x: 2, y: 0, zoom: 1}, 'heavvy']]", "no ease heavvy"),
])
def test_a_bad_key_fails_at_once_not_when_its_move_plays(tmp_path, keys, error):
    """At t = 0, before the bad key's segment: out of order, non-finite or an unknown ease all throw."""
    with pytest.raises(subprocess.CalledProcessError) as e:
        run(tmp_path, f"cam.cameraAt(0, {keys})")
    assert error in e.value.stderr


def test_a_push_in_takes_its_subject_straight_to_the_centre(tmp_path):
    """The review's case: a 1920 px stage, a box at x 1500-1860 framed from the whole stage. With the
    centre moving linearly its right edge swung out to 1992 px at t = 3; now every point of the box moves
    monotonically on screen and stays inside the frame."""
    out = run(tmp_path, """(() => {
      const keys = [[1, {x: 960, y: 460, z: 1}], [5, kit.frameOn([1500, 400, 1860, 560], [1920, 920], {margin: 46}), 'linear']]
      return [...Array(41).keys()].map(i => { const t = 1 + i / 10, k = kit.camAt(t, keys)
        return [1500, 1860].map(x => 960 + (x - k.x) * k.z) })
    })()""")
    for edge in (0, 1):
        xs = [p[edge] for p in out]
        steps = [b - a for a, b in zip(xs, xs[1:])]
        assert all(d <= 1e-9 for d in steps) or all(d >= -1e-9 for d in steps), edge
    assert max(p[1] for p in out) <= 1920 and min(p[0] for p in out) >= 0


def test_both_engines_take_one_default_ease(tmp_path):
    """The same keys without an ease give the same camera in live and Remotion: both pass none on, so the
    shared camera's inOut applies (Remotion's keyed would default to smooth)."""
    out = run(tmp_path, "[cam.CAMERA_EASE, kit.camAt(0.3, [[0, {x: 0, y: 0, z: 1}], [1, {x: 10, y: 0, z: 1}]]).x]")
    assert out == ["inOut", pytest.approx(10 * 4 * 0.3 ** 3)]
    map_tsx = (engine_dir("remotion") / "src" / "kit" / "map.tsx").read_text()
    assert "ease?: motion.Ease | keyof typeof motion.ease): Framing" in map_tsx and "motion.smooth): Framing" not in map_tsx
