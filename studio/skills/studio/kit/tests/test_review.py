import json
import re
import subprocess
from types import SimpleNamespace

import pytest

from studio_kit import review

SCRIPT = """# T

Status: revised, before review round 2

## Argument

- **Question.** Why charged twice?

## Chain

1. A retry can charge twice.

## Ledgers

- secret ledger

## Script

### 1. Opening

> A retry can charge twice.

*Screen:* a card.

## Evidence

| Claim | Source |
|---|---|
| charged twice | sims/retry.py |

## Review log

- round 1: VERDICT: REVISE
"""


def make(tmp_path, cfg=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "SCRIPT.md").write_text(SCRIPT)
    (tmp_path / "learner.md").write_text("# L\n\n## Background\n\nA backend developer.\n")
    (tmp_path / "video.json").write_text(json.dumps({"learner": "learner.md", **(cfg or {})}))
    (tmp_path / "research").mkdir()
    (tmp_path / "research" / "narrative.md").write_text("# N\n\n## Cut on purpose\n\n- the history of HTTP\n")
    return tmp_path


def test_each_reviewer_sees_only_its_material_plus_the_charter(tmp_path):
    inputs = review.script_inputs(make(tmp_path), 2)
    assert "## Evidence" in inputs["expert"] and "## Evidence" not in inputs["student"]
    assert "## Argument" in inputs["editor"] and "## Argument" not in inputs["expert"]
    assert all("secret ledger" not in v and "Review log" not in v.split("---", 1)[1] for v in inputs.values())
    assert all("the history of HTTP" in v for v in inputs.values())
    assert "A backend developer." in inputs["student"]


def test_a_round_must_be_named_on_the_status_line(tmp_path):
    with pytest.raises(SystemExit, match="review round 3"):
        review.script_inputs(make(tmp_path), 3)


def args(tmp_path, rnd):
    return SimpleNamespace(video=str(tmp_path), round=rnd, narrative=None, only="expert,student,editor")


def revise(video, rnd):
    """SCRIPT.md revised for round `rnd`: a new revision, named on the status line."""
    p = video / "SCRIPT.md"
    text = re.sub(r"review round \d+", f"review round {rnd}", p.read_text())
    p.write_text(re.sub(r"\*Screen:\* a card[^\n]*", f"*Screen:* a card, take {rnd}.", text))


def findings(text, cwd):
    return subprocess.CompletedProcess([], 0, "VERDICT: REVISE\n", "")


def test_rounds_count_per_script_revision_not_by_the_number_typed(tmp_path):
    """The cap compared the typed round number with max_rounds, so a structural rewrite inherited the
    earlier rounds and the cap was raised instead (3 to 17 in one build)."""
    from studio_kit import stage
    make(tmp_path, {"max_rounds": 2})
    review.main(args(tmp_path, 2), runner=findings)
    review.main(args(tmp_path, 2), runner=findings)            # the same revision again: a retry, not a round
    revise(tmp_path, 7)
    review.main(args(tmp_path, 7), runner=findings)            # a high number spends one round, like any other
    revise(tmp_path, 8)
    with pytest.raises(SystemExit, match=r"past max_rounds \(2\): this revision of the script has had 2 review rounds "
                                         r"since the first round.*--kind structural"):
        review.main(args(tmp_path, 8), runner=findings)
    assert not (tmp_path / "research" / "reviews" / "round08_student.md").exists()
    stage.mark(tmp_path, "revision", kind="local")
    with pytest.raises(SystemExit, match="past max_rounds"):
        review.main(args(tmp_path, 8), runner=findings)
    stage.mark(tmp_path, "revision", kind="structural")
    review.main(args(tmp_path, 8), runner=findings)            # a structural revision starts the count again
    revise(tmp_path, 9)
    review.main(args(tmp_path, 9), runner=findings)
    revise(tmp_path, 10)
    with pytest.raises(SystemExit, match=r"has had 2 review rounds since its revision mark"):
        review.main(args(tmp_path, 10), runner=findings)
    assert json.loads((tmp_path / "research" / "reviews" / "student.json").read_text())["round"] == 9


def test_a_failing_reviewer_is_retried_once_then_stops_loudly(tmp_path):
    calls = []

    def runner(text, cwd):
        calls.append(cwd)
        return subprocess.CompletedProcess([], 1, "", "sandbox error")

    with pytest.raises(RuntimeError, match="failed twice"):
        review.run_reviewer("x", runner)
    assert len(calls) == 2


def test_a_round_writes_reviews_and_verdicts(tmp_path, capsys):
    make(tmp_path)
    review.main(args(tmp_path, 2), runner=lambda t, cwd: subprocess.CompletedProcess([], 0, "ok\nVERDICT: PASS\n", ""))
    assert (tmp_path / "research" / "reviews" / "round02_expert.md").read_text().endswith("VERDICT: PASS\n")
    assert "VERDICT: PASS" in capsys.readouterr().out


def test_the_default_cap_is_three_rounds(tmp_path):
    make(tmp_path)
    for rnd in (2, 3, 4):
        revise(tmp_path, rnd)
        review.main(args(tmp_path, rnd), runner=findings)
    revise(tmp_path, 5)
    with pytest.raises(SystemExit, match=r"past max_rounds \(3\)"):
        review.main(args(tmp_path, 5), runner=findings)


def test_a_structural_mark_over_an_unchanged_script_starts_no_new_count(tmp_path):
    """One `studio stage --kind structural` with no change to the script reset the cap."""
    from studio_kit import stage
    make(tmp_path, {"max_rounds": 2})
    for rnd in (2, 3):
        revise(tmp_path, rnd)
        review.main(args(tmp_path, rnd), runner=findings)
    stage.mark(tmp_path, "revision", kind="structural")         # the script is the one round 3 reviewed
    revise(tmp_path, 4)
    with pytest.raises(SystemExit, match="a mark over an unchanged script does not"):
        review.main(args(tmp_path, 4), runner=findings)
    stage.mark(tmp_path, "revision", kind="structural")         # now over a revised script
    review.main(args(tmp_path, 4), runner=findings)


def test_an_unreadable_round_log_line_is_skipped_with_a_warning(tmp_path, capsys):
    make(tmp_path, {"max_rounds": 2})
    review.main(args(tmp_path, 2), runner=findings)
    log = tmp_path / "research" / "reviews" / "rounds.jsonl"
    log.write_text(log.read_text() + '{"kind": "script", "round": 3, "revis')       # a run killed mid-write
    revise(tmp_path, 3)
    review.main(args(tmp_path, 3), runner=findings)
    assert "1 unreadable line(s) skipped" in capsys.readouterr().out
    revise(tmp_path, 4)
    with pytest.raises(SystemExit, match="has had 2 review rounds"):
        review.main(args(tmp_path, 4), runner=findings)
