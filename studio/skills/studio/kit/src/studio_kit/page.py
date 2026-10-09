"""The desk: `studio desk VIDEO` (alias `serve`) plays the latest cut, collects notes on sentences,
and shows the builder's progress and replies as they happen.

Notes go straight to the project, with no copy and paste: every change is one line appended to
review/notes.jsonl, so the file is a log the agent can watch. `studio wait VIDEO` blocks until a new
note arrives, so a builder running it in the background is woken by each note.

  {"type": "note", "id", "cut", "t", "clip", "sentence_id", "sentence", "previous_id", "previous",
   "kind": "narration" | "picture" | "both", "note", "created"}
  {"type": "edit", "id", "note", "kind", "created"}
  {"type": "delete", "id", "created"}
  {"type": "round", "cut", "notes": [ids], "created"}     "Send round": the batch is ready
  {"type": "start", "id", "created"}                      the builder is working on a note
  {"type": "resolve", "id", "reply", "created"}           done, with a one-line reply shown under it

`studio notes VIDEO` folds the log into the current notes for a cut; review/status.json is the
builder's status line ({text, busy}), written by `studio status`.
"""
import json
import mimetypes
import re
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import settings
from . import cuts, render
from .workspace import locked
from . import timeline as tl

_lock = threading.Lock()


def notes_file(video):
    return Path(video) / "review" / "notes.jsonl"


def append(video, entry):
    f = notes_file(video)
    f.parent.mkdir(parents=True, exist_ok=True)
    entry = {**entry, "created": time.strftime("%Y-%m-%d %H:%M:%S")}
    with _lock, locked(video), f.open("a", encoding="utf-8") as out:
        out.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read_log(video):
    f = notes_file(video)
    if not f.exists():
        return []
    return [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]


def fold(log, cut=None, since=None):
    """(notes, rounds): the current notes, in the order written, after edits, deletes, starts and
    resolves; each note has a `status` (queued, working, done) and its `reply`, if any. With `cut`,
    the notes on that cut plus earlier ones still open or resolved at or after `since` (when the
    previous cut was made), so a reply shows on the cut that answers it."""
    notes, rounds = {}, []
    for e in log:
        if e["type"] == "note":
            notes[e["id"]] = {**e, "status": "queued", "reply": None}
        elif e["type"] == "start" and e["id"] in notes:
            notes[e["id"]]["status"] = "working"
        elif e["type"] == "resolve" and e["id"] in notes:
            notes[e["id"]].update(status="done", reply=e.get("reply"), resolved=e.get("created", ""))
        elif e["type"] == "edit" and e["id"] in notes:
            notes[e["id"]].update({k: e[k] for k in ("note", "kind") if k in e})
        elif e["type"] == "delete":
            notes.pop(e["id"], None)
        elif e["type"] == "round":
            rounds.append(e)
    kept = [n for n in notes.values() if cut is None or n["cut"] == cut
            or ((n["cut"] or 0) < cut and (n["status"] != "done" or (since and n.get("resolved", "") >= since)))]
    return kept, [r for r in rounds if cut is None or r["cut"] == cut]


def state(video, cut=None):
    video = Path(video)
    latest = render.latest_cut(video)
    n = cut or latest
    record = render.read_cut(video, n) if n else None
    snapshot = video / "cuts" / f"cut{n}" / "timeline.json"
    t = json.loads(snapshot.read_text()) if snapshot.exists() else tl.load(video)
    if record and record.get("video") and not cuts.playable(video, n):
        record = {**record, "video": None}
    if record:
        record = {**record, "kind": cuts.kind(record), "stills": [s for s in record.get("stills", [])
                                      if (video / "cuts" / f"cut{n}" / s["file"]).exists()]}
    # Replies made since the previous cut show here, whether the builder resolved before or after cutting.
    prev = render.read_cut(video, n - 1) if n and n > 1 else None
    notes, rounds = fold(read_log(video), n, (prev or {}).get("created") or (record or {}).get("created"))
    title = t.get("title") or video.name
    title = settings.raw(video).get("title", title)
    return {
        "title": title, "latest": latest, "cut": record,
        "cuts": sorted(int(p.name[3:]) for p in render.cuts_dir(video).glob("cut*")
                       if p.name[3:].isdigit() and (p / "cut.json").exists()),
        "narration": [{k: s[k] for k in ("id", "clip", "start", "end", "caption")} for s in t["tracks"]["narration"]],
        "chapters": [{"id": c["id"], "title": c["title"], "start": c["start"]} for c in t["tracks"]["scene"]],
        "notes": notes, "rounds": rounds, "status": read_status(video),
    }


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
    return append(video, {"type": how, "id": note_id, **({"reply": reply} if how == "resolve" else {})})


def wait(video, timeout=None, poll=0.5, settle=1.5):
    """Block until a note is added after the call, then return the new notes (a burst that arrives
    together comes back together). None on timeout."""
    known = {e["id"] for e in read_log(video) if e["type"] == "note"}
    end = time.time() + timeout if timeout else None
    while end is None or time.time() < end:
        if any(e["type"] == "note" and e["id"] not in known for e in read_log(video)):
            time.sleep(settle)
            notes, _ = fold(read_log(video))
            return [n for n in notes if n["id"] not in known]
        time.sleep(poll)
    return None


def notes_text(video, cut=None):
    """The notes for a cut as numbered plain text, the form the agent works from."""
    n = cut or render.latest_cut(video)
    notes, rounds = fold(read_log(video), n)
    count = f"{len(notes)} note" + ("" if len(notes) == 1 else "s")
    lines = [f"cut {n}: {count}" + (f", round sent {rounds[-1]['created']}" if rounds else ", round not sent")]
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
            return self._send(200, PAGE, "text/html; charset=utf-8")
        if path == "/api/events":
            return self._events()
        if path == "/api/state":
            q = re.search(r"cut=(\d+)", self.path)
            return self._json(state(self.video, int(q.group(1)) if q else None))
        m = re.fullmatch(r"/cut(\d+)/([\w./-]+)", path)
        if m and ".." not in m.group(2):
            f = render.cuts_dir(self.video) / f"cut{m.group(1)}" / m.group(2)
            if f.is_file():
                if f.name == "video.mp4":
                    cuts.mark_watched(self.video, int(m.group(1)))
                return self._file(f)
        self._send(404, b"not found", "text/plain")

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
        does, `cut` when a newer cut lands. Polled twice a second; a comment line keeps it open."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        def stamp(f):
            return f.stat().st_mtime_ns if f.exists() else 0
        seen = {"notes": stamp(notes_file(self.video)), "status": stamp(status_file(self.video)),
                "cut": render.latest_cut(self.video)}
        try:
            while True:
                time.sleep(0.5)
                now = {"notes": stamp(notes_file(self.video)), "status": stamp(status_file(self.video)),
                       "cut": render.latest_cut(self.video)}
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
            fields = ("cut", "t", "clip", "sentence_id", "sentence", "previous_id", "previous", "kind", "note")
            entry = append(self.video, {"type": "note", "id": uuid.uuid4().hex[:8], **{k: body.get(k) for k in fields}})
            return self._json(entry)
        m = re.fullmatch(r"/api/notes/(\w+)/(edit|delete)", self.path)
        if m:
            extra = {k: body[k] for k in ("note", "kind") if k in body} if m.group(2) == "edit" else {}
            return self._json(append(self.video, {"type": m.group(2), "id": m.group(1), **extra}))
        if self.path == "/api/round":
            cut = int(body["cut"])
            notes, _ = fold(read_log(self.video), cut)
            return self._json(append(self.video, {"type": "round", "cut": cut, "notes": [n["id"] for n in notes]}))
        self._send(404, b"not found", "text/plain")


def serve(video, port=8765, host="127.0.0.1"):
    handler = type("VideoHandler", (Handler,), {"video": Path(video).resolve()})
    server = ThreadingHTTPServer((host, port), handler)
    print(f"desk: http://{host}:{server.server_port}/  (notes → {notes_file(video)}; "
          f"studio wait {video} wakes on each)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


PAGE = (Path(__file__).parent / "page.html").read_text(encoding="utf-8")


def main_serve(args):
    serve(args.video, args.port)
    return 0


def main_notes(args):
    if args.start:
        mark(args.video, args.start, "start")
    if args.resolve:
        mark(args.video, args.resolve, "resolve", args.reply)
    if not (args.start or args.resolve):
        print(notes_text(args.video, args.cut))
    return 0


def main_wait(args):
    new = wait(args.video, args.timeout)
    if new is None:
        print(f"no new note in {args.timeout:g} s")
        return 2
    print(f"{len(new)} new note" + ("" if len(new) == 1 else "s") + ":")
    print("\n".join(describe(new)))
    return 0


def main_status(args):
    write_status(args.video, " ".join(args.text) or None, args.busy)
    return 0
