"""Music from the palette: two or three steady tracks under a narrated film, changing at chapter joins.

The palette is STUDIO_HOME/music: palette.json lists the tracks (title, artist, licence, where it came
from, seconds) and tracks/ID.mp3 holds them, kept in the media bucket like a film's media (its
media.json; fetched here when a track is missing). Every palette track is steady and gently moving,
the kind computing explainers keep under their voice, and Creative Commons Attribution, so a film
that uses one credits it.

video.json "music":
  true      the default `studio new` writes: studio chooses the tracks
  [ID, ...] these palette tracks, in this order
  false     no music; a video.json without the key (every film made before 0.31.0) has none either
Music entries in audio/tracks.json win: a film whose music was placed by hand keeps it.

The plan, deterministic for a film: about one track per TRACK_SPAN seconds (one to MAX_TRACKS),
chosen by the film's folder name so films differ; the chapters split into that many runs of nearly
equal length, each run's track starting with its first chapter, so the music changes where the story
does. A track shorter than its run hands over to the next palette track, never leaving a piece
shorter than MIN_PIECE (the two share the run instead). Neighbours cross over FADE
seconds: the leaving track fades out over the first FADE seconds of the next, which fades in. The
mix (audio.py) levels each entry under the narration and the duck settles it under speech.

The tracks are copied into assets/music/ID.mp3 with a provenance row (kind supplied, params.music),
so a film renders without the palette and `studio asset list --credits` and the page credit them.
"""
import hashlib
import json
import shutil
from pathlib import Path

from .env import studio_home

TRACK_SPAN = 420.0       # seconds of film per track, roughly
MAX_TRACKS = 3
MIN_PIECE = 90.0         # seconds: a hand-over never leaves a shorter piece of a track; the two share
FADE = 3.0               # seconds two tracks overlap, and the film's first fade in and last fade out
LICENSES = {"CC BY 3.0": "CC-BY-3.0", "CC BY 4.0": "CC-BY-4.0"}


def home():
    return studio_home() / "music"


def palette(root=None):
    """The palette's tracks, or [] when this machine has no palette."""
    f = Path(root or home()) / "palette.json"
    return json.loads(f.read_text())["tracks"] if f.exists() else []


def wanted(cfg, tracks):
    """The palette tracks the film asks for, or None when it asks for no music."""
    choice = cfg.get("music")
    if choice is True:
        return None if not tracks else "choose"
    if isinstance(choice, list):
        ids = {t["id"]: t for t in tracks}
        missing = [i for i in choice if i not in ids]
        if missing:
            raise SystemExit(f"video.json music: {', '.join(map(repr, missing))} not in the palette "
                             f"({home() / 'palette.json'}): {', '.join(ids)}")
        return [ids[i] for i in choice]
    if choice in (None, False):
        return None
    raise SystemExit(f"video.json music must be true, false or a list of palette track ids (got {choice!r})")


def choose(name, tracks):
    """The palette in the order a film called `name` uses it: from a place its name picks, around.
    Each run takes the first unused track long enough for it, else the first unused one."""
    k = int(hashlib.sha256(name.encode()).hexdigest(), 16) % len(tracks)
    return tracks[k:] + tracks[:k]


def runs(scenes, duration, n):
    """[(start, end)]: the chapters in n runs of nearly equal length, each starting at a chapter start."""
    starts = sorted({round(c["start"], 3) for c in scenes} | {0.0})
    n = max(1, min(n, len(starts)))
    cuts = [0.0]
    for i in range(1, n):
        aim = duration * i / n
        best = min((s for s in starts if s > cuts[-1]), key=lambda s: abs(s - aim), default=None)
        if best is None or best >= duration:
            break
        cuts.append(best)
    return list(zip(cuts, cuts[1:] + [duration]))


def plan(name, scenes, duration, tracks, chosen=None):
    """The music entries for a film (files as assets/music/ID.mp3), without touching any file.
    `chosen`: the tracks video.json names, else they are chosen from `tracks` by `name`."""
    n = min(MAX_TRACKS, max(1, round(duration / TRACK_SPAN)))
    order = chosen or choose(name, tracks)
    spans = runs(scenes, duration, len(chosen) if chosen else n)
    entries, queue = [], list(order)

    def take(need):
        """The next track: when choosing, the first in the queue long enough for `need` seconds."""
        if not queue:
            queue.extend(order)
        fits = [] if chosen else [x for x in queue if x["seconds"] - FADE >= need]
        track = (fits or queue)[0]
        queue.remove(track)
        return track

    for start, end in spans:
        t = start
        while end - t > 0.5:
            track = take(end - t)
            usable, left = track["seconds"] - FADE, end - t
            length = left if left <= usable else min(usable, left / 2) if left - usable < MIN_PIECE else usable
            entries.append({"file": f"assets/music/{track['id']}.mp3", "start": round(t, 3), "in": 0.0,
                            "out": round(length, 3), "fade": FADE, "role": "music"})
            t += length
    for e in entries[:-1]:          # each fades out under the next one's fade in
        e["out"] = round(min(e["out"] + FADE, _seconds(order, e)), 3)
    if entries and entries[-1]["start"] + entries[-1]["out"] > duration:
        entries[-1]["out"] = round(duration - entries[-1]["start"], 3)
    return entries


def _seconds(tracks, entry):
    tid = Path(entry["file"]).stem
    return next((t["seconds"] for t in tracks if t["id"] == tid), None)


def place(video, tracks, root=None):
    """Copy each track into assets/music/ with its provenance row; fetch it from the media bucket into
    the palette first when this machine lacks it. Returns the ids it could not place."""
    from . import assets, media
    root = Path(root or home())
    have = assets.read(video)
    missing = []
    for t in tracks:
        rel = f"music/{t['id']}.mp3"
        dst = assets.dir_of(video) / rel
        if dst.exists() and any(r["file"] == rel for r in have):
            continue
        src = root / t["file"]
        if not src.exists():
            try:
                media.pull(root)
            except SystemExit as e:
                print(f"warn: music: can't fetch the palette ({e.code}); the film has no music this time")
                return [x["id"] for x in tracks]
        if not src.exists():
            missing.append(t["id"])
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        assets.record(video, rel, "supplied", t["source"], LICENSES.get(t["license"], t["license"]),
                      {"music": t["id"], "title": t["title"], "artist": t["artist"], "homepage": t["source"],
                       "license_name": t["license"], "license_url": t["license_url"]})
    return missing


def prune(video, keep):
    """Remove the palette tracks a film no longer uses, and their provenance rows, so its credits name
    only the music it plays."""
    from . import assets
    rows = assets.read(video)
    gone = [r for r in rows if r["params"].get("music") and r["params"]["music"] not in keep]
    if not gone:
        return
    for r in gone:
        (assets.dir_of(video) / r["file"]).unlink(missing_ok=True)
    kept = [r for r in rows if r not in gone]
    assets._write(assets.dir_of(video) / "provenance.json", (json.dumps(kept, indent=1, ensure_ascii=False) + "\n").encode())


def entries(video, timeline, cfg, say=print):
    """The music entries a build adds: none unless video.json asks for music and the film is narrated."""
    tracks = palette()
    choice = wanted(cfg, tracks)
    if choice is None or not timeline["tracks"].get("narration"):
        if cfg.get("music") is True and not tracks:
            say(f"warn: video.json asks for music, but there is no palette at {home() / 'palette.json'}")
        return []
    chosen = None if choice == "choose" else choice
    es = plan(Path(video).resolve().name, timeline["tracks"]["scene"], timeline["duration"], tracks, chosen)
    used = [t for t in tracks if any(e["file"] == f"assets/music/{t['id']}.mp3" for e in es)]
    prune(video, {t["id"] for t in used})
    missing = place(video, used)
    if missing:
        say(f"warn: music: {', '.join(missing)} not in the palette's tracks/; the film has no music this time")
        return []
    return es
