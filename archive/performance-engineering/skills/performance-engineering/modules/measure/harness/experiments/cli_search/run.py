"""Wire the CLI probes into the harness and produce all artifacts.

Run from the repo root:  uv run python experiments/cli_search/run.py

The point of this experiment is the normalization hypothesis (C3): the
measurements come from hyperfine, an external tool, yet the aggregator
(stats.aggregate) and reporter (report.plot_scaling / format_table) are reused
*unchanged* from the library regime. The only new code is the CLI adapter
(harness/cli_regime.py) plus this experiment's target.py — mirroring claim C1.
"""

from __future__ import annotations

import json
from pathlib import Path

import target  # same directory; on sys.path because this file is the entrypoint

from harness.cli_regime import run_cli_suite
from harness.report import format_table, plot_scaling
from harness.stats import aggregate

RESULTS = Path(__file__).resolve().parents[2] / "results" / "cli_search"


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)

    # Stage 1 -> 2: invoke + measure via hyperfine (adapter enforces the gate).
    samples = run_cli_suite(target.probes, target.param_grid, prepare=target.prepare)
    (RESULTS / "raw_samples.json").write_text(json.dumps(samples, indent=2))

    # Stage 2 -> 3: aggregate into honest statistics — SPINE REUSED UNCHANGED.
    stats = aggregate(samples)
    (RESULTS / "stats.json").write_text(json.dumps(stats, indent=2))

    # Stage 3 -> 4: plot and tabulate — SPINE REUSED UNCHANGED.
    plot_scaling(
        stats,
        "lines",
        out_path=RESULTS / "scaling.png",
        title="Match counting: wall-clock cost vs corpus size (ripgrep vs grep)",
        x_label="corpus size (lines)",
        per_call_label="invocation",
    )
    print(format_table(stats, x_key="lines"))
    print(f"\nArtifacts written to {RESULTS}/")
    print("  raw_samples.json  stats.json  scaling.png")


if __name__ == "__main__":
    main()
