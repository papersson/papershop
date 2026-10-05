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
