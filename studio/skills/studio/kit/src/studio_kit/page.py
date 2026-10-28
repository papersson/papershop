"""Standalone film review desk. Notes are immediate, durable and scoped; build marks come
from recorded facts. Historical round records remain readable but no new round is created."""
import hashlib
import json
import mimetypes
import re
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import proc, settings
from . import cuts, events
from .workspace import locked
from . import timeline as tl

_lock = threading.Lock()


def notes_file(video):
    return Path(video) / "review" / "notes.jsonl"


def append(video, entry):
    f = notes_file(video)
    f.parent.mkdir(parents=True, exist_ok=True)
    entry = {**entry, "created": time.strftime("%Y-%m-%d %H:%M:%S")}
    with _lock, locked(video, 'notes'), f.open("a", encoding="utf-8") as out:
        out.write(json.dumps(entry, ensure_ascii=False) + "\n")
    notes = fold(read_log(video))[0]
    note = next((n for n in notes if n['id'] == entry.get('id')), {})
    events.emit(video, 'note.' + entry['type'], entry.get('reply') or entry.get('note') or entry['type'],
                lane=note.get('lane') or note.get('clip'), t=note.get('t'), note=entry.get('id'), source='review/notes.jsonl')
    return entry


def read_log(video):
    f = notes_file(video)
    if not f.exists():
        return []
    rows = []
    for line in f.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def fold(log, cut=None, since=None):
    """(notes, rounds): the current notes, in the order written, after edits, deletes, starts and
    resolves; each note has a `status` (queued, working, done) and its `reply`, if any. With `cut`,
    the notes on that cut plus earlier ones still open or resolved at or after `since` (when the
    previous cut was made), so a reply shows on the cut that answers it."""
    notes, rounds = {}, []
    for e in log:
        if e["type"] == "note":
            notes[e["id"]] = {**e, "status": e.get("status", "queued"), "reply": None}
        elif e["type"] in ("accept", "dismiss") and e["id"] in notes:
            if notes[e["id"]]["status"] == "suggested":
                notes[e["id"]]["status"] = "queued" if e["type"] == "accept" else "dismissed"
        elif e["type"] == "start" and e["id"] in notes:
            notes[e["id"]]["status"] = "working"
        elif e["type"] == "resolve" and e["id"] in notes:
            notes[e["id"]].update(status="done", reply=e.get("reply"), resolved=e.get("created", ""))
        elif e["type"] == "edit" and e["id"] in notes:
            note = notes[e['id']]
            changes = {k: e[k] for k in ("note", "kind", 't', 'end', 'scope', 'beat', 'lane', 'clip', 'sentence_id', 'sentence') if k in e}
            changed = any(note.get(k) != v for k, v in changes.items())
            note.update(changes)
            if changed and note['status'] in ('working', 'done'):
                note.update(status='queued', reply=None)
        elif e["type"] == "delete":
            notes.pop(e["id"], None)
        elif e["type"] == "round":
            rounds.append(dict(e))
        elif e["type"] == "received":
            sent = [r for r in rounds if r["cut"] == e["cut"] and "received" not in r]
            if sent:
                sent[-1]["received"] = e["created"]
    kept = [n for n in notes.values() if cut is None or n["cut"] == cut
            or ((n["cut"] or 0) < cut and (n["status"] not in ("done", "dismissed") or (since and n.get("resolved", "") >= since)))]
    return kept, [r for r in rounds if cut is None or r["cut"] == cut]


def live_view(video, cut, latest):
    """Keep a selected version stable while the default view follows saved live scenes."""
    cfg = settings.load(video)
    if cfg["engine"] != "live" or cut is not None:
        return False
    record = cuts.read(video, latest) if latest else None
    return not record or cuts.kind(record) != "animatic" or any(
        (Path(video) / 'scenes' / f'{c["id"]}.js').exists() for c in tl.load(video)['tracks']['scene'])


def live_audio(video, t):
    """What the live desk plays under the scenes: the whole mix, cached as a cut's is, else the
    narration alone when the mix can't be made (an effect's cue gone, the sound tools missing, a mix
    that comes out the wrong length while the timeline is mid-edit). An
    estimate has no narration to clock the scenes by, and its effects are not placed yet: silence."""
    import contextlib
    import io
    from . import audio
    if t.get("timing") == "estimate":
        return None
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return str(audio.soundtrack(video, t).relative_to(video))
    except (SystemExit, ImportError, OSError, ValueError, RuntimeError, proc.SubprocessError):
        return (tl.narration_audio(t) or {}).get("file")


def live_timeline(video):
    """Read chapter-owned cues without rewriting the shared timeline during a shoot."""
    t = tl.load(video)
    cues, _ = tl.cue_sources(video, t)
    t['cues'] = {**t.get('cues', {}), **tl._resolve_cues(cues, t)}
    return t


def state(video, cut=None):
    video = Path(video)
    latest = cuts.last(video)
    n = cut or latest
    record = cuts.read(video, n) if n else None
    # The live view follows the current timeline; an older cut shows the cut as it was.
    live = live_view(video, cut, latest)
    snapshot = cuts.cut_dir(video, n) / "timeline.json"
    t = live_timeline(video) if live or not snapshot.exists() else json.loads(snapshot.read_text())
    if live and not record:
        record = {"cut": 0, "kind": "live", "created": "", "quality": "live", "stills": [], "changelog": [],
                  "video": None, "duration": t.get("duration", 0)}
    if record and record.get("video") and not cuts.playable(video, n):
        record = {**record, "video": None}
    if record:
        record = {**record, "kind": cuts.kind(record), "stills": [s for s in record.get("stills", [])
                                      if (cuts.cut_dir(video, n) / s["file"]).exists()]}
    # Replies made since the previous cut show here, whether the builder resolved before or after cutting.
    prev = cuts.read(video, n - 1) if n and n > 1 else None
    notes, rounds = fold(read_log(video), n, (prev or {}).get("created") or (record or {}).get("created"))
    title = t.get("title") or video.name
    title = settings.raw(video).get("title", title)
    return {
        "title": title, "latest": latest, "cut": record,
        "cuts": sorted(cuts.records(video)),
        "narration": [{k: s[k] for k in ("id", "clip", "start", "end", "caption")} for s in t["tracks"]["narration"]],
        "chapters": [{k: c[k] for k in ('id', 'title', 'start', 'end')} for c in t["tracks"]["scene"]],
        "notes": notes, "rounds": rounds, "status": read_status(video),
        # The desk's clock: the mix (or the narration), else a silent clock.
        "live": {"audio": live_audio(video, t), "duration": t.get("duration", 0)} if live else None,
        "duration": t.get('duration', 0), "fps": t.get('fps', 30), "captions": t['tracks'].get('captions', []),
        "beats": story_beats(video, t), "sound": sound_marks(video, t),
        "waveform": waveform(video, t), "build": events.view(video, t['tracks']['scene']),
    }


def story_beats(video, t):
    f = Path(video) / 'data' / 'story-beats.json'
    # Explicit anchors only; chapter starts are the honest fallback, never equally spaced guesses.
    rows = json.loads(f.read_text()) if f.exists() else [
        {'id': c['id'], 'title': c['title'], 'clip': c['id'], 't': c['start']} for c in t['tracks']['scene']]
    return [{**e, 't': tl.event_time(t, e['t'])} for e in rows]


def sound_marks(video, t):
    f = Path(video) / 'audio' / 'sfx.json'
    rows = json.loads(f.read_text()) if f.exists() else []
    result = []
    for i, e in enumerate(rows):
        try:
            at = t.get('cues', {}).get(e['t']) if isinstance(e['t'], str) else tl.event_time(t, e['t'])
            if at is not None:
                result.append({'id': f'fx{i+1}', 't': at, 'title': e.get('type', 'sound')})
                for j, key in enumerate(e.get('events', [])):
                    result.append({'id': f'fx{i+1}-key{j}', 't': at + key[0], 'title': key[1] + ' key'})
        except (ValueError, KeyError, SystemExit):
            pass
    return result


def waveform(video, t):
    from array import array
    from .workspace import atomic_json
    src = (tl.narration_audio(t) or {}).get('file')
    if not src or not (Path(video) / src).exists():
        return []
    f = Path(video) / src
    cache = Path(video) / '.cache' / 'desk-waveform.json'
    stamp = [f.stat().st_mtime_ns, f.stat().st_size]
    with locked(video, 'waveform'):
        old = json.loads(cache.read_text()) if cache.exists() else {}
        if old.get('stamp') == stamp:
            return old['peaks']
        try:
            data = array('f', proc.ffmpeg('-i', f, '-ac', 1, '-ar', 8000, '-f', 'f32le', '-', capture_output=True).stdout)
            hop = max(1, len(data) // 1400)
            peaks = [round(max(map(abs, data[i:i+hop]), default=0), 4) for i in range(0, len(data), hop)]
            atomic_json(cache, {'stamp': stamp, 'peaks': peaks})
            return peaks
        except (SystemExit, OSError, proc.SubprocessError):
            return []


def status_file(video):
    return Path(video) / "review" / "status.json"


def read_status(video):
    f = status_file(video)
    try:
        return json.loads(f.read_text()) if f.exists() else None
    except ValueError:
        return None


def write_status(video, text=None, busy=False):
    f = status_file(video)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"text": text, "busy": bool(busy and text), "at": time.strftime("%H:%M:%S")}))


def mark(video, note_id, how, reply=None):
    """Mark a note as being worked on ("start") or done ("resolve", with a one-line reply)."""
    notes, _ = fold(read_log(video))
    if note_id not in {n["id"] for n in notes}:
        raise SystemExit(f"no open note {note_id} (studio notes VIDEO lists them)")
    note = next(n for n in notes if n["id"] == note_id)
    if how in ("start", "resolve") and note["status"] in ("suggested", "dismissed"):
        raise SystemExit("The user must accept a suggested note before work starts.")
    return append(video, {"type": how, "id": note_id, **({"reply": reply} if how == "resolve" else {})})


def wait(video, timeout=None, poll=0.25, settle=0, chapter=None):
    """At-least-once inbox. A reader cannot silently consume a note; notes --start ID acknowledges it.
    Notes queued while the watcher was absent are returned on its next start."""
    end = time.time() + timeout if timeout else None
    while end is None or time.time() < end:
        pending = [n for n in fold(read_log(video))[0] if n['status'] == 'queued'
                   and (not chapter or (n.get('lane') or n.get('clip')) in (None, chapter))]
        if pending:
            time.sleep(settle)
            return pending
        time.sleep(poll)
    return None


def notes_text(video, cut=None):
    """Reading is not acknowledgement: the builder starts each note explicitly."""
    n = cut or cuts.last(video)
    notes, rounds = fold(read_log(video), n)
    count = f"{len(notes)} note" + ("" if len(notes) == 1 else "s")
    lines = [f"cut {n}: {count}; notes arrive immediately"]
    lines += describe(notes)
    return "\n".join(lines)


def describe(notes):
    """Notes as numbered lines the builder works from: time, sentence, kind, id, status, text."""
    lines = []
    for i, x in enumerate(notes, 1):
        m, s = divmod(x["t"] or 0, 60)
        state = "" if x.get("status", "queued") == "queued" else f" {x['status']}"
        lines.append(f"{i}. [{int(m)}:{s:04.1f} {x['sentence_id'] or x['clip']} {x['kind']}] {x['note'] or '(here)'}"
                     f"  (id {x['id']}{state}, cut {x['cut']})")
        lines.append(f"   on screen: {x['sentence']}")
        from . import glossary
        named = [g["term"] for g in glossary.find(x["note"] or "")]
        if named:
            lines.append(f"   glossary: {', '.join(named)} (studio glossary --term TERM)")
        if x.get("reply"):
            lines.append(f"   reply: {x['reply']}")
    return lines


class Handler(BaseHTTPRequestHandler):
    video: Path

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False))

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            return self._send(200, (Path(__file__).parent / 'page.html').read_text(), "text/html; charset=utf-8")
        if path == "/api/events":
            return self._events()
        if path == "/api/state":
            q = re.search(r"cut=(\d+)", self.path)
            return self._json(state(self.video, int(q.group(1)) if q else None))
        if path == '/api/build':
            q = re.search(r'at=([\d.]+)', self.path)
            return self._json(events.view(self.video, tl.load(self.video)['tracks']['scene'], float(q.group(1)) if q else None))
        if path == '/api/health':
            return self._json({'video': str(self.video), 'ok': True})
        if path.startswith('/evidence/') and '..' not in path.split('/'):
            f = self.video / path[len('/evidence/'):]
            if f.is_file() and f.suffix in ('.png', '.jpg', '.json', '.jsonl'):
                return self._file(f)
        if path.startswith("/live/"):
            return self._live(path[len("/live/"):])
        m = re.fullmatch(r"/cut(\d+)/([\w./-]+)", path)
        if m and ".." not in m.group(2):
            f = cuts.cut_dir(self.video, m.group(1)) / m.group(2)
            if f.is_file():
                if f.name == "video.mp4":
                    cuts.mark_watched(self.video, int(m.group(1)))
                return self._file(f)
        self._send(404, b"not found", "text/plain")

    LIVE_DIRS = ("scenes", "boards", "assets", "data", "audio")

    def _live(self, rel):
        """The live engine, the engines' shared modules (its kit imports ../../shared/) and the
        video's live inputs, for drawing scenes in the page."""
        from .env import engine_dir
        if ".." in rel.split("/"):
            return self._send(404, b"not found", "text/plain")
        if rel.startswith("engine/"):
            f = engine_dir("live") / rel[len("engine/"):]
        elif rel.startswith("shared/"):
            f = engine_dir("shared") / rel[len("shared/"):]
        elif rel == "layout.json":
            f = self.video / "layout.json"
        elif rel.startswith("video/"):
            sub = rel[len("video/"):]
            if sub == 'timeline.json' and self.command != 'HEAD':
                return self._json(live_timeline(self.video))
            ok = (sub in ("timeline.json", "layout.json", "video.json") or sub.split("/", 1)[0] in self.LIVE_DIRS
                  or sub.startswith((".cache/sound/", ".cache/plates/")))
            f = self.video / sub if ok else None
        else:
            f = None
        if not f or not f.is_file():
            return self._send(404, b"not found", "text/plain")
        if self.command == "HEAD":
            self.send_response(200)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return
        return self._file(f)

    def do_HEAD(self):
        path = self.path.split("?")[0]
        if path.startswith("/live/"):
            return self._live(path[len("/live/"):])
        self._send(404, b"", "text/plain")

    def _file(self, f):
        """Serve a file with byte ranges, which a video element needs to seek."""
        size = f.stat().st_size
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        rng = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        with f.open("rb") as fh:
            if not rng:
                return self._send(200, fh.read(), ctype, {"Accept-Ranges": "bytes"})
            a = int(rng.group(1)) if rng.group(1) else max(0, size - int(rng.group(2)))
            b = int(rng.group(2)) if rng.group(1) and rng.group(2) else size - 1
            b = min(b, size - 1)
            fh.seek(a)
            return self._send(206, fh.read(b - a + 1), ctype,
                              {"Accept-Ranges": "bytes", "Content-Range": f"bytes {a}-{b}/{size}"})

    def _events(self):
        """Server-sent events: `notes` when the log changes, `status` when the builder's status line
        does, `cut` when a newer cut lands, `scenes` when what the live page reloads in place changes
        (live_inputs), and `page` when anything else it imports does, which reloads the page at the
        same moment. Polled twice a second; a comment line keeps it open."""
        def stamp(f):
            return f.stat().st_mtime_ns if f.exists() else 0

        def now_state():
            in_place, page = live_inputs(self.video)
            return {"notes": stamp(notes_file(self.video)), "status": stamp(status_file(self.video)),
                    "cut": cuts.last(self.video), "scenes": inventory(in_place), "page": inventory(page),
                    "build": stamp(events.path(self.video))}
        # The state is taken before the client hears it is subscribed: a note it adds the moment the
        # headers arrive must count as new.
        seen = now_state()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            while True:
                time.sleep(0.5)
                now = now_state()
                for k in now:
                    if now[k] != seen[k]:
                        self.wfile.write(f"event: {k}\ndata: {json.dumps(now[k])}\n\n".encode())
                seen = now
                self.wfile.write(b": ping\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        if self.path == "/api/notes":
            fields = ("cut", "t", "end", "scope", "beat", "lane", "clip", "sentence_id", "sentence", "previous_id", "previous", "kind", "note")
            entry = append(self.video, {"type": "note", "id": uuid.uuid4().hex[:8], **{k: body.get(k) for k in fields}})
            return self._json(entry)
        if self.path == '/api/stop':
            lane = body.get('lane')
            lanes = [lane] if lane else [c['id'] for c in tl.load(self.video)['tracks']['scene']]
            entries = []
            for target in lanes:
                entry = append(self.video, {'type': 'note', 'id': uuid.uuid4().hex[:8], 'cut': cuts.last(self.video),
                               'scope': 'lane', 'lane': target, 'clip': target, 't': None,
                               'sentence_id': None, 'sentence': '', 'kind': 'control', 'note': 'Stop this lane' if lane else 'Stop the build'})
                events.emit(self.video, 'stop.requested', entry['note'], lane=target, note=entry['id'])
                entries.append(entry)
            return self._json(entries)
        m = re.fullmatch(r"/api/notes/(\w+)/(edit|delete|accept|dismiss)", self.path)
        if m:
            extra = {k: body[k] for k in ("note", "kind", 't', 'end', 'scope', 'beat', 'lane', 'clip', 'sentence_id', 'sentence') if k in body} if m.group(2) == "edit" else {}
            return self._json(append(self.video, {"type": m.group(2), "id": m.group(1), **extra}))
        self._send(404, b"not found", "text/plain")


def live_inputs(video):
    """The files the desk's live page reads, in two groups: what it reloads in place (each chapter's
    and the overlay's scene file, which it imports afresh, and the JSON it fetches: timeline, boards,
    layout, video.json), and what only a fresh page picks up (the modules those scenes import, which a
    browser keeps by URL, anything else under scenes/, and the engine's own files)."""
    from .env import engine_dir
    video = Path(video)
    scenes = video / "scenes"
    try:
        clips = {c["id"] for c in json.loads((video / "timeline.json").read_text())["tracks"]["scene"]}
    except (OSError, ValueError, KeyError):
        clips = set()
    owned = {scenes / f"{c}.js" for c in clips} | {scenes / "overlay.js"}
    in_place = [video / "timeline.json", video / "layout.json", video / "video.json", *(video / "boards").glob("*.json"),
                *(f for f in owned if f.is_file())]
    page = [f for f in sorted(scenes.rglob("*")) if f.is_file() and f not in owned] if scenes.is_dir() else []
    page += [f for f in (video / 'data').rglob('*') if f.is_file() and f.suffix in ('.js', '.json')]
    in_place += list((video / 'cues').glob('*.json'))
    live = engine_dir("live")
    page += [live / "render.html", *sorted((live / "src").rglob("*")), *sorted(engine_dir("shared").rglob("*"))]
    return in_place, page


def inventory(files):
    """A stamp for a set of files that changes when one is edited, added or removed (a newest
    modification time alone misses a deletion, or a file restored with an older time)."""
    def entry(f):
        try:
            st = f.stat()
        except OSError:            # removed since it was listed
            return f"{f}:gone"
        return f"{f}:{st.st_mtime_ns}:{st.st_size}"
    return hashlib.sha1("\n".join(entry(f) for f in files).encode()).hexdigest()


PORT = 8765
PORT_TRIES = 20


def bind(video, port=None, host="127.0.0.1"):
    """The desk's server: on `port` when one is given (a busy one stops, with what to do), else on
    the first free port from PORT, else any free port, so a second desk or another program on 8765
    doesn't stop the user from opening this one."""
    handler = type("VideoHandler", (Handler,), {"video": Path(video).resolve()})
    for p in [port] if port else [*range(PORT, PORT + PORT_TRIES), 0]:
        try:
            return ThreadingHTTPServer((host, p), handler)
        except OSError as e:
            if port:
                raise SystemExit(f"desk: port {port} on {host} is not available ({e.strerror}); "
                                 "pass another --port, or none to take a free one")
    raise SystemExit(f"desk: no free port on {host}")


def serve(video, port=None, host="127.0.0.1"):
    server = bind(video, port, host)
    from .workspace import atomic_json
    import os
    atomic_json(Path(video) / 'review' / 'desk.json', {'pid': os.getpid(), 'port': server.server_port, 'video': str(Path(video).resolve())})
    observer = events.Observer(video)
    def watch():
        while True:
            observer.poll()
            time.sleep(0.5)
    threading.Thread(target=watch, daemon=True).start()
    print(f"desk: http://{host}:{server.server_port}/  (notes → {notes_file(video)}; "
          f"studio wait {video} wakes on each)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


PAGE = (Path(__file__).parent / "page.html").read_text(encoding="utf-8")


def main_serve(args):
    if getattr(args, 'foreground', False):
        serve(args.video, args.port)
        return 0
    import sys
    import urllib.request
    f = Path(args.video) / 'review' / 'desk.json'
    def running():
        try:
            record = json.loads(f.read_text())
            url = f'http://127.0.0.1:{record["port"]}/'
            health = json.loads(urllib.request.urlopen(url + 'api/health', timeout=0.5).read())
            return url if health['video'] == str(Path(args.video).resolve()) else None
        except (OSError, ValueError, KeyError):
            return None
    url = running()
    if not url:
        f.parent.mkdir(parents=True, exist_ok=True)
        with (f.parent / 'desk.log').open('a') as log:
            process = proc.popen([sys.executable, '-m', 'studio_kit.cli', 'desk', str(args.video), '--foreground',
                                  *(['--port', str(args.port)] if args.port else [])],
                                 stdout=log, stderr=log, start_new_session=True)
        for _ in range(100):
            url = running()
            if url or process.poll() is not None:
                break
            time.sleep(0.1)
    if not url:
        raise SystemExit(f'desk did not start; see {f.parent / "desk.log"}')
    print(f'desk: {url} (standalone; stays open when the agent exits)')
    return 0


def main_notes(args):
    for action in ("accept", "dismiss"):
        if getattr(args, action, None):
            mark(args.video, getattr(args, action), action)
    if args.start:
        mark(args.video, args.start, "start")
    if args.resolve:
        mark(args.video, args.resolve, "resolve", args.reply)
    if not (args.start or args.resolve or getattr(args, "accept", None) or getattr(args, "dismiss", None)):
        print(notes_text(args.video, args.cut))
    return 0


def main_wait(args):
    new = wait(args.video, args.timeout, chapter=getattr(args, 'chapter', None))
    if new is None:
        print(f"no new note in {args.timeout:g} s")
        return 2
    print(f"{len(new)} new note" + ("" if len(new) == 1 else "s") + ":")
    print("\n".join(describe(new)))
    return 0


def main_status(args):
    write_status(args.video, " ".join(args.text) or None, args.busy)
    return 0
