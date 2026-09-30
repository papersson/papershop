"""The engine interface: still, render, boxes and duration for one clip of a video.

Every engine is a CLI under engines/<name>/ that prints one JSON object per call; this module is
the only place the kit calls it, so a second engine only needs a second `_command`.
"""
import json
import subprocess
import tempfile
from pathlib import Path

from .env import engine_dir, resolve_browser

LAYERS = ("all", "no-captions", "no-band", "background")


class EngineError(RuntimeError):
    pass


class Engine:
    def __init__(self, video, name="remotion"):
        self.video = Path(video).resolve()
        self.name = name
        self.browser, _ = resolve_browser()

    def _command(self, op, *args):
        if self.name != "remotion":
            raise EngineError(f"no engine named {self.name}")
        cmd = ["node", str(engine_dir(self.name) / "cli.mjs"), op, "--video", str(self.video), *args]
        if self.browser:
            cmd += ["--browser", self.browser]
        return cmd

    def _call(self, op, *args):
        run = subprocess.run(self._command(op, *map(str, args)), capture_output=True, text=True)
        if run.returncode != 0:
            raise EngineError(f"{self.name} {op} failed:\n{run.stderr.strip()[-3000:]}")
        return json.loads(run.stdout.strip().splitlines()[-1])

    def still(self, clip, t, out, layers="all", scale=1.0):
        """The exact frame at clip time t, rendered alone."""
        assert layers in LAYERS, layers
        return self._call("still", "--clip", clip, "--t", t, "--out", out, "--layers", layers, "--scale", scale)

    def stills(self, requests):
        """Many stills in one browser session: [{clip, t, out, layers?, scale?}]."""
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump([{**r, "out": str(r["out"])} for r in requests], f)
        try:
            return self._call("stills", "--requests", f.name)
        finally:
            Path(f.name).unlink(missing_ok=True)

    def render(self, clip, out, quality="draft", range_=None):
        """The clip as a silent video, or the part of it between range_ = (a, b) seconds."""
        args = ["--clip", clip, "--out", out, "--quality", quality]
        if range_:
            args += ["--range", range_[0], range_[1]]
        return self._call("render", *args)

    def boxes_at(self, requests):
        """Boxes for many frames in one browser session: [{clip, t}] -> [{clip, t, band, boxes}]."""
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(requests, f)
        try:
            return self._call("boxesAt", "--requests", f.name)["frames"]
        finally:
            Path(f.name).unlink(missing_ok=True)

    def boxes(self, clip, t):
        """Pixel boxes of every labelled element at clip time t, and the caption band's position."""
        return self._call("boxes", "--clip", clip, "--t", t)

    def duration(self, clip):
        return self._call("duration", "--clip", clip)
