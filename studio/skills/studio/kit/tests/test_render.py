import copy
import json
from pathlib import Path

from studio_kit import render
from studio_kit import timeline as tl


def make_video(tmp_path):
    (tmp_path / "scenes").mkdir()
    for name in ("s1.tsx", "s2.tsx", "kit.tsx", "index.ts"):
        (tmp_path / "scenes" / name).write_text(f"// {name}\n")
    narration = [{"id": "s1_01", "clip": "s1", "text": "One.", "caption": "One.", "paragraph": 0,
                  "start": 0.5, "end": 1.5, "words": []},
                 {"id": "s2_01", "clip": "s2", "text": "Two.", "caption": "Two.", "paragraph": 0,
                  "start": 2.5, "end": 3.5, "words": []}]
    t = {"version": 1, "fps": 30, "duration": 4.0, "cues": {},
         "tracks": {"scene": [{"id": "s1", "engine": "remotion", "title": "A", "start": 0.0, "end": 2.0},
                              {"id": "s2", "engine": "remotion", "title": "B", "start": 2.0, "end": 4.0}],
                    "narration": narration, "captions": tl.chunk_captions(narration),
                    "audio": [{"file": "audio/narration.mp3", "start": 0.0}]}}
    tl.save(tmp_path, t)
    return t


def keys(video, t, quality="draft"):
    return {c["id"]: render.clip_key(video, t, c["id"], quality) for c in t["tracks"]["scene"]}


def test_editing_a_chapter_scene_changes_only_that_chapter(tmp_path):
    t = make_video(tmp_path)
    before = keys(tmp_path, t)
    (tmp_path / "scenes" / "s2.tsx").write_text("// s2, edited\n")
    after = keys(tmp_path, t)
    assert after["s1"] == before["s1"] and after["s2"] != before["s2"]


def test_editing_a_shared_scene_file_changes_every_chapter(tmp_path):
    t = make_video(tmp_path)
    before = keys(tmp_path, t)
    (tmp_path / "scenes" / "kit.tsx").write_text("// kit, edited\n")
    after = keys(tmp_path, t)
    assert all(after[c] != before[c] for c in before)


def test_a_caption_change_touches_only_the_clip_it_falls_in(tmp_path):
    t = make_video(tmp_path)
    before = keys(tmp_path, t)
    t2 = copy.deepcopy(t)
    t2["tracks"]["narration"][1]["caption"] = "Two, reworded."
    t2["tracks"]["captions"] = tl.chunk_captions(t2["tracks"]["narration"])
    after = keys(tmp_path, t2)
    assert after["s1"] == before["s1"] and after["s2"] != before["s2"]


def test_quality_is_part_of_the_key(tmp_path):
    t = make_video(tmp_path)
    assert keys(tmp_path, t, "draft")["s1"] != keys(tmp_path, t, "final")["s1"]


def test_latest_cut_ignores_folders_without_a_record(tmp_path):
    for n in (1, 2):
        d = tmp_path / "cuts" / f"cut{n}"
        d.mkdir(parents=True)
        (d / "cut.json").write_text(json.dumps({"cut": n}))
    (tmp_path / "cuts" / "cut3").mkdir()
    assert render.latest_cut(tmp_path) == 2


def test_keys_survive_moving_the_video(tmp_path):
    a = tmp_path / "a"
    a.mkdir()
    t = make_video(a)
    before = keys(a, t)
    b = tmp_path / "b"
    a.rename(b)
    assert keys(b, t) == before


def test_changing_data_rerenders_every_clip(tmp_path):
    t = make_video(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "runs.json").write_text('{"n": 1}')
    before = keys(tmp_path, t)
    (tmp_path / "data" / "runs.json").write_text('{"n": 2}')
    after = keys(tmp_path, t)
    assert all(after[c] != before[c] for c in before)


def test_clips_without_narration_get_stills_at_even_intervals(tmp_path):
    t = make_video(tmp_path)
    t["tracks"]["narration"] = [s for s in t["tracks"]["narration"] if s["clip"] == "s1"]
    reqs = render.still_requests(t, tmp_path)
    s2 = [r for r in reqs if r["clip"] == "s2"]
    assert [r["id"] for r in s2] == ["s2_t01", "s2_t02", "s2_t03"]
    assert all(0 <= r["t"] < 2.0 for r in s2) and [r["id"] for r in reqs if r["clip"] == "s1"] == ["s1_01"]


def test_a_chapter_moved_by_whole_frames_keeps_its_key(tmp_path):
    """A narration edit earlier in the video moves later chapters by whole frames (narration
    CHAPTER_GRID); their frames are the same, so their clips stay cached."""
    t = make_video(tmp_path)
    before = keys(tmp_path, t)
    t2 = copy.deepcopy(t)
    shift = 0.3                                   # 9 frames, 300 ms
    t2["tracks"]["scene"][0]["end"] += shift
    t2["tracks"]["scene"][1]["start"] += shift
    t2["tracks"]["scene"][1]["end"] += shift
    for s in t2["tracks"]["narration"][1:]:
        s["start"] += shift
        s["end"] += shift
    t2["tracks"]["captions"] = tl.chunk_captions(t2["tracks"]["narration"])
    after = keys(tmp_path, t2)
    assert after["s2"] == before["s2"] and after["s1"] != before["s1"]


class StillEngine:
    """Writes a tiny file per requested still and counts them."""
    def __init__(self):
        self.calls = []

    def stills(self, requests):
        self.calls.append(len(requests))
        for r in requests:
            Path(r["out"]).write_bytes(f"{r['clip']} {r['t']}".encode())


def test_stills_are_reused_unless_their_frame_changed(tmp_path):
    t = make_video(tmp_path)
    eng = StillEngine()
    reqs = lambda d: render.still_requests(t, d)
    (tmp_path / "a").mkdir()
    assert render.cached_stills(tmp_path, t, eng, reqs(tmp_path / "a")) == (2, 0)
    (tmp_path / "b").mkdir()
    assert render.cached_stills(tmp_path, t, eng, reqs(tmp_path / "b")) == (0, 2)
    assert (tmp_path / "b" / "s1_01.jpg").read_bytes() == (tmp_path / "a" / "s1_01.jpg").read_bytes()
    (tmp_path / "scenes" / "s2.tsx").write_text("// s2, edited\n")
    (tmp_path / "c").mkdir()
    assert render.cached_stills(tmp_path, t, eng, reqs(tmp_path / "c")) == (1, 1)
