"""The engine interface: still, render, boxes and duration for one clip of a video.

Every engine is a CLI under engines/<name>/ that prints one JSON object per call; this module is
the only place the kit calls it, so a second engine only needs a second `_command`.
"""
import json
import subprocess
import tempfile
from pathlib import Path

from . import settings
from . import timeline as tl
from .env import engine_dir, resolve_browser

ENGINES = ("remotion", "motion-canvas")
LAYERS = ("all", "no-captions", "no-band", "background")


class EngineError(RuntimeError):
    pass


class Engine:
    def __init__(self, video, name=None, fmt=None):
        self.video = Path(video).resolve()
        self.name = name or self._video_engine()
        self.fmt = fmt
        self.browser, _ = resolve_browser()

    def _video_engine(self):
        return settings.load(self.video)["engine"]

    def layout(self):
        """The layout this engine renders (the video's, with its format applied)."""
        return tl.layout(self.video, self.fmt)

    def _command(self, op, *args):
        if self.name not in ENGINES:
            raise EngineError(f"no engine named {self.name}; known: {', '.join(ENGINES)}")
        cmd = ["node", str(engine_dir(self.name) / "cli.mjs"), op, "--video", str(self.video), *args]
        if self.browser:
            cmd += ["--browser", self.browser]
        if self.fmt and self.fmt != "16:9":
            cmd += ["--layout", str(tl.layout_file(self.video, self.fmt))]
        return cmd

    def _call(self, op, *args):
        run = subprocess.run(self._command(op, *map(str, args)), capture_output=True, text=True)
        if run.returncode != 0:
            cause = run.stderr.strip()[-3000:]
            browser_failure = any(s in cause.lower() for s in ("failed to launch", "browser process", "sandbox", "operation not permitted", "eacces"))
            hint = ("\nBrowser launch failed. Try this studio invocation directly instead of through a helper shell; "
                    "run studio doctor and set STUDIO_BROWSER to a working browser. Use the host's approved "
                    "execution path for sandbox restrictions; do not disable its sandbox.") if browser_failure else ""
            raise EngineError(f"{self.name} {op} failed:\n{cause}{hint}")
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

    def durations(self, clips):
        """{clip: frames} for many clips; one browser session where the engine supports it."""
        if self.name == "remotion":
            return {r["clip"]: r["frames"] for r in self._call("durations", "--clips", ",".join(clips))["clips"]}
        return {c: self.duration(c)["frames"] for c in clips}

    @property
    def boxes_keep_frames(self):
        """Whether boxes_at can also save each frame (requests with "out"), so a caller needing
        both renders every frame once."""
        return self.name == "remotion"
