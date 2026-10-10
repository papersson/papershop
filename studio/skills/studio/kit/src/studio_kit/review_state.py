"""Review receipts identify the exact material judged, without exposing earlier findings.

research/reviews/<role>.json: {role, kind, revision, status, detail, created, t}, with the round of a
script or motion review, and for a frame or motion review the cut it judged and whether that cut was
older than the sources when the result came in (stale, with what had changed). What each kind
hashes, how its verdict reads, what an older revision's result does and what a settled receipt
stands for are its policies in reviews.py.
research/reviews/rounds.jsonl logs the revision each round reviewed, which the round cap counts.
"""
import hashlib
import json
import re
import shlex
import shutil
import time
from pathlib import Path

from . import reviews, settings
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
    if kind.scope == "sound":
        from . import audio
        return audio.revision(video)
    return fingerprint(video, frames=kind.scope == "frames")


def record(video, role, revision, status, detail="", **extra):
    """Write a receipt; `extra` (round, cut, stale, changed) only where the kind has them."""
    rec = {"role": role, "kind": kind_of(role).name, "revision": revision, "status": status, "detail": detail, "created": now(),
           "t": round(time.time(), 3)}
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


def cut_keys(video, cut=None):
    """The review keys cut N recorded, or (None) the current sources' ({} when there are none)."""
    if cut is not None:
        p = Path(video) / "cuts" / f"cut{cut}" / "cut.json"
        return (json.loads(p.read_text()).get("review_keys") or {}) if p.exists() else {}
    if not (Path(video) / "timeline.json").exists():
        return {}
    from . import timeline
    return review_keys(video, timeline.load(video))


def substantial(then, now):
    """How the picture changed from review keys `then` to `now`, when it changed enough to be a new
    lineage for a motion review (a clip that is new, or half the clips or more changed), else None."""
    new = [c for c in now if c not in then]
    changed = [c for c in now if c in then and then[c] != now[c]]
    if not now or not (new or 2 * len(changed) >= len(now)):
        return None
    return "; ".join(x for x in (f"{', '.join(new)} new" if new else "",
                                 f"{', '.join(changed)} changed ({len(changed)} of {len(now)} clips)" if changed else "") if x)


def cut_time(video, n):
    """When cut N was made, in epoch seconds: its record's "t", else its local "created" (to the
    second, for a cut made before records had "t"), else its file's time."""
    p = Path(video) / "cuts" / f"cut{n}" / "cut.json"
    try:
        rec = json.loads(p.read_text())
        return float(rec["t"]) if "t" in rec else time.mktime(time.strptime(rec["created"], "%Y-%m-%d %H:%M:%S"))
    except (OSError, ValueError, KeyError, TypeError):
        return p.stat().st_mtime if p.exists() else 0.0


def rounds(video, kind, revision=None, cut=None):
    """The units of a kind's material reviewed since the latest stage mark that starts its count
    again (kind.rounds.resets_on), and that mark (None: there is none, so every round counts). A
    unit is a revision (a script review: reviewers run again on a revision already reviewed are the
    same round), or what a round logged as its unit (a motion review: the cut's bundle, so a re-cut
    of an unchanged revision is a round of its own).
    A mark starts the count only when the material changed across it, so a mark alone buys no
    rounds. For a revision kind, the material it was made over (its "revisions", or for an older
    mark the first revision reviewed after it, or `revision`, about to be) is not the last revision
    reviewed before it. For a lineage kind, the picture changed substantially (substantial()) from
    the last cut reviewed before the mark to the first reviewed after it (or `cut`, about to be, or
    the current sources)."""
    from . import stage
    log, since = _logged(video, kind), None
    for m in stage.read(video):
        if m.get("kind") not in kind.rounds.resets_on:
            continue
        prior = [e for e in log if e["t"] < m["t"]]
        after = next((e for e in log if e["t"] >= m["t"]), None)
        if not prior:
            since = m
        elif kind.stands == "lineage":
            if substantial(cut_keys(video, prior[-1].get("cut")), cut_keys(video, after.get("cut") if after else cut)):
                since = m
        elif (m.get("revisions", {}).get(kind.name) or (after["revision"] if after else revision)) != prior[-1]["revision"]:
            since = m
    seen = []
    for e in log:
        unit = e.get("unit") or e["revision"]
        if (since is None or e["t"] >= since["t"]) and unit not in seen:
            seen.append(unit)
    return seen, since


def next_round(video, kind, revision, unit=None, cut=None):
    """The round a review of `unit` (default: `revision`) is in its count: the one that reviewed it
    already, or the next."""
    unit = unit or revision
    seen, _ = rounds(video, kind, revision, cut)
    return seen.index(unit) + 1 if unit in seen else len(seen) + 1


def quoted(video):
    """The video's path as a command line takes it, for a message's commands."""
    return shlex.quote(str(Path(video).resolve()))


def check_cap(video, kind, number, revision, cfg, unit=None, cut=None):
    """Refuse a new round of `kind` past its cap (counted as rounds() counts, so a typed round number
    neither spends nor saves one), with the kind's own reason and way forward."""
    cap = kind.rounds.cap(cfg) if kind.rounds.cap else None
    seen, since = rounds(video, kind, revision, cut)
    if cap is not None and (unit or revision) not in seen and len(seen) >= cap:
        fill = {"number": number, "cap": cap, "count": len(seen), "video": quoted(video),
                "where": f"its {since['stage']} mark ({since['at']})" if since else "the first round"}
        past = kind.rounds.past_cap
        raise SystemExit(past(**fill, last=read(video, kind.roles[0])) if callable(past) else past.format(**fill))


def start_round(video, kind, number, revision, cfg, unit=None, cut=None):
    """Log a round of `kind` on `revision` (as `unit`, of cut `cut`, where the kind counts those),
    unless it is a new round past the kind's cap."""
    check_cap(video, kind, number, revision, cfg, unit, cut)
    log = rounds_log(video)
    log.parent.mkdir(parents=True, exist_ok=True)
    text = log.read_text() if log.exists() else ""
    torn = bool(text) and not text.endswith("\n")      # a line cut short must not swallow this one
    with log.open("a") as f:
        f.write("\n" * torn + json.dumps({"kind": kind.name, "round": number, "revision": revision, "t": time.time(),
                                           **({"unit": unit} if unit else {}), **({"cut": cut} if cut is not None else {})}) + "\n")


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


def what_changed(video, rec, kind):
    """What changed since a receipt was recorded, in a few words, as far as it can tell: the clips
    since the cut it judged, or since the waiver that recorded the review keys; else the material
    its kind hashes."""
    if rec.get("cut") is not None:
        return changed_since(video, rec["cut"])
    if kind.scope == "frames" and rec.get("review_keys") and (Path(video) / "timeline.json").exists():
        from . import timeline
        then, current = rec["review_keys"], review_keys(video, timeline.load(video))
        clips = [c for c in {**then, **current} if then.get(c) != current.get(c)]
        return ", ".join(clips) if clips else "SCRIPT.md's Script or Evidence, or data/"
    return {"script": "the learner, the charter or SCRIPT.md's teaching sections", "sound": "the mix",
            "frames": "what the frames show (the receipt names no cut, so not which clips)"}[kind.scope]


def unsettled(video, role, kind, rec, current):
    """Why a receipt does not settle the gate: missing, stale (with what changed) or unresolved."""
    if not rec:
        return f"no {role} review is recorded"
    of = f" of cut {rec['cut']}" if rec.get("cut") is not None else ""
    if rec.get("revision") != current:
        return f"the {role} review{of} ({rec.get('status')}) is stale: {what_changed(video, rec, kind)} changed since it was recorded"
    return f"the {role} review{of} is unresolved: its status is {rec.get('status')}, and the gate takes {' or '.join(kind.settled)}"


def lineage_gone(video, rec, kind, current):
    """Why a lineage receipt no longer stands, or None while it does: a stage mark that restarted the
    kind's count came after the cut it judged was made, or the picture changed substantially since
    that cut (a new clip, or half the clips or more). A motion review stops by its rule, so later
    small edits (frame-review fixes, desk notes) don't ask for another round; the frame review and
    the user judge those."""
    _, since = rounds(video, kind, current)
    made = rec.get("cut_t", rec.get("t", 0))
    if since is not None and made < since["t"]:
        return f"cut {rec.get('cut', '?')} came before the {since['stage']} mark ({since['at']}) that started a new count"
    if rec.get("cut") is None:
        return None
    change = substantial(cut_keys(video, rec["cut"]), cut_keys(video))
    return f"since cut {rec['cut']}, {change}" if change else None


def stands(video, rec, kind, current):
    """Whether a receipt stands for the current material: it judged the current revision, or, for a
    kind that stands for its lineage, the lineage it judged goes on (lineage_gone)."""
    if not rec:
        return False
    if kind.stands != "lineage":
        return rec.get("revision") == current
    return lineage_gone(video, rec, kind, current) is None


def require(video, role):
    kind = kind_of(role)
    rec, current = read(video, role), revision(video, kind)
    if rec.get("status") in kind.settled and stands(video, rec, kind, current):
        return
    v = quoted(video)
    if kind.name == "motion" and not rec and settings.load(video).get("teaching_contract"):
        raise SystemExit("publish now needs a motion review for an explainer (new in this kit: Stage 11, Polish, in "
                         f"references/explainer.md): run studio review-motion {v} and have the main session's reviewer "
                         "judge it; for a video made before this requirement, with the user's agreement, record "
                         f"studio review-status {v} motion waived --reason \"…\"")
    gone = rec and kind.stands == "lineage" and lineage_gone(video, rec, kind, current)
    if gone:
        raise SystemExit(f"the {role} review no longer stands: {gone}. Mark a structural revision (studio stage {v} "
                         "revision --kind structural --summary …), which starts a new count, make a fresh cut and "
                         f"{kind.remedy.format(role=role, video=v)}; or record an authorized waiver with studio review-status")
    if kind.name == "motion" and rec.get("stopped") == "cap":
        raise SystemExit(f"the motion review of cut {rec.get('cut')} stopped at its cap with must-fix findings open "
                         f"({rec.get('detail') or 'no detail'}): fix them and record the user's acceptance with studio review-status "
                         f"{v} motion waived --reason …, or, if the user asks, raise video.json motion_rounds")
    if kind.freshness == "record-stale" and rec.get("cut") is not None and rec.get("revision") != current:
        raise SystemExit(f"the {role} review judged cut {rec['cut']}, and {changed_since(video, rec['cut'])} changed since: "
                         f"make a fresh cut and {kind.remedy.format(role=role, video=v)}, or record an authorized waiver with "
                         "studio review-status")
    raise SystemExit(f"{unsettled(video, role, kind, rec, current)}; {kind.remedy.format(role=role, video=v)}"
                     f"; an authorized waiver can be recorded with studio review-status {v} {role} waived --reason …")


def main_status(args):
    role = reviews.role(args.role)
    if args.status == "waived" and not args.reason:
        raise SystemExit("record the user's authorization in --reason for a waived review")
    kind = kind_of(role)
    if args.status not in kind.records:
        raise SystemExit(f"{role}: review-status records {' or '.join(kind.records)}"
                         + ("; a reviewer's pass comes from its own review" if args.status == "passed" else ""))
    at = getattr(args, "at", None)
    if at and kind.name != "listen":
        raise SystemExit("--at names the timecodes of a listening: review-status VIDEO listen passed --at …")
    extra = motion_waiver(args.video, args.reason or "") if kind.name == "motion" else {}
    if kind.name == "listen":
        extra |= listened(args.video, at)
    if kind.scope == "frames" and (Path(args.video) / "timeline.json").exists():
        from . import timeline      # what the frames showed, so a stale receipt can say which clips changed
        extra["review_keys"] = review_keys(args.video, timeline.load(args.video))
    record(args.video, role, revision(args.video, kind), args.status, args.reason or "", **extra)
    print(f"{role}: {args.status}" + (f" (cut {extra['cut']}, its {extra['accepted']} known issue(s) accepted)"
                                       if extra.get("accepted") else "")
          + (f", at {', '.join(m['at'] for m in extra['timecodes'])}" if extra.get("timecodes") else ""))


def _seconds(text):
    """Seconds from a timecode as the listening shows it (m:ss.s) or as seconds."""
    m, _, sec = text.strip().rpartition(":")
    try:
        return (int(m) * 60 if m else 0) + float(sec)
    except ValueError:
        raise SystemExit(f"--at: {text.strip()!r} is not a timecode (m:ss.s, or seconds)") from None


def listened(video, at=None):
    """What a listening receipt records beyond its reason: {timecodes: [{t, at, reasons}]}, the moments
    listened at. `at`, comma-separated timecodes, names them (each takes its reasons from the moment
    audio-check chose within half a second of it, if any); without it, the moments audio-check chose
    for this mix (audio_check.moments), which the listening step asked for. None when there are none:
    a listening with no timecodes is still recorded."""
    from .audio_check import moments, timecode
    offered = moments(video) or []
    if not at:
        return {"timecodes": offered or None}
    out = []
    for part in filter(str.strip, at.split(",")):
        t = _seconds(part)
        m = min(offered, key=lambda m: abs(m["t"] - t), default=None)
        out.append(m if m and abs(m["t"] - t) <= 0.5 else {"t": round(t, 2), "at": timecode(t), "reasons": []})
    return {"timecodes": out or None}


def listening(video, timeline):
    """Why the user's listening check is due, or None: a soundtrack with effects or music and no
    listening recorded for this mix. A narration alone does not need one. Where to listen is
    audio_check.listen_hint's."""
    from . import timeline as tl
    if not {tl.audio_role(e) for e in timeline["tracks"]["audio"]} & {"sfx", "music"}:
        return None
    from .audio import MixUnavailable
    kind, rec = KINDS["listen"], read(video, "listen")
    try:
        current = revision(video, kind)
    except MixUnavailable as e:     # a handoff or publish asking about the sound must not die on it
        return f"the mix can't be built: {e}"
    if rec.get("status") in kind.settled and stands(video, rec, kind, current):
        return None
    return "nobody has listened to this mix" + (f" (the {rec['status']} listening was of an earlier one)" if rec else "")


def motion_waiver(video, reason):
    """What a motion waiver records beyond its reason: the mode, the latest rendered cut (whose
    lineage it stands for), the desk notes it cites by id, and how many known issues it accepts.
    The user's desk notes can stand in for the review, named by their ids."""
    from . import cuts, page
    mode = settings.load(video)["mode"]
    ids = {e["id"] for e in page.read_log(video) if e.get("type") == "note"}
    notes = sorted(i for i in ids if re.search(rf"\b{re.escape(i)}\b", reason))
    if re.search(r"\bdesk\b|\bnotes?\b", reason, re.I) and not notes:
        raise SystemExit("name the desk notes that stand in for the motion review by their ids in --reason "
                         f"(studio notes {quoted(video)} lists them)")
    n = cuts.latest(video, cuts.RENDERED)
    issues = (cuts.records(video).get(n) or {}).get("known_issues") or []
    return {"mode": mode, "notes": notes or None, "cut": n or None, "cut_t": cut_time(video, n) if n else None,
            "accepted": len(issues) or None}


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
    # The sheets and data/ are the current sources'; a cut keeps only its stills and script, so an
    # older cut's bundle goes without them rather than pair its frames with other numbers.
    for src, target in ((cut / "stills", "stills"), (video / "out/sheets", "sheets"), (video / "data", "data")):
        if src.exists() and (target == "stills" or not stale):
            shutil.copytree(src, bundle / target, dirs_exist_ok=True)
    # What each still is, in time order: a sentence's end, an event or a pause (the ids alone don't say)
    atomic_json(bundle / "stills.json", [{"file": s["file"], "kind": s.get("kind", "sentence-end"), "time": s.get("time"),
                                          "label": s["caption"]} for s in rec.get("stills", [])])
    shutil.copyfile(cut / "SCRIPT.md" if (cut / "SCRIPT.md").exists() else video / "SCRIPT.md", bundle / "SCRIPT.md")
    # Strip conclusions and build history from the reviewer copy.
    from .script import sections
    parts = sections((bundle / "SCRIPT.md").read_text())
    (bundle / "SCRIPT.md").write_text(parts.get("Script", "") + "\n" + parts.get("Evidence", ""))
    (bundle / "prompt.md").write_text((ROOT / "prompts/frame_review.md").read_text() +
                                     f"\nInclude this exact line in your result: REVISION: {judged}\n")
    atomic_json(manifest, {"cut": n, "revision": judged, "script": "SCRIPT.md", "stills": "stills/", "stills_index": "stills.json",
                          "crops": None if stale else "sheets/", "data": None if stale else "data/", "prompt": "prompt.md"})
    if stale:
        print(f"cut {n} is older than the sources ({changed} changed since): its bundle has its stills and script but "
              "no crops or data, its review will be recorded as stale, and publish needs a review of a fresh cut")
    print(f"ready for frame review: {manifest}\nMain session: give this bundle to a fresh image-capable reviewer; "
          "import the response with --result FILE. This command does not run a reviewer.")
