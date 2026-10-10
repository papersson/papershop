"""Checks for motion pieces (genre motion), and the legibility and provenance checks every genre uses.

  dead      something new must happen every few seconds: frames sampled every second, and a run of
            identical frames longer than --limit seconds is a dead beat
  loop      with video.json "loop": true, the last frame must equal the first (within a whisker), or
            the loop stutters at the seam
  legible   every text box is at least 18 px tall at 1080p (a phone shows the frame at 360 px wide)
  provenance  every asset a scene refers to is in assets/ with a provenance row
  pacing    after a significant move, the picture holds at least HOLD_MIN before the next one starts
            (pacing_signal, moves)

Picture motion is measured one way: a rendered stage decoded grey at PACING_SIZE, the caption band
cropped off (_gray), and the change from each frame to the next (_diffs). The pacing check and the
motion review sample it PACING_FPS a second (pacing_signal, file_signal); audio-check reads it frame by
frame (frame_signal), in the words a sound marks: where motion starts and ends, its peak, a cut.
"""
import hashlib
import json
import re
import statistics
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
# Ambient life that never stops (a wobble, a breathing glow) would join every move into one: the
# ambient level is the median change within AMBIENT_WINDOW seconds either side, at most AMBIENT_MAX (more
# is a long move, not background), and a sample is movement when it exceeds that level by MOVE_LEVEL.
AMBIENT_WINDOW = 4.0
AMBIENT_MAX = 0.2
# Back-to-back moves leave no quiet sample between them. A run splits where what changes moves to other
# pixels (under LINK_MIN of a sample's changed pixels touch the previous sample's: one thing stopped,
# another started), or where it dips below DIP of the peaks either side (one eased move ended, the next began).
CHANGED = 8             # grey levels a pixel must change by to count as changed
LINK_MIN = 0.05
DIP = 0.35
# A cut is a one-frame spike of full-frame change: at least CUT_SHARE of the stage's pixels change by
# CHANGED into the frame, and less than that into the frames either side. A cut to another background
# changes nearly all of it; on 109 rendered clips (Remotion and live) the kit's own fades and wipes change
# at most 0.48 of the stage a frame, but a flat full-stage fade, a flash or a fast pan over texture
# changes all of it frame after frame, so it is the spike, not the share alone, that makes a cut: a run
# of full-frame changes is motion. A cut between two scenes on one background changes only where their
# content differs (a median 0.17 for frames of different scenes), and reads as motion too.
CUT_SHARE = 0.6
# A small element (a 40 px label fading in over 0.3 s) changes the stage by less than a move's level a
# frame, but its pixels still change visibly: where motion starts or ends also counts a frame where at
# least VISIBLE_SHARE of the stage changes by CHANGED over the window's median share (its ambient
# life). Calibrated on a live-engine "1 ms" label fading in at 540p: 0.0009 to 0.0013 of the stage a
# frame, against 0 for a held frame's encoding noise.
VISIBLE_SHARE = 0.0005


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
    """Raw grey frames at PACING_SIZE, the caption band cropped off, from an ffmpeg input. Every decoded
    frame once, in order (passthrough): the raw muxer's default frame-rate mode duplicated the first
    frame after a seek in two seek positions out of three, so a window read one frame late."""
    w, h = PACING_SIZE
    raw = proc.ffmpeg(*args, "-vf", f"{resample}scale={w}:{h},crop={w}:{crop}:0:0,format=gray",
                      "-fps_mode", "passthrough", "-f", "rawvideo", "-", capture_output=True).stdout
    return [raw[i:i + w * crop] for i in range(0, len(raw), w * crop)]


def _seek(first, fps):
    """ffmpeg input options that start decoding a file at its frame `first` exactly: half a frame
    early, so the frame before is never the one decoded first."""
    return ["-ss", f"{max(0.0, (first - 0.5) / fps):.4f}"]


def _crop(lay):
    """Rows of a PACING_SIZE frame above the caption band, even."""
    return int(PACING_SIZE[1] * (lay["height"] - lay["band"]["height"]) / lay["height"]) // 2 * 2


def _diffs(frames, crop):
    """[(change, link, share)] from each frame to the next: the mean absolute grey-level change, the
    share of its changed pixels that touch the previous change's (1 when either changed none), and the
    share of the stage's pixels that changed (by more than CHANGED)."""
    size = PACING_SIZE[0] * crop
    out, before = [], frozenset()
    for x, y in zip(frames, frames[1:]):
        diff = list(map(abs, map(int.__sub__, x, y)))
        mask = frozenset(i for i, v in enumerate(diff) if v > CHANGED)
        link = len(mask & before) / min(len(mask), len(before)) if mask and before else 1.0
        out.append((sum(diff) / size, round(link, 3), round(len(mask) / size, 4)))
        before = mask
    return out


def _changes(times, frames, crop):
    """[(time, change, link, share)]: _diffs from each sample to the next, at the time between them."""
    return [(round((a + b) / 2, 3), *d) for a, b, d in zip(times, times[1:], _diffs(frames, crop))]


def file_signal(path, t, lay, first, count):
    """A clip's signal as pacing_signal gives it, decoded from a rendered file that holds the clip's
    `count` frames from its frame `first`: a cut's own video.mp4 (first: where the clip starts in
    it) or its clip render (first 0), so a motion review finds the moves of the cut it judges."""
    crop, step = _crop(lay), max(1, round(t["fps"] / PACING_FPS))
    times = [k / t["fps"] for k in range(0, count, step)]
    frames = _gray([*_seek(first, t["fps"]), "-t", f"{count / t['fps']:.4f}", "-i", str(path)],
                   crop, f"fps={t['fps'] / step:g},")[:len(times)]
    return _changes(times[:len(frames)], frames, crop)


def pacing_signal(video, engine=None, clips=None, stills=True):
    """{clip: [(time, change, link, share)] or None}: each clip's stage (the caption band cropped off)
    sampled at PACING_FPS, and the change from each sample to the next (_diffs), at the time between
    them (clip seconds). The frames come from the clip's rendered video when a cut has one
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
    """The significant moves in a clip's signal [(time, change, link?, ...)]: [(start, end, change)]. A move
    is a run of samples changing at least `level` over the ambient level, split where its change jumps
    to other pixels or dips between two peaks; it is significant when its change adds up to
    `significant`. Moves split from one run follow each other with no hold."""
    d = [x[1] for x in signal]
    k = round(AMBIENT_WINDOW / dt)
    over = [v - min(AMBIENT_MAX, statistics.median(d[max(0, i - k):i + k + 1])) for i, v in enumerate(d)]
    runs = []
    for i, v in enumerate(over):
        if v < level:
            continue
        if runs and runs[-1][-1] == i - 1 and (signal[i][2] if len(signal[i]) > 2 else 1.0) >= LINK_MIN:
            runs[-1].append(i)
        else:
            runs.append([i])

    def split(run):
        for j in range(1, len(run) - 1):
            a, b, c = over[run[j - 1]], over[run[j]], over[run[j + 1]]
            if b <= a and b <= c and b < DIP * min(max(over[i] for i in run[:j]), max(over[i] for i in run[j + 1:])):
                return [run[:j + 1]] + split(run[j + 1:])
        return [run]
    found = [(signal[r[0]][0] - dt / 2, signal[r[-1]][0] + dt / 2, sum(d[i] for i in r)) for run in runs for r in split(run)]
    return [(round(a, 3), round(b, 3), round(c, 2)) for a, b, c in found if c >= significant]


# --- frame by frame: what a sound marks -------------------------------------------------------------

def frame_signal(path, lay, fps, first, count):
    """[(frame, change, link, share)] for frames first+1 .. first+count-1 of a rendered file: the change
    into each from the frame before it (_diffs), on the stage the pacing signal samples but at the
    file's own frame rate, decoded from its frame `first` exactly. The helpers below read it."""
    crop = _crop(lay)
    frames = _gray([*_seek(first, fps), "-i", str(path), "-frames:v", str(count)], crop)
    return [(first + k, *d) for k, d in enumerate(_diffs(frames, crop), 1)]


def moving(signal, fps):
    """The frames of a frame signal that move: they change by more than MOVE_LEVEL, a 0.1 s sample's
    level, shared out over the frames of a sample at `fps`, and are not cuts."""
    level, cut = MOVE_LEVEL * PACING_FPS / fps, set(cuts(signal))
    return [f for f, change, _, share in signal if change > level and f not in cut]


def changing(signal, fps):
    """The frames that move, or where a small element visibly changes (VISIBLE_SHARE of the stage over
    the window's median share); a single still frame between two changing ones (an ease's step that
    rounded to nothing) counts as changing. Where motion starts and ends is read from these."""
    import statistics
    if not signal:
        return []
    ambient, cut = statistics.median(r[3] for r in signal), set(cuts(signal))
    on = set(moving(signal, fps)) | {f for f, _, _, share in signal if share - ambient >= VISIBLE_SHARE and f not in cut}
    return sorted(on | {f for f, *_ in signal if f not in cut and f - 1 in on and f + 1 in on})


def starts(signal, fps):
    """The frames where motion starts: the first frame that differs after one that does not (changing).
    Motion under way at the window's start has no start in it."""
    on = set(changing(signal, fps))
    return [f for f, *_ in signal[1:] if f in on and f - 1 not in on]


def ends(signal, fps):
    """The frames where motion ends: the last frame that differs before one that does not (where a
    moving thing lands). Motion still under way at the window's end has no end in it."""
    on = set(changing(signal, fps))
    return [f for f, *_ in signal[:-1] if f in on and f + 1 not in on]


def peak(signal, fps):
    """The moving frame that changes most (the peak of a move's speed), or None when nothing moves."""
    on = set(moving(signal, fps))
    return max((r for r in signal if r[0] in on), key=lambda r: r[1], default=(None,))[0]


def cuts(signal):
    """The frames that are cuts: at least CUT_SHARE of the stage changes into them and less than that
    into the frame before and the frame after (where the signal has them). A run of full-frame
    changes, a fade, a flash in and out or a fast pan, is motion."""
    share = {f: s for f, _, _, s in signal}
    return [f for f, _, _, s in signal if s >= CUT_SHARE and share.get(f - 1, 0) < CUT_SHARE and share.get(f + 1, 0) < CUT_SHARE]


def is_cut(signal, frame):
    """Whether `frame` is a cut in a frame signal."""
    return frame in cuts(signal)


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
