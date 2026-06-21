# Benchmark tooling (cross-language)

**Status:** READY
**Loaded when:** picking a benchmark tool / microbenchmark harness.

This is the catalog behind the **measure** step of the SKILL.md loop. `benchmark.md` gives the fair-A/B method and `measurement-integrity.md` gives the rules a measurement must pass; this leaf is the shelf of tools that already implement those rules, so you pick one instead of rebuilding the hard parts. Each entry says what the tool measures, the statistical care it encodes, and the exact invocation.

## Why wrap, not roll your own

A benchmark loop looks trivial: start a timer, run the thing, stop the timer, print. That loop is wrong in ways that do not announce themselves. It times cold caches and an untrained predictor into the steady-state number. On a JIT/AOT runtime the optimizer deletes your unused result and you measure the dead-code eliminator instead of the work. One scheduler hiccup drags a mean-based headline. A single run carries no uncertainty, so a 15% "win" inside 20% machine noise reads as a win. The mature tools below each encode the fixes for these — warmup discard, an optimizer barrier, outlier handling, repeated runs with an interval — because their authors hit the same lies you would.

That is the whole argument for the harness's **Regime-and-Sourcing** rule (`harness/METHODOLOGY.md` §4): **wrap a battle-tested tool whenever a hard part is in play, build only the simple corner.** Concretely, wrap when the runtime is JIT/AOT (a real optimizer barrier and steady-state detection are not safely hand-rollable), when the regime is CLI (shell-spawn calibration and run-count budgeting), or when the regime is service/load (coordinated-omission correction and tail accuracy). Build your own loop only when *all* hold: library regime, no-JIT runtime, per-op CPU seconds, and none of {optimizer barrier, coordinated omission, HdrHistogram, high-rate scheduling} apply. Even then you own the spine and let it add the bootstrap CI these tools sometimes omit. The tools here are sample *sources* upstream of your raw samples, not replacements for the aggregator.

---

## Per-tool reference

### hyperfine — CLI / cross-language whole-program timing

Measures wall-clock time of a whole command invocation, startup included. This is the CLI-regime engine our own harness wraps.

What it encodes: warmup runs before timing (`--warmup`), so the first cold-cache invocations do not pollute the estimate; a separate shell-spawn calibration it subtracts, so you time your program and not the shell; statistical outlier detection that warns when results are affected by background load; machine-readable export for downstream aggregation; and parameter scans that turn a sweep into one command.

```sh
hyperfine --warmup 3 --runs 30 \
  --export-json out.json \
  'rg foo bigfile' 'grep foo bigfile'
# parameter scan:
hyperfine -P size 10000 100000 -D 10000 'sort --buffer-size={size}k data'
# fast op: take the shell out of the measurement
hyperfine -N --warmup 5 './tiny-cli'
```

Two cautions when wrapping it: it does not interleave between commands, so drive it round-robin per run yourself; and force `--runs 20–40` (never the default 10) so a bootstrap downstream has enough samples. Map its per-command `times[]` into the raw-sample schema, one sample per run, `batch=1`.

### Criterion.rs — Rust microbenchmarks

Statistical benchmarking for Rust functions. The ecosystem standard for an optimized native runtime where a naive loop measures nothing.

What it encodes: an optimizer barrier (`black_box`) so the compiler cannot fold away the work under test; warmup followed by sampling many iterations and a regression of time against iteration count, which separates per-iteration cost from fixed overhead; outlier classification (mild/severe) reported rather than hidden; and change detection against a stored baseline, so a re-run prints the delta and whether it is statistically significant.

```rust
use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn bench(c: &mut Criterion) {
    c.bench_function("parse 1k", |b| {
        b.iter(|| parse(black_box(INPUT)))
    });
}
criterion_group!(benches, bench);
criterion_main!(benches);
```

```sh
cargo bench                      # establishes/compares against the saved baseline
cargo bench -- --save-baseline pre
```

### JMH — JVM microbenchmarks

The official OpenJDK harness. The canonical "never roll your own on the JVM," because JIT tier-up, dead-code elimination, and constant folding make a hand-written loop measure the optimizer.

What it encodes: forks a fresh JVM per trial so one run's JIT profile and heap state do not leak into the next; explicit warmup iterations to let the JIT reach steady state before measured iterations begin; `Blackhole` and the return-value convention to defeat dead-code elimination; `@State` to control what setup is shared versus per-thread; and built-in modes (throughput, average time, sample-time distribution for tails).

```java
@Benchmark @Fork(2)
@Warmup(iterations = 5) @Measurement(iterations = 10)
public void parse(Blackhole bh, MyState s) {
    bh.consume(parse(s.input));
}
```

```sh
mvn package && java -jar target/benchmarks.jar -rf json
```

### Google Benchmark — C++ microbenchmarks

Registration-based benchmarking for C++. The standard wrap for optimized native code.

What it encodes: automatic iteration-count tuning, where it grows the loop until the total time is large enough to be stable and reports per-iteration cost; `benchmark::DoNotOptimize(x)` and `benchmark::ClobberMemory()` as the optimizer barriers that keep the compiler from deleting the work or hoisting it out of the loop; repetition with reported mean/median/stddev; and complexity (Big-O) estimation that fits a curve across a range argument so you read the asymptotics, not just one point.

```cpp
static void BM_Parse(benchmark::State& state) {
  for (auto _ : state) {
    benchmark::DoNotOptimize(parse(input));
  }
  state.SetComplexityN(state.range(0));
}
BENCHMARK(BM_Parse)->Range(1<<10, 1<<20)->Complexity();
BENCHMARK_MAIN();
```

```sh
./bench --benchmark_repetitions=20 --benchmark_format=json > out.json
```

### pytest-benchmark — Python microbenchmarks

A timing fixture for the no-JIT CPython library regime, the one case where a calibrated in-process loop is legitimate.

What it encodes: calibration of the inner loop count to clear timer resolution; optional GC control during timing so a collection cycle does not land in one sample; and reported stats (min, median, mean, stddev, IQR, outlier counts) with the raw runs exposed for your own aggregation. It does not compute a bootstrap CI on the median, which is exactly the gap our `core.py` build fills when you stay in this corner.

```python
def test_parse(benchmark):
    result = benchmark(parse, INPUT)
    assert result == EXPECTED        # correctness gate alongside timing
```

```sh
pytest --benchmark-json=out.json --benchmark-disable-gc
```

### benchstat — Go A/B comparison

Not a runner but the comparison tool for `go test -bench` output, and the model for honest A/B reporting. Go's `testing.B` owns the loop (it auto-scales `b.N` to a stable time and offers `b.Loop`); benchstat decides whether two result sets differ.

What it encodes: a non-parametric A/B comparison that reports the median and a 95% confidence interval per benchmark, then a Mann-Whitney U test at alpha 0.05 between the two files, printing the percent delta only when the difference is significant and `~` when it is not. That is interval-separation reasoning done for you: no significance, no claimed win.

```sh
go test -bench=. -count=10 ./... > old.txt
# (apply change)
go test -bench=. -count=10 ./... > new.txt
benchstat old.txt new.txt          # delta + p-value, or ~ for "no difference"
```

Use `-count=10` or more: benchstat needs several runs per side to estimate the interval.

---

## Which to use

| Language / regime | Tool | Why |
|---|---|---|
| Any command-line program | hyperfine | startup-aware whole-invocation timing; the CLI regime |
| Rust function | Criterion.rs | `black_box` barrier + baseline change detection |
| JVM (Java/Kotlin/Scala) | JMH | fork-per-run + warmup + Blackhole; JIT-safe |
| C / C++ | Google Benchmark | auto-tuned iterations + `DoNotOptimize` + Big-O |
| Go function | `testing.B` + benchstat | built-in loop + Mann-Whitney A/B |
| Python (CPython) function | pytest-benchmark, or build (`core.py`) | no-JIT corner; build adds the median bootstrap CI |
| HTTP / service tail under load | open-loop generator (`vegeta`/`k6`/`wrk2`) | coordinated-omission correction; see `benchmark.md` |

The decision rule, not the table, is what to remember: pick the regime from the headline unit (per-op, per-invocation, or per-request-under-a-rate), then wrap unless you are in the no-JIT library corner. When two regimes co-fire, the headline unit decides. Full procedure in `benchmark.md`; the underlying R&S framework in `harness/METHODOLOGY.md` §4.

These tools cover the *timing source*. They do not absolve you of the integrity rules: a wrapped tool can still be pointed at the wrong regime, fed a non-time metric it reports as seconds, or read as a point estimate with overlapping intervals. The tool encodes warmup, the barrier, and outlier handling; you still own the metric-type gate, the correctness gate, and reading the verdict from interval separation.

## Where next

| When you… | Go to |
|---|---|
| need the fair-A/B method these tools plug into | `benchmark.md` |
| need the don't-fool-yourself rules each tool partly encodes | `measurement-integrity.md` |
| want the runnable spine, schemas, and the wrap-vs-build R&S framework | `harness/` (README + METHODOLOGY) |
| are profiling a managed runtime rather than benchmarking it | `../diagnose/per-language.md` |
| have a benchmark and need to prove the change won and stayed correct | `verify.md` |
