"""Run one review round with three fresh-context reviewers: on a lesson's SCRIPT.md, or on a
narrative (the outline that comes before any script).

    python kit/review.py LESSON_DIR ROUND [--only expert,student,editor]
    python kit/review.py LESSON_DIR ROUND --narrative PATH/TO/NARRATIVE.md

Each reviewer is a separate `claude -p` process (a fresh context), started in an empty folder so it
cannot read the lesson's other files (earlier reviews, drafts, the review log), and it sees only its
own material:
  expert:  the script with screen notes, and the evidence table
  student: the learner model (who they are playing) and the script with screen notes
  editor:  the argument and chain, and the script with screen notes
A narrative round gives all three the narrative file, and the student the learner model too.
Script inputs are cut from SCRIPT.md by section and checked before anything runs. Reviews go to
research/reviews/roundNN_<role>.md (narratives: narrative_<name>_roundNN_<role>.md), and each
one's verdict line is printed.
"""
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

KIT = Path(__file__).resolve().parent
LESSON = Path(sys.argv[1]).resolve()
ROUND = int(sys.argv[2])
ONLY = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else ["expert", "student", "editor"]
NARRATIVE = Path(sys.argv[sys.argv.index("--narrative") + 1]).resolve() if "--narrative" in sys.argv else None
OUT = LESSON / "research" / "reviews"


def sections(text):
    parts = re.split(r"^## ", text, flags=re.M)
    return {p.split("\n", 1)[0].strip(): "## " + p for p in parts[1:]}


def learner_brief():
    # learner.md sits next to the kit folder (PROJECT/tutor/learner.md); LEARNER_MD overrides.
    t = Path(os.environ.get("LEARNER_MD", KIT.parent / "learner.md")).read_text()
    s = sections(t)
    keep = [s[k] for k in ("Background", "Standing instructions for the student reviewer") if k in s]
    assert keep, "learner.md is missing its Background section"
    return "\n".join(keep).replace("## ", "")


def prompt(name):
    p = (KIT / "reviewers" / name).read_text()
    return p.replace("{{LEARNER}}", learner_brief())


def script_inputs():
    text = (LESSON / "SCRIPT.md").read_text()
    # A round reviews the revision made for it: the status line must name this round.
    assert f"review round {ROUND}" in text.split("\n## ", 1)[0], \
        f"SCRIPT.md status does not say 'before review round {ROUND}'; revise it first"
    s = sections(text)
    script, evidence = s["Script"], s["Evidence"]
    argument = s["Argument"] + "\n" + s["Chain"]
    out = {
        "expert": prompt("expert.md") + "\n\n---\n\n" + script + "\n" + evidence,
        "student": prompt("student.md") + "\n\n---\n\n" + script,
        "editor": prompt("editor.md") + "\n\n---\n\n" + argument + "\n" + script,
    }
    # Each reviewer sees only its own material.
    for name, text in out.items():
        assert "## Review log" not in text and "## Ledgers" not in text, name
        assert "VERDICT" not in text.split("---", 1)[1], name
        assert "## Script" in text and "### 1." in text, name
    assert "## Evidence" in out["expert"] and "| Claim |" in out["expert"]
    assert "## Evidence" not in out["student"] and "## Argument" not in out["student"]
    assert "## Evidence" not in out["editor"] and "## Argument" in out["editor"]
    return out


def narrative_inputs():
    text = NARRATIVE.read_text()
    # The co-author track logs the learner's corrections under "## Decisions": reviewers judge the
    # narrative, not the conversation that shaped it.
    body = re.split(r"^## (Decisions|Review log)\b", text, flags=re.M)[0]
    assert "VERDICT" not in body, "the narrative file contains review output"
    return {name: prompt(f"narrative_{name}.md") + "\n\n---\n\n" + body for name in ("expert", "student", "editor")}


def run(item):
    name, text = item
    tag = f"narrative_{NARRATIVE.stem}_round{ROUND:02d}" if NARRATIVE else f"round{ROUND:02d}"
    path = OUT / f"{tag}_{name}.md"
    with tempfile.TemporaryDirectory() as empty:
        r = subprocess.run(["claude", "-p"], input=text, capture_output=True, text=True, timeout=1800, cwd=empty)
    path.write_text(r.stdout)
    verdict = [l for l in r.stdout.splitlines() if "VERDICT" in l]
    return name, verdict[-1].strip() if verdict else "(no verdict line)", len(r.stdout)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    inputs = narrative_inputs() if NARRATIVE else script_inputs()
    todo = [(k, v) for k, v in inputs.items() if k in ONLY]
    tag = f"narrative_{NARRATIVE.stem}_round{ROUND:02d}" if NARRATIVE else f"round{ROUND:02d}"
    for name, text in todo:
        (OUT / f"{tag}_{name}.input.md").write_text(text)
    with ThreadPoolExecutor(max_workers=3) as ex:
        for name, verdict, n in ex.map(run, todo):
            print(f"{name:8s} {verdict}  ({n} chars)")


if __name__ == "__main__":
    main()
