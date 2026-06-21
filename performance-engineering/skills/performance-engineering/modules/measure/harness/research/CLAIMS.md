# Claim ledger

Each architectural claim is a falsifiable prediction with a status. The meta
loop's job is to drive open claims to `confirmed` or `refuted`. A `refuted` claim
is a success: it updates the theory.

Status values: `untested` · `confirmed` · `refuted` · `partial`

| ID | Claim | Status | Evidence |
| --- | --- | --- | --- |
| C1 | To evaluate a new target you write only a probe/adapter; you never modify the spine (runner schema, stats, reporter). | `confirmed` | Now holds for a **third** regime. Iteration 5 added the SERVICE/load regime probe-only (`experiments/service_regime/{target.py,run.py}`); the three spine files (core.py, stats.py, report.py) are byte-for-byte unchanged (sha256 verified before/after a fresh run: core `d3087dc1…`, stats `542fa4b1…`, report `e93a724d…`). Confirmed for library, CLI, and service regimes. Caveat (now narrowed): a non-time metric is NOT absorbable probe-only — the NONTIME-METRIC refutation (Iter 4) showed the time key was hardcoded. Iteration 7 (PROVENANCE `confirmed`) fixed this by a single sanctioned, additive infrastructure evolution (not a per-target hack — proven by a byte-identical re-aggregation of all three legacy experiments), so the spine now carries non-time metrics honestly. C1 thus holds probe-only **within a metric family**; crossing to a new metric family was a one-time general spine evolution, not a target edit. |
| C2 | Median + bootstrap confidence interval is an adequate default statistic across regimes. | `confirmed (scoped)` | Adequate **for a central-tendency headline**, across two regimes (CLI wall-clock and library). Iteration 3 stress-tested the tail case and found the median CI is *not* a substitute band for a tail headline (see C2-tail); the qualifier "for the median" is now load-bearing, and the spine bands p90/p99 with their own CIs. |
| C2-tail | When the reader's headline is a TAIL statistic (p99), the spine's median bootstrap CI (a) almost never contains the true p99 and (b) is far narrower than the true experiment-to-experiment p99 spread, so it is misleading as a tail band; a `bootstrap_ci_quantile(p99)` achieves ~95% coverage. | `confirmed` | Iteration 3, pure-statistics stress test (`experiments/tail_ci`, K=200 experiments × n=2000, two heavy-tailed models). Fed synthetic heavy-tailed `raw_samples` through the **unmodified** `aggregate()` (re-touches C1). Both models: `cov_median`≈0.95 (median CI correct for the median), `cov_median_for_p99`=0.00, `cov_qci_for_p99`=0.92–0.93, and p99 sampling-SD / mean-median-CI-width = 23×–40× (the real p99 wobble dwarfs the only band the spine offered). Motivated the spine evolution below. **Iteration 5 exercised the same machinery on REAL (not synthetic) data** — vegeta latencies from a heavy-tailed HTTP endpoint, p99/median ≈ 14–16, and the spine's `p99_ci` width was 473×–541× the median-CI width — confirming the tail-CI fields produce honest, materially wider bands on live measurements. |
| C3 | A single raw-sample schema can faithfully represent measurements produced by *heterogeneous external tools* (e.g. hyperfine, Criterion, pytest-benchmark), not just our own loop. | `confirmed` | The new adapter maps hyperfine's per-command `times[]` array into the **existing** raw-sample schema (probe/params/rep/batch=1/seconds_per_op). The samples flow through unchanged `aggregate()` and `report.plot_scaling`/`format_table` into valid artifacts. The wall-clock-vs-in-process difference is absorbed entirely by the unit-agnostic schema; no spine edit was needed. |
| C4 | There is a decidable rule for *wrap an existing tool vs build our own* with explicit conditions. | `confirmed` | Framework authored: **REGIME-AND-SOURCING (R&S)** — a metric-type gate (Q0) + a five-question regime selector (Q1–Q5) + an explicit wrap/build rule + a decision table + seven worked decisions. It returns the same verdict for the membership target (LIBRARY+BUILD) and the rg-vs-grep target (CLI+WRAP hyperfine) actually run this iteration. See THEORY.md. |
| NONTIME-METRIC | The load-bearing raw-sample schema + `aggregate()` generalize past seconds: a non-time headline metric (peak RSS in bytes) flows through the spine without a rewrite. | `refuted` | Iteration 4 (`experiments/mem_metric`). Honest peak-RSS samples (`metric=peak_rss_bytes`, value in bytes, NO `seconds_per_op`) fed straight into the unmodified `aggregate()` raise `KeyError('seconds_per_op')` at stats.py:97 — the time key is hardcoded, the honest sample cannot pass at all. The only spine-free path is to stuff bytes into `seconds_per_op`; `aggregate()` then accepts it **silently** and reports median/min/p99/CI of bytes mislabeled as seconds (e.g. size_mb=256 → "median 275,808,904 seconds"). No guard objected: the schema carries no `metric`/`unit` and there is no metric-neutral `value` channel, so the **Q0 metric-type gate is designed in THEORY but unenforced in code**. Spine byte-identical before/after (sha256). Refutation is productive: it motivates the PROVENANCE evolution below. |
| SERVICE-REGIME | The SERVICE/load regime can be added probe-only: an open-loop generator's per-request latencies map 1:1 into the existing raw-sample schema (batch=1, `seconds_per_op` = latency_seconds) and flow unchanged through `aggregate()` and `report`, producing populated p99 + p99-CI on real heavy-tailed data. | `confirmed` | Iteration 5 (`experiments/service_regime`). A stdlib `ThreadingHTTPServer` endpoint with a seeded heavy-tailed delay (base ~2ms + 5% log-normal spikes) is driven open-loop by **vegeta** at rates 100/200/300 req/s; each request's `latency`/1e9 maps to `seconds_per_op`, batch=1. n=4800 real latencies flow through the **unmodified** `aggregate()` → non-null p99 + p99_ci. Spine sha256 byte-identical before/after (re-exercises C1). Tail is real: p99/median = 14.0/16.2/15.6 (≫3); p99-CI width = 473×/537×/541× the median-CI width (tail-CI machinery genuinely exercised). Two gates ran, not just declared: per-rate correctness (every request HTTP 200, 0 transport errors — PASS at all rates) and a validity gate that independently recomputes median/p99/median-CI and asserts byte-match against `aggregate` (abs diff < 1e-18 — PASS). vegeta latencies fit the CURRENT schema with no provenance edit. |
| IID-BOOTSTRAP | The spine's `aggregate()` resamples i.i.d. (stats.py draws indices uniformly with replacement). For a serially-correlated op trajectory (state-dependent cost: GC/JIT/cache/thermal drift, LSM compaction), the i.i.d. median bootstrap CI UNDER-COVERS the true marginal median, worsening with autocorrelation, while a moving-block bootstrap restores ~0.95 coverage. | `partial` | Iteration 6 (`experiments/iid_bootstrap`), pure-statistics, spine UNTOUCHED (sha256 of core/stats/report byte-identical before/after). Generative model: latency = BASE·exp(z), z a stationary AR(1) (σ=0.4), marginal lognormal, closed-form true median = BASE = 1e-6 (cross-checked vs 5M-draw reference, rel-err 3.2e-4). K=300 experiments × n=2000, ρ∈{0,0.7,0.9}; block bootstrap (L=13) defined ONLY in the experiment (mirrors tail_ci). Validity gate PASSES for all three models (spine median/ci_low/ci_high reproduce an independent local computation to <1e-18 — hard precondition met). **The blind spot is real:** control ρ=0 cov_iid=0.957 (harness unbiased); ρ=0.7 cov_iid=0.657; ρ=0.9 cov_iid=0.397 (material under-coverage), monotone degradation 0.397<0.657<0.957. The i.i.d. CI is too narrow: iid/block width ratio 0.55 (ρ=0.7), 0.39 (ρ=0.9); empirical between-experiment median SD shows the i.i.d. width is 0.26× the correct width at ρ=0.9. **Partial, not confirmed:** the block bootstrap improves coverage at every ρ (0.40→0.79 at ρ=0.9; 0.66→0.92 at ρ=0.7) but UNDER-corrects at the strongest dependence — cov_block=0.787 at ρ=0.9 is below the nominal 0.95 (and outside the pre-registered [0.88,0.97]). So serial dependence breaks the i.i.d. default decisively, and a block bootstrap is a directional but incomplete fix at high ρ (needs longer blocks / larger n). Refutation conditions NOT met (cov_iid far below 0.90; block > iid everywhere). |
| BATCH-HOMOGENEITY | The THEORY.md invariant (THEORY.md:186, "all samples in a group share a batch") is ENFORCED by the spine: `aggregate()` refuses (or slope-fits) a `(probe,params)` group that mixes batch sizes instead of silently pooling. | `refuted` | Iteration 8 (`experiments/batch_homogeneity`), pure-stdlib, spine UNTOUCHED (sha256 of core/stats/report byte-identical to before: core `d3087dc1…`, stats `2b211116…`, report `0f695d55…`). Two deterministically-seeded cohorts for the SAME `(probe="op", params={"size":1})` group with the SAME true 1.0 µs/op, differing only in `batch`: `cohort_fine` (n=60, batch=1000, tight, sd≈0.02 µs) and `cohort_coarse` (n=60, batch=1, noisy, sd≈0.40 µs). **Part A (the refutation):** `aggregate(cohort_fine + cohort_coarse)` returns normally with NO ValueError and `pooled_n == 120` — the spine silently merges two batch sizes into one summary. `_POOL_KEYS = ("unit","clock","includes_startup","overhead_removed")` excludes `batch`; `batch` is in the raw-sample schema but `aggregate()` never reads `s["batch"]`. **Part B (harm):** the pooled median CI width (2.30e-08) sits between the fine baseline (1.44e-08) and the coarse baseline (2.65e-07) — it is far too narrow to honestly express the coarse cohort's uncertainty yet polluted by it, so the pooled number answers neither cohort's question; the only tell that two incompatible cohorts merged is n=120. **Part C (control isolates batch as the unguarded dimension):** a homogeneous batch=1000 group aggregates cleanly (no raise), AND injecting a provenance mismatch (one `unit=bytes` sample) DOES raise `ValueError: refusing to pool mismatched provenance …` — proving the Iter-7 guard machinery works and only the `batch` dimension is missing from it. Validity gate PASSED: medians agree within the coarse CI width (gate_central) and coarse stdev > 5× fine stdev (gate_spread), so the CI gap is variance, not bias. Refutation is productive: motivates an additive batch-homogeneity guard parallel to `_POOL_KEYS` (sanctioned spine evolution, NOT applied this iteration — the refutation requires the spine unchanged). Artifacts: `results/batch_homogeneity/{raw_samples.json, stats.json, findings.json}`. |
| PROVENANCE | A single ADDITIVE, metric-neutral evolution of the spine satisfies three predictions at once: P1 re-aggregating every existing experiment's raw_samples is byte-identical on all pre-existing summary fields (C1 not broken); P2 a (probe,params) group disagreeing on (unit,clock,includes_startup,overhead_removed) raises a clear ValueError instead of silently pooling (kills the stats.py:97 units-lie); P3 a metric-neutral `value`-channel sample with metric=peak_rss_bytes/unit=bytes flows through aggregate() without KeyError and stays LABELLED bytes. | `confirmed` | Iteration 7 (`experiments/provenance`). Implemented the designed-in-CLAIMS evolution in `stats.py` (additive `_value` value-channel with seconds_per_op fallback; `_provenance` with time-defaults for legacy samples; `aggregate()` refuses to pool mismatched provenance; five provenance fields carried into each summary as NEW keys only) plus a defensive additive guard in `report.plot_scaling` (refuse to co-plot mismatched units). Baseline captured with the PRE-edit aggregate. **P1 PASS:** membership+cli_search+service_regime re-aggregate byte-identical → `back_compat_diff.json` empty (0 differ), additive, C1 preserved. **P2 PASS:** a seconds+bytes group raises `ValueError: refusing to pool mismatched provenance …` (`refusal_log.txt`). **P3 PASS:** a unit=bytes peak-RSS batch aggregates with no KeyError, stays unit=bytes/metric=peak_rss_bytes, medians in byte range (15.5M/40.1M/141.9M). Out-of-band: legacy membership plot re-renders, format_table unaffected, report guard fires on mixed units. Artifacts: `results/provenance/{baseline_summaries.json, back_compat_diff.json, refusal_log.txt, bytes_summary.json, findings.txt, membership_replot.png}`. **This FIXES the Iter-4 NONTIME-METRIC refutation by deliberate infrastructure (not a hack — proven by the byte-identical P1 regression), and lifts C1's "time-only / within-Q0" caveat.** |
| C5 | The correctness gate generalizes beyond library calls (e.g. comparing CLI tools that should produce equivalent output). | `confirmed` | Genuinely applied, not just declared: before timing, each probe command is run via subprocess, its stdout normalized and sha256-digested, and a mismatch raises `CORRECTNESS GATE FAILED`. `rg -c ERROR` and `grep -c ERROR` emit the same matching-line count and pass — the CLI analogue of the library hit-count gate. (R&S sharpens this for the general CLI case to semantic equivalence over a canonical form — color-off, path-normalized, sorted match set — since rg colorizes and reorders by default.) **Scope boundary (Iter 11, APPROXIMATE-RANDOMIZED-CORRECTNESS-GATE `confirmed`):** the gate generalizes across *regimes* but not across *correctness models* — it assumes a single canonical correct output. A target correct only *in distribution* (ANN at recall ≥ 0.90) cannot pass it (output is non-identical and, if stochastic, changes every run), forcing the gate off; a quality/tolerance contract is needed for that target class.) |
| NONLINEAR-BATCH-AMORTIZATION | The LIBRARY headline `value = elapsed/N` (core.py) is treated as batch-invariant — a property of the operation, independent of the calibrated batch N. Falsifiable: for a workload with within-batch amortization (fixed per-batch loop/timer overhead), `seconds_per_op(N)` varies monotonically with N by more than the bootstrap CI, AND the `run_suite` headline median shifts >~1.5x when only the calibration knob `min_batch_time` is changed — while the correctness gate still passes. | `partial` | Iteration 10 (`experiments/nonlinear_batch`), pure read of the spine, UNTOUCHED (sha256 of core/stats/report byte-identical before/after: core `d3087dc1…`, stats `2b211116…`, report `0f695d55…`). Two pure/idempotent workloads: a `tiny` op (≈0.1µs arithmetic, per-batch fixed cost large relative to per-op cost) and a `mem` numpy-sum over an array past L1/L2. **Conjunct A TRUE (naive batch-invariance is FALSE at fixed B):** a controlled fixed-batch sweep B∈{1,2,4,…,16384} (40 reps each, fed through unmodified `aggregate()`) shows the `tiny` per-op median falling 125ns→34.2ns (ratio 3.66x) with DISJOINT Bmin/Bmax CIs (change/CI-width = 11.5) — per-op cost is determined by B, not by the operation, for timer-overhead-dominated ops. The `mem` op (per-op cost dwarfs per-batch overhead) is flat (1.04x), bounding the effect to the overhead-dominated regime. **Conjunct B FALSE (the spine self-defends the headline):** running `core.run_suite` on the same probes with `min_batch_time` ∈ {0.0002, 0.002, 0.02, 0.2} shifts the headline median only 1.001x–1.082x (all < 1.1x), because `min_batch_time` calibration auto-grows the batch (e.g. tiny: 8192→8.4M) until the per-batch overhead is amortized away. So it is neither the full REFUTED (headline NOT shifted >1.5x) nor the full CONFIRMED (per-op NOT flat across fixed B). Correctness gate ran, not declared: 8 `run_suite` invocations (2 workloads × 4 knobs), each digest-comparing two distinct code paths (tiny `x*x+x` vs `x*(x+1)`; mem whole-sum vs strided-halves) — all PASS. **Net:** `elapsed/N` is batch-DEPENDENT at small fixed B, but the spine's `min_batch_time` calibration is a self-defense that keeps the production headline stable. The amortization assumption holds *only because* calibration drives N into the linear regime — it is not a property of the operation. Artifacts: `results/nonlinear_batch/{raw_samples.json, stats.json, seconds_per_op_vs_batch.png, findings.json}`. Productive caveat (THEORY): the LIBRARY headline is sound only when calibration has grown N past the overhead-dominated knee; a low/fixed `min_batch_time` (or an uncalibrated batch=1 slow-op path) can report an N-artifact. A linearity/knee check on the batch sweep (Criterion-style slope-fit) would surface this; it rescues only the linear case. |
| APPROXIMATE-RANDOMIZED-CORRECTNESS-GATE | The runner's correctness gate (core.py:111-122) admits only bit-identical outputs via exact `sha256(repr(output))` equality. For a target correct only *in distribution* (ANN search at a fixed recall target), two implementations BOTH correct by the domain's real criterion (recall@k ≥ 0.90 vs brute-force ground truth) produce non-identical output and the gate raises `ValueError`, refusing to compare them; a stochastic probe is even non-self-consistent across runs; and once the gate is bypassed (the only way to benchmark such a target) the spine still emits a confident bootstrap CI carrying zero correctness guarantee. | `confirmed` | Iteration 11 (`experiments/approx_correctness`), LIBRARY/in-process, spine UNTOUCHED (sha256 of core/stats/report byte-identical before/after: core `d3087dc1…`, stats `2b211116…`, report `0f695d55…`; run.py asserts `spine_unchanged=True`). Target: M=2000 random 16-dim float32 vectors, Q=50 queries, k=10; `exact` = brute-force L2 top-10 (ground truth), `approx` = random-projection LSH (16→8 dims, keep 600 candidates, re-rank exactly), tuned to recall in (0.90, 1.0). **All four pre-registered predictions met.** (A) recall@10 of approx vs exact = **0.9400** (≥ 0.90 → both domain-correct) yet outputs are NOT bit-identical. (B) `run_suite([exact, approx], grid)` raised `ValueError` containing **"CORRECTNESS GATE FAILED"** (`is_correctness_gate=True`) — the two correct-in-distribution probes cannot be compared. (C) a stochastic probe (`rng_seed=None`, fresh randomness inside `invoke`) yields differing digests across two calls (`bad315883878dde0` vs `abb888f8c4d16b82`) — non-self-consistent under the gate, so even a *single* approximate probe trips it. (D) bypassing via single-probe `run_suite` → `aggregate()` still emits a full summary for `approx` with `ci_low/ci_high` (median **3.37 ms**, CI **[3.367, 3.380] ms**) — a confident CI with the correctness guarantee silently dropped. Confirmed in code (grep): the gate is binary `sha256(repr(output))` equality with NO tolerance/recall/quality/isclose/rel_tol hook in core.py or stats.py. The binary-equality gate cannot place this correct-in-distribution target class, and bypassing it yields a confident-but-unguarded CI. Productive: motivates a queued **APPROX-CORRECTNESS-GATE** spine evolution (a quality/tolerance contract on `Probe` — compare a quality metric to a threshold, not digest equality). Attacks C5's binary-equality assumption (the gate generalizes across regimes but not across *correctness models*). Artifacts: `results/approx_correctness/{raw_samples.json (80 samples), stats.json, report.json}`. |
| RATIO-METRIC-ESTIMATOR | For a ratio-of-totals headline (throughput req/s, bytes/s, hit-rate, utilization) whose per-window denominators vary, the spine's default estimator is wrong in BOTH point and interval: feeding per-window rates (`value=num_i/den_i`) through the unmodified `aggregate()` gives a median/mean of rates that differs from the true `total_num/total_den` by >2×, and the median's 95% bootstrap CI covers the true ratio in ~0% of trials. A paired (num_i,den_i) resample bootstrap recovers ~0.95 coverage. The denominator is structurally invisible — it rides outside the single `value` channel and no provenance key inspects it. | `confirmed` | Iteration 9 (`experiments/ratio_metric`), pure-statistics, spine UNTOUCHED (sha256 of core/stats/report byte-identical before/after: core `d3087dc1…`, stats `2b211116…`, report `0f695d55…`). Synthetic throughput with denominator/rate correlation (the congestion pattern that makes the trap bite): FAST class (~50 short windows, ~1000 req/s, ~100 req each) + SLOW class (~5 long windows, ~100 req/s, ~1000 req each), mean-1 lognormal noise on durations (seed varied per trial). Closed-form true headline R*=181.82 req/s, cross-checked vs mean realized ratio over 50 datasets (rel-err 0.022). Each window mapped into the schema the ONLY way it allows: `value=rate_i`, `metric=throughput`, `unit=req_per_s`, with num/den keys that `aggregate()` IGNORES. **CONFIRMED on all three pre-registered clauses:** median-of-rates mean relative bias = 424% (≫200%); spine median-CI coverage of R* = **0.000** (≪0.10); paired ratio-of-totals bootstrap coverage = **0.983** (≥0.90). Representative trial: median-of-rates 848 vs R*=182 (median CI [613, 1049] excludes R*); paired point 179 (CI [133, 375] contains R*, paired rel bias 11%). Validity gate PASSED: spine reproduced an independent local median/median-CI (proving `aggregate` computes the biased median-of-rates), paired-bootstrap point == direct `sum(num)/sum(den)`, unit/metric provenance preserved. Confirmed in code that `_value` reads only `value` and `_POOL_KEYS=(unit,clock,includes_startup,overhead_removed)` never inspects num/den — the denominator is structurally invisible, a units-lie-grade silent error one level below PROVENANCE that provenance CANNOT catch. Productive: motivates a RATIO-CHANNEL spine evolution (denominator/weight channel + ratio estimator with paired bootstrap, or a Q0 gate routing ratio metrics out). Attacks C1 (fix needs a new channel, not probe-only) and C2 (default median+bootstrap is wrong for this estimand). Artifacts: `results/ratio_metric/{raw_samples.json, summary.json, comparison.json, report.txt}` (no plot — single param point). |

## Spine evolution (deliberate infrastructure, not target hacks)

Per the C1 invariant, editing the spine to fit one target is a refutation. A
*general* improvement that all regimes share is allowed, but must be recorded here.

- **Iteration 3 — tail-CI rule into code (motivated by C2-tail).** Added
  `bootstrap_ci_quantile(xs, q)` to `stats.py` (factored a shared `_bootstrap_ci`
  helper; `bootstrap_ci_median` is now the `q=0.5` special case and is
  bit-identical to before). `aggregate()` now also emits `p90_ci_low/high` and
  `p99_ci_low/high`; `report.format_table` bands the p99 with the p99's own CI
  instead of printing a tail next to a median-labelled CI. Gate: `q=0.5`
  subsumption is exact, and every pre-existing summary field is byte-identical to
  the pre-edit spine (additive change), so no regime regresses — verified by
  re-running `experiments/membership` end-to-end. This is target-agnostic: every
  regime now gets honest tail bands.

- **Iteration 7 — PROVENANCE evolution into code (motivated by the NONTIME-METRIC
  refutation, Iter 4).** Implemented exactly as designed below. `stats.py`:
  `_value(s)` reads the metric-neutral `value` channel, falling back to
  `seconds_per_op` (replaces the hardcoded units-lie at line 97); `_provenance(s)`
  fills `metric/unit/clock/includes_startup/overhead_removed` with time-defaults
  for legacy samples; `aggregate()` raises `ValueError` when a `(probe,params)`
  group disagrees on `(unit,clock,includes_startup,overhead_removed)`; the five
  provenance fields are carried into each summary as NEW keys only. `report.py`:
  `plot_scaling` refuses to co-plot mismatched units (additive guard). Gate: every
  pre-existing summary field is byte-identical across membership, cli_search, and
  service_regime (`back_compat_diff.json` empty) — additive, no regime regresses.
  Target-agnostic: every regime is now honestly metric-aware, and the units-lie is
  a hard error. See claim **PROVENANCE** (`confirmed`).

### Resolved follow-up (was: motivated by NONTIME-METRIC refutation, Iteration 4)

- **PROVENANCE evolution — DONE in Iteration 7 (above).** The original design,
  kept for the record: extend the raw-sample schema with a metric-neutral `value`
  channel plus `metric`/`unit` (and `clock`/`includes_startup`/`overhead_removed`
  provenance), have `aggregate()` read `value` (falling back to `seconds_per_op`
  for back-compat) and **refuse to pool** samples in a `(probe,params)` group that
  disagree on `(unit, clock, includes_startup, overhead_removed)`. That single,
  general change makes the schema honestly metric-agnostic for every regime and
  turns the units-lie that `aggregate()` accepted into a hard error. Implemented as
  deliberate infrastructure (all regimes benefit), not bent to the mem target —
  proven by the byte-identical P1 regression.

## How to add a claim

Phrase it as a prediction that an experiment could break. Vague aspirations
("the harness should be ergonomic") are not claims; "a new experiment needs
fewer than N lines of target-specific code" is.

## Open agenda (queued by the loop critic, run wf_f4a3febf — not yet dry)

### Implemented (iteration: fix-the-useful-few) — the broadly-useful fixes

Discovery was halted here (the critic never goes dry). The three confirmed breaks
that affect *common* metrics were implemented as deliberate spine evolutions and
verified by `experiments/fixes_verify/run.py` (legacy values byte-identical):

- **RATIO-CHANNEL — DONE (`confirmed`).** `stats.py` gains `numerator`/
  `denominator` channels + `ratio_of_totals_ci`; ratio groups report
  `sum(num)/sum(den)` with a paired bootstrap CI (rel err 4.7% vs the old
  median-of-rates' 459%), flagged `is_ratio`. Closes agenda item 8 / C8.
- **BATCH-HOMOGENEITY-GUARD — DONE (`confirmed`).** `aggregate()` refuses a
  group mixing `batch` sizes. Closes the BATCH-HOMOGENEITY follow-up.
- **APPROX-CORRECTNESS-GATE — DONE (`confirmed`).** `Probe.quality` + `run_suite
  min_quality`; approximate probes admitted on a quality bar, digest gate kept as
  default. Closes the APPROXIMATE-RANDOMIZED-CORRECTNESS-GATE follow-up.

Remaining items below are the *niche / scope-boundary* breaks deliberately left
open (estimate-vs-bound, non-stationarity, device clocks, vector/Pareto, …) — see
METHODOLOGY.md "Known limits" for the explicit scope call.

### Remaining (lower-value / scope decisions)

Ordered by value; the first is the prerequisite for the rest.

1. **PROVENANCE — DONE (Iteration 7, `confirmed`).** The metric-neutral spine
   evolution is implemented and verified (P1/P2/P3 all pass). No longer open.
2. **PROVENANCE-VALIDATE-NONTIME (forced next)** — now unblocked by Iter 7. Re-run
   `mem_metric` (real peak RSS via `/usr/bin/time -l`) through the evolved spine
   and confirm the NONTIME-METRIC refutation flips on REAL data (Iter 7 used a
   synthetic bytes batch for P3). Re-tests C1 across a metric family end-to-end.
3. **BATCH-HOMOGENEITY — DONE (Iteration 8, `refuted`).** Promoted to a tracked
   claim and tested: `aggregate()` does NOT enforce batch homogeneity — it silently
   pools a group mixing batch=1 and batch=1000 (`pooled_n=120`, no ValueError),
   while the Iter-7 provenance guard still fires on a unit mismatch, isolating
   `batch` as the one unguarded dimension. Follow-up (queued spine evolution): add
   a batch-homogeneity check to `aggregate()` parallel to `_POOL_KEYS` — either
   refuse a mixed-batch group, or slope-fit across heterogeneous iters
   (Criterion-style) when that is the intent. Design like the tail-CI rule;
   designing it in-experiment would invalidate the refutation.
4. **ESTIMATE-VS-BOUND** — R&S has no gate separating a statistical estimate from
   a guaranteed bound. Attack with hard-real-time WCET / safety: R&S emits p99+CI
   but the required answer is a sound worst-case upper bound sampling can't give.
   Add a Q0 epistemics gate or scope out explicitly.
5. **IID-BOOTSTRAP / NON-EXCHANGEABLE-OPS** — DONE (Iter 6, `partial`). The i.i.d.
   under-coverage blind spot is demonstrated; a block bootstrap helps but
   under-corrects at high ρ. Follow-up: a sanctioned, general **block-bootstrap
   option** (or an effective-sample-size / autocorrelation warning) for the
   backbone, with block length / n guidance so it actually reaches ~0.95 — this is
   spine evolution to design like the tail-CI rule was.
6. **CONTENTION-AUTOCORRELATION** — partially subsumed by IID-BOOTSTRAP (Iter 6
   showed the too-narrow CI on AR(1) trajectories). A SERVICE-regime variant on
   *real* autocorrelated load (not synthetic) would extend C2/C2-tail to live data.
7. **DEVICE-CLOCK / ASYNC-ACCELERATOR** — GPU/accelerator kernels break "runner
   owns the clock"; `clock(wall|cpu)` has no `device` value. Fold `clock=device`
   + a device-event collector seam into PROVENANCE, or scope out.

### New breaks (queued by the loop critic, run wf_a9286aa6 — highest first)

8. **RATIO-METRIC-ESTIMATOR — DONE (Iteration 9, `confirmed`).** Confirmed on all
   three clauses: median-of-rates bias 424%, spine median-CI coverage of R* 0.000,
   paired ratio-of-totals bootstrap coverage 0.983. The denominator is structurally
   invisible (`_value` reads only `value`; `_POOL_KEYS` never inspects num/den), so
   this is a units-lie-grade silent error provenance cannot catch. Follow-up
   (queued spine evolution): a **RATIO-CHANNEL** — add a denominator/weight channel
   to the schema plus a ratio-of-totals estimator with a paired (num,den) bootstrap,
   OR a Q0 gate that routes ratio-of-totals metrics out of the scalar path. Design
   like the tail-CI and block-bootstrap rules; building it in-experiment would
   invalidate the refutation. Now queued alongside the batch-homogeneity guard and
   the block-bootstrap option below.
9. **SINGLE-SHOT / NON-REPEATABLE** — cold-start, crash-recovery, time-to-first-
   JIT-steady-state: measuring perturbs the population so n is effectively 1 and
   the bootstrap CI is undefined. R&S Q4 splits fast/slow but never asks "is this
   repeatable / non-destructive?" Add a repeatability gate or scope out.
10. **NONLINEAR-BATCH-AMORTIZATION — DONE (Iteration 10, `partial`).** `elapsed/N`
    IS batch-dependent at small fixed B (tiny op: 125ns→34.2ns, 3.66x, disjoint
    CIs) — the naive batch-invariance of the per-op number is false for
    overhead-dominated ops — BUT the `run_suite` headline is stable across the
    `min_batch_time` knob (1.001x–1.082x, all <1.1x) because calibration auto-grows
    N past the overhead-dominated knee. Neither full refute nor full confirm:
    `elapsed/N` is sound only because calibration self-defends it. Energy-under-DVFS
    was out of scope (no power counter on this Mac). Follow-up (queued, optional
    spine evolution): a linearity/knee check on a batch sweep (Criterion-style
    slope-fit) that flags an uncalibrated or fixed-low `min_batch_time` reporting an
    N-artifact — rescues only the linear case. Design like the tail-CI rule.
11. **VECTOR / PARETO HEADLINE** — rate-distortion curves (lossy codec, ML
    quantization) where "performance" is a frontier, not a scalar, violating the
    one-value-per-sample contract Q0 presumes. Extend the schema/report, or scope out.
12. **APPROXIMATE / RANDOMIZED-CORRECTNESS GATE — DONE (Iteration 11, `confirmed`).**
    All four predictions met: an ANN target whose `approx` probe has recall@10=0.9400
    (≥0.90, both domain-correct) (A) produces non-bit-identical output, so (B)
    `run_suite([exact, approx])` raises "CORRECTNESS GATE FAILED"; (C) a stochastic
    probe's digest changes across runs (non-self-consistent); (D) bypassing the gate
    still yields a confident bootstrap CI (median 3.37 ms, CI [3.367, 3.380] ms)
    carrying zero correctness guarantee. The gate is binary `sha256(repr(output))`
    equality with no tolerance/recall/quality hook in core.py or stats.py. Follow-up
    (queued spine evolution): an **APPROX-CORRECTNESS-GATE** — a quality/tolerance
    contract on `Probe` (compare a quality metric to a threshold, not digest
    equality), e.g. an optional `quality(output)->float` + `min_quality` on the
    Probe contract, with the digest gate kept as the default for exact targets.
    Design like the tail-CI rule; building it in-experiment would invalidate the
    confirmation.
13. **SUITE-GEOMEAN / CROSS-PROBE HEADLINE** — attack with a benchmark-suite
    comparison: geometric mean of per-benchmark speedups of A vs B across N
    benchmarks (SPEC / compiler-flag style). Extend the spine with a cross-group
    estimator + paired-across-benchmark bootstrap, or scope out.
    Why: `aggregate()` groups strictly by `(probe,params)` and never aggregates
    across groups; report compares lines but computes no cross-group ratio. The
    canonical "is X faster overall" headline is a summary-of-summaries with a CI
    needing paired resampling across benchmarks — distinct from RATIO-METRIC.
14. **SATURATION-KNEE / INVERTED-INDEPENDENT-VARIABLE** — attack a service target
    whose headline is the arrival rate at which p99 first breaches an SLO: a
    search/inversion over the load axis, not a measurement at a fixed param. Add a
    closed-loop search seam + crossing-point CI, or scope out.
    Why: R&S Q3 routes "latency under an arrival rate" but has no notion of the
    rate itself being the unknown solved for. A function-inversion outcome with its
    own CI has no representation; a common capacity-planning question is unplaceable.
15. **MULTIPLICITY / FALSE-DISCOVERY-RATE** — run a CI perf-regression gate over
    N≈300 benchmarks vs a baseline, flagging any whose per-(probe,params) 95% CI
    excludes it; with no real regression, ~5% fire by chance. Add a family-wise /
    FDR layer (Holm or Benjamini-Hochberg over the per-group CIs) or scope out.
    Why: the commonest real use (block-merge regression gates over hundreds of
    benchmarks) is statistically unsound under independent-per-group CIs; distinct
    from SUITE-GEOMEAN (one ratio) — this is error-rate control across decisions.
16. **ANYTIME-ALGORITHM / QUALITY-TIME COUPLING** — attack with a SAT-solver-with-
    timeout, iterative optimizer, MCTS, or progressive renderer whose output quality
    rises with granted time. Add a "quality at budget T" / "time-to-quality-Q"
    contract or scope out.
    Why: granted time is an input to the output, so the fixed-output correctness
    gate and the runner-owns-the-clock timing stage stop being independent — a
    genuine break of the spine's foundational stage separation, untouched elsewhere.
17. **CLOCK-SKEW / MULTI-CLOCK** — attack with an end-to-end span across two+
    machines (microservice trace, distributed RPC) where each hop is stamped by a
    different skewed wall clock; naive subtraction yields negative/inflated latency.
    Add a clock-domain/skew model (or restrict to single-clock spans) or scope out.
    Why: a common production headline (cross-service p99) is undefined under the
    single-authoritative-clock assumption; distinct from DEVICE-CLOCK (item 7, a
    device with no clock) — this is multiple disagreeing wall clocks.

### New breaks (queued by the iteration 3 critic — highest first)

18. **NON-STATIONARITY / DRIFT GATE** — feed a non-stationary per-probe series
    (synthetic linear trend + a real throttling/warmup-incomplete target) through
    the spine; check whether any guard flags a still-drifting group. Add a
    steady-state/stationarity gate (split-half or Mann-Kendall trend test, or
    warmup-convergence detection) that refuses/flags a drifting group.
    Why: every CI the spine emits presumes stationarity (even the block bootstrap),
    yet thermal throttling / JIT tier-up past warmup=5 / compaction make the
    mean a moving target; distinct from IID-BOOTSTRAP/CONTENTION (stationary AR(1)).

19. **MULTIMODAL / BIMODAL DISTRIBUTION** — feed a deterministic bimodal mixture
    (fast-path/slow-path: cache hit/miss, branch predicted/mispredicted) through
    `aggregate()`; the median lands in the empty valley with a deceptively tight CI.
    Add a modality/dispersion gate (bimodality coefficient or dip test) that refuses
    a single central-tendency headline, or reports per-mode summaries.
    Why: bimodality is endemic at any cache/branch/IO boundary and the headline is
    structurally meaningless yet passes every guard; distinct from C2-tail (single
    heavy-tailed mode).

20. **COORDINATED OMISSION / SAMPLING-PROCESS DEPENDENCE** — a closed-loop SERVICE
    target where the generator stalls when the system stalls, so would-be-slow
    requests are never issued and the tail is under-sampled. Check whether the
    SERVICE regime records open-loop response time (incl. queue wait) or only
    service time. Add a Q-gate forcing open-loop / constant-arrival generation with
    intended-vs-actual send time, or a correction.
    Why: the bias is in data collection, not in `aggregate`, so the statistical
    layer cannot detect it; it directly undercuts the confirmed SERVICE-regime
    tail-CI story and is distinct from autocorrelation and multi-clock skew.

21. **INPUT-DISTRIBUTION-DEPENDENT / ADVERSARIAL WORST-CASE** — a target whose cost
    is a function over input space (hash table with colliding keys, quicksort
    adversarial pivots, regex catastrophic backtracking): show median over random
    inputs is fine while the adversarial input the framework can't request blows up.
    Add a "workload-is-the-unknown" gate or scope out.
    Why: R&S Q3 presumes params pin the workload, but here the input distribution is
    the contested unknown and the headline needs search/adversarial generation, not
    sampling a fixed param point; distinct from ESTIMATE-VS-BOUND (sound bound vs
    estimate) — here the framework cannot even state the question.
