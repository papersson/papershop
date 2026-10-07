"""Boards: one rough frame per beat, drawn before a chapter's scene exists.

A board settles what the picture shows, and where, while that costs minutes: the builder writes
boards/boards.json, {chapter id: [{"from": sentence id, "elements": [...]}]}, each frame holding from
its sentence until the next frame. Elements are {"box": label, "at": [x, y], "w"?, "h"?},
{"text": ..., "at": [x, y], "size"?}, {"arrow": [[x, y], [x, y]]}, {"line": [...]} and
{"dot": [x, y], "r"?}, in stage units (origin at the centre, y up, 8 units tall).

boards/notes.json is generated from SCRIPT.md's screen notes (sentence id -> note), so a board can
show the note in force (a note holds until the next one, like a frame), and a chapter without frames
still has a picture: its notes. A chapter with no scene file renders its board in every cut, which is what lets a cut show
the finished chapters animated and the rest as boards.
"""
import json
from pathlib import Path

from . import script

DIR = "boards"


def notes(video):
    """{sentence id: screen note}, each note copied to every sentence of the range it names."""
    video = Path(video)
    if not (video / "SCRIPT.md").exists():
        return {}
    try:
        chapters = script.read(video)
    except SystemExit:
        return {}
    out = {}
    for c in chapters:
        ids = [s.id for s in c.sentences]
        for n in c.screen:
            if n.start not in ids or n.end not in ids:
                continue                       # stale cue: script_check reports it
            for sid in ids[ids.index(n.start):ids.index(n.end) + 1]:
                out[sid] = f"{out[sid]} {n.text}" if sid in out else n.text
    return out


def write_notes(video):
    """Write boards/notes.json when it would change (an unchanged file keeps render keys stable)."""
    video = Path(video)
    found = notes(video)
    f = video / DIR / "notes.json"
    if not found and not f.exists():
        return None
    text = json.dumps(found, indent=1, ensure_ascii=False) + "\n"
    if not f.exists() or f.read_text() != text:
        f.parent.mkdir(exist_ok=True)
        f.write_text(text)
    return f


def frames(video):
    f = Path(video) / DIR / "boards.json"
    return json.loads(f.read_text()) if f.exists() else {}


def coverage(video, timeline):
    """Per sentence: "frame" (an authored frame holds over it), "note" (only its screen note) or None."""
    drawn = frames(video)
    found = notes(video)
    starts = {s["id"]: s["start"] for s in timeline["tracks"]["narration"]}
    out = {}
    for s in timeline["tracks"]["narration"]:
        held = [f for f in drawn.get(s["clip"], []) if starts.get(f.get("from"), float("inf")) <= s["start"]]
        noted = [x for x in timeline["tracks"]["narration"]       # a note holds until the next one
                 if x["clip"] == s["clip"] and x["start"] <= s["start"] and x["id"] in found]
        out[s["id"]] = "frame" if held else "note" if noted else None
    return out


def main(args):
    from . import render, timeline as tl
    video = Path(args.video).resolve()
    rec = render.make_cut(video, boards=True)
    cov = coverage(video, tl.load(video))
    drawn = sum(v == "frame" for v in cov.values())
    noted = sum(v == "note" for v in cov.values())
    bare = [k for k, v in cov.items() if v is None]
    print(f"boards cut {rec['cut']}: {len(cov)} sentences; {drawn} under a drawn frame, {noted} with only a note, "
          f"{len(bare)} with neither" + (f" ({', '.join(bare[:8])}{'…' if len(bare) > 8 else ''})" if bare else ""))
    return 0
