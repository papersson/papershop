"""`studio init VIDEO`: pin the kit a video is made with.

Copies the plugin's bin/, kit/, engines/, prompts/, flake and lock files into VIDEO/.studio/, and
`bin/studio` runs that copy whenever it is given this video's folder. A plugin update then can't
change how an old video renders: the tutor guaranteed this by copying its kit into every project,
and a byte-identical rebuild is the reason (the day its narration engine grew a second mode, the old
mode's timings were verified identical before merging).

The copy is committed; its node_modules, Python environment and caches are not, and come from
`.studio/bin/studio doctor --fetch` (the lock files are copied, so they install the same versions).
`studio init --update VIDEO` replaces the copy's sources with the plugin's current ones.
"""
import json
import shutil
from pathlib import Path

from .env import ROOT

# What is copied, relative to the skill folder (ROOT) and the plugin folder above it.
FROM_SKILL = ["bin", "prompts", "kit/src", "kit/pyproject.toml", "kit/uv.lock", "kit/.python-version",
              "engines/remotion/cli.mjs", "engines/remotion/src", "engines/remotion/package.json",
              "engines/remotion/package-lock.json", "engines/remotion/tsconfig.json",
              "engines/motion-canvas/cli.mjs", "engines/motion-canvas/render.html", "engines/motion-canvas/src",
              "engines/motion-canvas/package.json", "engines/motion-canvas/package-lock.json", "engines/motion-canvas/tsconfig.json"]
FROM_PLUGIN = ["flake.nix", "flake.lock", "shell.nix"]
GITIGNORE = ".cache/\nkit/.venv/\nengines/*/node_modules/\n__pycache__/\n"


def plugin_root():
    return ROOT.parent.parent


def plugin_version():
    f = plugin_root() / ".claude-plugin" / "plugin.json"
    return json.loads(f.read_text())["version"] if f.exists() else "unknown"


def copy(src, dst):
    if src.is_dir():
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "node_modules", ".venv", ".cache"), dirs_exist_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        dst.chmod(src.stat().st_mode)


def init(video, update=False):
    video = Path(video).resolve()
    if not (video / "video.json").exists():
        raise SystemExit(f"{video} is not a video folder (no video.json)")
    pin = video / ".studio"
    if pin.exists() and not update:
        raise SystemExit(f"{pin} exists: pinned to studio {(pin / 'PIN').read_text().split()[0] if (pin / 'PIN').exists() else '?'}; "
                         "use --update to replace it with this plugin's current kit")
    if update:
        for rel in FROM_SKILL:
            path = pin / rel
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
    for rel in FROM_SKILL:
        copy(ROOT / rel, pin / rel)
    for rel in FROM_PLUGIN:
        copy(plugin_root() / rel, pin / rel)
    (pin / ".gitignore").write_text(GITIGNORE)
    (pin / "PIN").write_text(f"{plugin_version()} pinned from {ROOT}\n")
    return pin


def main(args):
    pin = init(args.video, args.update)
    print(f"pinned studio {plugin_version()} to {pin}\n"
          f"install its packages with: {pin}/bin/studio doctor --fetch\n"
          "from now on `studio` commands given this video's folder run that copy")
    return 0
