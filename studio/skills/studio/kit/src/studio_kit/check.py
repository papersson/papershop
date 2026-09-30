"""`studio check VIDEO`: deterministic checks that run through the engine interface.

  length       each clip's frame count, as the engine computes it, equals the timeline's
  determinism  sample frames rendered twice in separate engine calls have the same hash
  bounds       every named element lies inside the frame, and captions inside the caption band
  band         no scene element enters the caption band: at sampled times the scene alone (layers
               no-band) and the bare background are compared over the band's pixels, and every
               named element's box is checked against the band
  contrast     the brightest pixel under the caption band, against the caption colour, is at least 4.5:1
  grid, palette  pixel videos only (see pixel.py): the canvas is whole k×k blocks, in the palette
  filler, cuts, levels, sync, segments  footage videos only (see footage.py)

Sample times are spread across each clip's sentences, `--samples` per clip.
"""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from . import timeline as tl
from .engine import Engine

CAPTION_COLOUR = (0xE6, 0xEB, 0xF0)      # theme.ts INK
MIN_CONTRAST = 4.5
SIDE_MARGIN = 80                         # px kept free either side of a caption line
SLACK = 1.0                              # px of tolerance on box edges


def sample_times(t, per_clip):
    """[{clip, t}]: `per_clip` moments per clip, each near the end of a sentence spread over the clip."""
    out = []
    for c in t["tracks"]["scene"]:
        sents = [s for s in t["tracks"]["narration"] if s["clip"] == c["id"]]
        if not sents:
            continue
        picks = sorted({sents[min(len(sents) - 1, round(i * (len(sents) - 1) / max(1, per_clip - 1)))]["id"]
                        for i in range(per_clip)})
        for s in sents:
            if s["id"] in picks:
                out.append({"clip": c["id"], "t": round(max(s["start"], s["end"] - 0.15) - c["start"], 3)})
    return out


def length(video, engine=None):
    engine, t = engine or Engine(video), tl.load(video)
    rows = []
    for c in t["tracks"]["scene"]:
        want = tl.frames(t, c["id"])[1]
        got = engine.duration(c["id"])["frames"]
        rows.append({"check": "length", "clip": c["id"], "ok": got == want, "detail": f"engine {got} frames, timeline {want}"})
    return rows


def determinism(video, samples=3, engine=None):
    """Render `samples` frames per clip twice, in separate engine calls, and compare their hashes.
    A frame that differs means some state leaks between frames (a timer, unseeded randomness)."""
    engine, t = engine or Engine(video), tl.load(video)
    reqs = []
    for c in t["tracks"]["scene"]:
        dur = c["end"] - c["start"]
        reqs += [{"clip": c["id"], "t": round(dur * (i + 1) / (samples + 1), 3)} for i in range(samples)]
    with tempfile.TemporaryDirectory() as tmp:
        runs = []
        for run in ("a", "b"):
            batch = [{**r, "out": str(Path(tmp) / f"{run}-{r['clip']}-{r['t']}.png")} for r in reqs]
            engine.stills(batch)
            runs.append([hashlib.sha256(Path(r["out"]).read_bytes()).hexdigest() for r in batch])
    return [{"check": "determinism", "clip": r["clip"], "t": r["t"], "ok": a == b, "detail": f"{a[:10]} {b[:10]}"}
            for r, a, b in zip(reqs, *runs)]


def _boxes(video, per_clip, engine):
    return engine.layout(), engine.boxes_at(sample_times(tl.load(video), per_clip))


def bounds(video, samples=3, engine=None, boxes=None):
    engine = engine or Engine(video)
    lay, frames = boxes or _boxes(video, samples, engine)
    W, H, band = lay["width"], lay["height"], lay["height"] - lay["band"]["height"]
    rows = []
    for f in frames:
        bad = []
        for b in f["boxes"]:
            if b["name"] == "caption":
                if b["x"] < SIDE_MARGIN - SLACK or b["x"] + b["w"] > W - SIDE_MARGIN + SLACK:
                    bad.append(f"caption line {b['w']:.0f} px wide leaves the {SIDE_MARGIN} px margins")
                if b["y"] < band - SLACK or b["y"] + b["h"] > H + SLACK:
                    bad.append("caption outside the band")
            elif b["x"] < -SLACK or b["y"] < -SLACK or b["x"] + b["w"] > W + SLACK:
                bad.append(f"{b['name']!r} leaves the frame")
        rows.append({"check": "bounds", "clip": f["clip"], "t": f["t"], "ok": not bad, "detail": "; ".join(bad)})
    return rows


def band_guard(video, samples=3, engine=None, boxes=None):
    """Named scene elements must end above the band."""
    engine = engine or Engine(video)
    lay, frames = boxes or _boxes(video, samples, engine)
    band = lay["height"] - lay["band"]["height"]
    rows = []
    for f in frames:
        bad = [f"{b['name']!r} reaches y={b['y'] + b['h']:.0f} (band starts at {band})"
               for b in f["boxes"] if b["name"] != "caption" and b["y"] + b["h"] > band + SLACK and b["y"] < band + lay["band"]["height"]]
        rows.append({"check": "band", "clip": f["clip"], "t": f["t"], "ok": not bad, "detail": "; ".join(bad)})
    return rows


def _band_pixels(png, lay):
    """Raw RGB bytes of the caption band region of an image, through ffmpeg."""
    h = lay["band"]["height"]
    return subprocess.run(["ffmpeg", "-v", "error", "-i", str(png), "-vf", f"crop={lay['width']}:{h}:0:{lay['height'] - h}",
                           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout


def luminance(rgb):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def brightest(pixels):
    best = (0, 0, 0)
    seen = set()
    for i in range(0, len(pixels), 3):
        px = (pixels[i], pixels[i + 1], pixels[i + 2])
        if px not in seen:
            seen.add(px)
            if luminance(px) > luminance(best):
                best = px
    return best


def band_pixels_check(video, samples=3, engine=None):
    """The scene alone against the bare background, over the band's pixels: any difference is
    scene content in the band. Then the caption contrast against what is under the band."""
    engine = engine or Engine(video)
    t, lay = tl.load(video), engine.layout()
    times = sample_times(t, samples)
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        reqs = []
        for i, r in enumerate(times):
            for layer in ("no-band", "background", "no-captions"):
                reqs.append({**r, "layers": layer, "out": str(Path(tmp) / f"{i}-{layer}.png")})
        engine.stills(reqs)
        for i, r in enumerate(times):
            scene = _band_pixels(Path(tmp) / f"{i}-no-band.png", lay)
            bare = _band_pixels(Path(tmp) / f"{i}-background.png", lay)
            diff = sum(1 for a, b in zip(scene, bare) if a != b)
            rows.append({"check": "band", "clip": r["clip"], "t": r["t"], "ok": diff == 0,
                         "detail": "" if diff == 0 else f"{diff // 3} pixels of scene content in the band"})
            under = brightest(_band_pixels(Path(tmp) / f"{i}-no-captions.png", lay))
            ratio = contrast_ratio(CAPTION_COLOUR, under)
            rows.append({"check": "contrast", "clip": r["clip"], "t": r["t"], "ok": ratio >= MIN_CONTRAST,
                         "detail": f"{ratio:.1f}:1 against the brightest pixel {under}"})
    return rows


CHECKS = ("length", "determinism", "bounds", "band", "contrast")


def genre(video):
    f = Path(video) / "video.json"
    return json.loads(f.read_text()).get("genre", "explainer") if f.exists() else "explainer"


def run(video, samples=3, only=None, engine=None, fmt=None):
    extra = {"pixel": ("grid", "palette"), "footage": ("filler", "cuts", "levels", "sync", "segments")}.get(genre(video), ())
    only = set(only or CHECKS + extra)
    engine = engine or Engine(video, fmt=fmt)
    rows = []
    if "length" in only:
        rows += length(video, engine)
    if "determinism" in only:
        rows += determinism(video, samples, engine)
    if only & {"bounds", "band"}:
        boxes = _boxes(video, samples, engine)
        if "bounds" in only:
            rows += bounds(video, samples, engine, boxes)
        if "band" in only:
            rows += band_guard(video, samples, engine, boxes)
    if only & {"band", "contrast"}:
        pix = band_pixels_check(video, samples, engine)
        rows += [r for r in pix if r["check"] in only]
    if genre(video) == "footage" and only & {"filler", "cuts", "levels", "sync", "segments"}:
        from . import footage
        rows += [r for r in footage.checks(video) if r["check"] in only]
    if only & {"grid", "palette"}:
        from . import pixel
        rows += [r for r in pixel.run(video, samples, engine) if r["check"] in only]
    return rows


def main(args):
    rows = run(args.video, args.samples, args.only.split(",") if args.only else None, fmt=args.format)
    for r in rows:
        where = f"{r['clip']}" + (f" t={r['t']}" if "t" in r else "")
        print(f"{'ok  ' if r['ok'] else 'FAIL'}  {r['check']:11} {where:16} {r['detail']}".rstrip())
    by = {}
    for r in rows:
        by.setdefault(r["check"], [0, 0])[0 if r["ok"] else 1] += 1
    print("; ".join(f"{k}: {v[0]} ok" + (f", {v[1]} FAILED" if v[1] else "") for k, v in by.items()))
    return 1 if any(not r["ok"] for r in rows) else 0
