"""`studio look-sheet`: the record of a video's model sheet, and when it is stale."""
import json

import pytest

from studio_kit import look
from test_render import make_video


class FakeEngine:
    def __init__(self, video, name="live"):
        self.video, self.name, self.calls = video, name, []

    def layout(self):
        return {"width": 1920, "height": 1080, "band": {"height": 160, "chars": 26}}

    def look(self, out, caption):
        self.calls.append(list(caption))
        pages = []
        for i, title in enumerate(["colour and type", "elements and states"]):
            f = out / f"look-{i + 1}.png"
            f.write_bytes(b"png")
            pages.append({"page": i + 1, "title": title, "out": str(f)})
        return {"pages": pages}


def test_the_sheet_is_recorded_for_the_review_bundles_and_goes_stale_with_its_sources(tmp_path):
    make_video(tmp_path)
    (tmp_path / "out" / "look").mkdir(parents=True)
    (tmp_path / "out" / "look" / "look-9.png").write_bytes(b"old")
    e = FakeEngine(tmp_path)
    rec = look.make(tmp_path, engine=e)
    assert e.calls == [["Captions go in the band,", "at most two lines."]]        # wrapped at the layout's width
    assert [p["file"] for p in rec["pages"]] == ["out/look/look-1.png", "out/look/look-2.png"]
    assert not (tmp_path / "out" / "look" / "look-9.png").exists() and rec["own"] is None
    assert json.loads((tmp_path / "out" / "look" / "look.json").read_text())["key"] == rec["key"]
    assert look.latest(tmp_path)["stale"] is False
    (tmp_path / "scenes" / "look.js").write_text("export default function look(c) {}\n")
    assert look.latest(tmp_path)["stale"] is True
    assert look.make(tmp_path, engine=e)["own"] == "scenes/look.js" and not look.latest(tmp_path)["stale"]
    assert look.sheet_dir(tmp_path, "9:16") == tmp_path / "out" / "look" / "9x16"


def test_no_sheet_and_engines_without_one(tmp_path):
    make_video(tmp_path)
    assert look.latest(tmp_path) is None
    with pytest.raises(SystemExit, match="motion-canvas engine has no look sheet"):
        look.make(tmp_path, engine=FakeEngine(tmp_path, "motion-canvas"))


def test_look_sheet_is_a_command():
    from studio_kit import cli
    help_, arguments, handler = cli.COMMANDS["look-sheet"]
    assert handler == "look:main" and "out/look" in help_
