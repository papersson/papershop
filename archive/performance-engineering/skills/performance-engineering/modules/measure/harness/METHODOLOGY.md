# Methodology: building a performance-evaluation harness for any codebase

This is the capstone of the performance-eval-harness project. It is not a
benchmark report. It is the transferable method the project arrived at by
running experiments against its own design: how to build a harness that measures
an arbitrary target fairly, what architecture survives contact with many kinds
of target, which statistics are honest, and where a sampling-based harness stops
being able to answer the question at all.

Everything here is grounded in the project's lab notebook (`research/THEORY.md`,
`research/CLAIMS.md`, `research/LOG.md`) and the spine source
(`src/harness/core.py`, `src/harness/stats.py`, `src/harness/report.py`). Where a
claim is stated, the experiment that established it is cited by name so you can
check it.

---

## 1. Purpose and stance

The goal is transferable knowledge of the form: given an arbitrary target, here
is how to evaluate its performance fairly. The harness is both the output and the
instrument. The work is empirical methodology development run as the scientific
method, not the construction of one benchmark.

The method rests on a falsifiable core claim and a discipline of attacking it.
The core claim (C1) is that to evaluate a new target you write only a
probe/adapter and never modify the shared spine. Every experiment in the project
is an attempt to break a claim like this. When an experiment breaks one, that is
a success, not a setback: a refutation tells you exactly where the design was
wrong and what to fix. Several of the most useful results in this document are
refutations (peak-RSS metrics, silent batch pooling, throughput ratios) that each
forced a concrete improvement.

Two loops run on top of each other.

- **Object loop:** build a harness, run an experiment, get a number.
- **Meta loop:** read the result, decide what it implies for *how to build
  harnesses*, generate the next question, and decide when to stop.

Experiments are instruments of the meta loop. Their job is to attack the claims,
not to produce numbers for their own sake. A number that does not move a claim is
noise.

This document is written for an engineer who wants to build evaluation harnesses
for their own codebase. Read it as a procedure plus a set of guardrails, with the
evidence attached so you can trust or contest each part.

---

## 2. Architecture: the shared spine plus swappable regimes

The harness is four stages. Each talks to the next only through plain data, so any
stage can be replaced without touching the others.

```
   probe/adapter ──▶ runner ──raw_samples──▶ aggregator ──stats──▶ reporter
  (target-specific)  (owns clock,           (median + bootstrap   (plots, tables)
                      warmup, calibration,    confidence interval)
                      correctness gate)
```

| Stage      | File                       | Reads          | Writes              |
| ---------- | -------------------------- | -------------- | ------------------- |
| probe      | `experiments/*/target.py`  | params         | a fixture + output  |
| runner     | `src/harness/core.py`      | probes + grid  | `raw_samples.json`  |
| aggregator | `src/harness/stats.py`     | raw samples    | `stats.json`        |
| reporter   | `src/harness/report.py`    | stats          | `scaling.png`, table |

The only target-specific code is the probe/adapter. Everything downstream depends
on the data contract between stages, never on how a measurement was produced. That
is what lets a hyperfine run, a vegeta run, and a hand-written in-process loop all
feed the same aggregator.

### The two load-bearing data contracts

**The raw-sample schema** (from `core.py`) is the contract every later stage reads.
One dict per measurement:

```
{
    "probe":           str,    # which implementation
    "params":          dict,   # the input point (e.g. {"n": 1000})
    "rep":             int,    # repetition index
    "batch":           int,    # iterations timed together (calibration)
    "seconds_per_op":  float,  # wall time / batch -- the measurement
}
```

Provenance and ratio channels were added later as additive, optional keys (covered
in sections 5 and 6): a metric-neutral `value` channel that `seconds_per_op` falls
back to, the provenance fields `metric` / `unit` / `clock` / `includes_startup` /
`overhead_removed`, and the ratio channels `numerator` / `denominator`. Legacy
samples that carry none of these still flow through unchanged.

**The summary schema** (from `stats.py`) is what the reporter reads. One dict per
`(probe, params)` group:

```
{
    "probe":   str,
    "params":  dict,
    "n":       int,     # number of raw samples
    "min":     float,   # often the cleanest estimate of true cost
    "median":  float,
    "mean":    float,
    "stdev":   float,
    "p90":     float,
    "p99":     float,
    "ci_low":  float,   # 95% bootstrap CI for the median
    "ci_high": float,
    "p90_ci_low":  float,   "p90_ci_high": float,   # CI for p90 (tail-CI rule)
    "p99_ci_low":  float,   "p99_ci_high": float,   # CI for p99
    "metric":           str,    "unit":      str,   # provenance, additive
    "clock":            str,    "includes_startup": bool,
    "overhead_removed": bool,
}
```

The reporter reads only this schema. It never reaches back into the runner or the
probe. That one-way dependency is what lets you add a plot or an output format
without touching how anything is measured.

### The core invariant (C1)

To add a target you write only a probe/adapter. The spine (`core.py`, `stats.py`,
`report.py`) is shared across every regime and is touched only by deliberate,
general, documented infrastructure evolution, never bent to fit one target.

Editing the spine to make one target work is itself a finding: it refutes the
normalization hypothesis. If you must do it, stop and record it as a claim
outcome. C1 is confirmed across three regimes (library, CLI, service), each added
probe-only with the three spine files byte-for-byte unchanged before and after a
fresh run (sha256 verified in `experiments/service_regime`, re-checked in every
later iteration). The only sanctioned spine changes in the whole project are
general improvements that all regimes share, each recorded in `CLAIMS.md`: the
tail-CI rule, the provenance evolution, and the three fixes in the
fix-the-useful-few iteration.

---

## 3. The three measurement regimes

Different targets need different timing machinery. The spine is shared; the regime
is selected per target. All three are confirmed.

| Regime | Targets | Timing machinery | Status |
| --- | --- | --- | --- |
| Library / in-process | functions, methods | calibrated in-process loop (`core.py`) | confirmed |
| CLI / subprocess | command-line tools | process wall-clock, startup-aware (wrap hyperfine) | confirmed |
| Service / load | servers, endpoints | open-loop generator + arrival schedule (wrap vegeta) | confirmed |

### Library / in-process

The target plugs in as a `Probe`: a `name`, a `prepare(params) -> fixture`
(untimed setup), and an `invoke(fixture) -> output` (the timed work). The runner
owns the clock. It calibrates an inner batch so a fast op clears timer resolution,
discards warmup, and times repetitions in randomized interleaved order.

Evidence: `experiments/membership` (Iteration 1) compared list, set, and dict
membership across container sizes 100 to 100,000. The list came out a clean
straight line on the log-log plot (linear, O(n)); set and dict were flat
(constant, O(1)). The correctness gate passed and the spine was not modified to
add the experiment.

### CLI / subprocess

The target plugs in through an adapter that wraps hyperfine. hyperfine owns the
process clock and the hard parts (shell-spawn calibration and subtraction, run
counts, warmup and cache hygiene). The adapter maps hyperfine's per-command
`times[]` array into the existing raw-sample schema (batch=1, one sample per run).

Evidence: `experiments/cli_search` (Iteration 2) benchmarked `rg` against `grep`
counting matches over corpora from 2k to 1M lines. grep wins at small inputs where
startup dominates (2k lines: grep 1.29 ms vs rg 2.50 ms). ripgrep wins decisively
once work dominates (1M lines: rg 10.06 ms vs grep 99.76 ms, about 10x). The
crossover sits near 20k lines (rg 2.60 ms vs grep 2.93 ms), and the CIs cleanly
separate the two at every size. hyperfine's output flowed through the unchanged
`aggregate()` and reporter; the correctness gate ran real subprocesses and agreed
on match counts before any timing.

### Service / load

The target is driven by an open-loop load generator (vegeta) at a fixed arrival
rate. The generator owns the clock and the arrival schedule. The adapter parses
each request's latency and emits one raw sample per request (batch=1).

Evidence: `experiments/service_regime` (Iteration 5) stood up a stdlib
`ThreadingHTTPServer` with a seeded heavy-tailed delay (base ~2ms plus 5%
log-normal spikes), driven open-loop by vegeta at 100/200/300 req/s. n=4800 real
latencies flowed through the unmodified `aggregate()`, which returned a populated
p99 and p99 CI natively. The tail was real: p99/median ran 14 to 16, and the
spine's p99-CI width came out 473x to 541x the median-CI width, which exercised the
tail-CI machinery on live data rather than synthetic draws. Two gates ran: every
request returned HTTP 200 with zero transport errors, and a validity gate
independently recomputed median/p99/median-CI and byte-matched the aggregator.

### Why the spine absorbs all three

The wall-clock-vs-in-process difference, and the per-request-vs-per-op difference,
are absorbed by the unit-agnostic schema. An external tool is a sample *source*
upstream of `raw_samples`; CI services (Bencher, Conbench) are exporters
*downstream* of `stats`. Neither replaces the schema or the aggregator. This is the
normalization-layer result (C3): the generalizable value is the unifying layer,
not the measurement loop.

---

## 4. The REGIME-AND-SOURCING (R&S) decision framework

R&S is the usable procedure for deciding how to measure a given target. Run the
metric-type gate first, then the regime selector, then the sourcing rule.

### Q0 — Metric-type gate (run first, record the answer)

What is the headline metric and its unit?

- If it is **time-per-unit in seconds**, proceed to the regime selector.
- If it is peak RSS, allocations/op, energy in joules, or any non-time metric, you
  may **not** force it into `seconds_per_op`. Tag the sample with extended
  provenance (`metric` + `unit` + `value`) and use a metric-appropriate collector
  (`-prof gc`, `/usr/bin/time -l`, `perf`, `powermetrics`), or declare the target
  out of scope. This is now enforced in code (section 5).
- Then ask a second question: **is the headline a ratio of totals?** Throughput
  (req/s, bytes/s), cache hit-rate, error-rate, and utilization are all
  `sum(num)/sum(den)`, not a central tendency of per-window rates. Tagging the unit
  is necessary but not sufficient, because the denominator lives outside the value
  channel. Route a ratio metric to the ratio estimator (section 5), not the scalar
  median path.

### Q1–Q5 — Regime selector

- **Q1, Access surface (branches may co-fire).** (a) in-process call → LIBRARY
  candidate; (b) one-shot process you spawn and wait for → CLI candidate;
  (c) network/RPC to a long-lived or request-triggered remote → SERVICE candidate;
  (d) stateful request/response over stdio to a persistent child (LSP, REPL) →
  SERVICE-stdio sub-case. Record every branch that is true.
- **Q2, Library-vs-IO test (any (a) candidate).** Does `invoke()` block on an fd or
  cross-process syscall whose wait dominates? Yes → route out of LIBRARY into the
  IO/SERVICE path (open-loop, unit=request, batch=1); async-awaiting-IO calls go
  here too. No (compute stays on-CPU) → stays LIBRARY.
- **Q3, Headline decider (mandatory when surfaces co-fire; this is the decider, not
  a tiebreak).** Pick the regime whose measured unit equals the headline unit:
  per-op on-CPU cost → LIBRARY; whole-invocation cost including process/interpreter
  startup → CLI; per-request latency or tail under an arrival rate → SERVICE.
- **Q4, Measurement-strategy sub-select (does not change the regime).** Is one op
  faster than ~5 ms? LIBRARY+fast → calibrate an inner batch N to a minimum batch
  time and report `elapsed/N` (the `core.py` path); LIBRARY+slow → batch=1. CLI is
  always batch=1; there the ~5 ms figure instead decides whether to run hyperfine
  with `-N`/`--shell=none` so the number is not dominated by shell-spawn
  calibration. `min_batch_time` is load-bearing, not cosmetic (section 7).
- **Q5, Runtime optimizer-barrier lookup (keyed on the *runtime*, not the source
  language).** No-JIT interpreters (CPython, Lua 5.x, Ruby MRI) → a liveness sink
  (`core._SINK`) is adequate and a hand-rolled loop is allowed. JIT/AOT runtimes
  (JVM, CLR, V8, PyPy, Numba, JAX, LuaJIT, optimized native Rust/C++/Swift/Go) → a
  real optimizer barrier (`black_box`/`DoNotOptimize`/`Blackhole`) plus warmup and
  steady-state detection are mandatory and not safely hand-rollable. This forces
  WRAP.

### Sourcing rule — wrap vs build

- **WRAP** if the runtime is JIT/AOT: barrier, warmup, and steady-state detection
  cannot be hand-rolled. Wrap the ecosystem-standard in-process framework.
- **WRAP** if the regime is CLI: wrap **hyperfine**. It owns shell-spawn
  calibration and subtraction, auto run-count and time-budget, warmup and
  `--prepare` cache hygiene, peak-RSS, and `--output` control. Constraint:
  hyperfine does not interleave between commands, so drive it round-robin per run
  and force `--runs 20–40` (never the default 10) so the bootstrap has enough
  samples.
- **WRAP** if the regime is SERVICE/load: wrap an open-loop generator (vegeta, k6
  arrival-rate, wrk2). Coordinated-omission correction, HdrHistogram tail accuracy,
  and high-rate scheduling are not safely hand-rollable. Plain wrk is fine for
  throughput but never for a latency-tail headline.
- **WRAP** if a language has a de-facto microbench framework and comparability to
  published numbers matters (Criterion, Google Benchmark, JMH, BenchmarkDotNet,
  `testing.B`+benchstat).
- **BUILD our own only when all of these hold:** regime is LIBRARY, runtime is
  no-JIT, headline is per-op CPU time in seconds, and none of the hard parts
  (optimizer barrier, coordinated-omission correction, HdrHistogram, high-rate
  scheduling) are in play. Then `core.py`'s calibrated loop suffices and adds the
  bootstrap median CI that timeit and pytest-benchmark omit.
- **Exception, build a thin driver** for SERVICE-stdio (LSP/REPL over stdio): no
  off-the-shelf open-loop tool speaks the framing. Build only the
  request/timestamp driver and reuse the spine and tail-CI aggregator unchanged.
- **Always build/own the spine.** External tools are sources upstream of
  `raw_samples`; CI services are exporters downstream of `stats`. Neither replaces
  the schema or the aggregator.

### Decision table (worked verdicts from THEORY.md)

| Target | Surface | Headline unit | Runtime | Verdict |
| --- | --- | --- | --- | --- |
| Python container membership | LIBRARY | per-op seconds | CPython (no-JIT) | LIBRARY + BUILD (`core.py`) |
| `rg` vs `grep` | CLI | per-invocation seconds (incl. startup) | native, optimized | CLI + WRAP hyperfine |
| Rust function microbench | LIBRARY | per-op seconds | native, optimized (JIT/AOT class) | WRAP Criterion |
| Go function microbench | LIBRARY | per-op seconds | compiled, optimized | WRAP `testing.B` + benchstat |
| HTTP endpoint p99 | SERVICE | per-request latency under a rate | server process | SERVICE + WRAP vegeta |
| LSP / REPL over stdio | SERVICE-stdio | per-request latency | persistent child | BUILD thin driver, reuse spine |

The framework returns the same verdict for the two targets actually run end to
end: membership → LIBRARY + BUILD, rg-vs-grep → CLI + WRAP hyperfine. The full
table across ~16 target characteristics and seven worked decisions is carried in
the iteration artifacts and folded into `THEORY.md`.

---

## 5. Fair, honest measurement

Two layers: regime-independent fairness principles that the runner enforces, and
the statistics the aggregator computes. Each item names the failure it prevents.

### Fairness principles (runner)

- **The runner owns the clock.** The target never times itself, so it cannot
  report a number that flatters itself or omits cost it would rather not count.
- **Batch calibration.** Fast ops are run in a calibrated batch and divided back
  out, which lifts the measurement above timer granularity so the number reflects
  the op, not the clock's resolution.
- **Correctness gate.** Probes that disagree on output for the same input are
  refused, so you never crown a fast-but-wrong implementation over a correct one.
- **Warmup discarded.** The first runs (cold caches, page faults, first-call
  setup) are thrown away so they do not pollute the steady-state estimate.
- **Randomized, interleaved repetitions.** Reps run in shuffled order across
  probes, so system drift during the run is spread across all probes equally rather
  than dumped on whichever ran last.

### Statistics (aggregator)

- **Median with a bootstrap CI.** The headline central estimate is the median,
  banded by a percentile bootstrap CI with no normality assumption. This prevents
  a single scheduler hiccup from dragging the headline (which a mean would let
  happen) and prevents reporting a point estimate with no stated uncertainty (C2,
  confirmed for central-tendency headlines).
- **The tail-CI rule.** When the headline is p90/p99/p99.9, band *that* statistic
  with its own bootstrap CI (`bootstrap_ci_quantile`), never the median's. This
  prevents printing a tail percentile next to a CI that actually describes the
  median. `experiments/tail_ci` (Iteration 3) showed a median bootstrap CI contains
  the true p99 in 0% of trials and is 23x to 40x narrower than the true p99
  sampling spread; a quantile CI restores ~95% coverage. `experiments/service_regime`
  confirmed it on live data, where the p99 CI was hundreds of times wider than the
  median CI.
- **Ratio-of-totals estimator.** For throughput and other rate headlines, the
  honest value is `sum(num)/sum(den)` with a *paired* bootstrap that resamples
  `(numerator, denominator)` pairs and recomputes the ratio of resampled totals
  (`ratio_of_totals_ci`). This prevents the biased median-of-rates and its
  mis-covering CI. `experiments/ratio_metric` (Iteration 9) measured the median of
  per-window rates as 424% biased with 0.000 coverage of the true throughput; the
  paired estimator recovered 0.983 coverage.
- **Provenance and unit enforcement.** `aggregate()` refuses to pool a
  `(probe, params)` group whose samples disagree on `(unit, clock,
  includes_startup, overhead_removed)`, and `report.plot_scaling` refuses to
  co-plot mismatched units. This prevents silently averaging bytes with seconds,
  or warm with cold-start, into one meaningless number (the units-lie).
- **Batch-homogeneity guard.** `aggregate()` refuses a group that mixes `batch`
  sizes. This prevents pooling a tight batch=1000 cohort with a noisy batch=1
  cohort into one bootstrap whose CI honestly describes neither.
- **Approximate-correctness gate.** A probe may supply `quality(output, fixture)
  -> float`, and `run_suite` may take `min_quality`; such a probe is admitted on a
  quality threshold and exempted from bit-equality, while the digest gate stays the
  default for exact targets. This prevents a correct-in-distribution target
  (approximate-nearest-neighbour at a recall target, a lossy codec at a
  PSNR/SSIM target, a randomized or LLM output) from being wrongly rejected by an
  exact-equality gate, or from being benchmarked with the correctness guarantee
  silently dropped.

---

## 6. What is established

The claim ledger (`CLAIMS.md`) tracks each architectural claim as a falsifiable
prediction with a status. A refuted claim is a success: it updated the theory.

### Confirmed

| Claim | What it establishes | Evidence |
| --- | --- | --- |
| C1 | New target = probe/adapter only; spine untouched | three regimes added probe-only, spine sha256 byte-identical |
| C2 | Median + bootstrap CI is an adequate default (central tendency) | membership, cli_search |
| C2-tail | A median CI is not a tail band; quantile CI restores coverage | `tail_ci`, confirmed on live data in `service_regime` |
| C3 | One schema absorbs heterogeneous external tools | hyperfine `times[]` into the unchanged schema |
| C4 | A decidable wrap-vs-build rule exists (R&S) | framework authored, same verdict on both run targets |
| C5 | The correctness gate generalizes beyond library calls | `cli_search` semantic-equivalence gate on `rg` vs `grep` |
| SERVICE-REGIME | The load regime maps 1:1 into the schema | `service_regime`, vegeta, n=4800 |
| PROVENANCE | One additive evolution carries non-time metrics honestly | `provenance`, back-compat byte-identical |
| RATIO-CHANNEL | Ratio-of-totals estimator with paired bootstrap | fix-the-useful-few, rel err 4.7% vs 459% |
| BATCH-HOMOGENEITY-GUARD | Mixed-batch pooling now raises | fix-the-useful-few |
| APPROX-CORRECTNESS-GATE | Quality contract admits approximate probes | fix-the-useful-few |

The three regimes (library, CLI, service) and the three implemented fixes
(ratio channel, batch-homogeneity guard, approximate-correctness gate) are all
confirmed and live in the spine.

### Productive refutations

Three experiments broke a claim, and each break drove a concrete, general fix.

- **Non-time-metric mislabeling (NONTIME-METRIC, refuted, Iteration 4).** An honest
  peak-RSS-in-bytes sample fed to the unmodified `aggregate()` raised
  `KeyError('seconds_per_op')`, because the time key was hardcoded. The only
  spine-free workaround was to stuff bytes into `seconds_per_op`, which the
  aggregator then accepted *silently* and reported "median 275,808,904 seconds".
  The Q0 gate was designed in theory but unenforced in code. **Fix:** the
  PROVENANCE evolution (Iteration 7) added a metric-neutral `value` channel (with
  `seconds_per_op` fallback) and provenance fields, made the aggregator refuse to
  pool mismatched units, and re-aggregated all three legacy experiments
  byte-identically. The units-lie became a hard `ValueError`.
- **Batch silent-pooling (BATCH-HOMOGENEITY, refuted, Iteration 8).** The theory
  asserted "all samples in a group share a batch" as an invariant, but the
  aggregator never read `s["batch"]`. A group mixing batch=1 and batch=1000 pooled
  silently into one summary (pooled_n=120, no error), producing a CI too narrow for
  the noisy cohort yet polluted by it. **Fix:** the batch-homogeneity guard in the
  fix-the-useful-few iteration, parallel to the provenance pool guard.
- **IID bootstrap under serial correlation (IID-BOOTSTRAP, partial, Iteration 6).**
  The bootstrap resamples i.i.d., which assumes exchangeable samples. For a
  state-dependent op trajectory (GC/JIT warmup, cache/thermal drift, LSM
  compaction) the median CI under-covers: coverage fell from 0.957 at zero
  autocorrelation to 0.397 at ρ=0.9. A moving-block bootstrap improved coverage
  everywhere (to 0.787 at ρ=0.9) but under-corrected at the strongest dependence,
  so this is **partial**, not fully fixed. The practical rule landed in the theory:
  the median+bootstrap default is honest only for exchangeable samples; randomized
  interleaving (already a fairness principle) helps break serial structure, and a
  genuinely state-dependent trajectory needs a block bootstrap or an
  effective-sample-size warning. The block-bootstrap option is queued spine
  evolution, deliberately not yet implemented.

A fourth result, NONLINEAR-BATCH-AMORTIZATION (partial, Iteration 10), is worth
noting here: `elapsed/N` is *not* batch-invariant at small fixed N (a ~0.1µs op
read 125ns at batch=1 versus 34.2ns at batch=16384, 3.66x, with disjoint CIs), but
the `run_suite` headline stays stable (within 1.1x) across the `min_batch_time`
knob because calibration auto-grows N past the per-batch-overhead knee into the
linear regime. The per-op number is honest only because calibration self-defends
it, which is why `min_batch_time` is load-bearing.

---

## 7. Known limits and scope boundaries

A sampling-based harness has boundaries. The project found these by adversarial
search and deliberately left them open rather than papering over them. Each is a
real class of question the current harness cannot answer soundly, with one line on
why it is out of scope and what closing it would take.

- **Estimate vs bound.** R&S emits p99 plus a CI, which is a statistical estimate.
  Hard-real-time WCET and safety certification need a *sound upper bound* that
  sampling cannot give. Closing it needs a Q0 epistemics gate that separates an
  estimate from a guaranteed bound, or static WCET analysis; otherwise scope out.
- **Non-stationarity and drift.** Every CI presumes stationarity, yet thermal
  throttling, JIT tier-up past a fixed warmup, and compaction make the mean a
  moving target. Closing it needs a steady-state/stationarity gate (split-half or
  Mann-Kendall trend test, or warmup-convergence detection) that flags a still-
  drifting group.
- **Coordinated omission.** A closed-loop generator that stalls when the system
  stalls never issues the would-be-slow requests, so the tail is under-sampled. The
  bias is in data collection, not in `aggregate`, so the statistical layer cannot
  detect it. The service regime mitigates it by using an open-loop generator;
  fully closing it needs an intended-vs-actual send-time correction.
- **Multimodal distributions.** At any cache/branch/IO boundary the distribution is
  bimodal and the median lands in the empty valley with a deceptively tight CI.
  Closing it needs a modality gate (bimodality coefficient or dip test) that
  refuses a single central-tendency headline and reports per-mode summaries.
- **Device and accelerator clocks.** GPU/accelerator kernels break "the runner owns
  the clock"; `clock` has no `device` value and there is no device-event collector.
  Closing it needs a `clock=device` provenance value and a device-event seam, or
  scope out.
- **Input-adversarial worst case.** For a hash table with colliding keys, quicksort
  adversarial pivots, or regex catastrophic backtracking, the median over random
  inputs is fine while the adversarial input the framework cannot request blows up.
  R&S Q3 presumes params pin the workload; here the input distribution is the
  contested unknown and the headline needs search or adversarial generation, not
  sampling a fixed param point.
- **Vector / Pareto headlines.** Rate-distortion frontiers (lossy codecs, ML
  quantization) make "performance" a curve, not a scalar, which violates the
  one-value-per-sample contract Q0 presumes. Closing it needs a schema and report
  extension for a frontier, or scope out.

Related open items in the same spirit, tracked in `CLAIMS.md`: single-shot /
non-repeatable measurements (n is effectively 1, the bootstrap is undefined),
suite-geomean cross-probe headlines, multiplicity / false-discovery control across
hundreds of regression gates, anytime-algorithm quality-time coupling, and
multi-clock skew across machines. They are out of current scope, not solved.

---

## 8. How this methodology was produced

The notebook was produced by a self-driving research loop,
`research/research_loop.js` (a Workflow script; see `research/LOOP.md`). One
invocation runs several iterations with no human in between. Each iteration:

1. **Read state** from `THEORY.md`, `CLAIMS.md`, `LOG.md` into open items.
2. **Plan** with a value function that picks the single highest-value open claim
   and designs a concrete, runnable experiment with a tool preflight.
3. **Snapshot** spine hashes so any change can be judged independently.
4. **Implement** the experiment under `experiments/<name>/`, run it for real,
   reuse the spine, and evolve the spine only as documented infrastructure.
5. **Verify** with a *separate* agent that re-runs it, checks artifacts and spine
   integrity, and judges the claim outcome (with a bounded fix loop for real bugs).
6. **Record** findings back into the notebook; a refutation is a result.
7. **Critic** runs an adversarial "target generator" that tries to break the
   framework and lists remaining high-value work.

This is the L3 rung on the automate-out-of-the-loop maturity ladder: the human
role shrinks to setting the goal and auditing the report. The ladder runs from
running everything by hand, to scripted single experiments, to this self-driving
multi-iteration loop, with the human supervising less at each rung.

The key strategic insight is about the stop condition. "Loop until the adversarial
critic goes dry" does **not** terminate. A creative critic always finds another
edge case: the open agenda in `CLAIMS.md` still lists device clocks, multimodal
distributions, multiplicity control, clock skew, and more, none of them
fabricated. So the stop condition cannot be "the critic ran out of ideas." It has
to be value- and budget-based, or a human scope call. That is exactly why
discovery was deliberately halted: rather than chase every niche break, the
project implemented the three confirmed breaks that affect *common* metrics
(the ratio channel, the batch-homogeneity guard, the approximate-correctness gate)
as general spine evolutions, and scoped the rest out explicitly in section 7. The
remaining critic ideas are genuine, but the marginal value of closing the next one
fell below the cost of doing it.

---

## 9. Using and extending the harness

### Add an experiment

Create `experiments/<name>/` with two files:

- `target.py` exposes `probes` (a list of `Probe`s, or a regime adapter) and a
  `param_grid` (a list of param dicts). A `Probe` is a `name`, a
  `prepare(params) -> fixture` (untimed), and an `invoke(fixture) -> output`
  (timed). For an approximate target, add `quality(output, fixture) -> float` and
  pass `min_quality` to `run_suite`.
- `run.py` wires the spine: `run_suite -> aggregate -> plot_scaling`/`format_table`,
  and writes `results/<name>/{raw_samples.json, stats.json, *.png}`.

You do not modify the spine. If you find you must, that is a finding: stop and
record it in `CLAIMS.md` as a claim outcome. For a CLI or service target, write an
adapter that wraps hyperfine or vegeta and maps its output into the raw-sample
schema, exactly as `cli_search` and `service_regime` do.

### Run

```sh
uv sync
uv run python experiments/<name>/run.py
```

An experiment is sound when the artifacts are produced, the correctness gate
passes (compared implementations agree on output, or clear their quality bar), and
the spine is unchanged, or any spine change is documented as a claim outcome.
Prefer verification by an agent that did not write the experiment.

### Verify the implemented fixes

```sh
uv run python experiments/fixes_verify/run.py
```

This checks the three confirmed fixes in one self-contained harness: the
ratio-of-totals estimator recovers the true throughput (rel err 4.7% versus the
median-of-rates' 459%) with a covering CI, mixed-batch pooling raises, and an
approximate probe (recall 0.93) is admitted under `min_quality=0.85` while the
default gate stays strict and an impossible bar (0.999) is rejected. The legacy
proof: re-aggregating membership, cli_search, and service_regime reproduces every
stored value identically, with only the provenance keys added.
