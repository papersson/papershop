"""Assets: files a video uses that it did not draw, and where each one came from.

VIDEO/assets/ holds them (scenes reach them with `staticFile`, or the engine kit's `Shot`), and
assets/provenance.json holds one row per file: kind (capture, generated or supplied), source (a
URL, a prompt and tool, or a person), when, size, a hash, and the licence or note. Real captured UI
and imagery beat illustrations, and they are evidence: a launch video that shows a product's
screen must be able to say where the screen came from.

A `library` asset is a recorded sound copied from the verified sound kit (soundkit.py) into
assets/sounds/ID.EXT, so the video renders without the cache; its row names the pack and member,
the licence, the creator and the digest. Git ignores the sound itself (it is media), and the row is
enough to copy it again: `studio asset restore` does, from the kit, refusing a different digest.

  studio capture URL VIDEO [--name N] [--size 1440x900]   a screenshot of a page, through the headless browser
  studio asset add VIDEO FILE --kind K --source S         copy a file in and record it
  studio asset library VIDEO SOUND [--name ID]            a kit sound (an id, or PACK:MEMBER) into assets/sounds/
  studio asset restore VIDEO                              copy missing library sounds back from the kit
  studio asset list VIDEO [--credits]                     the provenance table, or the credits for the page
"""
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
from pathlib import Path

from . import proc
from .env import resolve_browser

KINDS = ("capture", "generated", "supplied", "library")
STEM = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")        # a library sound's id: a file stem, nothing more
LIBRARY_FILE = re.compile(r"sounds/[A-Za-z0-9][A-Za-z0-9._-]*\.[a-z0-9]+")


def plain(name, what="--name"):
    """`name` when it is a plain file name, which can only land in assets/: no folder separator, no
    `..`, nothing absolute."""
    if not name or name in (".", "..") or any(c in name for c in "/\\\0"):
        raise SystemExit(f"{what} {name!r} must be a plain file name, without folders or ..")
    return name


def library_path(video, file):
    """assets/FILE for a library row's FILE, which must be sounds/STEM.EXT: a hand-edited
    provenance.json can't send a copy outside assets/sounds/."""
    if not LIBRARY_FILE.fullmatch(file) or ".." in file:
        raise SystemExit(f"assets/provenance.json: library file {file!r} is not sounds/NAME.EXT; fix the row")
    return dir_of(video) / file


def _write(path, data):
    """`data` at `path` through a temporary file of its own, so two writers never share one."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".part")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def dir_of(video):
    d = Path(video) / "assets"
    d.mkdir(exist_ok=True)
    return d


def read(video):
    f = dir_of(video) / "provenance.json"
    return json.loads(f.read_text()) if f.exists() else []


def record(video, file, kind, source, license="", params=None):
    assert kind in KINDS, kind
    path = dir_of(video) / file
    rows = [r for r in read(video) if r["file"] != file]
    rows.append({"file": file, "kind": kind, "source": source, "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                 "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                 "license": license, "params": params or {}})
    (dir_of(video) / "provenance.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n")
    return rows[-1]


def add(video, src, kind, source, license="", name=None):
    src = Path(src).expanduser()
    if not src.is_file():
        raise SystemExit(f"{src} is not a file")
    dst = dir_of(video) / plain(name or src.name, "--name" if name else "the file's name")
    shutil.copyfile(src, dst)
    return record(video, dst.name, kind, source, license)


def _kit_sound(name):
    """(pack id, member, curated entry or None) for a sound named by its kit id or as PACK:MEMBER."""
    from . import soundkit
    if ":" in name:
        pid, member = name.split(":", 1)
        return pid, member, None
    s = soundkit.sound(name)
    return s["pack"], s["member"], s


def add_library(video, name, sid=None):
    """Copy a sound from the verified sound kit into assets/sounds/SID.EXT and record it as a
    library asset. `name` is a curated sound's id or PACK:MEMBER; `sid` defaults to the curated id,
    or the member's file name. Idempotent: the same sound again changes nothing. Refuses a member
    whose digest is not the manifest's, and a different file already at the destination."""
    from . import soundkit
    pid, member, entry = _kit_sound(name)
    data, pack = soundkit.read_member(pid, member)
    sha = hashlib.sha256(data).hexdigest()
    if entry and sha != entry["sha256"]:
        raise SystemExit(f"{pid}:{member} has sha256 {sha}, the sound kit says {entry['sha256']}; not copied")
    sid = sid or (entry["id"] if entry else Path(member).stem)
    if not STEM.fullmatch(plain(sid)):
        raise SystemExit(f"--name {sid!r} must be a file stem: letters, digits, '.', '_' or '-', starting with a letter or digit")
    file = f"sounds/{sid}{Path(member).suffix.lower()}"
    dst = library_path(video, file)
    if dst.exists() and hashlib.sha256(dst.read_bytes()).hexdigest() != sha:
        raise SystemExit(f"assets/{file} exists and is not {pid}:{member}; pick another --name or remove it")
    params = {"pack": pid, "member": member, "title": pack["title"], "version": pack["version"],
              "url": pack["url"], "pack_sha256": pack["sha256"], "creator": pack["creator"],
              "homepage": pack["homepage"], **({"sound": entry["id"], "type": entry["type"]} if entry else {})}
    old = next((r for r in read(video) if r["file"] == file), None)
    if dst.exists() and old and old["kind"] == "library" and old["sha256"] == sha and old["params"] == params:
        return old
    _write(dst, data)
    return record(video, file, "library", f"{pid}:{member}", pack["license"], params)


def restore(video):
    """Copy back every library sound whose file is missing (a fresh clone: Git ignores sound), from
    the kit, checked against the digest its row recorded. Returns the files restored."""
    from . import soundkit
    done = []
    for r in read(video):
        if r["kind"] != "library":
            continue
        path = library_path(video, r["file"])
        if path.exists():
            continue
        data, _ = soundkit.read_member(r["params"]["pack"], r["params"]["member"])
        if hashlib.sha256(data).hexdigest() != r["sha256"]:
            raise SystemExit(f"assets/{r['file']}: the kit's {r['source']} is not the recorded file "
                             f"(sha256 {r['sha256'][:12]}); the video was made with another kit")
        _write(path, data)
        done.append(r["file"])
    return done


def library_packs(video):
    """{pack id: [its library rows]} over the video's assets, in the order first used."""
    packs = {}
    for r in read(video):
        if r["kind"] == "library":
            packs.setdefault(r["params"]["pack"], []).append(r)
    return packs


def license_name(spdx):
    from .soundkit import LICENSES
    return LICENSES.get(spdx, spdx)


def credits(video):
    """The CREDITS block for a video's page or description: one line per pack its sounds came from."""
    packs = library_packs(video)
    if not packs:
        return ""
    lines = ["CREDITS", "Sound effects:"]
    for rows in packs.values():
        p, n = rows[0]["params"], len(rows)
        lines.append(f"  {p['title']} by {p['creator']}, {license_name(rows[0]['license'])}, {p['homepage']} "
                     f"({n} {'sound' if n == 1 else 'sounds'}: {', '.join(Path(r['file']).name for r in rows)})")
    return "\n".join(lines)


def page_credits(video):
    """The published page's credit lines for library sounds: one line, the packs by creator."""
    by = {}
    for rows in library_packs(video).values():
        by.setdefault((rows[0]["params"]["creator"], license_name(rows[0]["license"])), []).append(rows[0]["params"]["title"])
    return ["Sound effects: " + "; ".join(f"{', '.join(titles)} by {creator} ({lic})"
                                          for (creator, lic), titles in by.items())] if by else []


def capture(video, url, name=None, size=(1440, 900), wait_ms=4000):
    """A screenshot of `url` at `size`, recorded as a capture. Uses the engine's headless shell (or an
    installed Chrome), so real pages are captured rather than redrawn."""
    browser, source = resolve_browser()
    if not browser:
        raise SystemExit("no browser: run `studio doctor --fetch`")
    slug = plain(name) if name else "".join(c if c.isalnum() else "-" for c in url.split("://")[-1])[:40].strip("-")
    out = dir_of(video) / f"{slug}.png"
    shell = Path(browser).name.startswith("chrome-headless-shell")
    cmd = [browser, "--headless" if shell else "--headless=new", "--disable-gpu", "--hide-scrollbars",
           f"--window-size={size[0]},{size[1]}", f"--virtual-time-budget={wait_ms}", f"--screenshot={out}", url]
    run = proc.run(cmd, capture_output=True, text=True, timeout=120)
    if not out.exists():
        raise SystemExit(f"capture failed: {run.stderr.strip()[-400:]}")
    return record(video, out.name, "capture", url, params={"size": list(size), "wait_ms": wait_ms, "browser": source})


def parse_size(text):
    w, h = text.lower().split("x")
    return int(w), int(h)


def main_capture(args):
    r = capture(args.video, args.url, args.name, parse_size(args.size), args.wait)
    print(f"assets/{r['file']}  {r['bytes'] // 1024} KB  ({args.size})")
    return 0


def main_asset(args):
    if args.action == "list":
        if args.credits:
            print(credits(args.video) or "no library sounds: nothing to credit")
            return 0
        rows = read(args.video)
        for r in rows:
            print(f"{r['file']:32} {r['kind']:9} {r['source'][:60]}" + (f"  [{r['license']}]" if r["license"] else ""))
        print(f"{len(rows)} assets")
        return 0
    if args.action == "library":
        if not args.file:
            raise SystemExit("asset library needs SOUND: a sound kit id, or PACK:MEMBER")
        r = add_library(args.video, args.file, args.name)
        print(f"assets/{r['file']} from {r['source']} [{r['license']}], sha256 {r['sha256'][:12]}")
        return 0
    if args.action == "restore":
        done = restore(args.video)
        print(f"restored {len(done)} library sounds" + "".join(f"\n  assets/{f}" for f in done))
        return 0
    if not args.file or not args.source:
        raise SystemExit("asset add needs FILE and --source (a URL, a prompt and tool, or a person)")
    r = add(args.video, args.file, args.kind, args.source, args.license, args.name)
    print(f"assets/{r['file']} recorded as {r['kind']}")
    return 0
