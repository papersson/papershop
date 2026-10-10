"""timeline.json is built from the files each command owns, and from nothing else."""
import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from studio_kit import align, audio, beats, narration, new, sfx
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
    assert t["cues"]["hit"] == round(38 / 30, 6) and t["beats"]["bpm"] and t["timing"] == "estimate"   # frame 37.5 rounds up
    assert [(a["file"], a["role"]) for a in t["tracks"]["audio"]] == [("assets/bed.wav", "music"), ("audio/sfx.wav", "sfx")]
    assert t["tracks"]["narration"][-1]["caption"] == "Send one key with every attempt."
    assert t["tracks"]["scene"][0]["engine"] == "live"
    assert t["sources"] == ["audio/timings.json", "cues.json", "audio/tracks.json", "audio/sfx.json", "audio/beats.json"]


def test_a_re_narration_moves_an_effect_placed_on_its_cue(tmp_path):
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    v = explainer(tmp_path)
    (v / "narration.json").write_text(json.dumps({"holds": {"s1_03": 1.0}}))
    narration.narrate(v, estimate=True)
    cue = "reveal:s1_03"
    (tmp_path / "fx.json").write_text(json.dumps([{"t": cue, "type": "click"}]))
    sfx.main(SimpleNamespace(video=v, cues=tmp_path / "fx.json"))
    onset = lambda: np.argmax(np.abs(sf.read(v / "audio" / "sfx.wav")[0]) > 0.01) / sfx.RATE
    before = tl.load(v)["cues"][cue]
    assert abs(onset() - before) < 0.01

    (v / "SCRIPT.md").write_text(SCRIPT.replace("Then the network goes quiet.", "Then, for a long while, the network goes quiet."))
    narration.narrate(v, estimate=True)
    t = tl.load(v)
    assert t["cues"][cue] > before + 0.3
    audio.sources(v, t)                               # every mix renders the effects against its timeline
    assert abs(onset() - t["cues"][cue]) < 0.01


def test_an_effect_whose_cue_a_re_narration_dropped_stops_the_cut_before_any_render(tmp_path, capsys):
    pytest.importorskip("numpy")
    from studio_kit import render
    v = explainer(tmp_path)
    (v / "narration.json").write_text(json.dumps({"holds": {"s1_03": 1.0}}))
    narration.narrate(v, estimate=True)
    (tmp_path / "fx.json").write_text(json.dumps([{"t": "reveal:s1_03", "type": "click"}]))
    sfx.main(SimpleNamespace(video=v, cues=tmp_path / "fx.json"))
    (v / "narration.json").write_text("{}")                     # the hold, and its reveal cue, are gone
    narration.narrate(v, estimate=True)
    assert "warn: audio/sfx.json: no time for 'reveal:s1_03'" in capsys.readouterr().out

    class Engine:
        def stills(self, reqs):
            raise AssertionError("rendered before the effects were checked")
        render = stills
    with pytest.raises(SystemExit, match="audio/sfx.json: no time for 'reveal:s1_03'"):
        render.make_cut(v, engine=Engine())


def test_an_old_effects_render_plays_when_numpy_is_missing(tmp_path, monkeypatch, capsys):
    """A video from before effects were placed at mix time has audio/sfx.wav and no render key."""
    v = explainer(tmp_path)
    narration.narrate(v, estimate=True)
    (v / "audio" / "sfx.json").write_text(json.dumps([{"t": 1.0, "type": "click"}]))
    (v / "audio" / "sfx.wav").write_bytes(b"an earlier render")

    def no_numpy(*a):
        raise ImportError("numpy")
    monkeypatch.setattr(sfx, "_mix", no_numpy)          # placing needs no numpy; mixing does
    assert sfx.rendered(v, tl.build(v)) == v / "audio" / "sfx.wav"
    assert "effects not re-placed" in capsys.readouterr().out and not (v / ".cache" / "sound" / "sfx.key").exists()
    (v / "audio" / "sfx.wav").unlink()
    with pytest.raises(SystemExit, match="doctor"):
        sfx.rendered(v, tl.build(v))


def test_sfx_stops_on_a_cue_with_no_time(tmp_path):
    v = explainer(tmp_path)
    narration.narrate(v, estimate=True)
    (tmp_path / "fx.json").write_text(json.dumps([{"t": "nowhere", "type": "click"}]))
    with pytest.raises(SystemExit, match="no time for cue"):
        sfx.main(SimpleNamespace(video=v, cues=tmp_path / "fx.json"))
    assert not (v / "audio" / "sfx.json").exists()


def test_an_estimate_lists_no_narration_audio(tmp_path):
    """A narration.mp3 left by an earlier narration would be mixed against the estimate's times."""
    v = explainer(tmp_path)
    (v / "audio").mkdir()
    (v / "audio" / "narration.mp3").write_bytes(b"an earlier narration")
    narration.narrate(v, estimate=True)
    t = tl.load(v)
    assert t["timing"] == "estimate" and tl.narration_audio(t) is None and t["tracks"]["audio"] == []
    with pytest.raises(SystemExit, match="estimate"):
        align.main(SimpleNamespace(video=v, model="tiny"))


def test_a_quiet_build_prints_nothing(tmp_path, capsys):
    v = explainer(tmp_path)
    narration.narrate(v, estimate=True)
    (v / "audio" / "words.json").write_text(json.dumps({"narration": "an older one", "words": []}))
    capsys.readouterr()
    tl.build(v, quiet=True)
    assert capsys.readouterr().out == ""
    tl.build(v)
    assert "ignored" in capsys.readouterr().out


def narrated(v):
    """An estimate passed off as a narration, with audio to align, so no voice need synthesise."""
    timings = read(v / "audio" / "timings.json")
    (v / "audio" / "timings.json").write_text(json.dumps({**timings, "timing": "narrated"}))
    (v / "audio" / "narration.mp3").write_bytes(b"mp3")
    return tl.build(v)


def test_aligned_words_are_ignored_once_the_narration_changes(tmp_path, monkeypatch, capsys):
    v = explainer(tmp_path)
    narration.narrate(v, estimate=True)
    narrated(v)
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
    out = capsys.readouterr().out
    assert "migrated into audio/timings.json" in out
    # the effects lost their cues: nothing said to run studio sfx again
    assert f"to have them follow their cues again, run `studio sfx {tmp_path.resolve()} CUES`" in out
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


# --- what the old kit (before build) left behind, as a first command after the upgrade finds it ----

def old_narrated(v):
    """An old real paragraph-mode narration: timings.json without "timing", the mp3, and a timeline
    from_timings made, with the engine's word times, no roles and no sources."""
    S = narration.Settings(v)
    chapters = narration.sc.load(v)
    timings = narration.layout(S, chapters, narration.estimate_durations(S, chapters))
    for seg in timings["segments"]:
        for ln in seg["lines"]:
            ws, d = ln["caption"].split(), (ln["end"] - ln["start"]) / len(ln["caption"].split())
            ln["words"] = [{"w": w, "start": round(ln["start"] + i * d, 3), "end": round(ln["start"] + (i + 1) * d - 0.01, 3)}
                           for i, w in enumerate(ws)]
    (v / "audio").mkdir(exist_ok=True)
    (v / "audio" / "narration.mp3").write_bytes(b"MP3" * 1000)
    (v / "audio" / "timings.json").write_text(json.dumps(timings, indent=1))
    old_timeline(v, tl.from_timings(timings))


def old_timeline(v, t):
    t.pop("sources", None)
    for a in t["tracks"]["audio"]:
        a.pop("role", None)
    (v / "timeline.json").write_text(json.dumps(t))


def test_a_new_narration_does_not_inherit_the_old_timelines_words(tmp_path, capsys):
    v = explainer(tmp_path)
    old_narrated(v)
    (v / "SCRIPT.md").write_text(SCRIPT.replace("Then the network goes quiet.", "Then, after a long wait, the network goes quiet."))
    narration.narrate(v, estimate=True)
    t = tl.load(v)
    assert not (v / "audio" / "words.json").exists() and "audio/words.json" not in t["sources"]
    assert all(not s["words"] for s in t["tracks"]["narration"]) and "aligned" not in capsys.readouterr().out


def test_an_import_over_an_old_timeline_keeps_the_lessons_own_timing(tmp_path):
    v = explainer(tmp_path)
    old_narrated(v)
    lesson = tmp_path / "lesson"
    (lesson / "audio").mkdir(parents=True)
    (lesson / "audio" / "narration.mp3").write_bytes(b"lesson")
    line = {"id": "s1_01", "text": "Hello.", "caption": "Hello.", "paragraph": 0, "start": 0.8, "end": 1.6}
    (lesson / "audio" / "timings.json").write_text(json.dumps(
        {"total": 3.0, "segments": [{"id": "s1", "title": "Hi", "start": 0.0, "end": 3.0, "lines": [line]}]}))
    t = tl.from_tutor(lesson, v)
    assert [s["caption"] for s in t["tracks"]["narration"]] == ["Hello."] and not t["tracks"]["narration"][0]["words"]
    assert not (v / "audio" / "words.json").exists()


def test_an_old_estimate_after_a_narration_is_the_newer_timing(tmp_path):
    v = explainer(tmp_path)
    old_narrated(v)
    (v / "SCRIPT.md").write_text(SCRIPT.replace("Send a key with every attempt.", "Send a key with every attempt. Keep it for a day."))
    S = narration.Settings(v)
    chapters = narration.sc.load(v)
    estimate = tl.from_timings(narration.layout(S, chapters, narration.estimate_durations(S, chapters)))
    estimate["timing"] = "estimate"
    old_timeline(v, estimate)            # the old --estimate rewrote the timeline and left timings.json
    t = tl.build(v)
    assert t["timing"] == "estimate" and t["duration"] == estimate["duration"]
    assert t["tracks"]["narration"][-1]["caption"] == "Keep it for a day."
    assert read(v / "audio" / "timings.json")["timing"] == "estimate"


def test_an_old_silent_piece_split_into_chapters_keeps_them(tmp_path):
    (tmp_path / "video.json").write_text(json.dumps({"title": "Reel", "genre": "motion", "engine": "remotion"}))
    old_timeline(tmp_path, {"version": 1, "fps": 30, "duration": 6.0, "cues": {}, "tracks": {
        "scene": [{"id": f"s{i + 1}", "engine": "remotion", "title": f"S{i + 1}", "start": 2.0 * i, "end": 2.0 * (i + 1)}
                  for i in range(3)], "narration": [], "captions": [], "audio": []}})
    t = tl.build(tmp_path)
    assert [(c["id"], c["start"], c["end"]) for c in t["tracks"]["scene"]] == [("s1", 0.0, 2.0), ("s2", 2.0, 4.0), ("s3", 4.0, 6.0)]
    assert read(tmp_path / "video.json")["clips"][1] == {"id": "s2", "title": "S2", "seconds": 2.0}
    assert t["sources"] == ["video.json clips"]


def test_clips_and_a_duration_must_agree(tmp_path):
    clips = [{"id": "s1", "seconds": 1.5}, {"id": "s2", "title": "Two", "seconds": 2.25}]
    (tmp_path / "video.json").write_text(json.dumps({"duration": 3.75, "clips": clips}))
    t = tl.build(tmp_path)
    assert t["duration"] == 3.75 and t["tracks"]["scene"][1] == {"id": "s2", "engine": "remotion", "title": "Two",
                                                               "start": 1.5, "end": 3.75}
    (tmp_path / "video.json").write_text(json.dumps({"duration": 4, "clips": clips}))
    with pytest.raises(SystemExit, match="disagree"):
        tl.build(tmp_path)


def test_a_music_bed_named_like_the_narration_is_still_music(tmp_path):
    assert tl.audio_role({"file": "assets/narration-bed.wav"}) == "music"
    assert tl.audio_role({"file": "audio/narration.wav"}) == "narration"
    v = explainer(tmp_path)
    old_narrated(v)
    t = tl.load(v)
    t["tracks"]["audio"].append({"file": "assets/narration-bed.wav", "start": 0.0, "gain": -20})
    (v / "timeline.json").write_text(json.dumps(t))
    assert [a["role"] for a in tl.build(v)["tracks"]["audio"]] == ["narration", "music"]


class StillEngine:
    def stills(self, requests):
        for r in requests:
            Path(r["out"]).write_bytes(b"jpg")


def test_a_cut_builds_the_timeline_first(tmp_path):
    from studio_kit import render
    (tmp_path / "video.json").write_text(json.dumps({"title": "Reel", "duration": 3}))
    tl.build(tmp_path)
    (tmp_path / "cues.json").write_text(json.dumps({"logo": 2.0}))
    rec = render.make_cut(tmp_path, stills_only=True, engine=StillEngine())
    assert tl.load(tmp_path)["cues"] == {"logo": 2.0}
    assert read(tmp_path / "cuts" / f"cut{rec['cut']}" / "timeline.json")["cues"] == {"logo": 2.0}
    from studio_kit import review_state      # what a stale frame review reports as changed is read from these
    assert rec["review_keys"] == review_state.review_keys(tmp_path, tl.load(tmp_path))
    assert rec["source_revision"] == review_state.fingerprint(tmp_path, frames=True)


def test_the_build_wraps_captions_at_each_formats_width_in_layout_json(tmp_path):
    v = explainer(tmp_path)
    (v / "layout.json").write_text(json.dumps({**tl.DEFAULT_LAYOUT, "formats": {"9:16": {"band": {"height": 340, "chars": 20}}}}))
    narration.narrate(v, estimate=True)
    for c in tl.load(v)["tracks"]["captions"]:
        text = " ".join(c["lines"])
        assert c["lines"] == tl.wrap(text, 42) and c["wrapped"]["9:16"] == tl.wrap(text, 20)


def test_the_desk_clocks_an_estimate_silently(tmp_path):
    """An estimate has no narration entry; the first audio entry (music, or effects not yet placed)
    played from its own first sample as the clock."""
    from studio_kit import page
    v = explainer(tmp_path)
    narration.narrate(v, estimate=True)
    (v / "audio" / "tracks.json").write_text(json.dumps([{"file": "assets/bed.wav", "start": 2.0, "in": 5.0}]))
    tl.build(v)
    assert page.state(v)["live"] == {"audio": None, "duration": tl.load(v)["duration"]}
    narrated(v)
    assert page.state(v)["live"]["audio"] == "audio/narration.mp3"


def test_check_rebuilds_an_old_timeline_first(tmp_path):
    """A timeline built before captions were wrapped per format stopped `check --format` with the
    rebuild message."""
    from studio_kit import check
    v = explainer(tmp_path)
    narration.narrate(v, estimate=True)
    old = tl.load(v)
    for c in old["tracks"]["captions"]:
        c.pop("wrapped", None)
    (v / "timeline.json").write_text(json.dumps(old))
    check.main(SimpleNamespace(video=v, samples=1, only="script", format="9:16", all=False))
    assert all("9:16" in c["wrapped"] for c in tl.load(v)["tracks"]["captions"])


def test_an_estimated_video_is_not_finished_published_or_exported_without_its_voice(tmp_path, monkeypatch):
    """Finishing the rest raised effects alone to the target and published a master with no voice."""
    from studio_kit import publish, render
    v = explainer(tmp_path)
    narration.narrate(v, estimate=True)
    click_track(tmp_path / "bed.wav")
    (v / "audio" / "tracks.json").write_text(json.dumps([{"file": str(tmp_path / "bed.wav"), "start": 0}]))
    monkeypatch.setattr(publish, "gate", lambda video: pytest.fail("the refusal comes before the gate"))
    for run in (lambda: audio.main(SimpleNamespace(video=v, lufs=-16.0, peak=-1.5)),
                lambda: publish.build(v), lambda: render.export_formats(v, ["16:9"]),
                lambda: render.make_cut(v, "final", engine=object())):
        with pytest.raises(SystemExit, match=r"no narration in .*estimate.*studio narrate"):
            run()
    assert not (v / "audio" / "final.wav").exists()


def test_a_piece_without_narration_still_finishes_its_music(tmp_path):
    (tmp_path / "video.json").write_text(json.dumps({"title": "M", "genre": "motion", "duration": 3}))
    click_track(tmp_path / "bed.wav")
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "tracks.json").write_text(json.dumps([{"file": str(tmp_path / "bed.wav"), "start": 0}]))
    assert audio.finish(tmp_path, timeline=tl.build(tmp_path)) is not None


def test_a_hand_edit_to_the_timeline_is_reported_when_build_replaces_it(tmp_path, capsys):
    v = explainer(tmp_path)
    narration.narrate(v, estimate=True)
    capsys.readouterr()
    tl.build(v)
    assert "by hand" not in capsys.readouterr().out
    t = tl.load(v)
    t["cues"]["mine"] = 2.0
    (v / "timeline.json").write_text(json.dumps(t))
    tl.build(v, quiet=True)
    out = capsys.readouterr().out
    assert "warn: timeline.json was edited by hand since it was built (cues)" in out and "cues.json" in out
    assert "mine" not in tl.load(v)["cues"]
    tl.build(v)
    assert "by hand" not in capsys.readouterr().out


def test_the_builders_captions_stay_as_written_and_the_kit_chunks_the_rest(tmp_path, monkeypatch, capsys):
    """Every build chunked the captions from the narration, so a hand-made caption was lost at the
    next narrate or align."""
    v = explainer(tmp_path)
    narration.narrate(v, estimate=True)
    kit = tl.load(v)["tracks"]["captions"]
    locked = {**kit[1], "lines": ["Kept exactly", "as the builder wrote it"]}
    custom = {"start": kit[3]["start"], "end": kit[3]["end"], "text": "A caption of the builder's own, wrapped per format"}
    (v / "captions.json").write_text(json.dumps([custom, locked]))
    narrated(v)
    heard = [{"w": w, "start": s["start"] + 0.05 + 0.1 * i, "end": s["start"] + 0.05 + 0.1 * i + 0.08}
             for s in tl.load(v)["tracks"]["narration"] for i, w in enumerate(s["caption"].split())]
    monkeypatch.setattr(align, "recognise", lambda audio, model: heard)
    align.main(SimpleNamespace(video=v, model="tiny"))
    t = tl.load(v)
    assert "captions.json" in t["sources"] and "audio/words.json" in t["sources"]
    caps = t["tracks"]["captions"]
    mine = next(c for c in caps if c["lines"] == locked["lines"])     # its lines, at its words' new times
    assert mine["wrapped"] == locked["wrapped"] and mine["anchor"] == locked["anchor"]
    said = next(s for s in t["tracks"]["narration"] if s["id"] == locked["anchor"]["sentence"])
    assert mine["start"] == said["words"][0]["start"] != locked["start"]
    fixed = next(c for c in caps if c.get("text") == custom["text"])
    assert (fixed["start"], fixed["end"]) == (custom["start"], custom["end"])
    assert fixed["lines"] == tl.wrap(custom["text"], 42) and fixed["wrapped"]["9:16"] == tl.wrap(custom["text"], 26)
    assert all(a["end"] <= b["start"] for a, b in zip(caps, caps[1:]))
    assert "fixed in time" not in capsys.readouterr().out

    (v / "narration.json").write_text(json.dumps({"kokoro": {"speed": 0.6}}))
    narration.narrate(v, estimate=True)
    assert "fixed in time (no anchor) written before the latest narration" in capsys.readouterr().out
    tl.build(v)
    assert "fixed in time" in capsys.readouterr().out            # at every build, until the file is saved again
    os.utime(v / "captions.json", ns=(time.time_ns(), time.time_ns() + 10**9))
    tl.build(v)
    assert "fixed in time" not in capsys.readouterr().out


def test_a_locked_caption_follows_its_words_when_the_narration_moves(tmp_path, capsys):
    """A chunk locked at 2.0-3.93 s kept those times after a slower re-narration, overlapped both its
    own sentence and the one before, and so dropped both phrases without a word."""
    v = explainer(tmp_path)
    narration.narrate(v, estimate=True)
    before = tl.load(v)
    locked = {**before["tracks"]["captions"][1], "lines": ["Then the network", "goes quiet."]}
    (v / "captions.json").write_text(json.dumps([locked]))
    (v / "narration.json").write_text(json.dumps({"kokoro": {"speed": 0.6}}))
    narration.narrate(v, estimate=True)
    t = tl.load(v)
    caps, said = t["tracks"]["captions"], {s["id"]: s for s in t["tracks"]["narration"]}
    mine = next(c for c in caps if c["lines"] == locked["lines"])
    assert mine["start"] == round(said["s1_02"]["start"], 3) > locked["start"]
    shown = [w for c in caps for w in c["anchor"]["text"].split()]
    assert shown == [w for s in t["tracks"]["narration"] for w in s["caption"].split()]     # every word, once, in order
    assert all(a["end"] <= b["start"] for a, b in zip(caps, caps[1:]))
    assert "warn" not in capsys.readouterr().out

    script = (v / "SCRIPT.md").read_text()
    (v / "SCRIPT.md").write_text(script.replace("> A checkout page", "> Here is a shop. A checkout page"))
    narration.narrate(v, estimate=True)                  # the sentences after the new one are renumbered
    mine = next(c for c in tl.load(v)["tracks"]["captions"] if c["lines"] == locked["lines"])
    assert mine["anchor"] == {"sentence": "s1_03", "words": [0, 5], "text": "Then the network goes quiet."}
    (v / "SCRIPT.md").write_text(script.replace("Then the network goes quiet.", "Then nothing comes back."))
    narration.narrate(v, estimate=True)
    caps = tl.load(v)["tracks"]["captions"]
    assert not any(c["lines"] == locked["lines"] for c in caps)
    assert any(c["anchor"]["text"] == "Then nothing comes back." for c in caps)
    assert "no longer matches the narration's words" in capsys.readouterr().out


def test_a_blank_chunk_hides_the_kits_captions_and_bad_chunks_stop_the_build(tmp_path):
    v = explainer(tmp_path)
    narration.narrate(v, estimate=True)
    t = tl.load(v)
    (v / "captions.json").write_text(json.dumps([{"start": 0, "end": t["duration"], "lines": []}]))
    assert [c["lines"] for c in tl.build(v)["tracks"]["captions"]] == [[]]
    for bad in ([{"start": 2, "end": 1, "text": "x"}], [{"start": 0, "end": 1}], [{"start": 0, "end": 1, "lines": "x"}],
                [{"start": 0, "end": 2, "text": "a"}, {"start": 1, "end": 3, "text": "b"}],
                [{"anchor": {"sentence": 3}, "text": "x"}], [{"anchor": {"sentence": "s1_01", "words": [2, 1]}, "text": "x"}],
                [{"start": 0, "end": 1, "text": "x", "wrapped": "x"}], [{"start": 0, "end": 1, "text": "x", "wrapped": {"4:5": ["x"]}}],
                [{"start": 0, "end": 1, "text": "x", "wrapped": {"9:16": "x"}}]):
        (v / "captions.json").write_text(json.dumps(bad))
        with pytest.raises(SystemExit, match="captions.json"):
            tl.build(v)


def test_a_builders_caption_too_long_for_a_format_is_reported(tmp_path, capsys):
    v = explainer(tmp_path)
    narration.narrate(v, estimate=True)
    capsys.readouterr()
    text = "A caption of the builder's own that fits a wide band, not a phone's"
    (v / "captions.json").write_text(json.dumps([{"start": 0.0, "end": 1.0, "text": text}]))
    tl.build(v)
    assert "more than 2 lines in 9:16, 1:1" in capsys.readouterr().out


def test_anchored_cues_resolve_on_the_frame_grid_and_follow_their_words(tmp_path):
    """The beat sheet: cues.json anchors resolve to the time their words are said, on the frame grid,
    and a phrase finds its sentence again after the sentences are renumbered."""
    v = explainer(tmp_path)
    narration.narrate(v, estimate=True)
    (v / "cues.json").write_text(json.dumps({
        "quiet": {"sentence": "s1_02", "phrase": "goes quiet"}, "open": {"sentence": "s1_01", "offset": 0.1},
        "close": {"sentence": "s1_02", "at": "end"}, "net": {"phrase": "the network", "word": 1}, "n": 1.25}))
    t = tl.build(v)
    said = {s["id"]: s for s in t["tracks"]["narration"]}
    grid = lambda x: round(tl.half_up(x * 30) / 30, 6)
    assert t["cues"]["quiet"] == grid(tl.phrase_start(said["s1_02"], "goes quiet"))
    assert t["cues"]["open"] == grid(said["s1_01"]["start"] + 0.1) and t["cues"]["close"] == grid(said["s1_02"]["end"])
    assert t["cues"]["net"] == grid(tl.phrase_start(said["s1_02"], "network"))
    assert all(abs(x * 30 - round(x * 30)) < 1e-4 for x in t["cues"].values())          # every cue on a frame
    assert tl.event_time(t, {"sentence": "s1_02", "phrase": "goes quiet"}) == t["cues"]["quiet"]
    assert sfx._time("quiet", t) == sfx._time({"phrase": "goes quiet"}, t) == t["cues"]["quiet"]   # one time for picture and sound

    script = (v / "SCRIPT.md").read_text()
    (v / "SCRIPT.md").write_text(script.replace("> A checkout page", "> Here is a shop. A checkout page"))
    narration.narrate(v, estimate=True)                  # s1_02 is now "A checkout page ...", s1_03 the quiet one
    t = tl.load(v)
    said = {s["id"]: s for s in t["tracks"]["narration"]}
    assert t["cues"]["quiet"] == grid(tl.phrase_start(said["s1_03"], "goes quiet"))
    assert t["cues"]["close"] == grid(said["s1_02"]["end"])                              # an id alone keeps its id
    rows = {r["name"]: r for r in tl.events(v)}
    assert rows["quiet"]["anchor"] == "s1_02 at 'goes quiet' (now s1_03)" and rows["n"]["anchor"] == "seconds"
    assert [r["time"] for r in tl.events(v)] == sorted(t["cues"].values())

    (v / "SCRIPT.md").write_text(script.replace("Then the network goes quiet.", "Then nothing comes back."))
    with pytest.raises(SystemExit, match="cue 'quiet' has no time: no sentence says 'goes quiet' any more"):
        narration.narrate(v, estimate=True)


@pytest.mark.parametrize("spec,error", [
    ({"sentence": "s1_01", "at": "word"}, "needs a word index"), ({"at": "start"}, "needs a sentence id or a phrase"),
    ({"sentence": "s1_01", "at": "middle"}, "at must be one of"), ({"sentence": "s1_01", "offset": "1"}, "offset must be seconds"),
    ({"sentence": "s1_01", "when": 1}, "must be seconds or an anchor"), ({"sentence": "s9_01"}, "no sentence s9_01"),
    ({"phrase": "the"}, "'the' is said in s1_01, s1_02"), ({"sentence": "s1_01", "word": 40}, "s1_01 has 8 words, no word 40"),
])
def test_a_bad_or_lost_anchor_stops_the_build_naming_the_cue(tmp_path, spec, error):
    v = explainer(tmp_path)
    narration.narrate(v, estimate=True)
    (v / "cues.json").write_text(json.dumps({"hit": spec}))
    with pytest.raises(SystemExit, match=f"cues.json: (the cue 'hit'|hit) .*{error}"):
        tl.build(v)


def test_an_anchored_cue_counts_only_for_the_clips_that_read_it(tmp_path):
    from studio_kit import render
    v = explainer(tmp_path)
    narration.narrate(v, estimate=True)
    (v / "scenes").mkdir()
    (v / "scenes" / "s2.js").write_text("export default c => c.P(c.cue('quiet'), 0.4)\n")
    keys = lambda t: {c["id"]: render.clip_key(v, t, c["id"], "draft") for c in t["tracks"]["scene"]}
    (v / "cues.json").write_text(json.dumps({"quiet": {"sentence": "s1_02", "phrase": "goes quiet"}}))
    before = keys(tl.build(v))
    (v / "cues.json").write_text(json.dumps({"quiet": {"sentence": "s1_02", "phrase": "goes quiet", "offset": 0.2}}))
    after = keys(tl.build(v))
    assert after["s2"] != before["s2"]           # s2 waits on it from the chapter before
    assert after["s1"] != before["s1"]           # and it lies inside s1's frames
    (v / "cues.json").write_text(json.dumps({"quiet": {"sentence": "s1_02", "phrase": "goes quiet", "offset": 0.2},
                                             "unread": {"sentence": "s2_01", "at": "end", "offset": 10}}))
    assert keys(tl.build(v)) == after            # past the end, read by no scene


def test_every_anchor_error_names_its_cue_and_says_why(tmp_path):
    v = explainer(tmp_path)
    narration.narrate(v, estimate=True)
    (v / "cues.json").write_text(json.dumps({"quiet": {"sentence": "s1_02", "phrase": "GOES  quiet"}}))
    assert tl.build(v)["cues"]["quiet"] > 0                       # another case and spacing, on an estimate
    t = tl.load(v)
    with pytest.raises(SystemExit, match=r"no time for cue .*'at': 'middle'.*: at must be one of"):
        sfx.resolve_time({"sentence": "s1_01", "at": "middle"}, t)
    with pytest.raises(SystemExit, match="no sentence says 'never said' any more"):
        sfx.check([{"t": {"phrase": "never said"}, "type": "click"}], t)
    assert sfx.unresolved([{"t": {"phrase": "never said"}}], t) == [{"phrase": "never said"}]
