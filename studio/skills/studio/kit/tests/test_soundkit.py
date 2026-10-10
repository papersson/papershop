import copy
import hashlib
import io
import json
import zipfile
from argparse import Namespace

import pytest

from studio_kit import assets, checkpoint, doctor, fetch, new, pin, publish, soundkit


def sha(data):
    return hashlib.sha256(data).hexdigest()


PACK = {"title": "Test Pack", "version": "1.0", "url": "https://example.org/p.zip", "sha256": "0" * 64,
        "bytes": 1, "license": "CC0-1.0", "creator": "Someone (example.org)",
        "homepage": "https://example.org/pack", "unpack": ["Audio/*.ogg", "License.txt"]}


@pytest.fixture
def kit(tmp_path, monkeypatch):
    """A one-pack manifest whose zip is served from a file:// URL, and an empty cache."""
    monkeypatch.setenv("STUDIO_CACHE", str(tmp_path / "cache"))
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    z = tmp_path / "remote" / "pack.zip"
    z.parent.mkdir()
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("Audio/thud.ogg", b"OggS thud")
        f.writestr("Audio/tick.ogg", b"OggS tick")
        f.writestr("License.txt", b"CC0")
        f.writestr("Kenney.url", b"[InternetShortcut]")
    data = z.read_bytes()
    m = {"version": 1, "packs": {"test-pack": {**PACK, "url": z.as_uri(), "sha256": sha(data), "bytes": len(data)}},
         "sounds": [{"id": "thud", "pack": "test-pack", "member": "Audio/thud.ogg", "type": "impact",
                     "sha256": sha(b"OggS thud"), "facts": {"seconds": 0.2}}]}
    path = tmp_path / "soundkit.json"
    path.write_text(json.dumps(m))
    monkeypatch.setattr(soundkit, "MANIFEST", path)
    monkeypatch.setattr(soundkit, "SCHEMES", ("https://", "file://", "http://127.0.0.1"))
    return m


def video(tmp_path):
    v, _ = new.create("v", directory=tmp_path / "video")
    return v


def test_the_committed_manifest_is_valid_cc0_and_pinned_by_digest():
    m = soundkit.load()
    assert soundkit.problems(m) == [] and 3 <= len(m["packs"]) <= 6
    for p in m["packs"].values():
        assert p["license"] == "CC0-1.0" and p["url"].startswith("https://kenney.nl/media/pages/assets/")
        assert len(p["sha256"]) == 64 and p["bytes"] > 0 and "*.url" not in p["unpack"]


@pytest.mark.parametrize("change, problem", [
    (lambda m: m["packs"]["test-pack"].update(license="CC-BY-4.0"), "not allowed"),
    (lambda m: m["packs"]["test-pack"].update(sha256="abc"), "64 lower-case hex"),
    (lambda m: m["packs"]["test-pack"].update(url="http://example.org/p.zip"), "https"),
    (lambda m: m["packs"]["test-pack"].pop("creator"), "creator must be a str"),
    (lambda m: m["packs"].update({"Bad Id": m["packs"]["test-pack"]}), "lower-case words"),
    (lambda m: m["sounds"].append(dict(m["sounds"][0])), "used twice"),
    (lambda m: m["sounds"][0].update(pack="nope"), "no pack nope"),
    (lambda m: m["sounds"][0].update(member="Kenney.url"), "not a member the pack unpacks"),
    (lambda m: m["sounds"][0].pop("type"), "needs id, pack, member, type, sha256"),
    (lambda m: m.update(version=2), "version must be 1"),
])
def test_the_validator_names_what_is_wrong(kit, change, problem):
    m = copy.deepcopy(kit)
    change(m)
    assert any(problem in p for p in soundkit.problems(m)), soundkit.problems(m)


def test_an_invalid_manifest_stops_loading(kit, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({**kit, "packs": {}}))
    with pytest.raises(SystemExit, match="not a valid sound kit manifest"):
        soundkit.load(bad)


def test_fetching_the_kit_verifies_unpacks_the_whitelist_and_skips_next_time(kit, tmp_path):
    assert soundkit.check()[0] == "missing"
    soundkit.fetch_kit(progress=io.StringIO())
    pid, pack = next(iter(kit["packs"].items()))
    d = soundkit.folder(pid, pack)
    assert (d / "Audio/thud.ogg").read_bytes() == b"OggS thud" and not (d / "Kenney.url").exists()
    assert soundkit.check()[0] == "ok" and pack["sha256"][:12] in d.name
    assert (tmp_path / "cache" / ".gitignore").exists()
    (tmp_path / "remote" / "pack.zip").unlink()                  # a second fetch needs no network
    soundkit.fetch_kit(progress=io.StringIO())
    soundkit.archive(pid, pack).write_bytes(b"tampered")
    assert soundkit.state(pid, pack) == "changed" and soundkit.check()[0] == "missing"


def test_doctor_reports_the_kit_and_its_repair(kit):
    level, name, detail, fix = doctor.check_sounds()
    assert (level, name) == (doctor.WARN, "sound kit") and "not fetched" in detail and fix.endswith("doctor --fetch --sounds")
    soundkit.fetch_kit(progress=io.StringIO())
    assert doctor.check_sounds()[0] == doctor.OK


def test_doctor_fetch_offline_is_a_skip_not_a_crash(kit, monkeypatch, capsys):
    kit["packs"]["test-pack"]["url"] = "http://127.0.0.1:9/pack.zip"
    soundkit.MANIFEST.write_text(json.dumps(kit))
    monkeypatch.setattr(doctor, "fetch", lambda **kw: None)
    monkeypatch.setattr(doctor, "checks", lambda net=False: [])
    monkeypatch.setattr(doctor, "extra_checks", lambda extras=(): [])
    code = doctor.main(Namespace(fetch=True, sounds=True, engine=[], extra=[], video=None, net=False))
    out = capsys.readouterr().out
    assert code == 0 and "skip: sound kit: could not reach" in out and "skipped the fetch" in out


def test_a_library_sound_is_copied_with_its_provenance_and_credited(kit, tmp_path):
    v = video(tmp_path)
    with pytest.raises(SystemExit, match="doctor --fetch --sounds"):
        assets.add_library(v, "thud")
    soundkit.fetch_kit(progress=io.StringIO())
    row = assets.add_library(v, "thud")
    assert (v / "assets/sounds/thud.ogg").read_bytes() == b"OggS thud"
    assert row["kind"] == "library" and row["source"] == "test-pack:Audio/thud.ogg" and row["license"] == "CC0-1.0"
    assert row["sha256"] == sha(b"OggS thud") and row["params"]["creator"] == "Someone (example.org)"
    assert row["params"]["type"] == "impact" and row["params"]["pack_sha256"] == kit["packs"]["test-pack"]["sha256"]
    assert assets.add_library(v, "thud") == row                       # idempotent: the same row, untouched
    assets.add_library(v, "test-pack:Audio/tick.ogg", "tick")
    assert [r["file"] for r in assets.read(v)] == ["sounds/thud.ogg", "sounds/tick.ogg"]
    block = assets.credits(v)
    assert block.splitlines()[:2] == ["CREDITS", "Sound effects:"]
    assert "Test Pack by Someone (example.org), CC0 1.0, https://example.org/pack (2 sounds: thud.ogg, tick.ogg)" in block
    assert assets.page_credits(v) == ["Sound effects: Test Pack by Someone (example.org) (CC0 1.0)"]


def test_a_library_copy_refuses_a_digest_mismatch_and_a_different_file(kit, tmp_path, monkeypatch):
    v = video(tmp_path)
    soundkit.fetch_kit(progress=io.StringIO())
    (v / "assets/sounds").mkdir(parents=True)
    (v / "assets/sounds/thud.ogg").write_bytes(b"someone else's")
    with pytest.raises(SystemExit, match="exists and is not"):
        assets.add_library(v, "thud")
    (v / "assets/sounds/thud.ogg").unlink()
    kit["sounds"][0]["sha256"] = "f" * 64
    soundkit.MANIFEST.write_text(json.dumps(kit))
    with pytest.raises(SystemExit, match="the sound kit says f"):
        assets.add_library(v, "thud")
    with pytest.raises(SystemExit, match="not one of test-pack's sounds"):
        assets.add_library(v, "test-pack:Kenney.url")


def test_a_clone_without_its_sounds_is_restored_from_the_kit(kit, tmp_path):
    v = video(tmp_path)
    soundkit.fetch_kit(progress=io.StringIO())
    assets.add_library(v, "thud")
    assert doctor.check_library(v)[0] == doctor.OK
    (v / "assets/sounds/thud.ogg").unlink()                      # Git leaves sound out of a clone
    level, _, detail, fix = doctor.check_library(v)
    assert level == doctor.FAIL and "1 of 1 missing" in detail and "asset restore" in fix
    assert assets.restore(v) == ["sounds/thud.ogg"] and doctor.check_library(v)[0] == doctor.OK
    (v / "assets/sounds/thud.ogg").write_bytes(b"edited")
    assert "not the recorded file" in doctor.check_library(v)[2]


def test_the_page_carries_the_sound_credits(tmp_path):
    from test_render import make_video
    t = make_video(tmp_path)
    page = publish.page_html(t, {"title": "T"}, 1, ["Sound effects: Impact Sounds by Kenney (www.kenney.nl) (CC0 1.0)"])
    assert '<p class="credit">Sound effects: Impact Sounds by Kenney (www.kenney.nl) (CC0 1.0)</p>' in page


def test_a_pin_carries_the_manifest_and_commits_leave_library_sounds_out(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    v = video(tmp_path)
    p = pin.init(v)
    assert (p / "kit/src/studio_kit/soundkit.json").read_text() == soundkit.MANIFEST.read_text()
    assert "*.[oO][gG][gG]" in checkpoint.GITIGNORE and "*.[wW][aA][vV]" in checkpoint.GITIGNORE


def test_a_fork_takes_its_library_sounds_along(kit, tmp_path):
    v = video(tmp_path)
    soundkit.fetch_kit(progress=io.StringIO())
    assets.add_library(v, "thud")
    f = new.fork(v, "f", directory=tmp_path / "fork")
    assert (f / "assets/sounds/thud.ogg").read_bytes() == b"OggS thud" and assets.read(f)[0]["kind"] == "library"
