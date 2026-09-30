import json

from studio_kit import assets, check, motion
from test_render import make_video


class Frames:
    def __init__(self, frames):
        self.frames = frames

    def boxes_at(self, requests):
        return [{**r, **f} for r, f in zip(requests, self.frames)]


def test_legible_flags_text_under_18_px_only(tmp_path):
    make_video(tmp_path)
    frames = [{"band": {}, "boxes": [{"name": "tiny label", "kind": "text", "x": 0, "y": 0, "w": 90, "h": 14},
                                     {"name": "big", "kind": "text", "x": 0, "y": 0, "w": 90, "h": 26},
                                     {"name": "a box", "kind": "", "x": 0, "y": 0, "w": 90, "h": 4}]}]
    lay = {"width": 1920, "height": 1080, "band": {"height": 160}}
    rows = motion.legible(tmp_path, boxes=(lay, [{"clip": "s1", "t": 1.0, **frames[0]}]))
    assert not rows[0]["ok"] and "tiny label" in rows[0]["detail"] and "big" not in rows[0]["detail"]


def test_at_global_maps_timeline_seconds_to_clip_time(tmp_path):
    t = make_video(tmp_path)
    assert motion.at_global(t, 0.5) == ("s1", 0.5) and motion.at_global(t, 2.5) == ("s2", 0.5)
    assert motion.at_global(t, 99)[0] == "s2"


def test_provenance_finds_assets_scenes_use_without_a_row(tmp_path):
    make_video(tmp_path)
    (tmp_path / "scenes" / "s1.tsx").write_text('<Shot file="ui.png" at={[0,0]} /> staticFile(\'logo.svg\')')
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "ui.png").write_bytes(b"x")
    assets.record(tmp_path, "ui.png", "capture", "https://example.com")
    rows = motion.provenance(tmp_path)
    assert not rows[0]["ok"] and "logo.svg" in rows[0]["detail"] and "ui.png" not in rows[0]["detail"].split(";")[0]
    (tmp_path / "assets" / "logo.svg").write_bytes(b"x")
    assets.record(tmp_path, "logo.svg", "supplied", "brand kit")
    assert motion.provenance(tmp_path)[0]["ok"]


def test_pixel_and_motion_videos_get_their_extra_checks_by_default(tmp_path):
    make_video(tmp_path)
    (tmp_path / "video.json").write_text(json.dumps({"genre": "motion", "loop": True}))
    assert check.genre(tmp_path) == "motion" and check.config(tmp_path)["loop"]
