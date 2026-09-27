"""The audio review, since the narration can't be listened to here: transcribe every sentence's clip
from audio/narration.wav with a speech recogniser (faster-whisper) and compare it, letter by letter,
with the text that should have been spoken. Numbers are spelled out on both sides first.

    python kit/voice_check.py LESSON_DIR [--model small.en] [--below 0.8]

Writes audio/voice_check.txt: one line per sentence with its score (0..1) and what was heard, and a
list of sentences under the threshold to look at. A low score usually means a clipped or garbled
word, a mispronounced term (add a "spoken" respelling in narration.json), or the recogniser's own
spelling of a name; read what was heard before re-rendering anything.
"""
import difflib
import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel
from num2words import num2words

LESSON = Path(sys.argv[1]).resolve()
MODEL = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else "small.en"
BELOW = float(sys.argv[sys.argv.index("--below") + 1]) if "--below" in sys.argv else 0.8


def letters(text):
    text = re.sub(r"(?<=\d),(?=\d{3})", "", text)
    text = re.sub(r"(\d)\s*%", r"\1 percent", text)
    text = re.sub(r"\b(1[89]\d\d|20\d\d)\b", lambda m: num2words(int(m.group()), to="year"), text)
    text = re.sub(r"\d+\.\d+", lambda m: num2words(float(m.group())), text)
    text = re.sub(r"\d+", lambda m: num2words(int(m.group())), text)
    return re.sub(r"[^a-z]", "", text.lower())


def main():
    t = json.loads((LESSON / "audio" / "timings.json").read_text())
    audio, sr = sf.read(LESSON / "audio" / "narration.wav", dtype="float32")
    model = WhisperModel(MODEL, device="cpu", compute_type="int8")
    pad = np.zeros(int(0.3 * sr), dtype=np.float32)
    rows, low = [], []
    for seg in t["segments"]:
        for ln in seg["lines"]:
            clip = np.concatenate([pad, audio[int(ln["start"] * sr): int(ln["end"] * sr)], pad])
            if sr != 16000:
                clip = np.interp(np.arange(0, len(clip), sr / 16000), np.arange(len(clip)), clip).astype(np.float32)
            parts, _ = model.transcribe(clip, language="en", beam_size=5, condition_on_previous_text=False)
            heard = " ".join(p.text.strip() for p in parts)
            score = difflib.SequenceMatcher(None, letters(ln["text"]), letters(heard), autojunk=False).ratio()
            rows.append(f"{ln['id']} {score:.2f}  heard: {heard}")
            if score < BELOW:
                low.append(f"{ln['id']} {score:.2f}")
            print(rows[-1])
    summary = f"{len(rows)} sentences; under {BELOW}: " + (", ".join(low) if low else "none")
    (LESSON / "audio" / "voice_check.txt").write_text("\n".join(rows + ["", summary]) + "\n")
    print(summary)


if __name__ == "__main__":
    main()
