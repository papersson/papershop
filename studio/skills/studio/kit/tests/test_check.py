import subprocess
import struct
import zlib
from pathlib import Path

from studio_kit import check, sheets
from test_render import make_video


def test_contrast_ratio_matches_wcag_endpoints():
    assert round(check.contrast_ratio((0, 0, 0), (255, 255, 255)), 1) == 21.0
    assert check.contrast_ratio((0xE6, 0xEB, 0xF0), (10, 13, 17)) > check.MIN_CONTRAST
    assert check.contrast_ratio((0x8C, 0x97, 0xA4), (0x60, 0x68, 0x74)) < check.MIN_CONTRAST


def test_sample_times_spread_over_each_clip(tmp_path):
    t = make_video(tmp_path)
    times = check.sample_times(t, 3)
    assert {r["clip"] for r in times} == {"s1", "s2"}
    assert all(r["t"] >= 0 for r in times)
    assert times[0]["t"] == round(1.5 - 0.15 - 0.0, 3)


class FakeEngine:
    def __init__(self, frames):
        self.frames = frames

    def boxes_at(self, requests):
        return [{**r, **self.frames} for r in requests]


LAYOUT = {"width": 1920, "height": 1080, "band": {"height": 160}}


def boxes(tmp_path, items):
    return LAYOUT, [{"clip": "s1", "t": 1.0, "band": {"y": 920, "h": 160}, "boxes": items}]


def test_band_guard_flags_an_element_that_reaches_the_band(tmp_path):
    ok = check.band_guard(tmp_path, boxes=boxes(tmp_path, [{"name": "label", "x": 100, "y": 800, "w": 200, "h": 30}]))
    bad = check.band_guard(tmp_path, boxes=boxes(tmp_path, [{"name": "label", "x": 100, "y": 900, "w": 200, "h": 40}]))
    assert ok[0]["ok"] and not bad[0]["ok"] and "'label'" in bad[0]["detail"]


def test_the_band_hides_what_a_moved_camera_pushes_under_it(tmp_path):
    """A deliberate push-in failed band ('panel' reaches y=943) though the opaque band hides it; a box
    with no camera still fails, and so does a camera's under a frosted band, which shows it."""
    pushed = {"name": "retry code", "x": 100, "y": 600, "w": 900, "h": 343, "camera": True}
    stray = {"name": "label", "x": 1200, "y": 900, "w": 200, "h": 40}
    rows = check.band_guard(tmp_path, boxes=boxes(tmp_path, [pushed, stray]))
    assert rows[0]["detail"] == "'label' reaches y=940 (band starts at 920)"
    frosted = {**LAYOUT, "band": {"height": 160, "style": "frosted"}}
    assert "'retry code'" in check.band_guard(tmp_path, boxes=(frosted, boxes(tmp_path, [pushed])[1]))[0]["detail"]
    # the band's pixels: the pushed box's (and its edge's) are left out, a pixel beyond them is counted
    W, h = 1920, 160
    bare = bytearray(W * h * 3)
    scene = bytearray(bare)
    for x in range(98, 1004):
        scene[(10 * W + x) * 3] = 255           # row 10 of the band (y=930): under the box, edges included
    assert check.scene_in_band(bytes(scene), bytes(bare), LAYOUT) == 906
    assert check.scene_in_band(bytes(scene), bytes(bare), LAYOUT, [pushed]) == 0
    scene[(10 * W + 1500) * 3] = 255
    assert check.scene_in_band(bytes(scene), bytes(bare), LAYOUT, [pushed]) == 1


def test_bounds_flags_elements_off_the_frame_and_wide_captions(tmp_path):
    rows = check.bounds(tmp_path, boxes=boxes(tmp_path, [
        {"name": "runaway", "x": 1900, "y": 100, "w": 100, "h": 20},
        {"name": "caption", "x": 40, "y": 950, "w": 1840, "h": 40}]))
    assert not rows[0]["ok"] and "runaway" in rows[0]["detail"] and "margins" in rows[0]["detail"]


def test_tile_joins_images_into_one_sheet(tmp_path):
    files = []
    for i in range(5):
        f = tmp_path / f"{i}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=blue:s=160x90:d=1", "-frames:v", "1", str(f)], check=True)
        files.append(f)
    out = sheets.tile(files, tmp_path / "sheet.png", 4, width=80)
    w, h = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(out)],
                          capture_output=True, text=True).stdout.strip().split("x")
    assert int(w) == 4 * 80 + 3 * 4 and int(h) == 2 * 45 + 1 * 4       # 4 columns, 2 rows, 4 px between


def test_a_clip_without_narration_is_still_sampled(tmp_path):
    t = make_video(tmp_path)
    t["tracks"]["narration"] = []
    times = check.sample_times(t, 3)
    assert [r["clip"] for r in times] == ["s1"] * 3 + ["s2"] * 3
    assert times[0]["t"] == 0.5 and times[2]["t"] == 1.5           # a 2 s clip: quarter points


def png(pixel, comment):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)) + \
        chunk(b"tEXt", b"Comment\0" + comment) + chunk(b"IDAT", zlib.compress(b"\0" + bytes(pixel))) + chunk(b"IEND", b"")


class PixelEngine:
    def __init__(self, colors):
        self.colors, self.calls = colors, 0

    def stills(self, requests):
        for r in requests:
            Path(r["out"]).write_bytes(png(self.colors[self.calls], str(self.calls).encode()))
        self.calls += 1


def test_determinism_compares_decoded_pixels_not_png_metadata(tmp_path):
    make_video(tmp_path)
    engine = PixelEngine([(1, 2, 3, 255)] * 2)
    rows = check.determinism(tmp_path, samples=1, engine=engine, clips={"s1"})
    assert all(r["ok"] for r in rows) and engine.calls == 2
    assert not (tmp_path / "research/determinism").exists()


def test_determinism_retries_but_preserves_a_flaky_failure_and_evidence(tmp_path):
    make_video(tmp_path)
    engine = PixelEngine([(1, 2, 3, 255), (2, 3, 4, 255), (1, 2, 3, 255), (1, 2, 3, 255)])
    rows = check.determinism(tmp_path, samples=1, engine=engine, clips={"s1"})
    assert engine.calls == 4 and not rows[0]["ok"]
    assert "FLAKY" in rows[0]["detail"] and "differing pixels 1" in rows[0]["detail"]
    evidence = next((tmp_path / "research/determinism").iterdir())
    assert len(list(evidence.glob("*.png"))) == 4 and (evidence / "results.json").exists()


def test_overlap_flags_text_on_text_but_not_text_on_a_shape():
    from studio_kit import check
    frames = [{"clip": "s1", "t": 1.0, "boxes": [
        {"name": "label a", "kind": "text", "x": 100, "y": 100, "w": 200, "h": 40},
        {"name": "label b", "kind": "text", "x": 150, "y": 110, "w": 200, "h": 40},
        {"name": "card", "kind": "", "x": 90, "y": 90, "w": 400, "h": 200},
        {"name": "caption", "kind": "text", "x": 100, "y": 100, "w": 200, "h": 40},
        {"name": "far", "kind": "text", "x": 900, "y": 100, "w": 100, "h": 40}]}]
    rows = check.overlap(None, engine=object(), boxes=({}, frames))
    assert not rows[0]["ok"] and rows[0]["detail"] == "'label a' and 'label b' overlap"
    frames[0]["boxes"][1]["x"] = 600
    assert check.overlap(None, engine=object(), boxes=({}, frames))[0]["ok"]


def test_inframe_warns_when_a_narrated_element_leaves_the_visible_stage(tmp_path):
    import json
    t = make_video(tmp_path)
    t["tracks"]["narration"][0]["text"] = "The server answers the client."
    (tmp_path / "timeline.json").write_text(json.dumps(t))
    (tmp_path / "boards").mkdir()
    (tmp_path / "boards" / "notes.json").write_text(json.dumps({"s1_01": "the cache lights"}))
    lay = {**LAYOUT, "header": {"height": 100}}
    frame = lambda items: (lay, [{"clip": "s1", "t": 1.35, "boxes": items}])
    box = lambda name, x, y, w=200, h=60, **kw: {"name": name, "x": x, "y": y, "w": w, "h": h, **kw}
    ok = check.in_frame(tmp_path, boxes=frame([box("node server", 800, 400), box("node client", 100, 400),
                                                box("node database", 2400, 400),          # not narrated: may leave
                                                box("SERVER", 40, 30, h=40),              # wholly in the header strip
                                                box("node cache", -900, 400, opacity=0)]))  # faded out
    assert ok == [{"check": "inframe", "clip": "s1", "t": 1.35, "ok": True, "detail": ""}]
    bad = check.in_frame(tmp_path, boxes=frame([box("node server", 1800, 400), box("client", 100, 80),
                                                 box("node cache", 300, 880), box("node client", 3000, 400)]))
    assert bad[0]["ok"] and bad[0]["severity"] == "warning"
    assert "'node server' (right)" in bad[0]["detail"] and "'client' (header)" in bad[0]["detail"]
    assert "'node cache' (band)" in bad[0]["detail"] and "'node client' (out of frame)" in bad[0]["detail"]
    assert check.in_frame(tmp_path, boxes=(lay, [{"clip": "s2", "t": 0.5, "boxes": [box("node server", 3000, 0)]}])) == []


def test_a_label_is_narrated_when_its_words_are_said_together():
    words = check._said("The hash function turns a key into a bucket.")
    assert check.narrated("box hash function", words) and check.narrated("bucket", words)
    assert not check.narrated("node function hash", words) and not check.narrated("card", words)
    assert not check.narrated("a", words) and not check.narrated("box the", words)


def test_bounds_leaves_elements_under_a_moved_camera_alone(tmp_path):
    lay = {"width": 1920, "height": 1080, "band": {"height": 160}}
    box = lambda name, x, **k: {"name": name, "kind": "", "x": x, "y": 100, "w": 300, "h": 100, **k}
    frames = [{"clip": "s1", "t": 1.0, "boxes": [box("cropped", 1800, camera=True), box("gone", 2500, camera=True)]},
              {"clip": "s1", "t": 2.0, "boxes": [box("placed off", 1800)]}]
    rows = check.bounds(tmp_path, engine=object(), boxes=(lay, frames))
    assert rows[0]["ok"] and rows[1]["detail"] == "'placed off' leaves the frame"


def test_inframe_flags_a_narrated_element_pushed_off_the_top_past_the_header(tmp_path):
    """With a header, an element wholly above the frame (y1 <= header but y0 < 0) is out of frame, not
    header content: only one lying within the strip is left alone."""
    import json
    t = make_video(tmp_path)
    t["tracks"]["narration"][0]["text"] = "The server answers."
    (tmp_path / "timeline.json").write_text(json.dumps(t))
    lay = {**LAYOUT, "header": {"height": 120}}
    rows = check.in_frame(tmp_path, boxes=(lay, [{"clip": "s1", "t": 1.35, "boxes": [
        {"name": "node server", "x": 800, "y": -300, "w": 200, "h": 100, "camera": True}]}]))
    assert rows[0]["severity"] == "warning" and "'node server' (out of frame)" in rows[0]["detail"]
    rows = check.in_frame(tmp_path, boxes=(lay, [{"clip": "s1", "t": 1.35, "boxes": [
        {"name": "node server", "x": 800, "y": 20, "w": 200, "h": 60}]}]))
    assert rows[0]["detail"] == ""


def test_bounds_leaves_a_shape_with_no_name_of_its_own_alone(tmp_path):
    lay = {"width": 1920, "height": 1080, "band": {"height": 160}}
    frames = [{"clip": "s1", "t": 1.0, "boxes": [{"name": "rect", "kind": "", "x": 1800, "y": 100, "w": 300, "h": 100, "named": False},
                                                 {"name": "node db", "kind": "", "x": 1800, "y": 300, "w": 300, "h": 100}]}]
    rows = check.bounds(tmp_path, engine=object(), boxes=(lay, frames))
    assert rows[0]["detail"] == "'node db' leaves the frame"
