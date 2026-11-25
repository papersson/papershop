# Fair benchmarking & A/B comparison

**Status:** READY
**Loaded when:** comparing alternatives or measuring whether a change actually helped.

This is the **measure** step of the SKILL.md loop (target → **measure** → locate → fix → prove → defend), used two ways: to compare candidates before you commit (A vs B), and to confirm a change moved the number it was supposed to. The core rule is one sentence: **the thing under test never times itself, and no number ships without a stated uncertainty and a passed correctness gate.** A faster-but-wrong implementation is not faster; a point estimate with no confidence interval is not a result.

The runnable engine for all of this is the harness in `harness/`. Read its `harness/README.md` for the shape and `harness/METHODOLOGY.md` for the evidence behind each rule. This leaf is the operator's guide to that engine: the contracts you plug into, which regime to measure in, how to make the A/B fair, and which statistics are honest. The discipline of *not fooling yourself* (tails, noise, coordinated omission, why microbenchmarks lie) lives next door in `measurement-integrity.md`; the catalog of ready-made tools lives in `tools.md`.

---

## The engine: a four-stage spine talking through plain data

Every fair benchmark is the same pipeline. Each stage reads only the previous stage's output, so any one can be swapped without touching the others.

```
   probe  ──prepare/invoke──▶  runner  ──raw_samples──▶  aggregator  ──stats──▶  reporter
(target-specific,             (owns the clock,          (median + bootstrap     (plots, tables)
 the ONLY code you            warmup, batch             confidence interval)
 write per target)            calibration,
                              correctness gate)
```

| Stage | File | Reads | Writes |
|---|---|---|---|
| probe | `harness/experiments/*/target.py` | params | a fixture + output |
| runner | `harness/src/harness/core.py` | probes + param grid | `raw_samples.json` |
| aggregator | `harness/src/harness/stats.py` | raw samples | `stats.json` |
| reporter | `harness/src/harness/report.py` | stats | `scaling.png`, table |

The only target-specific contract is a **`Probe`**: a `name`, a `prepare(params) -> fixture` (untimed setup), and an `invoke(fixture) -> output` (the timed work). Setup that you do not want counted goes in `prepare`; the cost you are measuring goes in `invoke`. For an approximate target add `quality(output, fixture) -> float`. To add a new target you write only the probe — the three spine files stay byte-for-byte identical (this is the harness's load-bearing invariant; editing the spine to make one target work is itself a finding, not a casual edit).

Two data contracts carry everything downstream:

- **Raw-sample schema** (one dict per measurement): `probe`, `params`, `rep`, `batch`, `seconds_per_op`. Optional additive channels carry non-time metrics (`metric`/`unit`/`value`), provenance (`clock`/`includes_startup`/`overhead_removed`), and ratios (`numerator`/`denominator`). Because the schema is unit-agnostic, an in-process loop, a `hyperfine` run, and a `vegeta` run all emit the same shape and feed the same aggregator.
- **Summary schema** (one dict per `(probe, params)` group): `n`, `min`, `median`, `mean`, `stdev`, `p90`, `p99`, `ci_low`/`ci_high` (95% bootstrap CI for the median), `p90_ci_*`/`p99_ci_*` (tail CIs), plus the carried provenance. The reporter reads only this; it never reaches back into the runner.

---

## Procedure: run a fair A/B

1. **State the decision and the headline metric.** What does this A/B decide, and in what unit? Per-op CPU seconds, whole-invocation seconds including startup, or per-request latency under an arrival rate are three different headlines that pick three different regimes. Write it down before measuring; it gates everything below. No target/decision → back to the gate in SKILL.md.
2. **Run the metric-type gate (Q0).** Is the headline *time-per-unit in seconds*? If yes, continue. If it is peak RSS, allocations/op, or joules, do **not** stuff it into `seconds_per_op` — tag it (`metric`+`unit`+`value`) and use a metric-appropriate collector. If the headline is a *ratio of totals* (throughput req/s, bytes/s, hit-rate, error-rate), route it to the ratio estimator, not the scalar median path. See "honest statistics" below.
3. **Pick the regime** (library / CLI / service — table below). The regime is the timing machinery; the spine is shared.
4. **Decide wrap vs build** (rule below). For anything on a JIT/AOT runtime, or any CLI or load test, wrap the standard tool from `tools.md`; do not hand-roll the hard parts.
5. **Write the probe(s)/adapter** — one per candidate in the A/B, sharing one `param_grid` so A and B see identical inputs. Put untimed setup in `prepare`, the measured work in `invoke`.
6. **Let the runner measure.** It owns the clock, calibrates the batch, discards warmup, runs reps in randomized interleaved order, and enforces the correctness gate across the candidates (the five fairness controls below).
7. **Aggregate honestly.** Median + bootstrap CI for a central headline; the tail-CI rule for a percentile headline; ratio-of-totals for a rate headline.
8. **Read the verdict from the CIs, not the point estimates.** A is faster than B only if their intervals separate. Overlapping CIs mean "no difference shown at this n" — gather more samples or accept the tie. Then prove the change end to end in `verify.md`.

---

## Pick the regime

Different targets need different timing machinery. Select per target; the spine absorbs all three.

| Regime | Targets | Timing machinery | Headline unit |
|---|---|---|---|
| **Library / in-process** | functions, methods, pure compute | calibrated in-process loop (`core.py`) | per-op seconds |
| **CLI / subprocess** | command-line tools | process wall-clock, startup-aware (wrap `hyperfine`) | per-invocation seconds (incl. startup) |
| **Service / load** | servers, endpoints | open-loop generator + arrival schedule (wrap `vegeta`/`k6`/`wrk2`) | per-request latency/tail under a rate |

How to decide when surfaces overlap (a function that also makes a network call could be measured three ways):

- **Access surface.** In-process call → library candidate. One-shot process you spawn and wait on → CLI candidate. Network/RPC to a long-lived or request-triggered remote → service candidate.
- **Library-vs-IO test.** If `invoke()` blocks on an fd or cross-process syscall whose wait dominates (including async-awaiting-IO), it is not a library benchmark — route it to the IO/service path (open-loop, unit=request, batch=1). Only on-CPU compute stays library.
- **Headline decides ties.** When surfaces co-fire, pick the regime whose measured unit *equals the headline unit* you wrote in step 1. Per-op on-CPU cost → library; whole-invocation cost including interpreter/process startup → CLI; per-request latency under a rate → service. This is the decider, not a tiebreak.
- **Fast-op sub-select (library only).** One op faster than ~5 ms → calibrate an inner batch `N` and report `elapsed/N` (the `core.py` path). Slower → batch=1. CLI is always batch=1; there the ~5 ms figure instead decides whether to run `hyperfine --shell=none`/`-N` so shell-spawn does not dominate.

---

## Wrap vs build

You almost always wrap. Build your own loop only in the narrow corner where nothing hard is in play.

- **Wrap if the runtime is JIT/AOT** (JVM, CLR, V8, PyPy, Numba, JAX, optimized native Rust/C++/Go/Swift). A real optimizer barrier (`black_box`/`DoNotOptimize`/`Blackhole`), warmup, and steady-state detection are mandatory and not safely hand-rollable. Wrap the ecosystem-standard framework (Criterion, JMH, Google Benchmark, `testing.B`+benchstat).
- **Wrap if the regime is CLI** → `hyperfine`. It owns shell-spawn calibration and subtraction, run-count and time budget, warmup, `--prepare` cache hygiene, and peak-RSS. Caveat: it does not interleave between commands, so drive it round-robin per run and force `--runs 20–40` so the bootstrap has enough samples — its default is a *minimum* of 10 (`--min-runs 10`), auto-growing more for fast commands within a ~3 s budget rather than fixing the count, so pinning a higher floor is what guarantees the sample size.
- **Wrap if the regime is service/load** → an open-loop generator (`vegeta`, `k6` arrival-rate, `wrk2`). Coordinated-omission correction, HdrHistogram tail accuracy, and high-rate scheduling are not safely hand-rollable. Plain `wrk` is fine for throughput but never for a latency-tail headline.
- **Build your own only when all hold:** regime is library, runtime is no-JIT (CPython, Lua 5.x, Ruby MRI), headline is per-op CPU seconds, and none of {optimizer barrier, coordinated omission, HdrHistogram, high-rate scheduling} apply. Then `core.py`'s calibrated loop suffices and adds the bootstrap median CI that `timeit`/`pytest-benchmark` omit.
- **Always own the spine.** External tools are sample *sources* upstream of `raw_samples`; CI dashboards (Bencher, Conbench) are exporters *downstream* of `stats`. Neither replaces the schema or the aggregator. Full tool-by-tool detail: `tools.md`.

---

## Fair A/B: the five controls the runner enforces

Each control names the unfairness it prevents. These are what make an A/B a comparison rather than two anecdotes.

1. **The runner owns the clock.** The target never times itself, so it cannot report a number that flatters itself or quietly omits cost. Every candidate is timed by the same external clock.
2. **Batch calibration.** A fast op is run in a calibrated inner batch sized to clear the timer's resolution, then divided back out. This lifts the measurement above clock granularity so the number reflects the op, not the timer. `min_batch_time` is load-bearing: calibration auto-grows `N` past the per-batch-overhead knee into the linear regime, which is the only reason `elapsed/N` is honest at small ops.
3. **A correctness gate.** Candidates that disagree on output for the same input are refused before any timing — you cannot accidentally crown a fast-but-wrong implementation. For approximate targets (ANN at a recall target, a lossy codec at PSNR/SSIM, a randomized or LLM output), supply `quality()` and a `min_quality` bar instead of bit-equality.
4. **Warmup discarded.** The first runs (cold caches, page faults, first-call setup, JIT tier-up) are thrown away so they do not pollute the steady-state estimate.
5. **Randomized, interleaved repetitions.** Reps run in shuffled order across candidates, so system drift during the run (thermal, scheduler, neighbors) is shared equally across A and B instead of dumped on whichever ran last. Naive "run all of A, then all of B" hands the second one a different machine.

The aggregator adds two pooling guards so the controls cannot be silently defeated: it refuses to pool a group whose samples disagree on `(unit, clock, includes_startup, overhead_removed)`, and it refuses a group that mixes `batch` sizes. Both turn a silently-meaningless average into a hard error.

---

## Honest statistics

Pick the estimator from the headline's shape. The wrong estimator produces a confident, wrong number.

- **Central-tendency headline → median + bootstrap CI.** Report the median banded by a 95% percentile bootstrap CI (no normality assumption). The median keeps one scheduler hiccup from dragging the headline the way a mean would; the bootstrap states the uncertainty a bare point estimate hides. `min` is often the cleanest estimate of true cost when you want the noise floor.
- **Tail headline → the tail-CI rule.** When the contract is p90/p99/p99.9, band *that* statistic with its own quantile bootstrap (`bootstrap_ci_quantile`), never the median's CI. A median CI contains the true p99 in ~0% of trials and is tens of times too narrow; printing a p99 next to a median CI is a lie. On live service data the p99 CI ran hundreds of times wider than the median CI — that width is real, not a defect.
- **Throughput / rate headline → ratio-of-totals.** Throughput, hit-rate, error-rate, and utilization are `sum(numerator)/sum(denominator)`, not a central tendency of per-window rates. Estimate `sum(num)/sum(den)` with a *paired* bootstrap that resamples `(num, den)` pairs and recomputes the ratio (`ratio_of_totals_ci`). The naive median-of-rates was measured at ~459% relative error with near-zero CI coverage; the paired estimator recovered it to ~4.7% with a covering interval.
- **Read the A/B from interval separation.** Disjoint CIs at every param point = a real difference (the `rg`-vs-`grep` crossover separates cleanly at every size). Overlapping CIs = no difference shown at this `n`; do not call it. This is the entire statistical content of "A is faster than B."

One precondition the bootstrap quietly assumes: **exchangeable samples.** Under strong serial correlation (GC/JIT warmup trajectories, thermal drift, LSM compaction) the i.i.d. bootstrap under-covers (coverage fell from 0.96 to 0.40 at ρ=0.9). Randomized interleaving helps break that structure; a genuinely state-dependent trajectory needs a block bootstrap or an effective-sample-size warning. This is the seam where benchmarking hands off to `measurement-integrity.md`.

---

## Pitfalls / over-engineering signals

Benchmarking invites cargo-culting because the machinery looks rigorous even when the question is wrong. Watch for:

- **Measuring the wrong regime for the headline.** Microbenchmarking a function in-process when the decision is about per-request tail under load gives a precise answer to a question nobody asked. Let the headline unit pick the regime.
- **Comparing point estimates.** "A: 1.21 ms, B: 1.24 ms, A wins." Without CIs that is noise. If the intervals overlap there is no result yet.
- **Forcing a non-time metric into `seconds_per_op`.** Reporting "median 275,808,904 seconds" because the value was actually bytes. Tag the unit; route ratios to the ratio estimator.
- **Hand-rolling on a JIT/AOT runtime.** A loop without an optimizer barrier measures the dead-code eliminator. Wrap the standard framework.
- **Closed-loop load generation for a tail headline.** A client that stalls when the server stalls never sends the would-be-slow requests, so the tail is under-sampled (coordinated omission). Use an open-loop generator. Detail in `measurement-integrity.md`.
- **Building a harness when a wrapped tool exists.** The spine is worth owning; the timing loop usually is not. Build only in the no-JIT/library/per-op-seconds corner.

The default is to wrap a battle-tested tool, plug it into the four contracts, and let the aggregator and its guards do the honest part. Complexity beyond that is earned by a number, not assumed.

---

## Worked examples

**Library A/B (membership).** Question: which container is fastest for membership tests, and how does it scale? Headline: per-op seconds (Q0 passes), in-process call with on-CPU work → library + build (`core.py`). Three probes (list, set, dict) over one param grid of sizes 100–100,000. The runner calibrated a batch per point, discarded warmup, interleaved reps, and ran the correctness gate (all three agree on the boolean result) before timing. Verdict from the CIs: list is a clean straight line on the log-log plot (O(n)); set and dict are flat (O(1)). The shape, not just the winner, fell straight out of the median+CI curve.

**CLI A/B (`rg` vs `grep`).** Question: which counts matches faster, and where does the crossover sit? Headline includes process startup → CLI + wrap `hyperfine`, `--runs 20–40`, round-robin between the two commands. The adapter mapped `hyperfine`'s per-command `times[]` into the raw-sample schema (batch=1, one sample per run); the unchanged aggregator and reporter did the rest. Verdict: `grep` wins where startup dominates (2k lines: 1.29 ms vs 2.50 ms), `rg` wins decisively once work dominates (1M lines: 10.06 ms vs 99.76 ms, ~10x), crossover near 20k lines, and the CIs separate cleanly at every size — so each verdict is real, not noise. The correctness gate ran the real subprocesses and confirmed identical match counts before any timing.

**Service A/B (endpoint tail).** Question: does the endpoint hold its p99 under load? Headline is per-request tail under an arrival rate → service + wrap `vegeta`, open-loop at 100/200/300 req/s. The adapter emitted one sample per request (batch=1); the aggregator returned a populated p99 with its own quantile CI natively. With a heavy-tailed delay the p99/median ran 14–16x and the p99-CI width came out hundreds of times the median-CI width — exactly the tail-CI rule earning its keep on live data. Two gates ran: every request returned HTTP 200 with zero transport errors, and a validity gate independently recomputed median/p99/median-CI and byte-matched the aggregator.

---

## Where next

| When you… | Go to |
|---|---|
| need the runnable engine (source, schemas, how to add an experiment) | `harness/` (README + METHODOLOGY) |
| need the don't-fool-yourself discipline (tails, noise, coordinated omission, why microbenchmarks lie) | `measurement-integrity.md` |
| are choosing a concrete tool (hyperfine, Criterion, JMH, Google Benchmark, pytest-benchmark) | `tools.md` |
| have a benchmark and need to prove the change won AND stayed correct | `verify.md` |
| are still locating the bottleneck, not yet comparing fixes | `../diagnose/index.md` |
| want the win confirmed against the original target | back to the gate in `../../SKILL.md` |
