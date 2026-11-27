#!/usr/bin/env python3
"""Play a walkthrough's clicks as a video: each line types out, then its one change, then a rest.

    python3 -I scripts/film.py OUT_DIR [--out OUT_DIR/film.mp4] [--fps 30] [--size 1920x1080] [--silent]

The beat comes from the engine's ?film mode (FILM in walk.js): the caption types out, the change
starts a quarter second after it is finished, and the picture rests while the reader catches up.
A soft tick marks each change; --silent leaves it out. The page is rendered with this skill's
current engine (a temporary copy of OUT_DIR with walk.js and walk.css replaced), so an older page
gets the film mode too, and OUT_DIR is not touched apart from the video.

Frames are a pure function of time: one headless Chrome, driven over its debugging pipe, seeks the
page to each frame's moment and takes a screenshot; a frame that cannot differ from the one before
(a rest) is reused. Needs Chrome (WALK_CHROME) and ffmpeg (WALK_FFMPEG). Standard library only.
"""
import argparse
import base64
import fcntl
import json
import math
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import walklib  # noqa: E402

RATE = 48000


class Chrome:
    """A headless Chrome spoken to over --remote-debugging-pipe: NUL-separated JSON on fds 3 and 4."""

    def __init__(self, chrome, profile):
        to_r, self._w = os.pipe()     # we write commands, Chrome reads fd 3
        self._r, from_w = os.pipe()   # Chrome writes fd 4, we read replies
        # Lift Chrome's ends above 4 first, so placing one on 3 or 4 cannot clobber the other.
        hi_r, hi_w = fcntl.fcntl(to_r, fcntl.F_DUPFD, 10), fcntl.fcntl(from_w, fcntl.F_DUPFD, 10)
        os.close(to_r)
        os.close(from_w)
        to_r, from_w = hi_r, hi_w

        def fds():
            os.dup2(to_r, 3)
            os.dup2(from_w, 4)

        args = [chrome, "--headless=new", "--remote-debugging-pipe", "--no-first-run", "--no-default-browser-check",
                "--disable-gpu", "--hide-scrollbars", "--mute-audio", "--force-color-profile=srgb",
                "--font-render-hinting=none", "--disable-extensions", "--disable-background-networking",
                "--allow-file-access-from-files", f"--user-data-dir={profile}", "about:blank"]
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            args.insert(1, "--no-sandbox")
        self.proc = subprocess.Popen(args, pass_fds=(3, 4), preexec_fn=fds,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.close(to_r)
        os.close(from_w)
        self._buf = b""
        self._id = 0
        self.session = None

    def call(self, method, params=None, session=True):
        self._id += 1
        msg = {"id": self._id, "method": method, "params": params or {}}
        if session and self.session:
            msg["sessionId"] = self.session
        os.write(self._w, json.dumps(msg).encode() + b"\0")
        while True:
            while b"\0" not in self._buf:
                chunk = os.read(self._r, 1 << 20)
                if not chunk:
                    raise RuntimeError("Chrome closed the debugging pipe")
                self._buf += chunk
            raw, self._buf = self._buf.split(b"\0", 1)
            reply = json.loads(raw)
            if reply.get("id") == self._id:
                if "error" in reply:
                    raise RuntimeError(f"{method}: {reply['error'].get('message')}")
                return reply.get("result", {})

    def open(self, url, size):
        target = self.call("Target.createTarget", {"url": "about:blank"}, session=False)["targetId"]
        self.session = self.call("Target.attachToTarget", {"targetId": target, "flatten": True}, session=False)["sessionId"]
        self.call("Emulation.setDeviceMetricsOverride", {"width": size[0], "height": size[1], "deviceScaleFactor": 1, "mobile": False})
        self.call("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "no-preference"}]})
        self.call("Page.enable")
        self.call("Page.navigate", {"url": url})

    def eval(self, expr):
        res = self.call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
        if "exceptionDetails" in res:
            raise RuntimeError(res["exceptionDetails"].get("exception", {}).get("description") or str(res["exceptionDetails"]))
        return res.get("result", {}).get("value")

    def shot(self):
        return base64.b64decode(self.call("Page.captureScreenshot", {"format": "png"})["data"])

    def close(self):
        try:
            self.call("Browser.close", session=False)
        except Exception:
            pass
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def tick():
    """The soft tick for a change: a short, low knock, seeded so every render is the same."""
    rnd = random.Random(7)
    n = int(RATE * 0.045)
    out = []
    for i in range(n):
        t = i / RATE
        env = math.exp(-t / 0.009) * min(1.0, t / 0.0015)
        tone = 0.75 * math.sin(2 * math.pi * 1250 * t) + 0.25 * math.sin(2 * math.pi * 2600 * t)
        out.append(env * (0.8 * tone + 0.2 * (rnd.random() * 2 - 1)))
    peak = max(abs(v) for v in out)
    level = 10 ** (-24 / 20)  # quiet: peaks at -24 dBFS
    return [v / peak * level for v in out]


def write_audio(path, duration_ms, ticks):
    total = int(RATE * duration_ms / 1000) + 1
    samples = [0.0] * total
    knock = tick()
    for at in ticks:
        start = int(RATE * at / 1000)
        for i, v in enumerate(knock):
            if start + i < total:
                samples[start + i] += v
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", max(-32767, min(32767, int(v * 32767)))) for v in samples))


def find_ffmpeg():
    return os.environ.get("WALK_FFMPEG") or shutil.which("ffmpeg")


NO_FFMPEG = "no ffmpeg found: install ffmpeg, or set WALK_FFMPEG to one"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out_dir")
    ap.add_argument("--out", help="the video (default OUT_DIR/film.mp4)")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--size", default="1920x1080", help="WxH of the video (default 1920x1080)")
    ap.add_argument("--silent", action="store_true", help="no tick on each change")
    ap.add_argument("--until", type=float, help="stop after this many seconds (for a quick look)")
    args = ap.parse_args()
    chrome = walklib.find_chrome()
    if not chrome:
        sys.exit(walklib.NO_BROWSER)
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        sys.exit(NO_FFMPEG)
    src = Path(args.out_dir)
    if not (src / "page.html").is_file():
        sys.exit(f"{src}/page.html not found: give the page's folder")
    size = tuple(int(v) for v in args.size.split("x"))
    out = Path(args.out) if args.out else src / "film.mp4"

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        page = tmp / "page"
        shutil.copytree(src, page, ignore=shutil.ignore_patterns("shots", "*.mp4"))
        for name in ("walk.js", "walk.css"):
            shutil.copy(walklib.ENGINE / name, page / name)
        browser = Chrome(chrome, tmp / "profile")
        try:
            browser.open((page / "page.html").resolve().as_uri() + "?film", size)
            for _ in range(200):
                if browser.eval("!!(window.WalkFilm && WalkFilm.ready) || !!document.getElementById('walk-error')"):
                    break
                time.sleep(0.05)
            err = browser.eval("(document.getElementById('walk-error') || {}).textContent || ''")
            if err:
                sys.exit("the page has errors; run check.py first:\n" + err)
            info = browser.eval("({duration: WalkFilm.duration, ticks: WalkFilm.ticks})")
            if not info:
                sys.exit("the page did not start its film mode")
            duration = info["duration"] if args.until is None else min(info["duration"], args.until * 1000)
            frames = int(math.ceil(duration / 1000 * args.fps))
            audio = tmp / "ticks.wav"
            write_audio(audio, duration, [] if args.silent else [t for t in info["ticks"] if t < duration])
            out.parent.mkdir(parents=True, exist_ok=True)
            enc = subprocess.Popen(
                [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "image2pipe", "-framerate", str(args.fps),
                 "-i", "-", "-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium",
                 "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest",
                 "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:v", "+bitexact", "-flags:a", "+bitexact",
                 "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
            last_key, last_png, unique = None, None, 0
            started = time.time()
            for i in range(frames):
                key = browser.eval(f"WalkFilm.seek({i * 1000 / args.fps:.3f})")
                if key != last_key:
                    last_png, last_key = browser.shot(), key
                    unique += 1
                enc.stdin.write(last_png)
            enc.stdin.close()
            if enc.wait():
                sys.exit("ffmpeg failed to write the video")
        finally:
            browser.close()
    print(f"{out}: {duration / 1000:.1f} s, {frames} frames ({unique} drawn) in {time.time() - started:.0f} s")


if __name__ == "__main__":
    main()
