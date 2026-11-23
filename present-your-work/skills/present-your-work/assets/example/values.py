#!/usr/bin/env python3
"""Compute every number the example presentation shows, print them, and check the page shows exactly these.

    python3 -I values.py

The work is invented: a nightly load of a season's 40 match files that finished too late for the
analysts, made faster by skipping files whose contents have not changed. The file contents, the
read time per file and the start time are made up; everything else (which files changed, their
fingerprints, the finish times) is computed here from them.
"""
import hashlib
import random
from datetime import datetime, timedelta
from pathlib import Path

PAGE = Path(__file__).resolve().parent / "page.html"
FILES = 40
START = datetime(2026, 11, 20, 5, 30)   # the load starts at 05:30
READ_MIN = 5.0                           # minutes to read one file
PRINT_MIN = 0.1                          # minutes to compute one file's fingerprint
DEADLINE = "07:00"                       # when the analysts start
EXAMPLE_FILE = 24                        # the file the key-idea chapter follows


def contents(i, night):
    """A file's contents on a night. Three files change between last night and tonight."""
    changed = set(random.Random(7).sample(range(1, FILES + 1), 3))
    return f"round {i} results" + (" corrected" if night == "tonight" and i in changed else "")


def fingerprint(text):
    return hashlib.sha256(text.encode()).hexdigest()[:8]


def finish(minutes):
    return (START + timedelta(minutes=minutes)).strftime("%H:%M")


def main():
    changed = [i for i in range(1, FILES + 1)
               if fingerprint(contents(i, "tonight")) != fingerprint(contents(i, "last"))]
    old = finish(FILES * READ_MIN)
    new = finish(FILES * PRINT_MIN + len(changed) * READ_MIN)
    worst = finish(FILES * PRINT_MIN + FILES * READ_MIN)   # a format change: every fingerprint differs
    pick_tonight = fingerprint(contents(EXAMPLE_FILE, "tonight"))
    pick_last = fingerprint(contents(EXAMPLE_FILE, "last"))

    print(f"changed files: {changed}")
    print(f"finish: before {old}, after {new}, on a format change {worst}; deadline {DEADLINE}")
    print(f"file {EXAMPLE_FILE}: tonight {pick_tonight}, last night {pick_last}")

    assert EXAMPLE_FILE not in changed and pick_tonight == pick_last, "the example file should be unchanged"
    assert old > DEADLINE > new, "the old load should miss the deadline and the new one meet it"

    page = PAGE.read_text()
    expected = [
        f"const CHANGED = {changed};",
        f"const TIMES = {{ old: '{old}', new: '{new}', worst: '{worst}', deadline: '{DEADLINE}' }};",
        f"const PICK = {{ file: {EXAMPLE_FILE}, tonight: '{pick_tonight}', last: '{pick_last}' }};",
        f"const FILES = {FILES};",
    ]
    missing = [e for e in expected if e not in page]
    assert not missing, "page.html does not show these computed values:\n" + "\n".join(missing)
    print(f"ok: {len(expected)} computed lines on the page match")


if __name__ == "__main__":
    main()
