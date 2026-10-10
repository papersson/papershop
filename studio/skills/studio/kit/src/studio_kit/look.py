"""`studio look-sheet VIDEO`: the model sheet, drawn before scenes are built.

Every visual element the scenes will use, in each of its states, rendered by the video's own engine
in its theme and layout: boxes (idle, lit, failed), arrows (idle, active, muted), the token's glyph
states, cards, highlights, labels at each type size, the caption band with a sample caption, and the
theme's colours with their roles (and, on Remotion, the map, the close-up and the code components),
and the video's colour legend (video.json legend, which `studio check` holds the scenes to) when it
declares one.
The builder adds the video's own elements in scenes/look.js (live) or scenes/look.tsx (Remotion);
templates/live/scenes/example-look.js and templates/scenes/example-look.tsx show how.

Output: out/look/look-<n>.png, one per page, and out/look/look.json, the record a review bundle
includes (`latest`). Another format's sheet goes to out/look/<format>/. The record's key covers the
engine's source, the layout, the legend and the video's look file, so a stale sheet is told apart
from a current one. Live and Remotion only.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from . import timeline as tl
from .engine import LOOK_ENGINES, Engine
from .env import engine_dir

SAMPLE = "Captions go in the band, at most two lines."     # two lines or fewer at every format's width
OWN = ("look.js", "look.tsx", "look.ts", "look.jsx")


def sheet_dir(video, fmt=None):
    """Where a format's sheet goes: out/look/, or out/look/<format>/ for another format."""
    out = Path(video) / "out" / "look"
    return out if not fmt or fmt == "16:9" else out / fmt.replace(":", "x")


def own_file(video):
    """The video's own look file (scenes/look.js or look.tsx), or None."""
    return next((Path(video) / "scenes" / f for f in OWN if (Path(video) / "scenes" / f).is_file()), None)


def look_files(video):
    """The video's look file and every scenes/ file it imports, followed as render follows a scene's."""
    from .render import _imports
    own = own_file(video)
    if own is None:
        return []
    root, seen, todo = (Path(video) / "scenes").resolve(), [], [own.resolve()]
    while todo:
        f = todo.pop(0)
        if f not in seen:
            seen.append(f)
            todo += _imports(f, f.read_text(errors="replace"), root)
    return seen


def key(video, engine, fmt=None):
    """A hash of what the sheet is drawn from: the engine and its source, the layout, the colour
    legend, and the video's look file with the scene files it imports."""
    from . import settings
    h = hashlib.sha256(engine.encode())
    h.update(json.dumps(tl.layout(video, fmt), sort_keys=True).encode())
    legend = settings.raw(video).get("legend")
    if legend:
        h.update(json.dumps(legend, sort_keys=True).encode())
    roots = [engine_dir(engine) / "src", engine_dir("shared")]
    for f in sorted(p for root in roots for p in root.rglob("*") if p.is_file() and "node_modules" not in p.parts):
        h.update(f.name.encode() + f.read_bytes())
    scenes = (Path(video) / "scenes").resolve()
    for f in look_files(video):
        h.update(str(f.relative_to(scenes)).encode() + f.read_bytes())
    return h.hexdigest()[:16]


def make(video, fmt=None, engine=None):
    """Render the sheet and write its record; returns the record."""
    video = Path(video)
    engine = engine or Engine(video, fmt=fmt)
    if engine.name not in LOOK_ENGINES:
        raise SystemExit(f"look-sheet: the {engine.name} engine has no look sheet; it is drawn by "
                         f"{' and '.join(LOOK_ENGINES)} (video.json engine)")
    if not (video / "timeline.json").exists():
        raise SystemExit("look-sheet needs timeline.json: narrate first (`studio narrate VIDEO`, or --estimate)")
    lay = engine.layout()
    out = sheet_dir(video, fmt)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("look-*.png"):
        old.unlink()
    r = engine.look(out, tl.wrap(SAMPLE, lay["band"].get("chars", tl.LINE_CHARS)))
    own = own_file(video)
    rec = {"engine": engine.name, "format": fmt or "16:9", "made": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "key": key(video, engine.name, fmt), "own": str(own.relative_to(video)) if own else None,
           "pages": [{"page": p["page"], "title": p.get("title", ""), "file": str(Path(p["out"]).resolve().relative_to(video.resolve()))}
                     for p in r["pages"]]}
    (out / "look.json").write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def latest(video, fmt=None):
    """The current sheet's record with "stale" (drawn by another engine than video.json's, or from an
    older engine source, layout, look file or file it imports) and each page's file checked, or None
    when there is no sheet. What the motion review's bundle includes."""
    from . import settings
    f = sheet_dir(video, fmt) / "look.json"
    if not f.exists():
        return None
    rec = json.loads(f.read_text())
    engine = settings.load(video)["engine"]
    rec["stale"] = (rec.get("engine") != engine or rec.get("key") != key(video, engine, fmt)
                    or not all((Path(video) / p["file"]).exists() for p in rec["pages"]))
    return rec


def main(args):
    rec = make(args.video, getattr(args, "format", None))
    for p in rec["pages"]:
        print(f"look {p['page']}: {p['title']}  {Path(args.video) / p['file']}")
    print(f"{len(rec['pages'])} pages ({rec['engine']}, {rec['format']}); "
          + (f"the video's own from {rec['own']}" if rec["own"] else "no scenes/look file yet: add the video's own elements there")
          + f"; record {sheet_dir(args.video, getattr(args, 'format', None)) / 'look.json'}")
    return 0
