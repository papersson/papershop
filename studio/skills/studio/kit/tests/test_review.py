import json
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


def test_rounds_stop_at_max_rounds(tmp_path):
    make(tmp_path, {"max_rounds": 1})
    with pytest.raises(SystemExit, match="past max_rounds"):
        review.main(args(tmp_path, 2))


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


def test_the_default_cap_is_three_rounds_and_thorough_restores_six(tmp_path):
    with pytest.raises(SystemExit, match=r"past max_rounds \(3\)"):
        review.main(args(make(tmp_path / "a"), 4))
    with pytest.raises(SystemExit, match=r"past max_rounds \(6\)"):
        review.main(args(make(tmp_path / "b", {"thorough": True}), 7))
