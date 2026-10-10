import json
import subprocess
from types import SimpleNamespace

import pytest

from studio_kit import audio, music, sfx
from studio_kit import timeline as tl

np = pytest.importorskip("numpy")
pytest.importorskip("soundfile")


def piece(tmp_path, seconds=8.0):
    v = tmp_path / "v"
    (v / "audio").mkdir(parents=True)
    (v / "video.json").write_text(json.dumps({"title": "x", "engine": "remotion", "genre": "motion", "duration": seconds}))
    tl.build(v, quiet=True)
    return v


def test_the_bed_is_deterministic_and_quiet_chords_on_a_pulse():
    a = music.render(10.0, "Am", 80)
    assert np.array_equal(a, music.render(10.0, "Am", 80)) and len(a) == 10 * music.RATE
    assert np.isfinite(a).all() and abs(np.abs(a).max() - 0.5) < 1e-6
    assert np.abs(a[:100]).max() < 0.01 and np.abs(a[-100:]).max() < 0.01        # faded in and out
    assert not np.array_equal(a, music.render(10.0, "C", 80))
    assert music.grid(3.0, 60) == [0.0, 1.0, 2.0]
    with pytest.raises(SystemExit, match="--key"):
        music.parse_key("H")


def test_the_bed_registers_as_music_with_its_grid_and_comes_out_again(tmp_path, capsys):
    v = piece(tmp_path)
    (v / "audio" / "tracks.json").write_text(json.dumps([{"file": "assets/hit.wav", "start": 1, "role": "sfx"}]))
    music.main(SimpleNamespace(video=v, bed=True, remove=False, seconds=None, key="D", bpm=60.0))
    tracks = json.loads((v / "audio" / "tracks.json").read_text())
    assert tracks[0]["file"] == "assets/hit.wav" and tracks[1]["file"] == music.BED and tracks[1]["role"] == "music"
    t = tl.load(v)
    assert any(a["file"] == music.BED and a["role"] == "music" for a in t["tracks"]["audio"])
    assert t["beats"]["bpm"] == 60.0 and sfx.resolve_time("beat_3", t) == 2.0 and sfx.resolve_time("downbeat_2", t) == 4.0
    # the bed sits BED_UNDER under the narration (a motion piece has none: NO_VOICE)
    assert abs(audio.measure(v / music.BED)[0] + tracks[1]["gain"] - (music.NO_VOICE - music.BED_UNDER)) < 0.5
    music.make(v, key="D", bpm=60.0)                                    # again: one entry, not two
    assert [e["file"] for e in json.loads((v / "audio" / "tracks.json").read_text())].count(music.BED) == 1
    music.main(SimpleNamespace(video=v, bed=False, remove=True, seconds=None, key="C", bpm=72.0))
    assert json.loads((v / "audio" / "tracks.json").read_text()) == [{"file": "assets/hit.wav", "start": 1, "role": "sfx"}]
    assert not (v / music.BED).exists() and not (v / "audio" / "beats.json").exists() and "beats" not in tl.load(v)
    with pytest.raises(SystemExit, match="--bed"):
        music.main(SimpleNamespace(video=v, bed=False, remove=False, seconds=None, key="C", bpm=72.0))


def test_the_bed_does_not_take_another_tracks_grid_silently(tmp_path, capsys):
    v = piece(tmp_path)
    (v / "audio" / "beats.json").write_text(json.dumps({"bpm": 120, "beats": [0.5], "downbeats": [0.5], "hits": []}))
    music.make(v, bpm=72.0)
    assert "was another track's grid" in capsys.readouterr().out
    assert json.loads((v / "audio" / "beats.json").read_text())["source"] == music.BED


def test_a_narration_with_the_bed_and_effects_is_processed_and_reaches_the_target(tmp_path):
    from test_audio import speech
    v = piece(tmp_path, 10.0)
    speech(v / "audio" / "narration.wav")
    t = {"duration": 10.0, "tracks": {"audio": [{"file": "audio/narration.wav", "start": 0.0, "role": "narration"}]}}
    music.make(v, seconds=10.0, bpm=72.0)
    bed = json.loads((v / "audio" / "tracks.json").read_text())[0]
    (v / "audio" / "sfx.json").write_text(json.dumps([{"t": 1.6, "type": "chime"}, {"t": 4.6, "type": "pop-large"}]))
    t["tracks"]["audio"] += [bed, dict(tl.SFX)]
    assert audio.processing(v, audio.sources(v, t)) == {"room": 1.0, "presence": True, "duck": True}
    r = audio.finish(v, timeline=t)
    assert abs(r["lufs"] - (-16.0)) < 0.5 and r["true_peak_dbtp"] <= -1.45
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=sample_rate", "-of", "csv=p=0",
                          str(v / "audio" / "final.wav")], capture_output=True, text=True).stdout.strip()
    assert out == "48000"
