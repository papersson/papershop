"""`studio narrate VIDEO`: narration from SCRIPT.md with Kokoro or ElevenLabs, into the timeline.

Each paragraph is one synthesis call (up to CHUNK_WORDS words), so intonation carries across its
sentences and pauses follow the punctuation. A sentence starts at its first word's timestamp and
ends where the pause into the next sentence begins, both snapped to silence. Kokoro can also
render one sentence per call with fixed gaps ("paragraph": false): flatter, since every sentence
then starts at the same pitch.

Writes audio/narration.wav and .mp3, and the timeline's narration track (with each sentence's
words, from the engine's own timestamps) and scene track (one clip per chapter).

Engines (narration.json "engine"):
  kokoro (default)  local, free, deterministic. "kokoro": voice, speed, paragraph. Each chunk's
                    audio is cached by its text and settings, so an edited sentence re-synthesises
                    only its paragraph.
  elevenlabs        hosted; needs ELEVENLABS_API_KEY. "elevenlabs": voice (a name from your voice
                    list) or voice_id, model (default eleven_multilingual_v2; eleven_v4 works too;
                    eleven_v3 returns no timestamps), stability, similarity_boost, style, speed (v4
                    takes neither style nor speed), seed. Each call gets the neighbouring paragraphs
                    as previous_text/next_text. Every response is cached in audio/elevenlabs_cache/
                    (commit it), so a re-run never pays twice and a machine without the key builds.

narration.json also holds:
  holds         {"s2_07": 1.0}   extra silence after a sentence, where the picture needs time
  spoken        [["BM25", "B M twenty-five"]]   written form -> spoken form, everywhere
  spoken_by_id  {"s3_02": [["x", "y"]]}   ... for one sentence only
                Both match whole words, case-sensitively, so a rule for "A" leaves "All" alone.
  phonemes      {"JSON": "ʤˈAsᵊn"}   a word's exact pronunciation, in Kokoro's phoneme alphabet
                (misaki), everywhere; the captions and the timeline keep the written word
  phonemes_by_id {"s6_17": {"A": "ˈA"}}   ... for one sentence only: the way to say a capital
                letter that names something ("A reads one"), since Kokoro reads a lone "A" as the
                article. Kokoro only; ElevenLabs ignores them and `studio narrate` says so.
  tail          seconds of silence after the last sentence, for the end card (default 6)
"""
import base64
import hashlib
import json
import math
import os
import re
import subprocess
import urllib.request
from pathlib import Path

from . import settings
from . import script as sc
from . import timeline as tl

RATE = 24_000
LEAD_IN = 0.8        # silence before the first sentence
SENTENCE_GAP = 0.3   # between sentences of one paragraph (Kokoro per-sentence mode only)
PARAGRAPH_GAP = 0.5  # between paragraphs
SEGMENT_GAP = 1.2    # between chapters
# Each chapter's first sentence starts on a 0.1 s grid (a whole number of frames at 30 fps, and of
# milliseconds), and its clip starts PRE_ROLL_FRAMES before it. So an edit that lengthens one chapter
# moves every later chapter by whole frames and whole milliseconds, and their clips, keyed on times
# relative to their own first frame, stay cached: only the edited chapter re-renders.
CHAPTER_GRID = 0.1
PRE_ROLL_FRAMES = 10
CHUNK_WORDS = 90     # longest run of sentences sent in one call
ASK_ABOVE = 2000     # ElevenLabs characters that need --yes


def whole_word(word):
    """A pattern for `word` that doesn't match inside a longer word (letters, digits, underscore)."""
    return re.compile(rf"(?<![\w]){re.escape(word)}(?![\w])")


class Settings:
    def __init__(self, video, config=None):
        self.video = Path(video).resolve()
        f = self.video / (config or "narration.json")
        cfg = json.loads(f.read_text()) if f.exists() else {}
        self.engine = cfg.get("engine", "kokoro")
        self.kokoro = {"voice": "af_heart", "speed": 1.0, "paragraph": True, **cfg.get("kokoro", {})}
        self.eleven = {"voice": None, "voice_id": None, "model": "eleven_multilingual_v2", "stability": 0.5,
                       "similarity_boost": 0.75, "style": 0.0, "speed": 1.0, "seed": None, **cfg.get("elevenlabs", {})}
        v4 = self.eleven["model"].startswith("eleven_v4")
        self.voice_settings = ("stability", "similarity_boost") + (() if v4 else ("style", "speed"))
        self.paragraph = self.engine == "elevenlabs" or self.kokoro["paragraph"]
        # How far a word's timestamp may trail the audio: Eleven v4's run up to about 0.3 s late.
        self.late = 0.35 if self.engine == "elevenlabs" and v4 else 0.2
        self.tail = cfg.get("tail", 6.0)
        self.holds = cfg.get("holds", {})
        self.timing = {"beat": 0.5, "chapter_hold": 0.0, "chapter_gap": SEGMENT_GAP, **cfg.get("timing", {})}
        for key, value in self.timing.items():
            if not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0:
                raise SystemExit(f"narration.json timing.{key} must be finite and nonnegative")
        from .preferences import lexicon
        shared = lexicon(video)
        self.spoken_pairs = list({**dict(shared.get("spoken", [])), **dict(cfg.get("spoken", []))}.items())
        self.accepted = cfg.get("accepted", [])
        self.spoken_by_id = {k: [tuple(p) for p in v] for k, v in cfg.get("spoken_by_id", {}).items()}
        self.phonemes = {**shared.get("phonemes", {}), **cfg.get("phonemes", {})}
        self.phonemes_by_id = cfg.get("phonemes_by_id", {})
        self.audio = self.video / "audio"

    def spoken(self, text, lid=None):
        table = {**dict(self.spoken_pairs), **dict(self.spoken_by_id.get(lid, []))}
        if not table:
            return text
        words = sorted(table, key=len, reverse=True)
        pattern = re.compile(r"(?<![\w])(" + "|".join(map(re.escape, words)) + r")(?![\w])")
        return pattern.sub(lambda m: table[m.group()], text)

    def phonemes_for(self, lid=None):
        return {**self.phonemes, **self.phonemes_by_id.get(lid, {})}

    def marked(self, text, lid=None):
        """The spoken text with phoneme overrides as Kokoro's markup, `[A](/ˈA/)`. Kokoro reports the
        plain text back as its graphemes, so word offsets still index the unmarked text."""
        table = self.phonemes_for(lid)
        if not table:
            return text
        # One pass, longest word first, so "A's" and "A" can both have entries without one rule
        # rewriting inside the other's markup.
        words = sorted(table, key=len, reverse=True)
        pattern = re.compile(r"(?<![\w])(" + "|".join(map(re.escape, words)) + r")(?![\w'’])")
        return pattern.sub(lambda m: f"[{m.group(0)}](/{table[m.group(0)]}/)", text)

    def voice_info(self):
        if self.engine == "elevenlabs":
            name = self.eleven["voice"] or self.eleven["voice_id"]
            return {"engine": "elevenlabs", "voice": name, "model": self.eleven["model"],
                    "speed": self.eleven["speed"] if "speed" in self.voice_settings else None, "mode": "paragraph",
                    "credit": f"Narration voice: ElevenLabs ({name})"}
        return {"engine": "kokoro", "voice": self.kokoro["voice"], "speed": self.kokoro["speed"],
                "mode": "paragraph" if self.paragraph else "sentence"}


def layout(S, chapters, durations, gaps=None, words=None):
    """Place every sentence on one track. `gaps` (paragraph mode): the voice's own pause after a
    sentence, measured in its paragraph's audio; it replaces SENTENCE_GAP there. `words`: each
    sentence's words relative to its own start."""
    gaps, words = gaps or {}, words or {}
    events = {s.id: s for c in sc.read(S.video, S.timing["beat"]) for s in c.sentences}
    dangling = set(S.holds) | set(S.spoken_by_id) | set(S.phonemes_by_id)
    if dangling - events.keys():
        print("warn: dangling narration sentence IDs: " + ", ".join(sorted(dangling - events.keys())))
    t, out = LEAD_IN, []
    for ci, (cid, title, sents) in enumerate(chapters):
        if ci:
            t += S.timing["chapter_gap"]
            t = math.ceil(round(t / CHAPTER_GRID, 6)) * CHAPTER_GRID
        seg = {"id": cid, "title": title, "start": t, "lines": []}
        # times inside a chapter are offsets from its (grid) start, rounded as offsets, so a chapter
        # that moves keeps exactly the same relative times
        g, r = round(t, 3), 0.0
        at = lambda x: round(g + round(x, 3), 3)
        prev_p = prev_id = None
        for lid, cap, pi in sents:
            if prev_p is not None:
                r += gaps.get(prev_id, SENTENCE_GAP) if pi == prev_p else PARAGRAPH_GAP
            d = durations[lid]
            seg["lines"].append({"id": lid, "text": S.spoken(cap, lid), "caption": cap, "paragraph": pi,
                                 "start": at(r), "end": at(r + d),
                                 "words": [{"w": w, "start": at(r + a), "end": at(r + b)}
                                           for w, a, b in words.get(lid, [])]})
            event = events.get(lid)
            hold = S.holds.get(lid, S.timing["chapter_hold"] if lid == sents[-1][0] else 0.0)
            if event and event.pause is not None:
                if lid in S.holds:
                    print(f"warn: {lid} inline pause replaces narration.json hold")
                hold = event.pause
            if hold:
                seg["lines"][-1]["pause"] = {"seconds": hold, "prediction": bool(event and event.prediction),
                                                   "start": at(r + d), "end": at(r + d + hold)}
            r += d + hold
            prev_p, prev_id = pi, lid
        t = g + r
        out.append(seg)
    total = t + S.tail
    out[0]["start"] = 0.0
    fps = tl.layout(S.video)["fps"]
    for a, b in zip(out, out[1:]):
        # PRE_ROLL_FRAMES before the chapter's first sentence, exactly on the frame grid
        b["start"] = (tl.half_up(b["lines"][0]["start"] * fps) - PRE_ROLL_FRAMES) / fps
        a["end"] = b["start"]
    out[-1]["end"] = round(total, 3)
    return {**S.voice_info(), "total": round(total, 3), "segments": out}


def silence_runs(audio, sr, below=35.0):
    """[(start, end)] in seconds of stretches at least 40 ms long that are quieter than the loud
    (95th percentile) level by `below` dB."""
    import numpy as np

    hop, win = int(0.01 * sr), int(0.025 * sr)
    frames = np.lib.stride_tricks.sliding_window_view(np.pad(audio, (0, win)), win)[::hop]
    db = 20 * np.log10(np.sqrt((frames ** 2).mean(1)) + 1e-9)
    sil = db < np.percentile(db, 95) - below
    runs, i = [], 0
    while i < len(sil):
        if sil[i]:
            j = i
            while j < len(sil) and sil[j]:
                j += 1
            if j - i >= 4:
                runs.append((i * 0.01, j * 0.01))
            i = j
        else:
            i += 1
    return runs


def chunked(S, sents):
    """Runs of consecutive sentences from one paragraph, at most CHUNK_WORDS words each:
    [[(sentence id, text to speak, paragraph index)]]."""
    chunks, cur, n = [], [], 0
    for lid, cap, pi in sents:
        text = S.spoken(cap, lid)
        w = len(text.split())
        if cur and (pi != cur[-1][2] or n + w > CHUNK_WORDS):
            chunks.append(cur)
            cur, n = [], 0
        cur.append((lid, text, pi))
        n += w
    chunks.append(cur)
    return chunks


def all_chunks(S, chapters):
    """Every chunk of the video in order, with the text before and after it (for ElevenLabs'
    previous_text/next_text): [(chunk, previous text, next text)]."""
    chunks = [c for _, _, sents in chapters for c in chunked(S, sents)]
    text = [" ".join(t for _, t, _ in c) for c in chunks]
    return [(c, text[i - 1] if i else "", text[i + 1] if i + 1 < len(chunks) else "") for i, c in enumerate(chunks)]


def cut(audio, a, b):
    """audio[a s : b s], with 5 ms fades so a cut never clicks."""
    import numpy as np

    clip = audio[int(a * RATE): int(b * RATE)].copy()
    fade = min(len(clip) // 2, int(0.005 * RATE))
    if fade:
        clip[:fade] *= np.linspace(0, 1, fade)
        clip[-fade:] *= np.linspace(1, 0, fade)
    return clip


# --- engines: each returns synth(text, previous, next) -> (audio at RATE, [(char offset, start s, end s)] per word)

def kokoro_pipeline():
    from .doctor import require_extra
    require_extra("kokoro")
    try:
        from kokoro import KPipeline
    except ImportError:
        raise SystemExit("Kokoro is not installed: run `studio doctor --fetch --extra kokoro`")
    return KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")


def kokoro_key(S, full):
    blob = json.dumps({"voice": S.kokoro["voice"], "speed": S.kokoro["speed"], "text": full}, sort_keys=True)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def kokoro_engine(S):
    """Kokoro, with each chunk's audio and word timings cached under .cache/narration/."""
    import numpy as np

    cache = S.video / ".cache" / "narration"
    pipe = None

    def synth(full, _prev, _next, marked=None):
        nonlocal pipe
        marked = marked or full
        key = kokoro_key(S, marked)
        wav, meta = cache / f"{key}.npy", cache / f"{key}.json"
        if wav.exists() and meta.exists():
            return np.load(wav), [tuple(w) for w in json.loads(meta.read_text())]
        pipe = pipe or kokoro_pipeline()
        audio, words, pos = [], [], 0
        for part in pipe(marked, voice=S.kokoro["voice"], speed=S.kokoro["speed"], split_pattern=None):
            at = full.find(part.graphemes, pos)
            assert at >= 0, (part.graphemes, full)
            off, c = sum(len(x) for x in audio) / RATE, at
            for tok in part.tokens:
                if tok.start_ts is not None and any(ch.isalnum() for ch in tok.text):
                    words.append((c, off + tok.start_ts, off + tok.end_ts))
                c += len(tok.text) + len(tok.whitespace)
            audio.append(part.audio.numpy().astype(np.float32))
            pos = at + len(part.graphemes)
        out = np.concatenate(audio)
        cache.mkdir(parents=True, exist_ok=True)
        np.save(wav, out)
        meta.write_text(json.dumps(words))
        return out, words

    return synth


def eleven_words(full, alignment):
    """Word timings from ElevenLabs' character alignment: [(char offset in `full`, start, end)]."""
    chars = alignment["characters"]
    starts, ends = alignment["character_start_times_seconds"], alignment["character_end_times_seconds"]
    assert "".join(chars) == full, "ElevenLabs aligned a different text than was sent"
    words, i = [], 0
    while i < len(chars):
        if chars[i].isalnum():
            j = i
            while j < len(chars) and (chars[j].isalnum() or (chars[j] in "'’-" and j + 1 < len(chars) and chars[j + 1].isalnum())):
                j += 1
            words.append((i, starts[i], ends[j - 1]))
            i = j
        else:
            i += 1
    return words


def eleven_request(S, full, prev, nxt):
    """The request body for one chunk, and the cache file its response lives in."""
    E = S.eleven
    body = {"text": full, "model_id": E["model"], "voice_settings": {k: E[k] for k in S.voice_settings}}
    if prev:
        body["previous_text"] = prev
    if nxt:
        body["next_text"] = nxt
    if E["seed"] is not None:
        body["seed"] = E["seed"]
    key = hashlib.sha256(json.dumps([E["voice"], E["voice_id"], body], sort_keys=True).encode()).hexdigest()[:16]
    return body, S.audio / "elevenlabs_cache" / f"{key}.json"


def eleven_fetch(S, chunks, yes=False):
    """Call ElevenLabs for every chunk not yet in the cache."""
    todo = []
    for chunk, prev, nxt in chunks:
        body, f = eleven_request(S, " ".join(t for _, t, _ in chunk), prev, nxt)
        if not f.exists():
            todo.append((body, f))
    n = sum(len(b["text"]) for b, _ in todo)
    print(f"ElevenLabs: {len(todo)} of {len(chunks)} chunks to fetch, {n} characters on {S.eleven['model']}")
    if not todo:
        return
    if n > ASK_ABOVE and not yes:
        raise SystemExit("re-run with --yes to spend those credits")
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        raise SystemExit("ELEVENLABS_API_KEY is not set in this environment")

    def call(method, path, body=None):
        req = urllib.request.Request("https://api.elevenlabs.io/v1" + path, method=method,
                                     headers={"xi-api-key": key, "Content-Type": "application/json"},
                                     data=json.dumps(body).encode() if body is not None else None)
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read())

    vid = S.eleven["voice_id"]
    if not vid:
        voices = call("GET", "/voices")["voices"]
        want = (S.eleven["voice"] or "").lower()
        match = [v for v in voices if v["name"].lower() == want or v["name"].lower().split(" - ")[0].strip() == want]
        if not match:
            raise SystemExit(f"no voice named {S.eleven['voice']!r}; available: {', '.join(sorted(v['name'] for v in voices))}")
        vid = match[0]["voice_id"]
    (S.audio / "elevenlabs_cache").mkdir(parents=True, exist_ok=True)
    for i, (body, f) in enumerate(todo, 1):
        # One attempt per chunk: a failure stops the run rather than retrying into the credit limit.
        r = call("POST", f"/text-to-speech/{vid}/with-timestamps?output_format=mp3_44100_128", body)
        f.write_text(json.dumps({"voice_id": vid, "request": body, "audio_base64": r["audio_base64"],
                                 "alignment": r["alignment"]}))
        print(f"  {i}/{len(todo)} fetched: {body['text'][:60]}")


def eleven_engine(S, chunks, yes=False):
    import numpy as np

    eleven_fetch(S, chunks, yes)

    def synth(full, prev, nxt):
        _, f = eleven_request(S, full, prev, nxt)
        r = json.loads(f.read_text())
        pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-f", "f32le", "-ac", "1", "-ar", str(RATE), "pipe:1"],
                             input=base64.b64decode(r["audio_base64"]), capture_output=True, check=True).stdout
        return np.frombuffer(pcm, dtype=np.float32).copy(), eleven_words(full, r["alignment"])

    return synth


_WORD = re.compile(r"[\w'’-]+")


def paragraph_clips(S, synth, chunks):
    """{sentence id: clip}, {sentence id: natural pause after it}, {sentence id: text as spoken},
    {sentence id: [(word, start, end)] relative to the clip's start}."""
    clips, gaps, said, words_by = {}, {}, {}, {}
    for chunk, prev, nxt in chunks:
        texts = [t for _, t, _ in chunk]
        full = " ".join(texts)
        marked = " ".join(S.marked(t, lid) for lid, t, _ in chunk)
        begins = [sum(len(t) + 1 for t in texts[:i]) for i in range(len(texts))]
        audio, words = synth(full, prev, nxt, marked) if marked != full else synth(full, prev, nxt)
        runs = silence_runs(audio, RATE)
        firsts = [next(w for w in words if w[0] >= b) for b in begins]
        starts = []
        for _, st, _ in firsts:
            # The pause before a sentence: the longest silence ending near its first word (a later,
            # shorter one is a consonant inside that word, and snapping to it clips the word).
            s = [(b - a, b) for a, b in runs if st - S.late <= b <= st + 0.1]
            starts.append(max(s)[1] if s else st)
        spans = []
        for i, (_, st, _) in enumerate(firsts):
            end = firsts[i + 1][1] if i + 1 < len(firsts) else len(audio) / RATE
            nxt_start = starts[i + 1] if i + 1 < len(starts) else len(audio) / RATE
            last = [w for w in words if st <= w[1] < end][-1]
            # The pause into the next sentence ends where that sentence starts once snapped, not at
            # its raw timestamp.
            e = [a for a, b in runs if last[1] <= a < nxt_start and b >= nxt_start - 0.1]
            spans.append((starts[i], min(e) if e else min(last[2], nxt_start)))
        for i, ((lid, text, _), (a, b)) in enumerate(zip(chunk, spans)):
            assert a < b <= (spans[i + 1][0] if i + 1 < len(spans) else len(audio) / RATE), (lid, a, b)
            clips[lid], said[lid] = cut(audio, a, b), text
            lo, hi = begins[i], begins[i] + len(text)
            words_by[lid] = [(_WORD.match(full, c).group(0) if _WORD.match(full, c) else full[c], max(0.0, ws - a), max(0.0, min(we, b) - a))
                             for c, ws, we in words if lo <= c < hi]
            if i + 1 < len(chunk):
                gaps[lid] = spans[i + 1][0] - b
            print(f"{lid}: {b - a:5.2f}s  gap {gaps.get(lid, 0):.2f}  {text[:70]}")
    return clips, gaps, said, words_by


def sentence_clips(S, sents):
    """{sentence id: clip}, {sentence id: phonemes}: one Kokoro call per sentence."""
    import numpy as np

    pipe = kokoro_pipeline()
    clips, phonemes = {}, {}
    for key, cap in sents:
        parts = list(pipe(S.marked(S.spoken(cap, key), key), voice=S.kokoro["voice"], speed=S.kokoro["speed"], split_pattern=None))
        audio = np.concatenate([p.audio.numpy() for p in parts])
        nz = np.flatnonzero(np.abs(audio) > 0.01)   # trim Kokoro's own silence
        clips[key] = audio[max(nz[0] - 240, 0): nz[-1] + 480]
        phonemes[key] = " ".join(p.phonemes for p in parts)
        print(f"{key}: {len(clips[key]) / RATE:5.2f}s  {phonemes[key][:80]}")
    return clips, phonemes


WORDS_PER_SECOND = 2.8   # spoken words per second at speed 1.0, for timing a script before its audio exists


def estimate_durations(S, chapters):
    """Each sentence's spoken length guessed from its word count and the voice's speed."""
    speed = S.kokoro["speed"] if S.engine == "kokoro" else S.eleven["speed"]
    return {sid: len(cap.split()) / (WORDS_PER_SECOND * speed) + 0.3 for _, _, ss in chapters for sid, cap, _ in ss}


def write_timeline(S, timings, timing="narrated"):
    """The narration and scene tracks from the laid-out timings; cues and engines are kept. `timing`
    records where the times came from: "narrated" (the audio) or "estimate" (word counts, no audio)."""
    video = S.video
    old = tl.load(video) if (video / "timeline.json").exists() else None
    t = tl.from_timings(timings, engine=(old or {}).get("tracks", {}).get("scene", [{}])[0].get("engine", "remotion"),
                        audio_file="audio/narration.mp3")
    t["timing"] = timing
    if old:
        t["cues"] = {**{k: v for k, v in old.get("cues", {}).items() if not k.startswith("reveal:")}, **t["cues"]}
    tl.save(video, t)
    if not (video / "layout.json").exists():
        (video / "layout.json").write_text(json.dumps(tl.DEFAULT_LAYOUT, indent=1) + "\n")
    return t


def narrate(video, config=None, estimate=False, fetch_only=False, yes=False):
    S = Settings(video, config)
    S.audio.mkdir(exist_ok=True)
    chapters = sc.load(S.video)
    sents = [(lid, cap) for _, _, ss in chapters for lid, cap, _ in ss]
    from . import pronounce
    pronounce.report(S, chapters)
    if estimate:
        timings = layout(S, chapters, estimate_durations(S, chapters))
        write_timeline(S, timings, timing="estimate")
        print(f"estimated total {timings['total']:.1f}s (no audio; scenes can be timed against it)")
        return timings
    from .doctor import require_extra
    require_extra("kokoro" if S.engine == "kokoro" else "audio")
    cfg = settings.load(S.video)
    if cfg.get("teaching_contract"):
        from .script_check import run as check_script
        failures = [r["detail"] for r in check_script(S.video) if not r["ok"]]
        if failures:
            raise SystemExit("script is not ready: " + "; ".join(failures))
        from .review_state import require, required_roles
        for role in required_roles(cfg):
            require(S.video, role)
    chunks = all_chunks(S, chapters)
    if S.engine == "elevenlabs" and (S.phonemes or S.phonemes_by_id):
        print("note: phoneme overrides are Kokoro-only; ElevenLabs speaks those words as written "
              "(give them a text respelling under \"spoken\" instead)")
    if fetch_only:
        if S.engine != "elevenlabs":
            raise SystemExit("--fetch-only is for the elevenlabs engine")
        eleven_fetch(S, chunks, yes)
        return None

    import numpy as np
    try:
        import soundfile as sf
    except ImportError:
        raise SystemExit("soundfile is not installed: run `studio doctor --fetch --extra kokoro`")

    gaps, words = None, None
    if S.engine == "elevenlabs":
        clips, gaps, spoken_text, words = paragraph_clips(S, eleven_engine(S, chunks, yes), chunks)
    elif S.paragraph:
        clips, gaps, spoken_text, words = paragraph_clips(S, kokoro_engine(S), chunks)
    else:
        clips, spoken_text = sentence_clips(S, sents)

    timings = layout(S, chapters, {k: len(a) / RATE for k, a in clips.items()}, gaps, words)
    track = np.zeros(int(timings["total"] * RATE) + RATE, dtype=np.float32)
    for seg in timings["segments"]:
        for ln in seg["lines"]:
            i = int(round(ln["start"] * RATE))
            track[i: i + len(clips[ln["id"]])] = clips[ln["id"]]
    track = track[: int(timings["total"] * RATE)]
    sf.write(S.audio / "narration.wav", track, RATE)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(S.audio / "narration.wav"),
                    "-codec:a", "libmp3lame", "-b:a", "128k", str(S.audio / "narration.mp3")], check=True)
    timings["phonemes"] = spoken_text
    timings["peak"] = float(np.abs(track).max())
    (S.audio / "timings.json").write_text(json.dumps(timings, indent=1))
    write_timeline(S, timings)
    print(f"total {timings['total']:.1f}s, peak {timings['peak']:.2f}")
    return timings


def plan(video, config=None):
    """What a narration would synthesise: (chunks, chunks not cached, characters not cached)."""
    S = Settings(video, config)
    chunks = all_chunks(S, sc.load(S.video))
    todo = []
    for chunk, prev, nxt in chunks:
        full = " ".join(t for _, t, _ in chunk)
        if S.engine == "elevenlabs":
            cached = eleven_request(S, full, prev, nxt)[1].exists()
        else:
            marked = " ".join(S.marked(t, lid) for lid, t, _ in chunk)
            cached = (S.video / ".cache" / "narration" / f"{kokoro_key(S, marked)}.npy").exists()
        if not cached:
            todo.append((chunk, full))
    return S, chunks, todo


def main(args):
    if args.list:
        for _, _, sents in sc.load(args.video):
            for lid, cap, _ in sents:
                print(lid, cap)
        return 0
    if args.plan:
        S, chunks, todo = plan(args.video, args.config)
        print(f"{len(chunks)} chunks, {len(chunks) - len(todo)} cached, {len(todo)} to synthesise "
              f"({sum(len(f) for _, f in todo)} characters) with {S.voice_info()}")
        for chunk, _ in todo:
            print(f"  {chunk[0][0]}..{chunk[-1][0]}")
        return 0
    narrate(args.video, args.config, args.estimate, args.fetch_only, args.yes)
    return 0
