import json

import pytest

from studio_kit import assets, render
from studio_kit import timeline as tl
from test_render import make_video


def test_layout_applies_a_format_over_the_video_layout(tmp_path):
    make_video(tmp_path)
    (tmp_path / "layout.json").write_text(json.dumps(tl.DEFAULT_LAYOUT))
    v = tl.layout(tmp_path, "9:16")
    assert (v["width"], v["height"]) == (1080, 1920) and v["band"]["height"] == 340 and v["band"]["style"] == "opaque"
    assert tl.layout(tmp_path, "16:9") == tl.DEFAULT_LAYOUT and tl.layout(tmp_path) == tl.DEFAULT_LAYOUT


def test_a_video_can_override_a_format_and_unknown_formats_are_refused(tmp_path):
    (tmp_path / "layout.json").write_text(json.dumps({**tl.DEFAULT_LAYOUT, "formats": {"4:5": {"width": 1080, "height": 1350, "band": {"height": 240}}}}))
    assert tl.layout(tmp_path, "4:5")["height"] == 1350
    with pytest.raises(SystemExit, match="unknown format"):
        tl.layout(tmp_path, "21:9")


def test_each_format_gets_its_own_layout_file_and_clip_keys(tmp_path):
    t = make_video(tmp_path)
    (tmp_path / "layout.json").write_text(json.dumps(tl.DEFAULT_LAYOUT))
    f = tl.layout_file(tmp_path, "9:16")
    assert f.name == "9x16.json" and json.loads(f.read_text())["width"] == 1080
    assert tl.layout_file(tmp_path, None).name == "layout.json"
    assert render.clip_key(tmp_path, t, "s1", "draft", fmt="9:16") != render.clip_key(tmp_path, t, "s1", "draft")


def test_assets_are_recorded_with_provenance_and_change_the_clip_key(tmp_path):
    t = make_video(tmp_path)
    src = tmp_path / "logo.png"
    src.write_bytes(b"\x89PNG fake")
    before = render.clip_key(tmp_path, t, "s1", "draft")
    row = assets.add(tmp_path, src, "supplied", "the brand kit", "own work")
    assert row["file"] == "logo.png" and len(row["sha256"]) == 64 and row["license"] == "own work"
    assert [r["source"] for r in assets.read(tmp_path)] == ["the brand kit"]
    assert render.clip_key(tmp_path, t, "s1", "draft") != before
    assets.add(tmp_path, src, "supplied", "the brand kit, v2")            # re-adding replaces the row
    assert len(assets.read(tmp_path)) == 1


def test_capture_needs_a_source_kind():
    with pytest.raises(AssertionError):
        assets.record("x", "f", "invented", "src")
