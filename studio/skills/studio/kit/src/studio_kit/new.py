"""`studio new NAME`: a video folder, ready for a script.

The folder goes to --dir, else $STUDIO_HOME/NAME (default ~/studio/NAME), so a video about a repo
does not put renders and caches into that repo; --source records which repo and commit it explains.
STUDIO_HOME also holds learner.md, the learner model every video's student reviewer plays.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

from .env import ROOT
from .review import studio_home
from . import timeline as tl
from .timeline import DEFAULT_LAYOUT

TEMPLATES = ROOT / "templates"
GITIGNORE = ".cache/\naudio/*.wav\ncuts/*/silent.mp4\n"


def source_record(path):
    p = Path(path).expanduser().resolve()
    rec = {"path": str(p)}
    try:
        rec["commit"] = subprocess.run(["git", "-C", str(p), "rev-parse", "HEAD"], capture_output=True, text=True,
                                       check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return rec


def create(name, directory=None, title=None, drive="author", source=None, genre="explainer", duration=None, engine="remotion"):
    video = Path(directory).expanduser().resolve() if directory else studio_home() / name
    if (video / "video.json").exists():
        raise SystemExit(f"{video} already holds a video")
    (video / "scenes").mkdir(parents=True, exist_ok=True)
    (video / "research").mkdir(exist_ok=True)
    cfg = {"title": title or name.replace("-", " ").capitalize(), "version": "v1", "genre": genre,
           "drive": drive, "destination": "private-page", "engine": engine, "poster": None,
           "budget": {"first_cut": 60, "round": 10}}     # minutes; `studio stage` reports against it
    if genre == "motion":
        cfg["loop"] = True            # the last frame equals the first; `studio check` verifies the seam
    if genre == "pixel":
        cfg["pixel"] = {"grid": [320, 180], "palette": ["#0f1318", "#e6ebf0", "#8fd3ff", "#f2a93b", "#e4715f", "#2b333c"]}
    if source:
        cfg["source"] = source_record(source)
    (video / "video.json").write_text(json.dumps(cfg, indent=1) + "\n")
    (video / "layout.json").write_text(json.dumps(DEFAULT_LAYOUT, indent=1) + "\n")
    if genre == "footage":
        # An edit, not a script: recordings go in with `studio ingest`, the edit list with `studio edit`.
        (video / "footage").mkdir(exist_ok=True)
        scenes = TEMPLATES / "footage" / "scenes"
    elif duration:
        # A piece with no narration (a motion reel, a product film): one clip of this length; scenes
        # time themselves, and captions are none.
        scenes = TEMPLATES / (genre if (TEMPLATES / genre).is_dir() else "scenes") / "scenes"
        tl.save(video, {"version": 1, "fps": tl.DEFAULT_LAYOUT["fps"], "duration": float(duration), "cues": {},
                        "tracks": {"scene": [{"id": "s1", "engine": "remotion", "title": cfg["title"], "start": 0.0, "end": float(duration)}],
                                   "narration": [], "captions": [], "audio": []}})
    else:
        shutil.copyfile(TEMPLATES / "narration.json", video / "narration.json")
        script = (TEMPLATES / "SCRIPT.md").read_text().replace("{{Title}}", cfg["title"])
        (video / "SCRIPT.md").write_text(script)
        scenes = TEMPLATES / "scenes"
    if engine == "motion-canvas":
        # Generator scenes; the script and timeline are unchanged. A genre with its own starter gets it.
        mc = TEMPLATES / "motion-canvas"
        scenes = (mc / genre if (mc / genre).is_dir() else mc) / "scenes"
    for f in scenes.iterdir():
        shutil.copyfile(f, video / "scenes" / f.name)
    (video / ".gitignore").write_text(GITIGNORE)
    learner = studio_home() / "learner.md"
    if not learner.exists():
        learner.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(TEMPLATES / "learner.md", learner)
    return video, learner


def main(args):
    video, learner = create(args.name, args.dir, args.title, args.drive, args.source, args.genre, args.duration, args.engine)
    print(f"new video at {video}\nlearner model: {learner}")
    return 0


# What a variant keeps from its source: the evidence, the assets and the look. Everything that
# depends on the words (script, narration, timeline, cuts) is rewritten for the new audience.
KEEP = ["data", "sims", "assets", "scenes", "captures", "layout.json", "narration.json"]


def variant(source, name, directory=None, learner=None, vocabulary=None, title=None):
    """A sibling video for another audience: same evidence, assets and look, new script."""
    source = Path(source).resolve()
    scfg = json.loads((source / "video.json").read_text())
    video = Path(directory).expanduser().resolve() if directory else studio_home() / name
    if (video / "video.json").exists():
        raise SystemExit(f"{video} already holds a video")
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
    cfg = {**scfg, "title": title or name.replace("-", " ").capitalize(), "version": "v1", "variant_of": str(source)}
    if learner:
        cfg["learner"] = str(Path(learner).expanduser().resolve())
    if vocabulary:
        cfg["vocabulary"] = str(Path(vocabulary).expanduser().resolve())
    (video / "video.json").write_text(json.dumps(cfg, indent=1) + "\n")
    (video / ".gitignore").write_text(GITIGNORE)
    return video


def main_variant(args):
    v = variant(args.source, args.name, args.dir, args.learner, args.vocabulary, args.title)
    print(f"variant at {v}: evidence, assets and scenes copied; rewrite SCRIPT.md for the new audience, then narrate")
    return 0
