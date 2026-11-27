"""The attention audit: what a staged frame should make true, measured on a chapter's render.

One thing lit, one place changing, short eye travel, time between onsets, a large subject and
stillness in every marked rest. These are references/staging.md's measures, ported from the Save
film's audit (click-save-film/tools/attention.py, which held Act 4 to them), so a chapter agent can
see a staging mistake on its own render before any reviewer does.

  studio attention VIDEO [--chapter CLIP] [--where] [--json FILE]

Renders each chapter as a draft (a chapter agent's in its private work folder), samples it at
5 fps, 480 by 270, in tiles of 15 px (32 by 18), and prints one row per chapter against the aims.
Motion inside a marked rest is a failure (exit 1); the other aims are warnings, because the numbers
are a proxy for where an eye goes: --where lists the clip seconds behind each one, to look at the
frames before trusting them. A camera move reads as movement over the whole frame and is left out
of `split`; a thing travelling under a following camera can read as a far jump.

Aims, with the Save film's Act 4 before staging in brackets: lit_over2 under 15% (82%), split under
8% (26%), far_jumps under 10% (27%), fast_onsets under 10% (22%), hero at least 3% (1.6%),
rest_motion 0 s.
"""
import json
import tempfile
from pathlib import Path

FPS, W, H, T = 5, 480, 270, 15
GX, GY = W // T, H // T

# (measure, aim, kind): kind "max" or "min" is a warning when missed, "fail" fails the chapter.
AIMS = [("lit_over2", 0.15, "max"), ("split", 0.08, "max"), ("far_jumps", 0.10, "max"),
        ("fast_onsets", 0.10, "max"), ("hero", 0.03, "min"), ("rest_motion", 0.0, "fail")]


def _np():
    try:
        import numpy as np
    except ImportError:
        raise SystemExit("the attention audit needs numpy, which the kit's audio extra installs: script/bootstrap")
    return np


def tiles(a):
    """(H, W) -> (GY, GX) tile means."""
    return a.reshape(GY, T, GX, T).mean(axis=(1, 3))


def comps(mask):
    """Connected components, 8-neighbour and bridging one-tile gaps, as lists of (y, x) tiles."""
    m = mask.copy()
    out = []
    for y, x in zip(*mask.nonzero()):
        if not m[y, x]:
            continue
        st, c = [(y, x)], []
        m[y, x] = False
        while st:
            cy, cx = st.pop()
            c.append((cy, cx))
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < GY and 0 <= nx < GX and m[ny, nx]:
                        m[ny, nx] = False
                        st.append((ny, nx))
        out.append(c)
    return out


def centroid(c):
    ys, xs = zip(*c)
    return (sum(xs) / len(xs) + .5) / GX, (sum(ys) / len(ys) + .5) / GY


def distance(a, b):
    """Eye travel between two frame positions, as a share of the frame's width."""
    return ((a[0] - b[0]) ** 2 + ((a[1] - b[1]) * 9 / 16) ** 2) ** .5


def analyse(images):
    """One row per frame from RGB arrays of shape (H, W, 3)."""
    np = _np()
    rows, prev = [], None
    for im in images:
        im = np.asarray(im, float)
        lum = im @ np.array([.2126, .7152, .0722])
        sat = im.max(2) - im.min(2)
        ground = np.median(lum)
        drawn = tiles((np.abs(lum - ground) > 14).astype(float)) > .02                    # anything visibly there
        strong = tiles(((lum > 150) | ((sat > 70) & (lum > 110))).astype(float)) > .03    # full ink or a colour
        lit = comps(strong)
        r = dict(drawn=float(drawn.mean()), lit=len(lit), share=float(strong.sum() / max(1, drawn.sum())),
                 big=max((len(c) for c in lit), default=0) / (GX * GY))
        if prev is not None:
            d = np.abs(lum - prev)
            ch = (tiles(d) > 3.0) | (tiles((d > 28).astype(float)) > .015)
            cc = comps(ch)
            cs = [centroid(c) for c in cc]
            r.update(moving=int(ch.sum()), whole=bool(ch.mean() > .35), peak=float(tiles(d).max()),
                     spread=max((distance(a, b) for a in cs for b in cs), default=0),
                     at=centroid([t for c in cc for t in c]) if cc else None, regions=len(cc))
        else:
            r.update(moving=0, whole=False, spread=0, at=None, regions=0, peak=0.0)
        prev = lum
        rows.append(r)
    # An encoder keyframe refreshes lit areas by a few levels for one frame: a lone, faint blip is not motion.
    for i in range(1, len(rows) - 1):
        r = rows[i]
        if r["moving"] and not rows[i - 1]["moving"] and not rows[i + 1]["moving"] and r["peak"] < 9:
            r.update(moving=0, whole=False, spread=0, at=None, regions=0)
    return rows


def _median(v):
    v = sorted(v)
    if not v:
        return 0.0
    m = len(v) // 2
    return float(v[m]) if len(v) % 2 else (v[m - 1] + v[m]) / 2


def summarise(rows, name, rests=(), where=False):
    """The measures for one chapter. rests are (start, end) clip seconds of its marked rests."""
    n = max(1, len(rows))
    mv = [r for r in rows if r["moving"] and not r["whole"]]
    notes = []
    onsets, quiet, holds = [], 99, []      # an onset: movement beginning after at least 0.4 s of stillness
    for i, r in enumerate(rows):
        if r["moving"]:
            if quiet >= 2 and r["at"]:
                onsets.append((i / FPS, r["at"]))
            if quiet and quiet < 99:
                holds.append(quiet / FPS)
            quiet = 0
        else:
            quiet += 1
    pairs = list(zip(onsets, onsets[1:]))
    jumps = [distance(a[1], b[1]) for a, b in pairs]
    gaps = [b[0] - a[0] for a, b in pairs]
    rest_motion = 0.0
    for a, b in rests:                     # the first 0.3 s of a rest is allowed for a landing to finish
        hit = [i / FPS for i in range(int((a + .3) * FPS) + 1, int(b * FPS)) if 0 <= i < len(rows) and rows[i]["moving"]]
        rest_motion += len(hit) / FPS
        if hit:
            notes.append(f"motion inside the rest {a:.1f}-{b:.1f} s at " + ", ".join(f"{t:.1f}" for t in hit[:8]))
    if where:
        def runs(ts):
            return ", ".join(f"{t:.1f}" for t in ts[:40]) + (" ..." if len(ts) > 40 else "")
        sp = [i / FPS for i, r in enumerate(rows) if r["moving"] and not r["whole"] and r["spread"] > .3]
        if sp:
            notes.append("change in two far places at " + runs(sp))
        l3 = [i / FPS for i, r in enumerate(rows) if r["lit"] > 2]
        if l3:
            notes.append(f"more than two lit things for {len(l3) / FPS:.0f} s, e.g. at " + runs(l3[::10]))
        fj = [f"{b[0]:.1f} (from {a[1][0]:.2f},{a[1][1]:.2f} to {b[1][0]:.2f},{b[1][1]:.2f})"
              for (a, b), j in zip(pairs, jumps) if j > .3]
        if fj:
            notes.append("far jumps at " + "; ".join(fj[:30]))
        fo = [f"{b[0]:.1f}" for (a, b), g in zip(pairs, gaps) if g < 1.2]
        if fo:
            notes.append("onsets under 1.2 s after the last at " + ", ".join(fo[:40]))
        wf = [i / FPS for i, r in enumerate(rows) if r["whole"]]
        if wf:
            notes.append("whole frame moving (a camera move or a join) at " + runs(wf[::3]))
    return dict(
        clip=name, seconds=len(rows) / FPS, rest_motion=rest_motion, notes=notes,
        lit_things=_median([r["lit"] for r in rows]),                      # separate things at full strength (want 1-2)
        lit_over2=sum(1 for r in rows if r["lit"] > 2) / n,                # share of time with more than two
        focus_share=_median([r["share"] for r in rows]),                   # lit over drawn (high: little furniture)
        drawn=_median([r["drawn"] for r in rows]),
        hero=_median([r["big"] for r in rows]),                            # the largest lit thing, share of frame
        split=sum(1 for r in mv if r["spread"] > .3) / max(1, len(mv)),    # moving frames changing in two far places
        whole_frame_s=sum(1 for r in rows if r["whole"]) / FPS,
        still=sum(1 for r in rows if not r["moving"]) / n, onsets=len(onsets),
        onset_gap=_median(gaps), fast_onsets=sum(1 for g in gaps if g < 1.2) / max(1, len(gaps)),
        jump=_median(jumps), far_jumps=sum(1 for j in jumps if j > .3) / max(1, len(jumps)),
        holds_2s=sum(1 for h in holds if h >= 2), longest_hold=max(holds, default=0))


def verdict(s):
    """(failures, warnings): the aims this chapter's measures miss, each as one line."""
    fails, warns = [], []
    for key, aim, kind in AIMS:
        v = s[key]
        if kind == "fail" and v > aim:
            fails.append(f"{key} {v:.1f} s, aim {aim:g} s: the picture moves during a marked rest")
        elif kind == "max" and v > aim:
            warns.append(f"{key} {v:.0%}, aim under {aim:.0%}")
        elif kind == "min" and v < aim:
            warns.append(f"{key} {v:.1%}, aim at least {aim:.0%}")
    return fails, warns


def read_frames(movie):
    """RGB frames of a video at FPS, W by H, through ffmpeg."""
    np = _np()
    from . import proc
    raw = proc.ffmpeg("-i", movie, "-vf", f"fps={FPS},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
                      capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)


def rests_of(timeline, clip):
    ch = next(c for c in timeline["tracks"]["scene"] if c["id"] == clip)
    return [(n["pause"]["start"] - ch["start"], n["pause"]["end"] - ch["start"])
            for n in timeline["tracks"]["narration"] if n.get("clip") == clip and n.get("pause")]


def audit(folder, timeline, clips, where=False):
    from .engine import Engine
    engine = Engine(folder)
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        for clip in clips:
            movie = Path(tmp) / f"{clip}.mp4"
            engine.render(clip, str(movie), "draft")
            s = summarise(analyse(read_frames(movie)), clip, rests_of(timeline, clip), where)
            s["fail"], s["warn"] = verdict(s)
            out.append(s)
    return out


COLS = [("clip", "{}"), ("seconds", "{:.0f}"), ("lit_over2", "{:.0%}"), ("split", "{:.0%}"), ("far_jumps", "{:.0%}"),
        ("fast_onsets", "{:.0%}"), ("hero", "{:.1%}"), ("rest_motion", "{:.1f}"), ("still", "{:.0%}"),
        ("onsets", "{}"), ("onset_gap", "{:.1f}"), ("whole_frame_s", "{:.1f}")]


def report(rows):
    lines = [" ".join(f"{k:>12}" for k, _ in COLS)]
    for s in rows:
        lines.append(" ".join(f"{f.format(s[k]):>12}" for k, f in COLS))
        lines += [f"  FAIL {x}" for x in s["fail"]] + [f"  warn {x}" for x in s["warn"]] + [f"  {x}" for x in s["notes"]]
    return "\n".join(lines)


def main(args):
    from . import timeline as tl
    video = Path(args.video)
    if args.chapter:
        from . import chapter
        with chapter.working_copy(video, args.chapter) as (work, timeline):
            rows = audit(work, timeline, [args.chapter], args.where)
        dest = video / ".cache" / "chapters" / args.chapter / "attention.json"
    else:
        timeline = tl.load(video)
        rows = audit(video, timeline, [c["id"] for c in timeline["tracks"]["scene"]], args.where)
        dest = video / ".cache" / "attention.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(rows, indent=1))
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=1))
    print(report(rows))
    print("The numbers point at moments to look at; staging.md has the rules behind each aim.")
    return 1 if any(s["fail"] for s in rows) else 0
