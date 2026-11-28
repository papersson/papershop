"""Where the kit's pieces live, and which headless browser the engines use.

The plugin and a workspace copy share one layout under a root: `bin/studio`, `kit/`, `engines/<name>/`.
"""
import json
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


def studio_home(root=None):
    """Where the videos, the shared sound cache and the lexicon live: $STUDIO_HOME, else ~/studio, else
    a studio-journey checkout beside the papershop one (a cloud session clones both under one folder
    and has no ~/studio), else ~/studio."""
    if os.environ.get("STUDIO_HOME"):
        return Path(os.environ["STUDIO_HOME"]).expanduser()
    home = Path("~/studio").expanduser()
    sibling = (root or ROOT).parents[2].parent / "studio-journey"
    return sibling if not home.is_dir() and sibling.is_dir() else home


def films_home():
    """Where `studio new` puts a video: STUDIO_HOME/films when that folder exists (a home that keeps
    its films apart from its notes and plans), else STUDIO_HOME itself."""
    films = studio_home() / "films"
    return films if films.is_dir() else studio_home()


def engine_dir(name):
    return ROOT / "engines" / name


def browser_cache():
    return ROOT / ".cache" / "browser"


def headless_shell():
    """The shell fetched by doctor, outside node_modules so npm ci cannot erase it."""
    cache = browser_cache()
    found = list(cache.glob("chromium_headless_shell-*/*/chrome-headless-shell"))
    found += list(cache.glob("chromium_headless_shell-*/*/headless_shell"))
    if found:
        return str(max(found, key=lambda p: p.stat().st_mtime_ns))
    imported = sorted((cache / "imported").glob("*/chrome-headless-shell"))
    return str(imported[0]) if imported else None


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
    if environ is os.environ and machine().get("browser"):
        return os.path.expanduser(machine()["browser"]), "machine.json"
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


def _sysctl(name):
    from . import proc
    return int(proc.run(["sysctl", "-n", name], capture_output=True, text=True).stdout)


def machine():
    """This machine's own render settings, STUDIO_HOME/machine.json, or {}: {"workers": N, "browser":
    PATH, "pin": true}. The kit measures the machine it runs on; this file is for what it cannot
    measure or the owner wants otherwise. It belongs to the machine, never to a video."""
    f = studio_home() / "machine.json"
    try:
        data = json.loads(f.read_text()) if f.is_file() else {}
    except (OSError, ValueError) as e:
        raise SystemExit(f"{f} is not readable JSON: {e}")
    return data if isinstance(data, dict) else {}


def physical_cores():
    """Physical cores, not hardware threads: a software-rendering browser gains nothing from the
    second thread of a core (measured: 30 workers on 20 cores were slower than 20)."""
    try:
        if platform.system() == "Linux":
            seen, phys = set(), None
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                k, _, v = line.partition(":")
                k = k.strip()
                if k == "physical id":
                    phys = v.strip()
                elif k == "core id":
                    seen.add((phys, v.strip()))
            if seen:
                return len(seen)
        elif platform.system() == "Darwin":
            return _sysctl("hw.physicalcpu")
    except (OSError, ValueError):
        pass
    return max(1, (os.cpu_count() or 2) // 2)


WORKER_GB = 2.0       # a render worker's browser and encoder, measured at 1.3 to 1.6 GB at 1080p


def available_gb():
    """Memory free for new work in GB, or None where it can't be read."""
    try:
        if platform.system() == "Linux":
            for line in Path("/proc/meminfo").read_text().splitlines():
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / 1e6
        elif platform.system() == "Darwin":      # no cheap "available" figure: half of what is installed
            return _sysctl("hw.memsize") / 2e9
    except (OSError, ValueError):
        pass
    return None


def render_workers(environ=None):
    """How many browsers render at once: STUDIO_WORKERS, else machine.json's workers, else one per
    physical core, fewer when memory is short. At least 1."""
    environ = os.environ if environ is None else environ
    asked = environ.get("STUDIO_WORKERS") or machine().get("workers")
    if asked:
        return max(1, int(asked))
    n = physical_cores()
    gb = available_gb()
    return max(1, min(n, int(gb / WORKER_GB))) if gb else n


def cpu_sets():
    """The CPU lists of this machine's sockets (NUMA nodes) when machine.json says "pin": true, on
    Linux with taskset and more than one socket; else []. Workers pinned alternately to a socket
    rendered 6% faster on a two-socket machine."""
    if not machine().get("pin") or platform.system() != "Linux" or not shutil.which("taskset"):
        return []
    sets = [f.read_text().strip() for f in sorted(Path("/sys/devices/system/node").glob("node[0-9]*/cpulist"))]
    sets = [s for s in sets if s]
    return sets if len(sets) > 1 else []
