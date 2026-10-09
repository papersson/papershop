"""`studio doctor`: check every layer of the environment and print the exact fix for what fails.

Run at setup, and first whenever a command fails with an environment error.
"""
import re
import os
import json
import importlib.util
from pathlib import Path
from importlib.metadata import version, PackageNotFoundError
import shutil
import sys
import tempfile
import urllib.request

from . import proc
from .env import ROOT, engine_dir, resolve_browser

OK, WARN, FAIL, SKIP = "ok", "warn", "FAIL", "skip"

NIX_FIX = "run through bin/studio (it loads `nix develop .#studio`), or install it"

HOSTS = ["https://registry.npmjs.org/", "https://huggingface.co/", "https://cache.nixos.org/", "https://raw.githubusercontent.com/explosion/spacy-models/master/compatibility.json"]


def _version(cmd):
    try:
        out = proc.run(cmd, capture_output=True, text=True, timeout=20)
    except (OSError, proc.TimeoutExpired):
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


ENGINE_MARKER = {"remotion": "remotion", "motion-canvas": "@motion-canvas/core", "live": "playwright-core"}


def check_engine(name):
    d = engine_dir(name)
    if not (d / "node_modules" / ENGINE_MARKER[name]).is_dir():
        return FAIL if name == "remotion" else WARN, f"engine {name}", "node packages not installed", f"studio doctor --fetch{'' if name == 'remotion' else ' --engine ' + name}"
    if not (d / "node_modules" / "@fontsource" / "ibm-plex-mono").is_dir():
        return FAIL, f"engine {name}", "bundled fonts missing", "studio doctor --fetch"
    return OK, f"engine {name}", str(d), ""


def check_browser():
    path, source = resolve_browser()
    if path is None:
        return WARN, "browser", "none installed; the engine downloads its headless shell on first use", \
            "install Chrome or set STUDIO_BROWSER (a proxy may block the download)"
    try:
        run = proc.run([path, "--headless=new", "--disable-gpu", "--dump-dom", "about:blank"],
                       capture_output=True, text=True, timeout=30)
    except (OSError, proc.TimeoutExpired) as e:
        return FAIL, "browser", f"{path} ({source}) did not start: {e}", "set STUDIO_BROWSER to a working Chrome"
    if "<html" not in run.stdout:
        return FAIL, "browser", f"{path} ({source}) returned no page", "set STUDIO_BROWSER to a working Chrome"
    return OK, "browser", f"{path} ({source})", ""


LAUNCH_SCENE = "export default function draw(c) { c.S.text('probe', c.W / 2, c.H / 2, 'studio doctor', { size: 48 }) }\n"


def check_launch(timeout=60):
    """A one-frame still through the live engine's own command, in a throwaway video: the browser
    starting the way a cut starts it, which `--dump-dom` does not show (a sandbox can allow one and
    refuse the other)."""
    if not (engine_dir("live") / "node_modules" / ENGINE_MARKER["live"]).is_dir() or not shutil.which("node"):
        return SKIP, "browser launch", "skipped: the live engine or node is not installed", ""
    from .engine import LAUNCH_HINT, Engine, launch_hint
    with tempfile.TemporaryDirectory(prefix="studio-doctor-") as tmp:
        video = Path(tmp)
        (video / "scenes").mkdir()
        (video / "scenes" / "probe.js").write_text(LAUNCH_SCENE)
        (video / "video.json").write_text(json.dumps({"engine": "live"}))
        (video / "timeline.json").write_text(json.dumps({"version": 1, "fps": 30, "duration": 1.0, "cues": {}, "tracks": {
            "scene": [{"id": "probe", "engine": "live", "title": "probe", "start": 0.0, "end": 1.0}],
            "narration": [], "captions": [], "audio": []}}))
        engine = Engine(video, "live")
        cmd = engine._command("still", "--clip", "probe", "--t", "0.5", "--out", str(video / "probe.png"))
        try:
            run = proc.run(cmd, capture_output=True, text=True, timeout=timeout)
        except (OSError, proc.TimeoutExpired) as e:
            return FAIL, "browser launch", f"the live engine's still did not finish: {e}", LAUNCH_HINT
        if run.returncode or not (video / "probe.png").is_file():
            cause = (run.stderr.strip() or run.stdout.strip()).splitlines()[-1:] or ["no output"]
            return FAIL, "browser launch", f"the live engine could not render a still: {cause[0][:300]}", \
                launch_hint(run.stderr) or "`studio still VIDEO CLIP T --out PNG` on a live video prints the engine's full error"
    return OK, "browser launch", "the live engine rendered a still", ""


def check_host(url):
    try:
        urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=10)
        return OK, f"host {url}", "reachable", ""
    except urllib.error.HTTPError as e:
        return WARN, f"host {url}", f"HTTP {e.code}: reachable but access failed", \
            "for the spaCy model: configure a wheel mirror/index and run studio doctor --fetch --extra kokoro"
    except OSError as e:
        return WARN, f"host {url}", f"unreachable ({e})", "allowlist it, or prefetch on a machine that can reach it"


def fetch(engines=("remotion",), extras=()):
    """Install what is downloaded rather than pinned in the flake: each engine's node packages, and
    any optional Python extras (e.g. `align`). Inexact, so extras installed earlier stay."""
    for name in engines:
        proc.run(["npm", "ci", "--no-audit", "--no-fund"], cwd=engine_dir(name), check=True)
        if name != "remotion":
            continue           # every engine uses the browser Remotion's renderer downloads
        # The headless shell; a blocked download is not fatal, the installed Chrome still works.
        get = proc.run(["node", "-e", "import('@remotion/renderer').then(r => r.ensureBrowser())"],
                       cwd=engine_dir(name))
        if get.returncode != 0:
            print("warn: the headless shell did not download; falling back to an installed Chrome")
    if extras:
        cmd = ["uv", "sync", "--quiet", "--frozen", "--inexact", "--project", str(ROOT / "kit")]
        proc.run(cmd + [a for e in extras for a in ("--extra", e)], check=True)
        if "kokoro" in extras:
            install_spacy_model()


EXTRAS = {"audio": ("numpy", "soundfile", "num2words"),
          "align": ("numpy", "soundfile", "num2words", "faster_whisper"),
          "kokoro": ("numpy", "soundfile", "num2words", "kokoro", "misaki", "en_core_web_sm")}


def repair(extra):
    return f"{ROOT / 'bin/studio'} doctor --fetch --extra {extra}"


def required(video):
    p = Path(video) / "narration.json"
    if not p.exists():
        return ()
    cfg = json.loads(p.read_text())
    return ("kokoro" if cfg.get("engine", "kokoro") == "kokoro" else "audio", "align")


def extra_checks(extras=()):
    rows = []
    for extra in dict.fromkeys(extras):
        if extra not in EXTRAS:
            raise SystemExit(f"unknown extra {extra}")
        missing = [m for m in EXTRAS[extra] if importlib.util.find_spec(m) is None]
        if extra == "kokoro" and "en_core_web_sm" not in missing:
            try:
                version("en-core-web-sm")
            except PackageNotFoundError:
                missing.append("en_core_web_sm")
        rows.append((FAIL if missing else OK, f"extra {extra}",
                     "missing: " + ", ".join(missing) if missing else "installed", repair(extra)))
    return rows


def require_extra(extra):
    bad = [r for r in extra_checks([extra]) if r[0] == FAIL]
    if bad:
        raise SystemExit(f"{bad[0][2]}; run `{bad[0][3]}` before narration (no model download during synthesis)")


def install_spacy_model():
    # spaCy and its language model share a major/minor compatibility family.
    probe = proc.run([str(ROOT / "kit/.venv/bin/python"), "-c",
                      "from importlib.metadata import version; print('.'.join(version('spacy').split('.')[:2]))"],
                     capture_output=True, text=True, check=True)
    family = probe.stdout.strip()
    if not re.fullmatch(r"\d+\.\d+", family):
        raise SystemExit("could not determine the installed spaCy model compatibility family")
    env = dict(os.environ)
    if not env.get("UV_INDEX_URL") and env.get("PIP_INDEX_URL"):
        env["UV_INDEX_URL"] = env["PIP_INDEX_URL"]
    cmd = ["uv", "pip", "install", "--python", str(ROOT / "kit/.venv/bin/python"),
           f"en-core-web-sm~={family}.0"]
    r = proc.run(cmd, env=env, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("spaCy model wheel unavailable through the configured index. Supply a compatible "
                         "en-core-web-sm wheel on UV_INDEX_URL/PIP_INDEX_URL, then rerun " + repair("kokoro") +
                         ". No GitHub fallback was attempted.")


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
        check_engine("motion-canvas"),
        check_engine("live"),
        check_browser(),
        check_launch(),
    ]
    if net:
        rows += [check_host(u) for u in HOSTS]
    return rows


def main(args):
    if args.fetch:
        fetch(engines=tuple(dict.fromkeys(("remotion", *args.engine))), extras=args.extra)
    extras = tuple(dict.fromkeys([*args.extra, *(required(args.video) if args.video else EXTRAS)]))
    rows = checks(net=args.net) + extra_checks(extras)
    if args.video:
        print("video requires: " + ", ".join(required(args.video)))
    if not args.video and not args.extra:
        rows = [(WARN if level == FAIL and name.startswith("extra ") else level, name, detail, fix)
                for level, name, detail, fix in rows]
    for level, name, detail, fix in rows:
        print(f"{level:4}  {name:22} {detail}" + (f"\n      fix: {fix}" if fix and level != OK else ""))
    failed = [r for r in rows if r[0] == FAIL]
    print(f"\nkit at {ROOT}\n" + ("doctor: FAIL" if failed else "doctor: ok"))
    return 1 if failed else 0
