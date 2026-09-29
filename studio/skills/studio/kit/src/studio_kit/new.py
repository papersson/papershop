"""`studio new NAME`: a video folder, ready for a script.

The folder goes to --dir, else $STUDIO_HOME/NAME (default ~/studio/NAME), so a video about a repo
does not put renders and caches into that repo; --source records which repo and commit it explains.
STUDIO_HOME also holds learner.md, the learner model every video's student reviewer plays.
"""
import json
import shutil
import subprocess
from pathlib import Path

from .env import ROOT
from .review import studio_home
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


def create(name, directory=None, title=None, drive="author", source=None):
    video = Path(directory).expanduser().resolve() if directory else studio_home() / name
    if (video / "video.json").exists():
        raise SystemExit(f"{video} already holds a video")
    (video / "scenes").mkdir(parents=True, exist_ok=True)
    (video / "research").mkdir(exist_ok=True)
    cfg = {"title": title or name.replace("-", " ").capitalize(), "version": "v1", "genre": "explainer",
           "drive": drive, "destination": "private-page", "engine": "remotion", "poster": None}
    if source:
        cfg["source"] = source_record(source)
    (video / "video.json").write_text(json.dumps(cfg, indent=1) + "\n")
    (video / "layout.json").write_text(json.dumps(DEFAULT_LAYOUT, indent=1) + "\n")
    shutil.copyfile(TEMPLATES / "narration.json", video / "narration.json")
    script = (TEMPLATES / "SCRIPT.md").read_text().replace("{{Title}}", cfg["title"])
    (video / "SCRIPT.md").write_text(script)
    for f in (TEMPLATES / "scenes").iterdir():
        shutil.copyfile(f, video / "scenes" / f.name)
    (video / ".gitignore").write_text(GITIGNORE)
    learner = studio_home() / "learner.md"
    if not learner.exists():
        learner.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(TEMPLATES / "learner.md", learner)
    return video, learner


def main(args):
    video, learner = create(args.name, args.dir, args.title, args.drive, args.source)
    print(f"new video at {video}\nlearner model: {learner}")
    return 0
