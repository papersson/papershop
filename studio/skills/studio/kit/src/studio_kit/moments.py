"""Moments: the frames the kit looks at, chosen in one place.

A moment is {id, clip, t, time, kind, label}: t is seconds into the clip (what an engine request
takes), time is seconds into the video. A moment that belongs to a sentence also names it
("sentence"); a sequence also lists its frames ("frames": clip times, at "fps").

  sentence-end  one per sentence, STILL_BEFORE_END before it ends, when its picture is complete
  spread        a clip with no narration, one every NO_NARRATION_STEP seconds, so it has stills too
  check-sample  evenly spaced inside a clip, its ends left out
  strip         consecutive frames around a time, inside its clip, to catch pops and overlaps

The cut's stills, the checks and the sheets take their frames from here, so a new kind is one more
function and every consumer can ask for it.
"""
from . import timeline as tl

STILL_BEFORE_END = 0.15     # seconds before a sentence's end, when its picture is complete
NO_NARRATION_STEP = 1.5     # seconds between stills of a clip that has no narration
STRIP_FRAMES = 12           # frames in a strip around a time


def _moment(c, local, kind, mid, label=None, **extra):
    return {"id": mid, "clip": c["id"], "t": round(local, 3), "time": round(c["start"] + local, 3),
            "kind": kind, "label": label if label is not None else f"{c['start'] + local:.1f} s", **extra}


def _scenes(t, clips):
    return [c for c in t["tracks"]["scene"] if clips is None or c["id"] in clips]


def sentence_ends(t, clips=None):
    """One moment near the end of every sentence, in narration order. `clips`: only these clips."""
    out = []
    for s in t["tracks"]["narration"]:
        if clips is not None and s["clip"] not in clips:
            continue
        c = tl.clip(t, s["clip"])
        out.append(_moment(c, max(s["start"], s["end"] - STILL_BEFORE_END) - c["start"], "sentence-end", s["id"],
                           s["caption"], sentence=s["id"]))
    return out


def spread(t, clips=None):
    """For each clip with no narration (a motion piece, a product film), a moment every
    NO_NARRATION_STEP seconds, at least three, none on the clip's last frame or after it."""
    narrated = {s["clip"] for s in t["tracks"]["narration"]}
    out = []
    for c in _scenes(t, clips):
        if c["id"] in narrated:
            continue
        dur = c["end"] - c["start"]
        n = max(3, int(dur / NO_NARRATION_STEP))
        out += [_moment(c, min(dur - 1 / t["fps"], (i + 0.5) * dur / n), "spread", f"{c['id']}_t{i + 1:02d}")
                for i in range(n)]
    return out


def stills(t, clips=None):
    """The cut's stills: every sentence's end, then the clips without narration."""
    return sentence_ends(t, clips) + spread(t, clips)


def even(t, n, clips=None):
    """`n` moments evenly spaced inside each clip, its ends left out."""
    out = []
    for c in _scenes(t, clips):
        dur = c["end"] - c["start"]
        out += [_moment(c, dur * (i + 1) / (n + 1), "check-sample", f"{c['id']}_e{i + 1:02d}") for i in range(n)]
    return out


def check_samples(t, per_clip, clips=None):
    """`per_clip` moments per clip, each a sentence's end, spread over the clip's sentences; evenly
    spaced when the clip has no narration, so a video without narration is still checked."""
    ends = sentence_ends(t, clips)
    out = []
    for c in _scenes(t, clips):
        mine = [m for m in ends if m["clip"] == c["id"]]
        if not mine:
            out += even(t, per_clip, [c["id"]])
            continue
        picks = {mine[min(len(mine) - 1, round(i * (len(mine) - 1) / max(1, per_clip - 1)))]["id"] for i in range(per_clip)}
        out += [m for m in mine if m["id"] in picks]
    return out


def sequence(t, clip, at, frames=STRIP_FRAMES, fps=None, kind="strip"):
    """`frames` consecutive frames at `fps` (the timeline's by default) around clip time `at`; any
    outside the clip are left out. The id names the frames and fps when they aren't the defaults, so
    two windows at one time don't share a file."""
    c = next((c for c in t["tracks"]["scene"] if c["id"] == clip), None)
    if c is None:
        raise SystemExit(f"no clip {clip!r} on the timeline")
    fps = fps or t["fps"]
    dur = c["end"] - c["start"]
    times = [x for x in (round(at + (i - frames // 2) / fps, 4) for i in range(frames)) if 0 <= x < dur]
    if not times:
        raise SystemExit(f"no frame of {clip} near {at} s: the clip runs from 0 to {dur:.2f} s")
    mid = f"{kind}_{clip}_{at}" + (f"_{frames}f" if frames != STRIP_FRAMES else "") + (f"_{fps:g}fps" if fps != t["fps"] else "")
    return _moment(c, at, kind, mid, frames=times, fps=fps)


def requests(moments):
    """Engine requests [{clip, t}] for moments' frames, a sequence's every frame in order."""
    return [{"clip": m["clip"], "t": x} for m in moments for x in m.get("frames", [m["t"]])]
