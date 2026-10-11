"""3D shots (engines/shared/camera3d.js) under node: shot keys give any frame alone, the target lands in
the middle of the view, the flat shot lines a model up with the 2D stage, and a dolly zoom keeps the
target's plane the same size on screen."""
import json
import shutil
import subprocess

import pytest

from studio_kit.env import engine_dir

pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")


def run(tmp_path, body):
    script = tmp_path / "camera3d.mjs"
    script.write_text(f"import * as c3 from {json.dumps((engine_dir('shared') / 'camera3d.js').as_uri())}\n"
                      f"import * as kit from {json.dumps((engine_dir('live') / 'src' / 'kit.js').as_uri())}\n"
                      f"console.log(JSON.stringify({body}))")
    return json.loads(subprocess.run(["node", str(script)], capture_output=True, text=True, check=True).stdout)


SHOT = "{target: [0, 0, 0], az: 0, el: 30, span: 100, fov: 30}"


def test_shot_keys_ease_hold_and_say_when_they_move(tmp_path):
    keys = f"[[1, {SHOT}], [3, {{...{SHOT}, az: 40, span: 400, fov: 1}}, 'linear'], [5, {{...{SHOT}, az: 40, span: 400, fov: 1}}]]"
    out = run(tmp_path, f"[0, 2, 3, 4, 9].map(t => c3.shotAt(t, {keys}))")
    assert out[0] == {"target": [0, 0, 0], "az": 0, "el": 30, "span": 100, "fov": 30}
    assert out[1]["az"] == pytest.approx(20) and out[1]["moving"] is True
    assert out[1]["span"] == pytest.approx(200) and out[1]["fov"] == pytest.approx(30 ** 0.5)   # in proportion
    assert "moving" not in out[3] and out[3] == out[4]          # between two equal keys is a hold, not a move
    assert run(tmp_path, f"(() => {{ const a = c3.shotAt(2.2, {keys}); [4, 0.3, 2.9].forEach(t => c3.shotAt(t, {keys})); return [a, c3.shotAt(2.2, {keys})] }})()") \
        == run(tmp_path, f"[c3.shotAt(2.2, {keys}), c3.shotAt(2.2, {keys})]")


@pytest.mark.parametrize("keys,error", [
    ("[[0, {target: [0, 0], az: 0, el: 0, span: 1, fov: 30}]]", "target must be [x, y, z]"),
    ("[[0, {target: [0, 0, 0], az: 0, el: 0, span: 0, fov: 30}]]", "span must be above 0"),
    ("[[0, {target: [0, 0, 0], az: 0, el: 0, span: 1, fov: 180}]]", "fov must be in (0, 170)"),
    ("[[1, {target: [0, 0, 0], az: 0, el: 0, span: 1, fov: 30}], [0, {target: [0, 0, 0], az: 0, el: 0, span: 1, fov: 30}]]", "time order"),
    ("[[0, {target: [0, 0, 0], az: 0, el: 0, span: 1, fov: 30}, 'wobbly']]", "no ease wobbly"),
])
def test_a_bad_key_fails_before_any_frame(tmp_path, keys, error):
    out = run(tmp_path, f"(() => {{ try {{ c3.shotAt(0, {keys}); return null }} catch (e) {{ return e.message }} }})()")
    assert error in out


def test_the_target_lands_in_the_middle_of_the_view_at_any_angle(tmp_path):
    # a 1920 x 1080 canvas whose view is the stage above a 160 px band: the view's middle is (960, 460)
    out = run(tmp_path, "[[0, 90, 1], [-30, 20, 40], [120, 5, 10]].map(([az, el, fov]) => {"
                        " const cam = c3.camera({target: [5, 7, -3], az, el, span: 460, fov}, [1920, 1080], [0, 0, 1920, 920]);"
                        " return c3.project(cam, [5, 7, -3]) })")
    for x, y, front in out:
        assert x == pytest.approx(960) and y == pytest.approx(460) and front


def test_the_flat_shot_puts_a_world_point_on_its_stage_pixel_and_a_dolly_zoom_keeps_its_size(tmp_path):
    out = run(tmp_path, "(() => { const view = [0, 0, 1920, 920], flat = c3.flatShot({x: 960, y: 460, z: 1}, 920);"
                        " const at = s => c3.camera(s, [1920, 1080], view);"
                        " const wide = {...flat, fov: 40};"
                        " return [flat, [[960, 0, 460], [100, 0, 200], [1500, 0, 800]].map(p => c3.project(at(flat), p)),"
                        "         c3.scaleAt(at(flat), [960, 0, 460]), c3.scaleAt(at(wide), [960, 0, 460])] })()")
    flat, points, s_flat, s_wide = out
    assert flat == {"target": [960, 0, 460], "az": 0, "el": 90, "span": 460, "fov": 1}
    for (x, y, _), (wx, wy) in zip(points, [(960, 460), (100, 200), (1500, 800)]):
        assert x == pytest.approx(wx, abs=1e-6) and y == pytest.approx(wy, abs=1e-6)
    assert s_flat == pytest.approx(1) and s_wide == pytest.approx(1)     # the target's plane: one pixel a unit either way


def test_frame_on_fits_points_in_the_view_and_the_kit_has_the_pure_versions(tmp_path):
    out = run(tmp_path, "(() => { const view = [0, 100, 1920, 820];"
                        " const pts = [0, 1, 2, 3, 4, 5, 6, 7].map(i => [i & 1 ? 400 : 0, i & 2 ? 200 : 0, i & 4 ? 300 : 0]);"
                        " const s = c3.frameOn3(pts, [1920, 1080], view, {az: -30, el: 25, fov: 35, margin: 0.1});"
                        " const cam = c3.camera(s, [1920, 1080], view);"
                        " const p = pts.map(q => c3.project(cam, q));"
                        " return [p, typeof kit.shotAt, typeof kit.flatShot, typeof kit.frameOn3] })()")
    points, *kinds = out
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    assert min(xs) >= 192 - 1 and max(xs) <= 1728 + 1 and min(ys) >= 100 + 82 - 1 and max(ys) <= 920 - 82 + 1   # inside the margins
    assert max((max(xs) - min(xs)) / 1536, (max(ys) - min(ys)) / 656) == pytest.approx(1, abs=0.01)          # and touching them
    assert kinds == ["function"] * 3


def test_a_point_behind_the_camera_is_not_in_front(tmp_path):
    out = run(tmp_path, f"(() => {{ const cam = c3.camera({SHOT}, [1920, 1080]); const p = c3.placement({SHOT});"
                        " const behind = p.position.map((v, j) => v + p.back[j] * 10); return c3.project(cam, behind) })()")
    assert out[2] is False
