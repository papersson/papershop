"""The sound kit: recorded CC0 effects, listed in a committed manifest and fetched once into the cache.

soundkit.json sits beside this module, so `studio init` pins it with the kit and a pinned video's
library never moves. It lists:

  packs   {id: {title, version, url, sha256, bytes, license, creator, homepage, unpack}}: a zip,
          pinned by digest and size, CC0 only, and `unpack` the glob patterns of the members that
          are unpacked (the audio and its licence; never the shortcuts a pack also ships)
  sounds  [{id, pack, member, type, sha256, facts?}]: the curated sounds, each a member of a pack
          with its own digest, a type (what it is for) and measured facts

`studio doctor --fetch --sounds` downloads and unpacks every pack into $STUDIO_HOME/cache/sounds/,
verified; a video never reads the cache when it renders: `studio asset library` copies a sound into
the video with its provenance, read from the verified zip itself.
"""
import json
import re
import sys
import zipfile
import fnmatch
from pathlib import Path

from . import fetch
from .env import ROOT

MANIFEST = Path(__file__).with_name("soundkit.json")
LICENSES = {"CC0-1.0": "CC0 1.0"}          # SPDX id: how a credit line writes it
SLUG = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
HEX64 = re.compile(r"[0-9a-f]{64}")
SCHEMES = ("https://",)                    # a pack's url (tests add file://)
PACK_KEYS = {"title": str, "version": str, "url": str, "sha256": str, "bytes": int, "license": str,
             "creator": str, "homepage": str, "unpack": list}
SOUND_KEYS = {"id": str, "pack": str, "member": str, "type": str, "sha256": str}


def repair():
    return f"{ROOT / 'bin/studio'} doctor --fetch --sounds"


def problems(manifest):
    """Every way `manifest` breaks the schema, as sentences; empty when it is valid."""
    out = []
    if manifest.get("version") != 1:
        out.append("version must be 1")
    packs = manifest.get("packs")
    if not isinstance(packs, dict) or not packs:
        return out + ["packs must be a non-empty object"]
    for pid, p in packs.items():
        where = f"pack {pid}"
        if not SLUG.fullmatch(pid):
            out.append(f"{where}: the id must be lower-case words joined by hyphens")
        mistyped = [f"{where}: {key} must be a {kind.__name__}" for key, kind in PACK_KEYS.items()
                    if not isinstance(p, dict) or not isinstance(p.get(key), kind)]
        if mistyped:
            out += mistyped
            continue
        if not p["url"].startswith(SCHEMES) or not p["homepage"].startswith("https://"):
            out.append(f"{where}: url and homepage must be https")
        if not HEX64.fullmatch(p["sha256"]):
            out.append(f"{where}: sha256 must be 64 lower-case hex digits")
        if p["bytes"] <= 0:
            out.append(f"{where}: bytes must be positive")
        if p["license"] not in LICENSES:
            out.append(f"{where}: license {p['license']!r} is not allowed (only {', '.join(LICENSES)})")
        if not p["creator"].strip() or not p["title"].strip():
            out.append(f"{where}: title and creator must not be empty")
        if not p["unpack"] or not all(isinstance(m, str) and m for m in p["unpack"]):
            out.append(f"{where}: unpack must list glob patterns")
    sounds = manifest.get("sounds")
    if not isinstance(sounds, list):
        return out + ["sounds must be a list"]
    seen = set()
    for i, s in enumerate(sounds):
        where = f"sound {s.get('id', i) if isinstance(s, dict) else i}"
        if not isinstance(s, dict) or any(not isinstance(s.get(k), t) for k, t in SOUND_KEYS.items()):
            out.append(f"{where}: needs " + ", ".join(SOUND_KEYS) + " as strings")
            continue
        if not SLUG.fullmatch(s["id"]):
            out.append(f"{where}: the id must be lower-case words joined by hyphens")
        if s["id"] in seen:
            out.append(f"{where}: the id is used twice")
        seen.add(s["id"])
        if not HEX64.fullmatch(s["sha256"]):
            out.append(f"{where}: sha256 must be 64 lower-case hex digits")
        if s["pack"] not in packs:
            out.append(f"{where}: no pack {s['pack']}")
        elif not unpacked_member(packs[s["pack"]], s["member"]):
            out.append(f"{where}: {s['member']} is not a member the pack unpacks")
        if not isinstance(s.get("facts", {}), dict):
            out.append(f"{where}: facts must be an object")
    return out


def load(path=None):
    path = path or MANIFEST
    m = json.loads(Path(path).read_text())
    bad = problems(m)
    if bad:
        raise SystemExit(f"{path} is not a valid sound kit manifest:\n  " + "\n  ".join(bad))
    return m


def unpacked_member(pack, member):
    return any(fnmatch.fnmatchcase(member, pat) for pat in pack["unpack"])


def _stem(pid, pack):
    return fetch.cache_root() / "sounds" / f"{pid}-{pack['sha256'][:12]}"


def archive(pid, pack):
    """Where a pack's zip is cached: named by its digest, so manifests of two kits never collide."""
    return _stem(pid, pack).with_suffix(".zip")


def folder(pid, pack):
    """Where a pack is unpacked; its .unpacked marker holds the digest of the zip it came from."""
    return _stem(pid, pack)


def state(pid, pack):
    """'ok', 'missing' (never fetched), 'changed' (the cached zip is not the pinned one) or
    'packed' (the zip is verified but not unpacked)."""
    z = archive(pid, pack)
    if not z.exists():
        return "missing"
    if not fetch.verified(z, pack["sha256"]):
        return "changed"
    marker = folder(pid, pack) / ".unpacked"
    return "ok" if marker.is_file() and marker.read_text().strip() == pack["sha256"] else "packed"


def fetch_kit(manifest=None, progress=sys.stderr):
    """Download and unpack every pack, verified. Raises fetch.Offline when a host can't be reached."""
    manifest = manifest or load()
    fetch.cache_root(create=True)
    for pid, pack in manifest["packs"].items():
        if state(pid, pack) == "ok":
            continue
        z = fetch.fetch(pack["url"], archive(pid, pack), pack["sha256"], pack["bytes"], progress=progress)
        d = folder(pid, pack)
        files = fetch.unpack(z, d, pack["unpack"])
        (d / ".unpacked").write_text(pack["sha256"] + "\n")
        print(f"sound kit: {pack['title']}: {len(files)} files in {d}", file=progress or sys.stdout)


def check(manifest=None):
    """(level, detail): 'ok' when every pack is fetched and verified, else 'missing' with which."""
    manifest = manifest or load()
    states = {pid: state(pid, p) for pid, p in manifest["packs"].items()}
    bad = {pid: s for pid, s in states.items() if s != "ok"}
    if not bad:
        return "ok", f"{len(states)} packs verified in {fetch.cache_root() / 'sounds'}"
    if all(s == "missing" for s in bad.values()) and len(bad) == len(states):
        return "missing", "not fetched (recorded effects are optional; synth voices need nothing)"
    return "missing", "; ".join(f"{pid} {s}" for pid, s in bad.items())


def sound(sid, manifest=None):
    manifest = manifest or load()
    for s in manifest["sounds"]:
        if s["id"] == sid:
            return s
    raise SystemExit(f"no sound {sid!r} in the sound kit; name one as PACK:MEMBER, e.g. "
                     f"{next(iter(manifest['packs']))}:Audio/<file>.ogg")


def read_member(pid, member, manifest=None):
    """(the member's bytes, its pack): read from the cached zip after verifying the zip's digest, so
    a file edited in the unpacked folder can't reach a video."""
    manifest = manifest or load()
    pack = manifest["packs"].get(pid)
    if pack is None:
        raise SystemExit(f"no pack {pid!r} in the sound kit (packs: {', '.join(manifest['packs'])})")
    if not unpacked_member(pack, member):
        raise SystemExit(f"{member} is not one of {pid}'s sounds (members matching {', '.join(pack['unpack'])})")
    z = archive(pid, pack)
    if not fetch.verified(z, pack["sha256"]):
        raise SystemExit(f"the sound kit's {pid} is {'not fetched' if not z.exists() else 'not the pinned zip'}; "
                         f"run `{repair()}`")
    with zipfile.ZipFile(z) as f:
        try:
            return f.read(member), pack
        except KeyError:
            raise SystemExit(f"{pid} has no member {member}") from None
