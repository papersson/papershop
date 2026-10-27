"""Render one small fixture and print a hash per layer of its output, so two machines' outputs can be
lined up with script/compare and the first layer where they part shows. Run by script/output-receipt.

The layers, from what the engine computes to what a viewer gets: the layout (every element's box),
one still's pixels, a clip's decoded frames, the encoded file, and Kokoro's audio for one sentence.
"""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

kit = Path(__file__).resolve().parents[1] / "studio/skills/studio/kit"
sys.path.insert(0, str(kit / "tests"))
from test_live_engine import live_video  # noqa: E402  the engine tests' fixture video

from PIL import Image  # noqa: E402
from studio_kit.engine import Engine  # noqa: E402


def digest(data):
    return hashlib.sha256(data).hexdigest()[:16]


with tempfile.TemporaryDirectory() as tmp:
    video = Path(tmp)
    live_video(video)
    engine = Engine(video)
    boxes = engine.boxes_at([{"clip": "s1", "t": 1.5}, {"clip": "s2", "t": 0.5}])
    print("layout (boxes):", digest(json.dumps(boxes, sort_keys=True).encode()))
    engine.still("s1", 1.5, video / "still.png")
    print("still pixels:", digest(Image.open(video / "still.png").convert("RGBA").tobytes()))
    engine.render("s1", video / "s1.mp4")
    clip = (video / "s1.mp4").read_bytes()
    frames = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video / "s1.mp4"), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                            capture_output=True, check=True).stdout
    print("clip decoded frames:", digest(frames))
    print("clip encoded file:", digest(clip))

try:
    import numpy as np
    from studio_kit.doctor import hf_cached
    from studio_kit.narration import KOKORO_REPO, KOKORO_REVISION, kokoro_pipeline
    if not hf_cached(KOKORO_REPO, KOKORO_REVISION):
        raise ImportError("weights not cached")
    synth = kokoro_pipeline()
    audio = np.concatenate([p.audio.numpy() for p in synth("Reproducible narration, twice over.", voice="af_heart",
                                                           speed=1.0, split_pattern=None)])
    print("kokoro audio:", digest(audio.tobytes()))
    print("kokoro audio, 16-bit:", digest((np.clip(audio, -1, 1) * 32767).round().astype("<i2").tobytes()))
except ImportError as e:
    print(f"kokoro audio: not here ({e})")
