import json
import subprocess

import pytest

from studio_kit import audio


def tone(path, seconds=6, db=-30, freq=220):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={seconds}:sample_rate=24000",
                    "-af", f"volume={db}dB", str(path)], check=True)


def video(tmp_path):
    (tmp_path / "audio").mkdir()
    tone(tmp_path / "audio" / "narration.wav")
    return tmp_path


def test_finish_hits_the_target_with_one_fixed_gain(tmp_path):
    r = audio.finish(video(tmp_path))
    assert abs(r["lufs"] - (-16.0)) < 0.5
    assert r["true_peak_dbtp"] <= -1.45
    assert (tmp_path / "audio" / "final.wav").exists()


def test_the_limiter_holds_the_ceiling_when_the_gain_would_clip(tmp_path):
    """A voice with a peak 12 dB over its body: the fixed gain that reaches the target would put it over the ceiling."""
    v = video(tmp_path)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(v / "audio" / "narration.wav"), "-f", "lavfi", "-i",
                    "sine=frequency=1000:duration=0.05:sample_rate=24000", "-filter_complex",
                    "[1:a]volume=-18dB,adelay=2000|2000[c];[0:a][c]amix=inputs=2:normalize=0", str(v / "audio" / "x.wav")], check=True)
    (v / "audio" / "x.wav").replace(v / "audio" / "narration.wav")
    r = audio.finish(v)
    assert r["true_peak_dbtp"] <= -1.45 and abs(r["lufs"] - (-16.0)) < 0.5
    assert r["input_true_peak_dbtp"] + r["gain_db"] > -1.5      # without the limiter it would have clipped


def test_mix_delays_and_trims_entries(tmp_path):
    v = video(tmp_path)
    t = {"duration": 4.0, "tracks": {"audio": [{"file": "audio/narration.wav", "start": 1.0, "in": 0.0, "out": 2.0}]}}
    audio.mix(v, t, tmp_path / "m.m4a")
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                str(tmp_path / "m.m4a")], capture_output=True, text=True).stdout)
    assert 3.9 < dur < 4.2
    # silence for the first second, then the tone
    lead = audio.measure(tmp_path / "m.m4a")
    assert lead[0] < -20


def test_pick_prefers_a_fresh_final_and_ignores_a_stale_one(tmp_path):
    v = video(tmp_path)
    audio.finish(v)
    assert audio.pick(v, "audio/narration.mp3").name == "final.wav"
    (v / "audio" / "narration.wav").touch()          # the narration changed after the finish
    assert audio.pick(v, "audio/narration.mp3").name == "narration.mp3"


def test_a_video_without_audio_gets_silence_of_its_length(tmp_path):
    t = {"duration": 2.0, "tracks": {"audio": [{"file": "audio/narration.mp3", "start": 0.0}]}}
    audio.mix(tmp_path, t, tmp_path / "m.m4a")
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                str(tmp_path / "m.m4a")], capture_output=True, text=True).stdout)
    assert 1.9 < dur < 2.3


def test_finish_is_skipped_when_its_source_is_unchanged(tmp_path, monkeypatch):
    v = video(tmp_path)
    first = audio.finish(v)
    assert json.loads((v / "audio" / "final.json").read_text()) == first and not (v / "timeline.json").exists()
    calls = []
    real = audio.measure
    monkeypatch.setattr(audio, "measure", lambda f: calls.append(f) or real(f))
    assert audio.finish(v) == first and calls == []
    (v / "audio" / "narration.wav").touch()          # the narration changed
    audio.finish(v)
    assert calls
