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


# The track before the sound resolver and place(): each voice read from the table, a build moved back
# by its length and cut at 0. Kept here so the refactor is held to sounding the same.
def _render_before(cues, timeline):
    placed = []
    for c in cues:
        fn, length, lands = sfx.VOICES[c["type"]]
        p = c.get("params", {})
        v = fn(np.arange(int(p.get("length", length) * sfx.RATE)) / sfx.RATE, p)
        i = int(sfx.resolve_time(c["t"], timeline) * sfx.RATE) + (-len(v) if lands == "end" else 0)
        if i < 0:
            v, i = v[-i:], 0
        placed.append((i, v, 10 ** (c.get("gain", 0) / 20)))
    end = max(i + len(v) for i, v, _ in placed) if placed else sfx.RATE
    buf = np.zeros(int(max(end, timeline["duration"] * sfx.RATE)) + sfx.RATE, dtype=np.float32)
    for i, v, g in placed:
        buf[i:i + len(v)] += (v * g).astype(np.float32)
    return buf


MIXED = {"duration": 4.0, "fps": 30, "cues": {"reveal": 2.0, "land": 3.1, "early": 0.4},
         "beats": {"beats": [0.5, 1.0, 1.5], "downbeats": [0.5], "hits": [2.5]}}
EFFECTS = [
    {"t": "reveal", "type": "riser", "gain": -3},
    {"t": 0.3, "type": "swell", "params": {"freq": 330}},                    # builds cut at the start
    {"t": "early", "type": "riser", "params": {"length": 1.2}, "gain": 2},
    {"t": "land", "type": "thump", "gain": -6.5},
    {"t": "beat_2", "type": "click", "params": {"freq": 2400, "decay": 120}},
    {"t": "downbeat_1", "type": "pop"},
    {"t": "hit_1", "type": "chime", "gain": -1},
    {"t": 1.234, "type": "whoosh", "params": {"length": 0.6}},
    {"t": -0.01, "type": "key-tick"},
    {"t": 3.5, "type": "glitch", "gain": 4},
    {"t": 3.6, "type": "slide-in", "params": {"length": 0.45, "freq": 280}, "sound": "synth:slide-in"},
    {"t": 3.9, "type": "shimmer"},
]


def test_the_track_sounds_as_it_did_before_the_resolver():
    before = _render_before([{k: v for k, v in c.items() if k != "sound"} for c in EFFECTS], MIXED)
    after = sfx.render(EFFECTS, MIXED)
    assert after.dtype == before.dtype and after.tobytes() == before.tobytes()


def test_a_placement_says_where_its_sound_starts_ends_and_lands():
    riser, swell, _, thump = sfx.place(EFFECTS[:4], MIXED)
    n = int(0.8 * sfx.RATE)
    assert (riser.time, riser.contact, riser.start, riser.end) == (2.0, 2 * sfx.RATE, 2 * sfx.RATE - n, 2 * sfx.RATE)
    assert riser.sound.lands == "end" and riser.sound.contact == n == riser.sound.length and riser.gain == -3
    assert swell.start == 0 and swell.end == int(0.3 * sfx.RATE) and swell.contact == swell.end      # cut at 0
    assert thump.sound.lands == "start" and thump.start == thump.contact == int(3.1 * sfx.RATE)
    assert thump.sound.rate == sfx.RATE and thump.sound.id == "synth:thump"
    loose = sfx.place([{"t": "gone", "type": "click"}], MIXED, strict=False)[0]
    assert (loose.time, loose.start, loose.end, loose.contact) == (None,) * 4
    with pytest.raises(SystemExit, match="no time for cue 'gone'"):
        sfx.place([{"t": "gone", "type": "click"}], MIXED)


def test_one_resolver_makes_every_sound():
    s = sfx.resolve({"type": "click", "params": {"freq": 1200}})
    assert np.array_equal(s.samples, sfx.voice("click", freq=1200)) and s.lands == "start" and s.contact == 0
    assert sfx.resolve("click", {"freq": 1200}).digest == s.digest == sfx.resolve("synth:click", {"freq": 1200}).digest
    assert s.digest != sfx.resolve("click").digest != sfx.resolve("pop").digest
    assert sfx.resolve({"type": "click", "sound": "synth:pop"}).id == "synth:pop"      # the sound, over the type
    with pytest.raises(SystemExit, match="unknown effect 'kit:door': no sound provider 'kit'"):
        sfx.check([{"t": 1.0, "type": "click", "sound": "kit:door"}], MIXED)
    with pytest.raises(SystemExit, match="unknown effect 'laser'"):
        sfx.check([{"t": 1.0, "type": "laser"}], MIXED)
    with pytest.raises(SystemExit, match=r"effect at 1\.0: length must be"):
        sfx.check([{"t": 1.0, "type": "riser", "params": {"length": 0}}], MIXED)


def test_the_track_re_renders_when_an_effect_changes_and_only_then(tmp_path, monkeypatch):
    (tmp_path / "audio").mkdir()
    fx = tmp_path / "audio" / "sfx.json"
    fx.write_text(json.dumps(EFFECTS[3:6]))
    made = []
    real = sfx._mix
    monkeypatch.setattr(sfx, "_mix", lambda placed, d: made.append(len(placed)) or real(placed, d))
    sfx.rendered(tmp_path, MIXED)
    sfx.rendered(tmp_path, MIXED)
    assert made == [3]
    monkeypatch.setattr(sfx, "__file__", str(tmp_path / "elsewhere.py"))     # the key isn't this file's bytes
    sfx.rendered(tmp_path, MIXED)
    assert made == [3]
    for change in ({**EFFECTS[3], "gain": -2}, {**EFFECTS[3], "params": {"freq": 70}}, {**EFFECTS[3], "t": 3.2}):
        fx.write_text(json.dumps([change] + EFFECTS[4:6]))
        sfx.rendered(tmp_path, MIXED)
    assert made == [3, 3, 3, 3]
