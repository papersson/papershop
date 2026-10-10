"""`studio check VIDEO`: deterministic checks that run through the engine interface.

  length       each clip's frame count, as the engine computes it, equals the timeline's
  determinism  sample frames rendered twice in separate engine calls have the same hash
  bounds       every named element lies inside the frame, and captions inside the caption band
  band         no scene element enters the caption band: at sampled times the scene alone (layers
               no-band) and the bare background are compared over the band's pixels, and every
               named element's box is checked against the band. Under a camera that has moved, what
               an opaque band covers is the camera's crop, as the frame edge is bounds' (see hidden_by_band)
  contrast     the brightest pixel under the caption band, against the caption colour, is at least 4.5:1
  overlap      no two text elements cover each other (more than 30% of the smaller one's box) at a sample
  inframe      the element being narrated stays in frame (in_frame): at each sentence's sample, a named
               element whose label the sentence or its screen note says lies inside the visible stage,
               below the layout's header and above the band. A warning: the match is by name
  pacing       after a significant move the stage holds at least 0.5 s before the next (motion.pacing): read
               from the cut's rendered clips; a chapter with none is skipped unless --only pacing, which
               samples stills at 10 fps instead (about 0.7 s of rendering a second of video). A short
               hold is a warning, not a failure
  pauses       with effects (audio/sfx.json, or an audio entry with role sfx) and a narration: no effect peaks over -24 dBFS, at the master's level,
               during a spoken word (audio_check.guard; `studio audio-check` measures the rest of the sound)
  grid, palette  pixel videos only (see pixel.py): the canvas is whole k×k blocks, in the palette
  filler, cuts, levels, sync, segments  footage videos only (see footage.py)

Sample times are spread across each clip's sentences, `--samples` per clip (moments.check_samples).

Incremental by default: the per-chapter checks (length, determinism, bounds, band, contrast,
legible, overlap, pacing) re-run only for chapters whose clip key changed since they last passed
there; a pass is remembered per chapter, check and format in .cache/check/ (a warning is a pass; a
pacing check skipped for want of a rendered clip runs again once a cut renders one). A warning is
remembered with its pass and printed again by each check that skips the chapter, until the chapter
changes. Video-wide checks always run. `--all` checks every chapter, and `studio publish` always runs
the full check as its gate.
"""
import hashlib
import json
import re
import tempfile
import shutil
import struct
import uuid
from pathlib import Path

from . import moments
from . import proc
from . import settings
from . import timeline as tl
from .engine import Engine

CAPTION_COLOUR = (0xE6, 0xEB, 0xF0)      # theme.ts INK
MIN_CONTRAST = 4.5
SIDE_MARGIN = 80                         # px kept free either side of a caption line
SLACK = 1.0                              # px of tolerance on box edges


PER_CLIP = ("length", "determinism", "bounds", "band", "contrast", "legible", "overlap", "pacing", "inframe")
OVERLAP = 0.3                            # share of the smaller text box another text box may cover


def sample_times(t, per_clip, clips=None):
    """[{clip, t}]: the moments the per-chapter checks look at (moments.check_samples)."""
    return moments.requests(moments.check_samples(t, per_clip, clips))


def length(video, engine=None, clips=None):
    engine, t = engine or Engine(video), tl.load(video)
    rows = []
    scenes = [c for c in t["tracks"]["scene"] if clips is None or c["id"] in clips]
    if not scenes:
        return rows
    got_all = engine.durations([c["id"] for c in scenes])
    for c in scenes:
        want = tl.frames(t, c["id"])[1]
        got = got_all[c["id"]]
        rows.append({"check": "length", "clip": c["id"], "ok": got == want, "detail": f"engine {got} frames, timeline {want}"})
    return rows


def determinism(video, samples=3, engine=None, clips=None):
    """Render `samples` frames per clip twice, in separate engine calls, and compare their hashes.
    A frame that differs means some state leaks between frames (a timer, unseeded randomness)."""
    engine, t = engine or Engine(video), tl.load(video)
    reqs = moments.requests(moments.even(t, samples, clips))
    if not reqs:
        return []
    def pixels(path):
        data = Path(path).read_bytes()
        dimensions = struct.unpack(">II", data[16:24])
        raw = proc.ffmpeg("-i", path, "-f", "rawvideo", "-pix_fmt", "rgba", "-", capture_output=True).stdout
        return digest(struct.pack(">II", *dimensions) + raw), digest(data), raw

    digest = lambda data: hashlib.sha256(data).hexdigest()
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        def pair(requests, tag):
            runs = []
            for run in ("a", "b"):
                batch = [{**r, "out": str(Path(tmp) / f"{tag}-{run}-{r['clip']}-{r['t']}.png")} for r in requests]
                engine.stills(batch)
                runs.append([(r["out"], *pixels(r["out"])) for r in batch])
            return list(zip(*runs))
        first = pair(reqs, "first")
        failed = [i for i, (a, b) in enumerate(first) if a[1] != b[1]]
        retry = dict(zip(failed, pair([reqs[i] for i in failed], "retry"))) if failed else {}
        evidence = Path(video) / "research" / "determinism" / uuid.uuid4().hex[:12]
        for i, (r, (a, b)) in enumerate(zip(reqs, first)):
            same = a[1] == b[1]
            detail = f"pixels {a[1]} {b[1]}; png {a[2]} {b[2]}"
            if not same:
                evidence.mkdir(parents=True, exist_ok=True)
                c, d = retry[i]
                for item in (a, b, c, d):
                    shutil.copyfile(item[0], evidence / Path(item[0]).name)
                differences = sum(a[3][j:j+4] != b[3][j:j+4] for j in range(0, min(len(a[3]), len(b[3])), 4))
                detail += f"; retry {c[1]} {d[1]}; {'FLAKY' if c[1] == d[1] else 'REPEATED'}; differing pixels {differences}; evidence {evidence}"
            rows.append({"check": "determinism", "clip": r["clip"], "t": r["t"], "ok": same, "detail": detail})
        if failed:
            (evidence / "results.json").write_text(json.dumps({"engine": getattr(engine, "name", "test"),
                "browser": getattr(engine, "browser", None), "rows": rows}, indent=1) + "\n")
    return rows


def _boxes(video, per_clip, engine, clips=None):
    times = sample_times(tl.load(video), per_clip, clips)
    return engine.layout(), (engine.boxes_at(times) if times else [])


def bounds(video, samples=3, engine=None, boxes=None):
    """Captions inside the band and its margins, and every other named element inside the frame. An
    element under a camera that has moved (a push-in, a pan: the engine marks its box "camera") may be
    cropped or left out of the shot: that is the camera's doing, and in_frame checks the narrated one.
    A box with no name of its own (a Remotion Rect given no name: "named" false) is never bounds' to
    fail, as the live engine reports no unnamed shape at all; a box a clip cuts is reported cut."""
    engine = engine or Engine(video)
    lay, frames = boxes or _boxes(video, samples, engine)
    W, H, band = lay["width"], lay["height"], lay["height"] - lay["band"]["height"]
    rows = []
    for f in frames:
        bad = []
        for b in f["boxes"]:
            if b["name"] == "caption":
                if b["x"] < SIDE_MARGIN - SLACK or b["x"] + b["w"] > W - SIDE_MARGIN + SLACK:
                    bad.append(f"caption line {b['w']:.0f} px wide leaves the {SIDE_MARGIN} px margins")
                if b["y"] < band - SLACK or b["y"] + b["h"] > H + SLACK:
                    bad.append("caption outside the band")
            elif not b.get("camera") and b.get("named", True) and (b["x"] < -SLACK or b["y"] < -SLACK or b["x"] + b["w"] > W + SLACK):
                bad.append(f"{b['name']!r} leaves the frame")
        rows.append({"check": "bounds", "clip": f["clip"], "t": f["t"], "ok": not bad, "detail": "; ".join(bad)})
    return rows


def overlap(video, samples=3, engine=None, boxes=None):
    """Two different text elements on top of each other: one label hides the other. Text inside a
    shape is fine (only text boxes are compared); captions are left to the band checks."""
    engine = engine or Engine(video)
    _, frames = boxes or _boxes(video, samples, engine)
    rows = []
    for f in frames:
        texts = [b for b in f["boxes"] if b.get("kind") == "text" and b["name"] != "caption" and b["w"] > 2 and b["h"] > 2]
        bad = []
        for i, a in enumerate(texts):
            for b in texts[i + 1:]:
                if a["name"] == b["name"]:
                    continue
                w = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
                h = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
                if w > 0 and h > 0 and w * h > OVERLAP * min(a["w"] * a["h"], b["w"] * b["h"]):
                    bad.append(f"{a['name'][:24]!r} and {b['name'][:24]!r} overlap")
        rows.append({"check": "overlap", "clip": f["clip"], "t": f["t"], "ok": not bad, "detail": "; ".join(bad[:4])})
    return rows


# inframe: a box's label is its name without the kind the kit prefixes ("node server" is "server"); a
# few names are kinds alone and never a label. An element named after its key (live text) rarely
# matches a sentence, which is why the check is a warning.
KINDS = ("board box ", "board text ", "box ", "node ", "layer ", "panel ", "close-up ", "term ", "variable ", "column ")
NOT_LABELS = {"rect", "card", "token", "ghost", "minimap", "caption", "close-up", "background", "band", "title", "panel",
              "code", "terminal", "table", "json", "look tag", "board tag", "board note", "board dot"}
SMALL_WORDS = {"a", "an", "the", "of", "to", "in", "on", "is", "it", "and", "or", "at", "by", "for"}


def _said(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def narrated(name, words):
    """Whether an element named `name` is what `words` (a sentence's, lowercased) talk about: its label's
    words appear together, in order. Labels of small words only, or under three letters, never match."""
    label = next((name[len(k):] for k in KINDS if name.startswith(k)), name)
    want = _said(label)
    if name in NOT_LABELS or not want or len("".join(want)) < 3 or set(want) <= SMALL_WORDS:
        return False
    return any(words[i:i + len(want)] == want for i in range(len(words) - len(want) + 1))


def in_frame(video, samples=3, engine=None, boxes=None):
    """At each sentence's check sample, every shown element the sentence (or its screen note in
    boards/notes.json) names lies inside the visible stage: inside the frame (the camera's view, as
    boxes are measured after it), below the layout's header and above the caption band. An element
    wholly inside the header strip is header content and is left alone. A warning, not a failure."""
    engine = engine or Engine(video)
    t = tl.load(video)
    lay, frames = boxes or _boxes(video, samples, engine)
    W, band, header = lay["width"], lay["height"] - lay["band"]["height"], (lay.get("header") or {}).get("height", 0)
    sentence = {(m["clip"], round(m["t"], 3)): m["sentence"] for m in moments.check_samples(t, samples) if m.get("sentence")}
    entries = {s["id"]: s for s in t["tracks"]["narration"]}
    notes_file = Path(video) / "boards" / "notes.json"
    notes = json.loads(notes_file.read_text()) if notes_file.exists() else {}
    rows = []
    for f in frames:
        sid = sentence.get((f["clip"], round(f["t"], 3)))
        if sid is None:
            continue
        e = entries.get(sid, {})
        words = _said(" ".join([e.get("text", ""), notes.get(sid, "")]))
        bad = {}
        for b in f["boxes"]:
            if b.get("opacity", 1) < 0.05 or b["w"] <= 2 or b["h"] <= 2 or not narrated(b["name"], words):
                continue
            x0, y0, x1, y1 = b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]
            if header and y0 >= -SLACK and y1 <= header + SLACK:      # within the header strip, not pushed off the top
                continue
            where = [side for side, out in (("left", x0 < -SLACK), ("right", x1 > W + SLACK),
                                            ("top" if not header else "header", y0 < header - SLACK), ("band", y1 > band + SLACK)) if out]
            if x1 <= 0 or x0 >= W or y1 <= header or y0 >= band:
                where = ["out of frame"]
            if where:
                bad.setdefault(b["name"], f"{b['name']!r} ({' and '.join(where)})")
        detail = (f"{sid} narrates " + "; ".join(bad.values()) + " outside the visible stage") if bad else ""
        rows.append({"check": "inframe", "clip": f["clip"], "t": f["t"], "ok": True, "detail": detail,
                     **({"severity": "warning"} if bad else {})})
    return rows


CAMERA_EDGE = 4        # px round a camera box whose pixels are still its own (its stroke, antialiasing)


def hidden_by_band(b, lay):
    """Whether the band may cover box `b`: it is under a camera that has moved (a push-in, a pan) and
    the band is opaque. The camera crops the scene at the band as at the frame's edges, and the band
    hides what it crops, so nothing shows through or reads as a caption; in_frame still warns when
    the element being narrated is pushed under it. A frosted band shows what is under it: no box is
    hidden there."""
    return bool(b.get("camera")) and lay["band"].get("style", "opaque") == "opaque"


def band_guard(video, samples=3, engine=None, boxes=None):
    """Named scene elements must end above the band, unless the band hides them (hidden_by_band)."""
    engine = engine or Engine(video)
    lay, frames = boxes or _boxes(video, samples, engine)
    band = lay["height"] - lay["band"]["height"]
    rows = []
    for f in frames:
        bad = [f"{b['name']!r} reaches y={b['y'] + b['h']:.0f} (band starts at {band})"
               for b in f["boxes"] if b["name"] != "caption" and b["y"] + b["h"] > band + SLACK and b["y"] < band + lay["band"]["height"]
               and not hidden_by_band(b, lay)]
        rows.append({"check": "band", "clip": f["clip"], "t": f["t"], "ok": not bad, "detail": "; ".join(bad)})
    return rows


def _band_pixels(png, lay):
    """Raw RGB bytes of the caption band region of an image, through ffmpeg."""
    h = lay["band"]["height"]
    return proc.ffmpeg("-i", png, "-vf", f"crop={lay['width']}:{h}:0:{lay['height'] - h}",
                       "-f", "rawvideo", "-pix_fmt", "rgb24", "-", capture_output=True).stdout


def luminance(rgb):
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def brightest(pixels):
    best = (0, 0, 0)
    seen = set()
    for i in range(0, len(pixels), 3):
        px = (pixels[i], pixels[i + 1], pixels[i + 2])
        if px not in seen:
            seen.add(px)
            if luminance(px) > luminance(best):
                best = px
    return best


def scene_in_band(scene, bare, lay, hidden=()):
    """How many band pixels differ between the scene alone and the bare background, leaving out those
    inside a box in `hidden` (boxes the band hides, with CAMERA_EDGE round them)."""
    W, top, e = lay["width"], lay["height"] - lay["band"]["height"], CAMERA_EDGE
    n = 0
    for i in range(0, min(len(scene), len(bare)), 3):
        if scene[i:i + 3] != bare[i:i + 3]:
            x, y = (i // 3) % W, (i // 3) // W + top
            n += not any(b["x"] - e <= x < b["x"] + b["w"] + e and b["y"] - e <= y < b["y"] + b["h"] + e for b in hidden)
    return n


def band_pixels_check(video, samples=3, engine=None, clips=None, boxes=None):
    """The scene alone against the bare background, over the band's pixels: any difference is
    scene content in the band, except inside a box the band hides (hidden_by_band). Then the caption
    contrast against what is under the band."""
    engine = engine or Engine(video)
    t, lay = tl.load(video), engine.layout()
    times = sample_times(t, samples, clips)
    rows = []
    if not times:
        return rows
    hidden = {}

    def hidden_at(r):           # the boxes are measured only once some sample has scene in the band
        if not hidden:
            hidden.update({(f["clip"], round(f["t"], 3)): [b for b in f["boxes"] if hidden_by_band(b, lay)]
                           for f in (boxes or _boxes(video, samples, engine, clips))[1]})
        return hidden.get((r["clip"], round(r["t"], 3)), ())
    with tempfile.TemporaryDirectory() as tmp:
        reqs = []
        for i, r in enumerate(times):
            for layer in ("no-band", "background", "no-captions"):
                reqs.append({**r, "layers": layer, "out": str(Path(tmp) / f"{i}-{layer}.png")})
        engine.stills(reqs)
        for i, r in enumerate(times):
            scene = _band_pixels(Path(tmp) / f"{i}-no-band.png", lay)
            bare = _band_pixels(Path(tmp) / f"{i}-background.png", lay)
            diff = scene_in_band(scene, bare, lay)
            diff = diff and scene_in_band(scene, bare, lay, hidden_at(r))
            rows.append({"check": "band", "clip": r["clip"], "t": r["t"], "ok": diff == 0,
                         "detail": "" if diff == 0 else f"{diff} pixels of scene content in the band"})
            under = brightest(_band_pixels(Path(tmp) / f"{i}-no-captions.png", lay))
            ratio = contrast_ratio(CAPTION_COLOUR, under)
            rows.append({"check": "contrast", "clip": r["clip"], "t": r["t"], "ok": ratio >= MIN_CONTRAST,
                         "detail": f"{ratio:.1f}:1 against the brightest pixel {under}"})
    return rows


CHECKS = ("length", "determinism", "bounds", "band", "contrast")
MORE = ("legible (text at least 18 px tall), overlap (no text on top of other text), pacing (a hold after each move), "
        "inframe (the narrated element stays in frame), "
        "provenance (assets used are recorded), dead and loop (motion)")


def config(video):
    return settings.load(video)


def genre(video):
    return config(video).get("genre", "explainer")


def _cache_file(video, fmt, samples):
    return Path(video) / ".cache" / "check" / f"{(fmt or '16:9').replace(':', 'x')}-s{samples}.json"


def _warnings_file(video, fmt, samples):
    return _cache_file(video, fmt, samples).with_suffix(".warnings.json")


def changed_clips(video, kinds, samples=3, fmt=None):
    """({clip: key}, {kind: clip ids whose key changed for that kind since it last passed})."""
    from . import render
    t = tl.load(video)
    keys = {c["id"]: render.clip_key(video, t, c["id"], "check", fmt=fmt) for c in t["tracks"]["scene"]}
    f = _cache_file(video, fmt, samples)
    passed = json.loads(f.read_text()) if f.exists() else {}
    from .motion import rendered_clip

    def want(cid, kind):      # a pacing check skipped for want of a rendered clip runs once a cut renders one
        return keys[cid] + ("+skipped" if kind == "pacing" and rendered_clip(video, t, cid, fmt) is None else "")
    return keys, {kind: {cid for cid in keys if passed.get(cid, {}).get(kind) != want(cid, kind)} for kind in kinds}


def remember(video, rows, keys, kinds, samples=3, fmt=None):
    """Record a pass for each (clip, kind) that ran in `rows` with no failure, and its warnings with it."""
    f = _cache_file(video, fmt, samples)
    passed = json.loads(f.read_text()) if f.exists() else {}
    ran, failed = set(), set()
    for r in rows:
        if r["check"] in kinds and r.get("clip") in keys and not r.get("remembered"):
            ran.add((r["clip"], r["check"]))
            if not r["ok"]:
                failed.add((r["clip"], r["check"]))
    skipped = {(r["clip"], r["check"]) for r in rows if r.get("skipped")}
    for cid, kind in ran - failed:
        passed.setdefault(cid, {})[kind] = keys[cid] + ("+skipped" if (cid, kind) in skipped else "")
    for cid, kind in failed:
        passed.get(cid, {}).pop(kind, None)
    passed = {cid: v for cid, v in passed.items() if cid in keys}
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(passed, indent=1, sort_keys=True))
    w = _warnings_file(video, fmt, samples)
    warned = json.loads(w.read_text()) if w.exists() else {}
    for cid, kind in ran:
        warned.get(cid, {}).pop(kind, None)
    for r in rows:
        key = (r.get("clip"), r["check"])
        if key in ran - failed and r.get("severity") == "warning" and not r.get("remembered"):
            entry = warned.setdefault(key[0], {}).setdefault(key[1], {"key": passed[key[0]][key[1]], "rows": []})
            entry["rows"].append(r)
    warned = {cid: v for cid, v in warned.items() if cid in keys and v}
    w.write_text(json.dumps(warned, indent=1, sort_keys=True))


def open_warnings(video, rows, kinds, samples=3, fmt=None):
    """The warnings remembered with the pass of each (clip, kind) that did not run in `rows`, while
    that pass still holds (the chapter has not changed): marked remembered, to be printed again."""
    w, f = _warnings_file(video, fmt, samples), _cache_file(video, fmt, samples)
    if not w.exists() or not f.exists():
        return []
    warned, passed = json.loads(w.read_text()), json.loads(f.read_text())
    ran = {(r.get("clip"), r["check"]) for r in rows}
    return [{**r, "remembered": True} for cid, by in warned.items() for kind, entry in by.items()
            if kind in kinds and (cid, kind) not in ran and passed.get(cid, {}).get(kind) == entry["key"]
            for r in entry["rows"]]


def run(video, samples=3, only=None, engine=None, fmt=None, everything=True):
    """The checks. With everything=False, the per-chapter checks run only on chapters whose clip
    key changed since they last passed (see changed_clips); a pass is remembered either way."""
    default = only is None
    extra = {"pixel": ("grid", "palette"), "footage": ("filler", "cuts", "levels", "sync", "segments"),
             "motion": ("dead",), "launch": ()}.get(genre(video), ())
    always = ("legible", "overlap", "pacing", "inframe") + (("provenance",) if (Path(video) / "assets" / "provenance.json").exists() else ())
    only = set(only or CHECKS + extra + always)
    known = set(CHECKS) | {"legible", "overlap", "pacing", "inframe", "provenance", "dead", "loop", "grid", "palette", "filler", "cuts", "levels", "sync", "segments", "script", "code-source", "pauses"}
    if only - known:
        raise SystemExit("unknown checks: " + ", ".join(sorted(only - known)))
    preflight = []
    if "script" in only or (default and config(video).get("teaching_contract")):
        from . import script_check
        preflight += script_check.run(video)
    if "code-source" in only or (default and (Path(video) / "data" / "steps" / "index.json").exists()):
        from . import steps
        preflight += steps.check(video)
    if "pauses" in only or default:      # video-wide, from the sound alone; nothing without effects
        from . import audio_check
        preflight += audio_check.guard(video)
    if only <= {"script", "code-source", "pauses"}:
        return preflight
    engine = engine or Engine(video, fmt=fmt)
    kinds = sorted(only & set(PER_CLIP))
    keys, by_kind = changed_clips(video, kinds, samples, fmt)
    todo = set().union(*by_kind.values())
    # pacing reads the cut's clips, so a cut can make it due alone: it doesn't re-run the others
    clips = None if everything else set().union(*(v for k, v in by_kind.items() if k != "pacing"))
    pacing_clips = None if everything else by_kind.get("pacing", set())
    if not everything:
        skipped = sorted(set(keys) - todo, key=lambda c: list(keys).index(c))
        print(f"check: {len(todo)} chapter(s) changed since their last pass"
              + (f"; skipping {', '.join(skipped)} (unchanged, passed before)" if skipped else "")
              + " (--all checks every chapter)", flush=True)
    rows = preflight
    if "length" in only:
        rows += length(video, engine, clips)
    if "determinism" in only:
        rows += determinism(video, samples, engine, clips)
    boxes = None
    if only & {"bounds", "band", "legible", "overlap", "inframe"}:
        boxes = _boxes(video, samples, engine, clips)
        if "inframe" in only:
            rows += in_frame(video, samples, engine, boxes)
        if "overlap" in only:
            rows += overlap(video, samples, engine, boxes)
        if "legible" in only:
            from . import motion
            rows += motion.legible(video, samples, engine, boxes)
        if "bounds" in only:
            rows += bounds(video, samples, engine, boxes)
        if "band" in only:
            rows += band_guard(video, samples, engine, boxes)
    if only & {"band", "contrast"}:
        pix = band_pixels_check(video, samples, engine, clips, boxes)
        rows += [r for r in pix if r["check"] in only]
    if genre(video) == "footage" and only & {"filler", "cuts", "levels", "sync", "segments"}:
        from . import footage
        rows += [r for r in footage.checks(video) if r["check"] in only]
    if "pacing" in only:
        from . import motion
        rows += motion.pacing(video, engine, pacing_clips, stills=not default)
    if "dead" in only:
        from . import motion
        rows += motion.dead_beats(video, engine=engine)
    if "loop" in only or (default and config(video).get("loop")):
        from . import motion
        rows += motion.loop_seam(video, engine)
    if "provenance" in only:
        from . import motion
        rows += motion.provenance(video)
    if only & {"grid", "palette"}:
        from . import pixel
        rows += [r for r in pixel.run(video, samples, engine) if r["check"] in only]
    remember(video, rows, keys, kinds, samples, fmt)
    return rows + open_warnings(video, rows, kinds, samples, fmt)


def summary(rows):
    """One line: per check, how many rows passed, warned, were skipped and failed; a warning is not
    counted as ok."""
    by = {}
    for r in rows:
        tally = by.setdefault(r["check"], {"ok": 0, "warning": 0, "skipped": 0, "FAILED": 0})
        tally["FAILED" if not r["ok"] else "warning" if r.get("severity") == "warning" else "skipped" if r.get("skipped") else "ok"] += 1
    return "; ".join(f"{k}: " + ", ".join(f"{n} {what}{'s' if what == 'warning' and n > 1 else ''}"
                                          for what, n in v.items() if n or what == "ok") for k, v in by.items())


def main(args):
    if (Path(args.video) / "timeline.json").exists():      # a script check runs before there is one
        tl.build(args.video)                               # as a cut does, so the checks see the sources
    rows = run(args.video, args.samples, args.only.split(",") if args.only else None, fmt=args.format,
               everything=getattr(args, "all", False))
    for r in rows:
        where = f"{r['clip']}" + (f" t={r['t']}" if "t" in r else "")
        mark = "WARN" if r.get("severity") == "warning" else "skip" if r.get("skipped") else "ok  " if r["ok"] else "FAIL"
        again = " (open since an earlier check; the chapter is unchanged)" if r.get("remembered") else ""
        print(f"{mark}  {r['check']:11} {where:16} {r['detail']}{again}".rstrip())
    print(summary(rows))
    return 1 if any(not r["ok"] for r in rows) else 0
