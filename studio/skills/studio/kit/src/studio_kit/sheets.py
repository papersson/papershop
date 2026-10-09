"""`studio sheets VIDEO OUTDIR`: what a reviewer looks at, made by seeking to the frames it needs.

  chapters/sN.png   one contact sheet per chapter: a frame near the end of every sentence
  phone.png         a sample of the whole video at 360 px wide, how it reads on a phone
  strip_CLIP_T.png  with --strip CLIP T (repeatable): 12 consecutive frames around T, to catch pops
                    and overlaps; --windows FILE gives a JSON list of {clip, t, frames?, fps?}
  crops/            full-resolution crops of every small label (under --below px tall), with
                    crops/index.json giving each one's sentences, text and rendered size at 1080p;
                    a label that looks the same in several sentences of a chapter is cropped once,
                    and unchanged frames reuse their crops (.cache/crops/)

A downscaled sheet misjudges text: four frame reviews reported "labels are 15-18 px" from sheets
when the labels measured 26 px. The crops and their sizes are what the frame review judges from.
"""
import json
import math
import shutil
from pathlib import Path

from . import proc
from . import cuts, moments, render
from . import timeline as tl
from .engine import Engine

PHONE_WIDTH = 360
PHONE_FRAMES = 15
STRIP_FRAMES = 12


def tile(files, out, cols, width=None):
    """Tile images (scaled to one width, so they can be joined) into one sheet with ffmpeg."""
    files = [str(f) for f in files]
    if not files:
        return None
    rows = math.ceil(len(files) / cols)
    cmd = []
    for f in files:
        cmd += ["-i", f]
    scale = f"scale={width}:-1," if width else ""
    chain = "".join(f"[{i}:v]{scale}setsar=1[v{i}];" for i in range(len(files)))
    join = "".join(f"[v{i}]" for i in range(len(files)))
    cmd += ["-filter_complex", f"{chain}{join}concat=n={len(files)}:v=1:a=0,tile={cols}x{rows}:padding=4:color=white[o]",
            "-map", "[o]", "-frames:v", "1", str(out)]
    proc.ffmpeg(*cmd)
    return out


def chapter_sheets(video, out, cut=None):
    video, out = Path(video), Path(out)
    n = cut or cuts.latest(video, cuts.SCENE_STILLS)
    rec = render.read_cut(video, n)
    (out / "chapters").mkdir(parents=True, exist_ok=True)
    made = []
    for c in tl.load(video)["tracks"]["scene"]:
        files = [render.cuts_dir(video) / f"cut{n}" / s["file"] for s in rec["stills"] if s["clip"] == c["id"]]
        if tile(files, out / "chapters" / f"{c['id']}.png", 4):
            made.append(c["id"])
    return made


def phone_sheet(video, out, engine=None):
    engine, t = engine or Engine(video), tl.load(video)
    ends = moments.sentence_ends(t)
    picks = [ends[round(i * (len(ends) - 1) / max(1, PHONE_FRAMES - 1))] for i in range(min(PHONE_FRAMES, len(ends)))]
    out = Path(out)
    (out / "_tmp").mkdir(parents=True, exist_ok=True)
    reqs = [{"clip": m["clip"], "t": m["t"], "out": str(out / "_tmp" / f"{m['id']}.png"),
             "scale": PHONE_WIDTH / tl.layout(video)["width"]} for m in picks]
    engine.stills(reqs)
    tile([r["out"] for r in reqs], out / "phone.png", 5)
    for f in (out / "_tmp").iterdir():
        f.unlink()
    (out / "_tmp").rmdir()
    return out / "phone.png"


def strips(video, out, windows, engine=None, width=320):
    """One strip per window {clip, t, frames?, fps?}: consecutive frames around t (moments.sequence),
    every window's frames rendered in one engine call."""
    engine, t = engine or Engine(video), tl.load(video)
    seqs = [moments.sequence(t, w["clip"], w["t"], w.get("frames", STRIP_FRAMES), w.get("fps")) for w in windows]
    out = Path(out)
    (out / "_tmp").mkdir(parents=True, exist_ok=True)
    scale = width / tl.layout(video)["width"]
    reqs = [[{**r, "out": str(out / "_tmp" / f"{i:02d}_{k:03d}.png"), "scale": scale} for k, r in enumerate(moments.requests([m]))]
            for i, m in enumerate(seqs)]
    engine.stills([r for rs in reqs for r in rs])
    paths = [tile([r["out"] for r in rs], out / f"{m['id']}.png", len(rs)) for m, rs in zip(seqs, reqs)]
    shutil.rmtree(out / "_tmp")
    return paths


def windows(strip=(), file=None):
    """The strips asked for: --strip CLIP T pairs, then a --windows file's entries."""
    asked = [{"clip": c, "t": t} for c, t in strip or ()] + (json.loads(Path(file).read_text()) if file else [])
    out = []
    for w in asked:
        try:
            out.append({"clip": str(w["clip"]), "t": float(w["t"]),
                        **{k: f(w[k]) for k, f in (("frames", int), ("fps", float)) if k in w}})
        except (TypeError, ValueError, KeyError):
            raise SystemExit(f"strip window {w}: needs a clip and a time t, and frames and fps as numbers")
    return out


def _crop_all(src, boxes, outdir, names):
    """Every crop of one frame in a single ffmpeg call (one process per frame, not per label)."""
    if not boxes:
        return
    split = f"[0:v]split={len(boxes)}" + "".join(f"[s{i}]" for i in range(len(boxes)))
    chains = [f"[s{i}]crop={w}:{h}:{x}:{y}[o{i}]" for i, (x, y, w, h) in enumerate(boxes)]
    cmd = ["-i", str(src), "-filter_complex", ";".join([split, *chains])]
    for i, name in enumerate(names):
        cmd += ["-map", f"[o{i}]", str(outdir / name)]
    proc.ffmpeg(*cmd)


def crops(video, out, below=40, ids=None, engine=None):
    """Full-resolution crops of small labels, and their measured sizes.

    Incremental and deduplicated: a frame whose clip key and frame number are unchanged reuses its
    crops from .cache/crops/, and a label that looks the same (same text and size) in several
    sentences of a chapter is cropped once, with every sentence it appears in listed in the index.
    """
    engine, t = engine or Engine(video), tl.load(video)
    video = Path(video)
    out = Path(out) / "crops"
    out.mkdir(parents=True, exist_ok=True)
    cache = video / ".cache" / "crops"
    cache.mkdir(parents=True, exist_ok=True)
    keys = {c["id"]: render.clip_key(video, t, c["id"], "crops") for c in t["tracks"]["scene"]}
    # the threshold is in the key: a frame measured under another --below kept other labels
    reqs = [{"clip": m["clip"], "t": m["t"], "id": m["id"],
             "key": f"{m['clip']}-{keys[m['clip']]}-{tl.half_up(m['t'] * t['fps'])}-b{below:g}"}
            for m in moments.sentence_ends(t) if not ids or m["id"] in ids]
    todo = [r for r in reqs if not (cache / r["key"] / "boxes.json").exists()]
    if todo:
        frames = engine.boxes_at([{"clip": r["clip"], "t": r["t"], "out": str(cache / r["key"] / "frame.png")}
                                  for r in todo] if engine.boxes_keep_frames else
                                 [{"clip": r["clip"], "t": r["t"]} for r in todo])
        if not engine.boxes_keep_frames:
            engine.stills([{"clip": r["clip"], "t": r["t"], "out": str(cache / r["key"] / "frame.png")} for r in todo])
        for r, f in zip(todo, frames):
            d = cache / r["key"]
            d.mkdir(exist_ok=True)
            kept = []
            for b in f["boxes"]:
                if b["name"] in ("caption", "rect") or b["name"].startswith(("node ", "lane ", "step ")) or b["h"] >= below or b["w"] < 4:
                    continue
                pad = 6
                kept.append({"text": b["name"], "height_px": round(b["h"], 1), "width_px": round(b["w"], 1),
                             "box": [max(0, int(b["x"]) - pad), max(0, int(b["y"]) - pad), int(b["w"]) + 2 * pad, int(b["h"]) + 2 * pad]})
            # identical labels within the frame (the same text and size twice) are cropped once
            uniq = list({(k["text"], k["height_px"], k["width_px"]): k for k in kept}.values())
            _crop_all(d / "frame.png", [(x, y, w, h) for x, y, w, h in (k["box"] for k in uniq)], d,
                      [f"{i + 1:02d}.png" for i in range(len(uniq))])
            (d / "frame.png").unlink(missing_ok=True)
            (d / "boxes.json").write_text(json.dumps([{**k, "file": f"{i + 1:02d}.png"} for i, k in enumerate(uniq)]))
    wanted = {r["key"] for r in reqs}
    if not ids:
        for old in cache.iterdir():
            if old.name not in wanted:
                shutil.rmtree(old, ignore_errors=True)
    for old in out.glob("*.png"):
        old.unlink()
    index, seen = [], {}
    for r in reqs:
        for k in json.loads((cache / r["key"] / "boxes.json").read_text()):
            same = (r["clip"], k["text"], k["height_px"], k["width_px"])
            if same in seen:                       # already cropped from an earlier sentence of this chapter
                seen[same]["sentences"].append(r["id"])
                continue
            name = f"{r['id']}_{k['file']}"
            shutil.copyfile(cache / r["key"] / k["file"], out / name)
            entry = {"file": name, "sentence": r["id"], "sentences": [r["id"]], "text": k["text"],
                     "height_px": k["height_px"], "width_px": k["width_px"]}
            seen[same] = entry
            index.append(entry)
    (out / "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n")
    made = len(todo)
    print(f"crops: {made} frames measured, {len(reqs) - made} unchanged (reused); "
          f"{len(index)} distinct labels")
    return index


def main(args):
    video, out = Path(args.video), Path(args.outdir)
    tl.build(video)                 # as a cut does, so the sheets see the current sources
    out.mkdir(parents=True, exist_ok=True)
    engine = Engine(video)
    wanted = windows(args.strip, args.windows)
    if wanted:
        print("\n".join(map(str, strips(video, out, wanted, engine))))
        return 0
    if not cuts.latest(video, cuts.SCENE_STILLS):
        raise SystemExit("no cut of the scenes yet: run `studio cut VIDEO` first")
    made = chapter_sheets(video, out, args.cut)
    print(f"chapter sheets: {', '.join(made)}")
    print(f"phone sheet: {phone_sheet(video, out, engine)}")
    idx = crops(video, out, args.below, None, engine)
    small = sorted(idx, key=lambda x: x["height_px"])[:3]
    print(f"{len(idx)} label crops in {out / 'crops'}; smallest: " +
          ", ".join(f"{x['text'][:24]!r} {x['height_px']} px" for x in small))
    return 0
