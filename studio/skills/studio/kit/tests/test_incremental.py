"""The revision loop's caches: the voice check and the label crops only redo what changed."""
import json
import subprocess
import sys
import types
from argparse import Namespace
from pathlib import Path

import numpy as np
import soundfile as sf

from studio_kit import sheets, voice_check
from studio_kit import timeline as tl
from test_render import make_video


def fake_whisper(monkeypatch, calls):
    class Part:
        def __init__(self, text):
            self.text = text

    class WhisperModel:
        def __init__(self, *a, **k):
            pass

        def transcribe(self, clip, **k):
            calls.append(len(clip))
            return [Part("One.")], None

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=WhisperModel))


def test_voice_check_transcribes_only_sentences_whose_audio_changed(tmp_path, monkeypatch):
    make_video(tmp_path)
    (tmp_path / "audio").mkdir()
    sr = 24000
    audio = (0.1 * np.sin(np.arange(4 * sr) * 0.05)).astype(np.float32)
    sf.write(tmp_path / "audio" / "narration.wav", audio, sr)
    calls = []
    fake_whisper(monkeypatch, calls)
    args = Namespace(video=str(tmp_path), model="small.en", below=0.8, all=False)
    voice_check.main(args)
    assert len(calls) == 2
    voice_check.main(args)
    assert len(calls) == 2                       # nothing changed: all from the cache
    audio[int(2.6 * sr):int(3.0 * sr)] = 0       # the second sentence's audio changes
    sf.write(tmp_path / "audio" / "narration.wav", audio, sr)
    voice_check.main(args)
    assert len(calls) == 3
    voice_check.main(Namespace(**{**vars(args), "all": True}))
    assert len(calls) == 5


class BoxEngine:
    """Reports one small label per frame and writes the frame it was asked to keep."""
    boxes_keep_frames = True

    def __init__(self):
        self.frames = 0

    def boxes_at(self, requests):
        self.frames += len(requests)
        for r in requests:
            Path(r["out"]).parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:s=320x180:d=1",
                            "-frames:v", "1", r["out"]], check=True)
        return [{"clip": r["clip"], "t": r["t"], "band": {}, "boxes": [
            {"name": "seed 62", "x": 10, "y": 10, "w": 60, "h": 20},
            {"name": "seed 62", "x": 100, "y": 10, "w": 60, "h": 20},      # the same label twice in a frame
            {"name": "caption", "x": 0, "y": 150, "w": 300, "h": 20}]} for r in requests]


def test_crops_reuse_unchanged_frames_and_crop_a_repeated_label_once(tmp_path):
    t = make_video(tmp_path)
    for s in t["tracks"]["narration"]:
        s["clip"] = "s1"                         # both sentences in one chapter
    t["tracks"]["scene"][0]["end"] = 4.0
    t["tracks"]["scene"] = t["tracks"]["scene"][:1]
    (tmp_path / "timeline.json").write_text(json.dumps(t))
    eng = BoxEngine()
    idx = sheets.crops(tmp_path, tmp_path / "out", engine=eng)
    assert eng.frames == 2
    assert len(idx) == 1 and idx[0]["sentences"] == ["s1_01", "s2_01"] and idx[0]["height_px"] == 20
    assert (tmp_path / "out" / "crops" / idx[0]["file"]).exists()
    sheets.crops(tmp_path, tmp_path / "out", engine=eng)
    assert eng.frames == 2                       # unchanged frames: no renders
    assert json.loads((tmp_path / "out" / "crops" / "index.json").read_text()) == idx


class CheckEngine:
    """Answers the check's engine calls with passing results, recording which clips it was asked about."""
    boxes_keep_frames = True

    def __init__(self, video, fail=()):
        self.video, self.fail, self.asked = video, set(fail), []

    def layout(self):
        return tl.layout(self.video)

    def durations(self, clips):
        self.asked += list(clips)
        t = tl.load(self.video)
        return {c: tl.frames(t, c)[1] for c in clips}

    def stills(self, requests):
        self.asked += [r["clip"] for r in requests]
        for r in requests:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=1920x1080:d=1",
                            "-frames:v", "1", r["out"]], check=True)

    def boxes_at(self, requests):
        self.asked += [r["clip"] for r in requests]
        return [{**r, "band": {}, "boxes": [{"name": "label", "kind": "text", "x": 10, "y": 10, "w": 100,
                                              "h": 10 if r["clip"] in self.fail else 30}]} for r in requests]


def test_check_reruns_only_changed_chapters_and_forgets_failures(tmp_path, capsys):
    from studio_kit import check
    make_video(tmp_path)
    eng = CheckEngine(tmp_path)
    rows = check.run(tmp_path, samples=1, engine=eng, everything=False)
    assert {r["clip"] for r in rows if r["check"] in check.PER_CLIP} == {"s1", "s2"} and all(r["ok"] for r in rows)
    eng.asked.clear()
    assert check.run(tmp_path, samples=1, engine=eng, everything=False) == [] or not eng.asked
    assert "skipping s1, s2" in capsys.readouterr().out
    (tmp_path / "scenes" / "s2.tsx").write_text("// s2, edited\n")
    eng = CheckEngine(tmp_path, fail={"s2"})                      # the edit makes s2's text illegible
    rows = check.run(tmp_path, samples=1, engine=eng, everything=False)
    assert set(eng.asked) == {"s2"} and any(not r["ok"] and r["check"] == "legible" for r in rows)
    eng = CheckEngine(tmp_path)
    check.run(tmp_path, samples=1, engine=eng, everything=False)
    assert set(eng.asked) == {"s2"}                               # a failure is never remembered as a pass
    eng = CheckEngine(tmp_path)
    check.run(tmp_path, samples=1, engine=eng, everything=True)
    assert set(eng.asked) == {"s1", "s2"}                         # --all and the publish gate check everything
