# Working theory: how to build performance-evaluation harnesses

> This file is the current best understanding. It is meant to be folded into
> every future research iteration as a "build on this, do not re-derive" prefix.
> It changes only when an experiment confirms or refutes a claim (see CLAIMS.md).

## Goal

Produce *transferable knowledge* of the form: "given an arbitrary target, here is
how to evaluate its performance fairly." The harness is both the output and the
instrument of inquiry. We are doing empirical methodology development, not
building one benchmark.

## The two loops

- **Object loop:** build a harness, run an experiment, get a number.
- **Meta loop:** observe the result, decide what it implies for *how to build
  harnesses*, generate the next question, decide when we are done.

Experiments are instruments of the meta loop. Their job is to attack the
falsifiable claims below, not to produce numbers for their own sake.

## Architecture so far: a shared spine + swappable regimes

Four stages, each talking to the next only through plain data, so any stage can
be replaced without touching the others.

```
   probe/adapter ──▶ runner ──raw_samples──▶ aggregator ──stats──▶ reporter
  (target-specific)  (owns clock,           (median + bootstrap   (plots, tables)
                      warmup, calibration,    confidence interval)
                      correctness gate)
```

- The **raw-sample schema** is the load-bearing contract. Everything downstream
  depends on it, not on how the measurement was produced.
- The only target-specific code is the probe/adapter.

### Measurement regimes

Different targets need different timing machinery. The spine is shared; the
regime is selected per target.

| Regime | Targets | Timing machinery | Status |
| --- | --- | --- | --- |
| Library / in-process | functions, methods | calibrated in-process loop | **confirmed** (membership exp) |
| CLI / subprocess | command-line tools | process wall-clock, startup-aware (wrap hyperfine) | **confirmed** (rg vs grep, Iteration 2) |
| Service / load | servers, endpoints | open-loop load generator + arrival schedule (wrap vegeta) | **confirmed** (HTTP endpoint, Iteration 5) |

## Fairness principles (regime-independent)

- The target never times itself; the runner owns the clock and loop.
- Batch calibration lifts fast ops above timer resolution.
- A correctness gate refuses to compare implementations that disagree on output.
- Warmup is discarded; repetitions run in randomized, interleaved order.
- Robust statistics: median with a bootstrap confidence interval, no normality
  assumption.

## Two open strategic ideas (to be tested, not assumed)

1. **Normalization-layer hypothesis — CONFIRMED (C3).** The generalizable value
   is the *unifying layer*, not the measurement loop. Iteration 2 mapped
   hyperfine's per-command `times[]` array into the unchanged raw-sample schema;
   the samples passed through `aggregate()` and the reporter untouched and
   produced valid artifacts. An external tool is a sample *source* upstream of
   `raw_samples`; the schema absorbs the wall-clock-vs-in-process difference. The
   spine owns the contract; the measurer is swappable.

2. **Build-vs-buy — STANCE TAKEN (C4).** Writing measurement code is cheap;
   getting it *statistically correct* is not (shell-spawn calibration, warmup
   discipline, optimizer barriers, coordinated-omission correction, HdrHistogram
   tails are what mature tools encode). The stance: **wrap** whenever any of
   those hard parts is in play (JIT/AOT runtime, CLI, or load regime), and
   **build** only when the target is LIBRARY + a no-JIT runtime (CPython/Lua/MRI)
   + a per-op-time-in-seconds headline + none of the hard parts present. We
   **always own the spine** regardless: external benchmark tools are sample
   sources upstream of `raw_samples`; CI services (Bencher, Conbench) are
   exporters downstream of `stats`; neither replaces the schema or the aggregator.

## Decision framework: REGIME-AND-SOURCING (R&S)

A decidable regime selector plus a wrap/build selector. Run the gate first, then
the five questions, then the sourcing rule. The framework returns the same
verdict for the two targets we have actually run: membership → LIBRARY + BUILD
(core.py); rg-vs-grep → CLI + WRAP hyperfine.

### Q0 — Metric-type gate (run first, record the answer)

What is the headline metric and unit? If it is **time-per-unit in seconds**,
proceed. If it is peak RSS, allocations/op, energy (joules), or bytes/sec
throughput, you may **not** force it into `seconds_per_op`: either tag the sample
with extended provenance (`metric` + `unit` + `value`) and use a
metric-appropriate collector (`-prof gc`, `/usr/bin/time -l`, `perf`,
`powermetrics`), or declare the target out of scope. **Status: now ENFORCED in
code (Iteration 7, claim PROVENANCE `confirmed`).** Iteration 4
(`experiments/mem_metric`, claim NONTIME-METRIC `refuted`) first proved the spine
ignored Q0: `aggregate()` read only `seconds_per_op` (then at stats.py:97), so an
honest peak-RSS-in-bytes sample `KeyError`ed and the only spine-free path silently
mislabeled bytes as seconds. Iteration 7 closed this with the PROVENANCE evolution
below: `aggregate()` now reads a metric-neutral `value` channel (falling back to
`seconds_per_op` for legacy samples), refuses to pool a group disagreeing on
`(unit, clock, includes_startup, overhead_removed)`, and carries those fields into
each summary — so a `unit=bytes` sample flows through labelled bytes, and the
units-lie is a hard `ValueError`. **Second caveat (Iter 9): a `bytes/sec` or
`req/s` throughput is a RATIO-OF-TOTALS, not just a non-time unit.** Tagging it
`unit=req_per_s` is necessary but NOT sufficient — provenance labels the `value`
channel but the denominator lives outside it, so the spine still computes a biased
median-of-rates with a mis-covering CI (RATIO-METRIC-ESTIMATOR `confirmed`). Q0
must additionally ask "is the headline a ratio of totals?" and, if so, route it to
a ratio estimator (paired bootstrap) rather than the scalar median path.

### Regime selector (Q1–Q5)

- **Q1 — Access surface (branches may co-fire).** (a) in-process call → LIBRARY
  candidate; (b) one-shot process you spawn and wait for → CLI candidate;
  (c) network/RPC to a long-lived or request-triggered remote → SERVICE
  candidate; (d) stateful request/response over stdio to a persistent child
  (LSP/REPL) → SERVICE-stdio sub-case. Record every branch that is true.
- **Q2 — Library-vs-IO test (any (a) candidate).** Does `invoke()` block on an fd
  or cross-process syscall whose wait dominates? YES → route out of LIBRARY into
  the IO/SERVICE path (open-loop, unit=request, batch=1); async-awaiting-IO calls
  go here too. NO (compute stays on-CPU) → stays LIBRARY.
- **Q3 — Headline decider (MANDATORY when surfaces co-fire; this is the decider,
  not a tiebreak).** Pick the regime whose measured unit equals the headline
  unit: per-op on-CPU cost → LIBRARY; whole-invocation cost incl. process/
  interpreter startup → CLI; per-request latency/tail under an arrival rate →
  SERVICE.
- **Q4 — Measurement-strategy sub-select (does NOT change the regime).** Is one
  op faster than ~5 ms? LIBRARY+fast → calibrate an inner batch N to a minimum
  batch time, report `elapsed/N` (core.py path); LIBRARY+slow → batch=1. CLI →
  always batch=1; here the ~5 ms figure instead selects whether to run hyperfine
  with `-N`/`--shell=none` so the number isn't dominated by shell-spawn
  calibration. **`min_batch_time` is load-bearing, not cosmetic (Iter 10,
  NONLINEAR-BATCH-AMORTIZATION `partial`):** `elapsed/N` is NOT batch-invariant for
  an overhead-dominated op — at a small fixed batch the per-op number is a function
  of N, not of the operation (a ~0.1µs op reads 125ns at B=1 vs 34.2ns at B=16384,
  3.66x, disjoint CIs). The `elapsed/N` headline is honest only because
  `min_batch_time` calibration auto-grows N past the per-batch-overhead knee into
  the linear regime, where it then becomes batch-stable (across `min_batch_time` ∈
  {0.0002…0.2} the calibrated headline moves <1.1x). So do NOT shrink
  `min_batch_time` to save time, and do NOT trust a fixed/uncalibrated batch=1
  per-op number for a sub-microsecond op — both report an N-artifact. An op whose
  per-op cost already dwarfs per-batch overhead (a memory-bandwidth sum here) is
  flat in N regardless.
- **Q5 — Runtime optimizer-barrier lookup (keyed on the *runtime*, not the source
  language — record it).** No-JIT interpreters (CPython, Lua 5.x, Ruby MRI) → a
  liveness sink (core.py `_SINK`) is adequate and a hand-rolled loop is allowed
  (note: `_SINK` is a liveness sink, not a true optimizer barrier). JIT/AOT
  runtimes (JVM, CLR, V8, PyPy, Numba, JAX, LuaJIT, native Rust/C++/Swift/Go with
  optimization) → a real optimizer barrier (`black_box`/`DoNotOptimize`/
  `Blackhole`) plus warmup and steady-state detection are MANDATORY and not
  safely hand-rollable; this forces WRAP.

### Sourcing rule (wrap vs build)

- **WRAP** if the runtime is JIT/AOT (barrier + warmup + steady-state can't be
  hand-rolled): wrap the ecosystem-standard in-process framework.
- **WRAP** if the regime is CLI: wrap **hyperfine** (it owns shell-spawn
  calibration+subtraction, auto run-count/time-budget, warmup/`--prepare` cache
  hygiene, peak-RSS, `--output` control). Constraint: hyperfine does **not**
  interleave between commands — drive it round-robin per run and force
  `--runs 20–40` (never the default 10) so the bootstrap has enough samples.
- **WRAP** if the regime is SERVICE/load: wrap an open-loop generator (vegeta,
  k6 arrival-rate, wrk2). Coordinated-omission correction, HdrHistogram tail
  accuracy, and high-rate scheduling aren't safely hand-rollable. Plain wrk only
  for throughput, never for a latency-tail headline. **Confirmed Iter 5:** vegeta
  in open-loop constant-rate mode, encoded to per-request JSON, maps probe-only
  into the schema; the per-request latency headline lands directly in the tail-CI
  machinery the spine already carries.
- **WRAP** if a language has a de-facto standard microbench framework and
  comparability to published numbers matters (Criterion, Google Benchmark, JMH,
  BenchmarkDotNet, testing.B+benchstat).
- **BUILD our own ONLY when ALL hold:** regime is LIBRARY + runtime is no-JIT +
  headline is per-op CPU time in seconds + none of the hard parts (optimizer
  barrier, CO-correction, HdrHistogram, high-rate scheduling) are in play. Then
  core.py's calibrated loop suffices and additionally yields the bootstrap median
  CI that timeit / pytest-benchmark omit.
- **EXCEPTION — BUILD a thin driver** for SERVICE-stdio (LSP/REPL over stdio): no
  off-the-shelf open-loop tool speaks the framing. Build only the request/
  timestamp driver; reuse the spine and tail-CI aggregator unchanged.
- **ALWAYS BUILD/OWN the spine:** the raw-sample schema, `aggregate()`, the
  bootstrap CIs, the reporter. External tools are sources upstream of
  `raw_samples`; CI services (Bencher, Conbench) are exporters downstream of
  `stats`. Neither replaces the schema or the aggregator.

### Invariants that make wrapping safe (the C3 normalization layer)

Extend the raw-sample schema with provenance: `{..., metric, unit(op|invocation|
request), clock(wall|cpu), includes_startup:bool, overhead_removed:bool}`.
`aggregate()` must **refuse** to pool samples within a `(probe,params)` group that
disagree on `(unit, clock, includes_startup, overhead_removed)`; `report.py` must
**refuse** to co-plot lines that disagree on these. This turns the old
cross-regime fairness *warning* into an enforced *invariant*. **Now in code
(Iteration 7, PROVENANCE `confirmed`):** `stats.aggregate()` reads a metric-neutral
`value` channel (legacy samples fall back to `seconds_per_op`), raises `ValueError`
on a `(probe,params)` group with disagreeing `(unit, clock, includes_startup,
overhead_removed)`, and carries the five provenance fields into each summary as new
keys only; `report.plot_scaling` refuses to co-plot mismatched units (legacy
unit-less rows render exactly as before). The change is additive — every
pre-existing summary field re-aggregates byte-identically across membership,
cli_search, and service_regime, so C1 is preserved (`back_compat_diff.json` empty).
Two more rules:
**batch-homogeneity** before bootstrapping (all samples in a group share a batch,
or fit a slope across heterogeneous iters as Criterion needs) — **this rule is
stated here but NOT yet enforced in code (Iter 8, BATCH-HOMOGENEITY `refuted`).**
`_POOL_KEYS = ("unit","clock","includes_startup","overhead_removed")` guards
provenance but omits `batch`; `aggregate()` never reads `s["batch"]`, so a
`(probe,params)` group mixing batch=1 and batch=1000 is silently pooled into one
summary (`experiments/batch_homogeneity`: `pooled_n=120`, no ValueError). The harm
is a CI that misrepresents both cohorts — pooled median-CI width 2.30e-08 falls
between the homogeneous fine (1.44e-08) and coarse (2.65e-07) baselines, too narrow
for the noisy cohort yet polluted by it, with n=120 the only tell. The Iter-7
provenance guard correctly fires on a unit mismatch in the same test, isolating
`batch` as the one unguarded dimension. Closing it is queued, sanctioned spine
evolution: add a batch-homogeneity check to `aggregate()` parallel to `_POOL_KEYS`
(refuse a mixed-batch group, or slope-fit across iters Criterion-style), designed
like the tail-CI rule. And the
**tail-CI** rule (when the headline is p90/p99/p99.9, band and label the CI of
*that* statistic via `bootstrap_ci_quantile` — stop printing a tail percentile
next to a CI labelled "for median"). **Now in code (Iteration 3, C2-tail):**
`stats.bootstrap_ci_quantile(xs, q)` exists, `aggregate()` emits `p90_ci_*` /
`p99_ci_*`, and `report.format_table` bands the p99 with its own CI. The empirical
justification (`experiments/tail_ci`): a median bootstrap CI contains the true p99
0% of the time and is 23–40× narrower than the true p99 sampling spread, so using
it as a tail band is actively misleading; a quantile CI restores ~95% coverage.

**Serial-dependence caveat on every bootstrap CI (Iter 6, IID-BOOTSTRAP `partial`).**
Both `bootstrap_ci_median` and `bootstrap_ci_quantile` resample raw samples
**i.i.d.** (uniform indices with replacement). That assumes the per-op samples are
exchangeable. They are not when the op is a *trajectory* — state-dependent cost
from GC/JIT warmup, cache/thermal drift, or LSM compaction makes consecutive
samples correlated. `experiments/iid_bootstrap` fed stationary AR(1) lognormal
samples (true median = BASE = 1e-6) through the unmodified `aggregate()`: at ρ=0
the median CI covers correctly (0.957), but coverage collapses with autocorrelation
(0.657 at ρ=0.7, 0.397 at ρ=0.9) because the i.i.d. CI is too narrow (≈0.26× the
true between-experiment spread at ρ=0.9). A moving-block bootstrap (block length
≈ n^(1/3), defined only in the experiment) improves coverage everywhere
(0.40→0.79 at ρ=0.9, 0.66→0.92 at ρ=0.7) but UNDER-corrects at the strongest
dependence (0.787 < 0.95 at ρ=0.9). **Practical rule:** the median+bootstrap
default is honest only for exchangeable samples; randomized/interleaved rep order
(already a fairness principle) helps break serial structure, but for genuinely
state-dependent trajectories the CI needs a block bootstrap (with block length and
n tuned to the correlation length) or an autocorrelation/effective-sample-size
warning. This is queued spine evolution, not yet in code.

**Ratio-of-totals caveat: the denominator is structurally invisible (Iter 9,
RATIO-METRIC-ESTIMATOR `confirmed`).** When the headline is a *ratio of totals* —
throughput (req/s, bytes/s), cache hit-rate, error-rate, utilization — the true
value is `sum(num_i)/sum(den_i)`, NOT a central tendency of per-window rates. The
schema has a single scalar `value` slot, so the only way to record a ratio metric
is `value = rate_i = num_i/den_i`; the denominator rides outside the channel and
`_POOL_KEYS` never inspects it. Feeding per-window rates through the unmodified
`aggregate()` is then wrong in BOTH point and interval: with varying denominators
the median/mean of rates is biased (Jensen / harmonic-vs-arithmetic — short
high-rate windows dominate the unweighted center), and the median's i.i.d.
bootstrap CI is computed over the wrong estimand. `experiments/ratio_metric` fed
a congestion-shaped synthetic dataset (many short fast windows + few long slow
windows, true R*=181.82 req/s) through the spine: median-of-rates bias 424%, and
the spine median-CI covered R* in **0.000** of 300 trials. A ratio-of-totals point
estimate with a **paired (num_i,den_i) resample bootstrap** (resample window
indices, recompute `sum(num)/sum(den)` per resample) recovers 0.983 coverage.
**This is a units-lie-grade SILENT error one level below PROVENANCE: provenance
cannot catch it because num and den are not in the `value` channel that the unit
tag describes.** Practical rule: a ratio-of-totals headline must NOT be reduced
to median/mean of per-window rates. The fix is a denominator/weight channel plus
a ratio estimator (queued spine evolution: **RATIO-CHANNEL**), or a Q0 gate that
routes ratio metrics out of the scalar path entirely.

### Per-tool adapter seams

- **hyperfine** `times[]` → seconds, batch=1, unit=invocation, clock=wall,
  includes_startup=true, overhead_removed=true unless `-N`.
- **Criterion** `sample.json` → fit slope per group, batch=iters, unit=op,
  clock=wall, overhead_removed=true (intercept absorbs fixed cost).
- **JMH** → detect mode; AverageTime is time/op (→ s); invert Throughput only
  after a validity check; unit=op; walk `rawData[fork][iter]`.
- **Google Benchmark** → choose and record `cpu_time` vs `real_time`; no raw
  per-iter, so `--benchmark_repetitions 20–50`, keep `run_type=='iteration'`.
- **pytest-benchmark** `stats.data` is already s/op.
- **k6** `http_req_duration` is ms (÷1000); **vegeta** latency is ns (÷1e9); both
  batch=1, unit=request, clock=wall.

### Correctness gate per regime

LIBRARY keeps digest-equality of `invoke()` output. CLI/SERVICE use **semantic
equivalence over a canonical form**, not a raw-byte digest: normalize ordering,
color, path prefixes, and trailing newline, then compare the normalized set/body.
(rg colorizes and reorders by default, so a raw digest falsely fails; comparing
the color-off, path-normalized, sorted match set passes correctly.)

**Correctness-model boundary: the gate assumes ONE canonical correct output
(Iter 11, APPROXIMATE-RANDOMIZED-CORRECTNESS-GATE `confirmed`).** Both forms above
— digest equality and canonical-form equivalence — presume a *deterministic,
exact* correct answer. A whole target class is correct only *in distribution*:
approximate-nearest-neighbor search at a recall target, lossy codecs at a
PSNR/SSIM target, randomized/Monte-Carlo and LLM inference. For these the domain's
real acceptance criterion is `quality(output) ≥ threshold`, not output identity.
`experiments/approx_correctness` showed an ANN `approx` probe with recall@10=0.94
(domain-correct vs a brute-force `exact` ground truth) cannot pass the gate: its
output is non-identical, so `run_suite([exact, approx])` raises "CORRECTNESS GATE
FAILED"; and an unseeded stochastic probe's `sha256(repr(output))` changes every
call, so it is not even self-consistent. The only way to benchmark such a target
is to bypass the gate (run each probe alone) — at which point `aggregate()` still
emits a confident bootstrap CI (median 3.37 ms, CI [3.367, 3.380] ms) carrying
zero correctness guarantee. The gate is binary `sha256(repr(output))` equality
(core.py:111-122) with no tolerance/recall/quality hook anywhere in core.py or
stats.py. **Practical rule:** before timing, classify the correctness model —
exact-deterministic → digest/canonical gate; correct-in-distribution → a
quality/tolerance gate (`quality(output) ≥ min_quality` against a reference), never
digest equality. Queued spine evolution: an **APPROX-CORRECTNESS-GATE** — an
optional `quality(output)->float` + `min_quality` on the `Probe` contract, with
the digest gate kept as the default for exact targets. Until that lands, a
correct-in-distribution target is out of scope for the automatic gate, and any
benchmark of one is reporting a CI with the correctness guarantee silently
dropped.

The full framework — decision table across ~16 target characteristics plus seven
worked decisions (Rust/Criterion, Python/CPython, rg-vs-grep, HTTP p99/vegeta,
LSP-stdio, Go/benchstat) — is carried in the iteration artifacts and folded in
here as the authoritative `wrap vs build` reference.
