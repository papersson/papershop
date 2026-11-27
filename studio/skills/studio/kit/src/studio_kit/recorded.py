"""The `recorded` narration engine: the film narrated in a voice someone recorded, not a synthetic one.

narration.json `"engine": "recorded"`. Each chapter has one take, `audio/takes/<chapter id>.<ext>`
(wav, m4a, mp3, flac, ogg, aac, caf), read straight through from the chapter's first sentence to its
last. A stumble is fine: stop, go back to the start of the sentence or the paragraph, and read on;
the last full reading of each paragraph wins.

For each take: `studio take`'s chain cleans it (cached by the take's bytes under .cache/takes/), a
recogniser hears its words with their times (faster-whisper, the `align` extra; cached beside the
cleaned take), and each paragraph of the script is matched to what was heard, letter by letter, so
"2,700" read as "two thousand seven hundred" still lines up. A paragraph's audio is then cut and
handed to the same sentence cutting the other engines use, so the pauses between sentences are the
reader's own, snapped to silence, and the timeline gets real word times for captions and cues.

The narration track is 48 kHz (synthetic voices are 24 kHz), so nothing above 12 kHz is lost.
"""
import difflib
import hashlib
import json
import re
from pathlib import Path

from . import proc, take

RATE = 48_000
KINDS = (".wav", ".m4a", ".mp3", ".flac", ".ogg", ".aac", ".caf")
LEAD = 0.25          # seconds of the take kept before a paragraph's first word
TAIL = 0.5           # ... and after its last word
JUMP = 3             # heard words with no script between them that mark a different reading
WORD = re.compile(r"[\w'’-]+")


def take_for(takes, cid):
    """The take file for chapter `cid`, or None."""
    found = [p for p in sorted(Path(takes).glob(f"{cid}.*")) if p.suffix.lower() in KINDS]
    return found[0] if found else None


def letters(word):
    from .voice_check import letters as spelled
    return spelled(word)


def spelled(tokens):
    """The tokens' letters run together, and for each letter the index of the token it came from."""
    text, owner = [], []
    for i, tok in enumerate(tokens):
        s = letters(tok)
        text.append(s)
        owner += [i] * len(s)
    return "".join(text), owner


def match(script_tokens, heard_tokens):
    """{script token index: heard token index} for the script tokens found in what was heard, in order.
    Letter by letter, so a number written as digits on one side and spelled on the other still meets.
    An earlier, abandoned reading of the same lines (a restart) is left out: the match keeps the run
    of words read without a long jump back."""
    a, a_owner = spelled(script_tokens)
    b, b_owner = spelled(heard_tokens)
    pairs = {}
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        if blk.size < 3:          # a letter or two in common is chance, not the same words
            continue
        for k in range(blk.size):
            pairs.setdefault(a_owner[blk.a + k], b_owner[blk.b + k])
    return pairs


def drop_restarts(pairs, heard=None):
    """The matched words of one reading. Where the heard words jump ahead of the script (words heard
    that the script doesn't have between two of its own), the matches before and after the jump
    come from different readings: a restart (the reader stopped and read the lines again) or the
    same words in a later paragraph. The longest run wins; on a tie, the later one, since the last
    full reading is the take."""
    keys = sorted(pairs)
    runs, cur = [], []
    for k in keys:
        if cur and pairs[k] - pairs[cur[-1]] > (k - cur[-1]) + JUMP:
            runs.append(cur)
            cur = []
        cur.append(k)
    if cur:
        runs.append(cur)
    best = max(reversed(runs), key=len) if runs else []
    return {k: pairs[k] for k in best}


def word_times(full, pairs, heard):
    """[(char offset in full, start, end)] for every word of the paragraph: heard times where a word
    was matched, spread evenly between its matched neighbours where it was not."""
    toks = [(m.start(), m.group()) for m in WORD.finditer(full)]
    known = {i: (heard[j]["start"], heard[j]["end"]) for i, j in pairs.items()}
    out = []
    for i, (c, _) in enumerate(toks):
        if i in known:
            out.append((c, *known[i]))
            continue
        before = max((k for k in known if k < i), default=None)
        after = min((k for k in known if k > i), default=None)
        lo = known[before][1] if before is not None else (known[after][0] if after is not None else 0.0)
        hi = known[after][0] if after is not None else lo
        n = (after if after is not None else i + 1) - (before if before is not None else i - 1) - 1
        k = i - (before if before is not None else i - 1) - 1
        step = (hi - lo) / max(n, 1)
        out.append((c, lo + k * step, lo + (k + 1) * step if hi > lo else lo))
    return out


class Take:
    """One chapter's take: the cleaned audio at RATE and the words heard in it."""

    def __init__(self, video, path, model):
        import numpy as np
        import soundfile as sf

        key = hashlib.sha256(path.read_bytes() + take.CHAIN_VERSION.encode()).hexdigest()[:16]
        cache = Path(video) / ".cache" / "takes"
        cache.mkdir(parents=True, exist_ok=True)
        clean, words = cache / f"{key}.wav", cache / f"{key}.{model}.words.json"
        if not clean.exists():
            take.clean(path, clean, take.measure(path)["lufs"])
            print(f"cleaned {path.name}")
        if not words.exists():
            from .align import recognise
            words.write_text(json.dumps(recognise(clean, model)))
        audio, sr = sf.read(clean, dtype="float32")
        assert sr == RATE, (clean, sr)
        self.audio = audio if audio.ndim == 1 else audio.mean(1)
        self.heard = [w for w in json.loads(words.read_text()) if letters(w["w"])]
        self.cursor = 0          # heard words before this belong to paragraphs already placed
        self.until = 0.0         # seconds: the end of the last paragraph cut from this take
        self.name = path.name
        self.np = np

    def paragraph(self, full):
        """(audio, word times) for the paragraph `full`, the next one read in this take."""
        tokens = [t.group() for t in WORD.finditer(full)]
        # Only as far ahead as this paragraph could reach, read twice over with stumbles: further on
        # the same words come back in later paragraphs.
        rest = self.heard[self.cursor:self.cursor + 3 * len(tokens) + 30]
        pairs = match(tokens, [w["w"] for w in rest])
        pairs = drop_restarts(pairs, rest)
        if len(pairs) < max(1, len(tokens) // 2):
            raise SystemExit(f"{self.name}: could not find \"{full[:60]}...\" in the take "
                             f"(heard {len(pairs)} of its {len(tokens)} words); is it read in this chapter's take?")
        times = word_times(full, pairs, rest)
        start = max(self.until, times[0][1] - LEAD)
        end = min(len(self.audio) / RATE, max(t[2] for t in times) + TAIL)
        nxt = self.cursor + max(pairs.values()) + 1
        if nxt < len(self.heard):
            end = min(end, max(self.heard[nxt]["start"] - 0.05, max(t[2] for t in times)))
        self.cursor, self.until = nxt, end
        clip = self.audio[int(start * RATE): int(end * RATE)].astype(self.np.float32)
        return clip, [(c, max(0.0, a - start), max(0.0, b - start)) for c, a, b in times]


def engine(S, chapters, chunks, model="small.en"):
    """synth(full, prev, next) for paragraph_clips: each chunk's audio cut from its chapter's take."""
    takes = S.video / S.recorded["takes"]
    missing = [cid for cid, _, _ in chapters if not take_for(takes, cid)]
    if missing:
        raise SystemExit(f"no take for chapter{'s' if len(missing) > 1 else ''} {', '.join(missing)}: "
                         f"record each as {takes.relative_to(S.video)}/<chapter id>.wav (or .m4a, .mp3)")
    owner = {lid: cid for cid, _, sents in chapters for lid, _, _ in sents}
    open_takes = {}

    def synth(full, _prev, _next, _marked=None):
        lid = next(l for chunk, _, _ in chunks for l, _, _ in chunk if " ".join(t for _, t, _ in chunk) == full)
        cid = owner[lid]
        if cid not in open_takes:
            open_takes[cid] = Take(S.video, take_for(takes, cid), model)
        return open_takes[cid].paragraph(full)

    return synth
