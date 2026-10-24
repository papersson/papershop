"""`studio new NAME`: a video folder, ready for a script.

The folder goes to --dir, else $STUDIO_HOME/NAME (default ~/studio/NAME), so a video about a repo
does not put renders and caches into that repo; --source records which repo and commit it explains.
"""
import json
import shutil
from pathlib import Path

from . import proc
from . import settings
from .env import ROOT, studio_home
from . import timeline as tl
from .timeline import DEFAULT_LAYOUT

TEMPLATES = ROOT / "templates"
from .checkpoint import GITIGNORE
from . import checkpoint, preferences


def source_record(path):
    p = Path(path).expanduser().resolve()
    rec = {"path": str(p)}
    try:
        rec["commit"] = proc.run(["git", "-C", str(p), "rev-parse", "HEAD"], capture_output=True, text=True,
                                 check=True).stdout.strip()
    except (proc.CalledProcessError, FileNotFoundError):
        pass
    return rec


def default_title(name):
    """A title from NAME, which may be a path: its folder's name, words for hyphens."""
    return Path(name).name.replace("-", " ").capitalize()


def target(name, directory=None):
    """The folder a new video goes into: --dir, else $STUDIO_HOME/NAME. Refused when it already
    holds a video, is STUDIO_HOME itself, or holds anything else: `new --dir $STUDIO_HOME` once made
    the home a video repository, with every video in it swept into its commits."""
    video = (Path(directory).expanduser() if directory else studio_home() / name).resolve()
    if (video / "video.json").exists():
        raise SystemExit(f"{video} already holds a video")
    if video == studio_home().resolve():
        raise SystemExit(f"{video} is STUDIO_HOME, which holds the videos; make the video in a new folder of its own")
    if video.is_dir() and any(video.iterdir()):
        raise SystemExit(f"{video} is not empty; make the video in a new folder")
    return video


def create(name, directory=None, title=None, source=None, duration=None, engine="live"):
    if engine != "live":
        raise SystemExit("Studio renders live scenes; use the older pinned kit for other engines")
    video = target(name, directory)
    (video / "scenes").mkdir(parents=True, exist_ok=True)
    for folder in ("research", "cues", "data"):
        (video / folder).mkdir(exist_ok=True)
    cfg = {"title": title or default_title(name), "version": "v1", "destination": "private-page",
           "engine": engine, "poster": None, "git": {"sign": None}, "keep_cuts": settings.DEFAULTS["keep_cuts"]}
    if source:
        cfg["source"] = source_record(source)
    if duration:
        cfg["duration"] = float(duration)
    (video / "video.json").write_text(json.dumps(cfg, indent=1) + "\n")
    (video / "layout.json").write_text(json.dumps(DEFAULT_LAYOUT, indent=1) + "\n")
    if duration:
        tl.build(video)
    else:
        nr = json.loads((TEMPLATES / "narration.json").read_text())
        nr["kokoro"]["speed"] = 0.95
        nr["timing"] = {"beat": 0.5, "chapter_hold": 2.0, "chapter_gap": 1.2, **nr.get("timing", {})}
        (video / "narration.json").write_text(json.dumps(nr, indent=1) + "\n")
        script = (TEMPLATES / "SCRIPT.md").read_text().replace("{{Title}}", cfg["title"])
        (video / "SCRIPT.md").write_text(script)
    scenes = TEMPLATES / "live" / "scenes"
    for f in scenes.iterdir():
        shutil.copyfile(f, video / "scenes" / f.name)
    (video / ".gitignore").write_text(GITIGNORE)
    preferences.snapshot(video)
    checkpoint.init(video)
    return video, ROOT / "references" / "taste.md"


def main(args):
    source_cfg = settings.raw(args.from_video) if args.from_video else {}
    args.engine = args.engine or source_cfg.get("engine") or "live"
    video, _ = create(args.name, args.dir, args.title, args.source, args.duration, args.engine)
    if args.from_video:
        copied = preferences.inherit(video, args.from_video, args.include)
        cfg = json.loads((video / "video.json").read_text())
        cfg["series_of"] = str(Path(args.from_video).resolve())
        if not args.source and source_cfg.get("source"):
            cfg["source"] = source_cfg["source"]
        (video / "video.json").write_text(json.dumps(cfg, indent=1) + "\n")
        print("series files copied: " + (", ".join(copied) or "look and pronunciation only"))
    print(f"new video at {video}")
    return 0


