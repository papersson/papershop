"""`studio align VIDEO`: word timings for the narration, then captions re-chunked from them.

The recognised words go to audio/words.json with a stamp of the narration they were heard in; the
timeline attaches them while that narration is current. Uses faster-whisper (the `align` extra);
the model downloads from Hugging Face on first use.
"""
from pathlib import Path

from . import timeline as tl
from .workspace import atomic_json

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
    narration = tl.narration_audio(tl.load(video))
    if not narration:
        raise SystemExit("this video has no narration to align (a footage edit's words come from `studio ingest`)")
    heard = recognise(video / narration["file"], args.model)
    atomic_json(video / "audio" / "words.json", {"narration": tl.narration_stamp(video), "words": heard})
    t = tl.build(video)
    print(f"{len(t['tracks']['captions'])} caption chunks")
    return 0
