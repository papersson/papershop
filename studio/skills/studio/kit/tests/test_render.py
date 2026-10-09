import copy
import json
import re
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
    (tmp_path / "timeline.json").write_text(json.dumps(t))          # a built timeline, as the engines read it
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


def cue_keys(tmp_path, t, cues):
    return keys(tmp_path, {**t, "cues": cues})


def test_moving_a_cue_no_scene_names_keeps_the_other_clips(tmp_path):
    t = make_video(tmp_path)
    (tmp_path / "scenes" / "s1.tsx").write_text("const { at, cue } = useClip();\n// waits on cue('late') below\n"
                                               "const x = spring(t - cue('chart_up', 0.2));\n")
    before = cue_keys(tmp_path, t, {"chart_up": 1.0, "other": 3.0})
    after = cue_keys(tmp_path, t, {"chart_up": 1.0, "other": 3.2})
    assert after["s1"] == before["s1"] and after["s2"] != before["s2"]      # s2's window holds `other`
    assert cue_keys(tmp_path, t, {"chart_up": 1.1, "other": 3.0})["s1"] != before["s1"]


def test_a_named_cue_outside_the_clip_changes_its_key(tmp_path):
    """An animation started before the clip is still running in it."""
    t = make_video(tmp_path)
    (tmp_path / "scenes" / "s2.js").write_text("export default c => c.P(c.cue(\"early\"), 3)\n")
    before = cue_keys(tmp_path, t, {"early": 0.5})
    after = cue_keys(tmp_path, t, {"early": 0.8})
    assert after["s2"] != before["s2"] and after["s1"] != before["s1"]       # s1 holds it in its window
    assert cue_keys(tmp_path, t, {"early": 0.5, "unused": 0.6})["s2"] == before["s2"]


def test_a_computed_cue_name_reads_every_cue(tmp_path):
    t = make_video(tmp_path)
    for code in ("names.map(n => cue(n))", "cue(`step_${i}`)", "timeline.cues[name]", "const { cue: when } = useClip()"):
        (tmp_path / "scenes" / "kit.tsx").write_text(code + "\n")       # a shared module: every clip
        before = cue_keys(tmp_path, t, {"far": 3.5})
        assert cue_keys(tmp_path, t, {"far": 3.6})["s1"] != before["s1"], code


def test_the_engine_kits_read_cues_only_through_cue():
    """scene_cues scans scene code only; a kit that read timeline cues itself, or called cue() with a
    name a scene passed it, would go unseen."""
    engines = Path(render.__file__).parents[3] / "engines"
    for f in engines.glob("*/src/**/*"):
        if f.suffix not in render.SCENE_CODE:
            continue
        code = render._CODE.sub(lambda m: m.group(1) or re.sub(r"[^\n]", " ", m.group(0)), f.read_text())
        lines = code.splitlines()
        for i, line in enumerate(lines):
            if re.search(r"\.cues\b|\[['\"]cues['\"]\]|\bcue\s*\(", line):
                assert any("cue: (name" in x for x in lines[max(0, i - 2):i + 1]), f"{f}:{i + 1}: {line.strip()}"


def test_a_formats_key_holds_that_formats_caption_lines(tmp_path):
    t = make_video(tmp_path)
    t["tracks"]["captions"][1]["wrapped"] = {"9:16": ["Two."], "1:1": ["Two."]}
    before = {f: keys_in(tmp_path, t, f) for f in ("9:16", "1:1")}
    t["tracks"]["captions"][1]["wrapped"]["9:16"] = ["Two", "lines."]
    assert keys_in(tmp_path, t, "9:16")["s2"] != before["9:16"]["s2"]
    assert keys_in(tmp_path, t, "9:16")["s1"] == before["9:16"]["s1"] and keys_in(tmp_path, t, "1:1") == before["1:1"]


def keys_in(video, t, fmt):
    return {c["id"]: render.clip_key(video, t, c["id"], "draft", fmt=fmt) for c in t["tracks"]["scene"]}
