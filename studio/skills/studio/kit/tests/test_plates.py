"""Plates: frames another renderer draws behind a live chapter (plates.py), here a stand-in renderer
(a Python script reading the same request Blender's adapter reads), and Blender itself when installed."""
import json
import shutil
import sys
from pathlib import Path

import pytest

from studio_kit import keys, plates
from studio_kit import timeline as tl
from studio_kit.engine import Engine
from studio_kit.env import engine_dir, resolve_browser
from test_render import make_video

needs_engine = pytest.mark.skipif(not (engine_dir("live") / "node_modules").is_dir() or not resolve_browser()[0]
                                  or not shutil.which("node"), reason="the live engine or a browser is not installed")

RENDERER = """
import json, sys
from pathlib import Path
from PIL import Image
req = json.loads(Path(sys.argv[1]).read_text())
out = Path(req["out"])
with open(out / "frames.jsonl", "a") as log:
    for f in req["frames"]:
        Image.new("RGB", (req["width"], req["height"]), (200, 40, 40)).save(out / f"f{f:05d}.png")
        log.write(json.dumps({"frame": f, "seconds": 0.01, "points": {"head": [req["width"] * 0.25, req["height"] * 0.5, True]}}) + "\\n")
Path(req["out"], "calls.txt").open("a").write(f"{len(req['frames'])}\\n")
"""

SCENE = """
export default function draw(c) {
  c.plate()
  const p = c.plate.at('head')
  if (p) c.S.text('label head', p[0] + 20, p[1], 'head', { size: 28 })
}
"""


def plated(tmp_path):
    t = make_video(tmp_path)
    (tmp_path / "sims").mkdir()
    (tmp_path / "sims" / "render.py").write_text(RENDERER)
    (tmp_path / "scenes" / "s1.js").write_text(SCENE)
    (tmp_path / "video.json").write_text(json.dumps({"title": "t", "engine": "live", "plates": {"s1": {
        "renderer": "command", "command": [sys.executable, "sims/render.py", "{request}"], "script": "sims/render.py",
        "project": ["head"]}}}))
    return t


def test_a_plate_renders_once_resumes_and_is_part_of_its_clips_key(tmp_path):
    t = plated(tmp_path)
    count = tl.frames(t, "s1")[1]
    d = plates.render(tmp_path, t, "s1", "draft", range(10))
    assert len(list(d.glob("f*.png"))) == 10 and plates.seconds_per_frame(d) == 0.01
    plates.render(tmp_path, t, "s1", "draft", range(count))            # resumes: only the frames it lacks
    assert [int(n) for n in (d / "calls.txt").read_text().split()] == [10, count - 10]
    before = keys.clip_key(tmp_path, t, "s1", "draft")
    (tmp_path / "sims" / "render.py").write_text(RENDERER + "\n# a change to the scene\n")
    assert keys.clip_key(tmp_path, t, "s1", "draft") != before and keys.clip_key(tmp_path, t, "s2", "draft")


@needs_engine
def test_a_live_chapter_draws_its_plate_and_labels_its_projected_points(tmp_path):
    """The plate fills the stage above the band, behind the scene; the label sits on the point the
    renderer projected; the band, the boxes and the checks are the live engine's as ever."""
    plated(tmp_path)
    e = Engine(tmp_path)
    e.stills([{"clip": "s1", "t": 1.0, "out": tmp_path / "a.png"}])
    from PIL import Image
    im = Image.open(tmp_path / "a.png").convert("RGB")
    assert im.getpixel((960, 300)) == (200, 40, 40) and im.getpixel((960, 1050)) != (200, 40, 40)   # under the band: the band
    box = {b["name"]: b for b in e.boxes("s1", 1.0)["boxes"]["boxes"]}["label head"]
    band_top = tl.band_top(tl.layout(tmp_path))
    assert abs(box["x"] - (1920 * 0.25 + 20)) < 4 and abs(box["y"] + box["h"] / 2 - band_top / 2) < 6
    assert json.loads((tmp_path / ".cache" / "plates" / "index.json").read_text())["s1"]["quality"] == "draft"


BLENDER_SCENE = """
import bpy

def build(scene, ctx):
    bpy.ops.mesh.primitive_cube_add(size=1)
    scene.objects[-1].name = "head"
    bpy.ops.object.camera_add(location=(0, -6, 0), rotation=(1.5708, 0, 0))
    scene.camera = scene.objects[-1]
    bpy.ops.object.light_add(type="SUN")

def pose(scene, t, ctx):
    bpy.data.objects["head"].location.x = t
"""


@pytest.mark.skipif(not plates.blender(), reason="Blender is not installed")
def test_blender_renders_a_plate_and_projects_its_objects(tmp_path):
    t = make_video(tmp_path)
    (tmp_path / "sims").mkdir()
    (tmp_path / "sims" / "scene.py").write_text(BLENDER_SCENE)
    (tmp_path / "video.json").write_text(json.dumps({"title": "t", "engine": "live", "plates": {"s1": {
        "script": "sims/scene.py", "project": ["head"], "draft": {"samples": 1, "scale": 0.25}}}}))
    d = plates.render(tmp_path, t, "s1", "draft", [0, 30])
    from PIL import Image
    assert Image.open(d / "f00030.png").size == plates.size(tmp_path, plates.config(tmp_path)["s1"], "draft")
    log = [json.loads(line) for line in (d / "frames.jsonl").read_text().splitlines()]
    x0, x1 = (next(e["points"]["head"][0] for e in log if e["frame"] == f) for f in (0, 30))
    assert x1 > x0                                      # the cube moved right between the two frames
