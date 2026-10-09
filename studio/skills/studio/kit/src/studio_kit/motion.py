"""Checks for motion pieces (genre motion), and the legibility and provenance checks every genre uses.

  dead      something new must happen every few seconds: frames sampled every second, and a run of
            identical frames longer than --limit seconds is a dead beat
  loop      with video.json "loop": true, the last frame must equal the first (within a whisker), or
            the loop stutters at the seam
  legible   every text box is at least 18 px tall at 1080p (a phone shows the frame at 360 px wide)
  provenance  every asset a scene refers to is in assets/ with a provenance row
  pacing    after a significant move, the picture holds at least HOLD_MIN before the next one starts
            (pacing_signal, moves)
"""
import hashlib
import json
import re
import tempfile
from pathlib import Path

from . import proc
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
    return proc.ffmpeg("-i", png, "-vf", "scale=192:-1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-", capture_output=True).stdout


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


# --- pacing: the hold after a move ------------------------------------------------------------------

PACING_FPS = 10         # samples a second: a 0.5 s hold is five
PACING_SIZE = (192, 108)   # pixels the frame is scaled to: whole moves show, texture and antialiasing don't
HOLD_MIN = 0.5          # seconds a significant move holds before the next one starts (style.md)
# Calibrated on the kit's templates (live and Remotion), in mean grey levels over the stage at PACING_SIZE.
# A sample moving at least MOVE_LEVEL (0.15% of the stage changing fully in 0.1 s) is movement; less is
# ambient (a jittering dot, a ticking counter, a slow fade). A run of movement is a significant move when
# it adds up to SIGNIFICANT, about 1% of the stage changing by 80 levels (a title fading in); a chapter
# tag fading out or an edge lighting up stays under it.
MOVE_LEVEL = 0.12
SIGNIFICANT = 0.8


def rendered_clip(video, t, cid, fmt=None):
    """A clip video `studio cut` (or export) rendered for the current scenes, or None."""
    from . import render
    tag = f"-{fmt.replace(':', 'x')}" if fmt and fmt != "16:9" else ""
    for q in ("final", "draft"):
        f = Path(video) / ".cache" / "clips" / f"{cid}-{q}{tag}-{render.clip_key(video, t, cid, q, fmt=fmt)}.mp4"
        if f.exists():
            return f
    return None


def _gray(args, crop, resample=""):
    """Raw grey frames at PACING_SIZE, the caption band cropped off, from an ffmpeg input."""
    w, h = PACING_SIZE
    raw = proc.ffmpeg(*args, "-vf", f"{resample}scale={w}:{h},crop={w}:{crop}:0:0,format=gray",
                      "-f", "rawvideo", "-", capture_output=True).stdout
    return [raw[i:i + w * crop] for i in range(0, len(raw), w * crop)]


def _crop(lay):
    """Rows of a PACING_SIZE frame above the caption band, even."""
    return int(PACING_SIZE[1] * (lay["height"] - lay["band"]["height"]) / lay["height"]) // 2 * 2


def _changes(times, frames, crop):
    """[(time, change)]: the mean absolute grey-level change from each sample to the next."""
    size = PACING_SIZE[0] * crop
    return [(round((a + b) / 2, 3), sum(map(abs, map(int.__sub__, x, y))) / size)
            for a, b, x, y in zip(times, times[1:], frames, frames[1:])]


def file_signal(path, t, lay, first, count):
    """A clip's signal as pacing_signal gives it, decoded from a rendered file that holds the clip's
    `count` frames from its frame `first`: a cut's own video.mp4 (first: where the clip starts in
    it) or its clip render (first 0), so a motion review finds the moves of the cut it judges."""
    crop, step = _crop(lay), max(1, round(t["fps"] / PACING_FPS))
    times = [k / t["fps"] for k in range(0, count, step)]
    frames = _gray(["-ss", f"{max(0.0, (first - 0.5) / t['fps']):.4f}", "-t", f"{count / t['fps']:.4f}", "-i", str(path)],
                   crop, f"fps={t['fps'] / step:g},")[:len(times)]
    return _changes(times[:len(frames)], frames, crop)


def pacing_signal(video, engine=None, clips=None, stills=True):
    """{clip: [(time, change)] or None}: each clip's stage (the caption band cropped off) sampled at
    PACING_FPS, and the mean absolute grey-level change from each sample to the next, at the time
    between them (clip seconds). The frames come from the clip's rendered video when a cut has one
    for the current scenes (decoding costs about 0.2 s a clip); otherwise, with stills, the engine
    renders every sample (about 70 ms each in the live engine), and without, the clip is None."""
    engine, t = engine or Engine(video), tl.load(video)
    fmt = getattr(engine, "fmt", None)
    lay = tl.layout(video, fmt)
    crop = _crop(lay)
    step = max(1, round(t["fps"] / PACING_FPS))
    out, todo = {}, []
    for c in t["tracks"]["scene"]:
        if clips is not None and c["id"] not in clips:
            continue
        times = [k / t["fps"] for k in range(0, tl.frames(t, c["id"])[1], step)]
        f = rendered_clip(video, t, c["id"], fmt)
        out[c["id"]] = (times, _gray(["-i", str(f)], crop, f"fps={t['fps'] / step:g},")[:len(times)]) if f else None
        if f is None and stills:
            todo.append((c["id"], times))
    if todo:
        with tempfile.TemporaryDirectory() as tmp:
            at = [(cid, x) for cid, times in todo for x in times]
            engine.stills([{"clip": cid, "t": round(x, 4), "out": str(Path(tmp) / f"{i:06d}.png"), "scale": PACING_SIZE[0] / lay["width"]}
                           for i, (cid, x) in enumerate(at)])
            frames = _gray(["-f", "image2", "-i", str(Path(tmp) / "%06d.png")], crop)
        i = 0
        for cid, times in todo:
            out[cid], i = (times, frames[i:i + len(times)]), i + len(times)
    return {cid: None if v is None else _changes(v[0], v[1], crop) for cid, v in out.items()}


def moves(signal, level=MOVE_LEVEL, significant=SIGNIFICANT, dt=1 / PACING_FPS):
    """The significant moves in a clip's signal: [(start, end, change)], a move being a run of samples
    changing at least `level` whose total change is at least `significant`."""
    runs = []
    for at, d in signal:
        if d < level:
            continue
        if runs and at - dt / 2 <= runs[-1][1] + 1e-6:
            runs[-1][1:] = [at + dt / 2, runs[-1][2] + d]
        else:
            runs.append([at - dt / 2, at + dt / 2, d])
    return [(round(a, 3), round(b, 3), round(c, 2)) for a, b, c in runs if c >= significant]


def pacing(video, engine=None, clips=None, hold=HOLD_MIN, stills=True):
    """Rows: a warning at every hold shorter than `hold` between two significant moves of a clip,
    else a passing row per clip; a clip with no rendered video, when stills are not to be rendered,
    is skipped. Ground truth is the rendered stage (pacing_signal)."""
    rows = []
    for cid, signal in pacing_signal(video, engine, clips, stills).items():
        if signal is None:
            rows.append({"check": "pacing", "clip": cid, "ok": True, "skipped": True,
                         "detail": "no rendered clip for these scenes: `studio cut` renders one; `--only pacing` samples stills (slower)"})
            continue
        found = moves(signal)
        short = [(a, b) for a, b in zip(found, found[1:]) if b[0] - a[1] < hold - 1e-6]
        for a, b in short:
            rows.append({"check": "pacing", "clip": cid, "t": a[1], "ok": True, "severity": "warning",
                         "detail": f"{b[0] - a[1]:.1f} s hold between the move at {a[0]:.1f}-{a[1]:.1f} s and the one "
                                   f"at {b[0]:.1f} s; hold at least {hold} s after a move"})
        if not short:
            rows.append({"check": "pacing", "clip": cid, "ok": True,
                         "detail": f"{len(found)} significant moves, each held at least {hold} s"})
    return rows
