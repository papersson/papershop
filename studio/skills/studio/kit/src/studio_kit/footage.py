"""Footage: recordings the video is cut from, edited by their words.

  studio ingest FILE VIDEO [--name N]   copy the recording into assets/ (recorded as supplied), then
        footage/N.words.json   every word with its start and end (faster-whisper)
        footage/N.shots.json   scene-change times (ffmpeg's scene score)
        footage/N.paper.md     a paper edit: the transcript as numbered sentences with timestamps,
                               filler words and long pauses marked, so an edit is a list of ids
  studio edit VIDEO EDL.json            build the timeline from an edit list

An edit list is a list of segments, [{"src": "N", "in": 12.4, "out": 19.0, "gain": 0}, ...], played
back to back (a jump cut is two segments). The timeline's footage track holds the segments, its
audio track each segment's sound (with a short fade at every cut so a cut never clicks), and its
narration track the words spoken inside each segment, so captions come from the footage and the
transcript can't drift from the picture. Overlays (callouts, zooms, titles) live in scenes/s1.tsx,
over the `Footage` component.

For footage videos `studio check` adds filler (a filler word left in a segment), cuts (a cut through a word), levels (a segment
more than 3 LU from the median), sync (a recording's audio and video lengths differ) and segments
(a segment under 0.4 s, which flickers).
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

from . import assets
from . import timeline as tl

FILLERS = {"um", "uh", "erm", "er", "ah", "hmm", "like", "basically", "actually", "so", "right", "okay"}
HARD_FILLERS = {"um", "uh", "erm", "er", "hmm"}
PAUSE = 0.7                 # seconds of silence that end a sentence
MIN_SEGMENT = 0.4
LEVEL_TOLERANCE = 3.0       # LU


def folder(video):
    d = Path(video) / "footage"
    d.mkdir(exist_ok=True)
    return d


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration,width,height:format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def shots(path, threshold=0.3):
    """Scene-change times in seconds."""
    run = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-vf",
                          f"select='gt(scene,{threshold})',metadata=print:file=-", "-an", "-f", "null", "-"],
                         capture_output=True, text=True)
    return [round(float(m.group(1)), 3) for m in re.finditer(r"pts_time:([\d.]+)", run.stdout + run.stderr)]


def sentences(words):
    """Words grouped into sentences: at end punctuation, or where a pause is over PAUSE seconds."""
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        gap = words[i + 1]["start"] - w["end"] if i + 1 < len(words) else 99
        if re.search(r"[.!?]$", w["w"]) or gap > PAUSE:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def bare(word):
    return re.sub(r"[^\w']", "", word.lower())


def paper_edit(name, words):
    lines = [f"# Paper edit: {name}", "",
             "Choose sentences by id; an edit list segment is {\"src\": \"%s\", \"in\": start, \"out\": end}." % name,
             "Marks: `~` a filler word inside, `…` a pause of over 0.7 s before it.", ""]
    prev_end = 0.0
    for n, s in enumerate(sentences(words), 1):
        text = " ".join(w["w"] for w in s)
        marks = ""
        if s[0]["start"] - prev_end > PAUSE:
            marks += " …"
        if any(bare(w["w"]) in HARD_FILLERS for w in s):
            marks += " ~"
        lines.append(f"{n:>3}. [{s[0]['start']:7.2f} – {s[-1]['end']:7.2f}]{marks} {text}")
        prev_end = s[-1]["end"]
    return "\n".join(lines) + "\n"


def ingest(video, file, name=None, model="small.en"):
    from . import align
    video, file = Path(video), Path(file).expanduser()
    if not file.is_file():
        raise SystemExit(f"{file} is not a file")
    name = name or re.sub(r"\W+", "-", file.stem).strip("-").lower()
    dst = assets.dir_of(video) / f"{name}{file.suffix.lower()}"
    if not dst.exists():
        shutil.copyfile(file, dst)
    assets.record(video, dst.name, "supplied", str(file))
    info = probe(dst)
    streams = {s["codec_type"] for s in info["streams"]}
    if "video" not in streams:
        raise SystemExit(f"{file} has no video stream")
    words = align.recognise(dst, model) if "audio" in streams else []
    d = folder(video)
    (d / f"{name}.words.json").write_text(json.dumps(words, indent=1, ensure_ascii=False) + "\n")
    (d / f"{name}.shots.json").write_text(json.dumps(shots(dst)) + "\n")
    (d / f"{name}.paper.md").write_text(paper_edit(name, words), encoding="utf-8")
    return {"name": name, "file": dst.name, "duration": float(info["format"]["duration"]), "words": len(words)}


def fade_ms():
    return 0.008


def build(video, edl):
    """The timeline for an edit list; returns it (and writes it)."""
    video = Path(video)
    fps = tl.DEFAULT_LAYOUT["fps"]
    footage, audio, narration = [], [], []
    at = 0.0
    words_cache = {}
    n_sent = 0
    for i, seg in enumerate(edl, 1):
        src, a, b = seg["src"], float(seg["in"]), float(seg["out"])
        if b <= a:
            raise SystemExit(f"segment {i}: out ({b}) is not after in ({a})")
        file = next((p.name for p in assets.dir_of(video).glob(f"{src}.*") if p.suffix.lower() in (".mp4", ".mov", ".mkv", ".webm", ".m4v")), None)
        if not file:
            raise SystemExit(f"segment {i}: no ingested recording named {src!r} (run studio ingest)")
        if src not in words_cache:
            words_cache[src] = json.loads((folder(video) / f"{src}.words.json").read_text())
        dur = b - a
        footage.append({"id": f"f{i}", "file": file, "in": a, "out": b, "start": round(at, 3), "end": round(at + dur, 3)})
        entry = {"file": f"assets/{file}", "start": round(at, 3), "in": a, "out": b, "gain": seg.get("gain", 0), "fade": fade_ms()}
        audio.append(entry)
        inside = [w for w in words_cache[src] if w["start"] >= a - 0.01 and w["end"] <= b + 0.01]
        for s in sentences(inside):
            n_sent += 1
            words = [{"w": w["w"], "start": round(at + w["start"] - a, 3), "end": round(at + w["end"] - a, 3)} for w in s]
            text = " ".join(w["w"] for w in s)
            narration.append({"id": f"s1_{n_sent:02d}", "clip": "s1", "text": text, "caption": text, "paragraph": i - 1,
                              "start": words[0]["start"], "end": words[-1]["end"], "words": words})
        at += dur
    t = {"version": 1, "fps": fps, "duration": round(at, 3), "cues": {},
         "tracks": {"scene": [{"id": "s1", "engine": "remotion", "title": "Edit", "start": 0.0, "end": round(at, 3)}],
                    "footage": footage, "narration": narration, "captions": tl.chunk_captions(narration, fps), "audio": audio}}
    tl.save(video, t)
    if not (video / "layout.json").exists():
        (video / "layout.json").write_text(json.dumps(tl.DEFAULT_LAYOUT, indent=1) + "\n")
    return t


# --- checks -----------------------------------------------------------------------------------------

def _loudness(path, a, b):
    from . import audio
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a), "-t", str(b - a), "-i", str(path), "-vn", "-ac", "1", f.name],
                       check=True)
        return audio.measure(f.name)[0]


def checks(video):
    video = Path(video)
    t = tl.load(video)
    rows = []
    for f in t["tracks"].get("footage", []):
        d = f["out"] - f["in"]
        rows.append({"check": "segments", "clip": f["id"], "ok": d >= MIN_SEGMENT, "detail": f"{d:.2f} s"})
    fillers, cuts = [], []
    for f in t["tracks"].get("footage", []):
        wf = folder(video) / f"{f['file'].rsplit('.', 1)[0]}.words.json"
        words = json.loads(wf.read_text()) if wf.exists() else []
        for w in words:
            overlap = min(w["end"], f["out"]) - max(w["start"], f["in"])
            if overlap <= 0.05:
                continue
            whole = w["start"] >= f["in"] - 0.01 and w["end"] <= f["out"] + 0.01
            if bare(w["w"]) in HARD_FILLERS:
                fillers.append(f"{f['id']}: {w['w']!r} at {w['start']:.2f} s")
            if not whole:
                cuts.append(f"{f['id']}: cuts through {w['w']!r} ({w['start']:.2f}-{w['end']:.2f} s)")
    rows.append({"check": "filler", "clip": "all", "ok": not fillers,
                 "detail": "; ".join(fillers) if fillers else "no um/uh/er in the segments"})
    rows.append({"check": "cuts", "clip": "all", "ok": not cuts,
                 "detail": "; ".join(cuts) if cuts else "every cut falls between words"})
    levels = []
    for f in t["tracks"].get("footage", []):
        if f["out"] - f["in"] >= 1.0:
            try:
                base = _loudness(video / "assets" / f["file"], f["in"], f["out"])
            except (subprocess.CalledProcessError, RuntimeError):
                rows.append({"check": "levels", "clip": f["id"], "ok": False, "detail": "cannot measure this segment's audio"})
                continue
            gain = next((e.get("gain", 0) for e in t["tracks"]["audio"] if e.get("start") == f["start"]), 0)
            levels.append((f["id"], base + gain))
    if levels:
        med = sorted(v for _, v in levels)[len(levels) // 2]
        for fid, v in levels:
            rows.append({"check": "levels", "clip": fid, "ok": abs(v - med) <= LEVEL_TOLERANCE,
                         "detail": f"{v:.1f} LUFS, {v - med:+.1f} LU from the median" +
                                   ("" if abs(v - med) <= LEVEL_TOLERANCE else f"; add gain {med - v:+.1f} dB")})
    for name in sorted({f["file"] for f in t["tracks"].get("footage", [])}):
        try:
            info = probe(video / "assets" / name)
        except subprocess.CalledProcessError:
            rows.append({"check": "sync", "clip": name, "ok": False, "detail": "ffprobe cannot read the file"})
            continue
        by = {s["codec_type"]: float(s["duration"]) for s in info["streams"] if s.get("duration")}
        if len(by) == 2:
            rows.append({"check": "sync", "clip": name, "ok": abs(by["video"] - by["audio"]) < 0.04,
                         "detail": f"video {by['video']:.2f} s, audio {by['audio']:.2f} s"})
    return rows


def main_ingest(args):
    r = ingest(args.video, args.file, args.name, args.model)
    print(f"{r['name']}: {r['duration']:.1f} s, {r['words']} words → footage/{r['name']}.paper.md")
    return 0


def main_edit(args):
    t = build(args.video, json.loads(Path(args.edl).read_text()))
    print(f"{len(t['tracks']['footage'])} segments, {t['duration']:.1f} s, {len(t['tracks']['narration'])} sentences, "
          f"{len(t['tracks']['captions'])} caption chunks")
    return 0
