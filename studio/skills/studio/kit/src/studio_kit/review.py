"""`studio review VIDEO ROUND`: one round of three fresh-context reviewers, on SCRIPT.md or on a
narrative (the outline that comes before any script).

Each reviewer is a separate `claude -p` process started in an empty folder to reduce accidental exposure to the
video's other files (earlier reviews, drafts, the review log), and it sees only its own material:
  expert:  the script with screen notes, and the evidence table
  student: the learner model (who they play) and the script with screen notes
  editor:  the argument and chain, and the script with screen notes
All three also get the charter the learner decided (the narrative's "Cut on purpose" and the
video's vocabulary), so a finding that reopens it can be declined on sight.

Guards, from earlier builds: a round must be named on SCRIPT.md's status line (rounds once started
on half-applied revisions); rounds stop at video.json's max_rounds (one lock took 18 rounds); and a
reviewer that fails to run is retried once, then the round stops loudly, because a fallback that
is not isolated from the project reviews with knowledge a newcomer would not have.
"""
import json
import os
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import settings
from .env import ROOT
from .script import sections

PROMPTS = ROOT / "prompts" / "reviewers"
ROLES = ("expert", "student", "editor")
# Rounds are the slowest loop in a build (one search video spent six rounds reaching the gate), so
# the default is two rounds plus one more for an expert's blocking finding; "thorough" restores six.
DEFAULT_MAX_ROUNDS = {"thorough": 6, "default": 3, "economy": 2}


def video_config(video):
    return settings.load(video)


def learner_path(video):
    """video.json's "learner", else LEARNER_MD, else learner.md in STUDIO_HOME."""
    cfg = video_config(video)
    if cfg.get("learner"):
        p = Path(cfg["learner"]).expanduser()
        return p if p.is_absolute() else Path(video) / p
    if os.environ.get("LEARNER_MD"):
        return Path(os.environ["LEARNER_MD"])
    return studio_home() / "learner.md"


def studio_home():
    return Path(os.environ.get("STUDIO_HOME", "~/studio")).expanduser()


def learner_brief(video):
    p = learner_path(video)
    if not p.exists():
        raise SystemExit(f"no learner model at {p}: write one from templates/learner.md, or set video.json's learner")
    s = sections(p.read_text())
    keep = [s[k] for k in ("Background", "Standing instructions for the student reviewer") if k in s]
    if not keep:
        raise SystemExit(f"{p} has no Background section")
    return "\n".join(keep).replace("## ", "")


def charter(video):
    """What the learner decided and reviewers must not reopen."""
    parts = []
    narrative = Path(video) / "research" / "narrative.md"
    if narrative.exists():
        s = sections(narrative.read_text())
        if "Vocabulary" in s:
            parts.append(s["Vocabulary"])
        if "Cut on purpose" in s:
            parts.append(s["Cut on purpose"].replace("## Cut on purpose", "Cut on purpose (decided with the learner):"))
    vocab = video_config(video).get("vocabulary")
    if vocab:
        vp = Path(vocab).expanduser()
        vp = vp if vp.is_absolute() else Path(video) / vp
        parts.append("Vocabulary (the canonical terms; any other term for these concepts is a finding):\n" + vp.read_text())
    if not parts:
        return ""
    return ("\n\nThe learner already decided the following. Do not ask for what it cuts, and do not ask for more "
            "explanation unless the chain breaks without it.\n\n" + "\n\n".join(parts))


def prompt(video, name):
    text = (PROMPTS / name).read_text()
    return text.replace("{{LEARNER}}", learner_brief(video)) if "{{LEARNER}}" in text else text


def script_inputs(video, rnd):
    text = (Path(video) / "SCRIPT.md").read_text()
    # A round reviews the revision made for it: the status line must name this round.
    if f"review round {rnd}" not in text.split("\n## ", 1)[0]:
        raise SystemExit(f"SCRIPT.md's status line does not say 'before review round {rnd}'; revise it first")
    s = sections(text)
    for need in ("Script", "Evidence", "Argument", "Chain"):
        if need not in s:
            raise SystemExit(f"SCRIPT.md has no '## {need}' section")
    script, evidence, argument = s["Script"], s["Evidence"], s["Argument"] + "\n" + s["Chain"]
    extra = charter(video)
    questions = re.search(r"^- \*\*Transfer questions[.:]?\*\*.*(?:\n(?!- \*\*|## ).+)*", s["Argument"], re.M)
    transfer = "\n\nTransfer cases (use only the model taught):\n" + questions.group() if questions else ""
    out = {
        "expert": prompt(video, "expert.md") + extra + "\n\n---\n\n" + script + "\n" + evidence,
        "student": prompt(video, "student.md") + extra + "\n\n---\n\n" + script + transfer,
        "editor": prompt(video, "editor.md") + extra + "\n\n---\n\n" + argument + "\n" + script,
    }
    # Each reviewer sees only its own material.
    for name, body in out.items():
        material = body.split("\n\n---\n\n", 1)[1]
        assert "## Review log" not in material and "## Ledgers" not in material, name
        assert "VERDICT" not in material, name
        assert "## Script" in material and "### 1." in material, name
    assert "## Evidence" in out["expert"]
    assert "## Evidence" not in out["student"] and "## Argument" not in out["student"]
    assert "## Evidence" not in out["editor"] and "## Argument" in out["editor"]
    return out


def narrative_inputs(video, narrative):
    text = Path(narrative).read_text()
    # The learner's corrections are logged under "## Decisions": reviewers judge the narrative,
    # not the conversation that shaped it.
    body = re.split(r"^## (Decisions|Review log)\b", text, flags=re.M)[0]
    if "VERDICT" in body:
        raise SystemExit("the narrative file contains review output")
    return {name: prompt(video, f"narrative_{name}.md") + "\n\n---\n\n" + body for name in ROLES}


def run_reviewer(text, runner=None):
    """One reviewer in an empty folder; retried once. Returns its output or raises."""
    runner = runner or (lambda t, cwd: subprocess.run(["claude", "-p"], input=t, capture_output=True, text=True,
                                                      timeout=1800, cwd=cwd))
    last = None
    for _ in range(2):
        with tempfile.TemporaryDirectory() as empty:
            r = runner(text, empty)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout
        last = (r.stderr or "").strip()[-500:] or f"exit {r.returncode}, no output"
    raise RuntimeError(f"an isolated reviewer failed twice: {last}\n"
                       "Do not fall back to a reviewer that can read the project. Record "
                       "'reviewers not isolated from round N' in the Review log if you must continue another way.")


def main(args, runner=None):
    video = Path(args.video).resolve()
    cfg = video_config(video)
    pace = "thorough" if cfg.get("thorough") else "economy" if cfg.get("economy") else "default"
    cap = cfg.get("max_rounds", DEFAULT_MAX_ROUNDS[pace])
    if not args.narrative and args.round > cap:
        raise SystemExit(f"round {args.round} is past max_rounds ({cap}): lock the script with every open finding "
                         "logged, or ask the learner to raise the cap")
    out_dir = video / "research" / "reviews"
    out_dir.mkdir(parents=True, exist_ok=True)
    narrative = Path(args.narrative).resolve() if args.narrative else None
    inputs = narrative_inputs(video, narrative) if narrative else script_inputs(video, args.round)
    tag = f"narrative_{narrative.stem}_round{args.round:02d}" if narrative else f"round{args.round:02d}"
    unknown = set(args.only.split(",")) - set(ROLES)
    if unknown:
        raise SystemExit("unknown reviewer roles: " + ", ".join(sorted(unknown)))
    from . import review_state
    revision = review_state.fingerprint(video)
    todo = [(k, v) for k, v in inputs.items() if k in args.only.split(",")]
    for name, text in todo:
        (out_dir / f"{tag}_{name}.input.md").write_text(text)

    def one(item):
        name, text = item
        try:
            body = run_reviewer(text, runner)
        except Exception as e:
            if not narrative:
                review_state.record(video, name, revision, "unavailable", str(e))
            raise
        (out_dir / f"{tag}_{name}.md").write_text(body)
        verdict = [line for line in body.splitlines() if "VERDICT" in line]
        if not narrative:
            status = "passed" if verdict and verdict[-1].strip() == "VERDICT: PASS" else "findings"
            review_state.record(video, name, revision, status, str(out_dir / f"{tag}_{name}.md"))
        return name, verdict[-1].strip() if verdict else "(no verdict line)", len(body)

    with ThreadPoolExecutor(max_workers=3) as ex:
        for name, verdict, n in ex.map(one, todo):
            print(f"{name:8s} {verdict}  ({n} chars)")
    return 0
