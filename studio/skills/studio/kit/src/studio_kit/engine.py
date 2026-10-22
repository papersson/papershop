"""The engine interface: still, render, boxes and duration for one clip of a video.

Every engine is a CLI under engines/<name>/ that answers each call with one JSON object, written
to the file named by --reply (engines/shared/reply.js); this module is the only place the kit calls
it, so a second engine only needs a second `_command`.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

from . import proc
from . import settings
from . import timeline as tl
from .env import engine_dir, resolve_browser

ENGINES = ("remotion", "motion-canvas", "live", "cairo")
LAYERS = ("all", "no-captions", "no-band", "background")
LOOK_ENGINES = ("live", "remotion")      # the engines that draw a look sheet
# What each engine needs and gives (declared, so a missing capability is reported, never faked):
# needs_browser/needs_listener: launches Chromium / binds a local port; boxes: pixel boxes of named elements;
# layers: the layers a still can omit; live_preview: the desk can redraw its scenes live; look: the look sheet.
CAPABILITIES = {
    "remotion": dict(needs_browser=True, needs_listener=True, boxes=True, layers=LAYERS, live_preview=False, look=True),
    "motion-canvas": dict(needs_browser=True, needs_listener=True, boxes=True, layers=LAYERS, live_preview=False, look=False),
    "live": dict(needs_browser=True, needs_listener=True, boxes=True, layers=LAYERS, live_preview=True, look=True),
    "cairo": dict(needs_browser=False, needs_listener=False, boxes=True, layers=LAYERS, live_preview=False, look=False),
}


class EngineError(RuntimeError):
    pass


LAUNCH_HINT = ("Browser launch failed. Try this studio invocation directly instead of through a helper shell; "
               "run studio doctor and set STUDIO_BROWSER to a working browser. Use the host's approved "
               "execution path for sandbox restrictions; do not disable its sandbox.")


def launch_hint(stderr):
    """LAUNCH_HINT when an engine's error reads as the browser failing to start (often a sandbox), else ""."""
    signs = ("failed to launch", "browser process", "sandbox", "operation not permitted", "eacces")
    return LAUNCH_HINT if any(s in stderr.lower() for s in signs) else ""


class Engine:
    def __init__(self, video, name=None, fmt=None):
        self.video = Path(video).resolve()
        self.name = name or self._video_engine()
        self.fmt = fmt
        self.browser = None if self.name == "cairo" else resolve_browser()[0]
        self.gl = settings.load(self.video)["gl"] if (self.video / "video.json").exists() else "cpu"

    def _video_engine(self):
        return settings.load(self.video)["engine"]

    def layout(self):
        """The layout this engine renders (the video's, with its format applied)."""
        return tl.layout(self.video, self.fmt)

    @property
    def capabilities(self):
        return CAPABILITIES[self.name]

    def _command(self, op, *args):
        if self.name not in ENGINES:
            raise EngineError(f"no engine named {self.name}; known: {', '.join(ENGINES)}")
        if self.name == "cairo":      # native: Python and pycairo, no browser and no listener
            cmd = [os.environ.get("STUDIO_CAIRO_PYTHON") or sys.executable, str(engine_dir("cairo") / "cli.py"), op, "--video", str(self.video), *args]
            if self.fmt and self.fmt != "16:9":
                cmd += ["--layout", str(tl.layout_file(self.video, self.fmt))]
            return cmd
        cmd = [proc.tool("node"), str(engine_dir(self.name) / "cli.mjs"), op, "--video", str(self.video), *args]
        if self.browser:
            cmd += ["--browser", self.browser]
        if self.name == "live":
            cmd += ["--gl", self.gl]
        if self.fmt and self.fmt != "16:9":
            cmd += ["--layout", str(tl.layout_file(self.video, self.fmt))]
        return cmd

    def _call(self, op, *args):
        with tempfile.TemporaryDirectory(prefix="studio-reply-") as d:
            answer = Path(d) / "reply.json"
            run = proc.run(self._command(op, *map(str, args), "--reply", str(answer)), capture_output=True, text=True)
            if run.returncode != 0:
                cause = run.stderr.strip()[-3000:]
                hint = launch_hint(cause)
                raise EngineError(f"{self.name} {op} failed:\n{cause}" + (f"\n{hint}" if hint else ""))
            if not answer.exists():
                raise EngineError(f"{self.name} {op} wrote no reply")
            return json.loads(answer.read_text())

    def _plates(self, requests, quality="draft"):
        """Render the frames of a plate (plates.py) these requests draw, before the page draws them:
        [{clip, t}], or a clip's every frame for a render (t None)."""
        from . import plates
        cfg = plates.config(self.video)
        wanted = [r for r in requests if r["clip"] in cfg]
        if not wanted or self.name != "live":
            return
        t = tl.load(self.video)
        need = {}
        for r in wanted:
            count = tl.frames(t, r["clip"])[1]
            frames = range(count) if r.get("t") is None else [min(count - 1, max(0, tl.half_up(float(r["t"]) * t["fps"])))]
            need.setdefault(r["clip"], set()).update(frames)
        plates.ensure(self.video, t, quality, need)

    def still(self, clip, t, out, layers="all", scale=1.0):
        """The exact frame at clip time t, rendered alone."""
        assert layers in LAYERS, layers
        self._plates([{"clip": clip, "t": t}])
        return self._call("still", "--clip", clip, "--t", t, "--out", out, "--layers", layers, "--scale", scale)

    def stills(self, requests):
        """Many stills in one browser session: [{clip, t, out, layers?, scale?}]."""
        self._plates(requests)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump([{**r, "out": str(r["out"])} for r in requests], f)
        try:
            return self._call("stills", "--requests", f.name)
        finally:
            Path(f.name).unlink(missing_ok=True)

    def render(self, clip, out, quality="draft", range_=None):
        """The clip as a silent video, or the part of it between range_ = (a, b) seconds."""
        self._plates([{"clip": clip, "t": None}], quality)
        args = ["--clip", clip, "--out", out, "--quality", quality]
        if range_:
            args += ["--range", range_[0], range_[1]]
        return self._call("render", *args)

    def boxes_at(self, requests):
        """Boxes for many frames in one browser session: [{clip, t}] -> [{clip, t, band, boxes}]."""
        self._plates(requests)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(requests, f)
        try:
            return self._call("boxesAt", "--requests", f.name)["frames"]
        finally:
            Path(f.name).unlink(missing_ok=True)

    def boxes(self, clip, t):
        """Pixel boxes of every labelled element at clip time t, and the caption band's position."""
        self._plates([{"clip": clip, "t": t}])
        return self._call("boxes", "--clip", clip, "--t", t)

    def look(self, outdir, caption=()):
        """The look sheet: one still per page (look-<n>.png in outdir), the band showing `caption`
        (lines); {pages: [{page, title, out}]}. Live and Remotion only."""
        if self.name not in LOOK_ENGINES:
            raise EngineError(f"the look sheet is drawn by the {' and '.join(LOOK_ENGINES)} engines, not {self.name}")
        return self._call("look", "--out", outdir, "--caption", json.dumps(list(caption)))

    def duration(self, clip):
        return self._call("duration", "--clip", clip)

    def webgl(self):
        """The browser and the WebGL renderer the live engine's 3D stage gets on this video's backend:
        {backend, browser, renderer, version, samples, three}."""
        if self.name != "live":
            raise EngineError(f"only the live engine has a 3D stage, not {self.name}")
        return self._call("gl")

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
