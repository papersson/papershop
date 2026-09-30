"""The timeline contract: `timeline.json` and `layout.json`, the only files an engine reads.

timeline.json
  fps, duration
  tracks.scene      [{id, engine, title, start, end}]           one generated clip per chapter
  tracks.narration  [{id, clip, text, caption, paragraph, start, end, words: [{w, start, end}]}]
  tracks.captions   [{start, end, lines}]                         chunked from the narration
  tracks.audio      [{file, start}]
  cues              {name: seconds}                               extra times scenes can wait on

Frame boundaries are rounded once, from absolute times, so clips rendered separately concatenate
to exactly the narration's length (rounding each clip's duration instead drifts a frame per clip).
"""
import json
import math
import re
import shutil
from difflib import SequenceMatcher
from pathlib import Path

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


def load(video):
    return json.loads((Path(video) / "timeline.json").read_text())


def save(video, timeline):
    (Path(video) / "timeline.json").write_text(json.dumps(timeline, indent=1, ensure_ascii=False) + "\n")


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


def split_phrases(text, width=LINE_CHARS * MAX_LINES):
    """Pieces of at most `width` characters, split after punctuation nearest the middle when a
    piece is too long, else at the word boundary nearest the middle."""
    if len(text) <= width:
        return [text]
    mid = len(text) / 2
    cuts = [m.end() for m in re.finditer(r"[,;:—]\s", text)] or [m.start() for m in re.finditer(r" ", text)]
    at = min(cuts, key=lambda i: abs(i - mid))
    return split_phrases(text[:at].strip(), width) + split_phrases(text[at:].strip(), width)


def chunk_captions(narration, fps=30):
    """One caption per sentence, or per phrase for long sentences, timed from word timings when
    present and from character counts otherwise."""
    chunks = []
    for s in narration:
        pieces = split_phrases(s["caption"])
        words = s.get("words") or []
        spans = _piece_spans(pieces, s, words)
        for piece, (a, b) in zip(pieces, spans):
            chunks.append({"start": round(a, 3), "end": round(b + TAIL, 3), "lines": wrap(piece)})
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
                              "start": line["start"], "end": line["end"], "words": line.get("words", [])})
    fps = DEFAULT_LAYOUT["fps"]
    return {"version": 1, "fps": fps, "duration": t["total"],
            "voice": {k: t[k] for k in ("engine", "voice", "model", "speed", "mode", "credit") if t.get(k) is not None},
            "tracks": {"scene": scenes, "narration": narration,
                       "captions": chunk_captions(narration, fps),
                       "audio": [{"file": audio_file, "start": 0.0}]},
            "cues": {}}


def from_tutor(lesson, video, engine="remotion"):
    """A timeline for an existing tutor lesson: its sentence timings and narration become the
    narration track, and each chapter becomes a scene clip."""
    lesson, video = Path(lesson), Path(video)
    t = json.loads((lesson / "audio" / "timings.json").read_text())
    (video / "audio").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(lesson / "audio" / "narration.mp3", video / "audio" / "narration.mp3")
    timeline = from_timings(t, engine)
    save(video, timeline)
    if not (video / "layout.json").exists():
        (video / "layout.json").write_text(json.dumps(DEFAULT_LAYOUT, indent=1) + "\n")
    return timeline
