"""`studio clean VIDEO [--dry-run]`: remove what the studio can regenerate, and say how much it freed.

Removed:
  cuts beyond the newest `keep_cuts` (video.json, default 3), except the cut of the latest notes round
  narration chunks in .cache/narration that the current script no longer uses (Kokoro)
  rendered clips (.cache/clips), web-encode parts (.cache/web), stills (.cache/stills) and label
  crops (.cache/crops) whose key no longer matches the timeline and scenes
  older Remotion bundles (.cache/bundle: the newest per layout is kept)
  mixed soundtracks other than the current one (.cache/sound)
  out/sheets (contact sheets and crops: `studio sheets` rebuilds them), out/web.mp4 (a copy of
  out/page/video.mp4) and audio/final.wav (the loudness pass: `studio publish` redoes it)

Never touched: SCRIPT.md, scenes/, data/, sims/, research/, assets/, narration.json, timeline.json,
layout.json, video.json, review/, audio/narration.mp3 and narration.wav, the ElevenLabs response
cache (paid for; committed with the video), the latest cut, out/master.mp4 and out/page/.

After every cut, `studio cut` applies the same rule to old cuts (prune_cuts).
"""
import json
import shutil
from pathlib import Path

from . import render
from . import timeline as tl

KEEP_CUTS = 3


def keep_cuts(video):
    f = Path(video) / "video.json"
    cfg = json.loads(f.read_text()) if f.exists() else {}
    return max(1, int(cfg.get("keep_cuts", KEEP_CUTS)))


def _size(p):
    p = Path(p)
    if p.is_symlink() or p.is_file():
        return p.lstat().st_size
    return sum(f.lstat().st_size for f in p.rglob("*") if f.is_file() or f.is_symlink())


def stale_cuts(video):
    """Cut folders to remove: all but the newest keep_cuts, never the latest, never the cut the latest
    notes round was about."""
    video = Path(video)
    nums = sorted(int(p.name[3:]) for p in render.cuts_dir(video).glob("cut*") if p.name[3:].isdigit())
    if not nums:
        return []
    keep = set(nums[-keep_cuts(video):]) | {nums[-1]}
    log = video / "review" / "notes.jsonl"
    if log.exists():
        rounds = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
        rounds = [r for r in rounds if r.get("type") == "round"]
        if rounds:
            keep.add(int(rounds[-1]["cut"]))
    return [render.cuts_dir(video) / f"cut{n}" for n in nums if n not in keep]


def prune_cuts(video):
    """Remove old cuts after a new one; returns bytes freed."""
    freed = 0
    for d in stale_cuts(video):
        freed += _size(d)
        shutil.rmtree(d, ignore_errors=True)
    return freed


def _narration_stale(video):
    from . import narration as nr, script as sc
    try:
        S = nr.Settings(video)
        chapters = sc.load(S.video)
    except (SystemExit, OSError, KeyError, ValueError):     # no script or settings yet: nothing to judge
        return []
    cache = Path(video) / ".cache" / "narration"
    if not cache.is_dir():
        return []
    wanted = set()
    for chunk, _, _ in nr.all_chunks(S, chapters):
        marked = " ".join(S.marked(t, lid) for lid, t, _ in chunk)
        wanted.add(nr.kokoro_key(S, marked))
        wanted.add(nr.kokoro_key(S, " ".join(t for _, t, _ in chunk)))
    return [f for f in cache.iterdir() if f.is_file() and f.stem not in wanted]


def _keyed_stale(video, t):
    """Clip, web, still and crop cache entries whose key is not the current one."""
    video = Path(video)
    ids = [c["id"] for c in t["tracks"]["scene"]]
    cache = video / ".cache"
    out = []
    clips = {}
    for q in ("draft", "final"):
        for cid in ids:
            clips[f"{cid}-{q}-{render.clip_key(video, t, cid, q)}"] = True
    fmts = {}
    for f in (cache / "clips").glob("*.mp4") if (cache / "clips").is_dir() else []:
        parts = f.stem.split("-")
        if f.stem in clips:
            continue
        if len(parts) == 4:              # <clip>-<quality>-<format>-<key>: another format's clip
            cid, q, tag, key = parts
            fmt = tag.replace("x", ":")
            fmts.setdefault(fmt, {})
            if cid in ids and q in ("draft", "final"):
                fmts[fmt].setdefault((cid, q), render.clip_key(video, t, cid, q, fmt=fmt))
                if fmts[fmt][(cid, q)] == key:
                    continue
            out.append(f)
        else:
            out.append(f)
    finals = {f"{cid}-final-{render.clip_key(video, t, cid, 'final')}" for cid in ids}
    for f in (cache / "web").glob("*.mp4") if (cache / "web").is_dir() else []:
        if not any(f.stem.startswith(s + "-") for s in finals):
            out.append(f)
    for kind, folder in (("still", "stills"), ("crops", "crops")):
        keys = {f"{cid}-{render.clip_key(video, t, cid, kind)}-" for cid in ids}
        d = cache / folder
        for f in d.iterdir() if d.is_dir() else []:
            if not any(f.name.startswith(k) for k in keys):
                out.append(f)
    return out


def _bundles_stale(video):
    root = Path(video) / ".cache" / "bundle"
    out = []
    for layout in root.iterdir() if root.is_dir() else []:
        dirs = sorted((d for d in layout.iterdir() if d.is_dir()), key=lambda d: d.stat().st_mtime)
        out += dirs[:-1]
    return out


def _sound_stale(video, t):
    d = Path(video) / ".cache" / "sound"
    if not d.is_dir():
        return []
    files = sorted(d.glob("*.m4a"), key=lambda f: f.stat().st_mtime)
    return files[:-1]


def plan(video):
    """[(path, reason)] of everything clean would remove."""
    video = Path(video).resolve()
    items = [(d, "old cut") for d in stale_cuts(video)]
    items += [(f, "narration chunk not in the current script") for f in _narration_stale(video)]
    if (video / "timeline.json").exists():
        t = tl.load(video)
        items += [(f, "cache entry for an older version") for f in _keyed_stale(video, t)]
        items += [(f, "older soundtrack mix") for f in _sound_stale(video, t)]
    items += [(d, "older bundle") for d in _bundles_stale(video)]
    for p, why in ((video / "out" / "sheets", "sheets (studio sheets rebuilds them)"),
                   (video / "out" / "web.mp4", "copy of out/page/video.mp4"),
                   (video / "audio" / "final.wav", "loudness pass (publish redoes it)")):
        if p.exists():
            items.append((p, why))
    return items


def clean(video, dry_run=False):
    items = plan(video)
    total = 0
    by = {}
    for p, why in items:
        n = _size(p)
        total += n
        by.setdefault(why, [0, 0])
        by[why][0] += 1
        by[why][1] += n
        if not dry_run:
            if p.is_dir() and not p.is_symlink():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink(missing_ok=True)
    return total, by


def main(args):
    total, by = clean(args.video, args.dry_run)
    for why, (n, size) in sorted(by.items(), key=lambda x: -x[1][1]):
        print(f"{size / 1e6:9.1f} MB  {n:5} × {why}")
    print(f"{'would free' if args.dry_run else 'freed'} {total / 1e6:.1f} MB ({total} bytes)")
    return 0
