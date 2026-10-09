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
