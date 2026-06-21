# Prove the win: faster AND still correct

**Status:** READY
**Loaded when:** after a change, to confirm it is a real, correct improvement (the **prove** step of the SKILL.md loop).

This is the **prove** step of the loop (target → measure → locate → fix → **prove** → defend). You arrive with a change you believe is faster. You leave only when two things hold at once: the change moved the counter you targeted by more than noise, and it still computes the same answer. Either half alone is a failure mode. A speedup inside run-to-run variance is a story you told yourself; a fast wrong answer is not an optimization, it is a bug with good latency.

The gate is one sentence: **ship the change only if (perf delta exceeds noise in the predicted direction) AND (output is still correct under test).** Both clauses, every time. The rest of this leaf is how to establish each clause without fooling yourself.

---

## The combined gate

Run these in order. Stop and revert the moment a clause fails.

> **Counter re-measurement is Linux/perf-flavored.** Steps 1-2 below assume hardware counters read via `perf` (top-down buckets, IPC, HITM, LLC-miss). On a local macOS / Apple Silicon host there is no `perf`/eBPF; reach the same signals through Instruments / `dtrace` / `powermetrics` — see `../environment/local-mac.md`. The gate logic (counter moved in the predicted direction, gain beats noise, still correct) is identical; only the instrument changes.

1. **Re-run the diagnosis, not just the clock.** Re-measure the *specific counter* you set out to move (`../diagnose/index.md`), not only wall time. If you targeted LLC-miss rate, read LLC-miss rate again. Wall time can drop for a reason unrelated to your fix (a quieter machine, a warmer cache, a different input), and it can fail to drop even when your fix worked because a second bottleneck took over. The honest question is "did the mechanism I changed behave as predicted?"
2. **Confirm the counter moved in the predicted direction.** Your fix came with a causal model ("branch-miss 12% is the bottleneck; a branchless state machine cuts it"). Verify the prediction: branch-miss should now be low. If the targeted counter did not move, the fix did not do what you think, even if wall time happened to improve. Find out why before believing the number.
3. **A/B with the harness, old vs new, same everything.** Run baseline and candidate through the same harness, same inputs, same machine, interleaved and randomized so machine drift spreads across both arms instead of landing on one (`benchmark.md`). The harness owns the clock, discards warmup, and calibrates batches so the number reflects the op and not timer resolution. Never compare a number you measured today against one you wrote in a doc last week on a different box.
4. **Require the gain to beat noise.** A point estimate is not a result. Band each arm with a bootstrap confidence interval and require the **CIs to not overlap** (or a paired test below your alpha). If baseline is 100 ms [96, 104] and candidate is 97 ms [93, 101], you have not shown a win; the intervals overlap, so this conservative test has *not demonstrated* a difference — which is not the same as proving the difference is inside the noise (two overlapping 95% CIs can still hide a significant paired difference, so fall back to a paired test below your alpha before concluding "no effect"). Match the statistic to the headline: a tail target (p99) needs a *quantile* CI, not the median's, and a throughput headline needs the ratio-of-totals estimator, not a median of per-window rates (`measurement-integrity.md`).
5. **Run the Over-Optimization Checklist (below).** Each "no" is a reason the measured win may be illusory or not worth its complexity.
6. **Prove still-correct.** Establish the second clause with the correctness techniques in the second half: differential test old vs new, property tests on invariants, floating-point tolerance for reordered math, fuzz the optimized path.
7. **Re-diagnose for the next bottleneck.** A fix shifts the binding constraint. The win you just proved may have uncovered the next one; if you are not done with the target, loop back to `../diagnose/index.md`. If you are done, go to **defend** to lock the gain against regression.

---

## Half 1 — Faster, and real

The trap this half defends against: believing a speedup that is noise, that came from the wrong cause, or that only exists in the benchmark.

### Confirm the cause, not just the effect

A wall-time drop is necessary but not sufficient. Re-run the characterization pass from `../diagnose/index.md` and check the counter your causal model named:

- Targeted **branch-miss** → branch-miss rate should fall in the hot loop; IPC should rise.
- Targeted **LLC-miss / bandwidth** → miss rate or bytes-moved should fall; top-down "memory-bound" share should shrink.
- Targeted **lock-wait / coherence** → lock-wait fraction or HITM events should drop; the scaling curve should straighten.
- Targeted **syscalls / GC** → syscall count or GC-pause fraction should fall.

If wall time improved but the targeted counter did not, you have a *coincidence*, not a fix. Common cause: a warmer cache or a quieter machine on the second run. Re-run interleaved before believing anything.

### A/B fairly, then test for significance

Put both versions behind the same harness and the same inputs. The non-negotiables (warmup discarded, randomized interleaving, the runner owns the clock, representative inputs) live in `measurement-integrity.md`; this leaf just uses them. The statistical bar:

- **Non-overlapping 95% CIs** is the cheap, honest first test for "is there a difference at all." Overlap → not proven, get more samples or accept there is no effect.
- For the headline statistic specifically: median gets a percentile bootstrap CI; a p99 headline gets its own quantile CI (a median CI is typically far too narrow to band a tail — often on the order of 20-40x, though the exact factor is distribution-dependent); a throughput/ratio headline gets a paired ratio-of-totals CI. Banding the wrong statistic is the most common way a "significant" win is fiction.
- Beware **serial correlation**: if samples come from a drifting trajectory (JIT tier-up, thermal throttling, cache warming), an i.i.d. bootstrap *under-covers* and the CI lies narrow. Randomized interleaving breaks some of this; a genuinely non-stationary run needs a block bootstrap or an effective-sample-size warning before you trust the interval.

### The Over-Optimization Checklist

Run this before believing a win is real and worth keeping. Each "no" is a warning that you may be reporting noise or buying complexity for no measured gain.

| Question | If no... |
|----------|----------|
| Did you measure with hardware counters, not just wall time? | Wall time says something changed; counters say *what*. Guess-confirmed-by-wall-time is gambling. |
| Is the code you optimized actually hot? | A 20% speedup of a function that is 0.5% of runtime is 0.1% overall. Confirm it was above threshold on the flame graph. |
| Is the win larger than run-to-run variance? | If variance is ±10% and the win is 5%, you cannot tell whether it worked. Get the CIs to separate or stop claiming a win. |
| Is the benchmark representative of production? | Cold caches, real data distributions, realistic contention, production traffic shape. Microbenchmarks are an *upper bound* on the production win, often a loose one. |
| Is the benchmark open-loop (if latency/tail matters)? | Closed-loop clients throttle their own send rate when the system slows, hiding the tail. A p99 claim needs open-loop load. |
| Did you check what `-O3 -march=native` (and PGO) already does? | Auto-vectorization, devirtualization, inlining often capture the "obvious" win with no code change, and your hand-written version may add nothing. |
| Does the optimization foreclose a simpler one? | Hand SIMD and lock-free code are expensive to change later. Weigh the long-term cost against the measured gain. |
| Is the dominant bottleneck still what you thought? | After one fix the bottleneck shifts. Re-measure before the next change. |
| Is the code already fast enough? | The right amount of optimization is what the target requires, not the maximum the hardware allows. A proven win past the target is complexity with no buyer. |

Every "no" is an invitation to stop. Optimization is a cost paid in complexity, maintenance, and foreclosed flexibility; a real win that nobody needed is still a net loss.

---

## Half 2 — Still correct

A faster function that returns a different answer is not optimized, it is broken. Optimizations are exactly the changes most likely to break correctness silently: they reorder operations, swap data structures, add parallelism, vectorize math, special-case hot paths. The old version is your oracle. Use it.

### Differential testing (old vs new on the same inputs)

Keep the baseline implementation as a reference oracle and assert the optimized version agrees with it over many inputs. This is the single highest-value correctness check for an optimization, because you already have a known-correct implementation: the one you started with.

```python
def test_optimized_matches_baseline():
    for case in generate_inputs(n=10_000):   # cover edge + random
        assert optimized(case) == baseline(case), f"diverged on {case!r}"
```

Cover the inputs that optimizations break first: empty and singleton inputs, sizes around the special-case threshold (the boundary where a fast path kicks in is exactly where it is wrong), sizes around SIMD/unroll widths (n=15,16,17 for an 8- or 16-wide kernel), maximum and overflow-adjacent values, duplicate and already-sorted data. A diff harness that compares outputs *before* it compares timings is the correctness gate the measurement harness already wants (`benchmark.md`); a probe whose output disagrees with its peers is refused before any number is crowned.

When the baseline is too slow to run at production scale, run the differential test at smaller sizes where the oracle is affordable, and lean on property tests (next) for the large-input regime.

### Property-based tests (invariants that must hold for all inputs)

When there is no reference oracle, or to complement one, assert the properties the answer must satisfy regardless of how it was computed. A property test generates hundreds of inputs and shrinks any failure to a minimal counterexample. The tool is language-specific but the discipline is identical: Python's `hypothesis`, Rust's `proptest` or `quickcheck`, and their equivalents elsewhere all generate-and-shrink the same way.

- **Round-trip:** `decode(encode(x)) == x`; `decompress(compress(x)) == x`.
- **Invariant of the result:** a sort output is a permutation of its input and is ordered; an optimized aggregate equals the same aggregate computed the naive way; a cache returns what the underlying source would.
- **Algebraic laws:** idempotence, commutativity where expected, `len(result) == len(input)` for a map.
- **Metamorphic relations** when no oracle exists: scaling every input by k scales the output by k; permuting inputs to an order-independent reduction leaves the result unchanged.

```python
from hypothesis import given, strategies as st

@given(st.lists(st.integers()))
def test_optimized_sort_is_a_sorted_permutation(xs):
    out = optimized_sort(xs)
    assert out == sorted(xs)                  # oracle property
    assert sorted(out) == sorted(xs)          # permutation property
```

The same test in Rust with `proptest` (or `quickcheck`, whose `Arbitrary`/shrinking model is equivalent):

```rust
proptest! {
    #[test]
    fn optimized_sort_is_a_sorted_permutation(xs in proptest::collection::vec(any::<i64>(), 0..1000)) {
        let out = optimized_sort(&xs);
        let mut expected = xs.clone();
        expected.sort();
        prop_assert_eq!(out, expected);        // oracle + permutation in one
    }
}
```

### Floating-point tolerance for reordered or vectorized math

Floating-point addition is not associative. The instant you reorder a sum, vectorize a reduction, or fuse multiply-add, bit-exact equality with the scalar baseline is the *wrong* test: it will fail on a correct optimization. Compare within a tolerance, not with `==`:

- Use a **relative + absolute** tolerance (`abs(a-b) <= atol + rtol*abs(b)`, e.g. `math.isclose`, `numpy.allclose`), sized to the operation's expected error, not pulled from the air.
- Expect error to grow with reduction length: a tree or pairwise reduction over N elements has roughly `O(log N)` worst-case relative error versus `O(N)` for a naive sequential sum, so a vectorized version can be *more* accurate than the baseline, not less. Decide which one is the reference deliberately.
- Watch the cases where tolerance is not enough and the answer is genuinely wrong: NaN/Inf handling that differs, catastrophic cancellation a reordering exposed, denormals flushed to zero by a fast-math flag. `-ffast-math` / `-Ofast` trade IEEE semantics for speed; if you enabled it, your correctness test must assert the properties you still need, because bit-equality with the strict build will not hold.
- For integer "optimizations," the opposite rule applies: there is no tolerance. Bit-exact or it is a bug. Watch for overflow introduced by a wider/narrower type, sign-extension, and rounding-mode changes.

### Fuzz the optimized path

Optimized paths add branches (the special-case fast path, the SIMD tail, the unaligned-head handler) and each branch is a place a hand-written optimization goes wrong on an input you did not imagine. Fuzz it:

- **Differential fuzzing** is the strongest form: feed the fuzzer's input to both old and new, fail on any divergence (or any tolerance breach for FP). This turns the fuzzer loose on finding the input where the fast path disagrees with the oracle.
- Drive coverage into the new branches specifically: the boundary between the vectorized body and the scalar remainder, alignment edges, the empty/tiny inputs that skip the fast path entirely.
- A few hours of `cargo fuzz` / libFuzzer / AFL++ / Hypothesis with a differential check finds the off-by-one in the SIMD tail that a fixed test suite walks right past.

---

## Worked example

**Change:** replaced a scalar `sum()` over a 1M-element `float32` column with an 8-wide SIMD reduction, expecting the kernel to go from bandwidth-bound-but-core-limited to bandwidth-bound, and wall time to roughly halve.

*Faster, and real.* Re-ran the diagnosis (`../diagnose/index.md`): top-down "core-bound" share dropped from 38% to 9% and back-end memory-bound rose to dominate, exactly the predicted shift; the kernel is now bandwidth-bound near STREAM, so the targeted counter moved the right way. A/B through the harness, interleaved: baseline 4.10 ms [4.02, 4.19], candidate 2.21 ms [2.16, 2.27]. CIs do not overlap, so the ~1.85x win is real and not noise. Checklist: the kernel was the top flame-graph frame (hot ✓), the win dwarfs ±2% variance ✓, inputs are production-shaped columns ✓, `-O3 -march=native` alone got only 1.1x so the hand-vectorization earned its keep ✓.

*Still correct.* Differential test against the scalar baseline over 10k random columns plus the boundary sizes n ∈ {0, 1, 7, 8, 9, 15, 16, 17, 1_000_001} caught the first bug immediately: the candidate dropped the scalar remainder when `n % 8 != 0`, so it agreed at n=16 and diverged at n=17. After the fix, bit-exact equality is the *wrong* gate (the SIMD version sums in 8 partial lanes, a different order than the scalar left-to-right), so the test compares with `numpy.allclose(rtol=1e-6)`; the pairwise lane sum is in fact slightly *more* accurate than the scalar baseline against a float64 reference, which we made the real oracle. A two-hour differential fuzz over random `float32` arrays including NaN, Inf, and denormals surfaced one more divergence: with the fast-math flag the candidate propagated a NaN differently, so we asserted NaN-position equality explicitly. Only then did the change ship.

The point: the wall-time win was real from the first run, and the change was still wrong twice. The gate is both clauses.

---

## Where next

| After proving… | Go to |
|---|---|
| the perf delta and you need the fair A/B mechanics | `benchmark.md` |
| and you suspect the number itself is fooling you | `measurement-integrity.md` |
| the counter didn't move / a new bottleneck surfaced | `../diagnose/index.md` |
| the win is real and correct — lock it against regression | the **defend** step of SKILL.md |
