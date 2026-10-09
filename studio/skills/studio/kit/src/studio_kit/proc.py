"""Every external program the kit runs starts here, with stdin closed.

A child that inherits stdin shares the agent's: ffmpeg reads it for keystrokes, so in a background
run it can hang or swallow input meant for something else. Stdin is /dev/null unless a caller feeds it.
"""
import functools
import json
import shutil
import subprocess
# Re-exported, so no other kit module needs to import subprocess.
from subprocess import PIPE, CalledProcessError, SubprocessError, TimeoutExpired


def _closed(kw):
    if "input" not in kw and "stdin" not in kw:
        kw["stdin"] = subprocess.DEVNULL
    return kw


def run(argv, **kw):
    return subprocess.run(argv, **_closed(kw))


def popen(argv, **kw):
    return subprocess.Popen(argv, **_closed(kw))


@functools.cache
def tool(name):
    """The absolute path of an external program, or a stop that names it."""
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"{name} is not on PATH; run `studio doctor` for the fix")
    return path


def ffmpeg(*args, check=True, **kw):
    """ffmpeg quietly, overwriting its output."""
    return run([tool("ffmpeg"), "-v", "error", "-y", *map(str, args)], check=check, **kw)


def ffprobe(path, *args):
    """ffprobe's JSON report on a media file."""
    r = run([tool("ffprobe"), "-v", "error", *args, "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)
