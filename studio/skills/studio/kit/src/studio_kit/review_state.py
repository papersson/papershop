"""Review receipts identify the exact material judged, without exposing earlier findings.

research/reviews/<role>.json: {role, kind, revision, status, detail, created}, with the round of a
script review, and for a frame review the cut it judged and whether that cut was older than the
sources when the result came in (stale, with what had changed). What each kind hashes, how its
verdict reads and what an older revision's result does are its policies in reviews.py.
research/reviews/rounds.jsonl logs the revision each round reviewed, which the round cap counts.
"""
import hashlib
import json
import shutil
import time
from pathlib import Path

from . import reviews
from .env import ROOT
from .reviews import KINDS, kind_of
from .workspace import atomic_json, now


def review_keys(video, t):
    """Each clip's review key (render.clip_key): what a frame of that clip shows."""
    from . import render
    return {c["id"]: render.clip_key(video, t, c["id"], "review") for c in t["tracks"]["scene"]}


def fingerprint(video, frames=False, keys=None):
    """The revision a review judged, so its receipt goes stale exactly when that material changes.

    A script review reads the learner, the charter and SCRIPT.md's teaching sections. A frame review
    reads its bundle: SCRIPT.md's Script and Evidence, data/, and the cut's frames, for which each
    clip's review key stands (its scene code, narration, captions, the cues it reads, layout, data
    and assets). timeline.json and narration.json are not hashed: they also change for what no
    frame shows (the timeline's sources, its audio and effects; the voice), and every part of them a
    frame shows is in some clip's key. `keys`: review_keys already worked out for the timeline.
    """
    video = Path(video)
    from .script import sections
    script = video / "SCRIPT.md"
    parts = sections(script.read_bytes().decode()) if script.exists() else None   # bytes: CRLF hashes as written
    h = hashlib.sha256()
    if frames:
        if parts is not None:
            h.update("\n".join(parts.get(k, "") for k in ("Script", "Evidence")).encode())
        for p in sorted((video / "data").rglob("*")):
            if p.is_file():
                h.update(str(p.relative_to(video)).encode())
                h.update(p.read_bytes())
        if keys is None and (video / "timeline.json").exists():
            from . import timeline
            keys = review_keys(video, timeline.load(video))
        for key in (keys or {}).values():
            h.update(key.encode())
        return h.hexdigest()
    from .review import learner_path, learner_brief, charter
    if learner_path(video).exists():
        h.update(learner_brief(video).encode())
    h.update(charter(video).encode())
    if parts is not None:
        # Status and Review log updates must not stale a review; the reviewed teaching material does.
        h.update(b"SCRIPT.md")
        h.update("\n".join(parts.get(k, "") for k in ("Argument", "Chain", "Script", "Evidence")).encode())
    return h.hexdigest()


def revision(video, kind):
    return fingerprint(video, frames=kind.scope == "frames")


def record(video, role, revision, status, detail="", **extra):
    """Write a receipt; `extra` (round, cut, stale, changed) only where the kind has them."""
    rec = {"role": role, "kind": kind_of(role).name, "revision": revision, "status": status, "detail": detail, "created": now()}
    rec |= {k: v for k, v in extra.items() if v is not None}
    atomic_json(Path(video) / "research" / "reviews" / f"{role}.json", rec)


def read(video, role):
    """A receipt, or {}; one written before receipts named their kind gets it from its role."""
    p = Path(video) / "research" / "reviews" / f"{role}.json"
    rec = json.loads(p.read_text()) if p.exists() else {}
    return {"kind": kind_of(role).name, **rec} if rec else rec


def required_roles(cfg):
    """Drive and depth choose script reviewers; explicit claim risk may add roles."""
    if not cfg.get("teaching_contract"):
        return ()
    roles = ["student"]
    if cfg.get("drive") == "learner" or cfg.get("level") == "deep-dive":
        roles += ["expert", "editor"]
    for role in cfg.get("review_roles", []):
        if role not in KINDS["script"].roles:
            raise SystemExit(f"unknown script review role: {role}")
        if role not in roles:
            roles.append(role)
    return tuple(roles)


def rounds_log(video):
    return Path(video) / "research" / "reviews" / "rounds.jsonl"


def _logged(video, kind):
    """A kind's rounds in the log, oldest first. A line that doesn't read (one cut short when a run
    was killed) is skipped with a warning, rather than stopping every later review."""
    p, out, bad = rounds_log(video), [], 0
    for line in p.read_text().splitlines() if p.exists() else []:
        try:
            e = json.loads(line)
            ok = isinstance(e, dict) and isinstance(e.get("t"), (int, float)) and isinstance(e.get("revision"), str)
        except ValueError:
            ok = False
        if not ok:
            bad += bool(line.strip())
        elif e.get("kind") == kind.name:
            out.append(e)
    if bad:
        print(f"warn: {p}: {bad} unreadable line(s) skipped")
    return out


def rounds(video, kind, revision=None):
    """The revisions of a kind's material reviewed since the latest stage mark that starts its count
    again (kind.rounds.resets_on), and that mark (None: there is none, so every round counts).
    A mark starts the count only when the material it was made over (its "revisions", or for an
    older mark the first revision reviewed after it, or `revision`, about to be) is not the last
    revision reviewed before it, so a mark alone buys no rounds. Reviewers run again on a revision
    already reviewed (a retry, an added role) are the same round."""
    from . import stage
    log, since = _logged(video, kind), None
    for m in stage.read(video):
        if m.get("kind") in kind.rounds.resets_on:
            before = [e["revision"] for e in log if e["t"] < m["t"]]
            over = m.get("revisions", {}).get(kind.name) or next((e["revision"] for e in log if e["t"] >= m["t"]), revision)
            if not before or over != before[-1]:
                since = m
    seen = []
    for e in log:
        if (since is None or e["t"] >= since["t"]) and e["revision"] not in seen:
            seen.append(e["revision"])
    return seen, since


def start_round(video, kind, number, revision, cfg):
    """Log a round of `kind` on `revision`, unless it is a new round past the kind's cap. The cap
    counts rounds of this revision of the script, so a typed round number neither spends nor saves
    one."""
    cap = kind.rounds.cap(cfg) if kind.rounds.cap else None
    seen, since = rounds(video, kind, revision)
    if cap is not None and revision not in seen and len(seen) >= cap:
        where = f"its {since['stage']} mark ({since['at']})" if since else "the first round"
        raise SystemExit(f"round {number} is past max_rounds ({cap}): this revision of the script has had {len(seen)} "
                         f"review rounds since {where}. Lock the script with every open finding logged, or ask the "
                         "learner to raise the cap. A structural rewrite (a new chapter or a changed arc, marked with "
                         "studio stage VIDEO revision --kind structural --summary …) starts a new count; a mark over "
                         "an unchanged script does not")
    log = rounds_log(video)
    text = log.read_text() if log.exists() else ""
    torn = bool(text) and not text.endswith("\n")      # a line cut short must not swallow this one
    with log.open("a") as f:
        f.write("\n" * torn + json.dumps({"kind": kind.name, "round": number, "revision": revision, "t": time.time()}) + "\n")


def changed_since(video, cut):
    """What a frame shows that changed since cut N, in a few words: the clips whose review keys
    differ from those the cut recorded, or just the fact for a cut that recorded none."""
    p = Path(video) / "cuts" / f"cut{cut}" / "cut.json"
    then = json.loads(p.read_text()).get("review_keys") if p.exists() else None
    if not then or not (Path(video) / "timeline.json").exists():
        return "the sources"
    from . import timeline
    current = review_keys(video, timeline.load(video))
    clips = [c for c in {**then, **current} if then.get(c) != current.get(c)]
    return ", ".join(clips) if clips else "SCRIPT.md's Script or Evidence"


def require(video, role):
    kind = kind_of(role)
    rec, current = read(video, role), revision(video, kind)
    if rec.get("revision") == current and rec.get("status") in ("passed", "waived"):
        return
    if kind.freshness == "record-stale" and rec.get("cut") is not None and rec.get("revision") != current:
        raise SystemExit(f"the {role} review judged cut {rec['cut']}, and {changed_since(video, rec['cut'])} changed since: "
                         f"make a fresh cut and {kind.remedy.format(role=role)}, or record an authorized waiver with "
                         "studio review-status")
    raise SystemExit(f"current {role} review missing, stale or unresolved; {kind.remedy.format(role=role)}"
                     "; an authorized waiver can be recorded with studio review-status")


def main_status(args):
    role = reviews.role(args.role)
    if args.status == "waived" and not args.reason:
        raise SystemExit("record the user's authorization in --reason for a waived review")
    record(args.video, role, revision(args.video, kind_of(role)), args.status, args.reason or "")
    print(f"{role}: {args.status}")


def main_frames(args):
    """Prepare a cut's frame-review bundle, or import its result. The bundle carries the cut's own
    revision, so an older cut can be reviewed; under the frames kind's freshness policy its result
    is then recorded as stale, and the receipt stays short of the current revision `require` asks for."""
    video = Path(args.video).resolve()
    from . import cuts
    n = args.cut or cuts.latest(video, cuts.RENDERED)
    cut = video / "cuts" / f"cut{n}"
    if not (cut / "cut.json").exists():
        raise SystemExit("make a cut before preparing its frame review")
    rec = json.loads((cut / "cut.json").read_text())
    kind = KINDS["frames"]
    judged, current = rec.get("source_revision"), revision(video, kind)
    if not judged:
        raise SystemExit(f"cut {n} predates review fingerprints; make a fresh cut")
    stale = judged != current
    if stale and kind.freshness == "refuse":
        raise SystemExit(f"cut {n} does not match current sources; make a fresh cut")
    changed = changed_since(video, n) if stale else None
    bundle = video / "research" / "frame_review" / f"cut{n}-{judged[:12]}"
    manifest = bundle / "manifest.json"
    if args.result:
        if not manifest.exists():
            raise SystemExit("prepare the review bundle before importing a result")
        judged = json.loads(manifest.read_text())["revision"]
        text = Path(args.result).read_text()
        if not any(line.strip() == f"REVISION: {judged}" for line in text.splitlines()):
            raise SystemExit("frame review must include the exact REVISION from its manifest")
        status, _ = kind.verdict(text)
        (bundle / "result.md").write_text(text)
        record(video, "frames", judged, status, str(bundle / "result.md"), cut=n, stale=stale, changed=changed)
        print(f"frames: {status}" + (f", recorded as stale: {changed} changed since cut {n}" if stale else "") +
              f"; {bundle / 'result.md'}")
        return 0 if status == "passed" and not stale else 1
    bundle.mkdir(parents=True, exist_ok=True)
    # the sheets are made from the current sources, so an older cut's bundle goes without them
    for src, target in ((cut / "stills", "stills"), (None if stale else video / "out/sheets", "sheets"), (video / "data", "data")):
        if src and src.exists():
            shutil.copytree(src, bundle / target, dirs_exist_ok=True)
    shutil.copyfile(cut / "SCRIPT.md" if (cut / "SCRIPT.md").exists() else video / "SCRIPT.md", bundle / "SCRIPT.md")
    # Strip conclusions and build history from the reviewer copy.
    from .script import sections
    parts = sections((bundle / "SCRIPT.md").read_text())
    (bundle / "SCRIPT.md").write_text(parts.get("Script", "") + "\n" + parts.get("Evidence", ""))
    (bundle / "prompt.md").write_text((ROOT / "prompts/frame_review.md").read_text() +
                                     f"\nInclude this exact line in your result: REVISION: {judged}\n")
    atomic_json(manifest, {"cut": n, "revision": judged, "script": "SCRIPT.md", "stills": "stills/",
                          "crops": "sheets/", "data": "data/", "prompt": "prompt.md"})
    if stale:
        print(f"cut {n} is older than the sources ({changed} changed since); its review will be recorded as stale, "
              "and publish needs a review of a fresh cut")
    print(f"ready for frame review: {manifest}\nMain session: give this bundle to a fresh image-capable reviewer; "
          "import the response with --result FILE. This command does not run a reviewer.")
