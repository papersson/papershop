"""`studio voice-check VIDEO`: the audio review, since nobody here can listen.

Transcribes every sentence's clip from audio/narration.wav with a speech recogniser (faster-whisper)
and compares it, letter by letter, with the text that should have been spoken; numbers are spelled
out on both sides first. Writes audio/voice_check.txt: one line per sentence with its score (0..1)
and what was heard, then the sentences under the threshold. A low score usually means a clipped or
garbled word, a mispronounced term (add a "spoken" respelling to narration.json), or the
recogniser's own spelling of a name: read what was heard before re-rendering anything.

Incremental: what was heard is cached per sentence (audio/voice_check_cache.json), keyed by the
sentence's audio samples, its spoken text and the model, so after an edit only the sentences whose
audio changed are transcribed again. --all ignores the cache.
"""
import difflib
import hashlib
import json
import re
from pathlib import Path

from . import timeline as tl


def letters(text):
    from num2words import num2words

    text = re.sub(r"(?<=\d),(?=\d{3})", "", text)
    text = re.sub(r"(\d)\s*%", r"\1 percent", text)
    text = re.sub(r"\b(1[89]\d\d|20\d\d)\b", lambda m: num2words(int(m.group()), to="year"), text)
    text = re.sub(r"\d+\.\d+", lambda m: num2words(float(m.group())), text)
    text = re.sub(r"\d+", lambda m: num2words(int(m.group())), text)
    return re.sub(r"[^a-z]", "", text.lower())


def score(expected, heard):
    return difflib.SequenceMatcher(None, letters(expected), letters(heard), autojunk=False).ratio()


def main(args):
    try:
        import numpy as np
        import soundfile as sf
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("the voice check needs the align extra: run `studio doctor --fetch --extra align`")
    video = Path(args.video)
    t = tl.load(video)
    wav = video / "audio" / "narration.wav"
    if not wav.exists():
        raise SystemExit("no audio/narration.wav: run `studio narrate` first (the mp3 is too lossy to judge)")
    audio, sr = sf.read(wav, dtype="float32")
    cache_file = video / "audio" / "voice_check_cache.json"
    cache = {} if getattr(args, "all", False) or not cache_file.exists() else json.loads(cache_file.read_text())
    model = None
    pad = np.zeros(int(0.3 * sr), dtype=np.float32)
    rows, low, fresh, heard_now = [], [], 0, {}
    for s in t["tracks"]["narration"]:
        samples = audio[round(s["start"] * sr): round(s["end"] * sr)]   # as narrate placed it
        key = hashlib.sha1(samples.tobytes() + s["text"].encode() + args.model.encode()).hexdigest()
        if key in cache:
            heard = cache[key]
        else:
            if model is None:
                model = WhisperModel(args.model, device="cpu", compute_type="int8")
            clip = np.concatenate([pad, samples, pad])
            if sr != 16000:
                clip = np.interp(np.arange(0, len(clip), sr / 16000), np.arange(len(clip)), clip).astype(np.float32)
            parts, _ = model.transcribe(clip, language="en", beam_size=5, condition_on_previous_text=False)
            heard = " ".join(p.text.strip() for p in parts)
            fresh += 1
        heard_now[key] = heard
        sc = score(s["text"], heard)
        rows.append(f"{s['id']} {sc:.2f}  heard: {heard}")
        if sc < args.below:
            low.append(f"{s['id']} {sc:.2f}")
        print(rows[-1])
    cache_file.write_text(json.dumps(heard_now, indent=0))
    print(f"transcribed {fresh}, unchanged {len(rows) - fresh} (cached)")
    summary = f"{len(rows)} sentences; under {args.below}: " + (", ".join(low) if low else "none")
    (video / "audio" / "voice_check.txt").write_text("\n".join(rows + ["", summary]) + "\n")
    print(summary)
    return 0
