"""The timeline contract: `timeline.json` and `layout.json`, the only files an engine reads.

timeline.json is a build product with one writer, `build(video)`. Each command owns one source file,
writes it and calls build; nothing carries over from an earlier timeline.json except through the
one-time `migrate`, and a hand edit to it is lost at the next build, which warns. Exactly one
source gives the base (scenes, narration, duration), in this order:

  footage/edit.json    studio edit       the edit list: footage track, each segment's sound, its words
  audio/timings.json   studio narrate    laid-out sentence timings; "timing": "estimate" | "narrated".
                                         An estimate lists no narration audio: an audio/narration.mp3
                                         left by an earlier narration would play against other times
  video.json clips     the builder       a piece with no narration in chapters: [{id, title?, seconds}]
                                         back to back
  video.json duration  studio new        a piece with no narration: one clip of that length

and the rest layer on:

  audio/words.json     studio align      recognised words, stamped with the narration they were heard
                                         in; attached only while that narration is current
  cues.json            the builder       named cues {name: seconds} scenes can wait on (reveal: cues
                                         come from the timings); anchors on sentences and words may
                                         join the numbers later
  audio/tracks.json    the builder       extra audio [{file, start, gain?, in?, out?, role?}] (music)
  audio/sfx.json       studio sfx        the effect cues; adds audio/sfx.wav to tracks.audio, which
                                         each mix renders against this timeline (audio.sources)
  audio/beats.json     studio beats      the beat grid, as "beats"
  layout.json          studio new        each format's caption line width (band.chars, and its own
                                         "formats"); every video has one, so it isn't in sources

timeline.json
  fps, duration, timing, voice, sources (the files it was built from)
  tracks.scene      [{id, engine, title, start, end}]           one generated clip per chapter
  tracks.narration  [{id, clip, text, caption, paragraph, start, end, words: [{w, start, end}]}]
  tracks.captions   [{start, end, lines, wrapped}]                chunked from the narration: lines are
                                                                  the 16:9 lines, wrapped {format: lines}
                                                                  every other format's (caption_lines)
  tracks.audio      [{file, start, role, gain?, in?, out?, fade?}]  role: narration | sfx | music | footage
  tracks.footage    [{id, file, in, out, start, end}]             footage videos only
  cues              {name: seconds}                               extra times scenes can wait on
  beats             {bpm, beats, downbeats, hits}

Captions are wrapped here only, for every format a video can be exported in: an engine shows the
lines stored for its layout's format, and fails on a format the timeline has none for.

Frame boundaries are rounded once, from absolute times, so clips rendered separately concatenate
to exactly the narration's length (rounding each clip's duration instead drifts a frame per clip).
"""
import hashlib
import json
import math
import re
import shutil
from difflib import SequenceMatcher
from pathlib import Path

from . import settings
from .workspace import atomic_json, locked

LINE_CHARS = 42
MAX_LINES = 2
MIN_SHOW = 1.2          # seconds a caption stays up at least
TAIL = 0.4              # seconds a caption outlasts its last word
WORD_SLACK = 0.2        # seconds a word may sit outside its sentence's narration timing
# Never end a caption line on one of these: the phrase it opens belongs on the next line.
NO_BREAK_AFTER = {"the", "a", "an", "of", "to"}

DEFAULT_LAYOUT = {
    "width": 1920, "height": 1080, "fps": 30,
    "band": {"height": 160, "style": "opaque"},
}


def _norm(w):
    return re.sub(r"[^\w]", "", w.lower())


def phrase_start(entry, phrase):
    """When a narration entry reaches `phrase`, in timeline seconds. The phrase's words are matched
    against the spoken words (`words`); when a spoken rule rewrote them (an acronym read as letters),
    the phrase's place in the written caption gives the time, proportionally. The Remotion kit's
    `phrase()` follows the same rule. Raises KeyError when the caption doesn't contain the phrase."""
    want = [w for w in map(_norm, phrase.split()) if w]
    got = [_norm(w["w"]) for w in entry.get("words", [])]
    for i in range(len(got) - len(want) + 1):
        if want and got[i:i + len(want)] == want:
            return entry["words"][i]["start"]
    k = entry.get("caption", entry.get("text", "")).find(phrase)
    if k < 0:
        raise KeyError(f"{entry.get('id')}: no phrase {phrase!r}")
    cap = entry.get("caption", entry.get("text", ""))
    return entry["start"] + (k / max(1, len(cap))) * (entry["end"] - entry["start"])


def timing(video, timeline=None):
    """Where the timeline's times came from: "estimate" or "narrated". Timelines written before this
    was recorded count as narrated when their narration audio exists."""
    t = timeline or load(video)
    if t.get("timing"):
        return t["timing"]
    audio = narration_audio(t)
    return "narrated" if audio and (Path(video) / audio.get("file", "")).exists() else "estimate"


def audio_role(entry, footage=()):
    """An audio entry's role. Entries written before roles were recorded are told by their file:
    the narration `studio narrate` writes, the sfx render, or a footage segment's recording."""
    if entry.get("role"):
        return entry["role"]
    f = entry.get("file", "")
    if f in ("audio/narration.mp3", "audio/narration.wav"):
        return "narration"
    if f == SFX["file"]:
        return "sfx"
    return "footage" if any(f == f"assets/{x['file']}" for x in footage) else "music"


def narration_audio(timeline):
    """The narration's tracks.audio entry, or None (a footage edit, a silent piece)."""
    return next((a for a in timeline.get("tracks", {}).get("audio", []) if audio_role(a) == "narration"), None)


def load(video):
    return json.loads((Path(video) / "timeline.json").read_text())


# Formats a video can be exported in. Each has its own stage (the frame above the caption band), so
# scenes lay out against the stage's size rather than fixed pixels; reframe type and UI per format,
# don't crop a 16:9 render to vertical.
FORMATS = {
    "16:9": {"width": 1920, "height": 1080, "band": {"height": 160}},
    "9:16": {"width": 1080, "height": 1920, "band": {"height": 340, "font": 54, "chars": 26}},
    "1:1": {"width": 1080, "height": 1080, "band": {"height": 200, "font": 44, "chars": 34}},
}


def layout(video, fmt=None):
    """layout.json, with a format's size and band applied: fmt is a key of FORMATS (or of the file's
    own "formats" overrides)."""
    p = Path(video) / "layout.json"
    base = json.loads(p.read_text()) if p.exists() else dict(DEFAULT_LAYOUT)
    if not fmt or fmt == "16:9":
        return base
    over = {**FORMATS.get(fmt, {}), **base.get("formats", {}).get(fmt, {})}
    if not over:
        raise SystemExit(f"unknown format {fmt!r}; known: {', '.join(FORMATS)}")
    return {**base, **over, "band": {**base["band"], **over.get("band", {})}, "format": fmt}


def layout_file(video, fmt):
    """A layout.json for the engine: the video's own for the default format, else a generated one."""
    if not fmt or fmt == "16:9":
        return Path(video) / "layout.json"
    out = Path(video) / ".cache" / "layouts" / f"{fmt.replace(':', 'x')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(layout(video, fmt), indent=1) + "\n")
    return out


def clip(timeline, clip_id):
    return next(c for c in timeline["tracks"]["scene"] if c["id"] == clip_id)


def frames(timeline, clip_id):
    """(first frame, frame count) of a clip on the video's frame grid."""
    fps, c = timeline["fps"], clip(timeline, clip_id)
    first, last = half_up(c["start"] * fps), half_up(c["end"] * fps)
    return first, last - first


def half_up(x):
    """Round halves up, as the engine's Math.round does: Python's round() sends 436.5 to 436, which
    put a chapter boundary one frame off from the engine's."""
    return math.floor(x + 0.5)


# --- captions -------------------------------------------------------------------------------------

def wrap(text, width=LINE_CHARS):
    """Greedy lines of at most `width` characters that never end on an article or preposition."""
    lines, cur = [], []
    for word in text.split():
        if cur and len(" ".join(cur + [word])) > width:
            carry = []
            while len(cur) > 1 and cur[-1].lower() in NO_BREAK_AFTER:
                carry.insert(0, cur.pop())
            lines.append(" ".join(cur))
            cur = carry
        cur.append(word)
    if cur:
        lines.append(" ".join(cur))
    return lines


def caption_widths(video=None):
    """Characters per caption line in each format a video can be exported in (FORMATS and
    layout.json's own "formats"), read from the layout the engine gets for it: {format: chars}.
    Without a video, the FORMATS defaults."""
    if video is None:
        return {f: v["band"].get("chars", LINE_CHARS) for f, v in FORMATS.items()}
    fmts = dict.fromkeys([*FORMATS, *layout(video).get("formats", {})])
    return {f: layout(video, f)["band"].get("chars", LINE_CHARS) for f in fmts}


def caption_lines(chunk, fmt=None):
    """A caption chunk's lines in a format; raises for a format the timeline wasn't wrapped for."""
    if not fmt or fmt == "16:9":
        return chunk["lines"]
    if fmt not in chunk.get("wrapped", {}):
        raise SystemExit(f"timeline.json has no {fmt} caption lines (built before they were kept, or for "
                         "another layout.json); `studio timeline VIDEO` rebuilds it")
    return chunk["wrapped"][fmt]


def split_phrases(text, width=LINE_CHARS * MAX_LINES):
    """Pieces of at most `width` characters, split after punctuation nearest the middle when a
    piece is too long, else at the word boundary nearest the middle."""
    if len(text) <= width:
        return [text]
    mid = len(text) / 2
    cuts = [m.end() for m in re.finditer(r"[,;:—]\s", text)] or [m.start() for m in re.finditer(r" ", text)]
    at = min(cuts, key=lambda i: abs(i - mid))
    return split_phrases(text[:at].strip(), width) + split_phrases(text[at:].strip(), width)


def chunk_captions(narration, fps=30, widths=None):
    """One caption per sentence, or per phrase for long sentences, timed from word timings when
    present and from character counts otherwise, and wrapped at `widths` (caption_widths)."""
    widths = widths or caption_widths()
    chunks = []
    for s in narration:
        pieces = split_phrases(s["caption"])
        words = s.get("words") or []
        spans = _piece_spans(pieces, s, words)
        for piece, (a, b) in zip(pieces, spans):
            chunks.append({"start": round(a, 3), "end": round(b + TAIL, 3), "lines": wrap(piece, widths["16:9"]),
                           "wrapped": {f: wrap(piece, w) for f, w in widths.items() if f != "16:9"}})
    gap = 2 / fps
    for cur, nxt in zip(chunks, chunks[1:]):
        cur["end"] = round(min(max(cur["end"], cur["start"] + MIN_SHOW), nxt["start"] - gap), 3)
    if chunks:
        chunks[-1]["end"] = round(max(chunks[-1]["end"], chunks[-1]["start"] + MIN_SHOW), 3)
    return chunks


def _piece_spans(pieces, sentence, words):
    a, b = sentence["start"], sentence["end"]
    if len(pieces) == 1:
        return [(words[0]["start"], words[-1]["end"]) if words else (a, b)]
    counts = [len(p.split()) for p in pieces]
    if words and len(words) == sum(counts):
        spans, i = [], 0
        for n in counts:
            spans.append((words[i]["start"], words[i + n - 1]["end"]))
            i += n
        return spans
    total, t, spans = sum(len(p) for p in pieces), a, []
    for p in pieces:
        dt = (b - a) * len(p) / total
        spans.append((t, t + dt))
        t += dt
    return spans


# --- word timings ---------------------------------------------------------------------------------

def _norm(w):
    return re.sub(r"[^\w]", "", w.lower())


def attach_words(timeline, heard):
    """Align recognised words [{w, start, end}] to the script's words and store them per sentence.
    Script words the recogniser missed get times interpolated between their matched neighbours.
    Returns (matched, total)."""
    script = [(s, w) for s in timeline["tracks"]["narration"] for w in s["caption"].split()]
    a, b = [_norm(w) for _, w in script], [_norm(h["w"]) for h in heard]
    times = [None] * len(script)
    for block in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(block.size):
            h = heard[block.b + k]
            times[block.a + k] = (h["start"], h["end"])
    matched = sum(t is not None for t in times)
    _interpolate(script, times)
    for s in timeline["tracks"]["narration"]:
        s["words"] = []
    for (s, w), (t0, t1) in zip(script, times):
        # The recogniser stretches a first word back over leading silence (to 0.0 at the video's
        # start), which would show its caption early; the narration's own timings bound the words.
        t0 = min(max(t0, s["start"] - WORD_SLACK), s["end"])
        t1 = max(min(t1, s["end"] + WORD_SLACK), t0)
        s["words"].append({"w": w, "start": round(t0, 3), "end": round(t1, 3)})
    return matched, len(script)


def _interpolate(script, times):
    i = 0
    while i < len(times):
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < len(times) and times[j] is None:
            j += 1
        # Bound the gap by the neighbours, or by the sentence edges at the ends of the track.
        lo = times[i - 1][1] if i > 0 else script[i][0]["start"]
        hi = times[j][0] if j < len(times) else script[j - 1][0]["end"]
        step = (hi - lo) / (j - i)
        for k in range(i, j):
            times[k] = (lo + step * (k - i), lo + step * (k - i + 1))
        i = j


# --- building a timeline --------------------------------------------------------------------------

def from_timings(t, engine="remotion", audio_file="audio/narration.mp3"):
    """A timeline from laid-out narration timings (what `studio narrate` and the tutor kit write):
    each chapter becomes a scene clip, each sentence a narration entry with its words."""
    scenes, narration = [], []
    for seg in t["segments"]:
        scenes.append({"id": seg["id"], "engine": engine, "title": seg["title"],
                       "start": seg["start"], "end": seg["end"]})
        for line in seg["lines"]:
            narration.append({"id": line["id"], "clip": seg["id"], "text": line["text"],
                              "caption": line["caption"], "paragraph": line["paragraph"],
                              "start": line["start"], "end": line["end"], "words": line.get("words", []),
                              **({"pause": line["pause"]} if "pause" in line else {})})
    fps = DEFAULT_LAYOUT["fps"]
    return {"version": 1, "fps": fps, "duration": t["total"],
            "voice": {k: t[k] for k in ("engine", "voice", "model", "speed", "mode", "credit") if t.get(k) is not None},
            "tracks": {"scene": scenes, "narration": narration,
                       "captions": chunk_captions(narration, fps),
                       "audio": [{"file": audio_file, "start": 0.0, "role": "narration"}]},
            "cues": {f"reveal:{s['id']}": s["pause"]["end"] for s in narration if "pause" in s}}


# --- the one writer --------------------------------------------------------------------------------

SFX = {"file": "audio/sfx.wav", "start": 0.0, "gain": -8, "role": "sfx"}
ROLES = ("narration", "sfx", "music", "footage")


def _read(p):
    return json.loads(p.read_text()) if p.exists() else None


def narration_stamp(video):
    """What recognised words were heard in: the narration's timings and its audio, hashed. Any new
    narration, an estimate included, changes it."""
    h = hashlib.sha256()
    for p in (Path(video) / "audio" / "timings.json", Path(video) / "audio" / "narration.mp3"):
        h.update(p.read_bytes() if p.exists() else b"")
        h.update(b"\0")
    return h.hexdigest()[:16]


def _base(video, cfg):
    """The timeline from the one source that gives scenes, narration and duration, and its name."""
    edl, timings = _read(video / "footage" / "edit.json"), _read(video / "audio" / "timings.json")
    if edl is not None:
        from .footage import compose
        return compose(video, edl), "footage/edit.json"
    if timings is not None:
        t = from_timings(timings, cfg["engine"])
        t["timing"] = timings.get("timing", "narrated")      # only real narrations kept timings before
        if t["timing"] == "estimate":
            t["tracks"]["audio"] = []
        return t, "audio/timings.json"
    if cfg.get("clips") or cfg.get("duration"):
        clips = cfg.get("clips") or [{"id": "s1", "title": cfg.get("title", "s1"), "seconds": float(cfg["duration"])}]
        scenes, at = [], 0.0
        for c in clips:
            end = round(at + float(c["seconds"]), 3)
            scenes.append({"id": c["id"], "engine": cfg["engine"], "title": c.get("title", c["id"]), "start": at, "end": end})
            at = end
        if cfg.get("clips") and cfg.get("duration") and abs(float(cfg["duration"]) - at) > 1e-6:
            raise SystemExit(f"video.json: duration {cfg['duration']} s and clips ({at} s) disagree; keep one")
        return {"version": 1, "fps": DEFAULT_LAYOUT["fps"], "duration": at, "cues": {},
                "tracks": {"scene": scenes, "narration": [], "captions": [], "audio": []}}, \
            "video.json clips" if cfg.get("clips") else "video.json duration"
    raise SystemExit(f"nothing to build {video / 'timeline.json'} from: narrate the script, `studio edit` "
                     "the footage, or give video.json a duration or clips")


def _stamp(video):
    return Path(video) / ".cache" / "studio" / "timeline.sha256"


def _hand_edited(video):
    """timeline.json as it is now, when its bytes are not what build last wrote (an agent used to
    editing it in place); else None. A timeline built before the stamp was kept is never reported."""
    f, stamp = Path(video) / "timeline.json", _stamp(video)
    if not f.exists() or not stamp.exists() or hashlib.sha256(f.read_bytes()).hexdigest() == stamp.read_text().strip():
        return None
    try:
        return json.loads(f.read_text())
    except ValueError:
        return {}


def build(video, quiet=False):
    """Write timeline.json from its sources (the contract above) and return it. Prints what it
    migrated and what it ignored, unless quiet (a command that builds again prints it then)."""
    video = Path(video)
    say = (lambda msg: None) if quiet else print
    a = video / "audio"
    with locked(video, "timeline"):
        edited = _hand_edited(video)
        if (video / "timeline.json").exists():
            migrate(video, load(video))
        t, base = _base(video, settings.load(video))
        used = [base]
        words = _read(a / "words.json")
        if words is not None and base == "audio/timings.json":
            if words.get("narration") == narration_stamp(video):
                matched, total = attach_words(t, words["words"])
                used.append("audio/words.json")
                say(f"timeline: aligned {matched} of {total} script words ({total - matched} interpolated)")
            else:
                say("timeline: audio/words.json was aligned against an earlier narration; ignored "
                      "(`studio align` again for word timings)")
        cues = _read(video / "cues.json")
        if cues is not None:
            bad = [k for k, v in cues.items() if not isinstance(v, (int, float)) or isinstance(v, bool)]
            if bad:
                raise SystemExit(f"cues.json: {', '.join(bad)} must be seconds")
            t["cues"] = {**cues, **t["cues"]}
            used.append("cues.json")
        sfx = (a / "sfx.json").exists()
        extra = _read(a / "tracks.json")
        if extra is not None:
            for e in extra:
                if "file" not in e or e.get("role", "music") not in ROLES:
                    raise SystemExit(f"audio/tracks.json: {e} needs a file, and a role among {', '.join(ROLES)}")
            # sfx.json owns audio/sfx.wav; a migrated copy of its entry gives way
            t["tracks"]["audio"] += [{"start": 0.0, **e, "role": e.get("role", "music")} for e in extra
                                     if not (sfx and e["file"] == SFX["file"])]
            used.append("audio/tracks.json")
        if sfx:
            t["tracks"]["audio"].append(dict(SFX))
            used.append("audio/sfx.json")
        beats = _read(a / "beats.json")
        if beats is not None:
            t["beats"] = beats
            used.append("audio/beats.json")
        if sfx:
            from .sfx import unresolved
            missing = unresolved(_read(a / "sfx.json"), t)
            if missing:      # a warning, not a stop: `studio sfx` builds before it replaces the effects
                say(f"warn: audio/sfx.json: no time for {', '.join(map(repr, missing))} in this timeline; "
                    "the next cut stops on it until `studio sfx VIDEO CUES` replaces the effects")
        # chunked last, from the final narration (its words included), at this video's line widths
        t["tracks"]["captions"] = chunk_captions(t["tracks"]["narration"], t["fps"], caption_widths(video))
        t["sources"] = used
        if edited is not None:      # printed even when quiet: the next build would find nothing to say
            parts = [k for k in sorted(set(edited) | set(t)) if k != "tracks" and edited.get(k) != t.get(k)]
            parts += [f"tracks.{k}" for k in sorted(set(edited.get("tracks", {})) | set(t["tracks"]))
                      if edited.get("tracks", {}).get(k) != t["tracks"].get(k)]
            print("warn: timeline.json was edited by hand since it was built" + (f" ({', '.join(parts)})" if parts else "")
                  + "; the edit is gone. It is built from its sources: cues go in cues.json, extra audio in "
                  "audio/tracks.json (the contract at the top of timeline.py)")
        atomic_json(video / "timeline.json", t)
        _stamp(video).parent.mkdir(parents=True, exist_ok=True)
        _stamp(video).write_text(hashlib.sha256((video / "timeline.json").read_bytes()).hexdigest())
        if not (video / "layout.json").exists():
            atomic_json(video / "layout.json", DEFAULT_LAYOUT)
    return t


def migrate(video, old):
    """Lift what a timeline.json from before `build` holds into the sources that now own it. Runs
    once: a built timeline names its sources, and an existing source is never overwritten (except a
    timings.json the old kit left stale, below). Clip engines are not lifted: the renderer always drew
    every clip with the video's engine. So on this first build a footage, duration or tutor piece on
    another engine re-renders once (the cache keys on the clip's engine label, which was "remotion"),
    and every video re-mixes once (each audio entry's new role enters the soundtrack's key)."""
    if "sources" in old:
        return
    a, lifted = video / "audio", []

    def lift(path, value):
        if value and not path.exists():
            atomic_json(path, value)
            lifted.append(str(path.relative_to(video)))

    tracks = old.get("tracks", {})
    footage, audio = tracks.get("footage", []), tracks.get("audio", [])
    if footage:
        gain = {e["start"]: e.get("gain", 0) for e in audio if audio_role(e, footage) == "footage"}
        lift(video / "footage" / "edit.json", [{"src": Path(f["file"]).stem, "in": f["in"], "out": f["out"],
                                                "gain": gain.get(f["start"], 0)} for f in footage])
    elif tracks.get("narration"):
        timings = _read(a / "timings.json")
        lift(a / "timings.json", _timings_of(video, old))
        if timings and "timing" not in timings and _sentences(timings) != _sentences(old):
            # The old kit's --estimate never wrote timings.json, so an estimate made after a narration
            # left that narration's timings behind; the timeline is the newer of the two.
            atomic_json(a / "timings.json", _timings_of(video, old))
            lifted.append("audio/timings.json")
    elif not (settings.raw(video).get("duration") or settings.raw(video).get("clips")):
        scenes = tracks.get("scene", [])
        if len(scenes) > 1:          # chapters split by hand in tracks.scene
            value = {"clips": [{"id": c["id"], "title": c.get("title", c["id"]), "seconds": round(c["end"] - c["start"], 3)}
                               for c in scenes]}
        else:
            value = {"duration": old["duration"]}
        atomic_json(video / "video.json", {**settings.raw(video), **value})
        lifted.append("video.json " + next(iter(value)))
    lift(video / "cues.json", {k: v for k, v in old.get("cues", {}).items() if not k.startswith("reveal:")})
    # the sfx cues were never kept, so its render stays as a plain track until `studio sfx` runs again
    lift(a / "tracks.json", [{**e, "role": audio_role(e, footage)} for e in audio if audio_role(e, footage) in ("music", "sfx")])
    lift(a / "beats.json", old.get("beats"))
    lift(a / "final.json", old.get("audio_finish"))
    timings = _read(a / "timings.json")
    # Words `studio align` attached in place belong to the old timeline's narration: lift them only
    # while timings.json is that same narration (a command that just wrote new timings is not).
    if timings and not footage and not (a / "words.json").exists() and _sentences(timings) == _sentences(old):
        said = {ln["id"]: ln.get("words", []) for seg in timings["segments"] for ln in seg["lines"]}
        if any(s.get("words") and s["words"] != said.get(s["id"]) for s in tracks.get("narration", [])):
            lift(a / "words.json", {"narration": narration_stamp(video),
                                    "words": [w for s in tracks["narration"] for w in s.get("words", [])]})
    if lifted:
        print("timeline: migrated into " + ", ".join(lifted))


def _sentences(x):
    """(id, text, start, end) of every sentence of a timings.json or a timeline."""
    lines = [ln for seg in x["segments"] for ln in seg["lines"]] if "segments" in x else x["tracks"]["narration"]
    return [(s["id"], s["text"], s["start"], s["end"]) for s in lines]


def _timings_of(video, t):
    """Narration timings from a timeline (from_timings inverted), for one made before
    audio/timings.json was kept: an estimate, or an imported lesson."""
    keep = ("id", "text", "caption", "paragraph", "start", "end", "words", "pause")
    segments = [{"id": c["id"], "title": c.get("title", c["id"]), "start": c["start"], "end": c["end"],
                 "lines": [{k: s[k] for k in keep if k in s} for s in t["tracks"]["narration"] if s["clip"] == c["id"]]}
                for c in t["tracks"]["scene"]]
    return {**t.get("voice", {}), "total": t["duration"], "segments": segments, "timing": timing(video, t)}


def from_tutor(lesson, video):
    """A video from an existing tutor lesson: its narration audio and sentence timings are copied in,
    and the timeline is built from them, one scene clip per chapter. A folder without video.json gets
    a minimal one, so the other commands accept it as a video."""
    lesson, video = Path(lesson), Path(video)
    (video / "audio").mkdir(parents=True, exist_ok=True)
    if not (video / "video.json").exists():
        atomic_json(video / "video.json", {"title": video.resolve().name.replace("-", " ").capitalize(), "version": "v1",
                                           "genre": "explainer", "engine": "remotion"})
    shutil.copyfile(lesson / "audio" / "narration.mp3", video / "audio" / "narration.mp3")
    (video / "audio" / "narration.wav").unlink(missing_ok=True)     # the mix would prefer an older wav
    t = json.loads((lesson / "audio" / "timings.json").read_text())
    atomic_json(video / "audio" / "timings.json", {**t, "timing": t.get("timing", "narrated")})
    return build(video)


def main(args):
    t = build(args.video)
    print(f"{len(t['tracks']['scene'])} clips, {len(t['tracks']['narration'])} sentences, {t['duration']:.1f} s "
          f"from {', '.join(t['sources'])}")
    return 0
