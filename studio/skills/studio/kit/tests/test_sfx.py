import json
import math

import pytest

from studio_kit import sfx

np = pytest.importorskip("numpy")


@pytest.mark.parametrize("kind", sfx.KINDS)
def test_every_voice_is_deterministic_finite_bounded_and_its_length(kind):
    fn, length, lands = sfx.VOICES[kind]
    a = sfx.voice(kind)
    assert np.array_equal(a, sfx.voice(kind))
    assert np.isfinite(a).all() and len(a) == int(length * sfx.RATE)
    assert 0.05 < np.abs(a).max() <= 1.0                          # audible, and never past full scale
    assert np.abs(a[-8:]).max() < 0.05                              # it ends quietly, not on a click
    assert len(sfx.voice(kind, length=0.5)) == int(0.5 * sfx.RATE)
    assert (fn.__doc__ or "").strip() and lands in ("start", "end")
    for p in sfx.CANDIDATES[kind]:
        v = sfx.voice(kind, **p)
        assert np.isfinite(v).all() and np.abs(v).max() <= 1.0


def test_the_first_voices_sound_as_they_did():
    t = np.arange(int(0.05 * sfx.RATE)) / sfx.RATE
    assert np.array_equal(sfx.voice("click"), np.sin(2 * math.pi * 1800 * t) * np.exp(-t * 90) * 0.5)
    t = np.arange(int(0.5 * sfx.RATE)) / sfx.RATE
    assert np.array_equal(sfx.voice("thump"), np.sin(2 * math.pi * (90 - 60 * t) * t) * np.exp(-t * 9) * 0.9)
    assert set(sfx.KINDS[:4]) == {"click", "pop", "thump", "whoosh"} and len(sfx.KINDS) >= 20
    assert set(sfx.CANDIDATES) == set(sfx.KINDS)


def test_a_build_ends_on_its_cue_and_a_hit_starts_on_it():
    t = {"duration": 3.0, "cues": {"reveal": 2.0}, "beats": {}}
    buf = sfx.render([{"t": "reveal", "type": "riser"}], t)
    at = int(2.0 * sfx.RATE)
    assert np.abs(buf[at - int(0.05 * sfx.RATE):at]).max() > 0.1 and np.abs(buf[at + 10:]).max() == 0
    buf = sfx.render([{"t": "reveal", "type": "chime"}], t)
    assert np.abs(buf[:at]).max() == 0 and np.abs(buf[at:at + 200]).max() > 0.05
    early = sfx.render([{"t": 0.2, "type": "swell"}], t)           # longer than the time before its cue: cut at 0
    assert np.abs(early[int(0.2 * sfx.RATE) + 10:]).max() == 0 and np.abs(early[:100]).max() > 0


def test_the_sound_lab_lists_every_voice_with_what_it_is_for(tmp_path):
    from studio_kit import timeline as tl
    (tmp_path / "timeline.json").write_text(json.dumps({"duration": 4.0, "tracks": {"narration": [], "scene": []}}))
    page = sfx.lab(tmp_path).read_text()
    assert page.count('type="radio"') == 3 * len(sfx.KINDS)
    for kind in sfx.KINDS:
        assert f"<legend>{kind}</legend>" in page
    assert "A card turning over" in page
    assert tl.load(tmp_path)["duration"] == 4.0


@pytest.mark.parametrize("kind", sfx.KINDS)
def test_params_a_voice_cannot_render_stop_at_sfx_not_at_the_mix(kind):
    """length 0 on a riser raised IndexError at mix time."""
    t = {"duration": 3.0, "cues": {}, "beats": {}}
    for bad in ({"length": 0}, {"length": -1}, {"freq": "high"}, {"loudness": 3}):
        with pytest.raises(SystemExit, match="effect"):
            sfx.check([{"t": 1.0, "type": kind, "params": bad}], t)
        with pytest.raises(SystemExit):
            sfx.voice(kind, **bad)
    v = sfx.voice(kind, length=0.01)
    assert len(v) == 480 and np.isfinite(v).all() and np.abs(v).max() <= 1.0
