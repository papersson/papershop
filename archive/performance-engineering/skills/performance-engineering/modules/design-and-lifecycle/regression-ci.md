# Performance regression testing in CI

**Status:** READY
**Loaded when:** defending performance over time (the **defend** step of the loop).

This is the last step of the SKILL.md loop (target → measure → locate → fix → prove →
**defend**) and the only one that runs forever. The other steps end; this one is a standing
guard. Performance does not stay won. A dependency bump adds an allocation, a refactor turns
one query into N, a "harmless" log line lands in a hot loop, and the system gets slower one
unremarkable commit at a time. No single change trips an alarm, the suite stays green, and six
months later the p99 you fought for is gone with no one diff to blame. Functional tests will
not catch this: the code is still correct, just slower. Defending performance means making "it
got slower" a build event, the same way "it broke" already is.

This module is about *preventing* regressions over time. If a regression is *already live* in
production and you need to diagnose it — correlate the p99 onset with a deploy or config change
and bisect by version — that is a different job: see `../diagnose/regression-incident.md`.

The budget set in `budgets-slos.md` is **what** you defend; this module is **how**. Each
component budget (a metric at a percentile) becomes a gate that a commit can fail. Without
enforcement a budget is a dashboard nobody reads; with it, the number has teeth in CI.

---

## Why fixed thresholds fail

The obvious gate is a relative threshold: fail the build if the benchmark is more than X%
slower than before. It does not work, because there is no single X that fits more than one
benchmark.

Per-benchmark noise varies wildly. A stable, CPU-bound microbenchmark on a quiet machine
repeats to within 3-4%; a benchmark that touches allocation, I/O, or shared cache swings 15-20%
run to run for reasons that have nothing to do with the code. Pick one threshold across that
range and you lose both ways:

- **Set it loose** (say 20%, to clear the noisy tests) and the stable tests can rot silently — a real 10% regression on a 4%-noise benchmark sails through, which is exactly the slow death this module exists to stop.
- **Set it tight** (say 5%, to catch the stable tests) and the noisy tests cry wolf on every other build, the alerts get muted, and a muted gate defends nothing.

You can tune a threshold per benchmark, but now you own a table of hand-set numbers that drifts
out of date as benchmarks and hardware change, and that nobody re-derives. Fixed thresholds
force a choice between false negatives and false positives that no setting resolves, because
they compare two points and a two-point comparison cannot tell a level shift from noise.

## What works: change-point detection over the history

The fix is to stop comparing the newest run to the previous one and instead analyze the whole
time series. Keep every benchmark result over time and ask a different question: *has the level
of this series shifted at any point, by more than its own noise?* A regression is a sustained
change in the series, not a single slow run, and you can only see "sustained" by looking at the
run of values around a candidate point, not at one neighbor.

The industry-standard method is **E-Divisive means**: a nonparametric, hierarchical
change-point algorithm. Nonparametric because it assumes no distribution (benchmark series are
not normal — they are multimodal, drifting, heavy-tailed); hierarchical because it finds the
most significant change point, splits the series there, and recurses, so it locates multiple
shifts in a long history. The output is a list of change points with their locations and
magnitudes — a triage queue for humans, not an instant pass/fail.

This path is well trodden. MongoDB's Evergreen CI evolved through exactly the stages above —
manual inspection of graphs, then fixed thresholds, then E-Divisive change-point detection —
and reported that the move to change-point detection *dramatically* cut false positives while
catching regressions the thresholds missed. Production-grade implementations you can adopt
rather than write:

- **Hunter** (DataStax) — wraps E-Divisive and adds a Student's t-test on the two sides of each candidate point for determinism, and suppresses changes below a configurable size (e.g. <5%) so trivial shifts do not page anyone.
- **Apache Otava** — the maintained successor in the same lineage, change-point detection for benchmark series.
- **MongoDB `signal_processing_algorithms`** — the E-Divisive implementation behind Evergreen, usable standalone.
- **Conbench** (Voltron Data; used by Apache Arrow's benchmarking but *not* an Apache Software Foundation project, and largely unmaintained since ~2024) — a change-point-tracking dashboard that ingests benchmark runs over time and flags shifts. Treat it as a reference design rather than a live adoption target.

Change-point detection is the right model for a *history* you control and keep. It needs a
stored series and a human to triage the queue, which is its cost. For a single PR that must
pass or fail on its own merits before merge, you still want a per-run gate (below) — the two
compose: the gate blocks the egregious regression at the PR, the change-point detector catches
the slow drift the gate's noise margin had to let through.

## Controlling measurement noise on CI runners

Both approaches are only as good as the measurements feeding them, and CI is a hostile place to
measure. Shared CI runners are multi-tenant VMs with noisy neighbors, variable CPU frequency,
and no isolation; wall-clock variance on them routinely exceeds 30%. That noise floor sets a
hard limit: you cannot reliably detect a 10% regression through 30% run-to-run swing, no matter
how good the statistics. Drive the noise down first.

- **Compare PR vs base in the same run, on the same machine.** This is the single highest-leverage move. Build both the PR and its merge-base, benchmark them back-to-back on the same runner in the same job, and report the *relative* difference. Whatever that machine's quirks are this run — a slow neighbor, a throttled core — they hit both sides roughly equally and cancel in the ratio. Comparing the PR's absolute number to a historical absolute number, taken on a different machine on a different day, folds machine variance straight into your signal. (This is rule 1 of `../measure/measurement-integrity.md`, before/after the same way, applied to CI.)
- **Use dedicated or bare-metal runners.** Shared runners trade isolation for cost. A dedicated/bare-metal runner can cut variance from the >30% range down to a few percent, which is the difference between detecting a 5% regression and not. (Exact figures here are uncited; Bencher is primarily a metrics-tracking/threshold service, so verify whether it actually provisions isolated runners or just expects you to bring your own before relying on it for variance reduction.)
- **Warm up and repeat.** Discard warmup iterations and collect a distribution per run, not one number, so each side of the comparison has a confidence interval rather than a point (rules 2-3 of `../measure/measurement-integrity.md`). A regression is a separation between two CIs, not between two points.
- **Or sidestep wall-clock noise entirely** — see CodSpeed below. If you measure something deterministic instead of time, the runner's variance stops mattering.

Whatever you measure, pick the statistic that matches the headline: a median with its CI for
central per-op cost, the percentile with *its own* CI for a tail target. Banding a p99 gate
with a median's interval is a common and wrong shortcut (`../measure/measurement-integrity.md`,
rule 5).

## Tool reference

| Tool | What it gives you | Metric / basis |
|---|---|---|
| **Bencher** (bencher.dev) | Seven configurable statistical threshold tests — static, percentage, z-score, t-test, log-normal, IQR, delta IQR — that fail the build via an **Alert** when a metric crosses a computed boundary. Primarily a metrics-tracking/threshold service; confirm whether it provisions isolated runners before relying on it for variance reduction. | wall-clock (or any metric you feed it) |
| **CodSpeed** | Its instruction-count mode simulates the CPU under Valgrind/Callgrind, so each benchmark runs **once** and yields a deterministic metric that sidesteps wall-clock noise; it also now offers a wall-time/dedicated-runner instrument, so it is no longer instruction-count-only. Stable enough for relative regression detection on shared runners. Caveat: instruction count is not wall time — Callgrind *does* model a cache hierarchy with a static cost model, but it misses real hardware memory-stall *timing*, frequency scaling, and true concurrency, so it catches "we execute more instructions" and not "we wait longer." | instruction count (or wall time) |
| **cargo-criterion + critcmp** | Rust: Criterion records benchmark baselines; `critcmp` compares two saved baselines (e.g. base vs PR) and prints the deltas. The manual, in-repo version of the same-machine relative comparison. (This particular toolchain is only semi-maintained — treat the same-machine PR-vs-base *comparison* as the durable idea, not these specific tools.) | wall-clock |
| **Hunter / Apache Otava** | Change-point detection over a stored benchmark history (E-Divisive + t-test). Produces a triage list of shifts, not a pass/fail. | any series |
| **Conbench** | Change-point-tracking dashboard; ingests runs over time and surfaces shifts. | any series |
| **MongoDB `signal_processing_algorithms`** | The standalone E-Divisive library if you are building the detector yourself. | any series |

Bencher's threshold tests are the per-run gate; the change-point tools are the longitudinal
detector. Most mature setups run both. CodSpeed's instruction-count approach and the
dedicated-runner approach are two different answers to the same noise problem — determinism by
measuring something else, versus isolation by owning the machine; pick whichever your
workload's bottleneck is honestly captured by.

## The gate: what a confirmed regression does

A regression that survives the noise controls resolves into one of two actions, and they map to
the two detection modes:

- **Per-run threshold / Alert breach → fail the build.** A PR whose benchmarked metric crosses its component budget is blocked the same as a failing unit test. This is the enforcement arm of the budget table from `budgets-slos.md`: each row (component, metric @ percentile, owner) becomes a CI threshold, and the owner who breaks it owns the fix before merge.
- **Change point in the history → flag for triage.** The drift detectors produce a queue, not a block. A human looks at each flagged shift, confirms it against the noise, and either files it as a regression to fix or accepts it as an intended cost (a feature that legitimately costs more).

Tie both to the **error-budget policy** rather than treating every wobble as an emergency. A
small regression that keeps the component inside its budget spends error budget and is allowed;
a regression that pushes it past the budget, or a burn rate that will exhaust the budget before
the window closes, is what triggers the freeze from `budgets-slos.md` step 6. The CI gate
enforces the per-commit budget; the production burn-rate alert enforces the same number live.
The point of wiring CI to the budget is that the gate inherits a threshold anchored in a real
consequence, instead of an arbitrary percentage someone picked.

A note on what to benchmark in CI: the same caution from `../measure/measurement-integrity.md`
rule 8 applies. A microbenchmark gate defends a microbenchmark; a 3x regression in a function
that is 1% of the request is a 0.3% regression to the system. Gate the metrics that sit on the
budget's critical path, and confirm CI wins in a macrobenchmark before believing them.

## Continuous profiling: the complementary always-on signal

CI regression testing is event-driven — it fires on a commit. The complementary signal is
**continuous profiling**: always-on, low-overhead sampling of where the code spends its cycles,
running in production and CI alike, so you can diff "where did the time go" between two
releases instead of only "did the headline number move." It catches the regression CI's curated
benchmarks never exercised, because it profiles real traffic.

This module does not re-cover the profilers. The tool detail (Parca, Pyroscope, Google-Wide
Profiling, eBPF fleet profilers) lives with the environments that run them:
`../environment/prod-distributed.md` for the fleet/production side and
`../environment/linux.md` for the host-level mechanism. The eBPF-based fleet profilers are
Linux-only; if you are profiling locally on macOS / Apple Silicon, see
`../environment/local-mac.md` for the Instruments-based equivalent. Treat continuous profiling
as the production complement to the CI gate, and go there for how to stand it up.

---

## Worked example: gating a checkout service

Take the checkout path from `budgets-slos.md`: the orchestrator owns 15 ms @ p99.9, the payment
step 50 ms @ p99 with a 10% retry budget. Turn those rows into a defense in two layers.

**Per-run gate (blocks the PR).** On every PR, the CI job checks out the merge-base and the PR head, builds both, and runs the checkout benchmark suite on the same dedicated runner, interleaved, 50 reps each after warmup. It computes the p99 of each side with a quantile CI and reports the relative shift. A Bencher threshold (t-test on the two distributions) fails the build when the PR's orchestrator p99.9 separates upward from base by more than the run's noise — and hard-fails outright if the absolute number crosses the 15 ms budget. The PR author sees "orchestrator p99.9 +18%, budget breached" next to the failing unit tests and owns it before merge. Because both sides ran on the same machine in the same job, the runner being slow today moved both numbers together and cancelled out.

**Longitudinal detector (catches the drift the gate let through).** The noise margin on the per-run gate has to allow, say, 6% so it does not cry wolf, which means a string of +3% commits each pass individually. Every merged run's p99 is appended to a stored series; nightly, Hunter runs E-Divisive over it. A series of discrete small step-ups (each a commit that nudged the level) registers as one or more change points — e.g. "orchestrator p99.9 stepped from 12 ms to 15.5 ms around 2026-06-09" — and lands in a triage queue. (Mind the limit: E-Divisive resolves *level shifts*, so a perfectly smooth linear creep with no step is its weak spot and may surface as a fuzzy cluster of small points rather than one clean before/after.) A human confirms it against the series, sees it crossed the budget, and files the regression with the offending commit range already identified.

**Tied to the budget.** A +4% shift that keeps the orchestrator at 12.5 ms, well inside 15 ms, spends a sliver of error budget and ships. The shift that pushes it to 15.5 ms past the budget is what the gate blocks and the detector flags; if it had reached production, the same number drives the burn-rate alert and, if the budget exhausts, the feature freeze. One number — the budget row — enforced at the PR, in the history, and in prod.

---

## Pitfalls / over-engineering signals

- **One threshold for every benchmark.** The failure this whole module opens with. Per-benchmark noise differs by 5x; one number cannot fit it.
- **Comparing against historical absolutes across machines.** Folds machine variance into the signal. Compare PR vs base on one machine in one run.
- **Gating on a noise floor you never measured.** If the runner swings 30%, a 10% gate is theatre. Measure the noise first, then set a gate above it — or move to dedicated/deterministic measurement so the gate can be tight.
- **Treating every change point as an incident.** The detector produces a triage queue. Suppress sub-threshold shifts (Hunter's <5% rule) and route the rest through the error budget, not a pager.
- **Banding a tail gate with a central-tendency CI.** A p99 gate needs a p99 CI; the median's interval is far too narrow and will pass real tail regressions (`../measure/measurement-integrity.md` rule 5).
- **Gating microbenchmarks off the critical path.** A green/red light on a metric that is 1% of the request defends 1% of the system. Gate what is on the budget.

---

## Where next

| When you need to… | Go to |
|---|---|
| set the budget this gate enforces, and the error-budget freeze policy | `budgets-slos.md` |
| diagnose a regression that is *already live* in production (not prevent one in CI) | `../diagnose/regression-incident.md` |
| make each measurement honest (noise, the right statistic, before/after) | `../measure/measurement-integrity.md` |
| set up the underlying benchmark (regime, sourcing, harness) | `../measure/benchmark.md` |
| pick the profiler or load generator the gate runs | `../measure/tools.md` |
| stand up always-on continuous profiling in prod/fleet | `../environment/prod-distributed.md` (and `../environment/linux.md` for the host mechanism) |
