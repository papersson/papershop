"""Plates: frames another renderer (Blender) draws behind a live chapter, for the few shots that need it.

A hard-drive film rendered in Blender outside the studio needed about fifty scripts of its own (a
desk, cut records, review bundles, a publish), and its labels, drawn in Blender, were out of every
check's reach. So Blender draws only the plate, the picture behind a chapter, and the chapter stays
a live scene: it draws the plate as its background (`c.plate()`), puts its labels on the points the
plate reports (`c.plate.at('head')`), and keeps the caption band, the checks, the desk, the reviews
and publish. Use it for physical, realistic hero shots (references/taste/look.md); diagrams, code
and most chapters stay flat or on the 3D stage.

video.json names the chapters that have one:

  "plates": {"s3": {"script": "sims/drive_scene.py",            build(scene, ctx) and pose(scene, t, ctx)
                    "inputs": ["sims/drive/*.py", "assets/models/*.blend"],   what else its pixels depend on
                    "project": ["head", "platter"],                objects whose screen points it reports
                    "draft": {"samples": 16}, "final": {"samples": 64}}}

(or "renderer": "command" with "command": [argv…, "{request}"], for a renderer of your own that
reads the same request and writes the same files). Frames are rendered at the stage's size above
the caption band, half that for a draft, into .cache/plates/<clip>-<quality>-<key>/: f00012.png per
frame and frames.jsonl (a line per frame: its render seconds and the projected points). The key
hashes the script, its inputs, the profile, the size and the clip's cues, so an edit renders again
and nothing else does. Rendering goes in batches, so a stopped render resumes where it stopped, and
`studio plate VIDEO CLIP --probe` renders a few frames spread over the clip to say how long the rest
will take before it starts. The engine renders a plate's missing frames itself, before a still, a
check or a cut needs them (engine.Engine), and writes .cache/plates/index.json, which tells the
live scene which plate to draw.
"""
import hashlib
import json
import os
import shutil
import statistics
import time
from pathlib import Path

from . import proc, settings
from . import timeline as tl
from .env import engine_dir

QUALITY = {"draft": {"scale": 0.5, "samples": 16}, "final": {"scale": 1.0, "samples": 64}}
BATCH = 120             # frames a renderer call: what a stopped render loses at most
PLATE_VERSION = 1


def config(video):
    """{clip: spec} from video.json `plates` (empty when the video has none)."""
    try:
        return settings.raw(video).get("plates") or {}
    except (SystemExit, FileNotFoundError, ValueError):
        return {}


def blender():
    """The Blender to render with: STUDIO_BLENDER, else `blender` on PATH, else the macOS app."""
    for c in (os.environ.get("STUDIO_BLENDER"), shutil.which("blender"), "/Applications/Blender.app/Contents/MacOS/Blender"):
        if c and Path(c).is_file():
            return c
    return None


def profile(spec, quality):
    return {**QUALITY["final" if quality == "final" else "draft"], **spec.get("final" if quality == "final" else "draft", {})}


def size(video, spec, quality):
    """(width, height) a plate's frames render at: the stage above the band, scaled by the profile."""
    lay = tl.layout(video)
    k = profile(spec, quality)["scale"]
    even = lambda n: max(2, int(round(n * k / 2)) * 2)          # noqa: E731
    return even(lay["width"]), even(tl.band_top(lay))


def _files(video, spec):
    video = Path(video)
    out = [video / spec["script"]] if spec.get("script") else []
    for pattern in spec.get("inputs", []):
        out += sorted(p for p in video.glob(pattern) if p.is_file())
    return out


def key(video, timeline, clip, quality):
    """What a plate's frames depend on: the renderer and its adapter, the scene script and inputs,
    the profile and size, the clip's frames and its cues (in clip seconds)."""
    spec = config(video)[clip]
    h = hashlib.sha256(json.dumps([PLATE_VERSION, spec, profile(spec, quality), size(video, spec, quality)], sort_keys=True).encode())
    if spec.get("renderer", "blender") == "blender":
        h.update((engine_dir("blender") / "plate.py").read_bytes())
        b = blender()
        h.update(f"{b}:{Path(b).stat().st_size}".encode() if b else b"no blender")
    for f in _files(video, spec):
        h.update(str(f.relative_to(video)).encode())
        h.update(f.read_bytes())
    c = tl.clip(timeline, clip)
    first, count = tl.frames(timeline, clip)
    h.update(json.dumps({"fps": timeline["fps"], "frames": count,
                         "cues": {k: round(v - first / timeline["fps"], 4) for k, v in timeline.get("cues", {}).items()},
                         "duration": round(c["end"] - c["start"], 4)}, sort_keys=True).encode())
    return h.hexdigest()[:16]


def store(video, clip, quality, k):
    return Path(video) / ".cache" / "plates" / f"{clip}-{quality}-{k}"


def frame_file(d, f):
    return d / f"f{f:05d}.png"


def _command(video, spec, request):
    if spec.get("renderer", "blender") == "blender":
        b = blender()
        if not b:
            raise SystemExit("a plate renders in Blender, which isn't installed: `brew install --cask blender` "
                             "(or set STUDIO_BLENDER to its binary); `studio doctor` checks it")
        return [b, "--background", "--factory-startup", "--python", str(engine_dir("blender") / "plate.py"), "--", "--request", str(request)]
    if spec.get("renderer") == "command":
        return [str(a).replace("{request}", str(request)) for a in spec["command"]]
    raise SystemExit(f"plates: unknown renderer {spec.get('renderer')!r} (blender or command)")


def seconds_per_frame(d):
    """The median render seconds a frame took in this store, or None before any."""
    log = d / "frames.jsonl"
    took = [json.loads(line)["seconds"] for line in log.read_text().splitlines() if line.strip()] if log.exists() else []
    return statistics.median(took) if took else None


def render(video, timeline, clip, quality, frames, progress=print):
    """Render the frames of `frames` the store lacks, in batches; returns the store."""
    video = Path(video)
    spec = config(video)[clip]
    k = key(video, timeline, clip, quality)
    d = store(video, clip, quality, k)
    todo = [f for f in sorted(set(frames)) if not frame_file(d, f).exists()]
    if not todo:
        return d
    d.mkdir(parents=True, exist_ok=True)
    w, h = size(video, spec, quality)
    first, count = tl.frames(timeline, clip)
    t0 = first / timeline["fps"]
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        per = seconds_per_frame(d)
        progress(f"plate {clip} ({quality}): frames {batch[0]}-{batch[-1]} of {count}, {len(todo) - i} to go"
                 + (f", about {(len(todo) - i) * per / 60:.0f} min at {per:.1f} s a frame" if per else ""))
        req = {"video": str(video), "clip": clip, "script": str(video / spec["script"]), "frames": batch,
               "fps": timeline["fps"], "width": w, "height": h, "duration": count / timeline["fps"],
               "profile": profile(spec, quality), "project": spec.get("project", []), "out": str(d),
               "cues": {name: round(v - t0, 4) for name, v in timeline.get("cues", {}).items()}}
        request = d / "request.json"
        request.write_text(json.dumps(req, indent=1))
        run = proc.run(_command(video, spec, request), capture_output=True, text=True, cwd=video)
        missing = [f for f in batch if not frame_file(d, f).exists()]
        if run.returncode != 0 or missing:
            cause = (run.stderr or run.stdout).strip()[-2000:]
            raise SystemExit(f"plate {clip}: the renderer {'failed' if run.returncode else 'left frames out'}"
                             + (f" ({len(missing)} missing)" if missing else "") + f":\n{cause}")
    return d


def ensure(video, timeline, quality, need=None, progress=print):
    """Every plated clip's frames for `quality` (or just `need`: {clip: frames}), rendered where
    missing, and .cache/plates/index.json naming the store each clip draws from."""
    video = Path(video)
    cfg = config(video)
    ids = {c["id"] for c in timeline["tracks"]["scene"]}
    index = {}
    for clip, spec in cfg.items():
        if clip not in ids:
            continue
        frames = range(tl.frames(timeline, clip)[1]) if need is None else need.get(clip, [])
        d = render(video, timeline, clip, quality, frames, progress) if frames else store(video, clip, quality, key(video, timeline, clip, quality))
        w, h = size(video, spec, quality)
        index[clip] = {"dir": str(d.relative_to(video)), "quality": quality, "width": w, "height": h}
    if cfg:
        f = video / ".cache" / "plates" / "index.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(index, indent=1))
    return index


def probe(video, timeline, clip, quality, n=6, progress=print):
    """Render n frames spread over the clip (the store keeps them) and say how long the whole would take."""
    count = tl.frames(timeline, clip)[1]
    frames = sorted({min(count - 1, round(i * (count - 1) / max(1, n - 1))) for i in range(n)})
    started = time.monotonic()
    d = render(video, timeline, clip, quality, frames, progress)
    per = seconds_per_frame(d) or (time.monotonic() - started) / max(1, len(frames))
    total = per * count
    progress(f"plate {clip} ({quality}): {per:.1f} s a frame over {len(frames)} probe frames; all {count} frames about "
             f"{total / 60:.0f} min (the slowest probe frame took {_slowest(d):.1f} s)")
    return {"per_frame": round(per, 2), "frames": count, "seconds": round(total, 1)}


def _slowest(d):
    log = d / "frames.jsonl"
    return max((json.loads(line)["seconds"] for line in log.read_text().splitlines() if line.strip()), default=0.0)


def main(args):
    video = Path(args.video)
    t = tl.build(video, quiet=True)
    cfg = config(video)
    clips = args.clips or list(cfg)
    unknown = [c for c in clips if c not in cfg]
    if unknown:
        raise SystemExit(f"video.json plates names no {', '.join(unknown)} (it has {', '.join(cfg) or 'none'})")
    for clip in clips:
        if args.probe:
            probe(video, t, clip, args.quality, args.probe)
        else:
            render(video, t, clip, args.quality, range(tl.frames(t, clip)[1]))
    ensure(video, t, args.quality, need={})
    return 0

