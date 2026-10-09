"""`studio handoff VIDEO`: research/handoff.md, a brief a fresh builder can resume from without the
earlier transcript.

One restart after a builder ran out of context depended on notes that builder happened to write.
So the brief is assembled from the files: the owner, mode and level, the stage against its budget,
the last cut and its open notes, reviews in flight, pending requests, the next commands they imply
and where scratch lives, with the builder's own notes for what only it knows. `lock acquire
--recover` prints it.
"""
import json
import shlex
from datetime import datetime
from pathlib import Path

from . import settings, stage, workspace


def path(video):
    return Path(video) / "research" / "handoff.md"


def frame_bundles(video):
    """[(cut, manifest)] for frame-review bundles prepared and not imported, past the last imported cut."""
    from .review_state import read
    done = read(video, "frames").get("cut") or 0
    out = []
    for m in sorted((Path(video) / "research" / "frame_review").glob("*/manifest.json")):
        cut = json.loads(m.read_text())["cut"]
        if not (m.parent / "result.md").exists() and cut > done:
            out.append((cut, m))
    return sorted(out)


def receipts(video):
    """[(receipt, why)] for each review receipt that does not stand for the current revision."""
    from .review_state import read, revision
    from .reviews import KINDS, ROLES
    current, out = {}, []
    for role in ROLES:
        rec = read(video, role)
        if not rec:
            continue
        kind = KINDS[rec["kind"]]
        current.setdefault(kind.name, revision(video, kind))
        if rec.get("revision") != current[kind.name]:
            out.append((rec, f"stale: judged {'cut ' + str(rec['cut']) if rec.get('cut') else 'an earlier revision'}"))
        elif rec["status"] not in ("passed", "waived"):
            out.append((rec, rec["status"]))
    return out


def assemble(video, notes=None, now=None):
    """The brief, as markdown."""
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
    bundles, stale, pending = frame_bundles(video), receipts(video), workspace.pending(video)
    when = datetime.fromtimestamp(now) if now is not None else datetime.now()

    out = [f"# Handoff: {cfg.get('title', video.name)}", "",
           f"Written {when.isoformat(timespec='seconds')}. The commands below name the video as $VIDEO:", "",
           f"    export VIDEO={shlex.quote(str(video))}", "", "## State", ""]
    out.append(f"- Owner: {owner['name']} since {owner['created']} on {owner['host']}" if owner else "- Owner: none")
    out.append(f"- Mode {cfg['mode']}, level {cfg['level']}, engine {cfg['engine']}")
    if s["stage"] is None:
        out.append("- Stage: none marked yet")
    else:
        own = f"; stage total {stage.fmt(s['total'])} of {stage.fmt(s['budget'])}" if s["budget"] is not None else ""
        sc = s["scope"]
        out.append(f"- Stage: {s['stage']} ({s['kind']}), {stage.fmt(s['spent'])} since its mark{own}"
                   f"{' (STOPPED: past the hard stop)' if s['stop'] else ' (over)' if s['over'] else ''}; "
                   f"{stage.fmt(sc['spent'])} into {stage.SCOPES[sc['name']]}, budget {stage.fmt(sc['limit'])}"
                   f"{' (over, advisory)' if sc['over'] else ''}")
    if n:
        rec = recs[n]
        out.append(f"- Last cut: {n} ({cuts.kind(rec)}, {rec.get('quality', '?')}, {rec.get('created', '?')})"
                   + (f"; last rendered cut {rendered}" if rendered and rendered != n else ""))
    else:
        out.append("- Last cut: none")
    out.append(f"- Open desk notes: {len(open_notes)}" + "".join(
        f"\n  - {x['id']} ({x['status']}, cut {x['cut']}, {x['sentence_id'] or x['clip']}): {x['note'] or '(here)'}"
        for x in open_notes))
    out.append("- Reviews in flight:" + (" none" if not (bundles or stale) else "".join(
        [f"\n  - frame review of cut {c} prepared, not imported: {m.relative_to(video)}" for c, m in bundles] +
        [f"\n  - {r['role']}: {why} ({r.get('detail') or 'no detail'})" for r, why in stale])))
    out.append("- Pending requests:" + (" none" if not pending else "".join(f"\n  - {r}" for r in pending)))

    steps = []
    if s["stop"]:
        steps.append(f"Stage {s['stage']} is past its hard stop: the main session decides whether to raise video.json "
                     f"budget.{s['stage']} before anyone continues it")
    steps += [f"The main session gives {m.parent.relative_to(video)} to a fresh reviewer; import its response: "
              f"`studio review-frames {v} --cut {c} --result FILE`" for c, m in bundles]
    for r, why in stale:
        if r["kind"] == "script":
            ready = f"report ready for the {r['role']} script review (`studio review {v} ROUND --only {r['role']}`)"
            steps.append(f"Address the findings in {r['detail']}, then {ready}" if r["status"] == "findings" else "R" + ready[1:])
        else:
            steps.append(f"Make a fresh cut, `studio sheets {v} {v}/out/sheets` and `studio review-frames {v}`, "
                         "and report ready for frame review")
    steps += [f"Incorporate request {r.split()[0]}, then `studio request {v} --resolve {r.split()[0]}`" for r in pending]
    steps += [f"Resolve note {x['id']}: `studio notes {v} --start {x['id']}`, change, then "
              f"`studio notes {v} --resolve {x['id']} --reply TEXT`" for x in open_notes]
    if rendered and recs[rendered].get("source_revision") != fingerprint(video, frames=True):
        steps.append(f"Cut, since the sources changed after cut {rendered}: `studio cut {v}`")
    steps.append(f"Mark the stage you resume: `studio stage {v} NAME`" + (f" (the log's latest is {s['stage']})" if s["stage"] else ""))
    out += ["", "## Next", ""] + [f"{i}. {step}" for i, step in enumerate(steps, 1)]

    work = video / ".studio" / "work"
    files = sorted(str(p.relative_to(work)) for p in work.rglob("*") if p.is_file()) if work.is_dir() else []
    out += ["", "## Scratch", "",
            f"$VIDEO/.studio/work: {len(files)} file{'' if len(files) == 1 else 's'}" + (": " + ", ".join(files[:12]) if files else "")
            + (", …" if len(files) > 12 else "") + ". Ignored by Git and left behind by fork; helpers worth keeping "
            "belong in sims/."]
    out += ["", "## Builder notes", "", (notes or "").strip() or "(none given)"]
    return "\n".join(out) + "\n"


def write(video, notes=None, now=None):
    p = path(video)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(assemble(video, notes, now))
    return p


def recovered(video):
    """What `lock acquire --recover` prints: the handoff and when it was written, or how to make one."""
    p = path(video)
    if not p.exists():
        return f"no handoff at {p}; assemble one from the files with `studio handoff {shlex.quote(str(Path(video).resolve()))}`"
    written = p.stat().st_mtime
    marks = stage.read(video)
    after = [m for m in marks if m["t"] > written]
    since = f"; {len(after)} stage mark{'' if len(after) == 1 else 's'} since (latest {after[-1]['stage']} at {after[-1]['at']})" \
        if after else ""
    return (f"handoff written {datetime.fromtimestamp(written).isoformat(timespec='seconds')}"
            f" ({stage.fmt(datetime.now().timestamp() - written)} ago{since}):\n\n{p.read_text()}")


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
    notes = Path(args.notes_file).read_text() if args.notes_file else args.notes
    p = write(args.video, notes)
    print(p.read_text() + f"\nwritten to {p}")
    return 0
