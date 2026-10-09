import re
import sys
from pathlib import Path

import pytest

from studio_kit import proc

KIT = Path(proc.__file__).parent


def test_a_child_reads_an_empty_stdin_unless_fed():
    read = [sys.executable, "-c", "import sys; print(repr(sys.stdin.read()))"]
    assert proc.run(read, capture_output=True, text=True, timeout=10).stdout.strip() == "''"
    assert proc.run(read, input="notes", capture_output=True, text=True, timeout=10).stdout.strip() == "'notes'"
    p = proc.popen(read, stdout=proc.PIPE, text=True)
    assert p.communicate(timeout=10)[0].strip() == "''"


def test_a_missing_program_stops_with_its_name_and_the_fix(monkeypatch):
    monkeypatch.setenv("PATH", "")
    proc.tool.cache_clear()
    try:
        with pytest.raises(SystemExit, match="no-such-tool is not on PATH.*studio doctor"):
            proc.tool("no-such-tool")
    finally:
        proc.tool.cache_clear()


def test_only_proc_starts_programs():
    # Every child must go through proc, or it inherits the agent's stdin again.
    direct = [p.name for p in KIT.glob("*.py") if p.name != "proc.py" and re.search(r"\bsubprocess\b", p.read_text())]
    assert not direct, f"call proc.run / proc.popen instead of subprocess in {direct}"
