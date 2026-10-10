"""`studio new NAME`: a video folder, ready for a script.

The folder goes to --dir, else $STUDIO_HOME/NAME (default ~/studio/NAME), so a video about a repo
does not put renders and caches into that repo; --source records which repo and commit it explains.
STUDIO_HOME also holds learner.md, the learner model every video's student reviewer plays.
"""
import json
import os
import re
import shutil
import time
from datetime import datetime
from pathlib import Path

from . import proc
from . import settings
from .env import ROOT, studio_home
from . import timeline as tl
from .timeline import DEFAULT_LAYOUT

TEMPLATES = ROOT / "templates"
from .checkpoint import GITIGNORE
from . import checkpoint, preferences
from .stage import LEVEL_BUDGET as LEVEL_BUDGETS


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


def create(name, directory=None, title=None, drive="author", source=None, genre="explainer", duration=None, engine="remotion",
           level="intro", checkpoints="few", mode="background", tone="plain"):
    video = target(name, directory)
    (video / "scenes").mkdir(parents=True, exist_ok=True)
    (video / "research").mkdir(exist_ok=True)
    cfg = {"title": title or default_title(name), "version": "v1", "genre": genre,
           "drive": drive, "destination": "private-page", "engine": engine, "poster": None,
           "level": level, "tone": tone, "mode": mode, "checkpoints": checkpoints, "budget": dict(LEVEL_BUDGETS[level]), "git": {"sign": None}, "keep_cuts": settings.DEFAULTS["keep_cuts"],
           "teaching_contract": genre == "explainer"}     # minutes; `studio stage` reports against it
    if genre == "motion":
        cfg["loop"] = True            # the last frame equals the first; `studio check` verifies the seam
    if genre == "pixel":
        cfg["pixel"] = {"grid": [320, 180], "palette": ["#0f1318", "#e6ebf0", "#8fd3ff", "#f2a93b", "#e4715f", "#2b333c"]}
    if source:
        cfg["source"] = source_record(source)
    if duration and genre != "footage":
        cfg["duration"] = float(duration)
    (video / "video.json").write_text(json.dumps(cfg, indent=1) + "\n")
    (video / "layout.json").write_text(json.dumps(DEFAULT_LAYOUT, indent=1) + "\n")
    if genre == "footage":
        # An edit, not a script: recordings go in with `studio ingest`, the edit list with `studio edit`.
        (video / "footage").mkdir(exist_ok=True)
        scenes = TEMPLATES / "footage" / "scenes"
    elif duration:
        # A piece with no narration (a motion reel, a product film): one clip of video.json's
        # duration; scenes time themselves, and captions are none.
        scenes = TEMPLATES / (genre if (TEMPLATES / genre).is_dir() else "scenes") / "scenes"
        tl.build(video)
    else:
        nr = json.loads((TEMPLATES / "narration.json").read_text())
        if genre == "explainer" and level == "intro":
            nr["kokoro"]["speed"] = 0.95
            nr["timing"] = {"beat": 0.5, "chapter_hold": 2.0, "chapter_gap": 1.2}
        (video / "narration.json").write_text(json.dumps(nr, indent=1) + "\n")
        script = (TEMPLATES / "SCRIPT.md").read_text().replace("{{Title}}", cfg["title"])
        (video / "SCRIPT.md").write_text(script)
        scenes = TEMPLATES / "scenes"
    if engine == "motion-canvas":
        # Generator scenes; the script and timeline are unchanged. A genre with its own starter gets it.
        mc = TEMPLATES / "motion-canvas"
        scenes = (mc / genre if (mc / genre).is_dir() else mc) / "scenes"
    elif engine == "live":
        # Plain JS scenes, one per chapter, drawn from t; chapters without one show their boards.
        scenes = TEMPLATES / "live" / "scenes"
    for f in scenes.iterdir():
        shutil.copyfile(f, video / "scenes" / f.name)
    (video / ".gitignore").write_text(GITIGNORE)
    learner = studio_home() / "learner.md"
    if not learner.exists():
        learner.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(TEMPLATES / "learner.md", learner)
    preferences.snapshot(video)
    checkpoint.init(video)
    return video, learner


def main(args):
    source_cfg = settings.raw(args.from_video) if args.from_video else {}
    # An explainer defaults to the live engine (instant reload on the desk); other genres, and code
    # explainers that need the Remotion code components, name their engine.
    args.engine = args.engine or source_cfg.get("engine") or ("live" if args.genre == "explainer" and not args.duration else "remotion")
    args.level = args.level or source_cfg.get("level", "intro")
    args.tone = getattr(args, "tone", None) or source_cfg.get("tone", "plain")
    video, learner = create(args.name, args.dir, args.title, args.drive, args.source, args.genre, args.duration, args.engine,
                            getattr(args, "level", "intro"), getattr(args, "checkpoints", None) or "few",
                            getattr(args, "mode", None) or ("interactive" if getattr(args, "checkpoints", None) == "many" else "background"),
                            args.tone)
    if args.from_video:
        copied = preferences.inherit(video, args.from_video, args.include)
        cfg = json.loads((video / "video.json").read_text())
        cfg["series_of"] = str(Path(args.from_video).resolve())
        if not args.source and source_cfg.get("source"):
            cfg["source"] = source_cfg["source"]
        (video / "video.json").write_text(json.dumps(cfg, indent=1) + "\n")
        print("series files copied: " + (", ".join(copied) or "look and pronunciation only"))
    print(f"new video at {video}\nlearner model: {learner}")
    return 0


# What a variant keeps from its source: the evidence, the assets and the look. Everything that
# depends on the words (script, narration, timeline, cuts) is rewritten for the new audience.
KEEP = ["data", "sims", "assets", "scenes", "captures", "layout.json", "narration.json", "lexicon.json"]


def variant(source, name, directory=None, learner=None, vocabulary=None, title=None):
    """A sibling video for another audience: same evidence, assets and look, new script."""
    source = Path(source).resolve()
    scfg = settings.raw(source)
    video = target(name, directory)
    video.mkdir(parents=True, exist_ok=True)
    for rel in KEEP:
        src = source / rel
        if src.is_dir():
            shutil.copytree(src, video / rel, ignore=shutil.ignore_patterns(".cache", "__pycache__"))
        elif src.exists():
            shutil.copyfile(src, video / rel)
    (video / "research").mkdir(exist_ok=True)
    # The narrative is the source's, to be revised for the new audience; reviews and cuts are not carried over.
    if (source / "research" / "narrative.md").exists():
        shutil.copyfile(source / "research" / "narrative.md", video / "research" / "narrative_source.md")
    script = (source / "SCRIPT.md").read_text() if (source / "SCRIPT.md").exists() else ""
    script = script.split("\n## Review log", 1)[0].rstrip() + "\n\n## Review log\n\n- Variant of " + source.name + \
        ": rewrite the Argument, Chain, Script and vocabulary for the new audience; keep the Evidence rows.\n"
    script = re.sub(r"^Status:.*$", "Status: draft variant, before review round 1", script, count=1, flags=re.M)
    (video / "SCRIPT.md").write_text(script)
    cfg = {**scfg, "title": title or default_title(name), "version": "v1", "variant_of": str(source)}
    if learner:
        cfg["learner"] = str(Path(learner).expanduser().resolve())
    if vocabulary:
        cfg["vocabulary"] = str(Path(vocabulary).expanduser().resolve())
    (video / "video.json").write_text(json.dumps(cfg, indent=1) + "\n")
    (video / ".gitignore").write_text(GITIGNORE)
    n = video / "narration.json"
    if n.exists():
        nr = json.loads(n.read_text())
        for key in ("holds", "spoken_by_id", "phonemes_by_id", "accepted"):
            nr.pop(key, None)
        n.write_text(json.dumps(nr, indent=1) + "\n")
    checkpoint.init(video)
    return video


def main_variant(args):
    v = variant(args.source, args.name, args.dir, args.learner, args.vocabulary, args.title)
    print(f"variant at {v}: evidence, assets and scenes copied; rewrite SCRIPT.md for the new audience, then narrate")
    return 0


# What a fork leaves behind. Anywhere: repositories, caches and package folders. At these paths:
# outputs, and what is the source's alone (its stage log, pending requests, handoff, the builder's
# scratch, its review rounds) or names its cuts (the desk's notes, frame-review bundles). Cuts stay
# behind whole: publish, sheets, frame review and the next cut read the stills and video beside a
# record, so a record without them is a broken cut.
FORK_SKIP_NAMES = {".git", ".cache", "node_modules", ".venv", "__pycache__"}
FORK_SKIP_PATHS = {"out", "cuts", "review", "research/frame_review", "research/motion_review", "research/timing.jsonl",
                   "research/requests.md", "research/handoff.md", "research/reviews/rounds.jsonl", ".studio/work"}


def fork(source, name, directory=None, title=None):
    """A copy of a video's sources under a new title, with a history of its own: a fresh stage log
    that starts at a forked_from mark, no cuts, notes, requests or owner. The tree is walked and
    copied file by file, pruning what is left behind before entering it, so a large cache is never
    read."""
    source = Path(source).resolve()
    video = (Path(directory).expanduser() if directory else studio_home() / name).resolve()
    # a fork into a folder that holds the source made that folder (STUDIO_HOME, once) a video
    # repository, so every later video landed inside it and a commit swept up its siblings
    if video == source or source in video.parents or video in source.parents:
        raise SystemExit(f"fork into a new folder of its own: {video} is {source.name}, inside it, or holds it")
    if (video / "video.json").exists():
        raise SystemExit(f"{video} already holds a video")
    if video.is_dir() and any(video.iterdir()):
        raise SystemExit(f"{video} is not empty; fork into a new folder")
    skip = lambda rel: rel.name in FORK_SKIP_NAMES or rel.as_posix() in FORK_SKIP_PATHS
    for root, dirs, files in os.walk(source):
        rel = Path(root).relative_to(source)
        (video / rel).mkdir(parents=True, exist_ok=True)
        dirs[:] = [d for d in dirs if not skip(rel / d)]
        links = [d for d in dirs if (Path(root) / d).is_symlink()]      # not walked: copied as links
        for f in files + links:
            if not skip(rel / f):
                shutil.copy2(Path(root) / f, video / rel / f, follow_symlinks=False)
    origin = source_record(source)
    cfg = {**settings.raw(source), "title": title or default_title(name), "version": "v1",
           "forked_from": origin}
    (video / "video.json").write_text(json.dumps(cfg, indent=1) + "\n")
    now = time.time()
    mark = {"stage": "forked_from", "t": now, "at": datetime.fromtimestamp(now).isoformat(timespec="seconds"),
            "kind": "fork", "source": origin["path"], **({"commit": origin["commit"]} if "commit" in origin else {})}
    (video / "research").mkdir(exist_ok=True)
    (video / "research" / "timing.jsonl").write_text(json.dumps(mark) + "\n")
    checkpoint.init(video)
    return video


def main_fork(args):
    v = fork(args.source, args.name, args.dir, args.title)
    pinned = " The pinned kit came without its packages: `.studio/bin/studio doctor --fetch`." if (v / ".studio" / "PIN").exists() else ""
    print(f"fork at {v}: sources copied, its stage log starts at the fork; cuts, notes and caches stay with "
          f"{Path(args.source).resolve().name}, so the first cut renders every clip.{pinned}")
    return 0
