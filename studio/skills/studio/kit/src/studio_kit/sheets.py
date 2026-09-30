"""`studio sheets VIDEO OUTDIR`: what a reviewer looks at, made by seeking to the frames it needs.

  chapters/sN.png   one contact sheet per chapter: a frame near the end of every sentence
  phone.png         a sample of the whole video at 360 px wide, how it reads on a phone
  strip_CLIP_T.png  with --strip CLIP T: 12 consecutive frames around T, to catch pops and overlaps
  crops/            full-resolution crops of every small label (under --below px tall), with
                    crops/index.json giving each one's sentence, text and rendered size at 1080p

A downscaled sheet misjudges text: four frame reviews reported "labels are 15-18 px" from sheets
when the labels measured 26 px. The crops and their sizes are what the frame review judges from.
"""
import json
import math
import subprocess
from pathlib import Path

from . import render
from . import timeline as tl
from .engine import Engine

PHONE_WIDTH = 360
PHONE_FRAMES = 15


def tile(files, out, cols, width=None):
    """Tile images (scaled to one width, so they can be joined) into one sheet with ffmpeg."""
    files = [str(f) for f in files]
    if not files:
        return None
    rows = math.ceil(len(files) / cols)
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for f in files:
        cmd += ["-i", f]
    scale = f"scale={width}:-1," if width else ""
    chain = "".join(f"[{i}:v]{scale}setsar=1[v{i}];" for i in range(len(files)))
    join = "".join(f"[v{i}]" for i in range(len(files)))
    cmd += ["-filter_complex", f"{chain}{join}concat=n={len(files)}:v=1:a=0,tile={cols}x{rows}:padding=4:color=white[o]",
            "-map", "[o]", "-frames:v", "1", str(out)]
    subprocess.run(cmd, check=True)
    return out


def chapter_sheets(video, out, cut=None):
    video, out = Path(video), Path(out)
    n = cut or render.latest_cut(video)
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
    sents = t["tracks"]["narration"]
    picks = [sents[round(i * (len(sents) - 1) / max(1, PHONE_FRAMES - 1))] for i in range(min(PHONE_FRAMES, len(sents)))]
    out = Path(out)
    (out / "_tmp").mkdir(parents=True, exist_ok=True)
    reqs = []
    for s in picks:
        c = tl.clip(t, s["clip"])
        reqs.append({"clip": s["clip"], "t": round(max(s["start"], s["end"] - 0.15) - c["start"], 3),
                     "out": str(out / "_tmp" / f"{s['id']}.png"), "scale": PHONE_WIDTH / tl.layout(video)["width"]})
    engine.stills(reqs)
    tile([r["out"] for r in reqs], out / "phone.png", 5)
    for f in (out / "_tmp").iterdir():
        f.unlink()
    (out / "_tmp").rmdir()
    return out / "phone.png"


def strip(video, out, clip, t0, engine=None, frames=12, width=320):
    engine, t = engine or Engine(video), tl.load(video)
    fps = t["fps"]
    out = Path(out)
    (out / "_tmp").mkdir(parents=True, exist_ok=True)
    reqs = [{"clip": clip, "t": round(t0 + (i - frames // 2) / fps, 4), "out": str(out / "_tmp" / f"{i:02d}.png"),
             "scale": width / tl.layout(video)["width"]} for i in range(frames)]
    reqs = [r for r in reqs if r["t"] >= 0]
    engine.stills(reqs)
    path = tile([r["out"] for r in reqs], out / f"strip_{clip}_{t0}.png", len(reqs))
    for f in (out / "_tmp").iterdir():
        f.unlink()
    (out / "_tmp").rmdir()
    return path


def crops(video, out, below=40, ids=None, engine=None):
    """Full-resolution crops of small labels, and their measured sizes."""
    engine, t = engine or Engine(video), tl.load(video)
    out = Path(out) / "crops"
    out.mkdir(parents=True, exist_ok=True)
    reqs = []
    for s in t["tracks"]["narration"]:
        if ids and s["id"] not in ids:
            continue
        c = tl.clip(t, s["clip"])
        reqs.append({"clip": s["clip"], "t": round(max(s["start"], s["end"] - 0.15) - c["start"], 3), "id": s["id"],
                     "text": s["caption"]})
    frames = engine.boxes_at([{"clip": r["clip"], "t": r["t"]} for r in reqs])
    full = [{"clip": r["clip"], "t": r["t"], "out": str(out / f"_{r['id']}.png")} for r in reqs]
    engine.stills(full)
    index = []
    for r, f in zip(reqs, frames):
        n = 0
        for b in f["boxes"]:
            if b["name"] in ("caption", "rect") or b["name"].startswith(("node ", "lane ", "step ")) or b["h"] >= below or b["w"] < 4:
                continue
            n += 1
            name = f"{r['id']}_{n:02d}.png"
            pad = 6
            x, y = max(0, int(b["x"]) - pad), max(0, int(b["y"]) - pad)
            w, h = int(b["w"]) + 2 * pad, int(b["h"]) + 2 * pad
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out / f"_{r['id']}.png"), "-vf",
                            f"crop={w}:{h}:{x}:{y}", str(out / name)], check=True)
            index.append({"file": name, "sentence": r["id"], "text": b["name"], "height_px": round(b["h"], 1),
                          "width_px": round(b["w"], 1)})
    for r in reqs:
        (out / f"_{r['id']}.png").unlink(missing_ok=True)
    (out / "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n")
    return index


def main(args):
    video, out = Path(args.video), Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    engine = Engine(video)
    if args.strip:
        print(strip(video, out, args.strip[0], float(args.strip[1]), engine))
        return 0
    if not render.latest_cut(video):
        raise SystemExit("no cut yet: run `studio cut VIDEO` first")
    made = chapter_sheets(video, out, args.cut)
    print(f"chapter sheets: {', '.join(made)}")
    print(f"phone sheet: {phone_sheet(video, out, engine)}")
    idx = crops(video, out, args.below, None, engine)
    small = sorted(idx, key=lambda x: x["height_px"])[:3]
    print(f"{len(idx)} label crops in {out / 'crops'}; smallest: " +
          ", ".join(f"{x['text'][:24]!r} {x['height_px']} px" for x in small))
    return 0
