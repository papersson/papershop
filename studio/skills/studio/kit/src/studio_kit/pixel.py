"""Pixel-art checks, for videos whose genre is pixel.

video.json says how the art is built:
  "pixel": {"grid": [320, 180], "palette": ["#0f1318", "#e6ebf0", ...]}

  grid     the canvas's output is made of whole k×k blocks, one per logical pixel: crop the canvas,
           scale it down and back up with nearest-neighbour, and it must be unchanged. Anything else
           is anti-aliasing, a fractional scale or sub-pixel motion.
  palette  every colour on the canvas, read back at its logical resolution, is in the palette.

Both look only at the canvas, found through the engine's `boxes` (the element named pixel-canvas),
so the caption band and the stage's background don't have to be in the palette.
"""
import json
import subprocess
import tempfile
from pathlib import Path

from . import timeline as tl
from .check import SLACK, sample_times
from .engine import Engine


def config(video):
    cfg = json.loads((Path(video) / "video.json").read_text()).get("pixel")
    if not cfg or "grid" not in cfg or "palette" not in cfg:
        raise SystemExit('video.json needs "pixel": {"grid": [w, h], "palette": ["#rrggbb", ...]}')
    return cfg


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _ffmpeg_raw(png, vf):
    return subprocess.run(["ffmpeg", "-v", "error", "-i", str(png), "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                          capture_output=True, check=True).stdout


def _differing_pixels(png, crop, k):
    """Count of pixels that change when the crop goes down and back up by k with nearest-neighbour."""
    cw, ch = crop[2], crop[3]
    a = _ffmpeg_raw(png, f"crop={cw}:{ch}:{crop[0]}:{crop[1]}")
    b = _ffmpeg_raw(png, f"crop={cw}:{ch}:{crop[0]}:{crop[1]},scale={cw // k}:{ch // k}:flags=neighbor,scale={cw}:{ch}:flags=neighbor")
    return sum(1 for x, y in zip(a, b) if x != y) // 3


def run(video, samples=3, engine=None, fmt=None):
    engine = engine or Engine(video, fmt=fmt)
    cfg = config(video)
    gw, gh = cfg["grid"]
    palette = {hex_rgb(c) for c in cfg["palette"]}
    times = sample_times(tl.load(video), samples)
    frames = engine.boxes_at(times)
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        stills = [{**r, "out": str(Path(tmp) / f"{i}.png"), "layers": "no-band"} for i, r in enumerate(times)]
        engine.stills(stills)
        for i, (r, f) in enumerate(zip(times, frames)):
            canvas = next((b for b in f["boxes"] if b["name"] == "pixel-canvas"), None)
            if canvas is None:
                rows += [{"check": c, "clip": r["clip"], "t": r["t"], "ok": False, "detail": "no PixelCanvas in this frame"}
                         for c in ("grid", "palette")]
                continue
            crop = (round(canvas["x"]), round(canvas["y"]), round(canvas["w"]), round(canvas["h"]))
            k = crop[2] // gw
            if k < 1 or abs(crop[2] - k * gw) > SLACK or abs(crop[3] - k * gh) > SLACK:
                rows.append({"check": "grid", "clip": r["clip"], "t": r["t"], "ok": False,
                             "detail": f"canvas is {crop[2]}x{crop[3]} px, not a whole multiple of the {gw}x{gh} grid"})
                continue
            crop = (crop[0], crop[1], gw * k, gh * k)
            bad = _differing_pixels(stills[i]["out"], crop, k)
            rows.append({"check": "grid", "clip": r["clip"], "t": r["t"], "ok": bad == 0,
                         "detail": f"{k}x scale" if bad == 0 else f"{bad} pixels are not on the {k}x grid"})
            raw = _ffmpeg_raw(stills[i]["out"], f"crop={crop[2]}:{crop[3]}:{crop[0]}:{crop[1]},scale={gw}:{gh}:flags=neighbor")
            used = {tuple(raw[j:j + 3]) for j in range(0, len(raw), 3)}
            off = sorted(used - palette)
            rows.append({"check": "palette", "clip": r["clip"], "t": r["t"], "ok": not off,
                         "detail": f"{len(used)} colours" if not off else f"{len(off)} colours outside the palette, e.g. #{'%02x%02x%02x' % off[0]}"})
    return rows
