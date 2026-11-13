#!/usr/bin/env python3
"""Tests for check_scratchbook.py: a complete scratchbook passes, and each rule fails when broken.

    python3 test_check_scratchbook.py

Standard library only.
"""
from __future__ import annotations

import contextlib
import io
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_scratchbook as cs  # noqa: E402

TEMPLATES = Path(__file__).parent.parent / "templates"
HEAD = "SUT: services/worker @ 3f2a9c1\nDate: 2026-01-31\n\n"

GOOD = {
    "property-catalog.md": "# Property catalog\n\n" + HEAD + """### post-at-most-once

**Property:** each report is posted at most once.
**Kind:** safety
**Assertion:** Always, because one duplicate is already a failure.
**Priority:** high, a duplicate reaches customers.
**Enforceable by construction:** no: a relation between the queue and the channel
**Found under:** duplicate delivery
**Confirmed:** by the queue's owners, 2026-01-30, `questions/q1.md`
**Status:** checked by workload
**Open questions:**
- (needs human input) may a report be reposted after an edit?

### every-job-finishes

**Property:** a job that is put on the queue is eventually acknowledged.
**Kind:** liveness
**Assertion:** Sometimes, the run must reach an empty queue.
**Priority:** medium, a stuck job is noticed late.
**Confirmed:** no
**Status:** not checked
""",
    "properties/post-at-most-once.md": """# post-at-most-once

Claim:            each report is posted at most once
Claim type:       guarantee the SUT makes
Evidence:         worker.py:41 posts before acknowledging
Failure scenario: a job is taken twice before the first worker acknowledges it
Competing story:  none found
How to check:     an invariant over the channel after every step
""",
    "properties/every-job-finishes.md": """# every-job-finishes

Claim:            a job that is put on the queue is eventually acknowledged
Evidence:
  worker.py:44 acknowledges after posting
Failure scenario: the worker crashes after posting and nothing takes the job again
How to check:     a Sometimes assertion on an empty queue
""",
    "questions/q1.md": """# Question q1

**About:** post-at-most-once
**Asked of:** the team that owns the queue. Asked 2026-01-29.

## Scenario

1. A report is requested, and its job goes on the queue.
2. A worker takes the job and posts the report.
3. Thirty seconds pass.
4. A second worker asks for a job.

## Question

In step 4, does the queue hand out the job from step 2 again?

## What each answer changes

**Yes:** the fake with a visibility timeout is kept, and the duplicate post is a finding.
**No:** the simpler fake is kept, and the property holds as checked.

## Observed

Not run.

## Answer

"Yes, after the visibility timeout." The queue's owners, 2026-01-30.
""",
    "fault-inventory.md": "# Fault inventory\n\n" + HEAD + """| Source | Status | Rule in the driver, or the reason | Took effect in |
|---|---|---|---|
| message delivered out of order | action | `deliver_any` | 240 of 300 test cases |
| message delivered twice | action | `duplicate` | 187 of 300 test cases |
| message held back | action | `hold` | 90 of 300 test cases |
| clock advanced | action | `advance` | 201 of 300 test cases |
| dependency call fails | action | `fail_post` | 77 of 300 test cases |
| dependency call times out after taking effect | not tried | the channel client has no timeout yet | |
| deferred operation applied late | not applicable | the worker defers nothing | |
| stale read | not applicable | one store, read-your-writes | |
| crash mid-operation | action | `crash_after_post` | 64 of 300 test cases |
| concurrent operations on one target | not tried | the library's concurrent mode is not set up | |
""",
    "run-record.md": "# Run record\n\n" + HEAD + """## Scope

Research and workload. No change to the SUT beyond a seam for the queue.

## Command

`python3 tests/test_worker.py`, Hypothesis 6.170.15, 300 test cases, derandomized.

## Result

```
1 failed, 1 passed
```
""",
    "mutation-report.md": "# Mutation report\n\n" + HEAD + """| Property | Mutant | Verdict | Counterexample, or the reason |
|---|---|---|---|
| post-at-most-once | worker.py:41, acknowledge skipped on retry | killed | token AXkB3 |
""",
    "findings/f1.md": """# Finding f1

**Property violated:** each report is posted at most once (`post-at-most-once`).
**Found by:** workload, in process.
**Reproduces on replay:** yes
**Replay:** token AXkB3, with `python3 tests/test_worker.py`

## Minimal counterexample

```
request(); take(); advance(30); take()
```

## The story

Two workers post the same report.

## Cause

**Class:** SUT defect
**Mechanism:** worker.py:41 posts before acknowledging.
""",
}


def build(root: Path, changes: dict[str, str | None] | None = None) -> None:
    files = dict(GOOD)
    files.update(changes or {})
    for name, text in files.items():
        if text is None:
            continue
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def run(changes: dict[str, str | None] | None = None, *args: str) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        build(Path(tmp), changes)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = cs.main([tmp, *args])
        return code, out.getvalue()


def edited(name: str, old: str, new: str) -> dict[str, str]:
    assert old in GOOD[name], (name, old)
    return {name: GOOD[name].replace(old, new)}


class Passes(unittest.TestCase):
    def test_a_complete_scratchbook_passes(self):
        code, out = run()
        self.assertEqual(code, 0, out)
        self.assertIn("ok (0 failures)", out)
        self.assertIn("2 properties, 1 confirmed", out)
        self.assertIn("faults: 6 action, 2 not applicable, 2 not tried", out)
        self.assertNotIn("absent", out.replace("absent, not checked: assumptions.md, audit-report.md, sut-analysis.md, workload-review.md", ""))
        self.assertIn("1 open questions need a person", out)

    def test_a_research_only_scratchbook_passes_and_lists_what_is_absent(self):
        code, out = run({"fault-inventory.md": None, "mutation-report.md": None, "findings/f1.md": None})
        self.assertEqual(code, 0, out)
        self.assertIn("absent, not checked:", out)
        self.assertIn("fault-inventory.md", out)

    def test_require_makes_an_absence_a_failure(self):
        code, out = run({"fault-inventory.md": None}, "--require", "fault-inventory.md")
        self.assertEqual(code, 1, out)
        self.assertIn("fault-inventory.md: required and absent", out)

    def test_a_missing_directory_is_a_usage_error(self):
        out = io.StringIO()
        with contextlib.redirect_stderr(out):
            self.assertEqual(cs.main(["/nonexistent/scratchbook"]), 2)


class Fails(unittest.TestCase):
    def assert_fails(self, changes, *expected: str):
        code, out = run(changes)
        self.assertEqual(code, 1, out)
        for text in expected:
            self.assertIn(text, out)

    def test_provenance(self):
        self.assert_fails(edited("property-catalog.md", "SUT: services/worker @ 3f2a9c1\n", ""), 'no "SUT: path @ commit" line')
        self.assert_fails(edited("fault-inventory.md", "Date: 2026-01-31\n", ""), 'fault-inventory.md: no "Date:" line')
        self.assert_fails(edited("run-record.md", "SUT: services/worker @ 3f2a9c1", "SUT: path/to/component @ commit"), 'run-record.md: no "SUT: path @ commit" line')

    def test_catalog_fields_and_values(self):
        self.assert_fails(edited("property-catalog.md", "**Priority:** high, a duplicate reaches customers.\n", ""),
                          'property-catalog.md [post-at-most-once]: no "**Priority:** value" line')
        self.assert_fails(edited("property-catalog.md", "**Kind:** liveness", "**Kind:** safety | liveness | reachability"), "Kind is")
        self.assert_fails(edited("property-catalog.md", "**Assertion:** Always,", "**Assertion:** Never,"), "Assertion is")
        self.assert_fails(edited("property-catalog.md", "**Status:** not checked", "**Status:** done"), "Status is")

    def test_catalog_and_evidence_files_agree(self):
        self.assert_fails({"properties/every-job-finishes.md": None}, "no evidence file; write properties/every-job-finishes.md")
        self.assert_fails({"properties/orphan.md": GOOD["properties/post-at-most-once.md"]}, 'properties/orphan.md: no "### orphan" entry')

    def test_evidence_fields(self):
        self.assert_fails(edited("properties/post-at-most-once.md", "Evidence:         worker.py:41 posts before acknowledging\n", "Evidence:\n"),
                          'properties/post-at-most-once.md: no "Evidence: value" line')

    def test_confirmed_needs_an_answered_question(self):
        self.assert_fails(edited("property-catalog.md", ", `questions/q1.md`", ""), "marked as confirmed without a question file")
        self.assert_fails({"questions/q1.md": None}, "cites questions/q1.md, which does not exist")
        self.assert_fails(edited("questions/q1.md", '"Yes, after the visibility timeout." The queue\'s owners, 2026-01-30.\n', ""),
                          "questions/q1.md has no answer")

    def test_question_form(self):
        seven = "".join(f"{n}. Step.\n" for n in range(1, 8))
        self.assert_fails({"questions/q2.md": re.sub(r"1\. A report.*?4\. [^\n]*\n", seven, GOOD["questions/q1.md"], flags=re.S)},
                          "questions/q2.md: the scenario has 7 numbered steps")
        self.assert_fails(edited("questions/q1.md", "does the queue hand out the job from step 2 again?", "the queue hands out the job again."),
                          "must hold exactly one question")
        self.assert_fails(edited("questions/q1.md", "**No:** the simpler fake is kept, and the property holds as checked.\n", ""),
                          "says nothing for No")

    def test_fault_inventory(self):
        self.assert_fails(edited("fault-inventory.md", "| stale read | not applicable | one store, read-your-writes | |\n", ""),
                          "fault-inventory.md [stale read]: the row is missing")
        self.assert_fails(edited("fault-inventory.md", "| message held back | action |", "| message held back | done |"), 'status is "done"')
        self.assert_fails(edited("fault-inventory.md", "`hold` | 90 of 300 test cases", " | 90 of 300 test cases"), "no rule named")
        for effect in ("", "0 of 300 test cases", "not measured"):
            self.assert_fails(edited("fault-inventory.md", "`hold` | 90 of 300 test cases", "`hold` | " + effect), '"Took effect in" gives no count above zero', "or mark the row not tried")
        code, out = run(edited("fault-inventory.md", "`fail_post` | 77 of 300 test cases", "`fail_post` | 0 of 300"))
        self.assertNotIn("or mark the row not tried", out)
        code, out = run(edited("fault-inventory.md", "`hold` | 90 of 300 test cases", "`hold` | 0.4% of 5000 test cases"))
        self.assertEqual(code, 0, out)
        self.assert_fails({"fault-inventory.md": GOOD["fault-inventory.md"] + "| crash mid-operation | not applicable | none | |\n"}, "[crash mid-operation]: the row appears twice")
        self.assert_fails(edited("fault-inventory.md", "not applicable | one store, read-your-writes", "not applicable | "), '"not applicable" needs a reason')

    def test_a_failing_dependency_and_a_crash_must_be_tried(self):
        self.assert_fails(edited("fault-inventory.md", "| crash mid-operation | action | `crash_after_post` | 64 of 300 test cases |",
                                 "| crash mid-operation | not tried | no time | |"),
                          "fault-inventory.md [crash mid-operation]: may not be left as not tried")

    def test_mutation_report(self):
        self.assert_fails(edited("mutation-report.md", "| post-at-most-once | worker.py:41, acknowledge skipped on retry | killed | token AXkB3 |\n", ""),
                          "mutation-report.md [post-at-most-once]: no row for this safety property")
        self.assert_fails(edited("mutation-report.md", "| killed |", "| caught |"), 'verdict is "caught"')
        self.assert_fails(edited("mutation-report.md", "| killed | token AXkB3 |", "| killed | |"), '"killed" needs its counterexample')

    def test_findings(self):
        self.assert_fails(edited("findings/f1.md", " (`post-at-most-once`)", ""), "names no slug from property-catalog.md")
        self.assert_fails(edited("findings/f1.md", "**Replay:** token AXkB3, with `python3 tests/test_worker.py`\n", ""), 'reproduces, but "**Replay:**" is empty')
        self.assert_fails(edited("findings/f1.md", "request(); take(); advance(30); take()\n", ""), "findings/f1.md: no counterexample")
        self.assert_fails(edited("findings/f1.md", "**Class:** SUT defect", "**Class:** bug"), 'Class is "bug"')

    def test_template_leftovers(self):
        self.assert_fails(edited("findings/f1.md", "# Finding f1", "# Finding {id}"), "findings/f1.md:1: a placeholder in braces")
        code, out = run({"sut-analysis.md": "# SUT analysis\n\n" + HEAD + "`GET /jobs/{id}` returns one job. Dates are sent as YYYY-MM-DD.\n"})
        self.assertEqual(code, 0, out)
        self.assert_fails(edited("questions/q1.md", "3. Thirty seconds pass.", "..."), 'a line of "..." is left from a template')


class Tolerates(unittest.TestCase):
    """Reasonable ways of filling in the templates pass."""

    def assert_passes(self, changes):
        code, out = run(changes)
        self.assertEqual(code, 0, out)
        return out

    def test_fields_as_a_list_or_with_the_colon_outside_the_bold(self):
        catalog = GOOD["property-catalog.md"]
        self.assert_passes({"property-catalog.md": re.sub(r"(?m)^\*\*", "- **", catalog)})
        self.assert_passes({"property-catalog.md": re.sub(r"(?m)^\*\*(\w[\w ]*):\*\*", r"**\1**:", catalog)})

    def test_backticks_and_capitals_in_values(self):
        out = self.assert_passes(edited("property-catalog.md", "**Assertion:** Always,", "**Assertion:** `Always`,"))
        self.assertIn("mutants: 1 killed", out)
        self.assert_passes(edited("property-catalog.md", "**Kind:** safety", "**Kind:** Safety"))

    def test_other_headings_in_the_catalog_are_not_entries(self):
        self.assert_passes({"property-catalog.md": GOOD["property-catalog.md"] + "\n### Relationships\n\nThe two properties share worker.py:41.\n"})

    def test_a_pipe_inside_a_code_span_does_not_split_a_cell(self):
        self.assert_passes(edited("mutation-report.md", "worker.py:41, acknowledge skipped on retry", "worker.py:41, `a || b` changed to `a && b`"))

    def test_a_verdict_may_say_more(self):
        self.assert_passes(edited("mutation-report.md", "| killed |", "| killed (rung 3) |"))

    def test_guidance_in_comments_is_not_content(self):
        code, out = run(edited("questions/q1.md", '"Yes, after the visibility timeout." The queue\'s owners, 2026-01-30.\n',
                               "<!-- The answer, in their words. -->\n"))
        self.assertEqual(code, 1, out)
        self.assertIn("questions/q1.md has no answer", out)


class NeedsACatalog(unittest.TestCase):
    def test_a_name_starting_with_no_is_not_no(self):
        code, out = run(edited("property-catalog.md", "**Confirmed:** by the queue's owners, 2026-01-30, `questions/q1.md`", "**Confirmed:** Nora, 2026-01-30"))
        self.assertEqual(code, 1, out)
        self.assertIn("marked as confirmed without a question file", out)

    def test_a_mutation_report_or_findings_without_a_catalog_fail(self):
        code, out = run({"property-catalog.md": None})
        self.assertEqual(code, 1, out)
        self.assertIn("mutation-report.md: refers to properties, and there is no property-catalog.md", out)
        self.assertIn("findings: refers to properties", out)

    def test_run_record_sections(self):
        code, out = run(edited("run-record.md", "`python3 tests/test_worker.py`, Hypothesis 6.170.15, 300 test cases, derandomized.\n", ""))
        self.assertEqual(code, 1, out)
        self.assertIn('run-record.md: the "Command" section is missing or empty', out)


class TemplatesAgree(unittest.TestCase):
    """The allowed values live in two places, the templates and the script. Keep them the same."""

    def read(self, name: str) -> str:
        return (TEMPLATES / name).read_text(encoding="utf-8")

    def alternatives(self, text: str, field: str) -> tuple[str, ...]:
        line = re.search(r"\*\*" + re.escape(field) + r":\*\* <!-- (.*?) -->", text).group(1)
        return tuple(re.sub(r"[,.(].*", "", part).strip() for part in line.split(" | "))

    def test_fault_sources(self):
        rows = [row[0] for row in cs.table_rows(cs.content(self.read("fault-inventory.md")))]
        self.assertEqual(tuple(rows[1:]), cs.FAULTS)
        workload = (TEMPLATES.parent / "modules" / "workload.md").read_text(encoding="utf-8")
        self.assertEqual(tuple(row[0] for row in cs.table_rows(workload) if row[0] in cs.FAULTS), cs.FAULTS)
        for status in cs.FAULT_STATUSES:
            self.assertIn(f"- `{status}`:", self.read("fault-inventory.md"))

    def test_verdicts(self):
        self.assertEqual(tuple(re.findall(r"^- `([a-z ]+)`:", self.read("mutation-report.md"), re.M)), cs.VERDICTS)

    def test_property_fields(self):
        text = self.read("property.md")
        self.assertEqual(self.alternatives(text, "Kind"), cs.KINDS)
        self.assertEqual(self.alternatives(text, "Assertion"), cs.ASSERTIONS)
        self.assertEqual(self.alternatives(text, "Status"), cs.STATUSES)
        for field in cs.CATALOG_FIELDS:
            self.assertIn(f"**{field}:**", text)
        for field in cs.EVIDENCE_FIELDS:
            self.assertRegex(text, r"(?m)^" + re.escape(field) + r":")

    def test_finding_fields(self):
        text = self.read("finding.md")
        self.assertEqual(self.alternatives(text, "Class"), cs.CAUSE_CLASSES)
        for field in ("Property violated", "Found by", "Reproduces on replay", "Replay"):
            self.assertIn(f"**{field}:**", text)
        self.assertIn("## Minimal counterexample", text)

    def test_question_sections(self):
        text = self.read("question.md")
        for heading in ("Scenario", "Question", "What each answer changes", "Answer"):
            self.assertIn(f"## {heading}", text)

    def test_run_record_sections(self):
        for heading in cs.RUN_RECORD_SECTIONS:
            self.assertIn(f"## {heading}", self.read("run-record.md"))

    def test_every_unfilled_template_fails(self):
        property_template = self.read("property.md")
        entry = property_template[property_template.index("### {slug}"):property_template.index("## In `properties/")]
        evidence = property_template[property_template.index("Claim:"):]
        unfilled = {
            "property-catalog.md": "# Property catalog\n\n" + HEAD + entry.replace("{slug}", "post-at-most-once"),
            "properties/post-at-most-once.md": evidence,
            "questions/q1.md": self.read("question.md"),
            "findings/f1.md": self.read("finding.md"),
            "fault-inventory.md": self.read("fault-inventory.md"),
            "mutation-report.md": self.read("mutation-report.md"),
            "run-record.md": self.read("run-record.md"),
            "assumptions.md": self.read("assumption-register.md"),
        }
        for name, text in unfilled.items():
            changes = {name: text}
            if name == "property-catalog.md":
                changes["properties/every-job-finishes.md"] = None
            code, out = run(changes)
            self.assertEqual(code, 1, name + "\n" + out)
            self.assertTrue(any(line.startswith(name.split("/")[0]) for line in out.splitlines()), name + "\n" + out)


if __name__ == "__main__":
    unittest.main()
