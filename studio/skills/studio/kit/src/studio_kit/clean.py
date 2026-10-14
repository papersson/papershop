"""Remove regenerable caches and old draft previews; MP4 deletion is explicit and protected."""
import json
import shutil
from pathlib import Path

from . import settings
from . import cuts, keys
from .workspace import atomic_json, locked, now
from . import timeline as tl

KEEP_CUTS = settings.DEFAULTS["keep_cuts"]


def keep_cuts(video):
    return max(1, int(settings.load(video)["keep_cuts"]))


def _size(p):
    p = Path(p)
    if p.is_symlink() or p.is_file():
        return p.lstat().st_size
    return sum(f.lstat().st_size for f in p.rglob("*") if f.is_file() or f.is_symlink())


def stale_cuts(video):
    """Unprotected old drafts whose previews may be removed; records always survive."""
    recs = cuts.records(video)
    movies = sorted(n for n in recs if cuts.playable(video, n))
    previews = sorted(n for n in recs if not cuts.playable(video, n))
    keep = cuts.protected(video, recs) | set(movies[-keep_cuts(video):]) | set(previews[-keep_cuts(video):])
    return [cuts.cut_dir(video, n) for n in sorted(recs) if n not in keep]


def cut_plan(video, videos=False):
    items = []
    for d in stale_cuts(video):
        for name in ("stills", "before", "crops", "silent.mp4"):
            if (d / name).exists():
                items.append((d / name, "old draft preview"))
        if videos and (d / "video.mp4").exists():
            items.append((d / "video.mp4", "unprotected old draft video"))
    return items


def prune_cuts(video):
    with locked(video):
        items = cut_plan(video)
        freed = sum(_size(p) for p, _ in items)
        for p, _ in items:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
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
            clips[f"{cid}-{q}-{keys.clip_key(video, t, cid, q)}"] = True
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
                fmts[fmt].setdefault((cid, q), keys.clip_key(video, t, cid, q, fmt=fmt))
                if fmts[fmt][(cid, q)] == key:
                    continue
            out.append(f)
        else:
            out.append(f)
    finals = {f"{cid}-final-{keys.clip_key(video, t, cid, 'final')}" for cid in ids}
    for f in (cache / "web").glob("*.mp4") if (cache / "web").is_dir() else []:
        if not any(f.stem.startswith(s + "-") for s in finals):
            out.append(f)
    for kind, folder in (("still", "stills"), ("crops", "crops")):
        current = {f"{cid}-{keys.clip_key(video, t, cid, kind)}-" for cid in ids}
        d = cache / folder
        for f in d.iterdir() if d.is_dir() else []:
            if not any(f.name.startswith(k) for k in current):
                out.append(f)
    return out


def _bundles_stale(video):
    root = Path(video) / ".cache" / "bundle"
    out = []
    for layout in root.iterdir() if root.is_dir() else []:
        dirs = sorted((d for d in layout.iterdir() if d.is_dir()), key=lambda d: d.stat().st_mtime)
        out += dirs[:-1]
    return out


def _plates_stale(video, t):
    """Plate frame stores (plates.py) not under a plated clip's current key for draft or final: an
    older version of the scene, or a clip that no longer has a plate. One film kept 20 GB of these."""
    from . import plates
    root = Path(video) / ".cache" / "plates"
    if not root.is_dir():
        return []
    ids = {c["id"] for c in t["tracks"]["scene"]}
    current = {f"{c}-{q}-{plates.key(video, t, c, q)}" for c in plates.config(video) if c in ids for q in ("draft", "final")}
    return [d for d in root.iterdir() if d.is_dir() and d.name not in current]


REVIEW_IMAGES = {".png", ".jpg", ".jpeg", ".webp"}


def _review_images_stale(video):
    """The frame images in review bundles older than each kind's newest: copies of a cut's frames,
    which the cut can make again. The manifest, the prompt and the reviewer's result stay."""
    out = []
    for kind in ("motion_review", "frame_review"):
        root = Path(video) / "research" / kind
        bundles = sorted((d for d in root.iterdir() if d.is_dir()), key=lambda d: d.stat().st_mtime) if root.is_dir() else []
        for d in bundles[:-1]:
            out += [f for f in d.rglob("*") if f.is_file() and f.suffix.lower() in REVIEW_IMAGES]
    return out


def _sound_stale(video, t):
    d = Path(video) / ".cache" / "sound"
    if not d.is_dir():
        return []
    files = sorted(d.glob("*.m4a"), key=lambda f: f.stat().st_mtime)
    return files[:-1]


def plan(video, videos=False):
    """[(path, reason)] of everything clean would remove."""
    video = Path(video).resolve()
    items = cut_plan(video, videos)
    items += [(f, "narration chunk not in the current script") for f in _narration_stale(video)]
    if (video / "timeline.json").exists():
        t = tl.load(video)
        items += [(f, "cache entry for an older version") for f in _keyed_stale(video, t)]
        items += [(f, "older soundtrack mix") for f in _sound_stale(video, t)]
        items += [(d, "plate frames for an older version") for d in _plates_stale(video, t)]
    items += [(d, "older bundle") for d in _bundles_stale(video)]
    items += [(f, "review images of an older bundle (its manifest and result stay)") for f in _review_images_stale(video)]
    for p, why in ((video / "out" / "sheets", "sheets (studio sheets rebuilds them)"),
                   (video / "out" / "web.mp4", "copy of out/page/video.mp4"),
                   (video / "audio" / "final.wav", "loudness pass (publish redoes it)")):
        if p.exists():
            items.append((p, why))
    return items


def _clean(video, dry_run=False, videos=False):
    items = plan(video, videos)
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
                if why == "unprotected old draft video":
                    record = p.parent / "cut.json"
                    rec = json.loads(record.read_text())
                    rec.update(video=None, media_removed=now())
                    atomic_json(record, rec)
    return total, by


def clean(video, dry_run=False, videos=False):
    if dry_run:
        return _clean(video, True, videos)
    with locked(video):
        return _clean(video, dry_run, videos)


def main(args):
    total, by = clean(args.video, args.dry_run, args.videos)
    for why, (n, size) in sorted(by.items(), key=lambda x: -x[1][1]):
        print(f"{size / 1e6:9.1f} MB  {n:5} × {why}")
    print(f"{'would free' if args.dry_run else 'freed'} {total / 1e6:.1f} MB ({total} bytes)")
    return 0
