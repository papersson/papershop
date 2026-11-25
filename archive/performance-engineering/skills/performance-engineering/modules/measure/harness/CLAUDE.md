# CLAUDE.md — performance-eval-harness

## What this project is

We are developing *transferable methodology*: "how to build performance-evaluation
harnesses for any codebase." The harness is both the output and the instrument.
This is empirical methodology development (the scientific method), not one benchmark.

Two loops: an **object loop** (build a harness, run an experiment, get numbers)
and a **meta loop** (refine how-to-build-harnesses knowledge). Experiments exist
to attack falsifiable claims, not to produce numbers for their own sake.

## Read first — the lab notebook is the source of truth

Before doing anything, read these and treat them as authoritative:

- `research/THEORY.md` — current best understanding (spine, regimes, open hypotheses).
- `research/CLAIMS.md` — the falsifiable claim ledger with statuses. The meta
  loop's job is to drive open claims to `confirmed` / `refuted`.
- `research/LOG.md` — append-only history of iterations.

After any experiment or iteration, **update the ledger and append to the log.**
A `refuted` claim is a success — it updates the theory.

## The one invariant (this is what makes the work falsifiable)

**Core claim (C1):** to evaluate a new target you write only a probe/adapter; you
never modify the spine. The spine is:

- `src/harness/core.py`   — in-process runner, the `Probe` contract, correctness gate.
- `src/harness/stats.py`  — `aggregate()` + bootstrap CI. The **normalization backbone**.
- `src/harness/report.py` — `plot_scaling()` / `format_table()`; reads only stats.

`stats.py` and `report.py` are shared across all regimes. Editing them to support
a new target is **a finding (a refutation of the normalization hypothesis), not a
casual edit** — if you must, stop and document it in `CLAIMS.md`. Components talk
only through the raw-sample schema (see THEORY.md), never by reaching across stages.

## Layout

- `src/harness/` — the shared spine (above).
- `experiments/<name>/` — one experiment: `target.py` (exposes `probes` + `param_grid`,
  or a regime adapter) and `run.py` (wires runner → `aggregate` → `plot_scaling`).
- `results/<name>/` — generated artifacts: `raw_samples.json`, `stats.json`, `*.png`.
- `research/` — the notebook.

Measurement **regimes** (timing machinery differs; spine is shared): library/
in-process (confirmed), CLI/subprocess (hyperfine), service/load. A regime is
selected per target by the decision framework in THEORY.md.

## Run / verify (the feedback loop)

```sh
uv sync
uv run python experiments/<name>/run.py
```

An experiment is sound when: artifacts are produced (`raw_samples.json`,
`stats.json`, a rendered plot), the **correctness gate passes** (compared
implementations agree on output), and the spine is unchanged — or any spine change
is documented as a claim outcome. Prefer verification by an agent that did not
write the experiment.

## How we work

Iterations are run by the **self-driving research loop**, `research/research_loop.js`
(a Workflow script; see `research/LOOP.md`). It reads the notebook, picks the
highest-value open claim, runs a real experiment, verifies it with a separate
agent, writes findings back, and repeats until an adversarial "target generator"
critic can no longer break the framework. Run it with
`Workflow({ scriptPath: "<repo>/research/research_loop.js", args: "perf-harness-research-loop" })`.
The human role is to set the goal and audit the report — see the automate-out-of-
the-loop maturity ladder.

## Keep this file lean

Always-on context is expensive. Put durable principles here and pointers to the
notebook; put detail in `research/` where it can be read on demand.
