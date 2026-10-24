"""Read video.json over the rendering defaults.

The file holds title, engine, destination, layout choices, source provenance, git.sign, keep_cuts,
poster, target_minutes, duration or clips for silent scenes, legend, gl, motion, plates and sound.
The brief holds the audience and the way the story should feel. Sound settings control the shared
room, ducking and presence processing; the narration settings stay in narration.json.
"""
import json
from pathlib import Path

DEFAULTS = {
    "destination": "private-page",
    "engine": "live",
    "keep_cuts": 10,
    "gl": "cpu",
    "motion": "full",
}

CHOICES = {"engine": ("live", "remotion"), "gl": ("cpu", "gpu"), "motion": ("full", "reduced")}


def raw(video):
    """The file as written, or {} when there is none."""
    f = Path(video) / "video.json"
    return json.loads(f.read_text()) if f.exists() else {}


def load(video):
    """video.json over the defaults, with enumerated values checked."""
    cfg = {**DEFAULTS, **raw(video)}
    for key, allowed in CHOICES.items():
        if cfg.get(key) not in allowed:
            raise SystemExit(f"video.json {key} must be one of {', '.join(allowed)} (got {cfg.get(key)!r})")
    return cfg


def update(video, **values):
    """Set keys in video.json, checked as load checks them (and an engine against the engines), and
    write it back in the file's form; returns the file as written."""
    from .engine import ENGINES
    cfg = {**raw(video), **values}
    for key, allowed in CHOICES.items():
        if key in values and values[key] not in allowed:
            raise SystemExit(f"video.json {key} must be one of {', '.join(allowed)} (got {values[key]!r})")
    if "engine" in values and values["engine"] not in ENGINES:
        raise SystemExit(f"video.json engine must be one of {', '.join(ENGINES)} (got {values['engine']!r})")
    (Path(video) / "video.json").write_text(json.dumps(cfg, indent=1) + "\n")
    return cfg


def get(video, key):
    return load(video).get(key)
