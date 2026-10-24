"""Atomic metadata updates and locks for commands sharing a video folder."""
import contextlib
import fcntl
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as f:
        tmp = Path(f.name)
        json.dump(value, f, indent=1, ensure_ascii=False)
        f.write("\n")
    try:
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def runtime(video):
    video = Path(video).resolve()
    # Only inside a folder that exists: a lock taken on a mistyped path must not create a video there.
    if not video.is_dir():
        raise SystemExit(f"no folder at {video}; `studio new` makes a video")
    p = video / ".cache" / "studio"
    p.mkdir(parents=True, exist_ok=True)
    return p


def scratch(video):
    """VIDEO/.studio/work, made if missing: the builder's scratch files and helper scripts. Inside the
    video, so they survive a restart; ignored by Git, so a helper worth
    keeping moves to sims/."""
    p = Path(video) / ".studio" / "work"
    p.mkdir(parents=True, exist_ok=True)
    return p


def inside(root, relative):
    """Resolve a source path without allowing it to escape its video."""
    root = Path(root).resolve()
    p = (root / relative).resolve()
    if p == root or not p.is_relative_to(root):
        raise SystemExit(f"path escapes its project: {relative}")
    return p


@contextlib.contextmanager
def locked(video, name="metadata"):
    """Wait for an in-flight writer so concurrent metadata updates cannot lose each other."""
    with (runtime(video) / f"{name}.lock").open("a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


@contextlib.contextmanager
def operation(video):
    """Serialize commands that rebuild shared outputs; ownership is a conversation convention."""
    with locked(video, "operation"):
        yield
