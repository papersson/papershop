"""Wire the membership probes into the harness and produce all artifacts.

Run from the repo root:  uv run python experiments/membership/run.py

This deliberately re-uses the shared spine (runner -> aggregator -> reporter)
and supplies only the target-specific probes. Adding a new experiment means
writing a new target.py, not touching the harness.
"""

from __future__ import annotations

import json
from pathlib import Path

import target  # same directory; on sys.path because this file is the entrypoint

from harness.core import run_suite
from harness.report import format_table, plot_scaling
from harness.stats import aggregate

RESULTS = Path(__file__).resolve().parents[2] / "results" / "membership"


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)

    # Stage 1 -> 2: invoke + measure (the runner enforces the correctness gate).
    samples = run_suite(target.probes, target.param_grid)
    (RESULTS / "raw_samples.json").write_text(json.dumps(samples, indent=2))

    # Stage 2 -> 3: aggregate into honest statistics.
    stats = aggregate(samples)
    (RESULTS / "stats.json").write_text(json.dumps(stats, indent=2))

    # Stage 3 -> 4: plot and tabulate.
    plot_scaling(
        stats,
        "n",
        out_path=RESULTS / "scaling.png",
        title="Membership test: cost per call vs container size",
        x_label="container size (number of elements)",
        per_call_label="call (200 lookups)",
    )
    print(format_table(stats))
    print(f"\nArtifacts written to {RESULTS}/")
    print("  raw_samples.json  stats.json  scaling.png")


if __name__ == "__main__":
    main()
