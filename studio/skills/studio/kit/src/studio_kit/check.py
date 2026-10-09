"""`studio check VIDEO`: deterministic checks that run through the engine interface.

  length       each clip's frame count, as the engine computes it, equals the timeline's
  determinism  sample frames rendered twice in separate engine calls have the same hash
  bounds       every named element lies inside the frame, and captions inside the caption band
  band         no scene element enters the caption band: at sampled times the scene alone (layers
               no-band) and the bare background are compared over the band's pixels, and every
               named element's box is checked against the band
  contrast     the brightest pixel under the caption band, against the caption colour, is at least 4.5:1
  overlap      no two text elements cover each other (more than 30% of the smaller one's box) at a sample
  grid, palette  pixel videos only (see pixel.py): the canvas is whole k×k blocks, in the palette
  filler, cuts, levels, sync, segments  footage videos only (see footage.py)

Sample times are spread across each clip's sentences, `--samples` per clip (moments.check_samples).

Incremental by default: the per-chapter checks (length, determinism, bounds, band, contrast,
legible) re-run only for chapters whose clip key changed since they last passed there; a pass is
remembered per chapter, check and format in .cache/check/. Video-wide checks always run. `--all`
checks every chapter, and `studio publish` always runs the full check as its gate.
"""
import hashlib
import json
import tempfile
import shutil
import struct
import uuid
from pathlib import Path

from . import moments
from . import proc
from . import settings
from . import timeline as tl
from .engine import Engine

CAPTION_COLOUR = (0xE6, 0xEB, 0xF0)      # theme.ts INK
MIN_CONTRAST = 4.5
SIDE_MARGIN = 80                         # px kept free either side of a caption line
SLACK = 1.0                              # px of tolerance on box edges


PER_CLIP = ("length", "determinism", "bounds", "band", "contrast", "legible", "overlap")
OVERLAP = 0.3                            # share of the smaller text box another text box may cover


def sample_times(t, per_clip, clips=None):
    """[{clip, t}]: the moments the per-chapter checks look at (moments.check_samples)."""
    return moments.requests(moments.check_samples(t, per_clip, clips))


def length(video, engine=None, clips=None):
    engine, t = engine or Engine(video), tl.load(video)
    rows = []
    scenes = [c for c in t["tracks"]["scene"] if clips is None or c["id"] in clips]
    if not scenes:
        return rows
    got_all = engine.durations([c["id"] for c in scenes])
    for c in scenes:
        want = tl.frames(t, c["id"])[1]
        got = got_all[c["id"]]
        rows.append({"check": "length", "clip": c["id"], "ok": got == want, "detail": f"engine {got} frames, timeline {want}"})
    return rows


def determinism(video, samples=3, engine=None, clips=None):
    """Render `samples` frames per clip twice, in separate engine calls, and compare their hashes.
    A frame that differs means some state leaks between frames (a timer, unseeded randomness)."""
    engine, t = engine or Engine(video), tl.load(video)
    reqs = moments.requests(moments.even(t, samples, clips))
    if not reqs:
        return []
    def pixels(path):
        data = Path(path).read_bytes()
        dimensions = struct.unpack(">II", data[16:24])
        raw = proc.ffmpeg("-i", path, "-f", "rawvideo", "-pix_fmt", "rgba", "-", capture_output=True).stdout
        return digest(struct.pack(">II", *dimensions) + raw), digest(data), raw

    digest = lambda data: hashlib.sha256(data).hexdigest()
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        def pair(requests, tag):
            runs = []
            for run in ("a", "b"):
                batch = [{**r, "out": str(Path(tmp) / f"{tag}-{run}-{r['clip']}-{r['t']}.png")} for r in requests]
                engine.stills(batch)
                runs.append([(r["out"], *pixels(r["out"])) for r in batch])
            return list(zip(*runs))
        first = pair(reqs, "first")
        failed = [i for i, (a, b) in enumerate(first) if a[1] != b[1]]
        retry = dict(zip(failed, pair([reqs[i] for i in failed], "retry"))) if failed else {}
        evidence = Path(video) / "research" / "determinism" / uuid.uuid4().hex[:12]
        for i, (r, (a, b)) in enumerate(zip(reqs, first)):
            same = a[1] == b[1]
            detail = f"pixels {a[1]} {b[1]}; png {a[2]} {b[2]}"
            if not same:
                evidence.mkdir(parents=True, exist_ok=True)
                c, d = retry[i]
                for item in (a, b, c, d):
                    shutil.copyfile(item[0], evidence / Path(item[0]).name)
                differences = sum(a[3][j:j+4] != b[3][j:j+4] for j in range(0, min(len(a[3]), len(b[3])), 4))
                detail += f"; retry {c[1]} {d[1]}; {'FLAKY' if c[1] == d[1] else 'REPEATED'}; differing pixels {differences}; evidence {evidence}"
            rows.append({"check": "determinism", "clip": r["clip"], "t": r["t"], "ok": same, "detail": detail})
        if failed:
            (evidence / "results.json").write_text(json.dumps({"engine": getattr(engine, "name", "test"),
                "browser": getattr(engine, "browser", None), "rows": rows}, indent=1) + "\n")
    return rows


def _boxes(video, per_clip, engine, clips=None):
    times = sample_times(tl.load(video), per_clip, clips)
    return engine.layout(), (engine.boxes_at(times) if times else [])


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


def overlap(video, samples=3, engine=None, boxes=None):
    """Two different text elements on top of each other: one label hides the other. Text inside a
    shape is fine (only text boxes are compared); captions are left to the band checks."""
    engine = engine or Engine(video)
    _, frames = boxes or _boxes(video, samples, engine)
    rows = []
    for f in frames:
        texts = [b for b in f["boxes"] if b.get("kind") == "text" and b["name"] != "caption" and b["w"] > 2 and b["h"] > 2]
        bad = []
        for i, a in enumerate(texts):
            for b in texts[i + 1:]:
                if a["name"] == b["name"]:
                    continue
                w = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
                h = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
                if w > 0 and h > 0 and w * h > OVERLAP * min(a["w"] * a["h"], b["w"] * b["h"]):
                    bad.append(f"{a['name'][:24]!r} and {b['name'][:24]!r} overlap")
        rows.append({"check": "overlap", "clip": f["clip"], "t": f["t"], "ok": not bad, "detail": "; ".join(bad[:4])})
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
    return proc.ffmpeg("-i", png, "-vf", f"crop={lay['width']}:{h}:0:{lay['height'] - h}",
                       "-f", "rawvideo", "-pix_fmt", "rgb24", "-", capture_output=True).stdout


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


def band_pixels_check(video, samples=3, engine=None, clips=None):
    """The scene alone against the bare background, over the band's pixels: any difference is
    scene content in the band. Then the caption contrast against what is under the band."""
    engine = engine or Engine(video)
    t, lay = tl.load(video), engine.layout()
    times = sample_times(t, samples, clips)
    rows = []
    if not times:
        return rows
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
MORE = "legible (text at least 18 px tall), overlap (no text on top of other text), provenance (assets used are recorded), dead and loop (motion)"


def config(video):
    return settings.load(video)


def genre(video):
    return config(video).get("genre", "explainer")


def _cache_file(video, fmt, samples):
    return Path(video) / ".cache" / "check" / f"{(fmt or '16:9').replace(':', 'x')}-s{samples}.json"


def changed_clips(video, kinds, samples=3, fmt=None):
    """({clip: key}, {clip ids whose key changed for any of `kinds` since it last passed})."""
    from . import render
    t = tl.load(video)
    keys = {c["id"]: render.clip_key(video, t, c["id"], "check", fmt=fmt) for c in t["tracks"]["scene"]}
    f = _cache_file(video, fmt, samples)
    passed = json.loads(f.read_text()) if f.exists() else {}
    todo = {cid for cid, k in keys.items() if any(passed.get(cid, {}).get(kind) != k for kind in kinds)}
    return keys, todo


def remember(video, rows, keys, kinds, samples=3, fmt=None):
    """Record a pass for each (clip, kind) that ran in `rows` with no failure."""
    f = _cache_file(video, fmt, samples)
    passed = json.loads(f.read_text()) if f.exists() else {}
    ran, failed = set(), set()
    for r in rows:
        if r["check"] in kinds and r.get("clip") in keys:
            ran.add((r["clip"], r["check"]))
            if not r["ok"]:
                failed.add((r["clip"], r["check"]))
    for cid, kind in ran - failed:
        passed.setdefault(cid, {})[kind] = keys[cid]
    for cid, kind in failed:
        passed.get(cid, {}).pop(kind, None)
    passed = {cid: v for cid, v in passed.items() if cid in keys}
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(passed, indent=1, sort_keys=True))


def run(video, samples=3, only=None, engine=None, fmt=None, everything=True):
    """The checks. With everything=False, the per-chapter checks run only on chapters whose clip
    key changed since they last passed (see changed_clips); a pass is remembered either way."""
    default = only is None
    extra = {"pixel": ("grid", "palette"), "footage": ("filler", "cuts", "levels", "sync", "segments"),
             "motion": ("dead",), "launch": ()}.get(genre(video), ())
    always = ("legible", "overlap") + (("provenance",) if (Path(video) / "assets" / "provenance.json").exists() else ())
    only = set(only or CHECKS + extra + always)
    known = set(CHECKS) | {"legible", "overlap", "provenance", "dead", "loop", "grid", "palette", "filler", "cuts", "levels", "sync", "segments", "script", "code-source"}
    if only - known:
        raise SystemExit("unknown checks: " + ", ".join(sorted(only - known)))
    preflight = []
    if "script" in only or (default and config(video).get("teaching_contract")):
        from . import script_check
        preflight += script_check.run(video)
    if "code-source" in only or (default and (Path(video) / "data" / "steps" / "index.json").exists()):
        from . import steps
        preflight += steps.check(video)
    if only <= {"script", "code-source"}:
        return preflight
    engine = engine or Engine(video, fmt=fmt)
    kinds = sorted(only & set(PER_CLIP))
    keys, todo = changed_clips(video, kinds, samples, fmt)
    clips = None if everything else todo
    if not everything:
        skipped = sorted(set(keys) - todo, key=lambda c: list(keys).index(c))
        print(f"check: {len(todo)} chapter(s) changed since their last pass"
              + (f"; skipping {', '.join(skipped)} (unchanged, passed before)" if skipped else "")
              + " (--all checks every chapter)", flush=True)
    rows = preflight
    if "length" in only:
        rows += length(video, engine, clips)
    if "determinism" in only:
        rows += determinism(video, samples, engine, clips)
    if only & {"bounds", "band", "legible", "overlap"}:
        boxes = _boxes(video, samples, engine, clips)
        if "overlap" in only:
            rows += overlap(video, samples, engine, boxes)
        if "legible" in only:
            from . import motion
            rows += motion.legible(video, samples, engine, boxes)
        if "bounds" in only:
            rows += bounds(video, samples, engine, boxes)
        if "band" in only:
            rows += band_guard(video, samples, engine, boxes)
    if only & {"band", "contrast"}:
        pix = band_pixels_check(video, samples, engine, clips)
        rows += [r for r in pix if r["check"] in only]
    if genre(video) == "footage" and only & {"filler", "cuts", "levels", "sync", "segments"}:
        from . import footage
        rows += [r for r in footage.checks(video) if r["check"] in only]
    if "dead" in only:
        from . import motion
        rows += motion.dead_beats(video, engine=engine)
    if "loop" in only or (default and config(video).get("loop")):
        from . import motion
        rows += motion.loop_seam(video, engine)
    if "provenance" in only:
        from . import motion
        rows += motion.provenance(video)
    if only & {"grid", "palette"}:
        from . import pixel
        rows += [r for r in pixel.run(video, samples, engine) if r["check"] in only]
    remember(video, rows, keys, kinds, samples, fmt)
    return rows


def main(args):
    if (Path(args.video) / "timeline.json").exists():      # a script check runs before there is one
        tl.build(args.video)                               # as a cut does, so the checks see the sources
    rows = run(args.video, args.samples, args.only.split(",") if args.only else None, fmt=args.format,
               everything=getattr(args, "all", False))
    for r in rows:
        where = f"{r['clip']}" + (f" t={r['t']}" if "t" in r else "")
        print(f"{'WARN' if r.get('severity') == 'warning' else 'ok  ' if r['ok'] else 'FAIL'}  {r['check']:11} {where:16} {r['detail']}".rstrip())
    by = {}
    for r in rows:
        by.setdefault(r["check"], [0, 0])[0 if r["ok"] else 1] += 1
    print("; ".join(f"{k}: {v[0]} ok" + (f", {v[1]} FAILED" if v[1] else "") for k, v in by.items()))
    return 1 if any(not r["ok"] for r in rows) else 0
