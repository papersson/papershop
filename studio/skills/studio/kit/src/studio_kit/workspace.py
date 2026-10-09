"""Atomic metadata updates, one build owner, short operation locks (Unix hosts), pending requests
and the builder's scratch folder."""
import contextlib
import fcntl
import json
import os
import socket
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as f:
        tmp = Path(f.name)
        json.dump(value, f, indent=1, ensure_ascii=False)
        f.write("\n")
    try:
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def runtime(video):
    video = Path(video).resolve()
    # Only inside a folder that exists: a lock taken on a mistyped path must not create a video there.
    if not video.is_dir():
        raise SystemExit(f"no folder at {video}; `studio new` makes a video")
    p = video / ".cache" / "studio"
    p.mkdir(parents=True, exist_ok=True)
    return p


@contextlib.contextmanager
def locked(video, name="metadata", blocking=True):
    with (runtime(video) / f"{name}.lock").open("a+") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError:
            raise SystemExit(f"another studio {name} operation is running for {video}")
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def owner(video):
    p = runtime(video) / "owner.json"
    return json.loads(p.read_text()) if p.exists() else None


def check_owner(video):
    """Stop unless this process holds the owner's token, or nobody owns the video."""
    rec = owner(video)
    if rec and rec["token"] != os.environ.get("STUDIO_OWNER"):
        raise SystemExit(f"video owned by {rec['name']} since {rec['created']}; use its STUDIO_OWNER token "
                         "or `studio lock VIDEO status` (recover only an abandoned build)")


@contextlib.contextmanager
def operation(video):
    with locked(video, "operation", blocking=False):
        check_owner(video)
        yield


def scratch(video):
    """VIDEO/.studio/work, made if missing: the builder's scratch files and helper scripts. Inside the
    video, so they survive a restart; ignored by Git and left behind by fork, so a helper worth
    keeping moves to sims/."""
    p = Path(video) / ".studio" / "work"
    p.mkdir(parents=True, exist_ok=True)
    return p


def pending(video):
    """The open requests in research/requests.md, as written after their checkbox: "ID TIME — TEXT"."""
    p = Path(video) / "research" / "requests.md"
    return [line[6:] for line in p.read_text().splitlines() if line.startswith("- [ ] ")] if p.exists() else []


def main_lock(args):
    with locked(args.video, "operation", blocking=False):
        rec = owner(args.video)
        p = runtime(args.video) / "owner.json"
        if args.action == "status":
            print(json.dumps(rec or {"owner": None}, indent=1))
        elif args.action == "acquire":
            if rec and not args.recover:
                raise SystemExit(f"already owned by {rec['name']}; --recover is only for an abandoned build")
            rec = {"name": args.owner, "token": uuid.uuid4().hex, "created": now(), "host": socket.gethostname()}
            atomic_json(p, rec)
            print(f"owner: {rec['name']}\nexport STUDIO_OWNER={rec['token']}")
            if args.recover:
                from . import handoff
                print("\n" + handoff.recovered(args.video))
        else:
            if rec and rec["token"] != os.environ.get("STUDIO_OWNER") and not args.recover:
                raise SystemExit("release needs the owner's STUDIO_OWNER token, or explicit --recover")
            p.unlink(missing_ok=True)
            print("owner released")
            from . import handoff
            reminder = handoff.reminder(args.video)
            if reminder:
                print(reminder)


def main_request(args):
    p = Path(args.video) / "research" / "requests.md"
    with locked(args.video):
        p.parent.mkdir(parents=True, exist_ok=True)
        text = p.read_text() if p.exists() else "# Pending requests\n"
        if args.resolve:
            marker = f"- [ ] {args.resolve} "
            if marker not in text:
                raise SystemExit(f"no pending request {args.resolve}")
            text = text.replace(marker, f"- [x] {args.resolve} ", 1)
            from .stage import read
            marks = read(args.video)
            text += f"\nResolved {args.resolve} at {now()}, stage {marks[-1]['stage'] if marks else 'unmarked'}.\n"
        elif args.text:
            text += f"\n- [ ] {uuid.uuid4().hex[:8]} {now()} — {args.text.replace(chr(10), ' ')}\n"
        else:
            print(text)
            return
        with tempfile.NamedTemporaryFile("w", dir=p.parent, delete=False) as f:
            f.write(text)
        Path(f.name).replace(p)
