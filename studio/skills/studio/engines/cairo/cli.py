#!/usr/bin/env python3
"""The cairo engine: the studio's engine interface drawn natively, with no browser and no local listener.

The same operations and JSON replies as the live engine (engines/live/cli.mjs), for a video whose
video.json says "engine": "cairo". Needs pycairo (and ffmpeg for render and scaled stills), nothing else.

  python3 cli.py still    --video DIR --clip ID --t SEC --out PNG [--layers L] [--scale S]
  python3 cli.py stills   --video DIR --requests JSON
  python3 cli.py render   --video DIR --clip ID --out MP4 [--quality draft|final] [--range A B]
  python3 cli.py boxes    --video DIR --clip ID --t SEC
  python3 cli.py boxesAt  --video DIR --requests JSON
  python3 cli.py duration --video DIR --clip ID

A chapter is scenes/<clip>.py defining `scene(c)`, called once per frame with a context `c`:

  c.t, c.frame, c.fps, c.width, c.height, c.clip      clip time in seconds, its frame, the format
  c.stage_height                                      pixels above the caption band
  c.cue(name)                                         a cues.json event in clip seconds (KeyError if none)
  c.cr                                                the raw cairo context, in pixels, y down
  c.rect(name, x, y, w, h, fill=, stroke=, radius=)   a rectangle; colours are (r, g, b) in 0..1 or "#rrggbb"
  c.text(name, x, y, string, size=, color=, anchor="left"|"center"|"right", font=)
  c.line(name, x1, y1, x2, y2, color=, width=)
  Named shapes are what `boxes` reports, as the live engine's labelled elements are. Everything must be a
  function of c.t alone: a frame drawn out of order is the same frame.

Not supported (declared, never faked): boards for a chapter without a scene (it draws the background),
the look sheet, 3D, plates, and camera boxes. Captions are drawn from the timeline's caption chunks.
"""
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_LAYOUT = {"width": 1920, "height": 1080, "fps": 30, "band": {"height": 160, "style": "opaque"}}
QUALITY = {"draft": {"scale": 0.5, "crf": 26}, "final": {"scale": 1, "crf": 18}}
BACKGROUND = (0.055, 0.07, 0.09)
INK = (0.9, 0.92, 0.94)


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)


try:
    import cairo
except ImportError:
    fail("the cairo engine needs pycairo (pip install pycairo, or uv run --with pycairo); no browser is involved")


def colour(c):
    if isinstance(c, str):
        h = c.lstrip("#")
        return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return tuple(c)


def half_up(x):
    return int(math.floor(x + 0.5))


class Context:
    def __init__(self, cr, video, layout, timeline, clip, frame):
        self.cr, self.layout, self.clip = cr, layout, clip
        self.width, self.height, self.fps = layout["width"], layout["height"], timeline["fps"]
        self.frame, self.t = frame, frame / self.fps
        self.stage_height = self.height - layout.get("band", {}).get("height", 0)
        self._start = next(c for c in timeline["tracks"]["scene"] if c["id"] == clip)["start"]
        self._cues = timeline.get("cues", {})
        self.boxes = []

    def cue(self, name):
        return self._cues[name] - self._start

    def _record(self, name, x, y, w, h):
        self.boxes.append({"name": name, "x": x, "y": y, "w": w, "h": h, "named": True})

    def rect(self, name, x, y, w, h, fill=None, stroke=None, radius=0, width=2):
        cr = self.cr
        cr.new_sub_path()
        if radius:
            for cx, cy, a in ((x + w - radius, y + radius, -90), (x + w - radius, y + h - radius, 0),
                              (x + radius, y + h - radius, 90), (x + radius, y + radius, 180)):
                cr.arc(cx, cy, radius, math.radians(a), math.radians(a + 90))
            cr.close_path()
        else:
            cr.rectangle(x, y, w, h)
        if fill is not None:
            cr.set_source_rgb(*colour(fill))
            cr.fill_preserve() if stroke is not None else cr.fill()
        if stroke is not None:
            cr.set_source_rgb(*colour(stroke))
            cr.set_line_width(width)
            cr.stroke()
        cr.new_path()
        if name:
            self._record(name, x, y, w, h)

    def text(self, name, x, y, string, size=36, color=INK, anchor="left", font="Sans"):
        cr = self.cr
        cr.select_font_face(font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(size)
        e = cr.text_extents(string)
        left = x - (e.x_advance if anchor == "right" else e.x_advance / 2 if anchor == "center" else 0)
        cr.set_source_rgb(*colour(color))
        cr.move_to(left, y)
        cr.show_text(string)
        cr.new_path()
        if name:
            fe = cr.font_extents()
            self._record(name, left, y - fe[0], e.x_advance, fe[0] + fe[1])

    def line(self, name, x1, y1, x2, y2, color=INK, width=3):
        cr = self.cr
        cr.set_source_rgb(*colour(color))
        cr.set_line_width(width)
        cr.move_to(x1, y1)
        cr.line_to(x2, y2)
        cr.stroke()
        if name:
            self._record(name, min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))


def read(path, default=None):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else default


def clip_range(timeline, clip):
    c = next((x for x in timeline["tracks"]["scene"] if x["id"] == clip), None)
    if c is None:
        fail(f"no clip {clip} in timeline.json")
    first = half_up(c["start"] * timeline["fps"])
    return first, half_up(c["end"] * timeline["fps"]) - first


def scene_for(video, clip):
    f = Path(video) / "scenes" / f"{clip}.py"
    if not f.exists():
        return None
    ns = {"__file__": str(f), "__name__": f"scene_{clip}"}
    exec(compile(f.read_text(), str(f), "exec"), ns)
    if "scene" not in ns:
        fail(f"{f} defines no scene(c)")
    return ns["scene"]


def caption_at(timeline, t):
    for c in timeline["tracks"].get("captions", []):
        if c["start"] <= t < c["end"]:
            return c["lines"]
    return []


def draw(video, layout, timeline, scene, clip, frame, layers="all"):
    """(surface, boxes, band) for one frame of a clip."""
    W, H = layout["width"], layout["height"]
    band = layout.get("band", {}).get("height", 0)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    cr = cairo.Context(surface)
    cr.set_antialias(cairo.ANTIALIAS_BEST)
    cr.set_source_rgb(*BACKGROUND)
    cr.paint()
    c = Context(cr, video, layout, timeline, clip, frame)
    if layers != "background" and scene is not None:
        try:
            scene(c)
        except Exception as e:      # the clip, the time and the error, as the other engines report
            fail(f"scene error in {clip} at {c.t:.3f} s: {type(e).__name__}: {e}")
    if layers in ("all", "no-captions") and band:
        cr.set_source_rgb(0.03, 0.04, 0.05)
        cr.rectangle(0, H - band, W, band)
        cr.fill()
    if layers == "all" and band:
        lines = caption_at(timeline, timeline_t(timeline, clip, frame))
        for i, line in enumerate(lines):
            c.text("caption", W / 2, H - band + 60 + i * 56, line, size=44, anchor="center")
    return surface, c.boxes, {"y": H - band, "h": band}


def timeline_t(timeline, clip, frame):
    first, _ = clip_range(timeline, clip)
    return (first + frame) / timeline["fps"]


def frame_in(timeline, clip, sec):
    return min(clip_range(timeline, clip)[1] - 1, max(0, half_up(float(sec) * timeline["fps"])))


def scaled(src, scale, out):
    if float(scale) == 1:
        Path(src).replace(out)
        return
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", f"scale=iw*{scale}:-2", str(out)])
    if r.returncode != 0:
        fail(f"could not scale a still to {out}")


def stills(video, requests):
    timeline, layout = read(Path(video) / "timeline.json"), read(Path(video) / "layout.json", DEFAULT_LAYOUT)
    done = []
    for r in requests:
        frame = frame_in(timeline, r["clip"], r["t"])
        surface, _, _ = draw(video, layout, timeline, scene_for(video, r["clip"]), r["clip"], frame, r.get("layers") or "all")
        out = Path(r["out"])
        out.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as d:
            raw = Path(d) / "still.png"
            surface.write_to_png(str(raw))
            scaled(raw, r.get("scale") or 1, out)
        done.append({"clip": r["clip"], "t": float(r["t"]), "frame": clip_range(timeline, r["clip"])[0] + frame, "out": str(out)})
    return {"stills": done}


def boxes_at(video, requests):
    timeline, layout = read(Path(video) / "timeline.json"), read(Path(video) / "layout.json", DEFAULT_LAYOUT)
    frames = []
    for r in requests:
        _, boxes, band = draw(video, layout, timeline, scene_for(video, r["clip"]), r["clip"], frame_in(timeline, r["clip"], r["t"]))
        frames.append({"clip": r["clip"], "t": float(r["t"]), "band": band, "boxes": boxes})
    return {"frames": frames}


def render(video, clip, out, quality, rng):
    import time
    q = QUALITY.get(quality or "draft") or fail(f"unknown quality {quality}")
    timeline, layout = read(Path(video) / "timeline.json"), read(Path(video) / "layout.json", DEFAULT_LAYOUT)
    count = clip_range(timeline, clip)[1]
    a, b = (half_up(rng[0] * timeline["fps"]), min(count - 1, half_up(rng[1] * timeline["fps"]))) if rng else (0, count - 1)
    scene, started = scene_for(video, clip), time.time()
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    W, H = layout["width"], layout["height"]
    scale = [] if q["scale"] == 1 else ["-vf", f"scale=iw*{q['scale']}:-2"]
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-framerate", str(timeline["fps"]),
                           "-i", "-", *scale, "-c:v", "libx264", "-crf", str(q["crf"]), "-pix_fmt", "yuv420p", "-r", str(timeline["fps"]), str(out)],
                          stdin=subprocess.PIPE)
    for f in range(a, b + 1):
        surface, _, _ = draw(video, layout, timeline, scene, clip, f)
        surface.flush()
        ff.stdin.write(bytes(surface.get_data()))
    ff.stdin.close()
    if ff.wait() != 0:
        fail("ffmpeg failed")
    return {"clip": clip, "out": str(out), "quality": quality or "draft", "frames": b - a + 1, "seconds": time.time() - started}


def duration(video, clip):
    timeline = read(Path(video) / "timeline.json")
    frames = clip_range(timeline, clip)[1]
    return {"clip": clip, "frames": frames, "fps": timeline["fps"], "seconds": frames / timeline["fps"]}


def main(argv):
    if not argv:
        fail("usage: cli.py OP --video DIR …")
    op, rest, opt, i = argv[0], argv[1:], {}, 0
    while i < len(rest):
        if rest[i].startswith("--"):
            key = rest[i][2:]
            if key == "range":
                opt["range"] = (float(rest[i + 1]), float(rest[i + 2]))
                i += 2
            else:
                opt[key] = rest[i + 1] if i + 1 < len(rest) and not rest[i + 1].startswith("--") else True
                i += 1
        i += 1
    video = str(Path(opt["video"]).resolve())
    ops = {
        "still": lambda: stills(video, [{"clip": opt["clip"], "t": opt["t"], "out": opt["out"], "layers": opt.get("layers"), "scale": opt.get("scale")}]),
        "stills": lambda: stills(video, json.loads(Path(opt["requests"]).read_text())),
        "render": lambda: render(video, opt["clip"], opt["out"], opt.get("quality"), opt.get("range")),
        "boxes": lambda: (lambda f: {"clip": opt["clip"], "t": float(opt["t"]), "boxes": {"band": f["band"], "boxes": f["boxes"]}})(
            boxes_at(video, [{"clip": opt["clip"], "t": opt["t"]}])["frames"][0]),
        "boxesAt": lambda: boxes_at(video, json.loads(Path(opt["requests"]).read_text())),
        "duration": lambda: duration(video, opt["clip"]),
    }
    if op not in ops:
        print(f"unknown op {op}; this engine has {', '.join(ops)}", file=sys.stderr)
        sys.exit(2)
    result = json.dumps(ops[op]())
    if opt.get("reply") and opt["reply"] is not True:
        Path(opt["reply"]).write_text(result)
    else:
        print(result)


if __name__ == "__main__":
    main(sys.argv[1:])
