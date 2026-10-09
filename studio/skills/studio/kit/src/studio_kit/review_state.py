"""Review receipts identify the exact material judged, without exposing earlier findings.

research/reviews/<role>.json: {role, kind, revision, status, detail, created}, with the round of a
script review and whether a frame review's result was for an older revision (stale). What each kind
hashes, how its verdict reads and when its results are refused are its policies in reviews.py.
"""
import hashlib
import json
import shutil
from pathlib import Path

from . import reviews
from .env import ROOT
from .reviews import KINDS, kind_of
from .workspace import atomic_json, now


def fingerprint(video, frames=False):
    """The revision a review judged, so its receipt goes stale exactly when that material changes.

    A script review reads the learner, the charter and SCRIPT.md's teaching sections. A frame review
    reads its bundle: SCRIPT.md's Script and Evidence, data/, and the cut's frames, for which each
    clip's review key stands (its scene code, narration, captions, the cues it reads, layout, data
    and assets). timeline.json and narration.json are not hashed: they also change for what no
    frame shows (the timeline's sources, its audio and effects; the voice), and every part of them a
    frame shows is in some clip's key.
    """
    video = Path(video)
    from .script import sections
    script = video / "SCRIPT.md"
    parts = sections(script.read_text()) if script.exists() else None
    h = hashlib.sha256()
    if frames:
        if parts is not None:
            h.update("\n".join(parts.get(k, "") for k in ("Script", "Evidence")).encode())
        for p in sorted((video / "data").rglob("*")):
            if p.is_file():
                h.update(str(p.relative_to(video)).encode())
                h.update(p.read_bytes())
        if (video / "timeline.json").exists():
            from . import render, timeline
            t = timeline.load(video)
            for scene in t["tracks"]["scene"]:
                h.update(render.clip_key(video, t, scene["id"], "review").encode())
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


def record(video, role, revision, status, detail="", round=None, stale=None):
    """Write a receipt; `round` and `stale` only where the kind has them."""
    rec = {"role": role, "kind": kind_of(role).name, "revision": revision, "status": status, "detail": detail, "created": now()}
    rec |= {k: v for k, v in (("round", round), ("stale", stale)) if v is not None}
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


def require(video, role):
    kind = kind_of(role)
    rec = read(video, role)
    if rec.get("revision") != revision(video, kind) or rec.get("status") not in ("passed", "waived"):
        raise SystemExit(f"current {role} review missing, stale or unresolved; {kind.remedy.format(role=role)}"
                         "; an authorized waiver can be recorded with studio review-status")


def main_status(args):
    role = reviews.role(args.role)
    if args.status == "waived" and not args.reason:
        raise SystemExit("record the user's authorization in --reason for a waived review")
    record(args.video, role, revision(args.video, kind_of(role)), args.status, args.reason or "")
    print(f"{role}: {args.status}")


def main_frames(args):
    from . import render
    video = Path(args.video).resolve()
    from . import cuts
    n = args.cut or cuts.latest(video, cuts.RENDERED)
    cut = video / "cuts" / f"cut{n}"
    if not (cut / "cut.json").exists():
        raise SystemExit("make a cut before preparing its frame review")
    rec = json.loads((cut / "cut.json").read_text())
    kind = KINDS["frames"]
    current = revision(video, kind)
    stale = rec.get("source_revision") != current
    if stale and (not args.result or kind.freshness == "refuse"):
        raise SystemExit("cut does not match current sources (or predates review fingerprints); make a fresh cut")
    bundle = video / "research" / "frame_review" / f"cut{n}-{current[:12]}"
    manifest = bundle / "manifest.json"
    if args.result:
        if not manifest.exists():
            raise SystemExit("prepare the review bundle before importing a result")
        text = Path(args.result).read_text()
        if not any(line.strip() == f"REVISION: {current}" for line in text.splitlines()):
            raise SystemExit("frame review must include the exact REVISION from its manifest")
        status, _ = kind.verdict(text)
        (bundle / "result.md").write_text(text)
        record(video, "frames", current, status, str(bundle / "result.md"), stale=stale)
        print(f"frames: {status}; {bundle / 'result.md'}")
        return 0 if status == "passed" else 1
    bundle.mkdir(parents=True, exist_ok=True)
    for src, target in ((cut / "stills", "stills"), (video / "out/sheets", "sheets"), (video / "data", "data")):
        if src.exists():
            shutil.copytree(src, bundle / target, dirs_exist_ok=True)
    shutil.copyfile(video / "SCRIPT.md", bundle / "SCRIPT.md")
    # Strip conclusions and build history from the reviewer copy.
    from .script import sections
    parts = sections((bundle / "SCRIPT.md").read_text())
    (bundle / "SCRIPT.md").write_text(parts.get("Script", "") + "\n" + parts.get("Evidence", ""))
    (bundle / "prompt.md").write_text((ROOT / "prompts/frame_review.md").read_text() +
                                     f"\nInclude this exact line in your result: REVISION: {current}\n")
    atomic_json(manifest, {"cut": n, "revision": current, "script": "SCRIPT.md", "stills": "stills/",
                          "crops": "sheets/", "data": "data/", "prompt": "prompt.md"})
    print(f"ready for frame review: {manifest}\nMain session: give this bundle to a fresh image-capable reviewer; "
          "import the response with --result FILE. This command does not run a reviewer.")
