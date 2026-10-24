"""Cuts: render what changed, composite, and write what the review page shows.

Clips are cached under their key (keys.py), so a cut renders only what changed.

videos/<name>/cuts/cutN/
  video.mp4      the composite with narration (draft: 540p)
  stills/        one frame per sentence, near its end, and at each event and long pause (moments.stills)
  timeline.json, layout.json, sfx.json, SCRIPT.md   the sources' snapshots (sfx.json with each effect's time)
  cut.json       what was rendered, how long each step took, and the changelog against cut N-1
"""
import json
import shutil
import time
from pathlib import Path

from . import proc
from . import settings
from . import audio
from . import cuts
from . import keys
from . import moments
from . import timeline as tl
from .engine import Engine

STILL_SCALE = 0.25          # 480×270 stills on the page


def plan(video, timeline, quality, fmt=None):
    """[(clip id, key, cached file or None)] for every clip in order."""
    rows = []
    for c in timeline["tracks"]["scene"]:
        key = keys.clip_key(video, timeline, c["id"], quality, c.get("engine"), fmt)
        f = keys.clip_file(video, c["id"], quality, key, fmt)
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


EVENT_LEAD = 0.5            # seconds before an event the page seeks to, so the contact plays


def still_requests(timeline, outdir, clips=None, extra=True):
    """The cut's stills (moments.stills, in time order) as engine requests, with what the review page
    shows: the kind, the caption (a sentence's, an event's name, "pause after <sentence>") and where
    to seek (a sentence's start, just before an event, a pause's start, else the frame's own time).
    extra=False leaves out the event and pause stills (boards, the animatic: one picture a sentence)."""
    said = {s["id"]: s for s in timeline["tracks"]["narration"]}

    def seek(m):
        if "sentence" in m:
            return round(said[m["sentence"]]["start"], 3)
        if "after" in m:
            return round(said[m["after"]]["end"], 3)
        return round(max(0.0, timeline["cues"][m["event"]] - EVENT_LEAD), 3) if "event" in m else m["time"]
    return [{"id": m["id"], "clip": m["clip"], "t": m["t"], "out": str(outdir / f"{m['id']}.jpg"), "scale": STILL_SCALE,
             "kind": m["kind"], "time": m["time"], "caption": m["label"], "at": seek(m)}
            for m in moments.stills(timeline, clips or None, extra)]


def cached_stills(video, timeline, engine, reqs, boards=False, cache_name=None):
    """Render the stills whose frame changed, and copy the rest from .cache/stills/ (board stills from
    .cache/board-stills/). A still's key is its clip's key and its frame number, so a still is reused
    exactly when its frame is the same. Each cache_name keeps its own folder, since a call removes the
    cached stills it no longer wants. Returns (rendered, reused)."""
    cache = Path(video) / ".cache" / (cache_name or ("board-stills" if boards else "stills"))
    cache.mkdir(parents=True, exist_ok=True)
    key = {c["id"]: keys.clip_key(video, timeline, c["id"], "boards" if boards else "still") for c in timeline["tracks"]["scene"]}
    fps = timeline["fps"]
    todo, wanted = [], set()
    for r in reqs:
        f = cache / f"{r['clip']}-{key[r['clip']]}-{tl.half_up(r['t'] * fps)}-{r['scale']}.jpg"
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
    from . import events
    events.emit(video, 'render.started', 'Making the next version', source='studio cut')
    stills_only = stills_only or boards
    from . import boards as bd
    bd.write_notes(video)
    timeline = tl.build(video)      # so an edit to cues.json or audio/tracks.json is in the cut
    if not stills_only:
        audio.sources(video, timeline)   # an effect with no time stops the cut before any clip renders
        if quality == "final":
            audio.require_voice(video, timeline)   # a draft may play without its voice; a final may not
    engine = engine or Engine(video)
    prev_n = cuts.latest(video, ("boards",) if boards else cuts.SCENE_STILLS)
    prev = cuts.read(video, prev_n) if prev_n else None
    n, d = cuts.allocate(video)
    timings = {}

    rows = plan(video, timeline, quality)
    prev_keys = {c["id"]: c["key"] for c in prev["clips"]} if prev else {}
    changed = [cid for cid, key, _ in rows if prev_keys.get(cid) != key]

    t0 = time.monotonic()
    reqs = still_requests(timeline, d / "stills", extra=not boards)      # a board looks the same at every event
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

    from .workspace import atomic_json
    media = cuts.media_info(d / "video.mp4") if not stills_only else {
        "width": round(tl.layout(video)["width"] * STILL_SCALE),
        "height": round(tl.layout(video)["height"] * STILL_SCALE), "fps": timeline["fps"]}
    notes = bd.notes(video)
    script_path = video / "SCRIPT.md"
    atomic_json(d / "cues.json", tl.cue_sources(video)[0])
    atomic_json(d / "timeline.json", timeline)
    atomic_json(d / "layout.json", tl.layout(video))       # what a motion review of this cut reads, as it was
    if (video / "audio" / "sfx.json").exists():
        from .sfx import place
        atomic_json(d / "sfx.json", [{**p.cue, "time": p.time}
                                     for p in place(json.loads((video / "audio" / "sfx.json").read_text()), timeline, strict=False)])
    if script_path.exists():
        shutil.copyfile(script_path, d / "SCRIPT.md")
    record = {
        "media": media, "final": quality == "final" and not stills_only,
        "cut": n, "kind": "boards" if boards else "stills" if stills_only else "final" if quality == "final" else "cut",
        "created": time.strftime("%Y-%m-%d %H:%M:%S"), "t": round(time.time(), 3), "quality": quality,
        "video": None if stills_only else "video.mp4", "duration": timeline["duration"],
        "chapters": [{"id": c["id"], "title": c["title"], "start": c["start"]} for c in timeline["tracks"]["scene"]],
        "clips": clips, "sound": sound, "changed": changed if prev else [],
        "stills": [{k: r[k] for k in ("id", "clip", "kind", "time", "caption", "at")} | {"file": f"stills/{r['id']}.jpg"}
                   | ({"note": notes[r["id"]]} if r["id"] in notes else {}) for r in reqs],
        "changelog": changelog or [],
        "seconds": timings,
    }
    if prev:
        _keep_befores(video, prev_n, d, record)
    cuts.write(video, n, record)
    events.emit(video, 'version.ready' if not stills_only else 'stills.ready',
                f'Version {n} ready', version=n, source=f'cuts/cut{n}/cut.json')
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
            src = cuts.cut_dir(video, prev_n) / s["file"]
            if src.exists() and src.read_bytes() != (d / s["file"]).read_bytes():
                before.mkdir(exist_ok=True)
                shutil.copyfile(src, before / src.name)
                s["before"] = f"before/{src.name}"


def estimate(video, timeline, quality, clips):
    """How long rendering `clips` should take, from the seconds a frame the earlier cuts at this
    quality took for the clips they rendered: {frames, per_frame, seconds, from: [cut numbers]}, or
    None with nothing to go on. Chapters differ in cost (a 3D chapter costs more than a map), so it
    is the median, said as an estimate."""
    import statistics
    rates, used = [], []
    for n, rec in sorted(cuts.records(video).items()):
        if rec.get("quality") != quality:
            continue
        for c in rec.get("clips", []):
            if c.get("rendered") and c.get("frames") and c.get("seconds"):
                rates.append(c["seconds"] / c["frames"])
                used.append(n)
    if not rates:
        return None
    frames = sum(tl.frames(timeline, c)[1] for c in clips)
    per = statistics.median(rates)
    return {"frames": frames, "per_frame": round(per, 3), "seconds": round(frames * per, 1), "from": sorted(set(used))}


def _minutes(seconds):
    return f"{seconds / 60:.0f} min" if seconds >= 90 else f"{seconds:.0f} s"


def render_clips(video, timeline, engine, quality="draft", fmt=None):
    """Render the clips whose cached video is missing (or stale) in `fmt`; returns ([files], [records]).
    Before rendering, it says how long that should take (estimate)."""
    files, records = [], []
    rows = plan(video, timeline, quality, fmt)
    todo = [cid for cid, _, cached in rows if cached is None]
    if todo:
        est = estimate(video, timeline, quality, todo)
        frames = sum(tl.frames(timeline, c)[1] for c in todo)
        log(f"render: {len(todo)} clip(s), {frames} frames at {quality}; " + (
            f"about {_minutes(est['seconds'])} ({est['per_frame']:.2f} s a frame in cut {', '.join(map(str, est['from'][-3:]))})"
            if est else "no earlier render at this quality to estimate from"))
    for cid, key, cached in rows:
        f = keys.clip_file(video, cid, quality, key, fmt)
        f.parent.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        if not f.exists():
            for old in f.parent.glob(f.name.replace(key, "*")):
                old.unlink()
            log(f"render {cid} ({quality}): changed")
            r = engine.render(cid, f, quality)
            log(f"  {r.get('frames', '?')} frames in {r.get('seconds', 0):.0f} s")
        else:
            log(f"render {cid} ({quality}): unchanged, cached")
        records.append({"id": cid, "key": key, "rendered": cached is None, "seconds": round(time.monotonic() - started, 1),
                        "frames": tl.frames(timeline, cid)[1]})
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
