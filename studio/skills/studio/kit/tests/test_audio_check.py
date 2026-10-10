import json
import subprocess
from types import SimpleNamespace

import pytest

from studio_kit import audio, audio_check, check
from studio_kit import timeline as tl

np = pytest.importorskip("numpy")
sf = pytest.importorskip("soundfile")


def narrated(tmp_path, effects=(), bed_gain=None, sound=None):
    """A narrated video by hand: four sentences of three words each (speech-like bursts at 0, 3, 6 and
    9 s), a cue in the first pause, optional effects and a bed."""
    from test_audio import speech
    v = tmp_path / "v"
    (v / "audio").mkdir(parents=True)
    (v / "video.json").write_text(json.dumps({"title": "x", "genre": "motion", **({"sound": sound} if sound else {})}))
    speech(v / "audio" / "narration.wav", seconds=10.5)
    narration = [{"id": f"s{i}", "clip": "a", "text": "one two three", "caption": "one two three", "start": 3.0 * i,
                  "end": 3.0 * i + 1.5, "words": [{"w": w, "start": 3.0 * i + 0.5 * k, "end": 3.0 * i + 0.5 * k + 0.45}
                                                   for k, w in enumerate(("one", "two", "three"))]} for i in range(4)]
    t = {"version": 1, "fps": 30, "duration": 10.5, "timing": "narrated",
         "tracks": {"scene": [{"id": "a", "engine": "remotion", "title": "A", "start": 0.0, "end": 10.5}],
                    "narration": narration, "captions": [],
                    "audio": [{"file": "audio/narration.wav", "start": 0.0, "role": "narration"}]},
         "cues": {"hit": 2.0, "inword": 3.5}}
    if bed_gain is not None:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=10.5:sample_rate=48000",
                        "-f", "lavfi", "-i", "sine=frequency=2000:duration=10.5:sample_rate=48000", "-filter_complex",
                        "amix=inputs=2:normalize=0", str(v / "bed.wav")], check=True)
        t["tracks"]["audio"].append({"file": "bed.wav", "start": 0.0, "gain": bed_gain, "role": "music"})
    if effects:
        (v / "audio" / "sfx.json").write_text(json.dumps(list(effects)))
        t["tracks"]["audio"].append(dict(tl.SFX))
    (v / "timeline.json").write_text(json.dumps(t))
    return v


def rows_of(rows, name):
    return [r for r in rows if r["check"] == name]


def test_an_effect_in_a_pause_is_in_sync_and_passes_the_guard(tmp_path):
    v = narrated(tmp_path, [{"t": "hit", "type": "pop"}, {"t": 5.0, "type": "click"}], bed_gain=-12)
    rows, _ = audio_check.run(v)
    sync = rows_of(rows, "sync")
    assert len(sync) == 1 and abs(sync[0]["offset_frames"]) <= 1 and "severity" not in sync[0]      # the click at 5.0 s names no event
    assert rows_of(rows, "pauses") == [{"check": "pauses", "clip": "audio", "ok": True,
                                        "detail": "no effect over -24 dBFS under any of 12 spoken words"}]
    duck = rows_of(rows, "ducking")[0]
    assert duck["duck_db"] > audio_check.DUCK_MIN and "severity" not in duck
    loud = rows_of(rows, "loudness")[0]
    assert abs(loud["lufs"] + 16) < 0.5 and loud["true_peak_dbtp"] <= -1.45
    assert rows_of(rows, "masking")[-1]["detail"].endswith("words clear by 10 dB in 1-4 kHz")


def test_a_loud_effect_on_a_word_fails_and_a_quiet_one_does_not(tmp_path, monkeypatch):
    v = narrated(tmp_path, [{"t": "inword", "type": "thump"}, {"t": 6.6, "type": "soft-tick", "gain": -40}])
    rows, _ = audio_check.run(v)
    bad = [r for r in rows if not r["ok"]]
    assert bad and {r["check"] for r in bad} == {"pauses"} and all(3.0 <= r["t"] < 4.5 for r in bad)
    assert "'two'" in bad[0]["detail"]
    assert check.run(v, only=["pauses"]) == audio_check.guard(v)            # `studio check` reports the same rows
    monkeypatch.setattr(tl, "build", lambda *a, **k: None)      # the timeline is made by hand, not from sources
    assert audio_check.main(SimpleNamespace(video=v, cut=None)) == 1
    report = json.loads((v / "out" / "audio-check.json").read_text())
    assert report["thresholds"]["pause_peak_dbfs"] == -24.0 and any(not r["ok"] for r in report["rows"])


def test_an_undocked_loud_bed_warns_on_ducking_and_masking(tmp_path):
    v = narrated(tmp_path, bed_gain=6, sound={"duck": False, "presence": False})
    rows, _ = audio_check.run(v)
    assert rows_of(rows, "ducking")[0]["severity"] == "warning"
    assert rows_of(rows, "masking")[-1]["severity"] == "warning" and len(rows_of(rows, "masking")) > 1
    assert all(r["ok"] for r in rows)


def test_sync_warns_when_the_sound_is_off_its_frame():
    class Stems:
        roles = {"sfx"}

        def __getitem__(self, role):
            y = np.zeros(4 * 48_000, "float32")
            y[int(2.1 * 48_000):int(2.1 * 48_000) + 400] = 0.5            # three frames late
            return y
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "audio").mkdir()
        (Path(d) / "audio" / "sfx.json").write_text(json.dumps([{"t": "hit", "type": "click"}]))
        rows = audio_check.sync(Stems(), d, {"fps": 30, "cues": {"hit": 2.0}})
    assert rows[0]["severity"] == "warning" and abs(rows[0]["offset_frames"] - 3) < 0.1


def test_the_guard_waits_for_a_voice_and_skips_a_video_without_effects(tmp_path):
    v = narrated(tmp_path)
    assert audio_check.guard(v) == [] and check.run(v, only=["pauses"]) == []
    t = json.loads((v / "timeline.json").read_text())
    (v / "audio" / "sfx.json").write_text(json.dumps([{"t": "hit", "type": "pop"}]))
    (v / "timeline.json").write_text(json.dumps({**t, "timing": "estimate"}))
    assert audio_check.guard(v)[0]["skipped"]


def test_the_full_check_runs_the_guard_when_there_are_effects(tmp_path, monkeypatch):
    """publish's gate is the full check, so this is how publish stops on a loud effect under a word."""
    v = narrated(tmp_path, [{"t": "hit", "type": "pop"}])
    called = []
    monkeypatch.setattr(audio_check, "guard", lambda video: called.append(video) or [])

    def no_engine(*a, **k):
        raise RuntimeError("the engine checks come next")
    monkeypatch.setattr(check, "Engine", no_engine)
    with pytest.raises(RuntimeError):
        check.run(v)
    assert called == [v]


def test_the_picture_note_finds_where_motion_starts(tmp_path):
    v = narrated(tmp_path)
    (v / "layout.json").write_text(json.dumps(tl.DEFAULT_LAYOUT))
    movie = tmp_path / "cut.mp4"
    # a box on a still background that moves from frame 63 on (the first frame of the file that differs)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=640x360:d=4:r=30", "-f", "lavfi",
                    "-i", "color=c=white:s=120x120:d=4:r=30", "-filter_complex", "[0][1]overlay=x='if(gte(n,64),(n-63)*12,0)':y=40",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(movie)], check=True)
    assert audio_check._picture(v, {"fps": 30}, 60, movie) == (63, "starts")
    assert audio_check._picture(v, {"fps": 30}, 20, movie) is None


def test_an_effect_from_tracks_json_is_guarded_too(tmp_path):
    """The guard ran only with audio/sfx.json, so a hit in tracks.json at +1 dBFS under a word passed check."""
    from studio_kit import sfx
    v = narrated(tmp_path)
    sfx.write_wav(v / "hit.wav", sfx.voice("thump"))
    t = json.loads((v / "timeline.json").read_text())
    t["tracks"]["audio"].append({"file": "hit.wav", "start": 3.5, "role": "sfx"})
    (v / "timeline.json").write_text(json.dumps(t))
    rows = audio_check.guard(v)
    assert rows and not rows[0]["ok"] and check.run(v, only=["pauses"]) == rows


def test_the_guard_names_the_overlap_and_its_level_there(tmp_path):
    """It said "peaks at 0.7 dBFS under the word 'into' (8.37-8.61 s)" for a thump starting at 8.60."""
    v = narrated(tmp_path, [{"t": 4.40, "type": "thump"}])       # the word 'three' runs 4.0-4.45
    (bad,) = audio_check.guard(v)
    x, y = bad["overlap"]
    assert abs(x - 4.40) < 0.01 and abs(y - 4.45) < 0.01 and bad["t"] == 4.4
    assert "for 4.400-4.450 s (50 ms) of the word 'three' (4.00-4.45 s)" in bad["detail"]
    assert "at the master's gain, before its limiter" in bad["detail"] and bad["peak_dbfs"] > audio_check.PAUSE_PEAK


def test_the_guard_keeps_the_target_the_mix_was_finished_to(tmp_path):
    """After `export --lufs -14`, the next check re-finished final.wav at -16."""
    v = narrated(tmp_path, [{"t": "hit", "type": "pop"}])
    audio.finish(v, -14.0, timeline=tl.load(v))
    audio_check.guard(v)
    assert json.loads((v / "audio" / "final.json").read_text())["target_lufs"] == -14.0
    rows, _ = audio_check.run(v)
    assert abs([r for r in rows if r["check"] == "loudness"][0]["lufs"] + 14) < 0.5


def test_a_piece_with_no_narration_has_nothing_to_guard(tmp_path):
    v = narrated(tmp_path, [{"t": 1.0, "type": "pop"}])
    t = json.loads((v / "timeline.json").read_text())
    t["tracks"]["narration"] = []
    t["tracks"]["audio"] = t["tracks"]["audio"][1:]
    (v / "timeline.json").write_text(json.dumps(t))
    assert audio_check.guard(v) == []


def test_the_picture_note_names_a_cut(tmp_path):
    from test_motion import gray_clip, picture
    v = narrated(tmp_path)
    (v / "layout.json").write_text(json.dumps(tl.DEFAULT_LAYOUT))
    movie = tmp_path / "cut.mp4"
    gray_clip(movie, picture())
    assert audio_check._picture(v, {"fps": 30}, 47, movie) == (45, "cut")
    assert audio_check._picture(v, {"fps": 30}, 15, movie) == (10, "starts")
    assert audio_check._picture(v, {"fps": 30}, 22, movie) == (20, "ends")
    assert audio_check._picture(v, {"fps": 30}, 80, movie) is None



# --- a recording timed by its peak, and every effect heard ------------------------------------------

import io  # noqa: E402

from studio_kit import soundkit  # noqa: E402
from test_sfx_kit import kit  # noqa: E402,F401  (the sound kit fixture: two recordings with a lead-in)


class Stem:
    """Stems by hand: an effects stem and nothing else."""
    roles = {"sfx"}

    def __init__(self, y):
        self.y = y

    def __getitem__(self, role):
        return self.y

    def span(self, role, a, b):
        return self.y[max(0, int(a * 48_000)):max(0, int(b * 48_000))] if role == "sfx" else np.zeros(max(0, int((b - a) * 48_000)), "float32")


def test_a_recording_is_timed_by_its_peak_not_its_lead_in(kit, tmp_path):
    """knock-late swells for 80 ms before its peak: placed with its peak on the event, its onset is
    two frames early, and sync, timing a recording by its peak, finds it on the frame."""
    from studio_kit import sfx
    v = tmp_path / "v"
    (v / "audio").mkdir(parents=True)
    cue = {"t": "hit", "type": "tap", "sound": "kit:knock-late"}
    (v / "audio" / "sfx.json").write_text(json.dumps([cue]))
    timeline = {"fps": 30, "duration": 4.0, "cues": {"hit": 2.0}, "beats": {}}
    p = sfx.place([cue], timeline)[0]
    y = np.zeros(4 * 48_000, "float32")
    soundkit.fetch_kit(progress=io.StringIO())
    s = sfx.resolve(cue)                                         # samples from the verified kit (no video here)
    y[p.start:p.start + s.length] = s.samples
    assert (audio_check._onset(y, 2.0, "start") - 2.0) * 30 < -1.5
    (row,) = audio_check.sync(Stem(y), v, timeline)
    assert abs(row["offset_frames"]) < 0.2 and "severity" not in row and "timed by its peak" in row["detail"]
    late = np.roll(y, int(0.1 * 48_000))                         # placed three frames late
    assert abs(audio_check.sync(Stem(late), v, timeline)[0]["offset_frames"] - 3) < 0.2


def noise_bed(v, gain):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    "anoisesrc=color=pink:duration=10.5:sample_rate=48000:amplitude=0.5:seed=1", str(v / "bed.wav")], check=True)
    t = json.loads((v / "timeline.json").read_text())
    t["tracks"]["audio"].append({"file": "bed.wav", "start": 0.0, "gain": gain, "role": "music"})
    (v / "timeline.json").write_text(json.dumps(t))
    return v


@pytest.mark.parametrize("case, effect, bed, warns", [
    ("a clear effect in a pause", {"gain": 0}, None, None),
    ("an effect buried under a loud bed", {"gain": -7}, 0, "masked"),
    ("an effect at -60 dBFS in silence", {"gain": -51}, None, "too quiet"),
])
def test_each_effect_is_heard_or_warned(tmp_path, case, effect, bed, warns):
    """The calibration: a pop in the first pause, alone (lifts silence, about 1 dB under the voice), under
    an undocked pink-noise bed at full gain (lifts it under 1 dB), and 44 dB down (peaking near -60
    dBFS, 45 dB under the voice). The "sound layer" we studied passed the last one. (This stand-in voice
    is 7 dB louder than Kokoro's and the effects follow it, so the last two take 7 dB off their gains.)"""
    v = narrated(tmp_path, [{"t": "hit", "type": "pop", **effect}], sound={"duck": False, "presence": False})
    if bed is not None:
        noise_bed(v, bed)
    t = tl.load(v)
    (row,) = rows_of(audio_check.audibility(audio_check.Stems(v, t, audio_check.finished(v, t)), v, t), "audible")
    assert row["check"] == "audible" and row["t"] == 2.0 and row["ok"]
    if warns is None:
        assert "severity" not in row and row["lift_db"] >= audio_check.AUDIBLE_LIFT and row["under_voice_db"] < 5, row
    else:
        assert row["severity"] == "warning" and warns in row["detail"], row
    if warns == "masked":
        assert row["lift_db"] < 2
    if warns == "too quiet":
        assert row["level_dbfs"] < -55 and row["lift_db"] == 99.0


def test_the_report_carries_the_audibility_thresholds(tmp_path, monkeypatch):
    v = narrated(tmp_path, [{"t": "hit", "type": "pop"}])
    monkeypatch.setattr(tl, "build", lambda *a, **k: None)
    audio_check.main(SimpleNamespace(video=v, cut=None))
    report = json.loads((v / "out" / "audio-check.json").read_text())
    assert report["thresholds"]["audible_lift_db"] == audio_check.AUDIBLE_LIFT
    assert [r["check"] for r in report["rows"]].count("audible") == 1


# --- picture tags, the loud audit, the sheet and the listening timecodes ------------------------------

def tagged_at(movie, frame, visual, fps=30, seams=()):
    from studio_kit import motion
    sig = motion.frame_signal(movie, tl.DEFAULT_LAYOUT, fps, max(0, frame - audio_check.PICTURE_WINDOW),
                              2 * audio_check.PICTURE_WINDOW + 1)
    return audio_check._judged(sig, frame, visual, fps, list(seams))


@pytest.mark.parametrize("frame, visual, mark, ok", [
    (15, "move", 15, True),         # the box is fastest into frame 15
    (11, "move", 15, False),        # four frames early: past the three a move allows
    (10, "appear", 10, True),
    (12, "appear", 10, True),       # two frames: an ease's first frames change by little
    (7, "appear", 10, False),
    (21, "land", 20, True),
    (47, "cut", 45, False),         # two frames from the cut: a cut allows one
    (46, "cut", 45, True),
])
def test_a_tagged_effect_is_judged_against_its_picture(tmp_path, frame, visual, mark, ok):
    from test_motion import gray_clip, picture
    movie = tmp_path / "cut.mp4"
    gray_clip(movie, picture())
    got = tagged_at(movie, frame, visual)
    assert (got["picture_frame"], got["picture_offset_frames"], got["picture_ok"]) == (mark, mark - frame, ok), got
    assert ("within" in got["picture"]) == ok


def test_a_cut_on_one_background_counts_at_a_clip_seam_only(tmp_path):
    """Two scenes on one background change only where their content differs (well under CUT_SHARE),
    which reads as motion starting: a `cut` tag takes it where the timeline has a seam, and nowhere else."""
    from test_motion import gray_clip
    w, h = 384, 216

    def frame(x):
        rows = [bytearray(w) for _ in range(h)]
        for r in rows[60:100]:
            r[x:x + 40] = bytes([255]) * 40
        return bytes(b"".join(rows))
    movie = tmp_path / "seam.mp4"
    gray_clip(movie, [frame(20)] * 45 + [frame(300)] * 45)
    on_seam = tagged_at(movie, 45, "cut", seams=[45])
    assert on_seam["picture_ok"] and on_seam["picture_frame"] == 45 and "one background" in on_seam["picture"]
    off_seam = tagged_at(movie, 45, "cut")
    assert not off_seam["picture_ok"] and "no cut within" in off_seam["picture"]


def test_sync_judges_a_tagged_effect_and_notes_an_untagged_one(tmp_path):
    from test_motion import gray_clip, picture
    v = narrated(tmp_path)
    (v / "layout.json").write_text(json.dumps(tl.DEFAULT_LAYOUT))
    movie = tmp_path / "cut.mp4"
    gray_clip(movie, picture())
    cues = [{"t": "hit", "type": "thump", "visual": "land"}, {"t": "late", "type": "pop"}, {"t": 1.0, "type": "pop", "visual": "appear"},
            {"t": 2.5, "type": "click"}]
    (v / "audio" / "sfx.json").write_text(json.dumps(cues))
    y = np.zeros(4 * 48_000, "float32")
    for at in (0.7, 1.0, 1.5):
        y[int(at * 48_000):int(at * 48_000) + 400] = 0.5
    timeline = {"fps": 30, "duration": 4.0, "cues": {"hit": 0.7, "late": 1.5}, "beats": {},
                "tracks": {"scene": [{"id": "a", "start": 0.0, "end": 1.5}, {"id": "b", "start": 1.5, "end": 4.0}]}}
    rows = audio_check.sync(Stem(y), v, timeline, movie)
    assert [r["effect"] for r in rows] == ["fx1", "fx2", "fx3"]          # fx4 is at seconds and untagged: no row
    land, untagged, appear = rows
    assert (land["picture_frame"], land["picture_offset_frames"], land["picture_ok"]) == (20, -1, True)
    assert "picture (land): motion ends at frame 20 (-1), within 2" in land["detail"] and "severity" not in land
    assert "picture: a cut at frame 45" in untagged["detail"] and "picture_ok" not in untagged
    assert appear["picture_ok"] is False and appear["severity"] == "warning" and appear["picture_frame"] == 10
    assert "picture (appear): motion starts at frame 10 (-20), more than 2 frames off" in appear["detail"]     # found up to 1 s away
    rows = audio_check.sync(Stem(y), v, timeline)                       # no cut: a tag is not judged
    assert "picture (land) not judged: no rendered cut" in rows[0]["detail"] and "severity" not in rows[0]


def test_sfx_takes_only_a_known_visual_tag():
    from studio_kit import sfx
    t = {"fps": 30, "duration": 4.0, "cues": {"hit": 1.0}, "beats": {}}
    sfx.check([{"t": "hit", "type": "pop", "visual": "appear"}], t)
    with pytest.raises(SystemExit, match="visual must be one of cut"):
        sfx.check([{"t": "hit", "type": "pop", "visual": "pop"}], t)


@pytest.mark.parametrize("effect, gain, loud", [("thump", 0, False), ("pop", 0, False), ("click", 10, True), ("thump", 10, True)])
def test_the_loud_audit_warns_an_effect_well_over_the_voice(tmp_path, effect, gain, loud):
    """The synth voices at gain 0, which the kit's trims match, pass, the loudest (thump) too; +10 dB warns.
    This stand-in voice is 7 dB louder than Kokoro's; the effects follow it, so the verdicts are Kokoro's."""
    v = narrated(tmp_path, [{"t": "hit", "type": effect, "gain": gain}])
    t = tl.load(v)
    rows = audio_check.audibility(audio_check.Stems(v, t, audio_check.finished(v, t)), v, t)
    (row,) = rows_of(rows, "loud")
    assert (row.get("severity") == "warning") == loud, row
    if loud:
        assert row["effect"] == "fx1" and row["over_loudness_db"] > audio_check.LOUD_OVER and row["against"] == "voice"
    else:
        assert row["detail"].startswith("no effect more than 13.5 dB over the voice's loudness; the loudest, fx1")


def test_the_heroes_and_the_listening_timecodes():
    found = [{"id": "fx1", "type": "pop", "t": 2.0, "event": True, "flags": [], "over": -4.0},
             {"id": "fx2", "type": "thump", "t": 5.0, "visual": "land", "event": True, "flags": ["PICTURE"], "over": 2.0},
             {"id": "fx3", "type": "click", "t": 8.0, "event": False, "flags": [], "over": 3.5},
             {"id": "fx4", "type": "chime", "t": 9.6, "visual": "appear", "event": True, "flags": [], "over": -9.0}]
    assert [e["id"] for e in audio_check.heroes(found)] == ["fx3", "fx2", "fx4"]       # the tagged two and the loudest
    rows = [{"check": "sync", "effect": "fx2", "visual": "land", "t": 5.0, "picture_ok": False, "picture_offset_frames": 4},
            {"check": "sync", "effect": "fx4", "visual": "appear", "t": 9.6, "picture_ok": True, "picture_offset_frames": 1},
            {"check": "masking", "detail": "", "closest": {"word": "two", "t": 3.5, "margin_db": 7.2}}]
    timeline = {"tracks": {"audio": [{"file": "bed.wav", "start": 0.0, "role": "music"}]}}
    got = audio_check.listening(found, rows, timeline)
    assert [m["at"] for m in got] == ["0:00.0", "0:03.5", "0:05.0", "0:08.0", "0:09.6"]
    by = {m["at"]: m["reasons"] for m in got}
    assert by["0:05.0"] == ["fx2 (land) is the tagged effect furthest from its picture: +4 frames", "hero effect fx2 thump (land) (PICTURE)"]
    assert by["0:08.0"][0] == "the loudest effect, fx3 click: +3.5 dB against the voice's loudness"
    assert by["0:00.0"] == ["the music's first entry"] and by["0:03.5"][0].startswith("the closest masking margin")
    assert audio_check.timecode(75.25) == "1:15.2" and audio_check.timecode(59.96) == "1:00.0"


def test_audio_check_draws_the_sheet_and_offers_timecodes_for_this_mix(tmp_path, monkeypatch, capsys):
    from studio_kit import sound_sheet
    v = narrated(tmp_path, [{"t": "hit", "type": "pop", "visual": "appear"}, {"t": 5.0, "type": "click"}], bed_gain=-12)
    monkeypatch.setattr(tl, "build", lambda *a, **k: None)
    audio_check.main(SimpleNamespace(video=v, cut=None))
    report = json.loads((v / "out" / "audio-check.json").read_text())
    assert report["heroes"] == ["fx2", "fx1"]          # the tagged one and the loudest, loudest first
    assert report["sheets"] == ["out/audio-sheet.png", "out/audio-sheet/fx2.png", "out/audio-sheet/fx1.png"]
    for f in report["sheets"]:
        info = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(v / f)],
                              capture_output=True, text=True, check=True).stdout.strip()
        assert info.split(",")[1] == str(sound_sheet.height())
    assert [e["id"] for e in report["effects"]] == ["fx1", "fx2"] and report["effects"][0]["visual"] == "appear"
    assert report["soundtrack"] == audio.revision(v) and report["listen"] == audio_check.moments(v)
    assert audio.soundtrack(v, tl.load(v)).name in report["sounds"]        # what a cut's record calls this sound
    assert any("hero effect fx1 pop (appear)" in why for m in report["listen"] for why in m["reasons"])
    out = capsys.readouterr().out
    assert "sound sheet: out/audio-sheet.png" in out and "listen at:\n  0:0" in out
    assert audio_check.listen_hint(v).startswith("at 0:0")
    (v / "video.json").write_text(json.dumps({"title": "x", "genre": "motion", "sound": {"room": 0}}))     # another mix
    assert audio_check.moments(v) is None and audio_check.listen_hint(v, '"$VIDEO"') == \
        'run `studio audio-check "$VIDEO"` first for the timecodes to listen at'


def test_a_pauses_failure_prints_a_short_overlap_as_it_is():
    """A 2 ms overlap printed "15.70-15.70 s"."""
    v_t = {"tracks": {"narration": [{"caption": "word", "start": 1.0, "end": 1.5, "words": [{"w": "word", "start": 1.0, "end": 1.5}]}]}}
    y = np.zeros(48_000 * 2, "float32")
    y[int(1.4985 * 48_000):int(1.5005 * 48_000)] = 0.5
    (bad,) = audio_check.pauses(Stem(y), v_t)
    assert "for 1.498-1.500 s (2 ms) of the word 'word'" in bad["detail"], bad["detail"]


def test_a_stale_cut_is_read_where_it_put_the_event_and_says_so(tmp_path):
    """Moving a cue after the cut gave a picture warning with no hint that the cut was stale: the
    picture is read at the frame the cut's own timeline put the event on, and the row says it moved."""
    from test_motion import gray_clip, picture
    v = narrated(tmp_path, [{"t": "hit", "type": "pop", "visual": "appear"}])
    (v / "layout.json").write_text(json.dumps(tl.DEFAULT_LAYOUT))
    d = v / "cuts" / "cut1"
    d.mkdir(parents=True)
    pic = picture()
    gray_clip(d / "video.mp4", pic + [pic[-1]] * (315 - len(pic)))
    t = json.loads((v / "timeline.json").read_text())
    t["cues"]["hit"] = 2.0
    (d / "timeline.json").write_text(json.dumps(t))
    (d / "cut.json").write_text(json.dumps({"kind": "cut", "video": "video.mp4"}))
    (v / "timeline.json").write_text(json.dumps(t))
    (row,) = rows_of(audio_check.run(v)[0], "sync")
    assert row["picture_ok"] and "cut_frame" not in row and "older than the sources" not in row["detail"], row["detail"]
    t["cues"]["hit"] = 2.5
    (v / "timeline.json").write_text(json.dumps(t))
    (row,) = rows_of(audio_check.run(v)[0], "sync")
    assert row["frame"] == 75 and row["cut_frame"] == 60 and row["picture_ok"], row["detail"]
    assert "the cut is older than the sources: it shows this cue at frame 60, the timeline has it at frame 75" in row["detail"]


def test_without_narration_the_effects_are_measured_against_the_music(tmp_path):
    """A thump at +20 dB in a music-only piece passed every row."""
    v = narrated(tmp_path, [{"t": "hit", "type": "thump", "gain": 20}], bed_gain=-12)
    t = json.loads((v / "timeline.json").read_text())
    t["tracks"]["narration"] = []
    t["tracks"]["audio"] = t["tracks"]["audio"][1:]
    (v / "timeline.json").write_text(json.dumps(t))
    t = tl.load(v)
    rows = audio_check.audibility(audio_check.Stems(v, t, audio_check.finished(v, t)), v, t)
    (loud,) = rows_of(rows, "loud")
    assert loud["severity"] == "warning" and loud["against"] == "music" and "against the music's loudness" in loud["detail"]
    (heard,) = rows_of(rows, "audible")
    assert "the music's level" in heard["detail"]


def test_with_neither_voice_nor_music_loudness_is_said_not_measured(tmp_path):
    v = narrated(tmp_path, [{"t": 1.0, "type": "pop"}])
    t = json.loads((v / "timeline.json").read_text())
    t["tracks"]["narration"] = []
    t["tracks"]["audio"] = t["tracks"]["audio"][1:]
    (v / "timeline.json").write_text(json.dumps(t))
    t = tl.load(v)
    rows = audio_check.audibility(audio_check.Stems(v, t, audio_check.finished(v, t)), v, t)
    assert rows_of(rows, "loud")[0]["detail"].startswith("loud and too quiet not measured: no narration or music")


def test_the_loud_audit_holds_at_any_narration_level(tmp_path):
    """With the narration 8 dB quieter the defaults warned at +12.8 dB: the effects follow the narration's
    loudness, so the thump sits where it sits against a voice of any level."""
    from studio_kit import sfx
    over = []
    for gain in (0, -8, -16):
        v = narrated(tmp_path / str(gain), [{"t": "hit", "type": "thump"}])
        t = json.loads((v / "timeline.json").read_text())
        t["tracks"]["audio"][0]["gain"] = gain
        (v / "timeline.json").write_text(json.dumps(t))
        t = tl.load(v)
        rows = audio_check.audibility(audio_check.Stems(v, t, audio_check.finished(v, t)), v, t)
        over.append(rows_of(rows, "audible")[0]["over_loudness_db"])
        assert "severity" not in rows_of(rows, "loud")[0], rows
        assert abs(sfx.narration_offset(v, t) - (sfx.narration_offset(v, {**t, "tracks": {**t["tracks"], "audio": [
            {**t["tracks"]["audio"][0], "gain": 0}]}}) + gain)) < 0.01
    assert max(over) - min(over) < 0.5, over


def test_an_effect_outside_the_video_is_never_heard_and_says_so(tmp_path):
    from studio_kit import sfx
    v = narrated(tmp_path, [{"t": 12.0, "type": "pop"}])
    t = tl.load(v)
    with pytest.raises(SystemExit, match="12.00 s is outside the video"):
        sfx.check([{"t": 12.0, "type": "pop"}], t)
    with pytest.raises(SystemExit, match="outside the video"):
        sfx.check([{"t": -1.0, "type": "pop"}], t)
    sfx.check([{"t": 0.3, "type": "riser"}], t)                  # a build may start before 0: its contact is inside
    (row,) = rows_of(audio_check.audibility(audio_check.Stems(v, t, audio_check.finished(v, t)), v, t), "audible")
    assert row["severity"] == "warning" and "outside the video (0 to 10.50 s): nobody hears it" in row["detail"]


def test_a_missed_tag_reports_where_the_picture_really_is_up_to_a_second_away(tmp_path):
    """A `land` 18 frames early warned, but neither the row nor the close-up said where the landing was."""
    from studio_kit import motion
    from test_motion import gray_clip, picture
    movie = tmp_path / "cut.mp4"
    gray_clip(movie, picture())
    window = round(audio_check.TAG_WINDOW * 30)
    sig = motion.frame_signal(movie, tl.DEFAULT_LAYOUT, 30, 0, 2 * window + 1)
    got = audio_check._judged(sig, 2, "land", 30, [], window)
    assert (got["picture_frame"], got["picture_offset_frames"], got["picture_ok"]) == (20, 18, False), got


def test_a_close_up_near_the_end_keeps_its_time_scale_and_a_long_sheet_draws(tmp_path):
    """0.8 s of audio was spread across a 1.5 s close-up, so the click sat at x=900 under a marker at 480;
    a sheet over 2880 s raised StopIteration."""
    from studio_kit import sound_sheet as ss
    y = np.zeros(10 * 48_000, np.float32)
    y[int(9.8 * 48_000):int(9.8 * 48_000) + 480] = 0.9
    sf.write(tmp_path / "end.wav", y, 48_000)
    a, b = ss.closeup_span(9.8)
    ss.draw(tmp_path / "end.wav", tmp_path / "end.png", a, b, [{"id": "fx1", "type": "pop", "t": 9.8, "flags": []}], fps=30, width=1200)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(tmp_path / "end.png"), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    im = np.frombuffer(raw, np.uint8).reshape(ss.height(), 1200, 3).astype(int)
    top = ss.TITLE_H + ss.LABEL_ROW_H * ss.LABEL_ROWS + ss.SPEECH_H
    band = im[top + 5:top + ss.WAVE_H - 5]
    loud = np.nonzero((((abs(band[..., 0] - 0x8f) < 30) & (abs(band[..., 1] - 0xd3) < 30) & (band[..., 2] > 200)).sum(axis=0)) > 20)[0]
    assert abs(loud.min() - (9.8 - a) / (b - a) * 1200) < 10, loud
    assert ss.tick_step(25.6) == 2 and ss.tick_step(3000) == 300 and ss.tick_step(30_000) == 1260
