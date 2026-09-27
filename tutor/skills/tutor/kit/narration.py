"""Render a lesson's narration from its locked script (SCRIPT.md) with Kokoro TTS.

SCRIPT.md is the single source of truth: every "> " line under a "### N. Title" heading is a
paragraph of narration, split here into sentences with ids like s2_13. Writes audio/narration.wav,
audio/narration.mp3 and audio/timings.json with every sentence's id, spoken text, caption text,
start and end, so the scenes can cue off sentence ids.

By default each paragraph is one Kokoro call, so intonation carries across sentences and pauses
follow the punctuation. A sentence starts at its first word's timestamp and ends where the pause
into the next sentence begins (Kokoro folds that pause into the last word), both snapped to
silence. With "paragraph": false every sentence is its own call, joined by fixed gaps: flatter,
since every sentence then starts at the same pitch after the same pause.

Per-lesson settings come from narration.json in the lesson folder:
  kokoro        {"voice": "af_heart", "speed": 1.0, "paragraph": true}
  holds         {"s2_07": 1.0}   extra silence after a sentence, where the picture needs time
  spoken        [["BM25", "B M twenty-five"]]   written form -> spoken form, everywhere
  spoken_by_id  {"s3_02": [["x", "y"]]}   ... for one sentence only
  tail          seconds of silence after the last sentence, for the end card (default 6)

    python kit/narration.py LESSON_DIR            # render
    python kit/narration.py LESSON_DIR --estimate # timings only, from word counts (no audio)
    python kit/narration.py LESSON_DIR --list     # print the sentence ids

Check the result with kit/voice_check.py: you cannot listen, so a speech recogniser does.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

RATE = 24_000
LEAD_IN = 0.8        # silence before the first sentence
SENTENCE_GAP = 0.3   # between sentences of one paragraph (per-sentence mode only)
PARAGRAPH_GAP = 0.5  # between paragraphs
SEGMENT_GAP = 1.2    # between segments
CHUNK_WORDS = 90     # longest run of sentences sent to Kokoro in one call

HERE = Path(sys.argv[1]).resolve()
OUT = HERE / "audio"
_CFG = json.loads((HERE / "narration.json").read_text()) if (HERE / "narration.json").exists() else {}
KOKORO = {"voice": "af_heart", "speed": 1.0, "paragraph": True, **_CFG.get("kokoro", {})}
TAIL = _CFG.get("tail", 6.0)
HOLDS = _CFG.get("holds", {})
SPOKEN = [tuple(p) for p in _CFG.get("spoken", [])]
SPOKEN_BY_ID = {k: [tuple(p) for p in v] for k, v in _CFG.get("spoken_by_id", {}).items()}


def load_script():
    """[(segment id, title, [(sentence id, caption text, paragraph index)])] from SCRIPT.md."""
    text = (HERE / "SCRIPT.md").read_text()
    body = text[text.index("## Script"):text.index("## Evidence")]
    segs = []
    for block in re.split(r"^### ", body, flags=re.M)[1:]:
        head, rest = block.split("\n", 1)
        num, title = head.split(". ", 1)
        sid = f"s{int(num)}"
        sentences, n = [], 0
        paras = [l[2:].strip() for l in rest.splitlines() if l.startswith("> ")]
        for pi, para in enumerate(paras):
            for sent in re.split(r'(?<=[.!?])\s+(?=[A-Z"])', para):
                n += 1
                sentences.append((f"{sid}_{n:02d}", sent.strip(), pi))
        segs.append((sid, title.strip(), sentences))
    return segs


def spoken(text, lid=None):
    for written, said in SPOKEN + SPOKEN_BY_ID.get(lid, []):
        text = text.replace(written, said)
    return text


def layout(segs, durations, gaps=None):
    """Place every sentence on one track. `gaps` (paragraph mode): the voice's own pause after a
    sentence, measured in its paragraph's audio; it replaces SENTENCE_GAP there."""
    gaps = gaps or {}
    t, out = LEAD_IN, []
    for si, (sid, title, sents) in enumerate(segs):
        if si:
            t += SEGMENT_GAP
        seg = {"id": sid, "title": title, "start": t, "lines": []}
        prev_p = prev_id = None
        for lid, cap, pi in sents:
            if prev_p is not None:
                t += gaps.get(prev_id, SENTENCE_GAP) if pi == prev_p else PARAGRAPH_GAP
            d = durations[lid]
            seg["lines"].append({"id": lid, "text": spoken(cap, lid), "caption": cap, "paragraph": pi,
                                 "start": round(t, 3), "end": round(t + d, 3)})
            t += d + HOLDS.get(lid, 0.0)
            prev_p, prev_id = pi, lid
        out.append(seg)
    total = t + TAIL
    out[0]["start"] = 0.0
    for a, b in zip(out, out[1:]):
        b["start"] = round(b["lines"][0]["start"] - 0.35, 3)
        a["end"] = b["start"]
    out[-1]["end"] = round(total, 3)
    mode = "paragraph" if KOKORO["paragraph"] else "sentence"
    return {"voice": KOKORO["voice"], "speed": KOKORO["speed"], "mode": mode, "total": round(total, 3),
            "segments": out}


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


def chunked(sents):
    """Runs of consecutive sentences from one paragraph, at most CHUNK_WORDS words each:
    [[(sentence id, text to speak, paragraph index)]]."""
    chunks, cur, n = [], [], 0
    for lid, cap, pi in sents:
        text = spoken(cap, lid)
        w = len(text.split())
        if cur and (pi != cur[-1][2] or n + w > CHUNK_WORDS):
            chunks.append(cur)
            cur, n = [], 0
        cur.append((lid, text, pi))
        n += w
    chunks.append(cur)
    return chunks


def cut(audio, a, b):
    """audio[a s : b s], with 5 ms fades so a cut never clicks."""
    import numpy as np

    clip = audio[int(a * RATE): int(b * RATE)].copy()
    fade = min(len(clip) // 2, int(0.005 * RATE))
    if fade:
        clip[:fade] *= np.linspace(0, 1, fade)
        clip[-fade:] *= np.linspace(1, 0, fade)
    return clip


def paragraph_clips(pipe, segs):
    """{sentence id: clip}, {sentence id: natural pause after it}, {sentence id: text as spoken}."""
    import numpy as np

    clips, gaps, said = {}, {}, {}
    for _, _, sents in segs:
        for chunk in chunked(sents):
            texts = [t for _, t, _ in chunk]
            full = " ".join(texts)
            begins = [sum(len(t) + 1 for t in texts[:i]) for i in range(len(texts))]
            audio, words, pos = [], [], 0          # words: (char offset, start s, end s)
            for part in pipe(full, voice=KOKORO["voice"], speed=KOKORO["speed"], split_pattern=None):
                at = full.find(part.graphemes, pos)
                assert at >= 0, (part.graphemes, full)
                off, c = sum(len(x) for x in audio) / RATE, at
                for tok in part.tokens:
                    if tok.start_ts is not None and any(ch.isalnum() for ch in tok.text):
                        words.append((c, off + tok.start_ts, off + tok.end_ts))
                    c += len(tok.text) + len(tok.whitespace)
                audio.append(part.audio.numpy().astype(np.float32))
                pos = at + len(part.graphemes)
            audio = np.concatenate(audio)
            runs = silence_runs(audio, RATE)
            firsts = [next(w for w in words if w[0] >= b) for b in begins]
            spans = []
            for i, (_, st, _) in enumerate(firsts):
                nxt = firsts[i + 1][1] if i + 1 < len(firsts) else len(audio) / RATE
                last = [w for w in words if st <= w[1] < nxt][-1]
                s = [b for a, b in runs if st - 0.2 <= b <= st + 0.1]
                e = [a for a, b in runs if last[1] <= a < nxt and b >= nxt - 0.1]   # the pause into the next
                spans.append((max(s) if s else st, min(e) if e else min(last[2], nxt)))
            for i, ((lid, text, _), (a, b)) in enumerate(zip(chunk, spans)):
                assert a < b <= (spans[i + 1][0] if i + 1 < len(spans) else len(audio) / RATE), (lid, a, b)
                clips[lid], said[lid] = cut(audio, a, b), text
                if i + 1 < len(chunk):
                    gaps[lid] = spans[i + 1][0] - b
                print(f"{lid}: {b - a:5.2f}s  gap {gaps.get(lid, 0):.2f}  {text[:70]}")
    return clips, gaps, said


def sentence_clips(pipe, sents):
    """{sentence id: clip}, {sentence id: phonemes}: one Kokoro call per sentence."""
    import numpy as np

    clips, phonemes = {}, {}
    for key, cap in sents:
        parts = list(pipe(spoken(cap, key), voice=KOKORO["voice"], speed=KOKORO["speed"], split_pattern=None))
        audio = np.concatenate([p.audio.numpy() for p in parts])
        nz = np.flatnonzero(np.abs(audio) > 0.01)   # trim Kokoro's own silence
        clips[key] = audio[max(nz[0] - 240, 0): nz[-1] + 480]
        phonemes[key] = " ".join(p.phonemes for p in parts)
        print(f"{key}: {len(clips[key]) / RATE:5.2f}s  {phonemes[key][:80]}")
    return clips, phonemes


def main():
    OUT.mkdir(exist_ok=True)
    segs = load_script()
    sents = [(lid, cap) for _, _, ss in segs for lid, cap, _ in ss]
    if "--list" in sys.argv:
        for lid, cap in sents:
            print(lid, cap)
        return
    if "--estimate" in sys.argv:
        timings = layout(segs, {k: len(c.split()) / 2.8 + 0.3 for k, c in sents})
        (OUT / "timings.json").write_text(json.dumps(timings, indent=1))
        print(f"estimated total {timings['total']:.1f}s")
        return

    import numpy as np
    import soundfile as sf
    from kokoro import KPipeline

    pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
    gaps = None
    if KOKORO["paragraph"]:
        clips, gaps, spoken_text = paragraph_clips(pipe, segs)
    else:
        clips, spoken_text = sentence_clips(pipe, sents)

    timings = layout(segs, {k: len(a) / RATE for k, a in clips.items()}, gaps)
    track = np.zeros(int(timings["total"] * RATE) + RATE, dtype=np.float32)
    for seg in timings["segments"]:
        for ln in seg["lines"]:
            i = int(round(ln["start"] * RATE))
            track[i: i + len(clips[ln["id"]])] = clips[ln["id"]]
    track = track[: int(timings["total"] * RATE)]
    sf.write(OUT / "narration.wav", track, RATE)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(OUT / "narration.wav"),
                    "-codec:a", "libmp3lame", "-b:a", "128k", str(OUT / "narration.mp3")], check=True)
    timings["phonemes"] = spoken_text
    timings["peak"] = float(np.abs(track).max())
    (OUT / "timings.json").write_text(json.dumps(timings, indent=1))
    print(f"total {timings['total']:.1f}s, peak {timings['peak']:.2f}")


if __name__ == "__main__":
    main()
