"""`studio doctor`: check every layer of the environment and print the exact fix for what fails.

Run at setup, and first whenever a command fails with an environment error.
"""
import re
import shutil
import subprocess
import sys
import urllib.request

from .env import ROOT, engine_dir, resolve_browser

OK, WARN, FAIL = "ok", "warn", "FAIL"

NIX_FIX = "run through bin/studio (it loads `nix develop .#studio`), or install it"

HOSTS = ["https://registry.npmjs.org/", "https://huggingface.co/", "https://cache.nixos.org/"]


def _version(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r"(\d+)\.(\d+)", out.stdout + out.stderr)
    return (int(m.group(1)), int(m.group(2))) if m else None


def check_tool(name, cmd, minimum=None, level=FAIL, why=""):
    if not shutil.which(cmd[0]):
        return level, name, f"not on PATH{why}", NIX_FIX
    if minimum:
        v = _version(cmd)
        if v is None or v < minimum:
            return level, name, f"version {v} is below {minimum}", NIX_FIX
        return OK, name, ".".join(map(str, v)), ""
    return OK, name, shutil.which(cmd[0]), ""


def check_engine(name):
    d = engine_dir(name)
    if not (d / "node_modules" / "remotion").is_dir():
        return FAIL, f"engine {name}", "node packages not installed", "studio doctor --fetch"
    if not (d / "node_modules" / "@fontsource" / "ibm-plex-mono").is_dir():
        return FAIL, f"engine {name}", "bundled fonts missing", "studio doctor --fetch"
    return OK, f"engine {name}", str(d), ""


def check_browser():
    path, source = resolve_browser()
    if path is None:
        return WARN, "browser", "none installed; the engine downloads its headless shell on first use", \
            "install Chrome or set STUDIO_BROWSER (a proxy may block the download)"
    try:
        run = subprocess.run([path, "--headless=new", "--disable-gpu", "--dump-dom", "about:blank"],
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        return FAIL, "browser", f"{path} ({source}) did not start: {e}", "set STUDIO_BROWSER to a working Chrome"
    if "<html" not in run.stdout:
        return FAIL, "browser", f"{path} ({source}) returned no page", "set STUDIO_BROWSER to a working Chrome"
    return OK, "browser", f"{path} ({source})", ""


def check_host(url):
    try:
        urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=10)
        return OK, f"host {url}", "reachable", ""
    except urllib.error.HTTPError:
        return OK, f"host {url}", "reachable", ""       # an error status still proves the route
    except OSError as e:
        return WARN, f"host {url}", f"unreachable ({e})", "allowlist it, or prefetch on a machine that can reach it"


def fetch(engines=("remotion",), extras=()):
    """Install what is downloaded rather than pinned in the flake: each engine's node packages, and
    any optional Python extras (e.g. `align`). Inexact, so extras installed earlier stay."""
    for name in engines:
        subprocess.run(["npm", "ci", "--no-audit", "--no-fund"], cwd=engine_dir(name), check=True)
    if extras:
        cmd = ["uv", "sync", "--quiet", "--frozen", "--inexact", "--project", str(ROOT / "kit")]
        subprocess.run(cmd + [a for e in extras for a in ("--extra", e)], check=True)


def checks(net=False):
    rows = [
        (OK, "python", f"{sys.version_info.major}.{sys.version_info.minor}", "")
        if sys.version_info >= (3, 11) else (FAIL, "python", sys.version.split()[0], NIX_FIX),
        check_tool("node", ["node", "--version"], (22, 0)),
        check_tool("npm", ["npm", "--version"]),
        check_tool("ffmpeg", ["ffmpeg", "-version"], (6, 0)),
        check_tool("ffprobe", ["ffprobe", "-version"], (6, 0)),
        check_tool("sox", ["sox", "--version"], level=WARN, why=" (needed for the audio finish)"),
        check_tool("uv", ["uv", "--version"]),
        check_engine("remotion"),
        check_browser(),
    ]
    if net:
        rows += [check_host(u) for u in HOSTS]
    return rows


def main(args):
    if args.fetch:
        fetch(extras=args.extra)
    rows = checks(net=args.net)
    for level, name, detail, fix in rows:
        print(f"{level:4}  {name:22} {detail}" + (f"\n      fix: {fix}" if fix and level != OK else ""))
    failed = [r for r in rows if r[0] == FAIL]
    print(f"\nkit at {ROOT}\n" + ("doctor: FAIL" if failed else "doctor: ok"))
    return 1 if failed else 0
