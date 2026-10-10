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


def test_every_encode_stays_under_the_ceiling(tmp_path):
    """AAC overshot a master finished to -1.5 dBTP: -1.2 at the web copy's 64 kbps, 0.0 at 48 and -0.1 at 28."""
    from studio_kit import publish
    v = video(tmp_path)
    tone(v / "audio" / "narration.wav", db=-6)
    (v / "audio" / "sfx.json").write_text(json.dumps([{"t": t, "type": "thump"} for t in (1.0, 2.5, 4.0)]))
    audio.finish(v, timeline=timeline(dict(tl.SFX)))
    for kbps, rate in ((160, "48000"), (64, "48000"), (48, "48000"), (28, "24000")):
        out = tmp_path / f"w{kbps}.m4a"
        audio.encode(v / "audio" / "final.wav", out, -1.5, "-b:a", f"{kbps}k", "-ar", rate, "-ac", "1")
        assert audio.measure(out)[1] <= -1.5, kbps
    still = tmp_path / "still.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:s=640x360:d=6:r=30",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(still)], check=True)
    r = publish.web_encode(still, tmp_path / "web.mp4", 6.0, limit=60_000, sound=v / "audio" / "final.wav", ceiling=-1.5)
    assert r["audio_kbps"] == 28 and audio.measure(tmp_path / "web.mp4")[1] <= -1.5


def sparse(tmp_path):
    """A quiet bed under one thump: a mix whose loudness jumps as the limiter flattens the hit."""
    v = tmp_path / "v"
    (v / "audio").mkdir(parents=True)
    (v / "assets").mkdir()
    (v / "video.json").write_text(json.dumps({"title": "x", "engine": "remotion", "genre": "motion", "duration": 6.0}))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=6:sample_rate=48000",
                    "-af", "volume=-18dB", str(v / "assets" / "bed.wav")], check=True)
    (v / "audio" / "tracks.json").write_text(json.dumps([{"file": "assets/bed.wav", "start": 0, "gain": -9}]))
    (v / "cues.json").write_text(json.dumps({"hit": 2.5}))
    (v / "audio" / "sfx.json").write_text(json.dumps([{"t": "hit", "type": "thump", "gain": -3}]))
    return v


def test_a_sparse_mix_reaches_its_target_or_says_so(tmp_path, monkeypatch, capsys):
    """Four passes left this mix at -16.5 LUFS for a -14 target, and `studio audio` exited 0."""
    pytest.importorskip("numpy")
    from types import SimpleNamespace
    v = sparse(tmp_path)
    r = audio.finish(v, -14.0, timeline=tl.build(v, quiet=True))
    assert abs(r["lufs"] - (-14.0)) <= audio.OFF_TARGET and r["true_peak_dbtp"] <= -1.45
    monkeypatch.setattr(audio, "MAX_PASSES", 1)
    assert audio.main(SimpleNamespace(video=v, lufs=-13.0, peak=-1.5)) == 1
    assert "warn: the finish landed at" in capsys.readouterr().out


def test_a_loud_effect_is_not_clipped_before_its_gain(tmp_path):
    """The render clipped at full scale before the mix's -8 dB, so a thump at +6 dB lost its peak."""
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    v = video(tmp_path)
    (v / "audio" / "sfx.json").write_text(json.dumps([{"t": 2.0, "type": "thump", "gain": 6}]))
    t = timeline(dict(tl.SFX))
    f = audio.sources(v, t)[1][1]
    peak = np.abs(sf.read(f)[0]).max()
    assert abs(peak - 0.9 * 10 ** (6 / 20)) < 0.1                        # the thump's peak, times its gain
    audio.mix(v, t, tmp_path / "bus.wav")
    assert abs(audio.measure(tmp_path / "bus.wav")[1] - (20 * np.log10(peak) - 8)) < 1.0


# --- the sub-buses' processing ---------------------------------------------------------------------

def speech(path, seconds=10, on=1.5, off=1.5):
    """A voice stand-in: noise bursts `on` seconds long with `off`-second pauses between them."""
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    t = np.arange(int(seconds * 48_000)) / 48_000
    noise = np.convolve(np.random.default_rng(1).standard_normal(len(t)), np.ones(8) / 8, mode="same")
    sf.write(path, (0.3 * noise * ((t % (on + off)) < on)).astype(np.float32), 48_000)
    return t, (t % (on + off) > 0.3) & (t % (on + off) < on), (t % (on + off) > on + 0.8)


def levels(f, speaking, pause, lo, hi):
    """(dB in the band while speaking, in the pauses) of a file's first channel."""
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    y = sf.read(f, always_2d=True)[0][:, 0]
    y = np.pad(y, (0, max(0, len(speaking) - len(y))))[:len(speaking)]
    spectrum = np.fft.rfft(y)
    freq = np.fft.rfftfreq(len(y), 1 / 48_000)
    spectrum[(freq < lo) | (freq > hi)] = 0
    band = np.fft.irfft(spectrum, len(y))
    return tuple(10 * np.log10(np.mean(band[m] ** 2)) for m in (speaking, pause))


def processed(tmp_path, sound=None):
    """A narrated video with a two-tone bed (music) and the same tones as an effects track."""
    v = tmp_path / "v"
    (v / "audio").mkdir(parents=True)
    (v / "video.json").write_text(json.dumps({"title": "x", **({"sound": sound} if sound is not None else {})}))
    _, speaking, pause = speech(v / "audio" / "narration.wav")
    for name in ("bed.wav", "fx.wav"):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=300:duration=10:sample_rate=48000",
                        "-f", "lavfi", "-i", "sine=frequency=2000:duration=10:sample_rate=48000", "-filter_complex",
                        "amix=inputs=2:normalize=0", str(v / name)], check=True)
    t = {"duration": 10.0, "tracks": {"audio": [{"file": "audio/narration.wav", "start": 0.0, "role": "narration"},
                                                {"file": "bed.wav", "start": 0.0, "role": "music"},
                                                {"file": "fx.wav", "start": 0.0, "role": "sfx"}]}}
    return v, t, speaking, pause


def test_music_ducks_under_speech_and_comes_back_in_the_pauses(tmp_path):
    v, t, speaking, pause = processed(tmp_path, {"room": 0})
    low_speaking, low_pause = levels(audio.stem(v, t, "music"), speaking, pause, 100, 600)
    dry = levels(v / "bed.wav", speaking, pause, 100, 600)
    assert 6 < (low_pause - dry[1]) - (low_speaking - dry[0]) < 13       # about 9 dB under speech
    assert abs(low_pause - dry[1]) < 1.0                                 # and back in the pauses


def test_effects_lose_presence_only_while_the_narration_speaks(tmp_path):
    v, t, speaking, pause = processed(tmp_path, {"room": 0})
    f = audio.stem(v, t, "sfx")
    mid, low = levels(f, speaking, pause, 1500, 2500), levels(f, speaking, pause, 100, 600)
    dry_mid, dry_low = levels(v / "fx.wav", speaking, pause, 1500, 2500), levels(v / "fx.wav", speaking, pause, 100, 600)
    assert 1.5 < (mid[1] - dry_mid[1]) - (mid[0] - dry_mid[0]) < 6        # the 1-4 kHz band dips under speech
    assert abs(mid[1] - dry_mid[1]) < 1.0 and abs(low[0] - dry_low[0]) < 1.0   # not in the pauses, not below the band
    assert abs(levels(audio.stem(v, t, "narration"), speaking, pause, 100, 20_000)[0]
               - levels(v / "audio" / "narration.wav", speaking, pause, 100, 20_000)[0]) < 0.1   # the voice stays dry


def test_the_processing_applies_only_where_its_roles_are(tmp_path, monkeypatch):
    graphs = []
    real = audio.proc.ffmpeg
    monkeypatch.setattr(audio.proc, "ffmpeg", lambda *a, **k: graphs.append(" ".join(map(str, a))) or real(*a, **k))
    v = video(tmp_path)
    alone = timeline()
    assert audio.processing(v, audio.sources(v, alone)) == {}
    files = audio.sources(v, alone)
    assert audio.inputs(alone, files, audio.processing(v, files)) == audio.inputs(alone, files)   # a narration's stamp is as it was
    audio.mix(v, alone, tmp_path / "a.wav")
    footage = timeline({"file": "audio/narration.wav", "start": 0.0, "role": "footage"})
    audio.mix(v, footage, tmp_path / "b.wav")
    assert not any(k in g for g in graphs for k in ("sidechaincompress", "aecho", "bandpass"))
    tone(v / "bed.wav", db=-20, freq=440)
    music = {"duration": 6.0, "tracks": {"audio": [{"file": "bed.wav", "start": 0.0, "role": "music"}]}}
    assert audio.processing(v, audio.sources(v, music)) == {"room": 1.0, "presence": False, "duck": False}  # no voice, no key
    graphs.clear()
    audio.mix(v, music, tmp_path / "c.wav")
    assert "aecho" in graphs[-1] and "sidechaincompress" not in graphs[-1]
    graphs.clear()
    audio.mix(v, timeline({"file": "bed.wav", "start": 0.0, "role": "music"}), tmp_path / "d.wav")
    assert graphs[-1].count("sidechaincompress") == 2 and "aecho" in graphs[-1]


def test_a_narration_alone_masters_as_before(tmp_path):
    """The master's loudness and peak with no effects or music: what the plain sum gave."""
    v = video(tmp_path)
    (v / "video.json").write_text(json.dumps({"title": "x", "sound": {"room": 2.0}}))     # nothing for it to act on
    plain = tmp_path / "plain.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(v / "audio" / "narration.wav"), "-af", "apad=whole_dur=6",
                    "-c:a", "pcm_f32le", str(plain)], check=True)
    r = audio.finish(v, timeline=timeline())
    alone = audio.master(plain, tmp_path / "m.wav")
    assert abs(r["lufs"] - alone["lufs"]) < 0.05 and abs(r["true_peak_dbtp"] - alone["true_peak_dbtp"]) < 0.05


def test_the_sound_settings_enter_the_mix_and_its_stamp(tmp_path, monkeypatch):
    v, t, _, _ = processed(tmp_path)
    files = audio.sources(v, t)
    on = audio.inputs(t, files, audio.processing(v, files))
    (v / "video.json").write_text(json.dumps({"title": "x", "sound": {"room": False, "duck": False}}))
    p = audio.processing(v, files)
    assert p == {"room": 0.0, "presence": True, "duck": False} and audio.inputs(t, files, p) != on
    _, g = audio.graph(files, 10.0, p, gain=0.0)
    assert "aecho" not in g and g.count("sidechaincompress") == 2        # presence on the music and the effects
    (v / "video.json").write_text(json.dumps({"title": "x", "sound": {"room": 0.5}}))
    _, g = audio.graph(files, 10.0, audio.processing(v, files), gain=0.0)
    assert audio.room(0.5) in g and "0.0600" in audio.room(0.5)
    for bad in ({"room": 3}, {"room": "big"}, {"duck": "yes"}, {"reverb": 1}):
        (v / "video.json").write_text(json.dumps({"title": "x", "sound": bad}))
        with pytest.raises(SystemExit, match="video.json sound"):
            audio.processing(v, files)


def test_a_mix_with_music_and_effects_reaches_the_target(tmp_path):
    v, t, _, _ = processed(tmp_path)
    r = audio.finish(v, timeline=t)
    assert abs(r["lufs"] - (-16.0)) < 0.5 and r["true_peak_dbtp"] <= -1.45
