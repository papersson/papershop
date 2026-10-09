"""`studio review-motion VIDEO [--cut N] [--result FILE]`: a motion review of a cut, judged from
consecutive frames, and the rule that stops it.

Stills near a sentence's end could not see a contact or a pop, so a motion review reads windows of
consecutive frames: one around every named event of the cut's beat sheet (WINDOW_FRAMES at about
WINDOW_FPS, the contact the fourth, so anticipation shows before it and the settle after), and one
over every significant move (motion.moves) no event window overlaps. Every frame comes from the cut
judged: its clip renders where they are still cached for its keys, else its own video.mp4; its
beat sheet is the cut's timeline snapshot. So the bundle carries the cut's own revision, and a
result for a cut older than the sources is recorded as stale (the kind's freshness, reviews.py).

research/motion_review/cut<N>-<rev12>/
  manifest.json   cut, revision, round and cap, and where everything is
  windows.json    [{name, kind: event|move, clip, time, t, contact_frame, frames, times, fps, sheet,
                    narration: {sentence, said, word?, pause?}, sfx: [{type, cue, time, frame}]}]
  sheets/         one strip per window, its frames left to right
  SCRIPT.md       the cut's Script section
  previous.json   the last round's findings, when there is one (the prompt asks about regressions)
  prompt.md       prompts/motion_review.md, with comic.md's questions when tone is comic
  result.md, findings.json   the imported response and its findings [{severity, window, t, frame, text}]

The stop rule: a motion review ends at a round with no must-fix findings, or at video.json
motion_rounds (default 2) rounds of the cut lineage, whichever comes first. In one long session the
loop ran for hours because should-fix findings plateaued at 25 to 45 a round. On ending, the last
round's should-fix and nit findings go on the cut record as known_issues (and on to later cuts), so
the desk shows them and nobody raises them again. The receipt says how it ended: "passed" (nothing
left), "known-issues" (no must-fix, smaller findings left) or "findings" (must-fix open; at the cap,
`stopped: "cap"`, reported to the main session as open, never passed).
"""
import json
import math
import re
import shutil
from pathlib import Path

from . import cuts, moments, motion, proc, settings
from . import timeline as tl
from .env import ROOT
from .review_state import changed_since, check_cap, next_round, read, record, revision, stands, start_round
from .reviews import KINDS
from .workspace import atomic_json

KIND = KINDS["motion"]
WINDOW_FRAMES = 12          # frames in an event's window
WINDOW_FPS = 15             # about this many a second: the timeline's fps over a whole step of frames
LEAD = 3                    # frames before the contact: it is the fourth
SETTLE = 5                  # frames after a move ends, at least, so its settle shows
MOVE_MAX_FRAMES = 24        # a long move's window stops here
SHEET_WIDTH = 320           # pixels a frame is wide on a sheet
SHEET_COLS = 12
SEVERITIES = {"must": "must-fix", "should": "should-fix", "nit": "nit"}


def bundle_root(video):
    return Path(video) / "research" / "motion_review"


# --- frames from the cut ---------------------------------------------------------------------------

def source(video, n, rec, t, clip):
    """(file, the clip's first frame in it) holding the cut's frames of `clip`: its clip render when
    it is still cached under the key the cut recorded, else the cut's own video.mp4, else None."""
    c = tl.clip(t, clip)
    key = next((x["key"] for x in rec.get("clips", []) if x["id"] == clip), None)
    f = Path(video) / ".cache" / "clips" / f"{clip}-{rec.get('quality', 'draft')}-{key}.mp4"
    if key and f.exists():
        return f, 0
    movie = Path(video) / "cuts" / f"cut{n}" / "video.mp4"
    return (movie, tl.half_up(c["start"] * t["fps"])) if movie.exists() else None


def sheet(path, frames, fps, out, width=SHEET_WIDTH):
    """Frames `frames` of `path` (frame numbers in that file, ascending) tiled into one strip: a seek
    to half a frame before the first (frame-accurate), then each picked by its count from there."""
    lo, cols = frames[0], min(SHEET_COLS, len(frames))
    pick = "+".join(f"eq(n\\,{f - lo})" for f in frames)
    proc.ffmpeg("-ss", f"{max(0.0, (lo - 0.5) / fps):.4f}", "-i", str(path), "-vf",
                f"select='{pick}',scale={width}:-2,tile={cols}x{math.ceil(len(frames) / cols)}:padding=4:color=white",
                "-frames:v", "1", str(out))
    return out


# --- windows -----------------------------------------------------------------------------------------

def _step(t):
    return max(1, round(t["fps"] / WINDOW_FPS))


def _narration(t, at):
    """What the narration says at video time `at`: the sentence it falls in (with the word, when
    timed), else the pause after the sentence before it."""
    said = t["tracks"]["narration"]
    s = next((s for s in said if s["start"] <= at <= s["end"]), None)
    if s:
        word = next((w["w"] for w in s.get("words") or [] if w["start"] <= at <= w["end"]), None)
        return {"sentence": s["id"], "said": s["caption"], **({"word": word} if word else {})}
    before = [s for s in said if s["end"] < at]
    return {"sentence": before[-1]["id"], "said": before[-1]["caption"], "pause": True} if before else {"sentence": None, "said": ""}


def _sfx(video, t, lo, hi):
    """The effects of audio/sfx.json that land between video times lo and hi on the cut's timeline."""
    p = Path(video) / "audio" / "sfx.json"
    if not p.exists():
        return []
    from .sfx import _time
    out = []
    for c in json.loads(p.read_text()):
        at = _time(c["t"], t)
        if at is not None and lo - 1e-6 <= at <= hi + 1e-6:
            out.append({"type": c.get("type"), "cue": c["t"] if isinstance(c["t"], str) else None,
                        "time": round(at, 3), "frame": tl.half_up(at * t["fps"])})
    return out


def _window(video, t, c, name, kind, local, frames, lead):
    """A window entry: `frames` frames at the window fps from `lead` before clip time `local`."""
    step = _step(t)
    m = moments.sequence(t, c["id"], local, frames, t["fps"] / step, "motion", before=lead)
    first = tl.half_up(c["start"] * t["fps"])
    numbers = sorted({first + tl.half_up(x * t["fps"]) for x in m["frames"]})
    contact = first + tl.half_up(local * t["fps"])
    times = [round(f / t["fps"], 3) for f in numbers]
    return {"name": name, "kind": kind, "clip": c["id"], "time": round(contact / t["fps"], 3), "t": round(local, 3),
            "contact_frame": contact, "frames": numbers, "times": times, "fps": round(t["fps"] / step, 3),
            "sheet": f"sheets/{name}.png", "narration": _narration(t, contact / t["fps"]),
            "sfx": _sfx(video, t, times[0], times[-1])}


def windows(video, n, rec, t):
    """The cut's motion windows, in time order: every named event of its beat sheet (not the reveal:
    holds), then every significant move in its frames that no event window overlaps."""
    step, fps = _step(t), t["fps"]
    out, names = [], set()

    def unique(name):
        name = re.sub(r"[^\w.-]+", "-", name)
        while name in names:
            name += "_"
        names.add(name)
        return name
    for ev in tl.events(video, t):
        if ev["name"].startswith("reveal:") or ev["clip"] is None:
            continue
        c = tl.clip(t, ev["clip"])
        local = (ev["frame"] - tl.half_up(c["start"] * fps)) / fps
        out.append(_window(video, t, c, unique(ev["name"]), "event", local, WINDOW_FRAMES, LEAD))
    lay = tl.layout(video)
    for c in t["tracks"]["scene"]:
        src = source(video, n, rec, t, c["id"])
        if src is None:
            raise SystemExit(f"cut {n}'s video and its clip renders are gone (studio clean --videos removes them); "
                             "make a fresh cut")
        mine = [w for w in out if w["clip"] == c["id"] and w["kind"] == "event"]
        for a, b, _ in motion.moves(motion.file_signal(src[0], t, lay, src[1], tl.frames(t, c["id"])[1])):
            lo, hi = c["start"] + a, c["start"] + b
            if any(w["times"][0] <= hi and lo <= w["times"][-1] for w in mine):
                continue
            frames = min(MOVE_MAX_FRAMES, max(WINDOW_FRAMES, LEAD + math.ceil((b - a) * fps / step) + SETTLE))
            out.append(_window(video, t, c, unique(f"move_{c['id']}_{a:.1f}"), "move", a, frames, LEAD))
    return sorted(out, key=lambda w: (w["frames"][0], w["name"]))


# --- the reviewer's response ------------------------------------------------------------------------

_SEVERITY = re.compile(r"\b(must|should)[\s_-]*fix\b|\bnits?\b", re.I)


def parse(text, names=()):
    """The findings in a response: [{severity, window, t, frame, text}], from lines that start with
    a severity (after any bullet, number or markdown) or end with "Severity: …". Tolerates drift:
    any letter case, "|", "—", ":" or "," between the fields, bold, and a window named anywhere in
    the line (the longest known name wins). Also the gags of a comic review: [{window, score, text}]."""
    findings, gags = [], []
    known = sorted(names, key=len, reverse=True)
    for raw in text.splitlines():
        line = re.sub(r"[*`]", "", raw).strip()
        line = re.sub(r"^(?:[-+>]|\d+[.)])\s*", "", line).strip()
        if re.match(r"^gag\b", line, re.I):
            score = re.search(r"\b([1-5])\s*/\s*5\b", line)
            if score:
                window = next((w for w in known if w in line), None)
                gags.append({"window": window, "score": int(score.group(1)), "text": _rest(line, window, score.group(0), r"^gag\b")})
            continue
        head = _SEVERITY.match(line)
        tail = re.search(r"severity\s*:?\s*(must[\s_-]*fix|should[\s_-]*fix|nit)\s*\.?$", line, re.I)
        m = head or tail
        if not m or re.match(r"^(must|should)[\s_-]*fix\s+\d+\s*[·,]", line, re.I):    # the counts line
            continue
        word = (tail.group(1) if tail and not head else m.group(0)).lower()
        severity = SEVERITIES["nit" if word.startswith("nit") else word.split()[0].split("-")[0].split("_")[0]]
        window = next((w for w in known if re.search(rf"(?<![\w.-]){re.escape(w)}(?![\w-])", line)), None)
        t = re.search(r"(?<![\w.])(\d+(?:\.\d+)?)\s*s\b", line)
        frame = re.search(r"\bframes?\s*#?\s*(\d+)", line, re.I)
        body = line[head.end():] if head else line[:tail.start()]
        findings.append({"severity": severity, "window": window, "t": float(t.group(1)) if t else None,
                         "frame": int(frame.group(1)) if frame else None,
                         "text": _rest(body, window, t.group(0) if t else None, frame.group(0) if frame else None)})
    return findings, gags


def _rest(line, *drop):
    """The line without its fields and the separators they leave behind."""
    for d in drop:
        if d:
            line = re.sub(d, "", line, count=1, flags=re.I) if d.startswith("^") else line.replace(d, "", 1)
    parts = [p.strip(" .,:;") for p in re.split(r"\s*(?:\||—|–|\s-\s)\s*", line)]
    return " · ".join(p for p in parts if p).strip(" ·:,")


# --- the stop rule's record on the cuts --------------------------------------------------------------

def write_known_issues(video, n, issues):
    """The known issues on cut N's record and every later cut's, replacing what was there."""
    for m, rec in cuts.records(video).items():
        if m >= n and rec:
            atomic_json(Path(video) / "cuts" / f"cut{m}" / "cut.json", {**rec, "known_issues": issues})


def previous(video, current):
    """The findings.json of this lineage's last motion round, or None (no round yet, a waiver, or a
    round from before a structural revision)."""
    rec = read(video, "motion")
    if not rec.get("round") or not stands(video, rec, KIND, current):
        return None
    p = Path(str(rec["detail"])).with_name("findings.json")
    return json.loads(p.read_text()) if p.exists() else None


def comic_questions():
    """comic.md's "Motion review: comic questions" section, read when the bundle is made."""
    from .script import sections
    part = sections((ROOT / "references" / "styles" / "comic.md").read_text()).get("Motion review: comic questions")
    if not part:
        raise SystemExit("references/styles/comic.md has no '## Motion review: comic questions' section")
    return part


def prompt(cfg, judged, prior):
    text = (ROOT / "prompts" / "motion_review.md").read_text()
    if cfg.get("tone") == "comic":
        text += ("\n\nThis video's tone is comic. " + comic_questions().split("\n", 1)[1].strip() +
                 "\n\nScore every gag on a line of its own: GAG | window name | n/5 | the reason in one line. "
                 "A gag scoring 2 or less is also a MUST FIX: cut or rebuild it.\n")
    if prior and prior.get("findings"):
        text += (f"\n\nFindings from the last round (round {prior.get('round', '?')}, cut {prior.get('cut', '?')}); "
                 "check each for a regression:\n" + "\n".join(
                     f"- {f['severity'].upper().replace('-', ' ')} | {f.get('window') or '?'} | {f.get('t')} s | "
                     f"frame {f.get('frame')} | {f['text']}" for f in prior["findings"]) + "\n")
    return text + f"\nInclude this exact line in your result: REVISION: {judged}\n"


# --- the command ------------------------------------------------------------------------------------

def main(args):
    video = Path(args.video).resolve()
    cfg = settings.load(video)
    n = args.cut or cuts.latest(video, cuts.RENDERED)
    cut = video / "cuts" / f"cut{n}"
    if not n or not (cut / "cut.json").exists():
        raise SystemExit("make a cut (studio cut VIDEO) before preparing its motion review")
    rec = json.loads((cut / "cut.json").read_text())
    if cuts.kind(rec) not in cuts.RENDERED:
        raise SystemExit(f"cut {n} is a {cuts.kind(rec)} cut: a motion review needs a rendered one (studio cut VIDEO)")
    judged, current = rec.get("source_revision"), revision(video, KIND)
    if not judged:
        raise SystemExit(f"cut {n} predates review fingerprints; make a fresh cut")
    stale = judged != current
    changed = changed_since(video, n) if stale else None
    bundle = bundle_root(video) / f"cut{n}-{judged[:12]}"
    manifest = bundle / "manifest.json"
    cap = KIND.rounds.cap(cfg)
    if args.result:
        return imported(video, n, bundle, manifest, Path(args.result), cfg, cap, stale, changed)
    number = next_round(video, KIND, judged)
    check_cap(video, KIND, number, judged, cfg)
    snapshot = cut / "timeline.json"
    if not snapshot.exists():
        raise SystemExit(f"cut {n} kept no timeline snapshot; make a fresh cut")
    t = json.loads(snapshot.read_text())
    if (bundle / "result.md").exists():
        raise SystemExit(f"cut {n} has had its motion review ({bundle / 'findings.json'}); make a fresh cut for the next round")
    if bundle.exists():
        shutil.rmtree(bundle)
    (bundle / "sheets").mkdir(parents=True)
    found = windows(video, n, rec, t)
    for w in found:
        f, first = source(video, n, rec, t, w["clip"])     # the video's frame numbers, as the clip's file numbers them
        offset = first - tl.half_up(tl.clip(t, w["clip"])["start"] * t["fps"])
        sheet(f, [x + offset for x in w["frames"]], t["fps"], bundle / w["sheet"])
    atomic_json(bundle / "windows.json", found)
    from .script import sections
    script = cut / "SCRIPT.md" if (cut / "SCRIPT.md").exists() else video / "SCRIPT.md"
    (bundle / "SCRIPT.md").write_text(sections(script.read_text()).get("Script", "") if script.exists() else "")
    prior = previous(video, current)
    if prior:
        atomic_json(bundle / "previous.json", prior)
    (bundle / "prompt.md").write_text(prompt(cfg, judged, prior))
    atomic_json(manifest, {"cut": n, "revision": judged, "round": number, "cap": cap, "tone": cfg.get("tone"),
                           "windows": "windows.json", "sheets": "sheets/", "script": "SCRIPT.md",
                           "previous": "previous.json" if prior else None, "prompt": "prompt.md"})
    if stale:
        print(f"cut {n} is older than the sources ({changed} changed since): its review will be recorded as stale")
    events = sum(w["kind"] == "event" for w in found)
    print(f"{len(found)} motion windows ({events} events, {len(found) - events} moves); round {number} of at most {cap}")
    print(f"ready for motion review: {manifest}\nMain session: give this bundle to a fresh image-capable reviewer; "
          "import the response with --result FILE. This command does not run a reviewer.")
    return 0


def imported(video, n, bundle, manifest, result, cfg, cap, stale, changed):
    """Import a response: its findings, the round it was, the receipt, and, when the stop rule ends
    the review, the known issues on the cut."""
    if not manifest.exists():
        raise SystemExit("prepare the motion review bundle before importing a result")
    m = json.loads(manifest.read_text())
    judged = m["revision"]
    text = result.read_text()
    if not any(re.sub(r"[*_`#>]", "", line).strip() == f"REVISION: {judged}" for line in text.splitlines()):
        raise SystemExit("motion review must include the exact REVISION from its manifest")
    status, line = KIND.verdict(text)
    if line is None:
        raise SystemExit("the motion review has no verdict line (MOTION: PASS or MOTION: FIX); ask the reviewer for one")
    names = [w["name"] for w in json.loads((bundle / "windows.json").read_text())]
    findings, gags = parse(text, names)
    must = [f for f in findings if f["severity"] == "must-fix"]
    left = [f for f in findings if f["severity"] != "must-fix"]
    if status == "passed" and must:
        print(f"warn: the verdict says PASS but {len(must)} finding(s) are MUST FIX; recorded as findings")
    number = next_round(video, KIND, judged)
    start_round(video, KIND, number, judged, cfg)
    status = "findings" if must or status == "findings" else "known-issues" if left else "passed"
    ended = status != "findings" or number >= cap
    (bundle / "result.md").write_text(text)
    atomic_json(bundle / "findings.json", {"cut": n, "round": number, "verdict": line, "status": status,
                                           "findings": findings, **({"gags": gags} if gags else {})})
    record(video, "motion", judged, status, str(bundle / "result.md"), cut=n, round=number, stale=stale, changed=changed,
           must_fix=len(must), left=len(left), stopped=("clean" if status != "findings" else "cap") if ended else None)
    if ended:
        write_known_issues(video, n, [{**f, "cut": n} for f in left])
    counts = f"{len(must)} must-fix, {len(left)} should-fix or nit"
    stale_note = f"; recorded as stale: {changed} changed since cut {n}" if stale else ""
    if status == "findings" and ended:
        print(f"motion: OPEN at the cap (round {number} of {cap}): {counts}{stale_note}. Report to the main session: the "
              "must-fix findings stay open; the rest are known issues on the cut. The main session decides: fix them and "
              "record the user's acceptance with studio review-status VIDEO motion waived --reason …, or, if the user "
              f"asks, raise video.json motion_rounds; {bundle / 'findings.json'}")
        return 1
    if status == "findings":
        print(f"motion: findings, round {number} of {cap}: {counts}{stale_note}. Fix the must-fix findings, make a "
              f"fresh cut and run studio review-motion again; {bundle / 'findings.json'}")
        return 1
    print(f"motion: {status}, round {number} of {cap}: {counts}{stale_note}. The review has ended by its rule"
          + (f"; {len(left)} known issue(s) recorded on cut {n} and later cuts" if left else "") + f"; {bundle / 'findings.json'}")
    return 0
