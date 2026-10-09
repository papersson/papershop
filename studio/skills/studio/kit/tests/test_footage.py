import json

import pytest

from studio_kit import assets, audio, footage
from studio_kit import timeline as tl

WORDS = [{"w": "Hello", "start": 1.0, "end": 1.3}, {"w": "there.", "start": 1.3, "end": 1.7},
         {"w": "Um", "start": 3.0, "end": 3.3}, {"w": "this", "start": 3.4, "end": 3.6}, {"w": "works.", "start": 3.6, "end": 4.0},
         {"w": "Next", "start": 6.0, "end": 6.3}, {"w": "part", "start": 6.3, "end": 6.6}]


def setup(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "talk.mp4").write_bytes(b"x")
    (tmp_path / "footage").mkdir()
    (tmp_path / "footage" / "talk.words.json").write_text(json.dumps(WORDS))
    return tmp_path


def test_sentences_split_at_punctuation_and_long_pauses():
    s = footage.sentences(WORDS)
    assert [" ".join(w["w"] for w in x) for x in s] == ["Hello there.", "Um this works.", "Next part"]


def test_paper_edit_marks_fillers_and_pauses():
    text = footage.paper_edit("talk", WORDS)
    lines = [l for l in text.splitlines() if l[:3].strip().isdigit()]
    assert "~" in lines[1] and "…" in lines[1] and "~" not in lines[0]


def test_edit_list_becomes_a_timeline_with_captions_from_the_footage(tmp_path):
    v = setup(tmp_path)
    t = footage.edit(v, [{"src": "talk", "in": 0.9, "out": 1.8}, {"src": "talk", "in": 2.9, "out": 4.1, "gain": -3}])
    f = t["tracks"]["footage"]
    assert [(x["start"], x["end"]) for x in f] == [(0.0, 0.9), (0.9, 2.1)]
    n = t["tracks"]["narration"]
    assert [s["text"] for s in n] == ["Hello there.", "Um this works."]
    assert n[0]["start"] == 0.1 and n[1]["start"] == 1.0          # mapped onto the new timeline: 0.9 + (3.0 - 2.9)
    assert t["duration"] == 2.1 and t["tracks"]["audio"][1]["gain"] == -3
    assert t["tracks"]["captions"] and t["tracks"]["scene"][0]["end"] == 2.1


def test_the_edit_list_is_kept_and_the_timeline_rebuilds_from_it(tmp_path):
    v = setup(tmp_path)
    edl = [{"src": "talk", "in": 0.9, "out": 1.8}, {"src": "talk", "in": 2.9, "out": 4.1, "gain": -3}]
    t = footage.edit(v, edl)
    assert json.loads((v / "footage" / "edit.json").read_text()) == edl and t["sources"] == ["footage/edit.json"]
    assert {a["role"] for a in t["tracks"]["audio"]} == {"footage"}
    (v / "audio").mkdir()
    (v / "audio" / "tracks.json").write_text(json.dumps([{"file": "assets/bed.wav", "start": 0, "gain": -20}]))
    again = tl.build(v)
    assert again["tracks"]["footage"] == t["tracks"]["footage"] and again["tracks"]["narration"] == t["tracks"]["narration"]
    assert [a["role"] for a in again["tracks"]["audio"]] == ["footage", "footage", "music"]
    with pytest.raises(SystemExit, match="not after"):
        footage.edit(v, [{"src": "talk", "in": 2.0, "out": 1.0}])
    assert json.loads((v / "footage" / "edit.json").read_text()) == edl      # a bad list is not kept


def test_segments_must_run_forward_and_recordings_must_be_ingested(tmp_path):
    v = setup(tmp_path)
    with pytest.raises(SystemExit, match="not after"):
        footage.edit(v, [{"src": "talk", "in": 2.0, "out": 1.0}])
    with pytest.raises(SystemExit, match="no ingested recording"):
        footage.edit(v, [{"src": "other", "in": 0, "out": 1}])


def test_checks_flag_a_kept_filler_and_a_flickering_segment(tmp_path):
    v = setup(tmp_path)
    footage.edit(v, [{"src": "talk", "in": 2.9, "out": 3.2}])
    rows = footage.checks(v)
    bad = {r["check"] for r in rows if not r["ok"]}
    assert {"filler", "cuts", "segments", "sync"} <= bad     # and the fake one-byte recording cannot be probed


def test_mixer_fades_each_cut(tmp_path):
    import subprocess
    (tmp_path / "assets").mkdir()
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=300:duration=4", str(tmp_path / "assets" / "a.wav")], check=True)
    t = {"duration": 2.0, "tracks": {"audio": [{"file": "assets/a.wav", "start": 0, "in": 1.0, "out": 3.0, "fade": 0.05}]}}
    audio.mix(tmp_path, t, tmp_path / "m.m4a")
    first = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(tmp_path / "m.m4a"), "-t", "0.01", "-af", "volumedetect", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
    mid = subprocess.run(["ffmpeg", "-hide_banner", "-ss", "0.5", "-i", str(tmp_path / "m.m4a"), "-t", "0.2", "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    level = lambda s: float(s.split("mean_volume:")[1].split("dB")[0])
    assert level(first) < level(mid) - 3           # the first 10 ms is inside the fade-in (an AAC stream's own priming blurs it)
