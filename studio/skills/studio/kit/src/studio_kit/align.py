"""`studio align VIDEO`: word timings for the narration, then captions re-chunked from them.

Uses faster-whisper (the `align` extra); the model downloads from Hugging Face on first use.
"""
from pathlib import Path

from . import timeline as tl

MODEL = "small.en"


def recognise(audio, model=MODEL):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("faster-whisper is not installed: run `studio doctor --fetch --extra align`")

    segments, _ = WhisperModel(model, device="cpu", compute_type="int8").transcribe(
        str(audio), word_timestamps=True, language="en")
    return [{"w": w.word.strip(), "start": w.start, "end": w.end} for s in segments for w in s.words]


def main(args):
    video = Path(args.video)
    t = tl.load(video)
    heard = recognise(video / t["tracks"]["audio"][0]["file"], args.model)
    matched, total = tl.attach_words(t, heard)
    t["tracks"]["captions"] = tl.chunk_captions(t["tracks"]["narration"], t["fps"])
    tl.save(video, t)
    print(f"aligned {matched} of {total} script words ({total - matched} interpolated); "
          f"{len(t['tracks']['captions'])} caption chunks")
    return 0
