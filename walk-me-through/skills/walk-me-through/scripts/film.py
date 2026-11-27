#!/usr/bin/env python3
"""Play a walkthrough's clicks as a video: each line types out, then its one change, then a rest.

    python3 -I scripts/film.py OUT_DIR [--out OUT_DIR/film.mp4] [--fps 30] [--size 1920x1080] [--silent]

The beat comes from the engine's ?film mode (FILM in walk.js): the caption types out, the change
starts a quarter second after it is finished, and the picture rests while the reader catches up.
Each change makes the sound of its kind (an arrival, a move, a verdict, a page turn: see voices()),
and the line is typed beside the thing it is about. --sounds none for silence, all for a soft key
per letter as well. The page is rendered with this skill's
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


def _env(t, attack, decay):
    return min(1.0, t / attack) * math.exp(-t / decay)


def _note(freq, seconds, attack=0.004, decay=0.08, partials=((1, 1.0), (2, 0.25), (3, 0.08))):
    n = int(RATE * seconds)
    return [_env(i / RATE, attack, decay) * sum(a * math.sin(2 * math.pi * freq * m * i / RATE) for m, a in partials)
            for i in range(n)]


def _noise(seconds, seed, cutoff, shape):
    """Noise through a one-pole low-pass whose cutoff follows cutoff(x), shaped by shape(x), x in 0..1."""
    rnd = random.Random(seed)
    n, y, out = int(RATE * seconds), 0.0, []
    for i in range(n):
        x = i / n
        a = 1 - math.exp(-2 * math.pi * cutoff(x) / RATE)
        y += a * ((rnd.random() * 2 - 1) - y)
        out.append(y * shape(x))
    return out


def _seq(*parts):
    """Notes placed at offsets in seconds: (offset, samples)."""
    end = max(int(RATE * off) + len(smp) for off, smp in parts)
    out = [0.0] * end
    for off, smp in parts:
        o = int(RATE * off)
        for i, v in enumerate(smp):
            out[o + i] += v
    return out


def _level(samples, dbfs):
    peak = max(abs(v) for v in samples) or 1
    g = 10 ** (dbfs / 20) / peak
    return [v * g for v in samples]


def _knock(f, seed):
    return [_env(i / RATE, 0.0015, 0.009) * (0.8 * (0.75 * math.sin(2 * math.pi * f * i / RATE)
            + 0.25 * math.sin(2 * math.pi * 2.08 * f * i / RATE)) + 0.2 * (random.Random(seed + i).random() * 2 - 1))
            for i in range(int(RATE * 0.045))]


# A staggered group ticks once per item, climbing a major pentatonic scale (no step can sound wrong
# against another), and holds the top note for a long group.
PENTATONIC = (0, 2, 4, 7, 9, 12, 14, 16)


def stepped_tick(step):
    semis = PENTATONIC[min(step, len(PENTATONIC) - 1)]
    return _level(_knock(1250 * 2 ** (semis / 12), 7), -24)


def voices():
    """One sound per kind of change, each with one meaning (after Kit Langton's effect.institute):
    tick, a thing arrives; tap, a thing already there changes; glide, a thing travels; yes and no, a
    verdict lands; ring, a part is singled out; wipe, the stage clears; turn, a new chapter; key, a
    letter of the line. Synthesized and seeded, so every render is the same; levels sit well under
    a voice would, since the film has none to sit under."""
    knock = _knock
    return {
        "tick": _level(knock(1250, 7), -24),
        "tap": _level(knock(880, 11), -30),
        "glide": _level(_noise(0.9, 3, lambda x: 500 + 2600 * math.sin(math.pi * x), lambda x: math.sin(math.pi * x) ** 2), -33),
        "yes": _level(_seq((0, _note(659.25, 0.35)), (0.09, _note(987.77, 0.45, decay=0.12))), -23),
        "no": _level(_seq((0, _note(233.08, 0.35, decay=0.1, partials=((1, 1), (3, .3), (5, .1)))),
                           (0.11, _note(185.0, 0.5, decay=0.14, partials=((1, 1), (3, .3), (5, .1))))), -23),
        "ring": _level(_note(1567.98, 0.9, attack=0.006, decay=0.25, partials=((1, 1), (2.76, .3))), -28),
        "wipe": _level(_noise(0.35, 5, lambda x: 3500 * (1 - x) + 300, lambda x: math.sin(math.pi * min(1, x * 1.3)) ** 2), -30),
        "turn": _level(_seq((0, _note(523.25, 0.4, decay=0.1)), (0.08, _note(659.25, 0.4, decay=0.1)),
                            (0.16, _note(783.99, 0.6, decay=0.16))), -27),
        "key": _level([_env(i / RATE, 0.0005, 0.004) * (random.Random(13 + i).random() * 2 - 1) for i in range(int(RATE * 0.02))], -38),
    }


LEVELS = {"none": set(), "events": {"tick", "tap", "glide", "yes", "no", "ring", "wipe", "turn"}}
LEVELS["all"] = LEVELS["events"] | {"key"}


def write_audio(path, duration_ms, sounds, level="events"):
    total = int(RATE * duration_ms / 1000) + 1
    samples = [0.0] * total
    bank, keep = voices(), LEVELS[level]
    for s in sounds:
        if s["kind"] not in keep or s["kind"] not in bank:
            continue
        start = int(RATE * s["t"] / 1000)
        step = s.get("step") or 0
        if step and (s["kind"], step) not in bank:
            bank[(s["kind"], step)] = stepped_tick(step)
        for i, v in enumerate(bank[(s["kind"], step)] if step else bank[s["kind"]]):
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
    ap.add_argument("--sounds", default="events", choices=sorted(LEVELS),
                    help="events (default): one sound per kind of change; all: also a soft key per letter; none")
    ap.add_argument("--sound-sheet", metavar="DIR", help="also write each sound as DIR/<kind>.wav, to audition them")
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
            info = browser.eval("({duration: WalkFilm.duration, sounds: WalkFilm.sounds})")
            if not info:
                sys.exit("the page did not start its film mode")
            duration = info["duration"] if args.until is None else min(info["duration"], args.until * 1000)
            frames = int(math.ceil(duration / 1000 * args.fps))
            audio = tmp / "ticks.wav"
            write_audio(audio, duration, [x for x in info["sounds"] if x["t"] < duration], args.sounds)
            if args.sound_sheet:
                sheet = Path(args.sound_sheet)
                sheet.mkdir(parents=True, exist_ok=True)
                for kind in voices():
                    write_audio(sheet / f"{kind}.wav", 1000, [{"t": 50, "kind": kind}], "all")
                write_audio(sheet / "stagger.wav", 1000, [{"t": 50 + 90 * i, "kind": "tick", "step": i} for i in range(5)])
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
