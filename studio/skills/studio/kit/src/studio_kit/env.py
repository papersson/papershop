"""Where the kit's pieces live, and which headless browser the engines use.

The plugin and a workspace copy share one layout under a root: `bin/studio`, `kit/`, `engines/<name>/`.
"""
import os
import platform
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# Installed Chrome, in the order tried: the fallback when the engine's own headless shell can't be
# downloaded (a corporate proxy that blocks it still allows the managed Chrome install).
CHROME_PATHS = {
    "Darwin": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ],
    "Linux": ["google-chrome-stable", "google-chrome", "chromium", "chromium-browser"],
}


def studio_home():
    """Where `studio new` puts videos, and the learner model and house defaults live."""
    return Path(os.environ.get("STUDIO_HOME", "~/studio")).expanduser()


def engine_dir(name):
    return ROOT / "engines" / name


def headless_shell(engine="remotion"):
    """The engine's downloaded Chrome headless shell, if `studio doctor --fetch` has fetched it."""
    found = sorted((engine_dir(engine) / "node_modules" / ".remotion").glob(
        "chrome-headless-shell/*/*/chrome-headless-shell"))
    return str(found[0]) if found else None


def resolve_browser(environ=None, system=None, exists=None, which=None, shell=None):
    """(path, source) of the browser to use: STUDIO_BROWSER, then the engine's headless shell
    (measured 4x faster per frame than a full Chrome in headless mode), then an installed Chrome
    (or, on Linux, Nix's Chromium on PATH), else (None, "engine download")."""
    environ = os.environ if environ is None else environ
    system = system or platform.system()
    exists = exists or (lambda p: Path(p).is_file())
    which = which or shutil.which
    shell = headless_shell() if shell is None else shell
    if environ.get("STUDIO_BROWSER"):
        return environ["STUDIO_BROWSER"], "STUDIO_BROWSER"
    if shell:
        return shell, "engine headless shell"
    for candidate in CHROME_PATHS.get(system, []):
        if "/" in candidate:
            path = os.path.expanduser(candidate)
            if exists(path):
                return path, "installed Chrome"
        elif which(candidate):
            return which(candidate), f"{candidate} on PATH"
    return None, "engine download"
