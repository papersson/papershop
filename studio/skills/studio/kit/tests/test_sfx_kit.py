"""The kit provider: curated recordings placed on their cue by their transient peak."""
import hashlib
import io
import json
import zipfile
from argparse import Namespace

import pytest

from studio_kit import assets, new, sfx, soundkit

np = pytest.importorskip("numpy")
sf = pytest.importorskip("soundfile")

SOURCE_RATE = 44_100


def recording(lead=0.03, rate=SOURCE_RATE, stereo=True, swell=0.0):
    """A knock with a lead-in: `lead` s of silence (or of a sound swelling to `swell` of the peak, as a
    whoosh does before it lands), a 2 ms rise to a peak, a 120 ms decay."""
    t = np.arange(int((lead + 0.2) * rate)) / rate
    hit = np.where(t < lead, swell * t / lead, np.minimum(1, (t - lead) / 0.002) * np.exp(-np.maximum(0, t - lead - 0.002) * 40))
    y = (np.sin(2 * np.pi * 700 * t) * hit * 0.8).astype(np.float32)
    return np.stack([y, y * 0.5], axis=1) if stereo else y


def ogg(y, rate=SOURCE_RATE):
    b = io.BytesIO()
    sf.write(b, y, rate, format="OGG", subtype="VORBIS")
    return b.getvalue()


def sha(data):
    return hashlib.sha256(data).hexdigest()


PACK = {"title": "Test Pack", "version": "1.0", "license": "CC0-1.0", "creator": "Someone (example.org)",
        "homepage": "https://example.org/pack", "unpack": ["Audio/*.ogg", "License.txt"]}


@pytest.fixture
def kit(tmp_path, monkeypatch):
    """A one-pack kit served from a file:// URL with two curated recordings (a knock with a 30 ms
    lead-in as `knock`, the default tap, and one that swells for 80 ms before its peak as
    `knock-late`), and an empty cache."""
    monkeypatch.setenv("STUDIO_CACHE", str(tmp_path / "cache"))
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    members = {"Audio/knock.ogg": ogg(recording()), "Audio/late.ogg": ogg(recording(lead=0.08, swell=0.3))}
    z = tmp_path / "remote" / "pack.zip"
    z.parent.mkdir()
    with zipfile.ZipFile(z, "w") as f:
        for name, data in members.items():
            f.writestr(name, data)
        f.writestr("License.txt", b"CC0")
    sounds = []
    for sid, member, extra in (("knock", "Audio/knock.ogg", {"default": True}), ("knock-late", "Audio/late.ogg", {})):
        y, raw = soundkit.decode(members[member])
        sounds.append({"id": sid, "type": "tap", **extra, "pack": "test-pack", "member": member,
                       "sha256": sha(members[member]), "facts": soundkit.measure(y, sfx.RATE)})
    sounds.append({**sounds[0], "id": "knock-q", "type": "question"})
    m = {"version": 1, "packs": {"test-pack": {**PACK, "url": z.as_uri(), "sha256": sha(z.read_bytes()),
                                               "bytes": z.stat().st_size}}, "sounds": sounds}
    path = tmp_path / "soundkit.json"
    path.write_text(json.dumps(m))
    monkeypatch.setattr(soundkit, "MANIFEST", path)
    monkeypatch.setattr(soundkit, "SCHEMES", ("https://", "file://"))
    return m


def fetched():
    soundkit.fetch_kit(progress=io.StringIO())


def video(tmp_path):
    v, _ = new.create("v", directory=tmp_path / "video")
    return v


# --- decoding and the contact ---------------------------------------------------------------------

def test_decoding_folds_stereo_to_mono_and_resamples_to_the_kit_rate():
    y, raw = soundkit.decode(ogg(recording()))
    assert y.dtype == np.float32 and y.ndim == 1 and len(y) == -(-int(0.23 * SOURCE_RATE) * 160 // 147)
    assert 0.5 < raw < 0.9 and abs(np.abs(y).max() - 0.6) < 0.06          # the mean of a channel and its half
    tone = np.sin(2 * np.pi * 1000 * np.arange(SOURCE_RATE) / SOURCE_RATE).astype(np.float32)
    up = soundkit.resample(tone, SOURCE_RATE, sfx.RATE)
    assert len(up) == sfx.RATE and np.array_equal(up, soundkit.resample(tone, SOURCE_RATE, sfx.RATE))
    mid = up[4800:43200]
    crossings = np.count_nonzero(np.diff(np.signbit(mid)))
    assert abs(crossings - 1600) <= 1 and abs(np.abs(mid).max() - 1) < 0.01  # still 1 kHz, still full scale


def test_the_contact_is_the_transient_peak_not_the_first_sample():
    y = soundkit.resample(recording(stereo=False), SOURCE_RATE, sfx.RATE)
    at = soundkit.contact(y, sfx.RATE)
    assert abs(at - int(0.032 * sfx.RATE)) < int(0.002 * sfx.RATE)        # 30 ms of lead-in, a 2 ms rise
    f = soundkit.measure(y, sfx.RATE)
    assert f["contact"] == at and f["events"] == 1 and 25 < f["lead_ms"] < 32 and f["attack_ms"] < 6


@pytest.mark.parametrize("ring_db, lands_on", [(3, "attack"), (9, "ring")])
def test_an_attack_wins_unless_what_follows_is_much_louder(ring_db, lands_on):
    r = sfx.RATE
    t = np.arange(int(0.5 * r)) / r
    attack = np.exp(-t * 200) * (t < 0.05)
    ring = np.exp(-np.abs(t - 0.25) * 30) * 10 ** (ring_db / 20)              # a louder swell 250 ms in
    y = (np.sin(2 * np.pi * 500 * t) * (attack + ring) * 0.3).astype(np.float32)
    at = soundkit.contact(y, r) / r
    assert (at < 0.01) if lands_on == "attack" else abs(at - 0.25) < 0.01


def test_two_bursts_count_as_two_events():
    r = sfx.RATE
    t = np.arange(int(0.4 * r)) / r
    env = np.exp(-t * 60) + np.exp(-np.maximum(0, t - 0.2) * 60) * (t >= 0.2)
    assert soundkit.measure((np.sin(2 * np.pi * 900 * t) * env * 0.5).astype(np.float32), r)["events"] == 2


# --- the provider -----------------------------------------------------------------------------------

def test_a_kit_sound_lands_on_its_peak_and_its_digest_is_its_file(kit):
    s = sfx.resolve({"t": 1.0, "type": "tap", "sound": "kit:knock"})
    facts = kit["sounds"][0]["facts"]
    assert (s.id, s.lands, s.contact, s.length, s.rate) == ("kit:knock", "peak", facts["contact"], facts["samples"], sfx.RATE)
    other = json.loads(soundkit.MANIFEST.read_text())
    other["sounds"][0]["sha256"] = "f" * 64
    soundkit.MANIFEST.write_text(json.dumps(other))
    assert sfx.resolve("kit:knock").digest != s.digest                  # the digest holds the file's sha256
    with pytest.raises(SystemExit, match="takes no params"):
        sfx.resolve({"t": 1.0, "sound": "kit:knock", "params": {"freq": 900}}, at=1.0)


def test_a_kit_sound_plays_at_its_trim_and_its_digest_holds_it(kit):
    fetched()
    before = sfx.resolve("kit:knock")
    m = json.loads(soundkit.MANIFEST.read_text())
    m["sounds"][0]["facts"]["trim_db"] = -6.0
    soundkit.MANIFEST.write_text(json.dumps(m))
    after = sfx.resolve("kit:knock")
    assert after.digest != before.digest                                 # so the track's key, and its render, move
    assert np.allclose(after.samples, before.samples * 10 ** (-6 / 20), atol=1e-6)
    m["sounds"][0]["facts"]["trim_db"] = 20
    assert any("facts.trim_db must be dB from -30 to 12" in p for p in soundkit.problems(m))


def test_a_trim_brings_a_recording_to_its_synth_voices_level():
    """By soundkit.level (K-weighted, the loudest 10 ms); a type the synths lack goes to their median."""
    hot = sfx.voice("confirm") * 4
    assert soundkit.trim(hot, "confirm") == pytest.approx(-12.0, abs=0.1)
    y = sfx.voice("pop")
    trimmed = y * 10 ** (soundkit.trim(y * 0.3, "dice") / 20) * 0.3
    assert soundkit.level(trimmed) == pytest.approx(soundkit.reference_level("dice"), abs=0.1)
    assert soundkit.level(sfx.voice("thump")) - soundkit.level(sfx.voice("thump") * 0.5) == pytest.approx(6.02, abs=0.01)


def test_a_cue_plays_the_synth_unless_it_asks_for_the_kit(kit):
    """A type keeps its synth voice; "kit" is the type's default recording; a type only the kit has
    plays its default; "kit" for a type the kit lacks stops."""
    assert sfx.resolve({"type": "tap"}).id == "synth:tap"
    assert sfx.resolve({"type": "tap", "sound": "kit"}).id == "kit:knock"
    assert sfx.resolve({"type": "question"}).id == "kit:knock-q"             # no synth voice of that name
    with pytest.raises(SystemExit, match="no 'swell' sound"):
        sfx.resolve({"type": "swell", "sound": "kit"})
    with pytest.raises(SystemExit, match="unknown effect 'kit:door'"):
        sfx.resolve({"type": "tap", "sound": "kit:door"})
    assert sfx.pinned({"t": 1, "type": "tap", "sound": "kit"}) == {"t": 1, "type": "tap", "sound": "kit:knock"}
    assert sfx.pinned({"t": 1, "type": "tap"}) == {"t": 1, "type": "tap"}


def test_placement_lines_the_peak_up_with_the_cue(kit, tmp_path):
    v = video(tmp_path)
    fetched()
    assert sfx.copy_in(v, [{"sound": "kit:knock"}]) == ["sounds/knock.ogg"]
    timeline = {"duration": 3.0, "cues": {"hit": 1.5}, "beats": {}}
    p = sfx.place([{"t": "hit", "type": "tap", "sound": "kit:knock"}], timeline, video=v)[0]
    assert p.contact == int(1.5 * sfx.RATE) and p.start == p.contact - p.sound.contact > 0
    track = sfx._mix([p], 3.0)
    env = soundkit.envelope(track, sfx.RATE)
    assert abs(int(np.argmax(env)) - int(1.5 * sfx.RATE)) <= int(0.001 * sfx.RATE)   # the peak on the cue's sample
    assert np.abs(track[:p.start]).max() == 0


def test_a_render_reads_the_videos_copy_never_the_cache(kit, tmp_path):
    v = video(tmp_path)
    fetched()
    timeline = {"duration": 3.0, "cues": {}, "beats": {}}
    with pytest.raises(SystemExit, match="assets/sounds/knock.ogg is missing.*asset restore"):
        sfx.place([{"t": 1.0, "sound": "kit:knock"}], timeline, video=v)[0].sound.samples
    sfx.copy_in(v, [{"sound": "kit:knock"}])
    s = sfx.place([{"t": 1.0, "sound": "kit:knock"}], timeline, video=v)[0].sound
    assert len(s.samples) == s.length and abs(float(np.abs(s.samples).max()) - 0.6) < 0.06
    (v / "assets/sounds/knock.ogg").write_bytes(ogg(recording(lead=0.01)))
    with pytest.raises(SystemExit, match="not the kit's test-pack:Audio/knock.ogg"):
        sfx.place([{"t": 1.0, "sound": "kit:knock"}], timeline, video=v)[0].sound.samples


def test_studio_sfx_copies_a_named_recording_in_or_says_how_to_fetch_it(kit, tmp_path, monkeypatch, capsys):
    from studio_kit import timeline as tl
    v = video(tmp_path)
    t = {"duration": 3.0, "fps": 30, "cues": {"reveal": 1.0}, "beats": {}, "tracks": {"narration": [], "scene": [], "audio": []}}
    monkeypatch.setattr(tl, "build", lambda video, quiet=False: t)
    cues = tmp_path / "cues.json"
    cues.write_text(json.dumps([{"t": "reveal", "type": "tap", "sound": "kit"}, {"t": 2.0, "type": "click"}]))
    with pytest.raises(SystemExit, match="doctor --fetch --sounds"):
        sfx.main(Namespace(video=str(v), cues=str(cues)))
    fetched()
    assert sfx.main(Namespace(video=str(v), cues=str(cues))) == 0
    assert "copied in assets/sounds/knock.ogg" in capsys.readouterr().out
    kept = json.loads((v / "audio/sfx.json").read_text())
    assert kept[0]["sound"] == "kit:knock" and "sound" not in kept[1]
    row = assets.read(v)[0]
    assert row["kind"] == "library" and row["params"]["sound"] == "knock" and row["sha256"] == kit["sounds"][0]["sha256"]
    sfx.main(Namespace(video=str(v), cues=str(cues)))
    assert "copied in" not in capsys.readouterr().out                    # there already: nothing copied


def test_the_lab_lists_the_kits_recordings_with_their_own_files(kit, tmp_path):
    (tmp_path / "timeline.json").write_text(json.dumps({"duration": 4.0, "tracks": {"narration": [], "scene": []}}))
    page = sfx.lab(tmp_path).read_text()
    assert "is not fetched" in page and "kit:knock" not in page
    fetched()
    page = sfx.lab(tmp_path).read_text()
    assert page.count('type="radio"') == 3 * len(sfx.KINDS) + 3 and "<legend>question</legend>" in page
    assert (tmp_path / "out/sound-lab/kit-tap-1_alone.wav").exists() and (tmp_path / "out/sound-lab/synth-tap-1_alone.wav").exists()
    assert "&quot;sound&quot;: &quot;kit:knock&quot;" in page and "is not fetched" not in page


# --- the committed manifest -------------------------------------------------------------------------

def test_the_curated_kit_has_a_default_per_type_and_a_line_per_sound():
    m = soundkit.load()
    text = soundkit.MANIFEST.read_text()
    assert 100 <= len(m["sounds"]) <= 160 and "by measurement, not by ear" in m["note"]
    assert sum(line.startswith('  {"id": ') for line in text.splitlines()) == len(m["sounds"])
    assert [s["id"] for s in m["sounds"]] == [s["id"] for s in sorted(m["sounds"], key=lambda s: (s["type"], not s.get("default"), s["id"]))]
    for kind in soundkit.types(m):
        assert sum(bool(s.get("default")) for s in m["sounds"] if s["type"] == kind) == 1, kind
    assert {"click", "pop", "thump", "whoosh", "confirm", "error", "chime", "key-tick"} <= set(soundkit.types(m))
    for s in m["sounds"]:
        f = s["facts"]
        assert 0 <= f["contact"] < f["samples"] and f["events"] == 1 and f["peak_dbfs"] >= -20, s["id"]
        assert -16 <= f["trim_db"] <= 9, s["id"]                       # Kenney's files are hot: most come down
        assert s["member"].startswith("Audio/") and s["id"].split("-")[0] in ("impact", "interface", "ui", "rpg", "casino")


def test_two_defaults_or_a_contact_past_the_end_is_invalid(kit):
    m = json.loads(soundkit.MANIFEST.read_text())
    m["sounds"][1]["default"] = True
    m["sounds"][0]["facts"]["contact"] = m["sounds"][0]["facts"]["samples"]
    bad = soundkit.problems(m)
    assert any("already has a default" in p for p in bad) and any("facts.contact must be" in p for p in bad)


def test_the_committed_facts_are_what_the_kit_measures():
    """Re-measures every curated sound from the fetched kit (skipped until `doctor --fetch --sounds`)."""
    m = soundkit.load()
    if soundkit.check(m)[0] != "ok":
        pytest.skip("the sound kit is not fetched")
    for s in m["sounds"]:
        data, _ = soundkit.read_member(s["pack"], s["member"], m)
        assert sha(data) == s["sha256"], s["id"]
        f = soundkit.measure(soundkit.decode(data)[0], sfx.RATE)
        assert (f["contact"], f["samples"]) == (s["facts"]["contact"], s["facts"]["samples"]), s["id"]
        assert s["facts"]["trim_db"] == soundkit.trim(soundkit.decode(data)[0], s["type"]), s["id"]
