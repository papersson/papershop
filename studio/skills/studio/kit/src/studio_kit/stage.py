"""`studio stage VIDEO NAME`: mark the start of a stage, and see where the time went.

A video's wall-clock time is the cost the user feels. Long builds came from loops nobody was
timing (six script review rounds, three competing narratives), so every stage is marked as it
starts: `studio stage VIDEO script`, `studio stage VIDEO scenes`, ... Each mark is appended to
research/timing.jsonl, and the command prints how long the previous stage took and the total
against video.json's "budget" (minutes: "first_cut" from the first mark to the first cut,
"round" for a revision round). Over budget, it says so: finish the stage with what is open
logged, rather than looping. `studio stage VIDEO --report` prints the table.
"""
import json
import time
from datetime import datetime
from pathlib import Path

from . import settings

DEFAULT_BUDGET = {"first_cut": 20, "round": 5}    # minutes, for the default "intro" level
LEVEL_BUDGET = {"intro": DEFAULT_BUDGET, "deep-dive": {"first_cut": 60, "round": 10}}
ROUND_STAGES = {"round", "revision"}              # a mark named like this starts a revision round


def log_path(video):
    return Path(video) / "research" / "timing.jsonl"


def read(video):
    f = log_path(video)
    if not f.exists():
        return []
    return [json.loads(line) for line in f.read_text().splitlines() if line.strip()]


def budget(video):
    cfg = settings.load(video)
    return {**LEVEL_BUDGET.get(cfg["level"], DEFAULT_BUDGET), **cfg.get("budget", {})}


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


def mark(video, name, now=None, kind="local", summary=None):
    """Append a mark and return the lines to print."""
    now = now if now is not None else time.time()
    marks = read(video)
    lines = []
    if marks:
        prev = marks[-1]
        lines.append(f"{prev['stage']}: {fmt(now - prev['t'])}")
    marks.append({"stage": name, "t": now, "at": datetime.fromtimestamp(now).isoformat(timespec="seconds"), "kind": kind})
    f = log_path(video)
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a") as out:
        out.write(json.dumps(marks[-1]) + "\n")
    b = budget(video)
    rounds = [m for m in marks if m["stage"] in ROUND_STAGES]
    start = marks.index(rounds[-1]) if rounds else 0
    spent = sum(d for stage, d in durations(marks[start:], now) if stage not in ("waiting", "finished"))
    structural = bool(rounds and rounds[-1].get("kind") == "structural")
    limit = (b.get("structural_round", b["round"] * 4) if structural else b["round"] if rounds else b["first_cut"]) * 60
    what = "this structural revision round" if structural else "this revision round" if rounds else "the first cut"
    lines.append(f"now: {name} · {fmt(spent)} into {what} (budget {fmt(limit)})")
    if spent > limit:
        lines.append(f"OVER BUDGET by {fmt(spent - limit)}: finish this stage with what is open logged, "
                     "treat the budget as advisory, re-estimate changed scope, and report stage time")
    if summary:
        from .script import append_review
        append_review(video, f"{datetime.fromtimestamp(now).isoformat(timespec='seconds')} {kind} revision: {summary}")
    requests = Path(video) / "research" / "requests.md"
    if requests.exists():
        lines += ["pending: " + line[6:] for line in requests.read_text().splitlines() if line.startswith("- [ ] ")]
    from . import page
    notes, _ = page.fold(page.read_log(video))
    lines += [f"open note {n['id']} on {n['sentence_id'] or n['clip']}: {n['note'] or '(here)'}"
              for n in notes if n["status"] != "done"]
    return lines


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


def main(args):
    if args.report or not args.name:
        print("\n".join(report(args.video)))
        return 0
    print("\n".join(mark(args.video, args.name, kind=args.kind, summary=args.summary)))
    return 0
