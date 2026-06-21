# performance-eval-harness

A small, generalizable harness for **invoking** code, **measuring** it fairly,
**aggregating** honest statistics, and **plotting** the result. The point is the
*contracts between components*, not any one benchmark.

## The shared spine

Four stages, each talking to the next only through plain data. Any stage can be
replaced without touching the others.

```
   probe  ──prepare/invoke──▶  runner  ──raw_samples──▶  aggregator  ──stats──▶  reporter
(target-specific)            (owns clock,            (median + bootstrap     (plots, tables)
 the ONLY code you            warmup, batch           confidence interval)
 write per project)           calibration,
                              correctness gate)
```

| Stage      | File                  | Reads            | Writes               |
| ---------- | --------------------- | ---------------- | -------------------- |
| probe      | `experiments/*/target.py` | params       | a fixture + output   |
| runner     | `src/harness/core.py` | probes + grid    | `raw_samples.json`   |
| aggregator | `src/harness/stats.py`| raw samples      | `stats.json`         |
| reporter   | `src/harness/report.py`| stats           | `scaling.png`, table |

The one target-specific contract is a `Probe`: a `name`, a `prepare(params) ->
fixture` (untimed setup), and an `invoke(fixture) -> output` (the timed work).
Everything downstream depends on the raw-sample schema, never on your code.

## What "fair measurement" means here

- **The target never times itself.** The runner owns the clock and the loop.
- **Batch calibration.** Fast operations are run in batches sized to clear the
  timer's resolution, then divided back out.
- **A correctness gate.** Probes that disagree on output for the same input are
  refused — you can never accidentally crown a fast-but-wrong implementation.
- **Warmup is discarded**, and repetitions run in **randomized, interleaved
  order** so system drift is shared across probes, not dumped on the last one.
- **Robust statistics.** The median with a 95% bootstrap confidence interval,
  no normality assumption.

## Run the first experiment

```sh
uv sync
uv run python experiments/membership/run.py
```

It compares three ways to test membership (list vs set vs dict) across container
sizes and writes artifacts to `results/membership/`. The expected result: the
list is a straight line on the log-log plot (linear, O(n)); the set and dict are
flat (constant, O(1)).

## Add your own experiment

Write a new `experiments/<name>/target.py` that exposes `probes` and
`param_grid`, plus a tiny `run.py` that calls `run_suite -> aggregate ->
plot_scaling`. You do not modify the harness.

## Scope (so far)

This implements one **measurement regime**: in-process microbenchmarking. Other
regimes — subprocess wall-clock (CLI tools), or a load generator with an arrival
schedule (services) — would plug into the same four contracts. The intended
shape is a shared spine plus a small set of regimes you select with a decision
checklist, rather than one timing strategy pretending to fit everything.
```
