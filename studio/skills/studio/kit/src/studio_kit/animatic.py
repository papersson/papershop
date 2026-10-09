"""The animatic: the video's stills (or boards) held to the narration, with its audio, before anything
is animated. It is the first time the whole piece plays at its real length, so pacing problems show
up while they are cheap: a chapter that runs long, a stretch where the picture never changes while
the voice talks, a sentence with nothing on screen.

Each sentence's still holds from that sentence's start until the next sentence starts (the first
still of a chapter also covers the chapter's lead-in). The animatic is a cut of kind "animatic":
it is shown on the review page and never chosen by publish or frame review.
"""
import json
import shutil
import time
from pathlib import Path

from . import proc, render, settings
from . import timeline as tl

SCALE = 0.5               # animatic stills: 960×540 from a 1080p layout
STILL_RUN = 12.0          # seconds of one unchanged picture worth reporting


def segments(timeline, stills):
    """[(still file, seconds)] covering the whole timeline, in order."""
    by_id = {s["id"]: s for s in stills}
    marks = []
    for s in timeline["tracks"]["narration"]:
        if s["id"] in by_id:
            marks.append((s["start"], by_id[s["id"]]["file"]))
    for c in timeline["tracks"]["scene"]:     # a chapter's lead-in shows its first still
        first = next((m for m in marks if m[0] >= c["start"]), None)
        if first and first[0] > c["start"]:
            marks.append((c["start"], first[1]))
    marks.sort()
    if not marks:
        raise SystemExit("no stills to hold: make a boards or stills cut first")
    if marks[0][0] > 0:
        marks.insert(0, (0.0, marks[0][1]))
    out = []
    for (t, f), nxt in zip(marks, marks[1:] + [(timeline["duration"], None)]):
        if nxt[0] > t:
            out.append((f, nxt[0] - t))
    return out


def stage_digest(still, stage_fraction):
    """A hash of the still above the caption band: captions change every sentence, so hashing the
    whole frame would never find the same picture twice."""
    r = proc.ffmpeg("-i", still, "-vf", f"crop=iw:trunc(ih*{stage_fraction:.4f}/2)*2:0:0", "-f", "md5", "-",
                    capture_output=True, text=True)
    return r.stdout.strip()


def pacing(video, timeline, cut_dir, stills, segs, boards=False):
    """The numbers worth reading before animating."""
    cfg = settings.load(video)
    lay = tl.layout(video)
    stage = (lay["height"] - lay["band"]["height"]) / lay["height"]
    digest = {}
    for s in stills:
        p = cut_dir / s["file"]
        digest[s["file"]] = stage_digest(p, stage) if p.exists() else s["file"]
    runs, current, length = [], None, 0.0
    t = 0.0
    start = 0.0
    for f, dur in segs:
        d = digest.get(f, f)
        if d != current:
            if current is not None:
                runs.append((start, length))
            current, length, start = d, 0.0, t
        length += dur
        t += dur
    runs.append((start, length))
    longest = max(runs, key=lambda r: r[1])
    chapters = [{"id": c["id"], "title": c["title"], "seconds": round(c["end"] - c["start"], 1)} for c in timeline["tracks"]["scene"]]
    from . import boards as bd
    cov = bd.coverage(video, timeline)
    on_board = {c["id"] for c in timeline["tracks"]["scene"] if boards or not render.has_scene(video, c["id"])}
    clip_of = {s["id"]: s["clip"] for s in timeline["tracks"]["narration"]}
    report = {
        "seconds": round(timeline["duration"], 1),
        "target_minutes": cfg.get("target_minutes"),
        "chapters": chapters,
        "longest_unchanged": {"at": round(longest[0], 1), "seconds": round(longest[1], 1)},
        "unchanged_runs": [{"at": round(a, 1), "seconds": round(b, 1)} for a, b in runs if b >= STILL_RUN],
        "no_picture": [k for k, v in cov.items() if v is None and clip_of[k] in on_board],
    }
    return report


def make(video, boards=False):
    video = Path(video).resolve()
    timeline = tl.build(video)
    if tl.timing(video, timeline) != "narrated":
        raise SystemExit("the timeline is estimated: run `studio narrate VIDEO` first, so the animatic plays the real voice")
    from . import boards as bd
    from .engine import Engine
    bd.write_notes(video)
    n = render.latest_cut(video) + 1
    d = render.cuts_dir(video) / f"cut{n}"
    if d.exists():
        shutil.rmtree(d)
    (d / "stills").mkdir(parents=True)
    t0 = time.monotonic()
    # Its own stills, at half resolution so text stays readable: scenes where they exist, boards
    # elsewhere (or boards throughout), cached like any other stills.
    reqs = render.still_requests(timeline, d / "stills")
    for r in reqs:
        r["scale"] = SCALE
    made, reused = render.cached_stills(video, timeline, Engine(video), reqs, boards=boards,
                                        cache_name="animatic-board-stills" if boards else "animatic-stills")
    notes = bd.notes(video)
    stills = [{k: r[k] for k in ("id", "clip", "caption", "at")} | {"file": f"stills/{r['id']}.jpg"}
              | ({"note": notes[r["id"]]} if r["id"] in notes else {}) for r in reqs]
    segs = segments(timeline, stills)
    lst = d / "segments.txt"
    lst.write_text("".join(f"file '{(d / f).resolve()}'\nduration {sec:.3f}\n" for f, sec in segs)
                   + f"file '{(d / segs[-1][0]).resolve()}'\n")
    silent = d / "silent.mp4"
    proc.ffmpeg("-f", "concat", "-safe", "0", "-i", lst, "-vf", f"fps={timeline['fps']},format=yuv420p",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", silent)
    sound = render.mixed_sound(video, timeline)
    proc.ffmpeg("-i", silent, "-i", sound, "-map", "0:v", "-map", "1:a", "-c", "copy", "-t", f"{timeline['duration']:.3f}",
                "-movflags", "+faststart", d / "video.mp4")
    for f in (lst, silent):
        f.unlink()
    report = pacing(video, timeline, d, stills, segs, boards)
    from .cuts import media_info
    from .review_state import fingerprint
    from .workspace import atomic_json
    atomic_json(d / "timeline.json", timeline)
    record = {
        "source_revision": fingerprint(video, frames=True), "media": media_info(d / "video.mp4"),
        "final": False, "cut": n, "kind": "animatic", "pictures": "boards" if boards else "scenes, boards where none",
        "created": time.strftime("%Y-%m-%d %H:%M:%S"), "quality": "draft", "video": "video.mp4",
        "duration": timeline["duration"],
        "chapters": [{"id": c["id"], "title": c["title"], "start": c["start"]} for c in timeline["tracks"]["scene"]],
        "clips": [], "changed": [], "stills": stills, "changelog": [], "pacing": report,
        "seconds": {"animatic": round(time.monotonic() - t0, 1), "stills_rendered": made, "stills_reused": reused},
    }
    (d / "cut.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    return record


def describe(report):
    m, s = divmod(int(round(report["seconds"])), 60)
    lines = [f"runtime {m}:{s:02d}" + (f" (target {report['target_minutes']} min)" if report.get("target_minutes") else "")]
    lines.append("chapters: " + ", ".join(f"{c['id']} {c['seconds']:.0f}s" for c in report["chapters"]))
    lu = report["longest_unchanged"]
    lines.append(f"longest unchanged picture: {lu['seconds']:.1f}s at {lu['at']:.1f}s")
    if report["unchanged_runs"]:
        lines.append(f"pictures held {STILL_RUN:.0f}s or more: " + ", ".join(f"{r['seconds']:.0f}s at {r['at']:.0f}s" for r in report["unchanged_runs"]))
    if report["no_picture"]:
        lines.append(f"sentences with no board and no screen note: {', '.join(report['no_picture'][:10])}")
    return lines


def main(args):
    rec = make(args.video, args.boards)
    print(f"animatic cut {rec['cut']} ({rec['pictures']}): {rec['media']['width']}×{rec['media']['height']}")
    for line in describe(rec["pacing"]):
        print("  " + line)
    return 0
