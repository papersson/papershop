#!/usr/bin/env python3
"""Check a correctness scratchbook for what a program can check: its form and its cross-references.

    python3 check_scratchbook.py [SCRATCHBOOK] [--require FILE ...]

SCRATCHBOOK defaults to correctness/scratchbook. The script reads the Markdown files the skill's
modules emit. It does not judge whether a property is the right one or a fake is faithful; that
is the reviewer's job (modules/review.md).

  provenance   every top-level file starts with "SUT: path @ commit" and "Date: YYYY-MM-DD";
  catalog      every entry of property-catalog.md has its fields, with a kind, an assertion type
               and a status from the allowed values, and an evidence file under properties/;
  evidence     every evidence file belongs to a catalog entry and gives a claim, its evidence, a
               failure scenario and a way to check it;
  confirmed    a property marked as confirmed names a question file, and that file has an answer;
  questions    every question has a scenario of one to six numbered steps, one question ending in
               a question mark, and what each answer changes;
  run record   run-record.md gives the scope, the command and the result;
  faults       fault-inventory.md keeps every row of the template; each row is an action with a
               rule and a count of how often it took effect, is not applicable with a reason, or
               is not tried with a reason; a failing dependency call and a crash may not be left
               as not tried;
  mutation     mutation-report.md has one row per safety property in the catalog, each with a
               known verdict and the counterexample or reason the verdict calls for;
  findings     every finding names a property from the catalog, a cause class, whether it
               reproduces, and a counterexample; one that reproduces says how to replay it;
  leftovers    no heading or table row still holds a placeholder from a template.

Text inside HTML comments is ignored, so a template's guidance never counts as content. A file
that does not exist is not checked and is listed as absent, so a research-only task passes. Pass
--require to make an absence a failure, for example
--require fault-inventory.md --require run-record.md once a workload has been built.

It prints one line per failure, "file: what is wrong; what to do", then one summary line. Exit 0
when every check holds, 1 when one fails, 2 on a usage error. Standard library only, Python 3.9+.
The allowed values below are the ones in templates/; change both together
(test_check_scratchbook.py fails when they disagree).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

KINDS = ("safety", "liveness", "reachability")
ASSERTIONS = ("Always", "AlwaysOrUnreachable", "Sometimes", "Reachable", "Unreachable")
SAFETY_ASSERTIONS = ("Always", "AlwaysOrUnreachable", "Unreachable")
STATUSES = ("not checked", "checked by workload", "checked by audit", "invalidated")
CATALOG_FIELDS = ("Property", "Kind", "Assertion", "Priority", "Confirmed", "Status")
EVIDENCE_FIELDS = ("Claim", "Evidence", "Failure scenario", "How to check")
FAULTS = (
    "message delivered out of order",
    "message delivered twice",
    "message held back",
    "clock advanced",
    "dependency call fails",
    "dependency call times out after taking effect",
    "deferred operation applied late",
    "stale read",
    "crash mid-operation",
    "concurrent operations on one target",
)
FAULT_STATUSES = ("action", "not applicable", "not tried")
FAULTS_THAT_MUST_BE_TRIED = ("dependency call fails", "crash mid-operation")
VERDICTS = ("killed", "survived", "collateral", "not reached", "equivalent", "stillborn", "not mutated")
CAUSE_CLASSES = ("SUT defect", "false assumption", "unfaithful fake", "wrong property", "workload defect")
RUN_RECORD_SECTIONS = ("Scope", "Command", "Result")
TOP_LEVEL = (
    "sut-analysis.md",
    "property-catalog.md",
    "assumptions.md",
    "run-record.md",
    "fault-inventory.md",
    "workload-review.md",
    "mutation-report.md",
    "audit-report.md",
)
NEED_A_CATALOG = ("mutation-report.md", "findings")
PLACEHOLDER = re.compile(r"\{[a-z]+\}")
BOLD_FIELD = re.compile(r"^[ \t]*(?:[-*][ \t]+)?\*\*([^*:\n]+?):?\*\*:?[ \t]*(.*)$", re.M)
PLAIN_FIELD = re.compile(r"^(?:[-*][ \t]+)?([A-Z][A-Za-z ]+):[ \t]*(.*)$")


def content(text: str) -> str:
    """The text without HTML comments, which hold a template's guidance."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def without_fences(text: str) -> str:
    """The text with fenced code blocks blanked, line count kept."""
    out, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            out.append("")
        else:
            out.append("" if fenced else line)
    return "\n".join(out)


def fenced_blocks(text: str) -> list[str]:
    return [m.strip() for m in re.findall(r"```[^\n]*\n(.*?)```", text, re.S)]


def sections(text: str, level: int) -> dict[str, str]:
    """Heading text to body, for headings of exactly this level outside code fences."""
    marks = "#" * level + " "
    result: dict[str, str] = {}
    name, fenced = None, False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        if not fenced and line.startswith(marks):
            name = line[len(marks):].strip()
            result[name] = ""
        elif not fenced and re.match(r"#{1,%d} " % level, line):
            name = None
        elif name is not None:
            result[name] += line + "\n"
    return result


def bold_fields(text: str) -> dict[str, str]:
    """"**Name:** value" lines, with or without a list marker, the colon inside or outside the bold."""
    return {m.group(1).strip(): m.group(2).strip() for m in BOLD_FIELD.finditer(without_fences(text))}


def plain_fields(text: str) -> dict[str, str]:
    """"Key: value" lines, where a value may continue on indented or unkeyed lines below."""
    result: dict[str, str] = {}
    key = None
    for line in without_fences(text).splitlines():
        if line.startswith("#"):
            key = None
            continue
        m = PLAIN_FIELD.match(line)
        if m:
            key = m.group(1).strip()
            result[key] = m.group(2).strip()
        elif key is not None and line.strip():
            result[key] = (result[key] + " " + line.strip()).strip()
    return result


def split_cells(line: str) -> list[str]:
    """The cells of one table row. A pipe inside a code span or after a backslash is not a separator."""
    cells, cell, in_code, i = [], "", False, 0
    line = line.strip()
    while i < len(line):
        ch = line[i]
        if ch == "\\" and i + 1 < len(line) and line[i + 1] == "|":
            cell += "|"
            i += 2
            continue
        if ch == "`":
            in_code = not in_code
        if ch == "|" and not in_code:
            cells.append(cell.strip())
            cell = ""
        else:
            cell += ch
        i += 1
    cells.append(cell.strip())
    return cells[1:-1] if line.startswith("|") and line.endswith("|") else cells[1:] if line.startswith("|") else cells


def table_rows(text: str) -> list[list[str]]:
    """Body and header rows of every Markdown table outside code fences."""
    rows = []
    for line in without_fences(text).splitlines():
        line = line.strip()
        if line.startswith("|") and not re.fullmatch(r"\|[\s:|-]+\|?", line):
            rows.append(split_cells(line))
    return rows


def plain(value: str) -> str:
    return value.replace("`", "").strip()


def starts_with_one_of(value: str, allowed: tuple[str, ...], exact_case: bool = False) -> str | None:
    """The longest allowed value that the text starts with as a whole word, backticks ignored."""
    value = plain(value)
    for option in sorted(allowed, key=len, reverse=True):
        if re.match(re.escape(option) + r"(?![A-Za-z])", value, 0 if exact_case else re.I):
            return option
    return None


class Check:
    def __init__(self, root: Path):
        self.root = root
        self.failures: list[tuple[str, str]] = []
        self.absent: list[str] = []
        self.summary: list[str] = []
        self.catalog: dict[str, dict[str, str]] = {}

    def fail(self, path: str, message: str) -> None:
        self.failures.append((path, message))

    def text(self, path: Path) -> str:
        return content(path.read_text(encoding="utf-8"))

    def read(self, name: str) -> str | None:
        path = self.root / name
        if not path.is_file():
            self.absent.append(name)
            return None
        return self.text(path)

    def files(self, folder: str) -> list[Path]:
        return sorted((self.root / folder).glob("*.md")) if (self.root / folder).is_dir() else []

    # ---- checks

    def provenance(self) -> None:
        for name in TOP_LEVEL:
            path = self.root / name
            if not path.is_file():
                continue
            head = "\n".join(self.text(path).splitlines()[:12])
            sut = re.search(r"^SUT:\s*(\S+)\s+@\s+(\S+)", head, re.M)
            if not sut or sut.group(1) == "path/to/component":
                self.fail(name, 'no "SUT: path @ commit" line in the first 12 lines; add it, with the real path and commit')
            if not re.search(r"^Date:\s*\d{4}-\d{2}-\d{2}\b", head, re.M):
                self.fail(name, 'no "Date:" line with a date such as 2026-01-31 in the first 12 lines; add it')

    def property_catalog(self) -> None:
        name = "property-catalog.md"
        text = self.read(name)
        if text is None:
            for needs in NEED_A_CATALOG:
                if (self.root / needs).exists():
                    self.fail(needs, "refers to properties, and there is no property-catalog.md; write the catalog first")
            return
        entries = {slug: bold_fields(body) for slug, body in sections(text, 3).items()}
        entries = {slug: fields for slug, fields in entries.items() if any(f in fields for f in CATALOG_FIELDS)}
        if not entries:
            self.fail(name, 'no entries; add one "### slug" section per property, in the form of templates/property.md')
        for slug, fields in entries.items():
            self.catalog[slug] = fields
            where = f"{name} [{slug}]"
            for field in CATALOG_FIELDS:
                if not fields.get(field):
                    self.fail(where, f'no "**{field}:** value" line, or its value is empty; fill it in')
            for field, allowed, exact in (("Kind", KINDS, False), ("Assertion", ASSERTIONS, True), ("Status", STATUSES, False)):
                value = fields.get(field, "")
                if value and (starts_with_one_of(value, allowed, exact) is None or " | " in value):
                    self.fail(where, f'{field} is "{value}"; start it with one of: {", ".join(allowed)}')
            if not (self.root / "properties" / f"{slug}.md").is_file():
                self.fail(where, f"no evidence file; write properties/{slug}.md")
            self.confirmation(where, fields.get("Confirmed", ""))
        confirmed = sum(1 for f in self.catalog.values() if f.get("Confirmed") and not self.unconfirmed(f["Confirmed"]))
        self.summary.append(f"{len(self.catalog)} properties, {confirmed} confirmed")

    @staticmethod
    def unconfirmed(value: str) -> bool:
        return starts_with_one_of(value, ("no",)) is not None

    def confirmation(self, where: str, value: str) -> None:
        if not value or self.unconfirmed(value):
            return
        cited = re.findall(r"questions/([A-Za-z0-9_.-]+?)\.md", value)
        if not cited:
            self.fail(where, "marked as confirmed without a question file; cite the file under questions/, or set Confirmed to no")
        for qid in cited:
            path = self.root / "questions" / f"{qid}.md"
            if not path.is_file():
                self.fail(where, f"cites questions/{qid}.md, which does not exist; write it, or set Confirmed to no")
            elif not sections(self.text(path), 2).get("Answer", "").strip():
                self.fail(where, f"marked as confirmed, but questions/{qid}.md has no answer; record the answer, or set Confirmed to no")

    def evidence(self) -> None:
        for path in self.files("properties"):
            where = f"properties/{path.name}"
            if self.catalog and path.stem not in self.catalog:
                self.fail(where, f'no "### {path.stem}" entry in property-catalog.md; add the entry, or remove the file')
            fields = plain_fields(self.text(path))
            for field in EVIDENCE_FIELDS:
                if not fields.get(field):
                    self.fail(where, f'no "{field}: value" line, or its value is empty; fill it in, or say what was looked for and not found')

    def questions(self) -> None:
        paths = self.files("questions")
        answered = 0
        for path in paths:
            where = f"questions/{path.name}"
            text = self.text(path)
            fields, parts = bold_fields(text), sections(text, 2)
            for field in ("About", "Asked of"):
                if not fields.get(field):
                    self.fail(where, f'no "**{field}:** value" line, or its value is empty; fill it in')
            steps = re.findall(r"^\d+\.\s+\S", parts.get("Scenario", ""), re.M)
            if not 1 <= len(steps) <= 6:
                self.fail(where, f"the scenario has {len(steps)} numbered steps; give one to six, one event each")
            asked = [line for line in parts.get("Question", "").splitlines() if line.strip()]
            if sum(line.rstrip().rstrip('"').endswith("?") for line in asked) != 1:
                self.fail(where, "the Question section must hold exactly one question, answerable with yes or no")
            changes = bold_fields(parts.get("What each answer changes", ""))
            for answer in ("Yes", "No"):
                if not changes.get(answer):
                    self.fail(where, f'"What each answer changes" says nothing for {answer}; say what that answer would change')
            if parts.get("Answer", "").strip():
                answered += 1
        if paths:
            self.summary.append(f"{len(paths)} questions, {answered} answered")

    def run_record(self) -> None:
        name = "run-record.md"
        text = self.read(name)
        if text is None:
            return
        parts = sections(text, 2)
        for section in RUN_RECORD_SECTIONS:
            if not parts.get(section, "").strip():
                self.fail(name, f'the "{section}" section is missing or empty; fill it in')

    def faults(self) -> None:
        name = "fault-inventory.md"
        text = self.read(name)
        if text is None:
            return
        rows: dict[str, list[str]] = {}
        for row in table_rows(text):
            fault = row[0].lower() if row else ""
            if fault in FAULTS:
                if fault in rows:
                    self.fail(f"{name} [{fault}]", "the row appears twice; keep one")
                rows[fault] = row
        counts = dict.fromkeys(FAULT_STATUSES, 0)
        for fault in FAULTS:
            where = f"{name} [{fault}]"
            if fault not in rows:
                self.fail(where, "the row is missing; restore it from templates/fault-inventory.md and give it a status")
                continue
            cells = rows[fault] + [""] * 4
            status, detail, effect = plain(cells[1]).lower(), cells[2], cells[3]
            must = fault in FAULTS_THAT_MUST_BE_TRIED
            if status not in FAULT_STATUSES:
                self.fail(where, f'status is "{cells[1]}"; choose one of: {", ".join(FAULT_STATUSES)}')
                continue
            counts[status] += 1
            if status == "action":
                if not detail:
                    self.fail(where, "no rule named; name the rule of the driver that injects this fault")
                if not re.search(r"[1-9]", effect) or re.match(r"0(?![.\d])", effect):
                    how = "give the rule a precondition under which it takes effect" + ("" if must else ", or mark the row not tried")
                    self.fail(where, f'"Took effect in" gives no count above zero; run the workload and record the count, and if it is zero, {how}')
            elif not detail:
                self.fail(where, f'"{status}" needs a reason in the third column')
            elif status == "not tried" and must:
                self.fail(where, "may not be left as not tried; add the action to the driver, or mark it not applicable with the reason")
        self.summary.append("faults: " + ", ".join(f"{n} {s}" for s, n in counts.items()))

    def mutation(self) -> None:
        name = "mutation-report.md"
        text = self.read(name)
        if text is None or not self.catalog:
            return
        rows: dict[str, list[str]] = {}
        for row in table_rows(text):
            slug = plain(row[0]) if row else ""
            if slug in self.catalog:
                if slug in rows:
                    self.fail(f"{name} [{slug}]", "the property has two rows; keep one mutant, and move the other to Rejected candidates")
                rows[slug] = row
        counts: dict[str, int] = {}
        for slug, fields in self.catalog.items():
            if starts_with_one_of(fields.get("Assertion", ""), ASSERTIONS, True) not in SAFETY_ASSERTIONS:
                continue
            where = f"{name} [{slug}]"
            if slug not in rows:
                self.fail(where, 'no row for this safety property; add its mutant and verdict, or a row with the verdict "not mutated" and the reason')
                continue
            cells = rows[slug] + [""] * 4
            verdict = starts_with_one_of(cells[2], VERDICTS)
            if verdict is None:
                self.fail(where, f'verdict is "{cells[2]}"; start it with one of: {", ".join(VERDICTS)}')
                continue
            counts[verdict] = counts.get(verdict, 0) + 1
            if verdict != "not mutated" and not cells[1]:
                self.fail(where, "no mutant described; give the file, the line and the change")
            if verdict != "stillborn" and not cells[3]:
                self.fail(where, f'"{verdict}" needs its counterexample or its reason in the last column')
        self.summary.append("mutants: " + (", ".join(f"{n} {v}" for v, n in counts.items()) or "none"))

    def findings(self) -> None:
        paths = self.files("findings")
        for path in paths:
            where = f"findings/{path.name}"
            text = self.text(path)
            fields, parts = bold_fields(text), sections(text, 2)
            violated = fields.get("Property violated", "")
            if not violated:
                self.fail(where, 'no "**Property violated:**" line, or it is empty; give the sentence and the slug')
            elif self.catalog and not any(re.search(r"(?<![\w-])" + re.escape(slug) + r"(?![\w-])", violated) for slug in self.catalog):
                self.fail(where, '"Property violated" names no slug from property-catalog.md; add the slug, or add the property to the catalog')
            if not fields.get("Found by"):
                self.fail(where, 'no "**Found by:**" line, or it is empty; say what found it and in which run mode')
            replay = fields.get("Reproduces on replay", "")
            outcome = starts_with_one_of(replay, ("yes", "no", "not applicable"))
            if outcome is None or " | " in replay:
                self.fail(where, '"Reproduces on replay" must start with yes, no or not applicable')
            elif outcome == "yes" and not fields.get("Replay"):
                self.fail(where, 'reproduces, but "**Replay:**" is empty; give the token or seed and the command that replays it')
            if not any(fenced_blocks(parts.get("Minimal counterexample", ""))):
                self.fail(where, "no counterexample; paste the verbatim output in a code block under Minimal counterexample")
            cause = fields.get("Class", "")
            if starts_with_one_of(cause, CAUSE_CLASSES) is None or " | " in cause:
                self.fail(where, f'Class is "{cause}"; choose one of: {", ".join(CAUSE_CLASSES)}')
        if paths:
            self.summary.append(f"{len(paths)} findings")

    def leftovers(self) -> None:
        open_questions = 0
        for path in sorted(self.root.rglob("*.md")):
            where = str(path.relative_to(self.root))
            text = self.text(path)
            open_questions += text.count("(needs human input)")
            if where == "review.md":
                continue  # the reviewer's own output, which quotes this script
            for number, line in enumerate(without_fences(text).splitlines(), 1):
                stripped = line.strip()
                first_cell = split_cells(stripped)[0] if stripped.startswith("|") else ""
                if (stripped.startswith("#") and PLACEHOLDER.search(stripped)) or PLACEHOLDER.fullmatch(first_cell):
                    self.fail(f"{where}:{number}", "a placeholder in braces is left from a template; replace it")
                elif re.fullmatch(r"(?:[-*]|\d+\.)?\s*\.\.\.", stripped):
                    self.fail(f"{where}:{number}", 'a line of "..." is left from a template; replace or remove it')
        self.summary.append(f"{open_questions} open questions need a person")

    def run(self, required: list[str]) -> None:
        self.provenance()
        self.property_catalog()
        self.evidence()
        self.questions()
        self.run_record()
        self.faults()
        self.mutation()
        self.findings()
        self.leftovers()
        for name in TOP_LEVEL:
            if not (self.root / name).is_file():
                self.absent.append(name)
        for name in required:
            if not (self.root / name).exists():
                self.fail(name, "required and absent; write it")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a correctness scratchbook.")
    parser.add_argument("scratchbook", nargs="?", default="correctness/scratchbook")
    parser.add_argument("--require", action="append", default=[], metavar="FILE",
                        help="fail when this file or folder is absent (repeatable)")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    root = Path(args.scratchbook)
    if not root.is_dir():
        print(f"{root}: not a directory; pass the scratchbook's path", file=sys.stderr)
        return 2
    check = Check(root)
    check.run(args.require)
    for path, message in check.failures:
        print(f"{path}: {message}")
    absent = sorted(set(check.absent) - set(args.require))
    if absent:
        print("absent, not checked: " + ", ".join(absent))
    print(("FAIL" if check.failures else "ok") + f" ({len(check.failures)} failures): " + "; ".join(check.summary))
    return 1 if check.failures else 0


if __name__ == "__main__":
    sys.exit(main())
