"""Review receipts identify the exact material judged, without exposing earlier findings."""
import hashlib
import json
import shutil
from pathlib import Path

from .env import ROOT
from .workspace import atomic_json, now


def fingerprint(video, frames=False):
    video = Path(video)
    files = [video / "SCRIPT.md"]
    if frames:
        files += [video / n for n in ("timeline.json", "layout.json", "narration.json")]
        files += [p for folder in ("scenes", "data", "assets") for p in (video / folder).rglob("*") if p.is_file()]
    from .review import learner_path, charter
    h = hashlib.sha256()
    audience = learner_path(video)
    if audience.exists():
        from .review import learner_brief
        h.update(learner_brief(video).encode())
    h.update(charter(video).encode())
    for p in sorted(files):
        if not p.exists():
            continue
        data = p.read_bytes()
        if p.name == "SCRIPT.md":
            from .script import sections
            parts = sections(data.decode())
            # Status and Review log updates must not stale a review; the reviewed teaching material does.
            data = "\n".join(parts.get(k, "") for k in ("Argument", "Chain", "Script", "Evidence")).encode()
        h.update(str(p.relative_to(video)).encode())
        h.update(data)
    if frames and (video / "timeline.json").exists():
        from . import render, timeline
        t = timeline.load(video)
        for scene in t["tracks"]["scene"]:
            h.update(render.clip_key(video, t, scene["id"], "review").encode())
    return h.hexdigest()


def record(video, role, revision, status, detail=""):
    atomic_json(Path(video) / "research" / "reviews" / f"{role}.json",
                {"role": role, "revision": revision, "status": status, "detail": detail, "created": now()})


def required_roles(cfg):
    """Drive and depth choose script reviewers; explicit claim risk may add roles."""
    if not cfg.get("teaching_contract"):
        return ()
    roles = ["student"]
    if cfg.get("drive") == "learner" or cfg.get("level") == "deep-dive":
        roles += ["expert", "editor"]
    for role in cfg.get("review_roles", []):
        if role not in ("student", "expert", "editor"):
            raise SystemExit(f"unknown script review role: {role}")
        if role not in roles:
            roles.append(role)
    return tuple(roles)


def require(video, role, frames=False):
    p = Path(video) / "research" / "reviews" / f"{role}.json"
    rec = json.loads(p.read_text()) if p.exists() else {}
    if rec.get("revision") != fingerprint(video, frames) or rec.get("status") not in ("passed", "waived"):
        raise SystemExit(f"current {role} review missing, stale or unresolved; "
                         + ("run studio review-frames and return its findings" if frames else f"run studio review VIDEO ROUND --only {role}")
                         + "; an authorized waiver can be recorded with studio review-status")


def main_status(args):
    if args.status == "waived" and not args.reason:
        raise SystemExit("record the user's authorization in --reason for a waived review")
    if args.status == "passed":
        raise SystemExit("passed results are recorded by studio review or review-frames --result")
    record(args.video, args.role, fingerprint(args.video, args.role == "frames"), args.status, args.reason or "")
    print(f"{args.role}: {args.status}")


def main_frames(args):
    from . import render
    video = Path(args.video).resolve()
    from . import cuts
    n = args.cut or cuts.latest(video, cuts.RENDERED)
    cut = video / "cuts" / f"cut{n}"
    if not (cut / "cut.json").exists():
        raise SystemExit("make a cut before preparing its frame review")
    rec = json.loads((cut / "cut.json").read_text())
    revision = fingerprint(video, frames=True)
    if rec.get("source_revision") != revision:
        raise SystemExit("cut does not match current sources (or predates review fingerprints); make a fresh cut")
    bundle = video / "research" / "frame_review" / f"cut{n}-{revision[:12]}"
    manifest = bundle / "manifest.json"
    if args.result:
        if not manifest.exists():
            raise SystemExit("prepare the review bundle before importing a result")
        text = Path(args.result).read_text()
        if not any(line.strip() == f"REVISION: {revision}" for line in text.splitlines()):
            raise SystemExit("frame review must include the exact REVISION from its manifest")
        verdicts = [line.strip() for line in text.splitlines() if line.strip().startswith("FRAMES:")]
        status = "passed" if verdicts and verdicts[-1] == "FRAMES: PASS" else "findings"
        (bundle / "result.md").write_text(text)
        record(video, "frames", revision, status, str(bundle / "result.md"))
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
                                     f"\nInclude this exact line in your result: REVISION: {revision}\n")
    atomic_json(manifest, {"cut": n, "revision": revision, "script": "SCRIPT.md", "stills": "stills/",
                          "crops": "sheets/", "data": "data/", "prompt": "prompt.md"})
    print(f"ready for frame review: {manifest}\nMain session: give this bundle to a fresh image-capable reviewer; "
          "import the response with --result FILE. This command does not run a reviewer.")
