"""Motion windows and sound sheets sampled from the cut being reviewed."""
import json
import math
import re
from pathlib import Path

from . import cuts, motion, proc
from . import timeline as tl
from .env import engine_dir
from .keys import clip_file

WINDOW_FRAMES = 12          # frames in an event's window
WINDOW_FPS = 15             # about this many a second: the timeline's fps over a whole step of frames
LEAD = 3                    # frames before the contact: it is the fourth
SETTLE = 5                  # frames after a move ends, at least, so its settle shows
MOVE_MAX_FRAMES = 24        # a long move's window stops here
SHEET_WIDTH = 320           # pixels a frame is wide on a sheet
SHEET_COLS = 12
# The frame labels' font, named outright: drawtext with no fontfile asks fontconfig, which printed
# "Fontconfig error: Cannot load default config file" once a sheet where it has no config. The first
# that exists: the Remotion engine's own mono font, then a system one.
LABEL_FONTS = (engine_dir("remotion") / "node_modules" / "@fontsource" / "ibm-plex-mono" / "files" / "ibm-plex-mono-latin-500-normal.woff",
               Path("/System/Library/Fonts/Menlo.ttc"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"))


# --- frames from the cut ---------------------------------------------------------------------------

def clip_render(video, rec, clip):
    """The clip's render cached under the key cut `rec` recorded, or None."""
    key = next((x["key"] for x in rec.get("clips", []) if x["id"] == clip), None)
    if not key:
        return None
    f = clip_file(video, clip, rec.get("quality", "draft"), key)
    return f if f.exists() else None


def source(video, n, rec, t, clip):
    """(file, the clip's first frame in it) holding the cut's frames of `clip`: the cut's own
    video.mp4, which spans every clip, else its clip render cached under the key the cut recorded,
    else None."""
    movie = cuts.cut_dir(video, n) / "video.mp4"
    if movie.exists():
        return movie, tl.frames(t, clip)[0]
    f = clip_render(video, rec, clip)
    return (f, 0) if f else None


def label_font():
    """drawtext's fontfile option for the first of LABEL_FONTS that exists, or "". The path is escaped
    twice: for the option's value, then for the filter graph."""
    found = next((f for f in LABEL_FONTS if f.is_file()), None)
    if not found:
        return ""
    value = re.sub(r"([\\':])", r"\\\1", str(found))
    return "fontfile=" + re.sub(r"([\\'\[\],;])", r"\\\1", value) + ":"


def sheet(path, frames, offset, contact, fps, out, width=SHEET_WIDTH):
    """Video frames `frames` (ascending; `offset` added gives their numbers in `path`) tiled into one
    strip, each labelled with its frame number and the contact outlined: a seek to half a frame
    before the first (frame-accurate), then each picked by its count from there. Where ffmpeg has no
    font for the labels, the strip goes without them."""
    lo, cols = frames[0], min(SHEET_COLS, len(frames))
    pick = "+".join(f"eq(n\\,{f - lo})" for f in frames)
    mark = f"drawbox=x=0:y=0:w=iw:h=ih:color=red:t=ih/40:enable='eq(n,{contact - lo})'," if contact in frames else ""
    label = f"drawtext={label_font()}text='%{{eif\\:n+{lo}\\:d}}':x=8:y=8:fontsize=h/9:fontcolor=white:box=1:boxcolor=black@0.6,"
    for text in (label, ""):
        try:
            proc.ffmpeg("-ss", f"{max(0.0, (lo + offset - 0.5) / fps):.4f}", "-i", str(path), "-vf",
                        f"{mark}{text}select='{pick}',scale={width}:-2,"
                        f"tile={cols}x{math.ceil(len(frames) / cols)}:padding=4:color=white", "-frames:v", "1", str(out))
            return bool(text)
        except proc.SubprocessError:
            if not text:
                raise
    return False


# --- windows -----------------------------------------------------------------------------------------

def _step(t):
    return max(1, round(t["fps"] / WINDOW_FPS))


def _narration(t, at):
    """What the narration says at video time `at`: the sentence it falls in (with the word, when
    timed), else the pause after the sentence before it."""
    said = t["tracks"]["narration"]
    s = next((s for s in said if s["start"] <= at <= s["end"]), None)
    if s:
        word = next((w["w"] for w in s.get("words") or [] if w["start"] <= at <= w["end"]), None)
        return {"sentence": s["id"], "said": s["caption"], **({"word": word} if word else {})}
    before = [s for s in said if s["end"] < at]
    return {"sentence": before[-1]["id"], "said": before[-1]["caption"], "pause": True} if before else {"sentence": None, "said": ""}


def effects(video, cut, t):
    """(the effects with their times on the cut's timeline, where they came from): the snapshot the
    cut kept (cuts/cutN/sfx.json), else audio/sfx.json resolved against the cut's timeline."""
    from .sfx import effect_id, place
    kept = cut / "sfx.json"
    if kept.exists():
        return [{**e, "effect": effect_id(i)} for i, e in enumerate(json.loads(kept.read_text())) if e.get("time") is not None], "the cut"
    p = Path(video) / "audio" / "sfx.json"
    if not p.exists():
        return [], "none"
    placed = place(json.loads(p.read_text()), t, strict=False)
    return ([{**e.cue, "time": e.time, "effect": effect_id(i)} for i, e in enumerate(placed) if e.time is not None],
            "the current sources (this cut kept none)")


def _clip_at(t, frame):
    return next((c for c in t["tracks"]["scene"] if c["start"] <= frame / t["fps"] < c["end"]), t["tracks"]["scene"][-1])


def _window(t, name, kind, contact, count, lead, bounds, sfx):
    """A window entry: `count` frames a step apart, `lead` of them before the contact frame, on the
    video's frame grid; frames outside `bounds` (first, end) are left out."""
    step, fps = _step(t), t["fps"]
    lo, hi = bounds
    frames = [f for f in (contact + (i - lead) * step for i in range(count)) if lo <= f < hi]
    times = [round(f / fps, 3) for f in frames]
    clips = list(dict.fromkeys(_clip_at(t, f)["id"] for f in frames))
    return {"name": name, "kind": kind, "clip": _clip_at(t, contact)["id"], "clips": clips,
            "time": round(contact / fps, 3), "contact_frame": contact, "contact_index": frames.index(contact),
            "frames": frames, "times": times, "fps": round(fps / step, 3), "sheet": f"sheets/{name}.png",
            "narration": _narration(t, contact / fps),
            "sfx": [{"effect": e.get("effect"), "type": e.get("type"), "cue": e["t"] if isinstance(e["t"], str) else None,
                     "time": round(e["time"], 3), "frame": tl.half_up(e["time"] * fps), **({"visual": e["visual"]} if e.get("visual") else {})}
                    for e in sfx if times[0] - 1e-6 <= e["time"] <= times[-1] + 1e-6]}


def windows(video, n, rec, t, sfx=(), lay=None, spans=True, chapter=None, event_video=None):
    """(windows in time order, events with no window and why). Every named event of the cut's beat
    sheet (not the reveal: holds) gets one, the contact fourth; then every significant move in its
    frames that no event window overlaps, its start fourth. `spans`: the frames come from the cut's
    video, so a window crosses into the next clip; otherwise it stays inside the contact's clip."""
    fps = t["fps"]
    end = tl.half_up(t["duration"] * fps)
    out, dropped, names = [], [], set()

    def unique(name):
        name = re.sub(r"[^\w.-]+", "-", name)
        while name in names:
            name += "_"
        names.add(name)
        return name

    def bounds(frame):
        if spans:
            return 0, end
        first, count = tl.frames(t, _clip_at(t, frame)["id"])
        return first, first + count
    for ev in tl.events(event_video or video, t):
        if chapter and ev["clip"] != chapter:
            continue
        if ev["name"].startswith("reveal:"):
            continue
        if ev["time"] < 0 or ev["frame"] < 0:
            dropped.append({"name": ev["name"], "time": ev["time"], "reason": "before the video's start"})
        elif ev["frame"] >= end or ev["clip"] is None:
            dropped.append({"name": ev["name"], "time": ev["time"], "reason": f"after the video's end ({t['duration']:g} s)"})
        else:
            out.append(_window(t, unique(ev["name"]), "event", ev["frame"], WINDOW_FRAMES, LEAD, bounds(ev["frame"]), sfx)
                       | {k: ev[k] for k in ("weight", "hitstop") if k in ev})
    lay = lay or tl.layout(video)
    events = list(out)
    for c in t["tracks"]["scene"]:
        if chapter and c["id"] != chapter:
            continue
        src = source(video, n, rec, t, c["id"])
        if src is None:
            raise SystemExit(f"cut {n}'s video and its clip renders are gone (studio clean --videos removes them); "
                             "make a fresh cut")
        first, count = tl.frames(t, c["id"])
        for a, b, _ in motion.moves(motion.file_signal(src[0], t, lay, src[1], count)):
            lo, hi = first + tl.half_up(a * fps), first + tl.half_up(b * fps)
            if any(w["frames"][0] <= hi and lo <= w["frames"][-1] for w in events):
                continue
            frames = min(MOVE_MAX_FRAMES, max(WINDOW_FRAMES, LEAD + math.ceil((hi - lo) / _step(t)) + SETTLE))
            out.append(_window(t, unique(f"move_{c['id']}_{a:.1f}"), "move", lo, frames, LEAD, bounds(lo), sfx))
    return sorted(out, key=lambda w: (w["frames"][0], w["name"])), dropped


def sound_sheets(video, n, found, t, bundle, movie, rec=None):
    """A sound sheet for each window with effects (sheets/NAME-sound.png, its path set on the window as
    sound_sheet), from the cut's own video.mp4, whose sound is the cut's: the window's span with a
    frame either side, its effects marked with their ids and tags, and the flags and picture marks of
    the audio-check made of this cut (out/audio-check.json, when its cut is this one and the cut's
    soundtrack is the one it measured: audio_check.sound_files). None without the cut's video
    (clip renders carry no sound) or when it has no sound track. Returns the windows given one."""
    from . import sound_sheet
    if not movie.exists() or not any(w["sfx"] for w in found) or not proc.ffprobe(movie, "-show_streams", "-select_streams", "a")["streams"]:
        return []
    report = Path(video) / "out" / "audio-check.json"
    report = json.loads(report.read_text()) if report.exists() else {}
    same = report.get("cut") == n and (rec or {}).get("sound") in report.get("sounds", [])
    measured = {e["id"]: e for e in report.get("effects", [])} if same else {}
    sentences = [{"id": s["id"], "start": s["start"], "end": s["end"]} for s in t["tracks"].get("narration", [])]
    done = []
    for w in found:
        if not w["sfx"]:
            continue
        marks = [{"id": e["effect"] or "fx", "type": e["type"], "t": e["time"], "flags": measured.get(e["effect"], {}).get("flags", []),
                  **({"visual": e["visual"]} if e.get("visual") else {}),
                  **({"picture_frame": measured[e["effect"]]["picture_frame"]} if "picture_frame" in measured.get(e["effect"], {}) else {})}
                 for e in w["sfx"]]
        name = w["sheet"].replace(".png", "-sound.png")
        sound_sheet.draw(movie, bundle / name, w["times"][0] - 1 / t["fps"], w["times"][-1] + 1 / t["fps"], marks, sentences,
                         fps=t["fps"], width=1200, title=f"{w['name']}  frames {w['frames'][0]}-{w['frames'][-1]}  (the cut sound)")
        w["sound_sheet"] = name
        done.append(w["name"])
    return done


