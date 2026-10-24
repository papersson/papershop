"""Stage timing measures the wait the user experiences without controlling the work."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .workspace import locked


def log_path(video):
    return Path(video) / "research" / "timing.jsonl"


def read(video):
    f = log_path(video)
    if not f.exists():
        return []
    return [json.loads(line) for line in f.read_text().splitlines() if line.strip()]


def fmt(seconds):
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}m{s:02d}s" if m < 60 else f"{m // 60}h{m % 60:02d}m"


def durations(marks, now=None):
    """[(stage, seconds)] for each mark, the last one running until `now`."""
    now = now if now is not None else time.time()
    out = []
    for a, b in zip(marks, marks[1:] + [{"t": now}]):
        out.append((a["stage"], max(0, b["t"] - a["t"]) if a["stage"] != "finished" else 0))
    return out


def report(video, now=None):
    marks = read(video)
    if not marks:
        return ["no stages marked yet (studio stage VIDEO NAME)"]
    rows = durations(marks, now)
    total = sum(s for _, s in rows)
    width = max(len(n) for n, _ in rows)
    out = [f"{n:<{width}}  {fmt(s):>7}  {100 * s / max(total, 1):4.0f}%" for n, s in rows]
    active = sum(s for n, s in rows if n not in ("waiting", "finished"))
    return out + [f"{'total':<{width}}  {fmt(total):>7}", f"active {fmt(active)} · waiting {fmt(total - active)}"]


def mark(video, name, now=None):
    """Append the start of a stage and report the preceding stage's elapsed time."""
    now = time.time() if now is None else now
    with locked(video):
        marks = read(video)
        entry = {"stage": name, "t": now, "at": datetime.fromtimestamp(now, timezone.utc).isoformat(timespec="seconds")}
        f = log_path(video)
        f.parent.mkdir(parents=True, exist_ok=True)
        with f.open("a") as out:
            out.write(json.dumps(entry) + "\n")
    lines = [f"{marks[-1]['stage']}: {fmt(now - marks[-1]['t'])}"] if marks else []
    from . import events
    events.emit(video, 'stage', name, ts=now, source='research/timing.jsonl')
    return lines + [f"now: {name}"]


def main(args):
    print("\n".join(report(args.video) if args.report or not args.name else mark(args.video, args.name)))
    return 0
