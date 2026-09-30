"""Cuts: render what changed, composite, and write what the review page shows.

A clip's cache key hashes everything its frames depend on: the engine, the video's shared scene
files, the clip's own scene file (scenes/<clip>.tsx), its slice of the timeline and the layout.
So an edit to one chapter's scene re-renders that chapter only, and an edit to a shared file
re-renders them all.

videos/<name>/cuts/cutN/
  video.mp4      the composite with narration (draft: 540p)
  stills/        one frame per sentence, near its end
  cut.json       what was rendered, how long each step took, and the changelog against cut N-1
"""
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

from . import audio
from . import timeline as tl
from .engine import Engine
from .env import engine_dir

STILL_SCALE = 0.25          # 480×270 stills on the page
STILL_BEFORE_END = 0.15     # seconds before a sentence's end, when its picture is complete


def _hash_tree(h, p, root=None):
    """Hash file names relative to `p` and contents, so a moved or copied video keeps its keys."""
    p = Path(p)
    root = root or (p if p.is_dir() else p.parent)
    if p.is_dir():
        for child in sorted(p.iterdir()):
            if child.name != "node_modules" and not child.name.startswith("."):
                _hash_tree(h, child, root)
    elif p.exists():
        h.update(str(p.relative_to(root)).encode())
        h.update(p.read_bytes())


def _engine_of(video):
    f = Path(video) / "video.json"
    return json.loads(f.read_text()).get("engine", "remotion") if f.exists() else "remotion"


def _hash_listing(h, p):
    p = Path(p)
    if p.is_dir():
        for f in sorted(p.rglob("*")):
            if f.is_file():
                st = f.stat()
                h.update(f"{f.relative_to(p)}:{st.st_size}:{int(st.st_mtime)}".encode())


def clip_key(video, timeline, clip_id, quality, engine=None, fmt=None):
    engine = engine or _engine_of(video)
    video = Path(video)
    clip_ids = {c["id"] for c in timeline["tracks"]["scene"]}
    h = hashlib.sha1(quality.encode())
    _hash_tree(h, engine_dir(engine) / "src")
    _hash_tree(h, engine_dir(engine) / "package-lock.json")
    for f in sorted((video / "scenes").iterdir()):
        if f.stem == clip_id or f.stem not in clip_ids:
            _hash_tree(h, f)
    _hash_tree(h, video / "data")       # scenes import their numbers from data/
    _hash_listing(h, video / "assets")  # assets: names, sizes and times (footage is too big to read)
    c = tl.clip(timeline, clip_id)
    part = {
        "clip": c, "frames": tl.frames(timeline, clip_id), "fps": timeline["fps"],
        "narration": [s for s in timeline["tracks"]["narration"] if s["clip"] == clip_id],
        "captions": [x for x in timeline["tracks"]["captions"] if x["end"] > c["start"] and x["start"] < c["end"]],
        "cues": timeline.get("cues", {}),
        "footage": timeline["tracks"].get("footage", []),
        "beats": timeline.get("beats", {}),
        "layout": tl.layout(video, fmt),
    }
    h.update(json.dumps(part, sort_keys=True).encode())
    return h.hexdigest()[:16]


def cuts_dir(video):
    return Path(video) / "cuts"


def latest_cut(video):
    """The highest cut number with a cut.json, or 0."""
    nums = [int(p.name[3:]) for p in cuts_dir(video).glob("cut*") if (p / "cut.json").exists() and p.name[3:].isdigit()]
    return max(nums, default=0)


def read_cut(video, n):
    p = cuts_dir(video) / f"cut{n}" / "cut.json"
    return json.loads(p.read_text()) if p.exists() else None


def plan(video, timeline, quality, fmt=None):
    """[(clip id, key, cached file or None)] for every clip in order."""
    cache = Path(video) / ".cache" / "clips"
    rows = []
    for c in timeline["tracks"]["scene"]:
        key = clip_key(video, timeline, c["id"], quality, c.get("engine") or _engine_of(video), fmt)
        f = cache / f"{c['id']}-{quality}-{key}.mp4"
        rows.append((c["id"], key, f if f.exists() else None))
    return rows


def _ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)], check=True)


def composite(video, timeline, clip_files, out):
    """Concatenate the clips' videos (identical encodes, so no re-encode) and mux the mixed soundtrack."""
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{f.resolve()}'\n" for f in clip_files))
    silent = out.with_name("silent.mp4")
    _ffmpeg("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent)
    sound = out.with_name("sound.m4a")
    audio.mix(video, timeline, sound)
    _ffmpeg("-i", silent, "-i", sound, "-map", "0:v", "-map", "1:a", "-c", "copy", "-t", f"{timeline['duration']:.3f}",
            "-movflags", "+faststart", out)
    for f in (lst, silent, sound):
        f.unlink()


NO_NARRATION_STEP = 1.5          # seconds between stills of a clip that has no narration


def still_requests(timeline, outdir, clips=None):
    """One still near the end of every sentence, and, for a clip with no narration (a motion piece,
    a product film), one every NO_NARRATION_STEP seconds, so the review page always has frames to browse."""
    reqs = []
    for s in timeline["tracks"]["narration"]:
        if clips and s["clip"] not in clips:
            continue
        c = tl.clip(timeline, s["clip"])
        t = max(s["start"], s["end"] - STILL_BEFORE_END) - c["start"]
        reqs.append({"id": s["id"], "clip": s["clip"], "t": round(t, 3), "out": str(outdir / f"{s['id']}.jpg"),
                     "scale": STILL_SCALE, "caption": s["caption"], "at": round(s["start"], 3)})
    narrated = {s["clip"] for s in timeline["tracks"]["narration"]}
    for c in timeline["tracks"]["scene"]:
        if c["id"] in narrated or (clips and c["id"] not in clips):
            continue
        dur = c["end"] - c["start"]
        for i in range(max(3, int(dur / NO_NARRATION_STEP))):
            local = min(dur - 1 / timeline["fps"], (i + 0.5) * dur / max(3, int(dur / NO_NARRATION_STEP)))
            sid = f"{c['id']}_t{i + 1:02d}"
            reqs.append({"id": sid, "clip": c["id"], "t": round(local, 3), "out": str(outdir / f"{sid}.jpg"),
                         "scale": STILL_SCALE, "caption": f"{c['start'] + local:.1f} s", "at": round(c["start"] + local, 3)})
    return reqs


def make_cut(video, quality="draft", stills_only=False, changelog=None, engine=None):
    """Render cut N+1: stills first (the fastest answer), then only the clips whose key changed,
    then the composite. Returns the cut record."""
    video = Path(video).resolve()
    timeline = tl.load(video)
    engine = engine or Engine(video)
    prev_n = latest_cut(video)
    prev = read_cut(video, prev_n) if prev_n else None
    n = prev_n + 1
    d = cuts_dir(video) / f"cut{n}"
    if d.exists():
        shutil.rmtree(d)
    (d / "stills").mkdir(parents=True)
    timings = {}

    rows = plan(video, timeline, quality)
    prev_keys = {c["id"]: c["key"] for c in prev["clips"]} if prev else {}
    changed = [cid for cid, key, _ in rows if prev_keys.get(cid) != key]

    t0 = time.monotonic()
    reqs = still_requests(timeline, d / "stills")
    engine.stills([{k: r[k] for k in ("clip", "t", "out", "scale")} for r in reqs])
    timings["stills"] = round(time.monotonic() - t0, 1)

    clips = []
    if not stills_only:
        files, clips = render_clips(video, timeline, engine, quality)
        t1 = time.monotonic()
        composite(video, timeline, files, d / "video.mp4")
        timings["composite"] = round(time.monotonic() - t1, 1)
    else:
        clips = [{"id": cid, "key": key, "rendered": False, "seconds": 0} for cid, key, _ in rows]

    record = {
        "cut": n, "created": time.strftime("%Y-%m-%d %H:%M:%S"), "quality": quality,
        "video": None if stills_only else "video.mp4", "duration": timeline["duration"],
        "chapters": [{"id": c["id"], "title": c["title"], "start": c["start"]} for c in timeline["tracks"]["scene"]],
        "clips": clips, "changed": changed if prev else [],
        "stills": [{k: r[k] for k in ("id", "clip", "caption", "at")} | {"file": f"stills/{r['id']}.jpg"} for r in reqs],
        "changelog": changelog or [],
        "seconds": timings,
    }
    if prev:
        _keep_befores(video, prev_n, d, record)
    (d / "cut.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    return record


def _keep_befores(video, prev_n, d, record):
    """Copy the previous cut's stills that changed, so the page can show before and after."""
    before = d / "before"
    for s in record["stills"]:
        if s["clip"] in record["changed"]:
            src = cuts_dir(video) / f"cut{prev_n}" / s["file"]
            if src.exists() and src.read_bytes() != (d / s["file"]).read_bytes():
                before.mkdir(exist_ok=True)
                shutil.copyfile(src, before / src.name)
                s["before"] = f"before/{src.name}"


def render_clips(video, timeline, engine, quality="draft", fmt=None):
    """Render the clips whose cached video is missing (or stale) in `fmt`; returns ([files], [records])."""
    cache = Path(video) / ".cache" / "clips"
    cache.mkdir(parents=True, exist_ok=True)
    tag = f"-{fmt.replace(':', 'x')}" if fmt and fmt != "16:9" else ""
    files, records = [], []
    for cid, key, cached in plan(video, timeline, quality, fmt):
        f = cache / f"{cid}-{quality}{tag}-{key}.mp4"
        started = time.monotonic()
        if not f.exists():
            for old in cache.glob(f"{cid}-{quality}{tag}-*.mp4"):
                old.unlink()
            engine.render(cid, f, quality)
        records.append({"id": cid, "key": key, "rendered": cached is None, "seconds": round(time.monotonic() - started, 1)})
        files.append(f)
    return files, records


def export_formats(video, formats, quality="final", lufs=None, name=None):
    """The whole video in each format, final quality by default, into out/export/. Every format comes
    from the same timeline and scenes; each has its own stage and caption band."""
    video = Path(video).resolve()
    timeline = tl.load(video)
    if lufs is not None:
        audio.finish(video, lufs)
    out = video / "out" / "export"
    out.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((video / "video.json").read_text()) if (video / "video.json").exists() else {}
    slug = name or "".join(c if c.isalnum() else "-" for c in cfg.get("title", video.name).lower()).strip("-")
    made = []
    for fmt in formats:
        lay = tl.layout(video, fmt)
        files, _ = render_clips(video, timeline, Engine(video, fmt=fmt), quality, fmt)
        target = out / f"{slug}_{fmt.replace(':', 'x')}.mp4"
        composite(video, timeline, files, target)
        made.append({"format": fmt, "file": str(target), "size": [lay["width"], lay["height"]]})
    return made


def main_export(args):
    made = export_formats(args.video, args.formats.split(","), args.quality, args.lufs)
    for m in made:
        print(f"{m['format']:5} {m['size'][0]}x{m['size'][1]}  {m['file']}")
    return 0
