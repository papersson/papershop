"""Assets: files a video uses that it did not draw, and where each one came from.

VIDEO/assets/ holds them (scenes reach them with `staticFile`, or the engine kit's `Shot`), and
assets/provenance.json holds one row per file: kind (capture, generated or supplied), source (a
URL, a prompt and tool, or a person), when, size, a hash, and the licence or note. Real captured UI
and imagery beat illustrations, and they are evidence: a launch video that shows a product's
screen must be able to say where the screen came from.

  studio capture URL VIDEO [--name N] [--size 1440x900]   a screenshot of a page, through the headless browser
  studio asset add VIDEO FILE --kind K --source S         copy a file in and record it
  studio asset list VIDEO                                 the provenance table
"""
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

from .env import resolve_browser

KINDS = ("capture", "generated", "supplied")


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
    dst = dir_of(video) / (name or src.name)
    shutil.copyfile(src, dst)
    return record(video, dst.name, kind, source, license)


def capture(video, url, name=None, size=(1440, 900), wait_ms=4000):
    """A screenshot of `url` at `size`, recorded as a capture. Uses the engine's headless shell (or an
    installed Chrome), so real pages are captured rather than redrawn."""
    browser, source = resolve_browser()
    if not browser:
        raise SystemExit("no browser: run `studio doctor --fetch`")
    slug = name or "".join(c if c.isalnum() else "-" for c in url.split("://")[-1])[:40].strip("-")
    out = dir_of(video) / f"{slug}.png"
    shell = Path(browser).name.startswith("chrome-headless-shell")
    cmd = [browser, "--headless" if shell else "--headless=new", "--disable-gpu", "--hide-scrollbars",
           f"--window-size={size[0]},{size[1]}", f"--virtual-time-budget={wait_ms}", f"--screenshot={out}", url]
    run = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
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
        rows = read(args.video)
        for r in rows:
            print(f"{r['file']:32} {r['kind']:9} {r['source'][:60]}" + (f"  [{r['license']}]" if r["license"] else ""))
        print(f"{len(rows)} assets")
        return 0
    if not args.file or not args.source:
        raise SystemExit("asset add needs FILE and --source (a URL, a prompt and tool, or a person)")
    r = add(args.video, args.file, args.kind, args.source, args.license, args.name)
    print(f"assets/{r['file']} recorded as {r['kind']}")
    return 0
