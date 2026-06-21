# Experiment log

Append-only record of iterations. Each entry: the question, what we did, the
result, and which claims it moved.

## Iteration 0 — Draft proposal (orchestrate workflow)

- **Question:** How should a generalizable performance-evaluation harness be
  structured for any codebase?
- **Method:** Multi-agent research + debate + synthesis (41 agents).
- **Result:** Produced a draft architecture ("Stratum"); the verifier panel
  returned `needs_revision`, with implementability the laggard.
- **Learning:** A single one-size-fits-all architecture is the wrong target. We
  need a *decision framework* selecting among regimes. → seeded C-series claims.

## Iteration 1 — Membership experiment (library regime)

- **Question:** Do the spine's contracts survive contact with a real target?
- **Method:** Built the four-stage spine and a probe comparing list/set/dict
  membership across container sizes 100..100,000. Ran it.
- **Result:** Clean O(n) for list, O(1) for set/dict. The correctness gate
  passed; the spine was not modified to add the experiment.
- **Moved:** C1 → `partial` (confirmed for the library regime).

## Iteration 2 — Existing tools, build-vs-buy, and the CLI regime

- **Question:** (a) What do mature tools actually guarantee, and when should we
  wrap one vs build our own? (b) Can our single raw-sample schema ingest a
  genuinely external tool's output (CLI regime via hyperfine) without changing
  the spine?
- **Method:** Authored the **REGIME-AND-SOURCING (R&S)** decision framework
  (Q0 metric gate + Q1–Q5 regime selector + wrap/build rule + decision table +
  7 worked decisions). Built a CLI regime: a new adapter
  `src/harness/cli_regime.py` wraps **hyperfine** and maps its per-command
  `times[]` into the existing raw-sample schema; `experiments/cli_search/target.py`
  benchmarks `rg` vs `grep` counting matches over corpora of 2k–1M lines, with a
  pre-timing correctness gate. The three spine files were not touched.
- **Result:** Confirmed. The spine (core.py, stats.py, report.py) is byte-for-byte
  unchanged before and after a fresh run; the experiment exits 0 and writes
  `results/cli_search/{raw_samples.json, stats.json, scaling.png}`. hyperfine
  samples flowed through the unchanged `aggregate()` and reporter. The correctness
  gate ran real subprocesses, agreed on match counts, and passed.
- **Headline numbers (median wall-clock per invocation):** grep wins at small
  inputs (startup-dominated) — 2k lines: grep 1.29 ms vs rg 2.50 ms. ripgrep wins
  decisively once work dominates — 200k lines: rg 3.86 ms vs grep 19.95 ms; 1M
  lines: rg 10.06 ms vs grep 99.76 ms (~10×). Crossover near 20k lines (rg 2.60 ms
  vs grep 2.93 ms). CIs are tight and cleanly separate the two at every size.
- **Moved:** C3 → `confirmed` (normalization layer ingests an external tool's
  output with no spine change). C4 → `confirmed` (R&S framework authored and
  decidable). C5 → `confirmed` (correctness gate generalizes to CLI tools).
  C1 → `confirmed` (holds for a second regime; only the adapter + target were
  added). C2 → `partial` (the median+bootstrap CI worked unchanged on the CLI
  regime; tail-CI case still untested).

## Iteration 3 — The tail-CI gap (C2-tail) and forcing the tail rule into code

- **Question:** C2 says "median + bootstrap CI is an adequate default across
  regimes." Is it still adequate when the reader's headline is a TAIL statistic
  (p99) rather than the center? The spine prints p90/p99 but bands only the
  median; if a reader reads the printed CI as the uncertainty on p99, is that
  band honest?
- **Method:** Pure-statistics stress test that touches NO spine files
  (`experiments/tail_ci/{target.py,run.py}`). Two heavy-tailed
  `seconds_per_op` models — bimodal (95% fast lognormal + 5% ~10× slow tail, a
  GC/scheduler hiccup) and a single fat lognormal (σ=1.5). TRUE median and TRUE
  p99 from a 5,000,000-draw reference. K=200 independent experiments per model,
  n=2000 each, built as `raw_samples` in the load-bearing schema and fed through
  the **unmodified** `aggregate()` (re-exercises C1). A reference
  `bootstrap_ci_quantile(p99)` was defined *only in the experiment* and measured
  against the spine's median band. Validity gate: the spine reproduced an
  independent local computation of median/p99/median-CI exactly for both models.
- **Result — C2-tail CONFIRMED (sharpens C2 to `confirmed (scoped)`).** Both
  models: `cov_median`≈0.95 (the median CI is correct *for the median*),
  `cov_median_for_p99`=0.00 (it essentially never contains the true p99),
  `cov_qci_for_p99`=0.92–0.93 (the reference p99 CI repairs coverage), and the
  per-experiment p99 sampling-SD was 23×–40× the mean median-CI width — the real
  p99 wobble dwarfs the only band the spine offered. Relative widths: median CI
  ~3%/17% of the value vs p99 CI ~30%/49%. Artifacts:
  `results/tail_ci/{coverage.json, tail_ci.png}`.
- **Spine evolution (deliberate, general — documented in CLAIMS.md).** The
  confirmation forced THEORY's tail-CI rule into code. Added
  `bootstrap_ci_quantile(xs, q)` to `stats.py` via a shared `_bootstrap_ci`
  helper (`bootstrap_ci_median` is now the q=0.5 special case, bit-identical to
  before); `aggregate()` now emits `p90_ci_low/high` and `p99_ci_low/high`; and
  `report.format_table` bands the p99 with the p99's own CI. Gate: q=0.5
  subsumption is exact and every pre-existing summary field is byte-identical to
  the pre-edit spine, so the change is additive and no regime regresses —
  verified by re-running `experiments/membership` end-to-end (its list_lookup
  p99 CIs are visibly far wider than the median CIs, as expected).
- **Moved:** added **C2-tail** → `confirmed`. C2 → `confirmed (scoped)` (adequate
  for a central-tendency headline; the "for the median" label is load-bearing,
  and tail headlines now get their own band). C1 re-touched (the experiment ran
  on the unmodified spine; the later spine edit is sanctioned infra evolution,
  not a target hack).

## Iteration 4 — Non-time metric (peak RSS): the schema is not metric-agnostic

- **Question:** Claim NONTIME-METRIC. THEORY's Q0 gate says a non-time headline
  metric must be carried as `metric`+`unit`+`value`, not forced into
  `seconds_per_op`. Is that gate enforced anywhere in code, or only aspirational?
  Concretely: can an honest peak-RSS-in-bytes sample flow through the unmodified
  spine?
- **Method:** New regime adapter `experiments/mem_metric/{target.py,run.py}` —
  LIBRARY/in-process probe wrapping a subprocess measured by an external tool
  (`/usr/bin/time -l`, macOS "peak memory footprint" in bytes). For each
  `size_mb` in {8,32,128,256}, spawn a child that allocates and touches that many
  MiB then `os._exit(0)`; parse peak RSS; 5 reps each. Emit HONEST samples
  `{probe,params,rep,batch,metric=peak_rss_bytes,unit=bytes,value=<bytes>}` with
  no `seconds_per_op`. STEP 1: feed them straight into the unmodified
  `aggregate()`. STEP 2: the only spine-free workaround — copy bytes into a
  `seconds_per_op` field and re-run. STEP 3: sha256 the three spine files before
  and after to prove no edits. Validity gate: peak RSS must be deterministic and
  monotonic in the allocation size.
- **Result — NONTIME-METRIC REFUTED (as predicted, productive).** STEP 1:
  `KeyError('seconds_per_op')` at stats.py:97 — the honest non-time sample cannot
  pass through the spine at all. STEP 2: `aggregate()` accepts the mislabeled
  samples silently and reports median/min/p99/CI of bytes wearing a "seconds"
  label (size_mb=256 → median 275,808,904 "seconds"); no guard objects because
  the schema carries no metric/unit and there is no neutral value channel — the
  Q0 gate is designed in THEORY but unenforced in code. STEP 3: core.py/stats.py/
  report.py byte-identical before and after (C1 re-exercised; spine only
  consumed). Validity gate passed: peak RSS strictly monotonic (15.4M < 40.6M <
  141.4M < 275.8M bytes) with <0.6% within-group spread, tracking ~7.5MB baseline
  + allocation. Artifacts: `results/mem_metric/{raw_samples.json,findings.txt,
  stats_units_lie.json}` (no `stats.json` — STEP 1 raised by design).
- **Moved:** added **NONTIME-METRIC** → `refuted`. Opened the PROVENANCE
  follow-up in CLAIMS.md (implement the metric-neutral `value` channel + unit
  guard as general infrastructure). No spine change made this iteration — the
  refutation REQUIRES the spine unchanged (STEP 3 verifies it), so implementing
  provenance here would invalidate the experiment; it is the next iteration's job.

## Iteration 5 — SERVICE/load regime (the third regime), open-loop via vegeta

- **Question:** Claim SERVICE-REGIME. Can the third regime be added probe-only —
  do an open-loop generator's per-request latencies map 1:1 into the existing
  raw-sample schema and flow unchanged through `aggregate()`/`report`, yielding a
  populated p99 + p99-CI on real heavy-tailed data? Refutation = any edit to
  stats.py/report.py, or `aggregate()` choking/mislabeling (the NONTIME-METRIC
  failure mode) for the third regime.
- **Method:** New adapter `experiments/service_regime/{target.py,run.py}`, no
  spine import modified. `target.py` stands up a stdlib `ThreadingHTTPServer` on
  an ephemeral 127.0.0.1 port whose handler sleeps a deterministic, seeded
  heavy-tailed delay (base ~2ms + jitter, 5% log-normal spikes ~20–80ms) to
  guarantee a real tail. The adapter drives it **open-loop** with
  `vegeta attack -rate=… | vegeta encode --to=json` at rates 100/200/300 req/s,
  parses each request's `latency` (ns), and emits one raw-sample
  `{probe:"http_endpoint", params:{rate,duration_s}, rep, batch:1,
  seconds_per_op: latency_ns/1e9}`. `run.py` records sha256 of the three spine
  files, feeds samples straight into `stats.aggregate`, renders the table and
  `plot_scaling` PNG, then re-records sha256 and asserts byte-identity. Two gates:
  per-rate correctness (every request HTTP 200, no transport error) and a validity
  gate that independently recomputes median/p99/median-CI and byte-matches them
  against `aggregate`'s summary.
- **Result — SERVICE-REGIME CONFIRMED.** Spine byte-identical before/after
  (core `d3087dc1…`, stats `542fa4b1…`, report `e93a724d…`); `spine_unchanged:
  true`. n=4800 real request latencies (800/1600/2400 across the three rates);
  `aggregate()` returned non-null p99 + p99_ci natively (no edit needed). Tail is
  real on measured data: p99/median = 14.0/16.2/15.6 (≫3). The spine's p99-CI
  width is 473×/537×/541× the median-CI width — the tail-CI machinery from Iter 3
  is genuinely exercised on live, not synthetic, data. Both gates PASS: 0 non-200
  / 0 transport errors at every rate; validity recompute matches `aggregate` to
  abs diff < 1e-18. Artifacts: `results/service_regime/{raw_samples.json (n=4800),
  stats.json, latency_scaling.png (1040×650)}`. Tool installed: vegeta 12.13.0.
- **Spine change:** none. vegeta latencies fit the CURRENT schema (`seconds_per_op`,
  batch=1) with no provenance edit, so no spine evolution was warranted this
  iteration — the open PROVENANCE follow-up (from Iter 4) is untouched and still
  the next infra step.
- **Moved:** added **SERVICE-REGIME** → `confirmed`. C1 → `confirmed` for a
  **third** regime (probe-only, spine byte-identical). C2-tail re-exercised on
  real data (the p99-CI machinery produces honest, materially wider bands on live
  latencies, not just synthetic draws).

## Iteration 6 — The i.i.d.-bootstrap blind spot under serial dependence (IID-BOOTSTRAP)

- **Question:** Claim IID-BOOTSTRAP. The spine's `aggregate()` resamples raw
  samples i.i.d. (uniform indices with replacement), assuming exchangeability. For
  a state-dependent op *trajectory* (correlated consecutive costs — GC/JIT warmup,
  cache/thermal drift, LSM compaction), is the i.i.d. median bootstrap CI still
  honest, or does it under-cover the true marginal median? Does a moving-block
  bootstrap fix it?
- **Method:** Pure-statistics experiment touching NO spine files
  (`experiments/iid_bootstrap/{target.py,run.py}`). Generative model:
  latency = BASE·exp(z), z a stationary AR(1) process (z_i = ρ·z_{i-1} + ε_i,
  σ=0.4), each path initialized from the stationary distribution. Marginal is
  lognormal, so closed-form TRUE median = BASE = 1e-6 (cross-checked vs a 5M-draw
  reference, rel-err 3.2e-4). Models ρ∈{0.0 (i.i.d. control), 0.7, 0.9}. K=300
  experiments × n=2000 samples, 2000 bootstrap iters, block length L=13 (≈n^(1/3)).
  Samples wrapped in the load-bearing schema (re-exercises C1) and fed through the
  **unmodified** `aggregate()`/`bootstrap_ci_median`; the moving-block bootstrap
  reference lives ONLY in the experiment (mirrors how tail_ci kept
  `bootstrap_ci_quantile` out of the spine). Validity gate: for each model, the
  spine's median/ci_low/ci_high must byte-match an independent local computation
  (<1e-18) before the coverage study runs.
- **Result — IID-BOOTSTRAP `partial` (INCONCLUSIVE per strict pre-registered
  criteria, a genuine finding).** Validity gate PASSES for all three models
  (mismatches={}), so the comparison is valid. The blind spot is real and
  monotone: control ρ=0 cov_iid=0.957 (harness unbiased) → cov_iid=0.657 at ρ=0.7
  → cov_iid=0.397 at ρ=0.9. The i.i.d. CI is too narrow: iid/block width ratio
  0.55 (ρ=0.7) and 0.39 (ρ=0.9); against the empirical between-experiment median
  SD, the i.i.d. width is only 0.26× the correct width at ρ=0.9. The block
  bootstrap improves coverage everywhere (0.40→0.79 at ρ=0.9; 0.66→0.92 at ρ=0.7)
  but UNDER-corrects at the strongest dependence: cov_block=0.787 at ρ=0.9 fell
  short of the pre-registered [0.88,0.97] — the only failing confirmation clause,
  hence `partial` rather than `confirmed`. Refutation conditions NOT met (cov_iid
  far below 0.90; block > iid at every ρ). Artifacts:
  `results/iid_bootstrap/{coverage.json, iid_bootstrap.png}`.
- **Spine change:** none. sha256 of core.py/stats.py/report.py byte-identical
  before and after a fresh run (re-exercises C1); the experiment only consumes the
  spine. A sanctioned, general block-bootstrap option (plus block-length/n
  guidance, or an autocorrelation/effective-sample-size warning) is queued spine
  evolution — designing it here would invalidate this measurement, so it is the
  next infra step, like the tail-CI rule was after Iter 3.
- **Moved:** added **IID-BOOTSTRAP** → `partial`. THEORY gains a serial-dependence
  caveat on every bootstrap CI (the median+bootstrap default is honest only for
  exchangeable samples). Partially subsumes the CONTENTION-AUTOCORRELATION agenda
  item. C1 re-exercised (spine byte-identical).

## Iteration 7 — PROVENANCE: the metric-neutral spine evolution (CONFIRMED)

- **Claim attacked:** PROVENANCE (new). Hypothesis: one ADDITIVE, metric-neutral
  evolution of `stats.py` can simultaneously satisfy three falsifiable
  predictions — P1 back-compat (C1 not broken), P2 honesty-as-hard-error (kill
  the units-lie at stats.py:97), P3 non-time flow (bytes via a value channel,
  labelled bytes). This implements the follow-up designed in CLAIMS after the
  Iter-4 NONTIME-METRIC refutation. Spine change is sanctioned infrastructure.
- **Spine change (deliberate, general — all regimes benefit):** `src/harness/stats.py`
  evolved additively. (a) `_value(s)` reads `s["value"]`, falling back to
  `s["seconds_per_op"]` for legacy samples (was the hardcoded units-lie at line
  97). (b) `_provenance(s)` fills `metric/unit/clock/includes_startup/overhead_removed`
  with time-defaults for legacy samples. (c) `aggregate()` collects the per-group
  provenance and raises `ValueError("refusing to pool mismatched provenance …")`
  when a `(probe,params)` group disagrees on `(unit,clock,includes_startup,
  overhead_removed)`. (d) Each summary now carries those five provenance fields
  (new keys only — nothing renamed or dropped); module docstring schema updated.
  `src/harness/report.py` got one additive guard: `plot_scaling` refuses to
  co-plot lines with mismatched `unit` (legacy unit-less rows plot exactly as
  before). No existing key, value, or plot path changed.
- **Experiment:** `experiments/provenance/{target.py,run.py}`. Pure re-aggregation
  of existing JSON plus two hand-built groups; runtime < 2 s, no new measurement.
  Baseline (`results/provenance/baseline_summaries.json`) was captured with the
  PRE-edit `aggregate()` before any spine change, so P1 is an honest regression.
- **Result — PROVENANCE `confirmed`.** P1 PASS: re-aggregating membership,
  cli_search, and service_regime through the evolved `aggregate()` reproduces
  every pre-existing summary field byte-identically — `back_compat_diff.json` is
  empty (0 experiments differ) → additive, C1 preserved. P2 PASS: a group mixing
  `unit=seconds` and `unit=bytes` raises a clear `ValueError` (logged to
  `refusal_log.txt`) instead of silently pooling — the stats.py:97 units-lie is
  now a refusal. P3 PASS: a `value`-channel / `unit=bytes` peak-RSS batch
  aggregates with no KeyError, stays `unit=bytes` / `metric=peak_rss_bytes`, and
  the medians sit in byte range (15.5M / 40.1M / 141.9M) — not relabelled seconds.
- **Gates:** P1 is itself the validity/correctness gate (byte-identical
  pre-existing fields across three regimes). Additionally verified out-of-band:
  the legacy `membership` plot re-renders (`membership_replot.png`) and
  `format_table` still works (reads only pre-existing fields); the report
  co-plot guard fires on mismatched units.
- **Artifacts:** `results/provenance/{baseline_summaries.json, back_compat_diff.json
  (empty), refusal_log.txt, bytes_summary.json, findings.txt, membership_replot.png}`.
- **Moved:** added **PROVENANCE** → `confirmed`. NONTIME-METRIC stays `refuted`
  (the original probe-only claim was false) but is now FIXED by this deliberate
  infrastructure; the units-lie is closed. C1's "holds within Q0 / time-only"
  caveat is lifted: the spine now carries a non-time metric honestly, by
  evolution-not-hack (proven by the byte-identical P1 regression).

## Iteration 8 — BATCH-HOMOGENEITY: the THEORY invariant is unenforced (REFUTED)

- **Question:** Claim BATCH-HOMOGENEITY (new). THEORY.md:186 asserts "all samples
  in a group share a batch" as an invariant. Is it actually enforced by the spine,
  or only aspirational? Concretely: does `aggregate()` refuse a `(probe,params)`
  group that mixes batch sizes, or silently pool them? `batch` is in the
  raw-sample schema but the Iter-7 `_POOL_KEYS` guard does not list it.
- **Method:** Pure-stdlib experiment touching NO spine files
  (`experiments/batch_homogeneity/{target.py,run.py}`). Two deterministically
  seeded (`random.Random`) cohorts for the SAME `(probe="op", params={"size":1})`
  group with the SAME true 1.0 µs/op, differing ONLY in `batch`: `cohort_fine`
  (n=60, batch=1000, sd≈0.02 µs — tight, averaged over 1000 ops) and
  `cohort_coarse` (n=60, batch=1, sd≈0.40 µs — noisy single-op jitter, clamped
  >0). **Part A:** `aggregate(cohort_fine + cohort_coarse)` inside try/except
  ValueError; record `raised` and pooled n/median/CI. **Part B:** compare the
  pooled CI width against homogeneous baselines `aggregate(cohort_fine)` and
  `aggregate(cohort_coarse)` separately. **Part C (control):** confirm a
  homogeneous batch=1000 group aggregates cleanly, and that injecting a provenance
  mismatch (one `unit=bytes` sample) DOES raise — proving the guard machinery
  works and only `batch` is missing. Validity gate: medians agree within the
  coarse CI width (same central value) AND coarse stdev > 5× fine stdev (genuine
  variance mismatch). Spine sha256 recorded; spine is read-only this iteration.
- **Result — BATCH-HOMOGENEITY REFUTED (the predicted, productive outcome).**
  Part A: `aggregate(mixed)` returned normally, NO ValueError, `pooled_n == 120` —
  the spine silently merges two batch sizes into one summary. Confirmed in code:
  `_POOL_KEYS = ("unit","clock","includes_startup","overhead_removed")` excludes
  `batch`; `aggregate()` groups solely by `(probe,params)` and never inspects
  `s["batch"]`. Part B (harm): pooled median-CI width 2.30e-08 sits between the
  fine baseline (1.44e-08) and coarse baseline (2.65e-07) — too narrow to express
  the coarse cohort's uncertainty yet polluted by it; n=120 is the only tell that
  two incompatible cohorts merged. Part C: homogeneous group aggregates cleanly
  (no raise); the unit-mismatch control DOES raise `ValueError: refusing to pool
  mismatched provenance …`, isolating `batch` as the one unguarded dimension.
  Validity gate PASSED (gate_central and gate_spread both True), so the CI gap is
  variance, not bias. Artifacts: `results/batch_homogeneity/{raw_samples.json
  (120 samples, batch ∈ {1,1000}), stats.json, findings.json}`. No plot (this is a
  spine-level enforcement probe, not a scaling sweep — `plot_scaling` not invoked).
- **Spine change:** none. sha256 of core/stats/report byte-identical before and
  after (core `d3087dc1…`, stats `2b211116…`, report `0f695d55…`); the experiment
  only calls `aggregate()` (re-exercises C1). The fix — an additive batch-
  homogeneity guard parallel to `_POOL_KEYS` — is sanctioned spine evolution
  deferred to a later iteration; applying it here would invalidate the refutation.
- **Moved:** added **BATCH-HOMOGENEITY** → `refuted`. THEORY's batch-homogeneity
  rule (THEORY.md:186) now annotated as stated-but-unenforced, with the harm
  evidence and the queued additive-guard follow-up. Agenda item 3 closed. C1
  re-exercised (spine byte-identical).

## Iteration 9 — RATIO-METRIC-ESTIMATOR: the denominator is structurally invisible (CONFIRMED)

- **Question:** Claim RATIO-METRIC-ESTIMATOR (new). For a ratio-of-totals headline
  (throughput req/s, bytes/s, hit-rate, utilization) whose per-window denominators
  vary, is the spine's default estimator wrong in both point and interval? The
  schema has one scalar `value` slot, so the only way to record a ratio is
  `value = num_i/den_i`; the denominator rides outside the channel. The true
  headline is `total_num/total_den`, whose CI comes from resampling (num,den) PAIRS.
- **Method:** Pure-statistics experiment touching NO spine files
  (`experiments/ratio_metric/{target.py,run.py}`). Generative model with the
  congestion pattern that makes the trap bite: a FAST class (~50 short windows,
  ~1000 req/s, ~100 req each — small denominator, many windows) plus a SLOW class
  (~5 long windows, ~100 req/s, ~1000 req each — large denominator, few windows),
  mean-1 lognormal noise on durations so denominators genuinely vary. Closed-form
  true headline R*=181.82 req/s (cross-checked vs mean realized ratio over 50
  datasets, rel-err 0.022). Each window mapped into the schema the only way allowed:
  `value=rate_i`, `metric=throughput`, `unit=req_per_s`, with num/den keys
  `aggregate()` IGNORES — the demonstration that the denominator is structurally
  invisible. Ran the unmodified `aggregate()` over the representative dataset, then
  a 300-trial coverage study comparing (a) the spine median-CI's coverage of R* vs
  (b) a paired (num,den) resample bootstrap defined ONLY in the experiment (mirrors
  how tail_ci/iid_bootstrap kept their reference estimators out of the spine).
  Deliberately did NOT reuse `report.format_table`/`plot_scaling` — they are
  time-shaped (scale by 1e9, label "ns") and would misrender req/s, itself a minor
  symptom of the same lower-is-better-time assumption. Validity gate: spine
  median/median-CI must byte-match an independent local computation, paired-bootstrap
  point must equal direct `sum(num)/sum(den)`, unit/metric provenance preserved.
- **Result — RATIO-METRIC-ESTIMATOR CONFIRMED (all three pre-registered clauses).**
  Median-of-rates mean relative bias = **424%** (≫200%); spine median-CI coverage
  of R* = **0.000** (≪0.10); paired ratio-of-totals bootstrap coverage = **0.983**
  (≥0.90). Representative trial: median-of-rates 848 vs R*=182, median CI [613, 1049]
  excludes R*; paired point 179 (CI [133, 375] contains R*, paired rel bias 11%).
  Validity gate PASSED (spine_mismatches={}, paired point == sum/sum, unit_ok).
  Confirmed in code that `_value` reads only `value` and `_POOL_KEYS=(unit,clock,
  includes_startup,overhead_removed)` never inspects num/den — the denominator is
  structurally invisible, a units-lie-grade silent error one level BELOW PROVENANCE
  that provenance cannot catch (the unit tag describes the `value` channel, not the
  missing denominator). Artifacts: `results/ratio_metric/{raw_samples.json (55
  windows), summary.json, comparison.json, report.txt}`. No plot (single param point).
- **Spine change:** none. sha256 of core/stats/report byte-identical before and
  after a fresh run (core `d3087dc1…`, stats `2b211116…`, report `0f695d55…`); the
  experiment only consumes `aggregate()` (re-exercises C1). The paired ratio-of-
  totals bootstrap and a byte-identical percentile helper live in the experiment so
  any CI difference is attributable only to the estimand.
- **Moved:** added **RATIO-METRIC-ESTIMATOR** → `confirmed`. Attacks C1 (the fix
  needs a new denominator/weight channel — not absorbable probe-only, like the
  NONTIME-METRIC family boundary) and C2 (the default median+bootstrap is the wrong
  estimator for a ratio-of-totals estimand). THEORY gains a ratio-of-totals caveat
  on every bootstrap CI and a second Q0 clause ("is the headline a ratio of
  totals?"). Agenda item 8 closed; queued a **RATIO-CHANNEL** spine evolution
  (denominator/weight channel + ratio estimator with paired bootstrap, or a Q0 gate
  routing ratio metrics out) alongside the batch-homogeneity guard and the
  block-bootstrap option — designing it here would invalidate the refutation.

## Iteration 10 — NONLINEAR-BATCH-AMORTIZATION: elapsed/N is N-dependent, but calibration self-defends the headline (PARTIAL)

- **Question:** Claim NONLINEAR-BATCH-AMORTIZATION (new). The LIBRARY headline
  `value = elapsed/N` (core.py) is presented as a property of the operation,
  independent of the calibrated batch N. Is the per-op number actually N-invariant,
  or is it a modeling artifact of the batch/calibration knob? Two falsifiable
  prongs: (A) does `seconds_per_op(N)` vary with N by more than the bootstrap CI at
  fixed batch? (B) does the `run_suite` headline median shift >~1.5x when only the
  calibration knob `min_batch_time` changes — while the correctness gate passes?
- **Method:** New experiment `experiments/nonlinear_batch/{target.py,run.py}`,
  spine read-only (imports `core._time_batch`, `core.run_suite`, `stats.aggregate`,
  `report.plot_scaling`/`format_table` unchanged — re-exercises C1). Two
  pure/idempotent workloads: `tiny` (≈0.1µs arithmetic, per-batch fixed cost large
  vs per-op cost) and `mem` (numpy sum over an array sized past L1/L2, genuine
  per-op bandwidth cost). **Part 2 (controlled fixed-batch sweep, isolates the
  model):** after one warmup, call `_time_batch` at FIXED B∈{1,2,4,16,64,256,1024,
  4096,16384}, 40 reps each, `seconds_per_op=elapsed/B`, fed through the unmodified
  `aggregate()`; median + bootstrap CI per B, rendered to
  `seconds_per_op_vs_batch.png`. **Part 3 (harness-path knob sweep, shows the knob
  drives the headline):** `core.run_suite` on the same probes with `min_batch_time`
  ∈ {0.0002, 0.002, 0.02, 0.2}; record the calibrated batch and median per knob.
  Correctness gate: each `run_suite` call digest-compares two distinct code paths
  (tiny `x*x+x` vs `x*(x+1)`; mem whole-sum vs strided-halves). Energy-under-DVFS
  was explicitly out of scope (no power counter accessible on this Mac); the attack
  uses loop/timer-overhead amortization plus a memory-bandwidth working set, both
  deterministic and measurable.
- **Result — NONLINEAR-BATCH-AMORTIZATION `partial` (a clean, mechanism-explained
  scoped outcome).** **Conjunct A TRUE:** the `tiny` per-op median falls
  125ns→34.2ns across B=1..16384 (ratio 3.66x) with DISJOINT Bmin/Bmax CIs
  (change/CI-width = 11.5) — naive batch-invariance of `elapsed/N` is FALSE for an
  overhead-dominated op; the per-op number is determined by B. The `mem` op (per-op
  cost dwarfs per-batch overhead) is flat (1.04x), bounding the effect to the
  overhead-dominated regime. **Conjunct B FALSE:** the `run_suite` headline median
  shifts only 1.001x–1.082x across the four `min_batch_time` values (all <1.1x),
  because `min_batch_time` calibration auto-grows the batch (tiny: 8192→8.4M) until
  per-batch overhead is amortized away. So it is neither full REFUTED (headline NOT
  shifted >1.5x) nor full CONFIRMED (per-op NOT flat at fixed B). Correctness gate
  genuinely ran: 8 invocations (2 workloads × 4 knobs), all PASS (2 probes agree
  each). **Net:** `elapsed/N` is batch-DEPENDENT at small fixed B, but the spine's
  `min_batch_time` calibration is a self-defense that keeps the production headline
  stable — the amortization assumption is sound only because calibration drives N
  past the overhead knee into the linear regime, not because it is a property of the
  operation. Artifacts: `results/nonlinear_batch/{raw_samples.json, stats.json,
  seconds_per_op_vs_batch.png (1040×650), findings.json}`.
- **Spine change:** none. sha256 of core/stats/report byte-identical before and
  after (core `d3087dc1…`, stats `2b211116…`, report `0f695d55…`); the experiment
  only consumes the spine (re-exercises C1). Default time provenance (Iter-7) was
  sufficient — no new fields needed.
- **Moved:** added **NONLINEAR-BATCH-AMORTIZATION** → `partial`. THEORY's Q4 gains
  a "`min_batch_time` is load-bearing" caveat (do not shrink the knob to save time;
  do not trust a fixed/uncalibrated batch=1 per-op number for a sub-µs op — both
  report an N-artifact). Agenda item 10 closed. Distinct from BATCH-HOMOGENEITY
  (which is about pooling mixed batches); this is about the per-op value's
  dependence on the single calibrated N. Follow-up (queued, optional): a
  linearity/knee check on a batch sweep (Criterion-style slope-fit) that flags an
  uncalibrated or fixed-low `min_batch_time` reporting an N-artifact.

## Iteration 11 — APPROXIMATE-RANDOMIZED-CORRECTNESS-GATE: the gate assumes one canonical correct output (CONFIRMED)

- **Question:** Claim APPROXIMATE-RANDOMIZED-CORRECTNESS-GATE (new). The runner's
  correctness gate is exact `sha256(repr(output))` equality (core.py:111-122). For
  a target correct only *in distribution* (ANN search at a recall target), two
  implementations that are BOTH correct by the domain's real criterion (recall@k ≥
  0.90 vs brute-force ground truth) produce non-identical output. Does the gate
  refuse to compare them? Is a stochastic probe even self-consistent across runs?
  And once the gate is bypassed (the only way to benchmark such a target), does the
  spine still emit a confident CI carrying no correctness guarantee?
- **Method:** New experiment `experiments/approx_correctness/{target.py,run.py}`,
  LIBRARY/in-process, spine read-only (re-exercises C1). Deterministic numpy
  dataset: M=2000 random 16-dim float32 vectors, Q=50 queries, k=10. `exact` =
  brute-force L2 top-10 (also the ground truth); `approx` = random-projection LSH
  (project 16→8 dims, keep 600 nearest candidates, re-rank exactly), tuned so
  recall@10 lands in (0.90, 1.0). Four steps: (A) compute recall@10 of approx vs
  exact (assert ≥ 0.90 → both domain-correct); (B) `run_suite([exact, approx],
  grid)` in try/except, capture whether "CORRECTNESS GATE FAILED" is raised;
  (C) a stochastic probe (`rng_seed=None`, fresh randomness inside `invoke`) —
  show `_digest(invoke())` differs across two calls; (D) bypass the gate via
  single-probe `run_suite`, then `aggregate()` the approx samples and show a full
  summary with `ci_low/ci_high` is produced. sha256 the three spine files before
  and after.
- **Result — APPROXIMATE-RANDOMIZED-CORRECTNESS-GATE CONFIRMED (all four
  predictions met).** (A) recall@10 = **0.9400** (≥ 0.90 → both domain-correct),
  outputs NOT bit-identical. (B) `run_suite([exact, approx])` raised `ValueError`
  containing **"CORRECTNESS GATE FAILED"** (`is_correctness_gate=True`) — the two
  correct-in-distribution probes cannot be compared. (C) the stochastic probe's
  digests differ across two calls (`bad315883878dde0` vs `abb888f8c4d16b82`) — not
  self-consistent, so even a single approximate probe trips the gate. (D) bypassing
  via single-probe `run_suite` → `aggregate()` still emits a full summary for approx
  with `ci_low/ci_high` (median **3.37 ms**, CI **[3.367, 3.380] ms**) — a confident
  CI with the correctness guarantee silently dropped. grep confirms the spine has
  NO tolerance/recall/quality/isclose/rel_tol hook in core.py or stats.py: the gate
  is binary `sha256(repr(output))` equality. The binary-equality gate cannot place
  this correct-in-distribution target class, and bypassing it yields a
  confident-but-unguarded CI. Artifacts: `results/approx_correctness/{raw_samples.json
  (80 samples = 40 reps × approx + 40 × exact), stats.json, report.json}`. No plot
  (single param point; run.py uses `format_table`, not `plot_scaling`).
- **Spine change:** none. sha256 of core/stats/report byte-identical before and
  after a fresh run (core `d3087dc1…`, stats `2b211116…`, report `0f695d55…`); the
  experiment only consumes the spine and run.py asserts `spine_unchanged=True`. The
  fix — a quality/tolerance contract on `Probe` — is sanctioned spine evolution
  deferred to a later iteration; applying it here would invalidate the confirmation.
- **Moved:** added **APPROXIMATE-RANDOMIZED-CORRECTNESS-GATE** → `confirmed`.
  THEORY's "Correctness gate per regime" section gains a correctness-model boundary:
  the gate (digest or canonical-form) assumes ONE deterministic correct output and
  cannot place a correct-in-distribution target. C5 annotated with the same scope
  boundary (the gate generalizes across regimes but not across correctness models).
  Agenda item 12 closed; queued an **APPROX-CORRECTNESS-GATE** spine evolution
  (optional `quality(output)->float` + `min_quality` on `Probe`, digest gate kept
  as default for exact targets) alongside the batch-homogeneity guard, the
  block-bootstrap option, and the RATIO-CHANNEL.

## Iteration — fix-the-useful-few (three confirmed breaks closed)

- **Question:** Stop discovery (the critic never goes dry); implement the three
  *broadly-useful* confirmed fixes so the harness is trustworthy on common
  metrics, as deliberate spine evolutions that keep legacy results byte-identical.
- **Method:** Implemented in the spine and verified by a single self-contained
  harness, `experiments/fixes_verify/run.py`:
  1. **RATIO-CHANNEL** (`stats.py`): new optional `numerator`/`denominator` raw
     channels + `ratio_of_totals_ci` paired bootstrap. A group whose samples all
     carry the channels aggregates to `sum(num)/sum(den)` with a paired-pair
     bootstrap CI, flagged `is_ratio`, keeping the biased per-rate estimators as
     `naive_*`. Triggered only by the new keys, so nothing legacy changes.
  2. **BATCH-HOMOGENEITY-GUARD** (`stats.py`): `aggregate()` now refuses a
     `(probe,params)` group mixing `batch` sizes (parallel to the provenance
     pool-guard).
  3. **APPROX-CORRECTNESS-GATE** (`core.py`): optional `quality(output, fixture)
     -> float` on `Probe` + `min_quality` on `run_suite`; a quality-gated probe is
     admitted on its score and exempted from bit-equality. The digest gate stays
     the default for exact targets.
- **Result (all verified):** ratio-of-totals recovers the true throughput (rel
  err 4.7% vs the median-of-rates' **459%**) with a CI that covers the truth;
  mixed-batch pooling now raises; an approximate (recall 0.93) probe is admitted
  under `min_quality=0.85`, the default gate stays strict, and an impossible bar
  (0.999) is rejected. Legacy proof: re-aggregating membership / cli_search /
  service_regime reproduces **every stored value identically** (only the
  iteration-7 provenance keys are added). `report.py` untouched.
- **Spine change:** deliberate infrastructure (`core.py`, `stats.py`); `report.py`
  byte-identical. This is sanctioned general evolution, not a per-target hack
  (C1 holds: no experiment edited the spine to fit itself).
- **Moved:** RATIO-CHANNEL, BATCH-HOMOGENEITY-GUARD, APPROX-CORRECTNESS-GATE →
  implemented & `confirmed`. C2 broadened: the spine now offers the correct
  estimator for ratio headlines, not just central-tendency.
