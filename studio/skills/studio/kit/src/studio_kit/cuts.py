"""Cut protection is shared by cleanup, the review page and the system player."""
import json
import subprocess
import sys
from pathlib import Path

from .workspace import atomic_json, locked, now


def records(video):
    out = {}
    for p in (Path(video) / "cuts").glob("cut*/cut.json"):
        if not p.parent.name[3:].isdigit():
            continue
        try:
            out[int(p.parent.name[3:])] = json.loads(p.read_text())
        except (ValueError, OSError):
            out[int(p.parent.name[3:])] = {}  # Unknown records must never be considered disposable.
    return out


def playable(video, n):
    return (Path(video) / "cuts" / f"cut{n}" / "video.mp4").is_file()


def protected(video, recs=None):
    recs = records(video) if recs is None else recs
    keep = {n for n, r in recs.items() if r.get("watched") or r.get("pinned") or r.get("quality") != "draft"}
    if recs:
        keep.add(max(recs))
    movies = [n for n in recs if playable(video, n)]
    if movies:
        keep.add(max(movies))
    log = Path(video) / "review" / "notes.jsonl"
    if log.exists():
        for line in log.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                return set(recs)  # An incomplete notes log is not permission to delete media.
            if r.get("type") in ("note", "round") and r.get("cut") is not None:
                keep.add(int(r["cut"]))
    return keep


def mark_watched(video, n):
    with locked(video):
        p = Path(video) / "cuts" / f"cut{n}" / "cut.json"
        if not p.exists() or not playable(video, n):
            raise SystemExit(f"cut {n} has no playable video")
        rec = json.loads(p.read_text())
        rec["watched"] = now()
        atomic_json(p, rec)


def main_open(args):
    recs = records(args.video)
    n = args.cut or max((n for n in recs if playable(args.video, n)), default=0)
    mark_watched(args.video, n)
    p = (Path(args.video) / "cuts" / f"cut{n}" / "video.mp4").resolve()
    command = ["open" if sys.platform == "darwin" else "xdg-open", str(p)]
    try:
        subprocess.run(command, check=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        raise SystemExit(f"cut {n} protected, but the player could not open {p}: {e}")
    print(f"opened cut {n}: {p} (protected; playback completion is not measured)")


def media_info(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate", "-of", "json", str(path)],
                       capture_output=True, text=True, check=True)
    s = json.loads(r.stdout)["streams"][0]
    a, b = s["r_frame_rate"].split("/")
    return {"width": s["width"], "height": s["height"], "fps": float(a) / float(b)}
