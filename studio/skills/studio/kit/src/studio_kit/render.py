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

from . import timeline as tl
from .engine import Engine
from .env import engine_dir

STILL_SCALE = 0.25          # 480×270 stills on the page
STILL_BEFORE_END = 0.15     # seconds before a sentence's end, when its picture is complete


def _hash_tree(h, p):
    p = Path(p)
    if p.is_dir():
        for child in sorted(p.iterdir()):
            if child.name != "node_modules" and not child.name.startswith("."):
                _hash_tree(h, child)
    elif p.exists():
        h.update(str(p).encode())
        h.update(p.read_bytes())


def clip_key(video, timeline, clip_id, quality, engine="remotion"):
    video = Path(video)
    clip_ids = {c["id"] for c in timeline["tracks"]["scene"]}
    h = hashlib.sha1(quality.encode())
    _hash_tree(h, engine_dir(engine) / "src")
    _hash_tree(h, engine_dir(engine) / "package-lock.json")
    for f in sorted((video / "scenes").iterdir()):
        if f.stem == clip_id or f.stem not in clip_ids:
            _hash_tree(h, f)
    c = tl.clip(timeline, clip_id)
    part = {
        "clip": c, "frames": tl.frames(timeline, clip_id), "fps": timeline["fps"],
        "narration": [s for s in timeline["tracks"]["narration"] if s["clip"] == clip_id],
        "captions": [x for x in timeline["tracks"]["captions"] if x["end"] > c["start"] and x["start"] < c["end"]],
        "cues": timeline.get("cues", {}),
        "layout": tl.layout(video),
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


def plan(video, timeline, quality):
    """[(clip id, key, cached file or None)] for every clip in order."""
    cache = Path(video) / ".cache" / "clips"
    rows = []
    for c in timeline["tracks"]["scene"]:
        key = clip_key(video, timeline, c["id"], quality, c.get("engine", "remotion"))
        f = cache / f"{c['id']}-{quality}-{key}.mp4"
        rows.append((c["id"], key, f if f.exists() else None))
    return rows


def _ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)], check=True)


def composite(video, timeline, clip_files, out):
    """Concatenate the clips' videos (identical encodes, so no re-encode) and mux the narration."""
    video = Path(video)
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{f.resolve()}'\n" for f in clip_files))
    silent = out.with_name("silent.mp4")
    _ffmpeg("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent)
    audio = video / timeline["tracks"]["audio"][0]["file"]
    _ffmpeg("-i", silent, "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
            "-b:a", "160k", "-t", f"{timeline['duration']:.3f}", "-movflags", "+faststart", out)
    lst.unlink()
    silent.unlink()


def still_requests(timeline, outdir, clips=None):
    reqs = []
    for s in timeline["tracks"]["narration"]:
        if clips and s["clip"] not in clips:
            continue
        c = tl.clip(timeline, s["clip"])
        t = max(s["start"], s["end"] - STILL_BEFORE_END) - c["start"]
        reqs.append({"id": s["id"], "clip": s["clip"], "t": round(t, 3), "out": str(outdir / f"{s['id']}.jpg"),
                     "scale": STILL_SCALE, "caption": s["caption"], "at": round(s["start"], 3)})
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
        cache = video / ".cache" / "clips"
        cache.mkdir(parents=True, exist_ok=True)
        files = []
        for cid, key, cached in rows:
            f = cache / f"{cid}-{quality}-{key}.mp4"
            started = time.monotonic()
            if cached is None:
                for old in cache.glob(f"{cid}-{quality}-*.mp4"):
                    old.unlink()
                engine.render(cid, f, quality)
            clips.append({"id": cid, "key": key, "rendered": cached is None,
                          "seconds": round(time.monotonic() - started, 1)})
            files.append(f)
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
    """Copy the previous cut's stills for changed clips, so the page can show before and after."""
    before = d / "before"
    for s in record["stills"]:
        if s["clip"] in record["changed"]:
            src = cuts_dir(video) / f"cut{prev_n}" / s["file"]
            if src.exists():
                before.mkdir(exist_ok=True)
                shutil.copyfile(src, before / src.name)
                s["before"] = f"before/{src.name}"
