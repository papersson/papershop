"""Cuts: render what changed, composite, and write what the review page shows.

A clip's cache key hashes everything its frames depend on: the engine, the video's shared scene
files, the clip's own scene file (scenes/<clip>.tsx), its slice of the timeline (as times relative
to the clip's first frame) and the layout. So an edit to one chapter's scene re-renders that
chapter only, a narration edit re-renders the chapter it is in (later chapters move by whole frames,
see narration.CHAPTER_GRID, and keep their keys), and an edit to a shared file re-renders them all.

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

from . import settings
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
    return settings.load(video)["engine"]


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
    scenes = sorted((video / "scenes").iterdir()) if (video / "scenes").is_dir() else []
    for f in scenes:
        if f.stem == clip_id or f.stem not in clip_ids:
            _hash_tree(h, f)
    if quality == "boards" or not any(f.stem == clip_id for f in scenes):
        _hash_tree(h, video / "boards")  # the chapter renders its board
    _hash_tree(h, video / "data")       # scenes import their numbers from data/
    _hash_listing(h, video / "assets")  # assets: names, sizes and times (footage is too big to read)
    c = tl.clip(timeline, clip_id)
    first, count = tl.frames(timeline, clip_id)
    t0 = first / timeline["fps"]
    rel = lambda x: round(x - t0, 4)   # the clip's frames depend on times relative to its first frame only
    part = {
        "clip": {**c, "start": rel(c["start"]), "end": rel(c["end"])}, "frames": count, "fps": timeline["fps"],
        "narration": [{**s, "start": rel(s["start"]), "end": rel(s["end"]),
                       "pause": {**s["pause"], "start": rel(s["pause"]["start"]), "end": rel(s["pause"]["end"])} if "pause" in s else None,
                       "words": [{**w, "start": rel(w["start"]), "end": rel(w["end"])} for w in s.get("words", [])]}
                      for s in timeline["tracks"]["narration"] if s["clip"] == clip_id],
        "captions": [{**x, "start": rel(x["start"]), "end": rel(x["end"])}
                     for x in timeline["tracks"]["captions"] if x["end"] > c["start"] and x["start"] < c["end"]],
        "cues": {k: rel(v) for k, v in timeline.get("cues", {}).items()
                 if not k.startswith("reveal:") or k.startswith(f"reveal:{clip_id}_")},
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


def mixed_sound(video, timeline):
    """The mixed soundtrack, cached under .cache/sound/ by its inputs (the audio track entries, each
    file's size and time, and the duration), so a cut that changed only pictures doesn't re-mix it."""
    video = Path(video)
    h = hashlib.sha1(json.dumps([timeline["tracks"]["audio"], timeline["duration"]], sort_keys=True).encode())
    for e in timeline["tracks"]["audio"]:
        f = audio.pick(video, e["file"])
        if f.exists():
            st = f.stat()
            h.update(f"{f.name}:{st.st_size}:{st.st_mtime_ns}".encode())
    cache = video / ".cache" / "sound"
    cache.mkdir(parents=True, exist_ok=True)
    f = cache / f"{h.hexdigest()[:16]}.m4a"
    if f.exists():
        log("soundtrack: unchanged, cached")
    else:
        for old in cache.glob("*.m4a"):
            old.unlink()
        audio.mix(video, timeline, f)
    return f


def composite(video, timeline, clip_files, out):
    """Concatenate the clips' videos (identical encodes, so no re-encode) and mux the mixed soundtrack."""
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{f.resolve()}'\n" for f in clip_files))
    silent = out.with_name("silent.mp4")
    _ffmpeg("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent)
    sound = mixed_sound(video, timeline)
    _ffmpeg("-i", silent, "-i", sound, "-map", "0:v", "-map", "1:a", "-c", "copy", "-t", f"{timeline['duration']:.3f}",
            "-movflags", "+faststart", out)
    for f in (lst, silent):
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


def cached_stills(video, timeline, engine, reqs, boards=False, cache_name=None):
    """Render the stills whose frame changed, and copy the rest from .cache/stills/ (board stills from
    .cache/board-stills/). A still's key is its clip's key and its frame number, so a still is reused
    exactly when its frame is the same. Each cache_name keeps its own folder, since a call removes the
    cached stills it no longer wants. Returns (rendered, reused)."""
    cache = Path(video) / ".cache" / (cache_name or ("board-stills" if boards else "stills"))
    cache.mkdir(parents=True, exist_ok=True)
    keys = {c["id"]: clip_key(video, timeline, c["id"], "boards" if boards else "still") for c in timeline["tracks"]["scene"]}
    fps = timeline["fps"]
    todo, wanted = [], set()
    for r in reqs:
        f = cache / f"{r['clip']}-{keys[r['clip']]}-{tl.half_up(r['t'] * fps)}-{r['scale']}.jpg"
        wanted.add(f.name)
        r["cache"] = f
        if not f.exists():
            todo.append({"clip": r["clip"], "t": r["t"], "out": str(f), "scale": r["scale"], "boards": boards})
    if todo:
        engine.stills(todo)
    for r in reqs:
        shutil.copyfile(r.pop("cache"), r["out"])
    for old in cache.glob("*.jpg"):          # stills of frames that no longer exist
        if old.name not in wanted:
            old.unlink()
    return len(todo), len(reqs) - len(todo)


def log(msg):
    print(msg, flush=True)


def make_cut(video, quality="draft", stills_only=False, changelog=None, engine=None, boards=False):
    """Render cut N+1: stills first (the fastest answer), then only the clips whose key changed,
    then the composite. With boards, a stills-only cut of every chapter's board. Returns the cut record."""
    video = Path(video).resolve()
    stills_only = stills_only or boards
    from . import boards as bd
    bd.write_notes(video)
    timeline = tl.load(video)
    engine = engine or Engine(video)
    from . import cuts
    prev_n = cuts.latest(video, ("boards",) if boards else cuts.SCENE_STILLS)
    prev = read_cut(video, prev_n) if prev_n else None
    n = latest_cut(video) + 1
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
    made, reused = cached_stills(video, timeline, engine, reqs, boards=boards)
    timings["stills"] = round(time.monotonic() - t0, 1)
    log(f"stills: {made} rendered, {reused} unchanged (reused)")

    clips = []
    if not stills_only:
        files, clips = render_clips(video, timeline, engine, quality)
        t1 = time.monotonic()
        composite(video, timeline, files, d / "video.mp4")
        timings["composite"] = round(time.monotonic() - t1, 1)
    else:
        clips = [{"id": cid, "key": key, "rendered": False, "seconds": 0} for cid, key, _ in rows]

    from .cuts import media_info
    from .workspace import atomic_json
    media = media_info(d / "video.mp4") if not stills_only else {
        "width": round(tl.layout(video)["width"] * STILL_SCALE),
        "height": round(tl.layout(video)["height"] * STILL_SCALE), "fps": timeline["fps"]}
    notes = bd.notes(video)
    script_path = video / "SCRIPT.md"
    script_text = script_path.read_text() if script_path.exists() else ""
    from .script import sections
    review_hash = hashlib.sha256(sections(script_text).get("Review log", "").encode()).hexdigest()
    if prev and changed and prev.get("review_log_hash") == review_hash and prev.get("quality") == quality:
        log("warn: changed chapters have no new Review log entry; record merges, cuts and expected runtime change")
    atomic_json(d / "timeline.json", timeline)
    if script_path.exists():
        shutil.copyfile(script_path, d / "SCRIPT.md")
    from .review_state import fingerprint
    record = {
        "source_revision": fingerprint(video, frames=True),
        "media": media, "final": quality == "final" and not stills_only,
        "review_log_hash": review_hash,
        "cut": n, "kind": "boards" if boards else "stills" if stills_only else "final" if quality == "final" else "cut",
        "created": time.strftime("%Y-%m-%d %H:%M:%S"), "quality": quality,
        "video": None if stills_only else "video.mp4", "duration": timeline["duration"],
        "chapters": [{"id": c["id"], "title": c["title"], "start": c["start"]} for c in timeline["tracks"]["scene"]],
        "clips": clips, "changed": changed if prev else [],
        "stills": [{k: r[k] for k in ("id", "clip", "caption", "at")} | {"file": f"stills/{r['id']}.jpg"}
                   | ({"note": notes[r["id"]]} if r["id"] in notes else {}) for r in reqs],
        "changelog": changelog or [],
        "seconds": timings,
    }
    if prev:
        _keep_befores(video, prev_n, d, record)
    (d / "cut.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    from .clean import keep_cuts, prune_cuts
    freed = prune_cuts(video)
    if freed:
        log(f"old draft previews removed (keeping the newest {keep_cuts(video)}): {freed / 1e6:.0f} MB freed")
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
            log(f"render {cid} ({quality}): changed")
            r = engine.render(cid, f, quality)
            log(f"  {r.get('frames', '?')} frames in {r.get('seconds', 0):.0f} s")
        else:
            log(f"render {cid} ({quality}): unchanged, cached")
        records.append({"id": cid, "key": key, "rendered": cached is None, "seconds": round(time.monotonic() - started, 1)})
        files.append(f)
    return files, records


def clip_files_fresh(video, timeline, quality, fmt=None):
    """Whether every clip's cached video exists for the current keys (so the parts of a composite
    can be reused, as publish's web encode does)."""
    return all(f is not None for _, _, f in plan(video, timeline, quality, fmt))


def export_formats(video, formats, quality="final", lufs=None, name=None):
    """The whole video in each format, final quality by default, into out/export/. Every format comes
    from the same timeline and scenes; each has its own stage and caption band."""
    video = Path(video).resolve()
    timeline = tl.load(video)
    if lufs is not None:
        audio.finish(video, lufs)
    out = video / "out" / "export"
    out.mkdir(parents=True, exist_ok=True)
    cfg = settings.raw(video)
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
