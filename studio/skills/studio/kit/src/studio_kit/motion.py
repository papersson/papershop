"""Checks for motion pieces (genre motion), and the legibility and provenance checks every genre uses.

  dead      something new must happen every few seconds: frames sampled every second, and a run of
            identical frames longer than --limit seconds is a dead beat
  loop      with video.json "loop": true, the last frame must equal the first (within a whisker), or
            the loop stutters at the seam
  legible   every text box is at least 18 px tall at 1080p (a phone shows the frame at 360 px wide)
  provenance  every asset a scene refers to is in assets/ with a provenance row
"""
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

from . import assets
from . import timeline as tl
from .engine import Engine

MIN_TEXT_PX = 18
DEAD_LIMIT = 4.0
SEAM_TOLERANCE = 0.005          # fraction of bytes allowed to differ between first and last frame


def at_global(t, seconds):
    """(clip id, clip-local time) for a time on the whole timeline."""
    for c in t["tracks"]["scene"]:
        if c["start"] <= seconds < c["end"]:
            return c["id"], round(seconds - c["start"], 3)
    c = t["tracks"]["scene"][-1]
    return c["id"], round(c["end"] - c["start"] - 1 / t["fps"], 3)


def dead_beats(video, step=1.0, limit=DEAD_LIMIT, engine=None):
    engine, t = engine or Engine(video), tl.load(video)
    times = [i * step for i in range(int(t["duration"] / step))]
    with tempfile.TemporaryDirectory() as tmp:
        reqs = []
        for i, s in enumerate(times):
            clip, local = at_global(t, s)
            reqs.append({"clip": clip, "t": local, "out": str(Path(tmp) / f"{i:04d}.png"), "scale": 0.1})
        engine.stills(reqs)
        hashes = [hashlib.sha1(Path(r["out"]).read_bytes()).hexdigest() for r in reqs]
    rows, i = [], 0
    while i < len(hashes):
        j = i
        while j + 1 < len(hashes) and hashes[j + 1] == hashes[i]:
            j += 1
        span = (j - i + 1) * step
        if span > limit:
            rows.append({"check": "dead", "clip": "all", "t": times[i], "ok": False,
                         "detail": f"nothing changes from {times[i]:.0f} s to {times[j] + step:.0f} s ({span:.0f} s)"})
        i = j + 1
    return rows or [{"check": "dead", "clip": "all", "ok": True, "detail": f"something changes at least every {limit:.0f} s"}]


def _raw(png):
    return subprocess.run(["ffmpeg", "-v", "error", "-i", str(png), "-vf", "scale=192:-1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                          capture_output=True, check=True).stdout


def loop_seam(video, engine=None):
    engine, t = engine or Engine(video), tl.load(video)
    first, last = at_global(t, 0.0), at_global(t, t["duration"] - 1 / t["fps"])
    with tempfile.TemporaryDirectory() as tmp:
        engine.stills([{"clip": first[0], "t": first[1], "out": str(Path(tmp) / "a.png")},
                       {"clip": last[0], "t": last[1], "out": str(Path(tmp) / "b.png")}])
        a, b = _raw(Path(tmp) / "a.png"), _raw(Path(tmp) / "b.png")
    frac = sum(1 for x, y in zip(a, b) if abs(x - y) > 8) / max(1, len(a))
    return [{"check": "loop", "clip": "all", "ok": frac <= SEAM_TOLERANCE,
             "detail": f"{frac * 100:.2f}% of the last frame differs from the first"}]


def legible(video, samples=3, engine=None, boxes=None):
    from .check import _boxes
    engine = engine or Engine(video)
    _, frames = boxes or _boxes(video, samples, engine)
    rows = []
    for f in frames:
        small = sorted({(b["name"], round(b["h"])) for b in f["boxes"] if b.get("kind") == "text" and b["h"] < MIN_TEXT_PX and b["w"] > 2})
        rows.append({"check": "legible", "clip": f["clip"], "t": f["t"], "ok": not small,
                     "detail": "; ".join(f"{n[:28]!r} is {h} px tall" for n, h in small[:4])})
    return rows


def scene_assets(video):
    """File names the scenes refer to as assets: file="x.png" props and staticFile('x.png') calls."""
    found = set()
    for f in [*(Path(video) / "scenes").glob("*.ts*"), *(Path(video) / "scenes").glob("*.js")]:
        text = f.read_text()
        found |= set(re.findall(r'file=["\']([^"\']+)["\']', text))
        found |= set(re.findall(r'staticFile\(["\']([^"\']+)["\']\)', text))
    return sorted(found)


def provenance(video):
    rows = {r["file"] for r in assets.read(video)}
    used = scene_assets(video)
    missing = [f for f in used if f not in rows]
    absent = [f for f in used if not (Path(video) / "assets" / f).exists()]
    return [{"check": "provenance", "clip": "scenes", "ok": not missing and not absent,
             "detail": (f"no provenance row for {', '.join(missing)}" if missing else "") +
                       (f"; missing from assets/: {', '.join(absent)}" if absent else "") or f"{len(used)} assets used, all recorded"}]
