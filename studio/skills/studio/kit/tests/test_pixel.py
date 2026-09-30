import json

import pytest

from studio_kit import check, new, pixel


def test_pixel_videos_get_a_grid_and_palette_and_extra_checks(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "h"))
    video, _ = new.create("p", directory=str(tmp_path / "p"), genre="pixel")
    cfg = pixel.config(video)
    assert cfg["grid"] == [320, 180] and len(cfg["palette"]) == 6
    assert check.genre(video) == "pixel"


def test_config_explains_what_is_missing(tmp_path):
    (tmp_path / "video.json").write_text(json.dumps({"genre": "pixel"}))
    with pytest.raises(SystemExit, match="palette"):
        pixel.config(tmp_path)


def test_hex_rgb():
    assert pixel.hex_rgb("#e6ebf0") == (0xE6, 0xEB, 0xF0)
