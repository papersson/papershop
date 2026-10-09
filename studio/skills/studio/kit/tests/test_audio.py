import json
import subprocess

import pytest

from studio_kit import audio
from studio_kit import timeline as tl


def tone(path, seconds=6, db=-30, freq=220):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={seconds}:sample_rate=24000",
                    "-af", f"volume={db}dB", str(path)], check=True)


def video(tmp_path):
    (tmp_path / "audio").mkdir()
    tone(tmp_path / "audio" / "narration.wav")
    return tmp_path


def timeline(*extra):
    """A narrated timeline's sound: the mp3 entry narrate writes (the mix takes its wav), and `extra`."""
    return {"duration": 6.0, "tracks": {"audio": [{"file": "audio/narration.mp3", "start": 0.0, "role": "narration"},
                                                  *extra]}}


def test_finish_hits_the_target_with_one_fixed_gain(tmp_path):
    r = audio.finish(video(tmp_path), timeline=timeline())
    assert abs(r["lufs"] - (-16.0)) < 0.5
    assert r["true_peak_dbtp"] <= -1.45
    assert (tmp_path / "audio" / "final.wav").exists()


def test_a_narration_alone_finishes_as_the_narration_file_did(tmp_path):
    """Before the finish moved to the mix, it ran on the narration file itself."""
    v = video(tmp_path)
    alone = audio.master(v / "audio" / "narration.wav", tmp_path / "alone.wav")
    mixed = audio.finish(v, timeline=timeline())
    assert abs(mixed["lufs"] - alone["lufs"]) < 0.1 and abs(mixed["true_peak_dbtp"] - alone["true_peak_dbtp"]) < 0.2
    assert abs(mixed["gain_db"] - alone["gain_db"]) < 0.2


def test_the_limiter_holds_the_ceiling_when_the_gain_would_clip(tmp_path):
    """A voice with a peak 12 dB over its body: the fixed gain that reaches the target would put it over the ceiling."""
    v = video(tmp_path)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(v / "audio" / "narration.wav"), "-f", "lavfi", "-i",
                    "sine=frequency=1000:duration=0.05:sample_rate=24000", "-filter_complex",
                    "[1:a]volume=-18dB,adelay=2000|2000[c];[0:a][c]amix=inputs=2:normalize=0", str(v / "audio" / "x.wav")], check=True)
    (v / "audio" / "x.wav").replace(v / "audio" / "narration.wav")
    r = audio.finish(v, timeline=timeline())
    assert r["true_peak_dbtp"] <= -1.45 and abs(r["lufs"] - (-16.0)) < 0.5
    assert r["input_true_peak_dbtp"] + r["gain_db"] > -1.5      # without the limiter it would have clipped


def test_a_loud_effect_stays_under_the_ceiling(tmp_path):
    """The finish ran on the narration alone, so an effect mixed over it could peak past the ceiling."""
    pytest.importorskip("numpy")
    v = video(tmp_path)
    tone(v / "audio" / "narration.wav", db=-6)
    (v / "audio" / "sfx.json").write_text(json.dumps([{"t": 2.0, "type": "thump"}]))
    r = audio.finish(v, timeline=timeline(dict(tl.SFX)))
    assert r["true_peak_dbtp"] <= -1.45 and abs(r["lufs"] - (-16.0)) < 0.5
    assert r["input_true_peak_dbtp"] + r["gain_db"] > 0            # the effect alone would have clipped
    assert (v / "audio" / "sfx.wav").exists()
    assert audio.measure(audio.soundtrack(v, timeline(dict(tl.SFX))))[1] <= -1.5   # and after the AAC encode


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


def test_each_role_goes_through_its_chain(tmp_path, monkeypatch):
    v = video(tmp_path)
    tone(v / "bed.wav", db=0, freq=440)
    t = {"duration": 6.0, "tracks": {"audio": [{"file": "bed.wav", "start": 0.0, "role": "music"}]}}
    audio.mix(v, t, tmp_path / "plain.wav")
    monkeypatch.setitem(audio.ROLE_CHAIN, "music", ["volume=-30dB"])
    assert "volume=-30dB" in audio.chain(t["tracks"]["audio"][0])
    assert "volume=-30dB" not in audio.chain({"file": "audio/narration.wav", "role": "narration"})
    audio.mix(v, t, tmp_path / "under.wav")
    drop = audio.measure(tmp_path / "plain.wav")[0] - audio.measure(tmp_path / "under.wav")[0]
    assert 29 < drop < 31


def test_a_draft_hears_the_finished_master_while_its_inputs_are_unchanged(tmp_path, monkeypatch):
    v, t = video(tmp_path), timeline()
    raw = audio.measure(audio.soundtrack(v, t))[0]
    assert raw < -25
    audio.finish(v, -14.0, timeline=t)
    calls = []
    real = audio.mix
    monkeypatch.setattr(audio, "mix", lambda *a: calls.append(a) or real(*a))
    first = audio.soundtrack(v, t)
    assert abs(audio.measure(first)[0] - (-14.0)) < 0.6 and calls == []        # the master, at its own target
    assert audio.soundtrack(v, t) == first and first.exists()                    # cached
    (v / "audio" / "narration.wav").touch()                                     # the narration changed
    assert abs(audio.measure(audio.soundtrack(v, t))[0] - raw) < 0.5 and len(calls) == 1


def test_a_video_without_audio_gets_silence_of_its_length(tmp_path):
    t = {"duration": 2.0, "tracks": {"audio": [{"file": "audio/narration.mp3", "start": 0.0}]}}
    audio.mix(tmp_path, t, tmp_path / "m.m4a")
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                str(tmp_path / "m.m4a")], capture_output=True, text=True).stdout)
    assert 1.9 < dur < 2.3
    assert audio.finish(tmp_path, timeline=t) is None


def test_finish_is_skipped_when_its_inputs_are_unchanged(tmp_path, monkeypatch):
    v, t = video(tmp_path), timeline()
    first = audio.finish(v, timeline=t)
    assert json.loads((v / "audio" / "final.json").read_text()) == first
    calls = []
    real = audio.measure
    monkeypatch.setattr(audio, "measure", lambda f: calls.append(f) or real(f))
    assert audio.finish(v, timeline=t) == first and calls == []
    (v / "audio" / "narration.wav").touch()          # the narration changed
    audio.finish(v, timeline=t)
    assert calls
    calls.clear()
    audio.finish(v, -14.0, timeline=t)                # another target
    assert calls
