"""What a clip's frames depend on, as a key: its scene code, data, assets, timeline slice, layout and
engine. The cut cache, stills, checks, crops and the review fingerprints are all keyed on it.

A clip's cache key hashes everything its frames depend on: the engine (engine_inputs: its source and
packages, and for the live engine its page, its WebGL backend and the browser), the video's shared scene
files, the clip's own scene file (scenes/<clip>.js), its slice of the timeline (as times relative
to the clip's first frame) and the layout. So an edit to one chapter's scene re-renders that
chapter only, a narration edit re-renders the chapter it is in (later chapters move by whole frames,
see narration.CHAPTER_GRID, and keep their keys), and an edit to a shared file re-renders them all.
Its cues are the ones its scene code names (see scene_cues), so moving a cue re-renders the
chapters that wait on it, and the beat grid counts only for chapters whose code reads it.
"""
import functools
import hashlib
import json
import re
from pathlib import Path

from . import proc
from . import settings
from . import timeline as tl
from .env import engine_dir, resolve_browser


def _hash_tree(h, p, root=None):
    """Hash file names relative to `p` and contents, so a moved or copied video keeps its keys."""
    p = Path(p)
    root = root or (p if p.is_dir() else p.parent)
    if p.is_dir():
        for child in sorted(p.iterdir()):
            if child.name != "node_modules" and not child.name.startswith("."):
                _hash_tree(h, child, root)
    elif p.exists():
        h.update(str(p.relative_to(root)).encode())
        h.update(p.read_bytes())


@functools.lru_cache(maxsize=None)
def _browser_identity():
    """The browser the engines render with (env.resolve_browser), as its path and size: another
    browser can draw the same scene differently, so live clips are keyed on it."""
    path, _ = resolve_browser()
    return f"{path}:{Path(path).stat().st_size}" if path and Path(path).is_file() else str(path)




def engine_inputs(h, engine, video):
    """Hash what an engine's pixels depend on outside the video: its source, the engines' shared
    modules and its lock file (a pinned package such as three.js), and for the live engine its CLI and
    page (launch flags, the import map), the video's WebGL backend (video.json gl) and the browser.
    The clip keys and the look sheet's key both use it, so neither goes stale where the other doesn't."""
    _hash_tree(h, engine_dir(engine) / "src")
    _hash_tree(h, engine_dir("shared"))  # the engines' shared modules: motion maths, narration times, cameras
    _hash_tree(h, engine_dir(engine) / "package-lock.json")
    if engine == "live":
        for f in ("cli.mjs", "render.html"):
            _hash_tree(h, engine_dir(engine) / f)
        h.update(json.dumps({"gl": settings.load(video)["gl"], "browser": _browser_identity()}).encode())


def _engine_of(video):
    return settings.load(video)["engine"]


def has_scene(video, clip_id, engine=None):
    """A chapter with scenes/<clip>.js draws live; otherwise it shows its board."""
    return (Path(video) / "scenes" / f"{clip_id}.js").is_file()


ASSET_BYTES_UNDER = 20_000_000   # bytes: assets up to this size are hashed by content, larger ones listed


@functools.lru_cache(maxsize=None)
def _digest(path, size, mtime_ns, ctime_ns):
    """A file's content hash, read once per process for each state of the file (every clip's key hashes the assets)."""
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()


def _hash_assets(h, p):
    """Assets by content, so a file replaced at the same size and time (cp -p, rsync -a, unzip) re-renders;
    footage and anything else over ASSET_BYTES_UNDER by name, size and time, since reading it on every
    key would cost more than the render it saves."""
    p = Path(p)
    if p.is_dir():
        for f in sorted(p.rglob("*")):
            if f.is_file():
                st = f.stat()
                if st.st_size <= ASSET_BYTES_UNDER:
                    h.update(f"{f.relative_to(p)}:{_digest(str(f), st.st_size, st.st_mtime_ns, st.st_ctime_ns)}".encode())
                else:
                    h.update(f"{f.relative_to(p)}:{st.st_size}:{int(st.st_mtime)}".encode())


SCENE_CODE = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py"}
# A scene registry lists clips without making them depend on one another.
REGISTRIES = {"index", "project"}
# Comments are read as code: a cue named in one costs an extra render at worst, where telling
# comments from JSX text, regexes and URLs would need a parser to get right.
_LITERAL_CUE = re.compile(r"""\bcue\s*\(\s*(?:"([^"\\]*)"|'([^'\\]*)'|`([^`\\$]*)`)\s*[,)]""")
_IMPORT = re.compile(r"""(?:\bfrom|\bimport|\brequire)\s*\(?\s*['"](\.\.?/[^'"?]+)""")


def _cue_names(text):
    """The cue names a scene file waits on, or None when it may read a cue by a name it computes:
    `cue(x)`, `cue` passed on or renamed, or the timeline's `cues` read directly."""
    names = {next(g for g in m.groups() if g is not None) for m in _LITERAL_CUE.finditer(text)}
    rest = _LITERAL_CUE.sub(" ", text)
    rest = re.sub(r"\{[^{}]*\}\s*=", lambda m: re.sub(r"\bcue\s*(?=[,}])", " ", m.group(0)), rest)  # const { cue } = ...
    return None if re.search(r"\bcues?\b", rest) else names


def _imports(f, text, root):
    """The scenes/ files `f` imports by a relative path."""
    for spec in _IMPORT.findall(text):
        base = (f.parent / spec).resolve()
        for c in (base, *(base.with_name(base.name + e) for e in SCENE_CODE), *(base / f"index{e}" for e in SCENE_CODE)):
            if c.is_file() and c.is_relative_to(root):
                yield c
                break


def scene_files(video, clip_id, clip_ids):
    """The scene code a clip runs: its own file (or folder), the shared modules (every scenes/ file
    not named after another clip), and whatever they import, another clip's file included."""
    root = (Path(video) / "scenes").resolve()
    owner = lambda f: Path(f.relative_to(root).parts[0]).stem
    files = sorted(root.rglob("*")) if root.is_dir() else []
    todo = [f for f in files if f.is_file() and f.suffix in SCENE_CODE and (owner(f) == clip_id or owner(f) not in clip_ids)]
    seen = []
    while todo:
        f = todo.pop(0)
        if f in seen:
            continue
        seen.append(f)
        if not (f.parent == root and f.stem in REGISTRIES):
            todo += _imports(f, f.read_text(errors="replace"), root)
    return seen


def scene_cues(video, clip_id, clip_ids):
    """The cue names a clip's scene code reads (scene_files), or None for all cues when any of it
    computes a cue name. The engine kits read cues only through their cue() helper, except the typed
    code editor (code.js), which reads the cues data/typing.json names: a scene that imports that
    file reads them all."""
    names = set()
    typing = view = False
    for f in scene_files(video, clip_id, clip_ids):
        text = f.read_text(errors="replace")
        found = _cue_names(text)
        if found is None:
            return None
        names |= found
        typing |= "data/typing.json" in text
        view |= "data/codeview.json" in text
    if typing and (Path(video) / "data" / "typing.json").exists():
        for b in json.loads((Path(video) / "data" / "typing.json").read_text()).values():
            names |= {b["cue"]} | {f"{b['cue']}-{k}" for k in ("save", "run", "pop")}
    if view and (path := Path(video) / "data" / "codeview.json").exists():
        spec = json.loads(path.read_text())
        def add(when):
            if when is not None:
                names.add(when if isinstance(when, str) else when[0])
        add(spec.get("payoff"))
        for a, b in spec.get("open", []):
            add(a), add(b)
        for group in ("folds", "highlights", "helpers"):
            for item in spec.get(group, []):
                add(item.get("from")), add(item.get("to"))
    return names


# A path into the video's data/ as scene code names it: an import ('../data/typing.json'), a fetch or a
# string handed to a helper ("data/steps/run/results.json"). A path built at run time can't be followed.
_DATA = re.compile(r"""['"`](?:\.\./|\./)*(data/[^'"`\s]*)['"`]""")
_DYNAMIC = re.compile(r"""\bimport\s*\(|\bfetch\s*\(|['"`](?:\.\./)*data/[^'"`]*\$\{""")
# A literal URL remains a known dependency when browser modules fetch JSON instead of importing it.
_STATIC_FETCH = re.compile(r"""\bfetch\s*\(\s*(?:['"](?:\.\.?/)*data/[^'"?]+['"]\s*|new\s+URL\s*\(\s*['"](?:\.\.?/)*data/[^'"?]+['"]\s*,\s*import\.meta\.url\s*\)\s*)(?=[,)])""")


def scene_data(video, clip_id, clip_ids):
    """The data/ files and folders a clip's scene code reads (scene_files), or None when it may read
    one by a path it builds (a template string, a dynamic import or fetch): then every file counts.
    A video that rewrites data/typing.json re-rendered every chapter, those without code too."""
    found = set()
    for f in scene_files(video, clip_id, clip_ids):
        text = f.read_text(errors="replace")
        if _DYNAMIC.search(_STATIC_FETCH.sub("", text)):
            return None
        found |= set(_DATA.findall(text))
    return found


# Beat helpers or the timeline's beats read directly.
_BEATS = re.compile(r"\b(?:beats?|downbeats?|hits|bpm)\b")


def scene_reads_beats(video, clip_id, clip_ids):
    """Whether a clip's scene code (scene_files) may read the beat grid. As with cues, a mention in a
    comment counts: it costs a render at worst. The engine kits read beats only through useClip."""
    return any(_BEATS.search(f.read_text(errors="replace")) for f in scene_files(video, clip_id, clip_ids))


def clip_key(video, timeline, clip_id, quality, engine=None, fmt=None):
    engine = engine or _engine_of(video)
    video = Path(video)
    clip_ids = {c["id"] for c in timeline["tracks"]["scene"]}
    h = hashlib.sha1(quality.encode())
    engine_inputs(h, engine, video)
    scenes = sorted((video / "scenes").iterdir()) if (video / "scenes").is_dir() else []
    for f in scenes:
        if f.stem == clip_id or f.stem not in clip_ids:
            _hash_tree(h, f)
    root = (video / "scenes").resolve()
    for f in scene_files(video, clip_id, clip_ids):     # a helper imported from another clip's file
        if Path(f.relative_to(root).parts[0]).stem in clip_ids - {clip_id}:
            _hash_tree(h, f, root)
    if quality == "boards" or not has_scene(video, clip_id, engine):
        _hash_tree(h, video / "boards")  # the chapter renders its board
    read = scene_data(video, clip_id, clip_ids)       # scenes import their numbers from data/
    if read is None:
        _hash_tree(h, video / "data")
    else:
        for rel in sorted(read):
            _hash_tree(h, video / rel, video)
    _hash_assets(h, video / "assets")
    c = tl.clip(timeline, clip_id)
    first, count = tl.frames(timeline, clip_id)
    t0 = first / timeline["fps"]
    rel = lambda x: round(x - t0, 4)   # the clip's frames depend on times relative to its first frame only
    named = scene_cues(video, clip_id, clip_ids)

    def reads(k, v):
        if named is None:
            return True
        if k.startswith("reveal:"):
            return k.startswith(f"reveal:{clip_id}_") or k in named
        # A named cue counts wherever it lies (an animation started before the clip may still run); one
        # inside the clip's frames counts anyway, in case a scene reaches it in a way the scan missed.
        return k in named or t0 <= v <= t0 + count / timeline["fps"]
    part = {
        "clip": {**c, "start": rel(c["start"]), "end": rel(c["end"])}, "frames": count, "fps": timeline["fps"],
        "narration": [{**s, "start": rel(s["start"]), "end": rel(s["end"]),
                       "pause": {**s["pause"], "start": rel(s["pause"]["start"]), "end": rel(s["pause"]["end"])} if "pause" in s else None,
                       "words": [{**w, "start": rel(w["start"]), "end": rel(w["end"])} for w in s.get("words", [])]}
                      for s in timeline["tracks"]["narration"] if s["clip"] == clip_id],
        "captions": [{"start": rel(x["start"]), "end": rel(x["end"]), "lines": tl.caption_lines(x, fmt)}
                     for x in timeline["tracks"]["captions"] if x["end"] > c["start"] and x["start"] < c["end"]],
        "cues": {k: rel(v) for k, v in timeline.get("cues", {}).items() if reads(k, v)},
        "footage": timeline["tracks"].get("footage", []),
        "beats": timeline.get("beats", {}) if scene_reads_beats(video, clip_id, clip_ids) else {},
        "layout": tl.layout(video, fmt),
    }
    # A plate (plates.py) is part of the frame: its key, at the quality a render of this clip draws.
    from . import plates
    if clip_id in plates.config(video):
        part["plate"] = plates.key(video, timeline, clip_id, "final" if quality == "final" else "draft")
    # The parts of video.json a scene reads as it draws: live scenes get the colour legend as
    # c.legend and the motion setting as c.motion. Each is left out when unset, so a video without
    # it keeps its keys.
    if engine == "live":
        part |= {k: settings.raw(video)[k] for k in ("legend", "motion") if settings.raw(video).get(k)}
    h.update(json.dumps(part, sort_keys=True).encode())
    return h.hexdigest()[:16]


def clip_file(video, clip_id, quality, key, fmt=None):
    """The cached render of a clip at a key: .cache/clips/<clip>-<quality>[-<format>]-<key>.mp4."""
    tag = f"-{fmt.replace(':', 'x')}" if fmt and fmt != "16:9" else ""
    return Path(video) / ".cache" / "clips" / f"{clip_id}-{quality}{tag}-{key}.mp4"
