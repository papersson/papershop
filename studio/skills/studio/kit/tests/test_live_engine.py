"""The live engine through the kit's engine interface: stills, boxes, durations, scene errors and
determinism, in a real headless browser. Skipped where the engine's packages or a browser are missing."""
import hashlib
import json
import shutil

import pytest

from studio_kit import render, settings
from studio_kit import timeline as tl
from studio_kit.engine import Engine, EngineError
from studio_kit.env import engine_dir, resolve_browser

needs_engine = pytest.mark.skipif(
    not (engine_dir("live") / "node_modules" / "playwright-core").is_dir() or not resolve_browser()[0] or not shutil.which("node"),
    reason="the live engine's packages or a browser are not installed")

SCENE = """
export default function draw(c) {
  const { S, P, W, H } = c
  S.text('title', W / 2, H * 0.3, 'Keys and values', { size: 48, anchor: 'middle', op: P(c.at('01'), 0.5) })
  S.rect('card', 200, 300, 400, 160, { fill: '#1C242E', stroke: '#F2A93B', box: 'card', op: P(c.phrase('01', 'values'), 0.4) })
  if (c.t > 1.4 && globalThis.BROKEN) throw new Error('boom')
}
"""


def live_video(tmp_path, scene=SCENE):
    (tmp_path / "scenes").mkdir()
    (tmp_path / "scenes" / "s1.js").write_text(scene)
    narration = [{"id": "s1_01", "clip": "s1", "text": "Keys and values.", "caption": "Keys and values.", "paragraph": 0,
                  "start": 0.3, "end": 1.6, "words": [{"w": "Keys", "start": 0.3, "end": 0.6}, {"w": "and", "start": 0.6, "end": 0.8},
                                                       {"w": "values.", "start": 0.8, "end": 1.6}]},
                 {"id": "s2_01", "clip": "s2", "text": "A board.", "caption": "A board.", "paragraph": 0,
                  "start": 2.2, "end": 3.0, "words": []}]
    t = {"version": 1, "fps": 30, "duration": 3.5, "cues": {},
         "tracks": {"scene": [{"id": "s1", "engine": "live", "title": "One", "start": 0.0, "end": 2.0},
                              {"id": "s2", "engine": "live", "title": "Two", "start": 2.0, "end": 3.5}],
                    "narration": narration, "captions": tl.chunk_captions(narration), "audio": []}}
    (tmp_path / "timeline.json").write_text(json.dumps(t))          # a built timeline, as the engines read it
    (tmp_path / "video.json").write_text(json.dumps({"title": "t", "engine": "live"}))
    return t


def test_live_is_an_engine_and_a_chapter_without_a_scene_file_shows_its_board(tmp_path):
    live_video(tmp_path)
    assert settings.load(tmp_path)["engine"] == "live"
    assert render.has_scene(tmp_path, "s1") and not render.has_scene(tmp_path, "s2")


def test_new_explainers_default_to_the_live_engine(tmp_path):
    from argparse import Namespace
    from studio_kit import new
    args = Namespace(name="v", dir=str(tmp_path / "v"), title="T", drive="author", source=None, genre="explainer",
                     duration=None, engine=None, level=None, checkpoints=None, from_video=None, include=[], mode=None)
    new.main(args)
    cfg = json.loads((tmp_path / "v" / "video.json").read_text())
    assert cfg["engine"] == "live"
    assert (tmp_path / "v" / "scenes" / "example-chapter.js").exists()


@needs_engine
def test_stills_boxes_and_durations(tmp_path):
    live_video(tmp_path)
    e = Engine(tmp_path)
    assert e.durations(["s1", "s2"]) == {"s1": 60, "s2": 45}
    frames = e.boxes_at([{"clip": "s1", "t": 1.5}, {"clip": "s2", "t": 0.5}])
    names = {b["name"] for b in frames[0]["boxes"]}
    assert {"title", "card", "caption"} <= names
    assert frames[0]["band"] == {"y": 920, "h": 160}
    text = [b for b in frames[0]["boxes"] if b["name"] == "title"][0]
    assert text["kind"] == "text" and text["h"] > 40
    assert "board tag" in {b["name"] for b in frames[1]["boxes"]}
    out = tmp_path / "a.png"
    e.still("s1", 1.5, out)
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


@needs_engine
def test_a_frame_is_the_same_whatever_was_drawn_before(tmp_path):
    live_video(tmp_path)
    e = Engine(tmp_path)
    reqs = [{"clip": "s1", "t": 1.5, "out": str(tmp_path / "alone.png")}]
    e.stills(reqs)
    e.stills([{"clip": "s2", "t": 1.0, "out": str(tmp_path / "x.png")}, {"clip": "s1", "t": 0.1, "out": str(tmp_path / "y.png")},
              {"clip": "s1", "t": 1.5, "out": str(tmp_path / "after.png")}])
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert h(tmp_path / "alone.png") == h(tmp_path / "after.png")


@needs_engine
def test_a_scene_error_names_the_clip_and_time(tmp_path):
    live_video(tmp_path, SCENE.replace("globalThis.BROKEN", "true"))
    with pytest.raises(EngineError, match=r"scene error in s1 at 1\.500 s: Error: boom"):
        Engine(tmp_path).still("s1", 1.5, tmp_path / "x.png")


@needs_engine
def test_the_kit_has_the_shared_keyed_track_and_a_format_shows_its_own_caption_lines(tmp_path):
    t = live_video(tmp_path, """
export default function draw(c) {
  c.S.rect('mover', c.kit.track(c.t, [[0, 100], [0.2, 700]]), 100, 50, 50, { fill: '#fff', box: 'mover' })
}
""")
    (f,) = Engine(tmp_path).boxes_at([{"clip": "s1", "t": 1.5}])
    assert next(b for b in f["boxes"] if b["name"] == "mover")["x"] == pytest.approx(700, abs=1)
    t["tracks"]["captions"][0]["wrapped"]["9:16"] = ["Keys", "and values."]
    (tmp_path / "timeline.json").write_text(json.dumps(t))
    (f,) = Engine(tmp_path, fmt="9:16").boxes_at([{"clip": "s1", "t": 1.0}])
    assert len([b for b in f["boxes"] if b["name"] == "caption"]) == 2
    del t["tracks"]["captions"][0]["wrapped"]
    (tmp_path / "timeline.json").write_text(json.dumps(t))
    with pytest.raises(EngineError, match="no 9:16 caption lines"):
        Engine(tmp_path, fmt="9:16").still("s1", 1.0, tmp_path / "x.png")


@needs_engine
def test_doctor_renders_a_still_the_way_the_engine_starts_its_browser():
    from studio_kit import doctor
    assert doctor.check_launch()[:2] == (doctor.OK, "browser launch")


@needs_engine
def test_bounds_leaves_a_push_ins_crop_to_inframe(tmp_path):
    """A camera pushed in on the left box crops the right one off the frame: the camera's doing, so
    bounds passes it; a box placed off the frame with the camera at rest still fails."""
    from studio_kit import check
    live_video(tmp_path, """
export default function draw(c) {
  const { S, W, H } = c
  c.camAt([[0, { x: W / 2, y: H / 2, z: 1 }], [1, { x: 400, y: H / 2, z: 3 }, 'linear']])
  S.rect('left', 300, H / 2 - 50, 200, 100, { fill: '#fff', box: 'left box' })
  S.rect('right', W - 400, H / 2 - 50, 300, 100, { fill: '#fff', box: 'right box' })
  if (c.t < 0.5) S.rect('stray', W - 100, 100, 300, 100, { fill: '#fff', box: 'stray box', layer: 'ui' })
}
""")
    e = Engine(tmp_path)
    lay = e.layout()
    frames = e.boxes_at([{"clip": "s1", "t": 1.5}, {"clip": "s1", "t": 0.2}])
    right = next(b for b in frames[0]["boxes"] if b["name"] == "right box")
    assert right["camera"] is True and right["x"] > lay["width"]
    rows = check.bounds(tmp_path, boxes=(lay, frames))
    assert rows[0]["ok"] and not rows[1]["ok"] and "'stray box' leaves the frame" in rows[1]["detail"]


PAN_AND_OVERLAY = """
export default function draw(c) {
  const { S, W } = c
  c.camAt([[0, { x: W / 2, y: c.H / 2, z: 1 }], [1, { x: W / 2 + 100.5, y: c.H / 2 - 40.25, z: 1.15 }, 'linear']])
  S.rect('box', W / 2 - 100, 200, 200, 120, { fill: '#8FD3FF', box: 'box' })
  S.text('title', W / 2, 40, 'A title card', { size: 40, anchor: 'middle', layer: 'over', box: 'title card' })
}
"""


@needs_engine
def test_a_moving_camera_leaves_the_background_and_the_overlays_where_they_are(tmp_path):
    """The background sat inside the camera group, so a pan left a seam one shade off in the band (the
    band pixel check failed); the 'over' layer moved with the camera too, so an overlay's title went
    off the top. Both stay put now; the scene under them moves."""
    from studio_kit import check
    live_video(tmp_path, PAN_AND_OVERLAY)
    e = Engine(tmp_path)
    rest, f = e.boxes_at([{"clip": "s1", "t": 0.0}, {"clip": "s1", "t": 1.45}])
    named = lambda frame, n: next(b for b in frame["boxes"] if b["name"] == n)
    assert named(f, "title card")["camera"] is False and named(f, "title card")["y"] == pytest.approx(named(rest, "title card")["y"])
    assert named(f, "box")["camera"] is True and named(f, "box")["y"] != pytest.approx(named(rest, "box")["y"])
    rows = [r for r in check.band_pixels_check(tmp_path, samples=1, engine=e, clips={"s1"}) if r["check"] == "band"]
    assert rows and all(r["ok"] for r in rows), rows


@needs_engine
def test_a_broken_look_file_is_named(tmp_path):
    live_video(tmp_path)
    (tmp_path / "scenes" / "look.js").write_text("export default function look(c) {\n")
    with pytest.raises(EngineError, match=r"scenes/look\.js: .*Unexpected end of input"):
        Engine(tmp_path).look(tmp_path / "out", [])
    assert Engine(tmp_path).boxes_at([{"clip": "s1", "t": 1.0}])           # the chapters still draw


@needs_engine
def test_boxes_carry_colours_and_meanings_and_the_look_sheet_draws_the_legend(tmp_path):
    """The legend check's inputs, from a real browser: each element's resolved colours and its `means`
    tag, the legend on the scene's context, and a legend page on the look sheet."""
    live_video(tmp_path, """
export default function draw(c) {
  const { S, kit: { C } } = c
  S.rect('card', 200, 300, 400, 160, { fill: C.bg2, stroke: c.legend.step, box: 'card', means: 'step' })
  S.text('title', 400, 200, 'Keys', { fill: C.cold })
}
""")
    (tmp_path / "video.json").write_text(json.dumps({"title": "t", "engine": "live", "legend": {"step": "hot", "focus": "cold"}}))
    (f,) = Engine(tmp_path).boxes_at([{"clip": "s1", "t": 1.0}])
    by = {b["name"]: b for b in f["boxes"]}
    assert (by["card"]["fill"], by["card"]["stroke"], by["card"]["means"]) == ("rgb(21, 27, 34)", "rgb(242, 169, 59)", "step")
    assert by["title"]["fill"] == "rgb(143, 211, 255)" and "means" not in by["title"]
    from studio_kit import check
    (w,) = [r["detail"] for r in check.run(tmp_path, only=["legend"]) if r.get("severity") == "warning"]
    assert w.startswith("cold, which the legend keeps for focus, is on 'title' at s1")
    pages = Engine(tmp_path).look(tmp_path / "out", [])["pages"]
    assert [p["title"] for p in pages][-1] == "colour legend"


@needs_engine
def test_a_legend_colour_is_named_in_any_case_and_an_unknown_one_fails(tmp_path):
    """{"focus": "Hot"} drew nothing (var(--Hot)) and the check passed; a name the theme lacks drew
    nothing too."""
    live_video(tmp_path, """
export default function draw(c) {
  c.S.rect('picked', 100, 300, 200, 100, { stroke: c.legend.focus, box: 'picked', means: 'focus' })
}
""")
    (tmp_path / "video.json").write_text(json.dumps({"title": "t", "engine": "live", "legend": {"focus": "Hot"}}))
    (f,) = Engine(tmp_path).boxes_at([{"clip": "s1", "t": 1.0}])
    assert next(b for b in f["boxes"] if b["name"] == "picked")["stroke"] == "rgb(242, 169, 59)"
    (tmp_path / "video.json").write_text(json.dumps({"title": "t", "engine": "live", "legend": {"focus": "Hto"}}))
    with pytest.raises(EngineError, match='legend "focus": "Hto" is not a theme colour'):
        Engine(tmp_path).boxes_at([{"clip": "s1", "t": 1.0}])


@needs_engine
def test_the_close_ups_minimap_is_the_kits_and_the_legend_page_stacks_its_rows(tmp_path):
    """With focus: cold the default minimap warned; a long meaning ran into the colour column."""
    from studio_kit import check
    live_video(tmp_path, """
export default function draw(c) {
  c.S.closeUp('cu', c.view, { open: 1, name: 'detail', map: [[0, 0, 100, 50], [150, 0, 100, 50]], of: 0 })
}
""")
    legend = {"focus": "cold", "a much longer meaning name than most": "key"}
    (tmp_path / "video.json").write_text(json.dumps({"title": "t", "engine": "live", "legend": legend}))
    assert [r for r in check.run(tmp_path, only=["legend"]) if r.get("severity")] == []
    for fmt in (None, "9:16"):
        page = Engine(tmp_path, fmt=fmt).look(tmp_path / "out", [])["pages"][-1]
        by = {b["name"]: b for b in page["boxes"]}
        for meaning in legend:
            a, b = by[f"legend {meaning}"], by[f"legend colour {meaning}"]
            assert a["y"] + a["h"] <= b["y"] + 1 or a["x"] + a["w"] <= b["x"], (fmt, meaning)


# --- the 3D stage --------------------------------------------------------------------------------

needs_3d = pytest.mark.skipif(not (engine_dir("live") / "node_modules" / "three").is_dir(), reason="three.js is not installed")

SCENE_3D = """
export default function draw(c) {
  const { S, G, t, W, kit } = c
  const cy = c.view[1] + c.view[3] / 2
  const side = { target: [W / 2, -40, cy], az: -25, el: 30, span: 300, fov: 30 }
  c.shot([[0.5, c.flatShot()], [1.0, side, 'heavy']])
  if (t < 0.5) {
    S.rect('slab', W / 2 - 200, cy - 100, 400, 200, { fill: kit.C.bg3, stroke: kit.C.edge, sw: 3, r: 0, box: 'slab' })
    return
  }
  G.mesh('slab', 'box', { size: [400, 12, 200] }, { at: [W / 2, -6, cy], color: kit.C.bg3, edges: { width: 3, color: kit.C.edge }, box: 'slab' })
  G.mesh('gear', 'cylinder', { r: 30, h: 20 }, { at: [W / 2, -40, cy], color: c.legend.gear, means: 'gear', box: 'gear' })
  G.mesh('pin', 'sphere', { r: 20 }, { at: [W / 2 + 120, 40, cy], color: kit.C.hot, box: 'pin' })
  const [x, y] = G.project([W / 2 + 200, 0, cy])
  S.text('label slab', x + 30, y, 'slab', { size: 28 })
}
"""


def video_3d(tmp_path, scene=SCENE_3D, seconds=2.0, cues=None):
    (tmp_path / "scenes").mkdir()
    (tmp_path / "scenes" / "s1.js").write_text(scene)
    narration = [{"id": "s1_01", "clip": "s1", "text": "The gear turns under the slab.", "caption": "The gear turns under the slab.",
                  "paragraph": 0, "start": 0.3, "end": 1.6, "words": []}]
    t = {"version": 1, "fps": 30, "duration": seconds, "cues": cues or {},
         "tracks": {"scene": [{"id": "s1", "engine": "live", "title": "One", "start": 0.0, "end": seconds}],
                    "narration": narration, "captions": tl.chunk_captions(narration), "audio": []}}
    (tmp_path / "timeline.json").write_text(json.dumps(t))
    (tmp_path / "video.json").write_text(json.dumps({"title": "t", "engine": "live", "legend": {"gear": "cold"}}))
    return t


def rgba(path):
    from studio_kit import proc
    return proc.ffmpeg("-i", str(path), "-f", "rawvideo", "-pix_fmt", "rgb24", "-", capture_output=True).stdout


@needs_engine
@needs_3d
def test_a_flat_diagram_opens_into_depth_without_a_jump_and_its_3d_elements_are_reported(tmp_path):
    """The SVG diagram and the 3D model built in the same numbers meet on the handover frame: the frame
    before it (SVG) and the frame of it (WebGL, the flat shot) differ only by antialiasing. The 3D
    boxes carry their palette colour, legend meaning, camera state and visible share."""
    video_3d(tmp_path)
    e = Engine(tmp_path)
    e.stills([{"clip": "s1", "t": 14 / 30, "out": tmp_path / "svg.png"}, {"clip": "s1", "t": 15 / 30, "out": tmp_path / "gl.png"}])
    a, b = rgba(tmp_path / "svg.png"), rgba(tmp_path / "gl.png")
    assert len(a) == len(b) and sum(abs(x - y) for x, y in zip(a, b)) / len(a) < 0.5
    frames = e.boxes_at([{"clip": "s1", "t": 0.75}, {"clip": "s1", "t": 1.5}])
    moving, held = ({b["name"]: b for b in f["boxes"]} for f in frames)
    assert moving["slab"]["kind"] == "3d" and moving["slab"]["camera"] is True and held["slab"]["camera"] is False
    assert held["gear"]["fill"] == "rgb(143, 211, 255)" and held["gear"]["means"] == "gear" and held["slab"]["stroke"] == "rgb(201, 211, 221)"
    assert held["gear"]["visible"] == 0 and held["pin"]["visible"] > 0.95 and held["slab"]["visible"] > 0.95
    assert held["label slab"]["kind"] == "text"                    # labels stay SVG text, which the checks read


@needs_engine
@needs_3d
def test_3d_frames_are_the_same_in_any_order_and_the_background_layer_hides_the_canvas(tmp_path):
    video_3d(tmp_path)
    e = Engine(tmp_path)
    times = [1.5, 0.75, 1.2, 0.2]
    digests = []
    for order in (times, times[::-1]):
        batch = [{"clip": "s1", "t": t, "out": tmp_path / f"{len(digests)}-{t}.png"} for t in order]
        e.stills(batch)
        digests.append({r["t"]: hashlib.sha256(rgba(r["out"])).hexdigest() for r in batch})
    assert digests[0] == digests[1]
    e.stills([{"clip": "s1", "t": 1.5, "out": tmp_path / "bg3d.png", "layers": "background"},
              {"clip": "s1", "t": 0.2, "out": tmp_path / "bg2d.png", "layers": "background"}])
    assert rgba(tmp_path / "bg3d.png") == rgba(tmp_path / "bg2d.png")


@needs_engine
@needs_3d
def test_occluded_warns_about_a_narrated_part_the_model_hides(tmp_path):
    from studio_kit import check
    video_3d(tmp_path)
    rows = check.occluded(tmp_path, engine=Engine(tmp_path))
    assert any("'gear' (0% visible)" in r["detail"] for r in rows)
    assert not any("'slab'" in r["detail"] for r in rows)


@needs_engine
@needs_3d
def test_the_template_3d_chapter_draws_through_its_cues(tmp_path):
    from studio_kit.env import ROOT
    scene = (ROOT / "templates" / "live" / "scenes" / "example-3d.js").read_text()
    scene = scene.replace("{{opens into depth}}", "open").replace("{{flattens again}}", "close")
    video_3d(tmp_path, scene, seconds=6.0, cues={"open": 1.0, "close": 4.0})
    e = Engine(tmp_path)
    assert len(e.stills([{"clip": "s1", "t": t, "out": tmp_path / f"{t}.png"} for t in (0.5, 3.0, 5.6)])["stills"]) == 3
    names = {b["name"] for b in e.boxes("s1", 3.0)["boxes"]["boxes"]}
    assert {"layer {{top layer}}", "layer {{bottom layer}}", "label0:txt"} <= names


@needs_engine
@needs_3d
def test_doctor_names_the_webgl_renderer_the_3d_stage_gets():
    from studio_kit import doctor
    level, name, detail, _ = doctor.check_webgl()
    assert (level, name) == ("ok", "webgl cpu") and "WebGL 2.0" in detail and "three r" in detail


@needs_engine
@needs_3d
def test_a_view_of_its_own_draws_an_item_in_its_panel(tmp_path):
    """Two items side by side, each in a view with its own camera (a look sheet's items): each one's
    box lies in its panel, and a node in a view nobody pointed a camera at fails, naming the view."""
    scene = """
export default function draw(c) {
  const { G, kit } = c
  const shot = { target: [0, 0, 0], az: -20, el: 30, span: 160, fov: 30 }
  G.camera(shot, { view: 'left', rect: [0, 0, 960, 920] })
  G.camera(shot, { view: 'right', rect: [960, 0, 960, 920] })
  G.mesh('a', 'box', { size: [120, 120, 120] }, { view: 'left', color: kit.C.hot, box: 'cube left' })
  G.mesh('b', 'box', { size: [120, 120, 120] }, { view: 'right', color: kit.C.cold, box: 'cube right' })
  if (c.t > 1) G.mesh('c', 'box', { size: [10, 10, 10] }, { view: 'nowhere' })
}
"""
    video_3d(tmp_path, scene)
    boxes = {b["name"]: b for b in Engine(tmp_path).boxes("s1", 0.5)["boxes"]["boxes"]}
    left, right = boxes["cube left"], boxes["cube right"]
    assert 0 < left["x"] and left["x"] + left["w"] < 960 and 960 < right["x"] and right["x"] + right["w"] < 1920
    assert right["x"] - left["x"] == pytest.approx(960, abs=1) and right["w"] == pytest.approx(left["w"], abs=0.5)
    with pytest.raises(EngineError, match="no camera for the view \"nowhere\""):
        Engine(tmp_path).still("s1", 1.5, tmp_path / "x.png")


@needs_engine
@needs_3d
def test_a_3d_box_is_clipped_to_its_view_and_bounds_leaves_it_to_inframe(tmp_path):
    """A model that overfills its panel is cropped there on screen, so its box is the part in the
    panel, marked clipped; bounds leaves the view's crop alone (as a camera's), and inframe warns when
    the narration names the part the view cuts."""
    scene = """
export default function draw(c) {
  const { G, kit } = c
  const shot = { target: [0, 0, 0], az: -20, el: 30, span: 160, fov: 30 }
  G.camera(shot, { view: 'left', rect: [0, 0, 960, 920] })
  G.mesh('a', 'box', { size: [600, 120, 120] }, { view: 'left', color: kit.C.hot, box: 'slab' })
  G.mesh('b', 'box', { size: [20, 20, 20] }, { view: 'left', color: kit.C.cold, box: 'gear' })
}
"""
    video_3d(tmp_path, scene)
    boxes = {b["name"]: b for b in Engine(tmp_path).boxes("s1", 0.5)["boxes"]["boxes"]}
    slab, gear = boxes["slab"], boxes["gear"]
    assert slab["clipped"] is True and slab["x"] >= 0 and slab["x"] + slab["w"] <= 960 and slab["y"] + slab["h"] <= 920
    assert "clipped" not in gear
    from studio_kit import check
    assert all(r["ok"] for r in check.bounds(tmp_path, samples=1))
    assert any("'slab'" in r["detail"] for r in check.in_frame(tmp_path, samples=1))
