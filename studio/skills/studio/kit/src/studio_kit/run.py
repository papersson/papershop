"""`studio run VIDEO SCRIPT [ARGS…]`: run a builder's script through the kit's own entry point.

Builders ran their helper scripts by path, and to get one past the macOS sandbox they put "claude"
in its path. Through `bin/studio`, which is already allowed, a script runs with the kit's Python
(the kit importable), in the video's folder, with STUDIO_VIDEO and STUDIO_WORK set, `studio` on
PATH as this kit's own entry point, and stdin closed. Its output streams, SIGTERM and SIGHUP reach
it, its arguments pass verbatim (a `--` included) and its exit status is the command's. A script
outside the video is refused unless --allow-outside, so the helpers a build depends on stay in the
video (sims/, .studio/work). `.mjs` and `.js` run with the engines' node; engine packages are not
on its import path.
"""
import os
import signal
import sys
from pathlib import Path

from . import proc, workspace
from .env import ROOT

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
    # `studio` inside the script is this kit's entry point: the video's pinned copy when it has one,
    # and without STUDIO_PINNED, so the copy still routes a call that names another video.
    env = {k: v for k, v in os.environ.items() if k != "STUDIO_PINNED"}
    env |= {"STUDIO_VIDEO": str(video), "STUDIO_WORK": str(workspace.scratch(video)),
            "PATH": os.pathsep.join([str(ROOT / "bin"), env.get("PATH", "")])}
    child = proc.popen([*argv, *args], cwd=video, env=env)
    forward = lambda sig, _: child.send_signal(sig)       # a stopped `studio run` stops its script
    old = {sig: signal.signal(sig, forward) for sig in (signal.SIGTERM, signal.SIGHUP)}
    try:
        code = child.wait()
    finally:
        for sig, handler in old.items():
            signal.signal(sig, handler)
    return code if code >= 0 else 128 - code          # killed by a signal: the shell's convention


def main(args):
    return run(args.video, args.script, args.args, args.allow_outside)
