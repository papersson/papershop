"""`studio run VIDEO SCRIPT [ARGS…]`: run a builder's script through the kit's own entry point.

Builders ran their helper scripts by path, and to get one past the macOS sandbox they put "claude"
in its path. Through `bin/studio`, which is already allowed, a script runs with the kit's Python
(the kit importable), in the video's folder, with STUDIO_VIDEO and STUDIO_WORK set and stdin closed;
its output streams and its exit status is the command's. A script outside the video is refused
unless --allow-outside, so the helpers a build depends on stay in the video (sims/, .studio/work).
`.mjs` and `.js` run with the engines' node; engine packages are not on its import path.
"""
import os
import sys
from pathlib import Path

from . import proc, workspace

PYTHON, NODE = (".py",), (".mjs", ".js")


def script_path(video, script):
    """SCRIPT as given, else relative to the video."""
    p = Path(script).expanduser()
    return (p if p.exists() or p.is_absolute() else Path(video) / p).resolve()


def run(video, script, args=(), allow_outside=False):
    video = Path(video).resolve()
    p = script_path(video, script)
    if not p.is_file():
        raise SystemExit(f"no script at {p}")
    if video not in p.parents and not allow_outside:
        raise SystemExit(f"{p} is outside {video}: keep the helper in the video (sims/ to keep it, .studio/work for "
                         "scratch), or pass --allow-outside")
    if p.suffix in PYTHON:
        argv = [sys.executable, str(p)]
    elif p.suffix in NODE:
        argv = [proc.tool("node"), str(p)]
    else:
        raise SystemExit(f"studio run takes a Python (.py) or node (.mjs, .js) script, not {p.name}")
    workspace.check_owner(video)
    env = {**os.environ, "STUDIO_VIDEO": str(video), "STUDIO_WORK": str(workspace.scratch(video))}
    code = proc.run([*argv, *args], cwd=video, env=env).returncode
    return code if code >= 0 else 128 - code          # killed by a signal: the shell's convention


def main(args):
    return run(args.video, args.script, args.args, args.allow_outside)
