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
import signal
import sys
import tempfile
import urllib.request

from . import proc
from . import settings
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
    fix = f"studio doctor --fetch{'' if name == 'remotion' else ' --engine ' + name}"
    if not (d / "node_modules" / ENGINE_MARKER[name]).is_dir():
        return FAIL if name == "remotion" else WARN, f"engine {name}", "node packages not installed", fix
    if not (d / "node_modules" / "@fontsource" / "ibm-plex-mono").is_dir():
        return FAIL if name == "remotion" else WARN, f"engine {name}", "bundled fonts missing", fix
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


def probe_video(video, gl="cpu"):
    """A throwaway one-chapter live video in an empty folder, for the engine's own commands."""
    video = Path(video)
    (video / "scenes").mkdir()
    (video / "scenes" / "probe.js").write_text(LAUNCH_SCENE)
    (video / "video.json").write_text(json.dumps({"engine": "live", "gl": gl}))
    (video / "timeline.json").write_text(json.dumps({"version": 1, "fps": 30, "duration": 1.0, "cues": {}, "tracks": {
        "scene": [{"id": "probe", "engine": "live", "title": "probe", "start": 0.0, "end": 1.0}],
        "narration": [], "captions": [], "audio": []}}))
    return video


def live_ready():
    return (engine_dir("live") / "node_modules" / ENGINE_MARKER["live"]).is_dir() and shutil.which("node")


def check_launch(timeout=60):
    """A one-frame still through the live engine's own command, in a throwaway video: the browser
    starting the way a cut starts it, which `--dump-dom` does not show (a sandbox can allow one and
    refuse the other)."""
    if not live_ready():
        return SKIP, "browser launch", "skipped: the live engine or node is not installed", ""
    from .engine import LAUNCH_HINT, Engine, launch_hint
    with tempfile.TemporaryDirectory(prefix="studio-doctor-") as tmp:
        video = probe_video(tmp)
        engine = Engine(video, "live")
        cmd = engine._command("still", "--clip", "probe", "--t", "0.5", "--out", str(video / "probe.png"))
        try:     # its own session, so a hung launch is killed with the browser it started
            run = proc.popen(cmd, stdout=proc.PIPE, stderr=proc.PIPE, text=True, start_new_session=True)
        except OSError as e:
            return FAIL, "browser launch", f"the live engine's still did not start: {e}", LAUNCH_HINT
        try:
            out, err = run.communicate(timeout=timeout)
        except proc.TimeoutExpired:
            os.killpg(run.pid, signal.SIGKILL)
            run.communicate()
            return FAIL, "browser launch", f"the live engine's still did not finish in {timeout} s", LAUNCH_HINT
        if run.returncode or not (video / "probe.png").is_file():
            cause = (err.strip() or out.strip()).splitlines()[-1:] or ["no output"]
            return FAIL, "browser launch", f"the live engine could not render a still: {cause[0][:300]}", \
                launch_hint(err) or "`studio still VIDEO CLIP T --out PNG` on a live video prints the engine's full error"
    return OK, "browser launch", "the live engine rendered a still", ""


def check_webgl(gl="cpu", timeout=60):
    """The WebGL renderer the live engine's 3D stage gets on a backend (video.json gl), from the engine's
    own page: SwiftShader for cpu, this machine's GPU for gpu. A browser without WebGL can still draw
    every 2D scene, so a failure here is a warning."""
    name = f"webgl {gl}"
    if not live_ready():
        return SKIP, name, "skipped: the live engine or node is not installed", ""
    if not (engine_dir("live") / "node_modules" / "three").is_dir():
        return WARN, name, "three.js is not installed (3D scenes need it)", "studio doctor --fetch --engine live"
    from .engine import Engine, EngineError
    with tempfile.TemporaryDirectory(prefix="studio-doctor-") as tmp:
        try:
            info = Engine(probe_video(tmp, gl), "live").webgl()
        except (EngineError, OSError) as e:
            return WARN, name, f"no WebGL for the 3D stage: {str(e).strip().splitlines()[-1][:200]}", \
                "2D scenes are unaffected; set STUDIO_BROWSER to a Chrome with WebGL for 3D"
    return OK, name, f"{info['renderer']} (WebGL {info['version'].split()[1]}, {info['samples']}x MSAA, three r{info['three']}, browser {info['browser']})", ""


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
    # An explicit source lets a public install use spaCy's official release wheel. Never silently
    # bypass a configured package mirror when it is unavailable.
    model = os.environ.get("STUDIO_SPACY_MODEL", f"en-core-web-sm~={family}.0")
    cmd = ["uv", "pip", "install", "--python", str(ROOT / "kit/.venv/bin/python"), model]
    r = proc.run(cmd, env=env, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("spaCy model wheel unavailable from the selected source. Supply a compatible "
                         "en-core-web-sm wheel on UV_INDEX_URL/PIP_INDEX_URL, or explicitly set "
                         "STUDIO_SPACY_MODEL to a compatible wheel URL/path (references/setup.md), then rerun " +
                         repair("kokoro") + ". No GitHub fallback was attempted.")
    probe = proc.run([str(ROOT / "kit/.venv/bin/python"), "-c",
                      "import spacy; spacy.load('en_core_web_sm')"], capture_output=True, text=True)
    if probe.returncode:
        raise SystemExit("the installed spaCy model could not load; supply a compatible en-core-web-sm wheel "
                         f"for spaCy {family} (references/setup.md)")


def check_sounds(offline=None):
    """The sound kit's row: optional, so a kit not fetched is a warning; `offline` is why a fetch
    asked for just now was skipped."""
    from . import soundkit
    state, detail = soundkit.check()
    if state == "ok":
        return OK, "sound kit", detail, ""
    return WARN, "sound kit", detail + (f"; skipped the fetch: {offline}" if offline else ""), soundkit.repair()


def _some(files, n=4):
    return ", ".join(files[:n]) + (f" and {len(files) - n} more" if len(files) > n else "")


def check_blender(video=None):
    """Blender, for a video's plates (plates.py): required when video.json names plates, else optional."""
    from . import plates
    needed = bool(video and plates.config(video))
    b = plates.blender()
    if b:
        return OK, "blender", f"{b} (plates render with it)", ""
    return (FAIL if needed else WARN), "blender", ("missing: this video's plates render in Blender" if needed else
                                                   "not installed (optional: plates for realistic hero shots)"), \
        "brew install --cask blender (or set STUDIO_BLENDER to its binary)"


def check_library(video):
    """A video's library sounds: each in assets/ with the digest its row recorded (Git leaves sound
    out, so a fresh clone has rows and no files). None when the video uses none."""
    from .assets import LIBRARY_FILE
    from .fetch import sha256_of
    root = Path(video) / "assets"
    table = root / "provenance.json"
    rows = [r for r in json.loads(table.read_text()) if r["kind"] == "library"] if table.exists() else []
    if not rows:
        return None
    bad = [r["file"] for r in rows if not LIBRARY_FILE.fullmatch(r["file"]) or ".." in r["file"]]
    if bad:
        return FAIL, "library sounds", "rows outside assets/sounds/: " + _some(bad), "fix those rows in assets/provenance.json"
    missing = [r["file"] for r in rows if not (root / r["file"]).is_file()]
    changed = [r["file"] for r in rows if r["file"] not in missing and sha256_of(root / r["file"]) != r["sha256"]]
    if changed:
        return FAIL, "library sounds", f"{len(changed)} of {len(rows)} not the recorded file: " + _some(changed), \
            f"remove them and run `{ROOT / 'bin/studio'} asset restore {video}`"
    if missing:
        return FAIL, "library sounds", f"{len(missing)} of {len(rows)} missing (Git leaves sound out): " + _some(missing), \
            f"{ROOT / 'bin/studio'} asset restore {video} (after `doctor --fetch --sounds` if the kit is not fetched)"
    return OK, "library sounds", f"{len(rows)} in assets/sounds, verified", ""


def check_sound_host(url):
    """A host the sound kit downloads from, with the sound kit's own remedy."""
    level, name, detail, fix = check_host(url)
    return level, name, detail, fix and ("allowlist it, or run `doctor --fetch --sounds` on a machine that can "
                                         "reach it and copy $STUDIO_HOME/cache/sounds/ over")


def system_checks():
    return [
        (OK, "python", f"{sys.version_info.major}.{sys.version_info.minor}", "")
        if sys.version_info >= (3, 11) else (FAIL, "python", sys.version.split()[0], NIX_FIX),
        check_tool("node", ["node", "--version"], (22, 0)),
        check_tool("npm", ["npm", "--version"]),
        check_tool("ffmpeg", ["ffmpeg", "-version"], (6, 0)),
        check_tool("ffprobe", ["ffprobe", "-version"], (6, 0)),
        check_tool("sox", ["sox", "--version"], level=WARN, why=" (needed for the audio finish)"),
        check_tool("uv", ["uv", "--version"]),
    ]


def checks(net=False):
    rows = system_checks() + [
        check_engine("remotion"),
        check_engine("motion-canvas"),
        check_engine("live"),
        check_browser(),
        check_launch(),
        check_webgl(),
    ]
    if net:
        from .soundkit import hosts
        rows += [check_host(u) for u in HOSTS] + [check_sound_host(u) for u in hosts()]
    return rows


def report(rows, label="doctor"):
    for level, name, detail, fix in rows:
        print(f"{level:4}  {name:22} {detail}" + (f"\n      fix: {fix}" if fix and level != OK else ""))
    failed = any(r[0] == FAIL for r in rows)
    print(f"\nkit at {ROOT}\n{label}: " + ("FAIL" if failed else "ok"))
    return 1 if failed else 0


def require_engines(rows, engines):
    """An optional engine becomes required when selected for this task."""
    names = {f"engine {e}" for e in engines}
    return [(FAIL if name in names and level != OK else level, name, detail, fix)
            for level, name, detail, fix in rows]


def hf_cached(repo):
    """Whether a Hugging Face model repo is in the local cache (no network): HF_HOME, else ~/.cache/huggingface."""
    home = Path(os.environ.get("HF_HOME") or Path.home() / ".cache" / "huggingface")
    return (home / "hub" / ("models--" + repo.replace("/", "--"))).is_dir()


def check_cairo():
    """pycairo, in the interpreter the cairo engine runs (STUDIO_CAIRO_PYTHON, else the kit's)."""
    py = os.environ.get("STUDIO_CAIRO_PYTHON") or sys.executable
    try:
        ok = proc.run([py, "-c", "import cairo"], capture_output=True, timeout=30).returncode == 0
    except (OSError, Exception):
        ok = False
    return (OK, "engine cairo", f"pycairo importable in {py}; no browser or listener needed", "") if ok else \
        (FAIL, "engine cairo", f"pycairo is not importable in {py}", "install pycairo there, or set STUDIO_CAIRO_PYTHON to a Python that has it")


def model_checks(extras):
    """Speech models in the local cache, so an offline run (STUDIO_OFFLINE=1) can say what it lacks before it starts."""
    rows = []
    if "kokoro" in extras:
        rows.append((OK, "kokoro weights", "cached", "") if hf_cached("hexgrad/Kokoro-82M") else
                    (WARN, "kokoro weights", "not in the local cache", "studio doctor --fetch --extra kokoro on a machine with network, then copy ~/.cache/huggingface over; offline runs (STUDIO_OFFLINE=1) cannot fetch them"))
    return rows


def main_preflight(args):
    engine = args.engine or (settings.load(args.video)["engine"] if args.video else "live")
    if args.silent:
        extras = ()
    elif args.extra is not None:
        extras = args.extra
    else:
        extras = required(args.video) if args.video else ("kokoro", "align")
    if engine == "cairo":      # native: no node packages, no browser
        rows = system_checks() + [check_cairo()] + extra_checks(extras) + model_checks(extras)
    else:
        rows = system_checks() + [check_engine(e) for e in dict.fromkeys(("remotion", engine))]
        rows = require_engines(rows, ("remotion", engine)) + extra_checks(extras) + model_checks(extras)
        path, source = resolve_browser()
        present = path and Path(path).is_file() and os.access(path, os.X_OK)
        rows.append((OK if present else FAIL, "browser", f"{path} ({source}); not launched" if present else
                     "no executable browser installed", "studio doctor --fetch, or set STUDIO_BROWSER to a working Chrome"))
    if args.video:
        from . import plates
        if plates.config(args.video):
            rows.append(check_blender(args.video))
    print("No installs, downloads or browser/model launches. Model weights are verified during setup with doctor --speech.")
    return report(rows, "preflight")


def check_speech(timeout=300):
    """An opt-in smoke test, isolated from any video; first use can download model weights."""
    missing = [r for r in extra_checks(("kokoro", "align")) if r[0] == FAIL]
    if missing:
        return FAIL, "speech", "install kokoro and align extras first", "studio doctor --fetch --extra kokoro --extra align"
    code = '''import numpy as np
from studio_kit.narration import kokoro_pipeline
from faster_whisper import WhisperModel
from studio_kit.voice_check import score
text = "The studio is ready to make a video."
parts = list(kokoro_pipeline()(text, voice="af_heart", speed=1.0, split_pattern=None))
audio = np.concatenate([p.audio.numpy() for p in parts])
assert np.isfinite(audio).all() and np.max(np.abs(audio)) > 0.01, "empty or invalid speech"
audio = np.interp(np.arange(0, len(audio), 1.5), np.arange(len(audio)), audio).astype(np.float32)
parts, _ = WhisperModel("small.en", device="cpu", compute_type="int8").transcribe(audio, language="en")
heard = " ".join(p.text.strip() for p in parts)
assert score(text, heard) >= 0.7, "speech could not be recognised: " + heard
print(heard)
'''
    print("speech: synthesising and recognising a short sample (first use may download model weights)", flush=True)
    fix = "check the model download/native-library error, then rerun studio doctor --speech (references/setup.md)"
    try:
        result = proc.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=timeout)
    except proc.TimeoutExpired:
        return FAIL, "speech", f"sample timed out after {timeout} seconds", fix
    except OSError as e:
        return FAIL, "speech", f"sample did not complete: {e}", fix
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-1500:]
        return FAIL, "speech", detail or "sample failed", fix
    return OK, "speech", "local narration and recognition passed: " + result.stdout.strip().splitlines()[-1], ""


def fetch_sounds():
    """Fetch the sound kit; the reason when the network can't reach it (a skip, not a failure). A
    download that does not match its pinned digest stops here, loudly."""
    from . import soundkit
    from .fetch import Offline
    try:
        soundkit.fetch_kit()
    except Offline as e:
        print(f"skip: sound kit: {e}")
        return str(e).split(";")[0]
    return None


def installs_engines(args):
    """Whether --fetch installs the engines (and extras): always, unless it was asked for the sound
    kit alone, with --sounds and no --engine or --extra, while Remotion is installed already (npm ci
    would wipe and download its packages and browser again for nothing)."""
    return not args.sounds or bool(args.engine or args.extra) or check_engine("remotion")[0] != OK


def main(args):
    offline = fetch_sounds() if args.fetch and args.sounds else None
    if args.fetch and installs_engines(args):
        fetch(engines=tuple(dict.fromkeys(("remotion", *args.engine))), extras=args.extra)
    # Explicit extras are the task's requirements, not a request to require every optional voice.
    defaults = required(args.video) if args.video else (() if args.extra else EXTRAS)
    extras = tuple(dict.fromkeys([*args.extra, *defaults]))
    rows = checks(net=args.net) + extra_checks(extras) + [check_sounds(offline)]
    engines = [*args.engine, *([settings.load(args.video)["engine"]] if args.video else [])]
    rows = require_engines(rows, engines)
    if getattr(args, "speech", False):
        rows.append(check_speech())
    if args.video and (library := check_library(args.video)):
        rows.append(library)
    if args.video:
        from . import plates
        if plates.config(args.video):
            rows.append(check_blender(args.video))
    if args.video and (Path(args.video) / "video.json").exists() and settings.load(args.video)["engine"] == "live" \
            and settings.load(args.video)["gl"] != "cpu":
        rows.append(check_webgl(settings.load(args.video)["gl"]))
    if args.video:
        print("video requires: " + ", ".join(required(args.video)))
    if not args.video and not args.extra:
        rows = [(WARN if level == FAIL and name.startswith("extra ") else level, name, detail, fix)
                for level, name, detail, fix in rows]
    return report(rows)
