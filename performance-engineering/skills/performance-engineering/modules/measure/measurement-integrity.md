# Measurement integrity (don't fool yourself)

**Status:** READY
**Loaded when:** always, as the quality bar on every measurement in every branch.

This is the discipline that makes the **measure** step of the SKILL.md loop (target → measure → locate → fix → prove → defend) worth anything. Every other leaf produces or consumes numbers; this one decides whether those numbers are real. The core rule: a measurement is a claim about the world, and most ways of taking it quietly produce a number that flatters you. Each rule below is paired with the concrete failure it prevents, because the only reason to follow a rule you find tedious is the specific lie it stops you from telling yourself.

Two sources stand behind this leaf: the mechanical-sympathy measurement discipline (tails, noise, coordinated omission, microbenchmarks), and the experimentally-verified findings of the performance-eval harness, whose statistics layer was built by trying to break its own claims and recording what broke. Where a number appears below (`0% coverage`, `424% biased`, `3.66x`), it is a measured result from that harness, cited so you can trust or contest it. The harness lives at `harness/` and its full write-up at `harness/METHODOLOGY.md`.

---

## The rules (each with the failure it prevents)

Run these as a gate. A measurement that violates any of them is not evidence yet.

### 1. Measure before and after, the same way

Capture a baseline under the identical harness, machine, and load you will use for the after-measurement. Change one thing, re-measure.

- **Prevents:** "it got faster on my laptop" — an anecdote with no baseline to subtract, no way to tell the change from the noise, the time of day, or the build flags. Without a before, "after" is a number, not a result.
- **Defense:** same binary path, same input, same machine state, baseline and treatment run back-to-back (ideally interleaved, rule 4). If you cannot reproduce the baseline twice and get the same number, stop — you are measuring the environment, not the code.

### 2. Discard warmup

Throw out the first N iterations. Caches are cold, the branch predictor is untrained, a JIT has not compiled, the frequency governor has not ramped, transparent huge pages are not yet faulted in.

- **Prevents:** a steady-state estimate polluted by one-time startup cost, which makes a fast implementation look slow and hides real regressions under transient noise.
- **Defense:** the harness runner discards warmup as a fairness principle before timing anything. But warmup is not always finite: a JIT that tiers up past your fixed warmup window, or thermal throttling that arrives late, means "steady state" never settles. The harness's IID-bootstrap experiment found that confidence-interval coverage holds only for stationary samples; a still-drifting trajectory needs a convergence check, not a fixed discard count.

### 3. One run is noise — use a distribution

Never report a single measurement. Run enough repetitions that run-to-run variance is small relative to the effect you are claiming.

- **Prevents:** reporting a point with no uncertainty. On a multi-tenant machine (cloud VM, laptop running a browser) run-to-run variance is routinely 20%+; your "15% improvement" can be entirely noise.
- **Defense:** collect a sample of measurements and a confidence interval, not a number. With n effectively 1 (a single non-repeatable run), the bootstrap is undefined and you have no claim. The harness's central-tendency default is a median with a 95% percentile bootstrap CI, which assumes no normality. Two implementations whose CIs overlap are not distinguishable; the `rg` vs `grep` experiment only crowned a winner because the CIs cleanly separated at every input size.

### 4. Randomize and interleave repetitions

Run the reps for all variants in shuffled, interleaved order, not all-of-A-then-all-of-B.

- **Prevents:** system drift (thermal ramp, a neighbor waking up, a background compaction) landing entirely on whichever variant ran last, manufacturing a difference that is really just elapsed time.
- **Defense:** interleaving spreads drift across all variants equally. It also partly breaks serial correlation between samples: the harness found that under autocorrelation ρ=0.9, median-CI coverage collapsed from 0.957 to 0.397, and a moving-block bootstrap only recovered it to 0.787. Interleaving is the cheap first defense against that serial structure; a genuinely state-dependent trajectory (GC, JIT, LSM compaction) needs a block bootstrap on top.

### 5. Pick the right statistic — and band the tail with its own interval

The median resists outliers; the mean does not. When the headline is a tail percentile (p99, p99.9), report that percentile, banded by a confidence interval computed for *that percentile*, never the median's.

- **Prevents:** two distinct failures. First, a single scheduler hiccup dragging a mean-based headline (a 2 ms service with one 500 ms stall has a misleading mean; the median does not move). Second, and subtler, printing a tail number next to an interval that secretly describes the center. The harness's tail-CI experiment found a **median bootstrap CI contains the true p99 in 0% of trials** and is **23x to 40x narrower** than the true p99 sampling spread; a quantile CI restored near-nominal coverage (~93%). On live service data the p99 CI came out **473x to 541x wider** than the median CI. A tail banded by a median's interval is not conservative, it is wrong.
- **Defense:** median + median-CI for central tendency; quantile + quantile-CI for a tail. Two statistics, two intervals. The tail is its own measurement.

### 6. Know your metric — throughput is a ratio of totals, not an average of rates

Throughput (req/s, bytes/s), hit-rate, error-rate, and utilization are `sum(numerator) / sum(denominator)` over the whole window. They are not the mean or median of per-window rates.

- **Prevents:** the biased-ratio trap. Averaging per-second rates over-weights idle windows and under-weights busy ones. The harness measured **the median of per-window rates as 424% biased with 0.000 coverage** of the true throughput; a paired bootstrap that resamples `(numerator, denominator)` pairs and recomputes the ratio of totals recovered **0.983 coverage** (paired relative error ~11% over trials, ~1% at the representative point, versus the median-of-rates' 424%).
- **Defense:** compute ratio metrics as totals over totals, with a paired bootstrap for the interval. Do not route a rate through the scalar-median path. More broadly: tag every sample with its metric, unit, and clock. The harness's hardest unenforced bug was a peak-RSS-in-bytes sample stuffed into a `seconds_per_op` field and reported as "median 275,808,904 seconds" — the units-lie, now a hard error. Never average bytes with seconds, or warm-start with cold-start, into one number.

### 7. Defeat coordinated omission

Drive load open-loop: issue requests on a fixed schedule (a target arrival rate) regardless of whether prior responses have returned, and measure latency from *scheduled* send time to receipt.

- **Prevents:** the most dangerous tail bug. A closed-loop client that sends, waits, then sends again does not issue the requests it *would* have sent during a slow period, so the slow period is under-sampled and the tail you report is fiction. The bias lives in data collection, so no statistic downstream can detect or repair it.
- **Defense:** open-loop generation (wrk2, vegeta, k6 arrival-rate, fortio configured correctly). The harness's service regime uses an open-loop generator for exactly this reason; under it, real p99/median ran 14 to 16. Plain wrk and naive closed loops are fine for a throughput number and never for a latency-tail headline.

### 8. Microbenchmarks lie — confirm in the macro

A microbenchmark runs a tight loop with hot caches and a warm predictor. Production runs with cold caches, a polluted predictor, memory pressure, and neighbors sharing the L3.

- **Prevents:** shipping a "3x speedup" that does not move the system at all because the real bottleneck was elsewhere. Microbenchmark numbers are upper bounds on production performance, not estimates of it.
- **Defense:** treat a microbenchmark win as a hypothesis, then verify it in a macrobenchmark — the actual system under actual load (`verify.md`). A second subtlety the harness surfaced: at small fixed batch sizes the per-op number is not even stable (a ~0.1µs op read 125ns at batch=1 versus 34.2ns at batch=16384, a **3.66x swing with disjoint CIs**), because per-batch overhead dominates until calibration grows the batch past the knee. The micro number is honest only when the harness owns the clock and calibrates the batch.
  - *Apple Silicon caveat (LOCAL is often macOS):* cache-sharing effects scale with the cache line, which is **128 bytes** on Apple Silicon, not the x86 64. Never hardcode 64 for padding/false-sharing work — query `sysctl hw.cachelinesize` and use `std::hardware_destructive_interference_size`. There is no shared L3 in the x86 sense; the cluster-shared last level behaves differently, which only widens the micro-to-macro gap.

### 9. Keep correctness — a fast wrong answer is not a result

Gate every measurement on output correctness before you trust its timing.

- **Prevents:** crowning a fast-but-wrong implementation. An optimization that drops a bounds check, skips a flush, or returns stale data is not faster, it is broken; its number is meaningless.
- **Defense:** the harness refuses to compare probes that disagree on output for the same input (a digest gate), and for approximate targets (ANN at a recall target, a lossy codec at a PSNR bar, a randomized or LLM output) admits them only against an explicit quality threshold rather than silently dropping the correctness guarantee. Decide the correctness contract first, then measure the things that satisfy it.

---

## Quick reference: which statistic for which headline

| Headline | Statistic | Interval | Generation |
|---|---|---|---|
| Central per-op / per-request cost | median | percentile bootstrap CI on the median | calibrated in-process loop |
| Tail latency (p99, p99.9) | that percentile | bootstrap CI on **that** quantile | open-loop, per-request samples |
| Throughput / hit-rate / any rate | sum(num)/sum(den) | paired bootstrap on resampled pairs | totals over the whole window |
| Non-time metric (RSS, allocs, joules) | metric-appropriate | per-metric | tagged unit + matching collector |

Two homogeneity guards sit under this table: never pool samples that disagree on unit/clock/warm-vs-cold, and never pool samples taken at different batch sizes (a tight batch=1000 cohort mixed with a noisy batch=1 cohort yields a CI that honestly describes neither). The harness enforces both as hard errors.

---

## Pitfalls and over-claiming signals

- **Reporting a delta inside the noise.** A "10% speedup" within either variant's run-to-run variation is not a speedup. If the CIs overlap, you have no result — say so.
- **One sound rule, wrong distribution.** All the statistics above assume samples are stationary and unimodal. At a cache/branch/IO boundary the distribution is bimodal and the median lands in the empty valley between the two modes with a deceptively tight CI. A single central-tendency headline is then a lie of a different kind; report per-mode summaries.
- **Estimate mistaken for bound.** A p99 with a CI is a statistical *estimate*. Hard-real-time WCET and safety certification need a sound upper *bound*, which sampling cannot give. Know which one your context demands before you quote a number.
- **Cleanroom theater.** Pinning cores (`taskset`), fixing the governor (`cpupower frequency-set -g performance`), and disabling turbo reduce variance and are worth doing — but a spotless microbenchmark machine makes rule 8 *more* dangerous, not less, because the gap to production widens. Clean the bench to compare two variants; do not mistake the clean number for the production number. (`taskset`/`cpupower` and `perf`/eBPF profiling are Linux-only; when LOCAL is macOS / Apple Silicon there is no governor knob or `taskset` equivalent — see `../environment/local-mac.md` for the macOS quiescing and profiling equivalents.)

---

## Worked example

A change to a JSON parser shows **40% faster** in a tight loop over one cached 4 KB document. Apply the gate.

1. **Before/after, same way** (rule 1): re-run the baseline twice; it varies 8% run-to-run, so the bench is noisy before any change.
2. **Discard warmup, use a distribution** (rules 2–3): drop the first 50 iterations; collect 40 reps. The 40% becomes 22% with a CI of [14%, 31%].
3. **Interleave** (rule 4): shuffling baseline and treatment reps shrinks the apparent gain to 18% — some of the original delta was thermal drift on the all-A-then-all-B order.
4. **Right statistic** (rule 5): the headline is throughput (docs/sec across a stream), not per-doc median. Recomputed as a ratio of totals, the gain holds at 17%.
5. **Microbenchmark lies** (rule 8): in the macrobenchmark — the ingestion service under open-loop load (rule 7) — end-to-end p99 (banded with its own quantile CI, rule 5) moves 2%, because parsing was 11% of the request and the tail is dominated by a downstream call. The win is real but small; the 40% was an artifact of a hot, single-document loop.
6. **Correctness** (rule 9): the faster path skipped UTF-8 validation. Gate fails. The number is void until validation is restored, after which the macro gain is 1%.

The honest result: a correct 17% microbenchmark win worth ~1% to the system. Whether that ships is a cost decision, not a performance claim dressed up as 40%.

---

## Where next

| When you need to… | Go to |
|---|---|
| set up the actual benchmark (regime, sourcing, harness) | `benchmark.md` |
| prove a fix moved the targeted number | `verify.md` |
| locate the bottleneck these numbers point at | `../diagnose/index.md` |
| read the experimentally-verified statistics in full | `harness/METHODOLOGY.md` |
