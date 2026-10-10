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
  cues.json            the builder       the beat sheet: named events scenes and effects are timed from
                                         (reveal: cues come from the timings' holds). A value is seconds,
                                         or an anchor on the narration that follows its words:
                                           {"sentence": "s2_03", "at": "start" | "end" | "word" | "phrase",
                                            "word": i, "phrase": "text", "offset": seconds}
                                         at "start"/"end": the sentence's ends; "phrase": when the voice
                                         reaches the phrase (phrase_start); "word": the start of caption
                                         word i, counted from the phrase's first word when one is given.
                                         `at` defaults to "phrase" with a phrase, "word" with a word, else
                                         "start". A phrase also finds the sentence after a renumbering: the
                                         named sentence when it still says the phrase, else the one sentence
                                         that does. An anchor whose words are gone, or whose phrase several
                                         sentences say, stops the build naming the cue (event_time)
  captions.json        the builder       caption chunks whose words are kept: [{text} or {lines,
                                         wrapped?}] (other formats wrapped from them), each either
                                         anchored, {anchor: {sentence, words?, text?}}, so it follows its
                                         words when the narration moves (a chunk copied from timeline.json
                                         is: that is how one is locked), or fixed at {start, end}, which
                                         warns once the narration changes. The kit chunks only the words
                                         and times they don't cover; {start, end, lines: []} blanks a span
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
  tracks.captions   [{start, end, lines, wrapped, anchor?}]       chunked from the narration, and
                                                                  captions.json's: lines are the 16:9
                                                                  lines, wrapped {format: lines} every
                                                                  other format's (caption_lines), anchor
                                                                  {sentence, words: [i, j], text} the
                                                                  words a chunk shows
  tracks.audio      [{file, start, role, gain?, in?, out?, fade?}]  role: narration | sfx | music | footage
  tracks.footage    [{id, file, in, out, start, end}]             footage videos only
  cues              {name: seconds}                               every cue resolved and on the frame grid
  beats             {bpm, beats, downbeats, hits}

Captions are wrapped here only, for every format a video can be exported in: an engine shows the
lines stored for its layout's format, and fails on a format the timeline has none for.

Every cue, a plain number included, is moved onto the frame it falls on (frame_time, half up as
the engines' frameOf), so a move and an effect timed from one cue start on the same frame. Engines
read the numbers through cue(); Python reads an anchor's time through event_time.

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
NO_BREAK_AFTER = {"the", "a", "an", "of", "to", "and", "or", "in", "on", "for", "with"}
PAUSES = (",", ";", ":", "—")    # a word ending in one is where a long sentence splits best

DEFAULT_LAYOUT = {
    "width": 1920, "height": 1080, "fps": 30,
    "band": {"height": 160, "style": "opaque"},
}


def _norm(w):
    return re.sub(r"[^\w]", "", w.lower())


def _words_at(words, phrase):
    """The index in `words` where the phrase's words begin, compared without case or punctuation."""
    want, got = [w for w in map(_norm, phrase.split()) if w], [_norm(w) for w in words]
    return next((i for i in range(len(got) - len(want) + 1) if want and got[i:i + len(want)] == want), None)


def phrase_start(entry, phrase):
    """When a narration entry reaches `phrase`, in timeline seconds: the start of the spoken word it
    begins on (`words`, compared without case or punctuation); else, when there are none (an estimate)
    or a spoken rule rewrote them (an acronym read as letters), its caption word's share of the
    sentence's time, as _word_times shares it; else, for a part of a word, its exact place in the
    caption. The engines' phraseStart follows the same rule. Raises KeyError when the caption doesn't
    contain the phrase."""
    i = _words_at([w["w"] for w in entry.get("words", [])], phrase)
    if i is not None:
        return entry["words"][i]["start"]
    cap = entry.get("caption", entry.get("text", ""))
    words, span = cap.split(), entry["end"] - entry["start"]
    i = _words_at(words, phrase)
    if i is not None:
        return entry["start"] + span * len(" ".join(words[:i] + [""])) / max(1, len(" ".join(words)))
    k = cap.find(phrase)
    if k < 0:
        raise KeyError(f"{entry.get('id')}: no phrase {phrase!r}")
    return entry["start"] + (k / max(1, len(cap))) * span


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


# --- events: cues.json's named times ---------------------------------------------------------------

AT = ("start", "end", "word", "phrase")
ANCHOR_KEYS = {"sentence", "at", "word", "phrase", "offset"}


def frame_time(t, fps):
    """A time moved onto the frame it falls on (half up, as the engines' frameOf)."""
    return round(half_up(t * fps) / fps, 6)


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def anchor_problem(spec):
    """Why a cues.json value is neither seconds nor a well-formed anchor, or None."""
    if _num(spec):
        return None
    if not isinstance(spec, dict) or set(spec) - ANCHOR_KEYS:
        return "must be seconds or an anchor {sentence, at, word?, phrase?, offset?}"
    at = _at(spec)
    if not isinstance(spec.get("sentence", ""), str) or not isinstance(spec.get("phrase", ""), str) or \
            not (spec.get("sentence") or spec.get("phrase", "").strip()):
        return "needs a sentence id or a phrase"
    if at not in AT:
        return f"at must be one of {', '.join(AT)}"
    if at == "word" and not (type(spec.get("word")) is int and spec["word"] >= 0):
        return "at word needs a word index (0 is the first)"
    if at == "phrase" and not spec.get("phrase", "").strip():
        return "at phrase needs a phrase"
    if not _num(spec.get("offset", 0)):
        return "offset must be seconds"
    return None


def _at(spec):
    return spec.get("at") or ("word" if "word" in spec else "phrase" if spec.get("phrase") else "start")


def _phrase_word(s, phrase):
    """The caption word a phrase starts on in sentence s, or None: its words matched, else (a spoken
    rule rewrote them, a part of a word) its place in the caption."""
    cap = s.get("caption", s.get("text", ""))
    i = _words_at(cap.split(), phrase)
    if i is not None:
        return i
    k = cap.find(phrase)
    if k < 0:
        return None
    return len(cap[:k].split()) - (1 if k and not cap[k - 1].isspace() else 0)


def _event_sentence(narration, spec):
    """(sentence, first word of the phrase) an anchor names in this narration; ValueError if none."""
    sid, phrase = spec.get("sentence"), spec.get("phrase")
    by_id = {s["id"]: s for s in narration}
    if not phrase:
        if sid not in by_id:
            raise ValueError(f"no sentence {sid} in the narration (an anchor with a phrase follows a renumbering)")
        return by_id[sid], 0
    if sid in by_id and _phrase_word(by_id[sid], phrase) is not None:
        return by_id[sid], _phrase_word(by_id[sid], phrase)
    found = [(s, _phrase_word(s, phrase)) for s in narration if _phrase_word(s, phrase) is not None]
    if len(found) == 1:
        return found[0]
    if not found:
        raise ValueError(f"no sentence says {phrase!r} any more" + (f" ({sid} doesn't)" if sid else ""))
    raise ValueError(f"{phrase!r} is said in {', '.join(s['id'] for s, _ in found)}: name the sentence it belongs to")


def resolve_event(timeline, spec):
    """(seconds on the frame grid, sentence id or None) of a cues.json value: see event_time."""
    problem = anchor_problem(spec)
    if problem:
        raise ValueError(problem)
    if _num(spec):
        return frame_time(float(spec), timeline["fps"]), None
    s, first = _event_sentence(timeline["tracks"]["narration"], spec)
    at = _at(spec)
    if at in ("start", "end"):
        t = s[at]
    elif at == "phrase":    # as a scene's phrase() gives it; it finds what _event_sentence found, so never raises
        t = phrase_start(s, spec["phrase"])
    else:
        times, k = _word_times(s, s["caption"].split()), first + spec["word"]
        if k >= len(times):
            raise ValueError(f"{s['id']} has {len(times)} words, no word {k}")
        t = times[k][0]
    return frame_time(t + spec.get("offset", 0), timeline["fps"]), s["id"]


def event_time(timeline, spec):
    """A cues.json value in timeline seconds, on the frame grid (frame_time): a number as given, an
    anchor where its words are in this timeline's narration (the contract above). The one rule for
    the build and for Python callers. Raises ValueError saying why an anchor has no time."""
    return resolve_event(timeline, spec)[0]


def _resolve_cues(cues, t):
    """cues.json resolved against the timeline being built; stops naming the first cue with no time."""
    if not isinstance(cues, dict):
        raise SystemExit("cues.json must be an object {name: seconds or anchor}")
    out = {}
    for k, v in cues.items():
        problem = anchor_problem(v)
        if problem:
            raise SystemExit(f"cues.json: {k} {problem} (the contract at the top of timeline.py)")
        try:
            out[k] = event_time(t, v)
        except (ValueError, KeyError) as e:
            raise SystemExit(f"cues.json: the cue {k!r} has no time: {e}; anchor it again or remove it")
    return out


def describe_anchor(spec, resolved=None):
    """An anchor in words, for listings: "s2_03 word 4 of 'hits the floor' +0.10 s"."""
    if _num(spec):
        return "seconds"
    at = _at(spec)
    out = spec.get("sentence") or "the sentence"
    out += {"start": " start", "end": " end", "phrase": "", "word": f" word {spec.get('word')}"}[at]
    if spec.get("phrase"):
        out += (" of " if at == "word" else " at ") + repr(spec["phrase"])
    if spec.get("offset"):
        out += f" {spec['offset']:+.2f} s"
    if resolved and resolved != spec.get("sentence"):
        out += f" (now {resolved})"
    return out


def events(video, t=None):
    """Every cue with its resolved time: [{name, time, frame, clip, t, anchor}], in time order.
    cues.json's carry their anchor; reveal: cues are the timings' holds."""
    t = t or load(video)
    raw = _read(Path(video) / "cues.json") or {}
    rows = []
    for name, at in t.get("cues", {}).items():
        spec = raw.get(name) if not name.startswith("reveal:") else None
        sid = None
        if isinstance(spec, dict):
            try:
                sid = resolve_event(t, spec)[1]
            except ValueError:
                pass
        c = next((c for c in t["tracks"]["scene"] if c["start"] <= at < c["end"]), None)
        rows.append({"name": name, "time": at, "frame": half_up(at * t["fps"]), "clip": c["id"] if c else None,
                     "t": round(at - c["start"], 3) if c else None,
                     "anchor": "hold end" if name.startswith("reveal:") else describe_anchor(spec, sid) if spec is not None else "seconds"})
    return sorted(rows, key=lambda r: (r["time"], r["name"]))


# --- captions -------------------------------------------------------------------------------------

def wrap(text, width=LINE_CHARS):
    """As few lines of at most `width` characters as hold the text, as even in length as they can
    be (a greedy fill left a word or two alone on the last line). A line ends on a word in
    NO_BREAK_AFTER, or holds a lone word, only when no other break fits; a word longer than the
    width gets a line of its own."""
    words = text.split()
    n = len(words)
    span = lambda i, j: sum(map(len, words[i:j])) + j - i - 1
    best = {0: ((0, 0), [])}      # words placed -> ((faults, sum of squared lengths), breaks), per line count
    for _ in range(n):
        nxt = {}
        for i, ((faults, squares), breaks) in best.items():
            for j in range(i + 1, n + 1):
                k = span(i, j)
                if k > width and j > i + 1:
                    break
                cost = (faults + (j < n and words[j - 1].lower() in NO_BREAK_AFTER) + (j == i + 1 and n > 1), squares + k * k)
                if j not in nxt or cost < nxt[j][0]:
                    nxt[j] = (cost, breaks + [j])
        if n in nxt:
            cuts = [0] + nxt[n][1]
            return [" ".join(words[a:b]) for a, b in zip(cuts, cuts[1:])]
        best = nxt
    return []


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


def split_phrases(text, widths=None):
    """A sentence in pieces that each wrap to at most MAX_LINES lines at every width (by default the
    formats' caption_widths): the chunks are shared by every format, so the narrowest decides. A
    long piece splits after a pause near its middle, else at the word boundary nearest it, and not
    after a word in NO_BREAK_AFTER nor leaving a lone word when another cut will do. Pieces are
    whole words in order, so they map onto the sentence's word timings."""
    widths = list(widths or caption_widths().values())
    words = text.split()
    if len(words) < 2 or all(len(wrap(text, w)) <= MAX_LINES for w in widths):
        return [text.strip()]
    half = len(" ".join(words)) / 2

    def cost(k):            # a cut after words[k - 1]
        at, last = len(" ".join(words[:k])), words[k - 1]
        bad = last.lower() in NO_BREAK_AFTER or min(k, len(words) - k) < 2
        return bad, abs(at - half) - (half / 2 if last.endswith(PAUSES) else 0)
    k = min(range(1, len(words)), key=cost)
    return split_phrases(" ".join(words[:k]), widths) + split_phrases(" ".join(words[k:]), widths)


def chunk_captions(narration, fps=30, widths=None, kept=(), warn=print):
    """One caption per sentence, or per phrase for long sentences, timed from word timings when
    present and from character counts otherwise, and wrapped at `widths` (caption_widths). Each
    chunk names the words it shows: "anchor": {sentence, words: [first, past the last], text}.

    The builder's chunks `kept` (captions.json) keep their lines. One with an anchor (a chunk copied
    from timeline.json has one) follows its words when the narration moves: it is timed as the kit
    would time them, and the kit chunks the rest of the sentence around it. One without stays at
    its times and replaces every phrase it overlaps. An anchor whose words are gone is dropped,
    with a warning, and the kit captions those words again."""
    widths = widths or caption_widths()
    own = [_kept(c, widths, warn) for c in kept]
    loose = sorted((c for c in own if "anchor" not in c), key=lambda c: c["start"])
    for a, b in zip(loose, loose[1:]):
        if b["start"] < a["end"]:
            raise SystemExit(f"captions.json: the chunks at {a['start']} s and {b['start']} s overlap")
    locks = {}
    for c in own:
        if "anchor" in c:
            found = _find(c["anchor"], narration)
            if found is None:
                warn(f"warn: captions.json: the chunk anchored on {c['anchor'].get('text') or c['anchor']['sentence']!r} "
                     "no longer matches the narration's words; dropped, and the kit captions them (anchor it again)")
                continue
            locks.setdefault(found[0], []).append((found[1], found[2], c))
    timed = []
    for s in narration:
        words = s["caption"].split()
        times = _word_times(s, words)

        def add(chunk, p, q):
            a, b = times[p][0], times[q - 1][1]
            if not any(a < k["end"] and k["start"] < b for k in loose):
                timed.append({**chunk, "start": round(a, 3), "end": round(b + TAIL, 3),
                              "anchor": {"sentence": s["id"], "words": [p, q], "text": " ".join(words[p:q])}})
        at = 0
        for i, j, c in sorted(locks.get(s["id"], []), key=lambda x: x[:2]) + [(len(words), len(words), None)]:
            if i < at:
                warn(f"warn: captions.json: two chunks anchor on the same words of {s['id']}; the later is dropped")
                continue
            p = at
            for piece in split_phrases(" ".join(words[at:i]), widths.values()) if i > at else []:
                q = p + len(piece.split())
                add({"lines": wrap(piece, widths["16:9"]),
                     "wrapped": {f: wrap(piece, w) for f, w in widths.items() if f != "16:9"}}, p, q)
                p = q
            if c is not None:
                add(c, i, j)
            at = j
    gap, kit = 2 / fps, {id(c) for c in timed}
    chunks = sorted(timed + loose, key=lambda c: c["start"])
    for cur, nxt in zip(chunks, chunks[1:]):
        if id(cur) in kit:
            cur["end"] = round(min(max(cur["end"], cur["start"] + MIN_SHOW), nxt["start"] - gap), 3)
    if chunks and id(chunks[-1]) in kit:
        chunks[-1]["end"] = round(max(chunks[-1]["end"], chunks[-1]["start"] + MIN_SHOW), 3)
    return chunks


def _kept(c, widths, warn=print):
    """A captions.json chunk as the timeline holds one: the lines it gives kept, the rest wrapped."""
    raw, c = c, c if isinstance(c, dict) else {}
    num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)
    strs = lambda x: isinstance(x, list) and all(isinstance(y, str) for y in x)
    lines, text, anchor, given = c.get("lines"), c.get("text"), c.get("anchor"), c.get("wrapped", {})
    if lines is not None:
        text = " ".join(lines) if strs(lines) else None
    others = [f for f in widths if f != "16:9"]
    if not (isinstance(text, str) and (_anchored(anchor) if anchor is not None else
                                       num(c.get("start")) and num(c.get("end")) and c["end"] > c["start"])
            and isinstance(given, dict) and all(f in others and strs(v) for f, v in given.items())):
        raise SystemExit(f"captions.json: {raw} needs text or lines, and an anchor {{sentence, words?: [first, past "
                         f"the last], text?}} or a start before its end; wrapped, if given, maps {', '.join(others)} to lines")
    out = {**c, "lines": lines if lines is not None else wrap(text, widths["16:9"]),
           "wrapped": {f: given[f] if f in given else wrap(text, widths[f]) for f in others}}
    over = [f for f in widths if len(caption_lines(out, f)) > MAX_LINES]
    if over:
        warn(f"warn: captions.json: {text[:40]!r} takes more than {MAX_LINES} lines in {', '.join(over)}; the band "
             "holds two, so shorten it or give those lines")
    return out


def _anchored(a):
    """Whether an anchor is well formed: a sentence id, and optionally a word span and its text."""
    w = a.get("words") if isinstance(a, dict) else None
    return isinstance(a, dict) and isinstance(a.get("sentence"), str) and isinstance(a.get("text", ""), str) and \
        (w is None or isinstance(w, list) and len(w) == 2 and all(type(x) is int for x in w) and 0 <= w[0] < w[1])


def _find(anchor, narration):
    """(sentence id, first word, past the last) of an anchor's words in this narration, or None.
    Its text is looked for in the sentence it names, then in every sentence in order: sentence ids
    are positions, so a sentence inserted earlier renumbers the rest. Without text, its span is
    taken as it stands."""
    said = {s["id"]: s["caption"].split() for s in narration}
    sid = anchor["sentence"]
    i, j = anchor.get("words") or (0, len(said.get(sid, [])))
    if "text" not in anchor:
        return (sid, i, j) if sid in said and j <= len(said[sid]) else None
    want = anchor["text"].split()
    if said.get(sid, [])[i:j] == want:
        return sid, i, j
    for k in [sid] * (sid in said) + list(said):
        ws = said[k]
        at = next((x for x in range(len(ws) - len(want) + 1) if ws[x:x + len(want)] == want), None)
        if want and at is not None:
            return k, at, at + len(want)
    return None


def _word_times(sentence, words):
    """(start, end) of each of a sentence's caption words: its word timings when they match the
    caption, else the sentence's time shared out by character position."""
    heard = sentence.get("words") or []
    if len(heard) == len(words):
        return [(w["start"], w["end"]) for w in heard]
    a, b = sentence["start"], sentence["end"]
    total, at, out = max(1, len(" ".join(words))), 0, []
    for w in words:
        out.append((a + (b - a) * at / total, a + (b - a) * (at + len(w)) / total))
        at += len(w) + 1
    return out


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


def _warn_unanchored(video, kept):
    """Chunks fixed in time (no anchor) stay put when the narration moves, so say so once the
    narration has changed since captions.json last did. Printed even when quiet, at every build,
    until the file is checked and saved again."""
    if not isinstance(kept, list) or all(isinstance(c, dict) and "anchor" in c for c in kept):
        return
    p, f = Path(video) / ".cache" / "studio" / "captions.json", Path(video) / "captions.json"
    version = f"{f.stat().st_mtime_ns}:{hashlib.sha256(f.read_bytes()).hexdigest()}"     # saved again counts too
    seen, stamp = _read(p) or {}, narration_stamp(video)
    if seen.get("version") != version:
        atomic_json(p, {"version": version, "narration": stamp})
    elif seen.get("narration") != stamp:
        print("warn: captions.json has chunks fixed in time (no anchor) written before the latest narration; check "
              "their times and save the file, or anchor them to their words (the contract at the top of timeline.py)")


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
            t["cues"] = {**_resolve_cues(cues, t), **t["cues"]}
            used.append("cues.json")
        t["cues"] = {k: frame_time(v, t["fps"]) for k, v in t.get("cues", {}).items()}
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
        kept = _read(video / "captions.json")
        if kept is not None:
            used.append("captions.json")
            _warn_unanchored(video, kept)
        t["tracks"]["captions"] = chunk_captions(t["tracks"]["narration"], t["fps"], caption_widths(video), kept or ())
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
    if getattr(args, "events", False):
        rows = events(args.video, t)
        print(f"{len(rows)} events (cues.json and holds), on the {t['fps']} fps grid:" if rows else "no events: cues.json is the beat sheet")
        for r in rows:
            where = f"{r['clip']} {r['t']:7.3f} s" if r["clip"] else "before the start" if r["time"] < 0 else "after the end"
            print(f"  {r['time']:8.3f} s  frame {r['frame']:<6} {where:16} {r['name']:24} {r['anchor']}")
    return 0
