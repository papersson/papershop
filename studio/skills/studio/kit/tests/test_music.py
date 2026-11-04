import json
import subprocess

import pytest

from studio_kit import assets, music
from studio_kit import timeline as tl

TRACKS = [{"id": f"t{i}", "file": f"tracks/t{i}.mp3", "title": f"Track {i}", "artist": "A. Composer",
           "license": "CC BY 4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
           "source": f"https://example.org/t{i}", "seconds": s} for i, s in enumerate((300.0, 200.0, 400.0))]


def chapters(*starts, end):
    return [{"id": f"c{i}", "start": a, "end": b} for i, (a, b) in enumerate(zip(starts, starts[1:] + (end,)))]


def test_a_film_gets_a_track_per_run_of_chapters_starting_at_a_chapter_and_crossing_over():
    scenes = chapters(0.0, 100.0, 260.0, 430.0, 600.0, 700.0, end=840.0)
    es = music.plan("some-film", scenes, 840.0, TRACKS)
    starts = {c["start"] for c in scenes}
    assert len({e["file"] for e in es}) >= 2 and es[0]["start"] == 0.0
    assert all(e["start"] in starts or e["start"] > 0 for e in es)
    first_changes = [e["start"] for e in es[1:]]
    assert any(s in starts for s in first_changes)                     # a change lands on a chapter join
    for a, b in zip(es, es[1:]):
        assert a["start"] + a["out"] == pytest.approx(b["start"] + music.FADE)   # fades out under the next fade in
    assert es[-1]["start"] + es[-1]["out"] == pytest.approx(840.0)
    assert music.plan("some-film", scenes, 840.0, TRACKS) == es       # the same film, the same music
    others = {tuple(e["file"] for e in music.plan(n, scenes, 840.0, TRACKS)) for n in ("a", "b", "c", "d", "e")}
    assert len(others) > 1                                             # films differ


def test_a_run_longer_than_its_track_hands_over_to_the_next():
    es = music.plan("x", chapters(0.0, end=450.0), 450.0, TRACKS, chosen=[TRACKS[1], TRACKS[0]])
    assert [e["file"] for e in es] == ["assets/music/t1.mp3", "assets/music/t0.mp3"]
    assert es[0]["out"] == pytest.approx(200.0) and es[1]["start"] == pytest.approx(200.0 - music.FADE)


def test_what_video_json_asks_for():
    assert music.wanted({}, TRACKS) is None and music.wanted({"music": False}, TRACKS) is None
    assert music.wanted({"music": True}, TRACKS) == "choose" and music.wanted({"music": True}, []) is None
    assert music.wanted({"music": ["t2"]}, TRACKS) == [TRACKS[2]]
    with pytest.raises(SystemExit, match="not in the palette"):
        music.wanted({"music": ["nope"]}, TRACKS)
    with pytest.raises(SystemExit, match="must be true, false"):
        music.wanted({"music": "yes"}, TRACKS)


@pytest.fixture
def palette(tmp_path, monkeypatch):
    root = tmp_path / "music"
    (root / "tracks").mkdir(parents=True)
    for t in TRACKS:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=330:duration=2",
                        str(root / t["file"])], check=True)
    (root / "palette.json").write_text(json.dumps({"tracks": TRACKS}))
    monkeypatch.setattr(music, "home", lambda: root)
    return root


def narrated(tmp_path, cfg):
    v = tmp_path / "film"
    (v / "audio").mkdir(parents=True)
    (v / "video.json").write_text(json.dumps({"title": "x", **cfg}))
    narration = [{"id": "s0_01", "clip": "s0", "text": "Hello there.", "caption": "Hello there.", "start": 0.5, "end": 2.0}]
    (v / "timeline.json").write_text("{}")
    t = {"duration": 600.0, "tracks": {"scene": chapters(0.0, 300.0, end=600.0), "narration": narration, "audio": []}}
    return v, t


def test_the_tracks_are_copied_in_with_provenance_and_credited(tmp_path, palette):
    v, t = narrated(tmp_path, {"music": True})
    es = music.entries(v, t, {"music": True})
    assert es and all((v / e["file"]).exists() for e in es)
    rows = assets.music_rows(v)
    assert {r["file"] for r in rows} == {e["file"].removeprefix("assets/") for e in es}
    assert rows[0]["license"] == "CC-BY-4.0" and rows[0]["params"]["artist"] == "A. Composer"
    assert assets.credits(v).startswith("CREDITS\nMusic:\n  \"Track")
    assert assets.page_credits(v)[0].startswith("Music: \"Track") and "(CC BY 4.0)" in assets.page_credits(v)[0]
    assert music.entries(v, t, {"music": True}) == es                  # again: nothing changes
    music.entries(v, t, {"music": [TRACKS[2]["id"]]})                   # a different choice: the rest go
    assert [r["params"]["music"] for r in assets.music_rows(v)] == ["t2"]
    assert sorted(p.name for p in (v / "assets" / "music").iterdir()) == ["t2.mp3"]


def test_no_music_without_the_ask_or_a_narration(tmp_path, palette):
    v, t = narrated(tmp_path, {})
    assert music.entries(v, t, {}) == [] and music.entries(v, t, {"music": False}) == []
    t["tracks"]["narration"] = []
    assert music.entries(v, t, {"music": True}) == []
    assert not (v / "assets" / "music").exists()


def test_a_missing_palette_warns_and_builds_without_music(tmp_path, monkeypatch):
    monkeypatch.setattr(music, "home", lambda: tmp_path / "nowhere")
    v, t = narrated(tmp_path, {"music": True})
    said = []
    assert music.entries(v, t, {"music": True}, said.append) == []
    assert said and "no palette" in said[0]


def test_a_new_film_has_palette_music_unless_music_was_placed_by_hand(tmp_path, palette, monkeypatch):
    from studio_kit import narration, new
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    video, _ = new.create("retry-safety")
    assert json.loads((video / "video.json").read_text())["music"] is True
    (video / "SCRIPT.md").write_text((video / "SCRIPT.md").read_text().replace(
        "> {{Narration paragraph", "> Retries can charge twice. {{Narration paragraph"))
    narration.narrate(video, estimate=True)
    placed = [e for e in tl.load(video)["tracks"]["audio"] if e["role"] == "music"]
    assert placed and all(e["file"].startswith("assets/music/") for e in placed)
    (video / "audio" / "tracks.json").write_text(json.dumps([{"file": "bed.wav", "role": "music"}]))
    t = tl.build(video, quiet=True)
    assert [e["file"] for e in t["tracks"]["audio"] if e["role"] == "music"] == ["bed.wav"]
