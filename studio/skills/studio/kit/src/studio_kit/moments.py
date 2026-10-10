"""Moments: the frames the kit looks at, chosen in one place.

A moment is {id, clip, t, time, kind, label}: t is seconds into the clip (what an engine request
takes), time is seconds into the video. A moment that belongs to a sentence also names it
("sentence"); a sequence also lists its frames ("frames": clip times, at "fps").

  sentence-end  one per sentence, STILL_BEFORE_END before it ends, when its picture is complete
  spread        a clip with no narration, one every NO_NARRATION_STEP seconds, so it has stills too
  event         one per named cue (cues.json, the beat sheet; not reveal: holds), EVENT_AFTER frames
                after its contact, so the contact's result is in the frame: id "ev_<name>"
  pause         the middle of every narration pause longer than PAUSE_MIN, what the viewer looks at
                while they think: id "pause_<sentence>", labelled "pause after <sentence>"
  check-sample  evenly spaced inside a clip, its ends left out
  strip         consecutive frames around a time, inside its clip, to catch pops and overlaps

The cut's stills, the checks and the sheets take their frames from here, so a new kind is one more
function and every consumer can ask for it.
"""
import hashlib
import re

from . import timeline as tl

STILL_BEFORE_END = 0.15     # seconds before a sentence's end, when its picture is complete
NO_NARRATION_STEP = 1.5     # seconds between stills of a clip that has no narration
STRIP_FRAMES = 12           # frames in a strip around a time
# Frames after an event's contact. On its own frame a move timed from the cue has not started (prog,
# pulse and spring are all 0 there); two frames on, at 30 fps, a 0.4 s ease-out is 42% of the way, a
# 0.6 s pulse at a third of its height: the result shows, and the next move has not begun.
EVENT_AFTER = 2
PAUSE_MIN = 0.8             # seconds: a shorter pause is a breath, with nothing new to look at


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


def _clip_at(t, frame):
    """The clip a frame of the video belongs to, by the frames each clip renders (timeline.frames)."""
    fps = t["fps"]
    return next((c for c in t["tracks"]["scene"] if tl.half_up(c["start"] * fps) <= frame < tl.half_up(c["end"] * fps)), None)


def event_id(name):
    """A still's id for an event: ev_<name>, its unsafe characters replaced and then a hash of the
    name added, so two names never share an id whatever order the cues come in."""
    safe = re.sub(r"[^\w.-]+", "-", name)
    return "ev_" + safe + ("" if safe == name else "-" + hashlib.sha1(name.encode()).hexdigest()[:6])


def _local(t, c, frame):
    """Clip seconds of a frame of the video: the clip renders its own frames from its first one."""
    return (frame - tl.half_up(c["start"] * t["fps"])) / t["fps"]


def events(t, clips=None):
    """One moment EVENT_AFTER frames after every named cue (not the reveal: holds), inside the clip
    that frame falls in; a cue past the video's end has none."""
    out = []
    for name, at in t.get("cues", {}).items():
        if name.startswith("reveal:"):
            continue
        frame = tl.half_up(at * t["fps"]) + EVENT_AFTER
        c = _clip_at(t, frame)
        if c is None or (clips is not None and c["id"] not in clips):
            continue
        out.append(_moment(c, _local(t, c, frame), "event", event_id(name), name, event=name))
    return out


def pauses(t, clips=None):
    """One moment in the middle of every narration pause longer than PAUSE_MIN, on a whole frame."""
    out = []
    for s in t["tracks"]["narration"]:
        p = s.get("pause")
        if not p or p["end"] - p["start"] <= PAUSE_MIN:
            continue
        frame = tl.half_up((p["start"] + p["end"]) / 2 * t["fps"])
        c = _clip_at(t, frame)
        if c is None or (clips is not None and c["id"] not in clips):
            continue
        out.append(_moment(c, _local(t, c, frame), "pause", f"pause_{s['id']}", f"pause after {s['id']}", after=s["id"]))
    return out


def stills(t, clips=None, extra=True):
    """The cut's stills in time order: every sentence's end and the clips without narration, and
    (extra) the events and long pauses. A sentence-end still names its sentence; the others don't."""
    found = sentence_ends(t, clips) + spread(t, clips) + (events(t, clips) + pauses(t, clips) if extra else [])
    return sorted(found, key=lambda m: m["time"])


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


def sequence(t, clip, at, frames=STRIP_FRAMES, fps=None, kind="strip", before=None):
    """`frames` consecutive frames at `fps` (the timeline's by default) around clip time `at`, `before`
    of them ahead of it (half by default; a motion review puts a contact fourth, so its anticipation
    shows before and its settle after); any outside the clip are left out. The id names the frames,
    fps and lead when they aren't the defaults, so two windows at one time don't share a file."""
    c = next((c for c in t["tracks"]["scene"] if c["id"] == clip), None)
    if c is None:
        raise SystemExit(f"no clip {clip!r} on the timeline")
    fps = fps or t["fps"]
    lead = frames // 2 if before is None else before
    dur = c["end"] - c["start"]
    times = [x for x in (round(at + (i - lead) / fps, 4) for i in range(frames)) if 0 <= x < dur]
    if not times:
        raise SystemExit(f"no frame of {clip} near {at} s: the clip runs from 0 to {dur:.2f} s")
    mid = f"{kind}_{clip}_{at}" + (f"_{frames}f" if frames != STRIP_FRAMES else "") + (f"_{fps:g}fps" if fps != t["fps"] else "") \
        + (f"_{lead}b" if lead != frames // 2 else "")
    return _moment(c, at, kind, mid, frames=times, fps=fps)


def requests(moments):
    """Engine requests [{clip, t}] for moments' frames, a sequence's every frame in order."""
    return [{"clip": m["clip"], "t": x} for m in moments for x in m.get("frames", [m["t"]])]
