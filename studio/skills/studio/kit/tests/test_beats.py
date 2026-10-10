import json
import subprocess

import numpy as np
import pytest

from studio_kit import beats, sfx
from test_render import make_video


def click_track(path, bpm=120, seconds=12, offset=0.25, rate=22050):
    y = np.zeros(int(seconds * rate), dtype=np.float32)
    period = 60 / bpm
    t = np.arange(int(0.02 * rate)) / rate
    click = np.sin(2 * np.pi * 1500 * t) * np.exp(-t * 200)
    for k in range(int((seconds - offset) / period)):
        i = int((offset + k * period) * rate)
        y[i:i + len(click)] += click.astype(np.float32)
        if k % 4 == 0:                       # accent the downbeat
            y[i:i + len(click)] += click.astype(np.float32)
    import soundfile as sf
    sf.write(path, y, rate)


def test_a_120_bpm_click_track_gives_120_bpm_on_the_right_phase(tmp_path):
    f = tmp_path / "t.wav"
    click_track(f)
    r = beats.analyse(beats.load_mono(f))
    assert abs(r["bpm"] - 120) < 1.5
    assert abs(r["beats"][0] - 0.25) < 0.03 and abs(r["beats"][1] - r["beats"][0] - 0.5) < 0.03
    assert abs(r["downbeats"][0] - 0.25) < 0.03 and abs(r["downbeats"][1] - r["downbeats"][0] - 2.0) < 0.06
    assert any(abs(h - 0.25) < 0.05 for h in r["hits"])


def test_effects_are_placed_on_cue_names_and_are_deterministic(tmp_path):
    t = make_video(tmp_path)
    t["beats"] = {"bpm": 120, "beats": [0.5, 1.0, 1.5], "downbeats": [0.5], "hits": []}
    cues = [{"t": "beat_2", "type": "click"}, {"t": 2.0, "type": "whoosh", "gain": -6}, {"t": "downbeat_1", "type": "thump"}]
    a = sfx.render(cues, t)
    assert np.array_equal(a, sfx.render(cues, t))
    assert np.abs(a[int(0.99 * sfx.RATE):int(1.05 * sfx.RATE)]).max() > 0.1          # the click at beat 2
    assert np.abs(a[int(0.2 * sfx.RATE):int(0.45 * sfx.RATE)]).max() == 0            # nothing before the first cue
    with pytest.raises(SystemExit, match="no time for cue"):
        sfx.render([{"t": "beat_9", "type": "click"}], t)
    with pytest.raises(SystemExit, match="unknown effect"):
        sfx.voice("laser")


def test_sound_lab_page_offers_every_candidate(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_CACHE", str(tmp_path / "cache"))        # the kit not fetched: synth voices only
    make_video(tmp_path)
    page = sfx.lab(tmp_path).read_text()
    assert page.count('type="radio"') == sum(len(v) for v in sfx.CANDIDATES.values())
    assert 'id="copy"' in page and '<meta charset="utf-8">' in page
    assert (tmp_path / "out" / "sound-lab" / "synth-click-2_alone.wav").exists()
