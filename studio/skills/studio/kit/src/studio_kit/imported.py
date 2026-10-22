"""Cuts made elsewhere, reviewed here: `studio import-cut`, and a review that needs no listener.

A renderer outside the kit (another machine, another tool) can hand over an MP4, the timeline it was
made to and, optionally, a provenance file. `import-cut` checks the pieces agree and records the cut
like any other, with an identity that cannot change: the media's hash and the timeline's. Notes belong
to that identity, so a replaced video never inherits them, and approvals and listenings bind to it.

  studio import-cut VIDEO MP4 --timeline FILE [--provenance FILE] [--producer NAME]
  studio review-export VIDEO [--cut N] [--out DIR]      a static page (no server) to watch the cut and write notes
  studio notes-export VIDEO [--cut N] [--out FILE]      the cut's notes with its identity
  studio notes-import VIDEO FILE                        notes from an export, only onto a cut of the same identity

Checks on import: the movie's length and frame rate against the timeline's; chapters inside the
duration; files the provenance lists exist beside it. A mismatch stops the import and names it.
"""
import hashlib
import html
import json
import shutil
import time
import uuid
from pathlib import Path

from . import cuts, proc
from . import timeline as tl
from .workspace import atomic_json, locked

DURATION_SLACK = 0.5      # seconds the movie may differ from the timeline's duration
FPS_SLACK = 0.01


def sha(path, n=16):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:n]


def identity(media, timeline_bytes):
    """A cut's identity: its media and its timeline, each hashed."""
    return {"media": sha(media), "timeline": hashlib.sha256(timeline_bytes).hexdigest()[:16]}


def problems(movie, timeline, provenance=None, base=None):
    """What stops a movie and a timeline from being one cut: [str]."""
    out = []
    info = proc.ffprobe(movie, "-show_entries", "stream=codec_type,r_frame_rate,width,height:format=duration")
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    if video is None:
        return [f"{movie} has no video stream"]
    a, b = video["r_frame_rate"].split("/")
    fps = float(a) / float(b or 1)
    seconds = float(info["format"]["duration"])
    if abs(fps - timeline["fps"]) > FPS_SLACK:
        out.append(f"the movie runs at {fps:g} fps, the timeline at {timeline['fps']:g}")
    if abs(seconds - timeline["duration"]) > DURATION_SLACK:
        out.append(f"the movie is {seconds:.2f} s long, the timeline {timeline['duration']:.2f} s")
    for c in timeline["tracks"]["scene"]:
        if not 0 <= c["start"] < c["end"] <= timeline["duration"] + DURATION_SLACK:
            out.append(f"chapter {c['id']} ({c['start']}-{c['end']} s) is outside the {timeline['duration']:.2f} s duration")
    for f in (provenance or {}).get("files", []):
        if not (Path(base) / f).exists():
            out.append(f"the provenance lists {f}, which is not beside it")
    return out


def import_cut(video, movie, timeline_file, provenance_file=None, producer=None):
    video, movie = Path(video).resolve(), Path(movie)
    raw = Path(timeline_file).read_bytes()
    timeline = json.loads(raw)
    provenance = json.loads(Path(provenance_file).read_text()) if provenance_file else None
    found = problems(movie, timeline, provenance, Path(provenance_file).parent if provenance_file else None)
    if found:
        raise SystemExit("cannot import this cut:\n- " + "\n- ".join(found))
    with locked(video):
        n, d = cuts.allocate(video)
        shutil.copyfile(movie, d / "video.mp4")
        (d / "timeline.json").write_bytes(raw)
        who = identity(d / "video.mp4", raw)
        info = cuts.media_info(d / "video.mp4")
        cuts.write(video, n, {
            "cut": n, "kind": "cut", "imported": True, "producer": producer or (provenance or {}).get("producer"),
            "identity": who, "source_revision": who["media"] + who["timeline"], "provenance": provenance,
            "created": time.strftime("%Y-%m-%d %H:%M:%S"), "t": round(time.time(), 3), "quality": "imported",
            "video": "video.mp4", "duration": timeline["duration"], **info,
            "chapters": [{"id": c["id"], "title": c.get("title", c["id"]), "start": c["start"]} for c in timeline["tracks"]["scene"]],
            "stills": [], "changelog": [f"imported from {movie.name}"], "final": False})
    print(f"imported as cut {n}: media {who['media']}, timeline {who['timeline']}; the desk plays it, and notes belong to this identity")
    return n


def _resolve(video, cut):
    n, rec = cuts.resolve(video, cut)
    if not rec:
        raise SystemExit("no rendered or imported cut to use")
    return n, rec


def export_notes(video, cut=None, out=None):
    from . import page
    n, rec = _resolve(video, cut)
    notes, _ = page.fold(page.read_log(video), n)
    body = {"identity": rec.get("identity") or {"media": sha(cuts.cut_dir(video, n) / "video.mp4")},
            "cut": n, "notes": [{k: v for k, v in x.items() if k not in ("status", "reply", "resolved")} for x in notes]}
    text = json.dumps(body, indent=1, ensure_ascii=False) + "\n"
    if out:
        Path(out).write_text(text)
    else:
        print(text, end="")
    return body


def import_notes(video, file):
    """Append an export's notes to the cut of this video that has the same media; stop when none has."""
    from . import page
    data = json.loads(Path(file).read_text())
    media = data["identity"]["media"]
    target = next((n for n, r in sorted(cuts.records(video).items())
                   if (r.get("identity") or {}).get("media") == media
                   or (cuts.playable(video, n) and sha(cuts.cut_dir(video, n) / "video.mp4") == media)), None)
    if target is None:
        raise SystemExit(f"no cut here has the media {media}: the notes were written on a different video, and notes "
                         "do not move to another timing. Import that cut (studio import-cut) first")
    known = {x["id"] for x in page.read_log(video) if x.get("type") == "note"}
    added = 0
    for x in data["notes"]:
        if x["id"] in known:
            continue
        page.append(video, {**{k: v for k, v in x.items() if k not in ("created", "status")}, "type": "note", "cut": target})
        added += 1
    print(f"{added} note(s) added to cut {target} ({len(data['notes']) - added} already there)")
    return added


PAGE = """<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>body{{font:16px system-ui;margin:0 auto;max-width:960px;padding:16px;background:#0f1318;color:#e6ebf0}}
video{{width:100%;background:#000}}li{{margin:.3em 0;cursor:pointer}}li:hover{{color:#8fd3ff}}textarea{{width:100%;height:4em}}
button{{font:inherit;padding:.4em .8em}}small{{color:#8a96a3}}</style>
<h1>{title}</h1><p><small>Cut {n}, media {media}. A static review page: no server runs. Notes stay in this browser until you
download them, then <code>studio notes-import</code> brings them back.</small></p>
<video id="v" controls src="video.mp4"></video>
<h2>Add a note at <span id="at">0.0</span> s</h2><textarea id="note"></textarea>
<p><button id="add">Add note</button> <button id="dl">Download notes.json</button></p><ol id="notes"></ol>
<h2>Narration</h2><ul id="lines"></ul>
<script>
const DATA = {data};
const v = document.getElementById('v'), notes = [];
const sentence = t => DATA.narration.filter(s => s.start <= t + 1e-6).pop() || DATA.narration[0];
v.ontimeupdate = () => document.getElementById('at').textContent = v.currentTime.toFixed(1);
for (const s of DATA.narration) {{
  const li = document.createElement('li'); li.textContent = s.start.toFixed(1) + ' s  ' + s.caption;
  li.onclick = () => {{ v.currentTime = s.start; v.play(); }}; document.getElementById('lines').append(li);
}}
function draw() {{ document.getElementById('notes').innerHTML = ''; for (const n of notes) {{
  const li = document.createElement('li'); li.textContent = n.t.toFixed(1) + ' s (' + n.sentence_id + '): ' + n.note;
  document.getElementById('notes').append(li); }} }}
document.getElementById('add').onclick = () => {{
  const text = document.getElementById('note').value.trim(); if (!text) return;
  const s = sentence(v.currentTime);
  notes.push({{type: 'note', id: Math.random().toString(16).slice(2, 10), cut: DATA.cut, t: +v.currentTime.toFixed(2), clip: s.clip,
    sentence_id: s.id, sentence: s.caption, kind: 'both', note: text}});
  document.getElementById('note').value = ''; draw(); }};
document.getElementById('dl').onclick = () => {{
  const a = document.createElement('a'); a.download = 'notes.json';
  a.href = URL.createObjectURL(new Blob([JSON.stringify({{identity: DATA.identity, cut: DATA.cut, notes}}, null, 1)])); a.click(); }};
</script>
"""


def review_export(video, cut=None, out=None):
    """A folder with the cut's movie and a static page to watch it and write notes, with no server."""
    n, rec = _resolve(video, cut)
    t = json.loads((cuts.cut_dir(video, n) / "timeline.json").read_text()) if (cuts.cut_dir(video, n) / "timeline.json").exists() else tl.load(video)
    out = Path(out or Path(video) / "out" / f"review-cut{n}")
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cuts.cut_dir(video, n) / "video.mp4", out / "video.mp4")
    who = rec.get("identity") or {"media": sha(out / "video.mp4")}
    data = {"cut": n, "identity": who, "narration": [{k: s[k] for k in ("id", "clip", "start", "end", "caption")} for s in t["tracks"]["narration"]]}
    title = html.escape(rec.get("title") or Path(video).name)
    (out / "index.html").write_text(PAGE.format(title=title, n=n, media=who["media"], data=json.dumps(data).replace("</", "<\\/")))
    print(f"review page for cut {n}: {out / 'index.html'} (open the file; no server needed)")
    return out


def main_import(args):
    import_cut(args.video, args.movie, args.timeline, args.provenance, args.producer)
    return 0


def main_review_export(args):
    review_export(args.video, args.cut, args.out)
    return 0


def main_notes_export(args):
    export_notes(args.video, args.cut, args.out)
    return 0


def main_notes_import(args):
    import_notes(args.video, args.file)
    return 0
