"""Cut records, their kinds and their protection, shared by cleanup, the review page, publish and
the system player.

A cut's kind says what its pictures are: "stills" (one frame per sentence from the scenes, no
movie), "boards" (frames drawn from the boards, before scene code), "animatic" (stills or boards
held to the narration, with its audio), "cut" (the scenes rendered at draft quality) and "final".
Only "cut" and "final" are the video itself; publish and frame review choose among those."""
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


KINDS = ("stills", "boards", "animatic", "cut", "final")
RENDERED = ("cut", "final")
SCENE_STILLS = ("stills", "cut", "final")   # kinds whose stills come from the scene code


def kind(rec):
    """A record's kind; records written before kinds existed are classified by their fields."""
    if rec.get("kind"):
        return rec["kind"]
    if "video" in rec and not rec["video"]:
        return "stills"           # stills-only cuts record "video": null
    return "final" if rec.get("final") else "cut"


def latest(video, kinds=KINDS, playable_only=False, recs=None):
    """The highest cut number of one of these kinds (0 when there is none)."""
    recs = records(video) if recs is None else recs
    return max((n for n, r in recs.items() if kind(r) in kinds and (not playable_only or playable(video, n))), default=0)


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
    rendered = latest(video, RENDERED, playable_only=True, recs=recs)
    if rendered:
        keep.add(rendered)        # a newer animatic must not leave the last real cut unprotected
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
    n = args.cut or latest(args.video, ("animatic", "cut", "final"), playable_only=True, recs=recs)
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
