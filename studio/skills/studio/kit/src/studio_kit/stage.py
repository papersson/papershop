"""`studio stage VIDEO NAME`: mark the start of a stage, and see where the time went.

A video's wall-clock time is the cost the user feels. Long builds came from loops nobody was
timing (six script review rounds, three competing narratives), so every stage is marked as it
starts: `studio stage VIDEO script`, `studio stage VIDEO scenes`, ... Each mark is appended to
research/timing.jsonl, and the command prints how long the previous stage took and the total
against video.json's "budget" (minutes: "first_cut" from the first mark to the first cut,
"round" for a revision round, "structural_round" for a structural one, and any stage's name for
that stage alone). Over budget, it says so: finish the stage with what is open logged, rather than
looping. `studio stage VIDEO --report` prints the table. `status` is the same reading as data.

Budgets are advisory, with one exception: in background mode a stage with its own budget in
video.json stops at twice that budget (one polish stage ran over five hours unattended). `mark`
then prints STOP, and `studio stage VIDEO --check`, which a builder runs between chapters, exits 3.
The scopes' defaults are not calibrated against real builds, so they never stop anything.
"""
import json
import shlex
import time
from datetime import datetime
from pathlib import Path

from . import settings, workspace

DEFAULT_BUDGET = {"first_cut": 20, "round": 5}    # minutes, for the default "intro" level
LEVEL_BUDGET = {"intro": DEFAULT_BUDGET, "deep-dive": {"first_cut": 60, "round": 10}}
ROUND_STAGES = {"round", "revision"}              # a mark named like this starts a revision round
AGGREGATES = {"first_cut", "round", "structural_round"}   # budget keys that are not a stage's own
SCOPES = {"first_cut": "the first cut", "round": "this revision round",
          "structural_round": "this structural revision round"}
HARD_STOP = 2                                     # × a stage's own budget, in background mode
STOPPED = 3                                       # `stage --check`'s exit status once stopped


def log_path(video):
    return Path(video) / "research" / "timing.jsonl"


def read(video):
    f = log_path(video)
    if not f.exists():
        return []
    return [json.loads(line) for line in f.read_text().splitlines() if line.strip()]


def budget(video, cfg=None):
    cfg = cfg or settings.load(video)
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


def status(video, now=None):
    """Where the build stands against its budgets, as data, for `mark` to print and for anything that
    acts on an overrun. Seconds throughout:
    {stage, kind, spent, total, budget, over, stop, scope: {name, spent, limit, ratio, over}}: the
    latest mark and the time since it; every run of that stage in the scope (a stage resumed after
    waiting counts once more), against video.json's budget for it if it names one, and whether that
    total has reached the hard stop (background mode only); and the scope the stage counts towards
    (first_cut, round or structural_round), which runs from the latest round mark on.
    """
    now = now if now is not None else time.time()
    cfg = settings.load(video)
    marks, b = read(video), budget(video, cfg)
    current = marks[-1] if marks else {}
    spent = now - current["t"] if marks else 0
    own = b.get(current.get("stage")) if current.get("stage") not in AGGREGATES else None
    rounds = [m for m in marks if m["stage"] in ROUND_STAGES]
    start = marks.index(rounds[-1]) if rounds else 0
    runs = durations(marks[start:], now)
    total = sum(d for stage, d in runs if stage == current.get("stage"))
    scope_spent = sum(d for stage, d in runs if stage not in ("waiting", "finished"))
    scope = "structural_round" if rounds and rounds[-1].get("kind") == "structural" else "round" if rounds else "first_cut"
    limit = (b.get("structural_round", b["round"] * 4) if scope == "structural_round" else b[scope]) * 60
    return {"stage": current.get("stage"), "kind": current.get("kind"), "spent": spent, "total": total,
            "budget": own * 60 if own is not None else None, "over": own is not None and total > own * 60,
            "stop": own is not None and cfg["mode"] == "background" and current["stage"] not in ("waiting", "finished")
                    and total >= HARD_STOP * own * 60,
            "scope": {"name": scope, "spent": scope_spent, "limit": limit, "ratio": scope_spent / limit if limit else None,
                      "over": scope_spent > limit}}


def mark(video, name, now=None, kind="local", summary=None):
    """Append a mark and return the lines to print."""
    now = now if now is not None else time.time()
    lines = []
    if read(video):
        ended = status(video, now)
        line = f"{ended['stage']}: {fmt(ended['spent'])}"
        if ended["budget"] is not None:
            line += f" (stage: {fmt(ended['total'])} of {fmt(ended['budget'])}" + \
                (f", over by {fmt(ended['total'] - ended['budget'])})" if ended["over"] else ")")
        lines.append(line)
    entry = {"stage": name, "t": now, "at": datetime.fromtimestamp(now).isoformat(timespec="seconds"), "kind": kind}
    f = log_path(video)
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a") as out:
        out.write(json.dumps(entry) + "\n")
    s = status(video, now)
    sc = s["scope"]
    own = f" (stage: {fmt(s['total'])} of {fmt(s['budget'])})" if s["budget"] is not None else ""
    lines.append(f"now: {name}{own} · {fmt(sc['spent'])} into {SCOPES[sc['name']]} (budget {fmt(sc['limit'])})")
    if s["stop"]:
        lines.append(stop_line(video, s))
    elif sc["over"]:
        lines.append(f"OVER BUDGET by {fmt(sc['spent'] - sc['limit'])}: finish this stage with what is open logged, "
                     "treat the budget as advisory, re-estimate changed scope, and report stage time")
    if summary:
        from .script import append_review
        append_review(video, f"{datetime.fromtimestamp(now).isoformat(timespec='seconds')} {kind} revision: {summary}")
    lines += ["pending: " + r for r in workspace.pending(video)]
    from . import page
    notes, _ = page.fold(page.read_log(video))
    lines += [f"open note {n['id']} on {n['sentence_id'] or n['clip']}: {n['note'] or '(here)'}"
              for n in notes if n["status"] != "done"]
    return lines


def stop_line(video, s):
    v = shlex.quote(str(Path(video).resolve()))
    return (f"STOP: {s['stage']} has run {fmt(s['total'])} against its {fmt(s['budget'])} budget, and in background mode "
            f"{HARD_STOP}× a stage's budget ends the run. Write a handoff (studio handoff {v} --notes \"what only you "
            "know\"), report to the main session, and do not continue: the main session decides whether to raise "
            f"video.json budget.{s['stage']} or stop here")


def check(video, now=None):
    """(lines, stopped): the current stage against its budgets, read without marking anything."""
    s = status(video, now)
    if s["stage"] is None:
        return ["no stages marked yet (studio stage VIDEO NAME)"], False
    sc = s["scope"]
    own = f", stage {fmt(s['total'])} of {fmt(s['budget'])}" + (" (over)" if s["over"] else "") if s["budget"] is not None else ""
    lines = [f"{s['stage']}: {fmt(s['spent'])} since its mark{own} · {fmt(sc['spent'])} into {SCOPES[sc['name']]} "
             f"(budget {fmt(sc['limit'])}{', over, advisory' if sc['over'] else ''})"]
    return lines + ([stop_line(video, s)] if s["stop"] else []), s["stop"]


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
    if args.check:
        lines, stopped = check(args.video)
        print("\n".join(lines))
        return STOPPED if stopped else 0
    if args.report or not args.name:
        print("\n".join(report(args.video)))
        return 0
    print("\n".join(mark(args.video, args.name, kind=args.kind, summary=args.summary)))
    return 0
