"""Where the kit's pieces live, and which headless browser the engines use.

The plugin and a workspace copy share one layout under a root: `bin/studio`, `kit/`, `engines/<name>/`.
"""
import os
import platform
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# Installed Chrome, in the order tried. Chrome, not Chromium, because a corporate proxy that blocks
# the engines' browser download still allows the managed Chrome install.
CHROME_PATHS = {
    "Darwin": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ],
    "Linux": ["google-chrome-stable", "google-chrome", "chromium", "chromium-browser"],
}


def engine_dir(name):
    return ROOT / "engines" / name


def resolve_browser(environ=None, system=None, exists=None, which=None):
    """(path, source) of the browser to use: STUDIO_BROWSER, then an installed Chrome (or, on
    Linux, Nix's Chromium on PATH), else (None, "engine download") so the engine fetches its own."""
    environ = os.environ if environ is None else environ
    system = system or platform.system()
    exists = exists or (lambda p: Path(p).is_file())
    which = which or shutil.which
    if environ.get("STUDIO_BROWSER"):
        return environ["STUDIO_BROWSER"], "STUDIO_BROWSER"
    for candidate in CHROME_PATHS.get(system, []):
        if "/" in candidate:
            path = os.path.expanduser(candidate)
            if exists(path):
                return path, "installed Chrome"
        elif which(candidate):
            return which(candidate), f"{candidate} on PATH"
    return None, "engine download"
