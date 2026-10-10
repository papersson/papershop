"""The Remotion engine through the kit's engine interface, in a real headless browser. Skipped where the
engine's packages or a browser are missing."""
import json
import shutil

import pytest

from studio_kit.engine import Engine
from studio_kit.env import engine_dir, resolve_browser
from test_render import make_video

needs_engine = pytest.mark.skipif(
    not (engine_dir("remotion") / "node_modules" / "remotion").is_dir() or not resolve_browser()[0] or not shutil.which("node"),
    reason="the Remotion engine's packages or a browser are not installed")

TERMINAL = """
import React from 'react';
import {Chapter, Terminal, useClip} from '@studio';

const RUNS = [{argv: ['ls'], stdout: 'a\\nb\\n', stderr: '', exit: 0},
	{argv: ['cat', 'notes.txt'], stdout: 'a much longer line of output that the panel has to shrink to fit its width\\n', stderr: '', exit: 0}];

export const S1: React.FC = () => {
	const {t} = useClip();
	return <Chapter><Terminal at={[0, 0]} w={8} runs={RUNS} progress={Math.min(1, t / 1.5)} size={24} /></Chapter>;
};
"""


@needs_engine
def test_a_terminal_keeps_one_text_size_as_it_plays(tmp_path):
    """It was sized for the lines shown so far, so its text shrank when the long line appeared."""
    make_video(tmp_path)
    (tmp_path / "video.json").write_text(json.dumps({"title": "t", "engine": "remotion"}))
    (tmp_path / "scenes" / "s1.tsx").write_text(TERMINAL)
    (tmp_path / "scenes" / "index.ts").write_text("import {S1} from './s1';\nexport default {s1: S1} as Record<string, import('react').FC>;\n")
    (tmp_path / "scenes" / "kit.tsx").unlink()
    early, late = Engine(tmp_path).boxes_at([{"clip": "s1", "t": 0.4}, {"clip": "s1", "t": 1.9}])
    rows = lambda f: {round(b["h"], 2) for b in f["boxes"] if b["name"].startswith("terminal row")}
    assert len(rows(early)) == 1 and rows(early) == rows(late)


CAMERA_AND_CLIP = """
import React from 'react';
import {Camera, CloseUp, Rect, RowTable, Txt, frameOn, useStage, type MapNode} from '@studio';

// s1: a push-in onto the right box crops the left ones; an unnamed shape and a named one sit off the
// frame with no camera. s2: a clipped close-up with a child wider than its panel, one it hides, and a table.
export const S1: React.FC = () => {
	const s = useStage();
	return <>
		<Camera keys={[[0, {cx: 0, cy: 0, zoom: 1}], [1, frameOn(s, [4.5, -0.7, 7.5, 0.7]), 'linear']]}>
			<Rect at={[6, 0]} w={3} h={1.4} fill="#8FD3FF" name="node server" />
			<Rect at={[-6, 0]} w={3} h={1.4} fill="#8FD3FF" name="node cache" />
			<Rect at={[-4, 1]} w={2} h={1} fill="#8FD3FF" />
		</Camera>
		<Rect at={[9, -2]} w={2} h={1} fill="#F2A93B" />
		<Rect at={[9, 2]} w={2} h={1} fill="#F2A93B" name="stray" />
	</>;
};

const NODES: MapNode[] = [{id: 'a', name: 'client', at: [-4, 0]}, {id: 'b', name: 'record', at: [0, 0]}, {id: 'c', name: 'db', at: [4, 0]}];
export const S2: React.FC = () => <>
	<CloseUp open={1} from={NODES[1]} name="record" nodes={NODES} clip>
		<Rect at={[0, 1.5]} w={30} h={0.6} fill="#8FD3FF" name="node wide bar" />
		<Rect at={[12, 1.5]} w={1} h={0.6} fill="#8FD3FF" name="node hidden" />
		<RowTable at={[0, -1.5]} w={6} columns={['id', 'price']} rows={[{id: 1, price: 30}, {id: 2, price: 12}]} />
	</CloseUp>
</>;
"""


@pytest.fixture(scope="module")
def camera_video(tmp_path_factory):
    v = tmp_path_factory.mktemp("camera")
    make_video(v)
    (v / "video.json").write_text(json.dumps({"title": "t", "engine": "remotion"}))
    (v / "scenes" / "kit.tsx").unlink()
    (v / "scenes" / "s1.tsx").write_text(CAMERA_AND_CLIP)
    (v / "scenes" / "s2.tsx").write_text("export {S2} from './s1';\n")
    (v / "scenes" / "index.ts").write_text("import {S1, S2} from './s1';\nexport default {s1: S1, s2: S2} as Record<string, import('react').FC>;\n")
    return v


@needs_engine
def test_a_push_in_and_shapes_with_no_name_of_their_own_never_fail_bounds(camera_video):
    """A Camera that has moved marks what it crops, and a Rect given no name (reported as "rect") is
    never bounds' to fail; a named element off the frame with no camera still fails."""
    from studio_kit import check
    e = Engine(camera_video)
    (f,) = e.boxes_at([{"clip": "s1", "t": 1.5}])
    named = {b["name"]: b for b in f["boxes"] if b["name"] != "rect"}
    assert named["node cache"]["camera"] is True and named["node cache"]["x"] + named["node cache"]["w"] < 0
    assert {b.get("named") for b in f["boxes"] if b["name"] == "rect"} == {False}
    rows = check.bounds(camera_video, engine=e, boxes=(e.layout(), [f]))
    assert rows[0]["detail"] == "'stray' leaves the frame"


@needs_engine
def test_a_clipped_close_up_reports_what_its_clip_shows(camera_video):
    from studio_kit import check
    e = Engine(camera_video)
    (f,) = e.boxes_at([{"clip": "s2", "t": 1.0}])
    by = {b["name"]: b for b in f["boxes"]}
    panel, bar = by["close-up"], by["node wide bar"]
    assert "node hidden" not in by
    assert bar["x"] == pytest.approx(panel["x"], abs=1) and bar["x"] + bar["w"] == pytest.approx(panel["x"] + panel["w"], abs=1)
    assert check.bounds(camera_video, engine=e, boxes=(e.layout(), [f]))[0]["ok"]


PUSH_INTO_BAND = """
import React from 'react';
import {Camera, CodePanel, Rect} from '@studio';

const SOURCE = {text: 'one\\ntwo\\nthree\\nfour\\nfive\\nsix\\n', sha256: 'synthetic'};
// s1: a push-in that takes a named code panel under the band. s2: a shape put in the band, no camera.
export const S1: React.FC = () => <Camera keys={[[0, {cx: 0, cy: 0, zoom: 2.5}]]}>
	<CodePanel name="retry code" at={[0, 0]} w={8} source={SOURCE} />
</Camera>;
export const S2: React.FC = () => <Rect at={[0, -4.2]} w={2} h={1} fill="#F2A93B" name="stray" />;
"""


@needs_engine
def test_the_band_hides_a_push_in_and_a_code_panel_goes_by_its_name(tmp_path):
    """A push-in under the opaque band failed both band checks, and the box was reported as 'panel',
    not the CodePanel's name; a shape put in the band with no camera still fails both."""
    from studio_kit import check
    make_video(tmp_path)
    (tmp_path / "video.json").write_text(json.dumps({"title": "t", "engine": "remotion"}))
    (tmp_path / "scenes" / "kit.tsx").unlink()
    (tmp_path / "scenes" / "s1.tsx").write_text(PUSH_INTO_BAND)
    (tmp_path / "scenes" / "s2.tsx").write_text("export {S2} from './s1';\n")
    (tmp_path / "scenes" / "index.ts").write_text("import {S1, S2} from './s1';\nexport default {s1: S1, s2: S2} as Record<string, import('react').FC>;\n")
    e = Engine(tmp_path)
    lay, frames = boxes = check._boxes(tmp_path, 1, e)
    panel = next(b for f in frames for b in f["boxes"] if b["name"] == "retry code")
    assert panel["camera"] is True and panel["y"] + panel["h"] > lay["height"] - lay["band"]["height"]
    guard = {r["clip"]: r for r in check.band_guard(tmp_path, engine=e, boxes=boxes)}
    assert guard["s1"]["ok"] and not guard["s2"]["ok"] and guard["s2"]["detail"].startswith("'stray' reaches")
    pixels = {r["clip"]: r for r in check.band_pixels_check(tmp_path, samples=1, engine=e) if r["check"] == "band"}
    assert pixels["s1"]["ok"] and not pixels["s2"]["ok"], pixels


def runs(line):
    """(bright, length) runs along a row or column of RGB pixels: TRAY_EDGE against the panel."""
    out = []
    for px in line:
        bright = sum(px) > 400
        if out and out[-1][0] == bright:
            out[-1][1] += 1
        else:
            out.append([bright, 1])
    return [n for bright, n in out if bright]


@needs_engine
def test_a_tables_outline_is_heavier_than_its_dividers_in_whole_pixels(camera_video, tmp_path):
    """Measured on the rendered frame: Chrome rounded 2.5 and 1.5 borders down and cells doubled their
    shared edges (outline 2, rows 2, columns 3 px). Now: outline 3, every divider 1."""
    import subprocess
    e = Engine(camera_video)
    (f,) = e.boxes_at([{"clip": "s2", "t": 1.0, "out": str(tmp_path / "t.png")}])
    table = next(b for b in f["boxes"] if b["name"] == "table")
    x0, y0, w, h = (round(table[k]) for k in ("x", "y", "w", "h"))
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(tmp_path / "t.png"), "-vf", f"crop={w + 4}:{h + 4}:{x0 - 2}:{y0 - 2}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    W = w + 4
    px = lambda x, y: tuple(raw[(y * W + x) * 3:(y * W + x) * 3 + 3])
    across = [px(x, 2 + 12) for x in range(W)]             # just inside the header row, above its text: outline, divider, outline
    down = [px(2 + 12, y) for y in range(h + 4)]             # just inside the first column, left of its text: outline, 2 dividers, outline
    assert runs(across) == [3, 1, 3] and runs(down) == [3, 1, 1, 3]


@needs_engine
def test_a_broken_look_file_breaks_the_look_sheet_alone(tmp_path):
    """@look was in the bundle every still and render uses, so a syntax error in scenes/look.tsx broke
    them all; the look sheet is a bundle of its own now."""
    from studio_kit.engine import EngineError
    make_video(tmp_path)
    (tmp_path / "video.json").write_text(json.dumps({"title": "t", "engine": "remotion"}))
    (tmp_path / "scenes" / "kit.tsx").unlink()
    (tmp_path / "scenes" / "s1.tsx").write_text("import React from 'react';\nexport const S1: React.FC = () => <div data-box=\"one\">one</div>;\n")
    (tmp_path / "scenes" / "index.ts").write_text("import {S1} from './s1';\nexport default {s1: S1} as Record<string, import('react').FC>;\n")
    (tmp_path / "scenes" / "look.tsx").write_text("export default {'mine': () => <div>\n")
    e = Engine(tmp_path)
    e.still("s1", 1.0, tmp_path / "s.png")
    assert (tmp_path / "s.png").stat().st_size > 0
    with pytest.raises(EngineError, match=r"look\.tsx"):
        e.look(tmp_path / "out", [])
