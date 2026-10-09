"""timeline.json is built from the files each command owns, and from nothing else."""
import json
from types import SimpleNamespace

import pytest

from studio_kit import align, beats, narration, new, sfx
from studio_kit import timeline as tl
from test_beats import click_track
from test_narration import SCRIPT


def explainer(tmp_path):
    (tmp_path / "SCRIPT.md").write_text(SCRIPT)
    (tmp_path / "video.json").write_text(json.dumps({"title": "T", "engine": "live"}))
    return tmp_path


def read(path):
    return json.loads(path.read_text())


def test_a_narration_keeps_what_other_commands_and_the_builder_added(tmp_path):
    v = explainer(tmp_path)
    narration.narrate(v, estimate=True)
    assert read(v / "audio" / "timings.json")["timing"] == "estimate"
    (v / "cues.json").write_text(json.dumps({"hit": 1.25}))
    (v / "audio" / "tracks.json").write_text(json.dumps([{"file": "assets/bed.wav", "start": 0, "gain": -18}]))
    click_track(tmp_path / "track.wav")
    beats.main(SimpleNamespace(video=v, file=tmp_path / "track.wav"))
    (tmp_path / "fx.json").write_text(json.dumps([{"t": "hit", "type": "click"}, {"t": "beat_2", "type": "pop"}]))
    sfx.main(SimpleNamespace(video=v, cues=tmp_path / "fx.json"))
    assert (v / "audio" / "sfx.wav").exists() and read(v / "audio" / "sfx.json")[0]["t"] == "hit"

    (v / "SCRIPT.md").write_text(SCRIPT.replace("Send a key", "Send one key"))
    narration.narrate(v, estimate=True)
    t = tl.load(v)
    assert t["cues"]["hit"] == 1.25 and t["beats"]["bpm"] and t["timing"] == "estimate"
    assert [(a["file"], a["role"]) for a in t["tracks"]["audio"]] == [
        ("audio/narration.mp3", "narration"), ("assets/bed.wav", "music"), ("audio/sfx.wav", "sfx")]
    assert t["tracks"]["narration"][-1]["caption"] == "Send one key with every attempt."
    assert t["tracks"]["scene"][0]["engine"] == "live"
    assert t["sources"] == ["audio/timings.json", "cues.json", "audio/tracks.json", "audio/sfx.json", "audio/beats.json"]


def test_aligned_words_are_ignored_once_the_narration_changes(tmp_path, monkeypatch, capsys):
    v = explainer(tmp_path)
    narration.narrate(v, estimate=True)
    first = tl.load(v)["tracks"]["narration"][0]
    heard = [{"w": w, "start": first["start"] + 0.3 * i, "end": first["start"] + 0.3 * i + 0.25}
             for i, w in enumerate(first["caption"].split())]
    monkeypatch.setattr(align, "recognise", lambda audio, model: heard)
    align.main(SimpleNamespace(video=v, model="tiny"))
    t = tl.load(v)
    assert [w["start"] for w in t["tracks"]["narration"][0]["words"]] == [round(h["start"], 3) for h in heard]
    assert "audio/words.json" in t["sources"]

    (v / "SCRIPT.md").write_text(SCRIPT.replace("Did the charge go through?", "Did the charge go through at all?"))
    narration.narrate(v, estimate=True)
    t = tl.load(v)
    assert all(not s["words"] for s in t["tracks"]["narration"]) and "audio/words.json" not in t["sources"]
    assert "aligned against an earlier narration; ignored" in capsys.readouterr().out


def test_narration_is_found_by_its_role():
    t = {"tracks": {"audio": [{"file": "assets/bed.wav", "start": 0, "role": "music"},
                              {"file": "audio/voice.mp3", "start": 0, "role": "narration"}]}}
    assert tl.narration_audio(t)["file"] == "audio/voice.mp3"
    assert tl.narration_audio({"tracks": {"audio": [{"file": "audio/sfx.wav", "start": 0}]}}) is None


def test_a_piece_without_narration_takes_its_length_from_video_json(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    v, _ = new.create("reel", directory=str(tmp_path / "reel"), genre="motion", duration=4, engine="motion-canvas")
    assert read(v / "video.json")["duration"] == 4.0
    t = tl.load(v)
    assert t["duration"] == 4.0 and t["sources"] == ["video.json duration"]
    assert t["tracks"]["scene"] == [{"id": "s1", "engine": "motion-canvas", "title": "Reel", "start": 0.0, "end": 4.0}]
    (v / "audio").mkdir()
    (v / "audio" / "tracks.json").write_text(json.dumps([{"file": "assets/song.wav", "start": 0.5}]))
    assert tl.build(v)["tracks"]["audio"] == [{"file": "assets/song.wav", "start": 0.5, "role": "music"}]


def test_nothing_to_build_from_says_what_would_be(tmp_path):
    with pytest.raises(SystemExit, match="narrate the script"):
        tl.build(tmp_path)


def test_cues_must_be_seconds(tmp_path):
    (tmp_path / "video.json").write_text(json.dumps({"duration": 2}))
    (tmp_path / "cues.json").write_text(json.dumps({"hit": "soon"}))
    with pytest.raises(SystemExit, match="hit must be seconds"):
        tl.build(tmp_path)


# A timeline.json from before build: hand cues, a music bed, the sfx render, beats, the audio finish
# and an engine override, all edited into the file itself.
OLD = {"version": 1, "fps": 30, "duration": 4.0, "timing": "narrated",
       "voice": {"engine": "kokoro", "voice": "af_heart"},
       "tracks": {"scene": [{"id": "s1", "engine": "remotion", "title": "A", "start": 0.0, "end": 2.0},
                            {"id": "s2", "engine": "motion-canvas", "title": "B", "start": 2.0, "end": 4.0}],
                  "narration": [{"id": "s1_01", "clip": "s1", "text": "One two.", "caption": "One two.", "paragraph": 0,
                                 "start": 0.5, "end": 1.5, "words": [{"w": "One", "start": 0.5, "end": 0.9},
                                                                      {"w": "two.", "start": 1.0, "end": 1.5}],
                                 "pause": {"seconds": 0.4, "prediction": True, "start": 1.5, "end": 1.9}},
                                {"id": "s2_01", "clip": "s2", "text": "Three.", "caption": "Three.", "paragraph": 0,
                                 "start": 2.5, "end": 3.5, "words": []}],
                  "captions": [], "audio": [{"file": "audio/narration.mp3", "start": 0.0},
                                            {"file": "assets/bed.wav", "start": 0.0, "gain": -20},
                                            {"file": "audio/sfx.wav", "start": 0.0, "gain": -8}]},
       "cues": {"reveal:s1_01": 1.9, "chart_up": 2.75},
       "beats": {"bpm": 120, "beats": [0.5, 1.0], "downbeats": [0.5], "hits": []},
       "audio_finish": {"lufs": -16.0, "stamp": "narration.wav:1:2:-16.0:-1.5"}}


def test_an_old_timeline_is_lifted_into_its_sources_once(tmp_path, capsys):
    (tmp_path / "timeline.json").write_text(json.dumps(OLD))
    (tmp_path / "cues.json").write_text(json.dumps({"mine": 1.0}))           # an existing source wins
    t = tl.build(tmp_path)
    assert "migrated into audio/timings.json" in capsys.readouterr().out
    assert read(tmp_path / "cues.json") == {"mine": 1.0}
    assert read(tmp_path / "audio" / "tracks.json") == [{**OLD["tracks"]["audio"][1], "role": "music"},
                                                       {**OLD["tracks"]["audio"][2], "role": "sfx"}]
    assert read(tmp_path / "audio" / "beats.json") == OLD["beats"]
    assert read(tmp_path / "audio" / "final.json") == OLD["audio_finish"]
    assert read(tmp_path / "audio" / "timings.json")["timing"] == "narrated"
    assert "audio_finish" not in t and t["beats"] == OLD["beats"] and t["voice"] == OLD["voice"]
    assert t["tracks"]["narration"] == OLD["tracks"]["narration"]           # the aligned words survive
    assert t["cues"] == {"mine": 1.0, "reveal:s1_01": 1.9}
    assert [(a["file"], a["role"]) for a in t["tracks"]["audio"]] == [
        ("audio/narration.mp3", "narration"), ("assets/bed.wav", "music"), ("audio/sfx.wav", "sfx")]
    assert {c["engine"] for c in t["tracks"]["scene"]} == {"remotion"}      # the video's engine draws every clip

    (tmp_path / "cues.json").unlink()                 # a built timeline is never migrated again
    assert "chart_up" not in tl.build(tmp_path)["cues"] and not (tmp_path / "cues.json").exists()
    (tmp_path / "audio" / "sfx.json").write_text("[]")
    sounds = [a["file"] for a in tl.build(tmp_path)["tracks"]["audio"]]
    assert sounds.count("audio/sfx.wav") == 1         # studio sfx's own entry replaces the lifted one


def test_an_old_silent_piece_keeps_its_length(tmp_path):
    (tmp_path / "video.json").write_text(json.dumps({"title": "Reel", "genre": "motion"}))
    old = {"version": 1, "fps": 30, "duration": 6.0, "cues": {},
           "tracks": {"scene": [{"id": "s1", "engine": "remotion", "title": "Reel", "start": 0.0, "end": 6.0}],
                      "narration": [], "captions": [], "audio": []}}
    (tmp_path / "timeline.json").write_text(json.dumps(old))
    assert tl.build(tmp_path)["duration"] == 6.0
    assert read(tmp_path / "video.json") == {"title": "Reel", "genre": "motion", "duration": 6.0}


def test_words_aligned_in_place_are_lifted_with_the_current_narration(tmp_path):
    v = explainer(tmp_path)
    narration.narrate(v, estimate=True)
    old = tl.load(v)
    del old["sources"]
    s = old["tracks"]["narration"][0]
    s["words"] = [{"w": w, "start": round(s["start"] + 0.2 * i, 3), "end": round(s["start"] + 0.2 * i + 0.15, 3)}
                  for i, w in enumerate(s["caption"].split())]
    (v / "timeline.json").write_text(json.dumps(old))
    t = tl.build(v)
    assert read(v / "audio" / "words.json")["narration"] == tl.narration_stamp(v)
    assert t["tracks"]["narration"][0]["words"] == s["words"]
