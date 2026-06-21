"""The thing under test (CLI regime): ripgrep vs grep counting matches.

A classic CLI comparison: count the lines matching a pattern in a text file,
two ways. Both ``rg -c`` and ``grep -c`` print a single integer — the number of
matching lines — so for the same corpus they MUST agree. The CLI correctness
gate depends on that, exactly as the library experiment's gate depends on all
three containers returning the same hit count.

The corpus is generated deterministically (fixed seed) and parameterized by the
number of lines, so the experiment scales the input and reveals how each tool's
wall-clock cost grows.
"""

from __future__ import annotations

import random
from pathlib import Path

from harness.cli_regime import CliProbe

_PATTERN = "ERROR"
_HIT_RATE = 0.1  # fraction of lines that contain the pattern
_CORPUS_DIR = Path(__file__).resolve().parents[2] / "results" / "cli_search" / "corpus"


def _corpus_path(lines: int) -> Path:
    return _CORPUS_DIR / f"corpus_{lines}.txt"


def prepare(params: dict) -> None:
    """Materialize the corpus for an input point (untimed setup, deterministic)."""
    lines = params["lines"]
    _CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    path = _corpus_path(lines)

    rng = random.Random(1234 + lines)  # deterministic, distinct per size
    chunks: list[str] = []
    for i in range(lines):
        if rng.random() < _HIT_RATE:
            chunks.append(f"2026-06-20 {_PATTERN} request {i} failed code={rng.randint(400, 599)}")
        else:
            chunks.append(f"2026-06-20 INFO  request {i} ok latency={rng.randint(1, 200)}ms")
    path.write_text("\n".join(chunks) + "\n")


def _rg_command(params: dict) -> str:
    return f"rg -c {_PATTERN} {_corpus_path(params['lines'])}"


def _grep_command(params: dict) -> str:
    return f"grep -c {_PATTERN} {_corpus_path(params['lines'])}"


probes = [
    CliProbe(name="ripgrep", command=_rg_command),
    CliProbe(name="grep", command=_grep_command),
]

# Modest grid so the suite finishes in a couple of minutes.
param_grid = [{"lines": n} for n in (2_000, 20_000, 200_000, 1_000_000)]
