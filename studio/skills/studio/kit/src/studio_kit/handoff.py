"""`studio handoff VIDEO`: research/handoff.md, a brief a fresh builder can resume from without the
earlier transcript.

One restart after a builder ran out of context depended on notes that builder happened to write.
So the brief is assembled from the files: the owner, mode and level, the stage against its budget,
the last cut and its open notes, reviews in flight, pending requests, the next commands they imply
and where scratch lives, with the builder's own notes for what only it knows. `lock acquire
--recover` rebuilds the state from the files and keeps only those notes. A chapter fixer
(STUDIO_ROLE=fixer) reports to the main session instead of writing one.
"""
import json
import os
import shlex
import time
from datetime import datetime
from pathlib import Path

from . import settings, stage, workspace


NOTES = "## Builder notes"


def path(video):
    return Path(video) / "research" / "handoff.md"


def one_line(text):
    """TEXT with its whitespace collapsed, so a note or a request can't start a line of the brief."""
    return " ".join(str(text).split())


def bundle_dir(video, kind):
    """Where a review kind packaged for the main session keeps its bundles: research/<kind>_review
    (frames: frame_review), unless the kind names its own `bundles` folder."""
    return Path(video) / (getattr(kind, "bundles", None) or f"research/{kind.name.removesuffix('s')}_review")


def bundles(video):
    """[(kind, cut, manifest)] for review bundles prepared and not imported, newer than the cut that
    kind's receipts last judged, for every kind in the registry."""
    from .review_state import read
    from .reviews import KINDS
    out = []
    for kind in KINDS.values():
        done = max((read(video, role).get("cut") or 0 for role in kind.roles), default=0)
        for m in bundle_dir(video, kind).glob("*/manifest.json"):
            cut = json.loads(m.read_text()).get("cut") or 0
            if not (m.parent / "result.md").exists() and cut > done:
                out.append((kind, cut, m))
    return sorted(out, key=lambda b: (b[0].name, b[1]))


def receipts(video):
    """[(receipt, why)] for each review receipt that does not stand for the current revision (or, for
    a kind that stands for its lineage, that a structural revision has superseded) or is unsettled."""
    from .review_state import read, revision, stands
    from .reviews import KINDS, ROLES
    current, out = {}, []
    for role in ROLES:
        rec = read(video, role)
        if not rec:
            continue
        kind = KINDS[rec["kind"]]
        current.setdefault(kind.name, revision(video, kind))
        if not stands(video, rec, kind, current[kind.name]):
            out.append((rec, f"stale: judged {'cut ' + str(rec['cut']) if rec.get('cut') else 'an earlier revision'}"))
        elif rec["status"] not in kind.settled:
            out.append((rec, rec["status"] + (", OPEN at the round cap" if rec.get("stopped") == "cap" else "")))
    return out


def relative(video, detail):
    """A receipt's detail, as a path inside the video where it is one."""
    p = Path(str(detail))
    return str(p.relative_to(video)) if p.is_absolute() and p.is_relative_to(video) else str(detail)


def assemble(video, notes=None, now=None, notes_at=None):
    """The brief, as markdown. Paths are relative to the video and commands name it as $VIDEO, so the
    brief reads the same on another machine; `notes_at` dates builder notes kept from an earlier brief."""
    from . import cuts, page
    from .review_state import fingerprint
    video = Path(video).resolve()
    v = '"$VIDEO"'
    cfg = settings.load(video)
    owner = workspace.owner(video)
    s = stage.status(video, now)
    recs = cuts.records(video)
    n = cuts.latest(video, recs=recs)
    rendered = cuts.latest(video, cuts.RENDERED, recs=recs)
    open_notes = [x for x in page.fold(page.read_log(video))[0] if x["status"] != "done"]
    waiting, stale, pending = bundles(video), receipts(video), [one_line(r) for r in workspace.pending(video)]
    when = datetime.fromtimestamp(now) if now is not None else datetime.now()
    fmt = stage.fmt

    out = [f"# Handoff: {one_line(cfg.get('title', video.name))}", "",
           f"Written {when.isoformat(timespec='seconds')}. Paths are relative to the video's folder, and the commands "
           "name it as $VIDEO (`export VIDEO=PATH` first).", "", "## State", ""]
    out.append(f"- Owner: {one_line(owner['name'])} since {owner['created']}" if owner else "- Owner: none")
    out.append(f"- Mode {cfg['mode']}, level {cfg['level']}, engine {cfg['engine']}")
    if s["stage"] is None:
        out.append("- Stage: none marked yet")
    else:
        own = f"; stage total {fmt(s['total'])} of {fmt(s['budget'])}" if s["budget"] is not None else ""
        sc = s["scope"]
        out.append(f"- Stage: {one_line(s['stage'])} ({s['kind']}), {fmt(s['spent'])} since its mark{own}"
                   f"{' (STOPPED: past the hard stop)' if s['stop'] else ' (over)' if s['over'] else ''}; "
                   f"{fmt(sc['spent'])} into {stage.SCOPES[sc['name']]}, budget {fmt(sc['limit'])}"
                   f"{' (over, advisory)' if sc['over'] else ''}")
    if n:
        rec = recs[n]
        out.append(f"- Last cut: {n} ({cuts.kind(rec)}, {rec.get('quality', '?')}, {rec.get('created', '?')})"
                   + (f"; last rendered cut {rendered}" if rendered and rendered != n else ""))
    else:
        out.append("- Last cut: none")
    out.append(f"- Open desk notes: {len(open_notes)}" + "".join(
        f"\n  - {one_line(x['id'])} ({x['status']}, cut {x['cut']}, {one_line(x['sentence_id'] or x['clip'])}): "
        f"{one_line(x['note'] or '(here)')}" for x in open_notes))
    out.append("- Reviews in flight:" + (" none" if not (waiting or stale) else "".join(
        [f"\n  - {k.name} review of cut {c} prepared, not imported: {m.relative_to(video)}" for k, c, m in waiting] +
        [f"\n  - {r['role']}: {why} ({one_line(relative(video, r.get('detail') or 'no detail'))})" for r, why in stale])))
    out.append("- Pending requests:" + (" none" if not pending else "".join(f"\n  - {r}" for r in pending)))

    steps = []
    if s["stop"]:
        steps.append(f"Stage {one_line(s['stage'])} is past its hard stop: the main session decides whether to raise "
                     f"video.json budget.{one_line(s['stage'])} before anyone continues it")
    steps += [f"The main session gives {m.parent.relative_to(video)} to a fresh reviewer; import its response: "
              f"`studio review-{k.name} {v} --cut {c} --result FILE`" for k, c, m in waiting]
    for r, why in stale:
        if r["kind"] == "script":
            ready = f"report ready for the {r['role']} script review (`studio review {v} ROUND --only {r['role']}`)"
            steps.append(f"Address the findings in {one_line(relative(video, r['detail']))}, then {ready}"
                         if r["status"] == "findings" else "R" + ready[1:])
        elif r.get("stopped") == "cap" and not why.startswith("stale"):
            steps.append(f"The motion review stopped at its cap with must-fix findings open "
                         f"({one_line(relative(video, r.get('detail') or 'no detail'))}): the main session decides whether to "
                         f"fix them and record the user's acceptance (`studio review-status {v} motion waived --reason …`) "
                         "or, if the user asks, raise video.json motion_rounds")
        elif not any(k.name == r["kind"] for k, _, _ in waiting):    # a newer bundle is already out
            sheets = f"`studio sheets {v} {v}/out/sheets`, " if r["kind"] == "frames" else ""
            fix = f"Fix the must-fix findings in {one_line(relative(video, r['detail']))}, then make" \
                if r["status"] == "findings" and not why.startswith("stale") else "Make"
            steps.append(f"{fix} a fresh cut, {sheets}`studio review-{r['kind']} {v}`, and report ready for "
                         f"the {r['kind']} review")
    steps += [f"Incorporate request {r.split()[0]}, then `studio request {v} --resolve {r.split()[0]}`" for r in pending]
    steps += [f"Resolve note {one_line(x['id'])}: `studio notes {v} --start {one_line(x['id'])}`, change, then "
              f"`studio notes {v} --resolve {one_line(x['id'])} --reply TEXT`" for x in open_notes]
    if rendered and recs[rendered].get("source_revision") != fingerprint(video, frames=True):
        steps.append(f"Cut, since the sources changed after cut {rendered}: `studio cut {v}`")
    steps.append(f"Mark the stage you resume: `studio stage {v} NAME`"
                 + (f" (the log's latest is {one_line(s['stage'])})" if s["stage"] else ""))
    out += ["", "## Next", ""] + [f"{i}. {step}" for i, step in enumerate(steps, 1)]

    work = video / ".studio" / "work"
    files = sorted(one_line(p.relative_to(work)) for p in work.rglob("*") if p.is_file()) if work.is_dir() else []
    out += ["", "## Scratch", "",
            f".studio/work: {len(files)} file{'' if len(files) == 1 else 's'}" + (": " + ", ".join(files[:12]) if files else "")
            + (", …" if len(files) > 12 else "") + ". Ignored by Git and left behind by fork; helpers worth keeping "
            "belong in sims/."]
    dated = f" (written {datetime.fromtimestamp(notes_at).isoformat(timespec='seconds')})" if notes_at else ""
    out += ["", NOTES + dated, "", (notes or "").strip() or "(none given)"]
    return "\n".join(out) + "\n"


def write(video, notes=None, now=None):
    p = path(video)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(assemble(video, notes, now))
    return p


def stored_notes(video):
    """(notes, when written) from research/handoff.md: the one part of a brief the files can't rebuild."""
    p = path(video)
    head, sep, tail = p.read_text().partition("\n" + NOTES)
    notes = tail.split("\n", 1)[1].strip() if sep and "\n" in tail else ""
    return ("" if notes == "(none given)" else notes), p.stat().st_mtime


def export(video):
    return f"export VIDEO={shlex.quote(str(Path(video).resolve()))}"


def recovered(video):
    """What `lock acquire --recover` prints: a brief assembled now, so it never repeats a state that
    has changed since (a stop the main session lifted), with the stored builder notes and their age."""
    p = path(video)
    if not p.exists():
        return f"no handoff at {p}; assemble one from the files with `studio handoff {shlex.quote(str(Path(video).resolve()))}`"
    notes, written = stored_notes(video)
    after = [m for m in stage.read(video) if m["t"] > written]
    since = f"; {len(after)} stage mark{'' if len(after) == 1 else 's'} since (latest {one_line(after[-1]['stage'])} " \
        f"at {after[-1]['at']})" if after else ""
    return (f"handoff: the state below is read from the files now; the builder notes were written "
            f"{datetime.fromtimestamp(written).isoformat(timespec='seconds')} "
            f"({stage.fmt(time.time() - written)} ago{since})\n{export(video)}\n\n"
            + assemble(video, notes, notes_at=written))


def reminder(video):
    """A line for the end of a background run whose handoff is missing or older than its latest mark."""
    if settings.load(video)["mode"] != "background":
        return None
    marks = stage.read(video)
    if marks and marks[-1]["stage"] == "finished":
        return None
    p = path(video)
    if p.exists() and (not marks or p.stat().st_mtime >= marks[-1]["t"]):
        return None
    return (f"the build is not finished and {'its handoff is older than the latest stage mark' if p.exists() else 'has no handoff'}: "
            f"write one for the next builder with `studio handoff {shlex.quote(str(Path(video).resolve()))} --notes \"…\"`")


def main(args):
    if os.environ.get("STUDIO_ROLE") == "fixer":
        raise SystemExit("a chapter fixer reports its notes to the main session, which writes the handoff")
    notes = Path(args.notes_file).read_text() if args.notes_file else args.notes
    p = write(args.video, notes)
    print(f"{export(args.video)}\n\n{p.read_text()}\nwritten to {p}")
    return 0
