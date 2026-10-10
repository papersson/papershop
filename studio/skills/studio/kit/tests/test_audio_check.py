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
    assert "for 4.40-4.45 s of the word 'three' (4.00-4.45 s)" in bad["detail"]
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
    ("an effect buried under a loud bed", {"gain": 0}, 0, "masked"),
    ("an effect at -60 dBFS in silence", {"gain": -44}, None, "too quiet"),
])
def test_each_effect_is_heard_or_warned(tmp_path, case, effect, bed, warns):
    """The calibration: a pop in the first pause, alone (lifts silence, about 1 dB under the voice), under
    an undocked pink-noise bed at full gain (lifts it under 1 dB), and 44 dB down (peaking near -60
    dBFS, 45 dB under the voice). The "sound layer" we studied passed the last one."""
    v = narrated(tmp_path, [{"t": "hit", "type": "pop", **effect}], sound={"duck": False, "presence": False})
    if bed is not None:
        noise_bed(v, bed)
    t = tl.load(v)
    (row,) = audio_check.audibility(audio_check.Stems(v, t, audio_check.finished(v, t)), v, t)
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
