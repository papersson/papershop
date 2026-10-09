"""Cuts: render what changed, composite, and write what the review page shows.

A clip's cache key hashes everything its frames depend on: the engine, the video's shared scene
files, the clip's own scene file (scenes/<clip>.tsx), its slice of the timeline (as times relative
to the clip's first frame) and the layout. So an edit to one chapter's scene re-renders that
chapter only, a narration edit re-renders the chapter it is in (later chapters move by whole frames,
see narration.CHAPTER_GRID, and keep their keys), and an edit to a shared file re-renders them all.
Its cues are the ones its scene code names (see scene_cues), so moving a cue re-renders the
chapters that wait on it.

videos/<name>/cuts/cutN/
  video.mp4      the composite with narration (draft: 540p)
  stills/        one frame per sentence, near its end
  cut.json       what was rendered, how long each step took, and the changelog against cut N-1
"""
import hashlib
import json
import re
import shutil
import time
from pathlib import Path

from . import proc
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


def has_scene(video, clip_id, engine=None):
    """Whether a chapter renders its own scene rather than its board: as the Remotion root decides,
    a scenes/<clip>.tsx registered in scenes/index.ts; for the live engine, a scenes/<clip>.js.
    Motion Canvas videos always render scenes."""
    video = Path(video)
    engine = engine or _engine_of(video)
    if engine == "live":
        return (video / "scenes" / f"{clip_id}.js").exists()
    if engine != "remotion":
        return True
    index = next((p for p in (video / "scenes" / "index.ts", video / "scenes" / "index.tsx") if p.exists()), None)
    registered = bool(index and re.search(rf"(?<![\w-]){re.escape(clip_id)}\s*:", index.read_text()))
    return registered and any((video / "scenes" / f"{clip_id}{ext}").exists() for ext in (".tsx", ".ts", ".jsx", ".js"))


def _hash_listing(h, p):
    p = Path(p)
    if p.is_dir():
        for f in sorted(p.rglob("*")):
            if f.is_file():
                st = f.stat()
                h.update(f"{f.relative_to(p)}:{st.st_size}:{int(st.st_mtime)}".encode())


SCENE_CODE = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
# The engines' lists of every clip (Remotion's scenes/index.ts, Motion Canvas's scenes/project.ts)
# import each clip's file without drawing it into the others.
REGISTRIES = {"index", "project"}
# Comments are read as code: a cue named in one costs an extra render at worst, where telling
# comments from JSX text, regexes and URLs would need a parser to get right.
_LITERAL_CUE = re.compile(r"""\bcue\s*\(\s*(?:"([^"\\]*)"|'([^'\\]*)'|`([^`\\$]*)`)\s*[,)]""")
_IMPORT = re.compile(r"""(?:\bfrom|\bimport|\brequire)\s*\(?\s*['"](\.\.?/[^'"?]+)""")


def _cue_names(text):
    """The cue names a scene file waits on, or None when it may read a cue by a name it computes:
    `cue(x)`, `cue` passed on or renamed, or the timeline's `cues` read directly."""
    names = {next(g for g in m.groups() if g is not None) for m in _LITERAL_CUE.finditer(text)}
    rest = _LITERAL_CUE.sub(" ", text)
    rest = re.sub(r"\{[^{}]*\}\s*=", lambda m: re.sub(r"\bcue\s*(?=[,}])", " ", m.group(0)), rest)  # const { cue } = ...
    return None if re.search(r"\bcues?\b", rest) else names


def _imports(f, text, root):
    """The scenes/ files `f` imports by a relative path."""
    for spec in _IMPORT.findall(text):
        base = (f.parent / spec).resolve()
        for c in (base, *(base.with_name(base.name + e) for e in SCENE_CODE), *(base / f"index{e}" for e in SCENE_CODE)):
            if c.is_file() and c.is_relative_to(root):
                yield c
                break


def scene_files(video, clip_id, clip_ids):
    """The scene code a clip runs: its own file (or folder), the shared modules (every scenes/ file
    not named after another clip), and whatever they import, another clip's file included."""
    root = (Path(video) / "scenes").resolve()
    owner = lambda f: Path(f.relative_to(root).parts[0]).stem
    files = sorted(root.rglob("*")) if root.is_dir() else []
    todo = [f for f in files if f.is_file() and f.suffix in SCENE_CODE and (owner(f) == clip_id or owner(f) not in clip_ids)]
    seen = []
    while todo:
        f = todo.pop(0)
        if f in seen:
            continue
        seen.append(f)
        if not (f.parent == root and f.stem in REGISTRIES):
            todo += _imports(f, f.read_text(errors="replace"), root)
    return seen


def scene_cues(video, clip_id, clip_ids):
    """The cue names a clip's scene code reads (scene_files), or None for all cues when any of it
    computes a cue name. The engine kits read cues only through their cue() helper."""
    names = set()
    for f in scene_files(video, clip_id, clip_ids):
        found = _cue_names(f.read_text(errors="replace"))
        if found is None:
            return None
        names |= found
    return names


def clip_key(video, timeline, clip_id, quality, engine=None, fmt=None):
    engine = engine or _engine_of(video)
    video = Path(video)
    clip_ids = {c["id"] for c in timeline["tracks"]["scene"]}
    h = hashlib.sha1(quality.encode())
    _hash_tree(h, engine_dir(engine) / "src")
    _hash_tree(h, engine_dir("shared"))  # the engines' shared modules: motion maths, narration times
    _hash_tree(h, engine_dir(engine) / "package-lock.json")
    scenes = sorted((video / "scenes").iterdir()) if (video / "scenes").is_dir() else []
    for f in scenes:
        if f.stem == clip_id or f.stem not in clip_ids:
            _hash_tree(h, f)
    root = (video / "scenes").resolve()
    for f in scene_files(video, clip_id, clip_ids):     # a helper imported from another clip's file
        if Path(f.relative_to(root).parts[0]).stem in clip_ids - {clip_id}:
            _hash_tree(h, f, root)
    if quality == "boards" or not has_scene(video, clip_id, engine):
        _hash_tree(h, video / "boards")  # the chapter renders its board
    _hash_tree(h, video / "data")       # scenes import their numbers from data/
    _hash_listing(h, video / "assets")  # assets: names, sizes and times (footage is too big to read)
    c = tl.clip(timeline, clip_id)
    first, count = tl.frames(timeline, clip_id)
    t0 = first / timeline["fps"]
    rel = lambda x: round(x - t0, 4)   # the clip's frames depend on times relative to its first frame only
    named = scene_cues(video, clip_id, clip_ids)

    def reads(k, v):
        if named is None:
            return True
        if k.startswith("reveal:"):
            return k.startswith(f"reveal:{clip_id}_") or k in named
        # A named cue counts wherever it lies (an animation started before the clip may still run); one
        # inside the clip's frames counts anyway, in case a scene reaches it in a way the scan missed.
        return k in named or t0 <= v <= t0 + count / timeline["fps"]
    part = {
        "clip": {**c, "start": rel(c["start"]), "end": rel(c["end"])}, "frames": count, "fps": timeline["fps"],
        "narration": [{**s, "start": rel(s["start"]), "end": rel(s["end"]),
                       "pause": {**s["pause"], "start": rel(s["pause"]["start"]), "end": rel(s["pause"]["end"])} if "pause" in s else None,
                       "words": [{**w, "start": rel(w["start"]), "end": rel(w["end"])} for w in s.get("words", [])]}
                      for s in timeline["tracks"]["narration"] if s["clip"] == clip_id],
        "captions": [{"start": rel(x["start"]), "end": rel(x["end"]), "lines": tl.caption_lines(x, fmt)}
                     for x in timeline["tracks"]["captions"] if x["end"] > c["start"] and x["start"] < c["end"]],
        "cues": {k: rel(v) for k, v in timeline.get("cues", {}).items() if reads(k, v)},
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


def composite(video, timeline, clip_files, out):
    """Concatenate the clips' videos (identical encodes, so no re-encode) and mux the soundtrack;
    returns the soundtrack's file."""
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{f.resolve()}'\n" for f in clip_files))
    silent = out.with_name("silent.mp4")
    proc.ffmpeg("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent)
    sound = audio.soundtrack(video, timeline)
    proc.ffmpeg("-i", silent, "-i", sound, "-map", "0:v", "-map", "1:a", "-c", "copy", "-t", f"{timeline['duration']:.3f}",
                "-movflags", "+faststart", out)
    for f in (lst, silent):
        f.unlink()
    return sound


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
    timeline = tl.build(video)      # so an edit to cues.json or audio/tracks.json is in the cut
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

    clips, sound = [], None
    if not stills_only:
        files, clips = render_clips(video, timeline, engine, quality)
        t1 = time.monotonic()
        sound = composite(video, timeline, files, d / "video.mp4").name
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
        "clips": clips, "sound": sound, "changed": changed if prev else [],
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


def export_formats(video, formats, quality="final", lufs=-16.0, name=None):
    """The whole video in each format, final quality by default, into out/export/, its sound finished
    to `lufs`. Every format comes from the same timeline and scenes; each has its own stage and
    caption band."""
    video = Path(video).resolve()
    timeline = tl.build(video)
    audio.finish(video, lufs, timeline=timeline)
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
