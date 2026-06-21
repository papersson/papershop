# Diagnosing the bound type

**Status:** READY
**Loaded when:** deciding what KIND of bottleneck you have (the input to picking a lever).

You arrive here from the **locate** step of the SKILL.md loop (target → measure → locate → fix → prove → defend) holding a measurement that says one resource or counter dominates. This leaf turns that into a *named bound type*. The bound type is the thing that picks the lever: each bound has a fingerprint (a symptom plus a confirming counter) and a matching family of fixes, and a fix aimed at the wrong bound buys nothing. A perfectly vectorized loop the memory system cannot feed is not faster; a lock-free queue that lives in CAS retries is not faster.

One rule governs the whole leaf: **read the bound off counters, not off the symptom.** "Slow" and "high CPU" name a feeling, not a cause. The same symptom (a growing queue, a bad p99, 100% CPU) maps to different bounds that need opposite fixes. Measure down to the bound, then act.

---

## The procedure

> **Scope.** The spine below — and most of the confirming-signal column in the fingerprint table — is written for a **Linux / x86 host** (`perf`, `perf c2c`, `numastat`, `strace`, eBPF/`offcputime`). The *bound types* and *lever families* are universal, but the *instruments* are not. If you are working LOCAL on macOS / Apple Silicon (per SKILL.md's Orient split, where there is no `perf`/eBPF), use the Instruments/`dtrace`/`powermetrics` equivalents in `../environment/local-mac.md` to gather the same signals, then read the rows below for the diagnosis. Numbers tied to x86 (cache-line size, IPC-vs-width) carry inline Apple-Silicon caveats where they appear.

### 1. First cut on-CPU: the four top-down buckets

If the work runs hot on a core, attribute every cycle to one of four buckets with `perf stat --topdown` (or `toplev.py`; on macOS this counter view is not available — see the Instruments equivalent in `../environment/local-mac.md`). One usually dominates, and it tells you which half of the taxonomy you are in.

| Bucket | Meaning | Points at |
|---|---|---|
| **Retiring** | the cycle produced useful work | compute-bound — you are already working every cycle; go faster only by doing less or wider work |
| **Bad speculation** | the cycle ran instructions that got squashed | branch / control-flow bound |
| **Front-end bound** | back-end was ready, front-end could not supply µops | front-end bound (I-cache, decode, indirect dispatch) |
| **Back-end bound** | front-end ready, back-end could not execute | the big one — splits into **memory-bound** (waiting on loads/stores) and **core-bound** (port saturation, dependency chains, long-latency ops) |

A bucket is dominant above ~40%, worth a look at 20–40%, ignorable below 20% (full bands in `../diagnose/calibration-tables.md`). Back-end bound is the most common and the least specific; resolving it into bandwidth vs latency vs core is step 3.

### 2. Recognize what top-down cannot see

Top-down is a single-core, on-CPU view. Time spent *off* CPU (blocked on a lock, a syscall, I/O, a GC pause) or *across* cores (coherence) does not appear as its own bucket — it either shows up as back-end bound with the wrong cause, or it does not show up at all because the thread is not running. So whenever the symptom is bad scaling, a lumpy tail, or "CPU is only 70% but it's slow," check the orthogonal bounds explicitly: coherence/false sharing, lock contention, NUMA, syscall/kernel, page faults, GC, I/O wait, and (distributed) coordination/network. These are the lower half of the fingerprint table below.

### 3. Match the fingerprint, name one bound

Most counters are unremarkable after measurement. The dominant bound is whatever is **consuming most of the cycles or wall-time that are not doing useful work.** Find the one row whose symptom and confirming signal both fire. Decide dominant-vs-noise against the thresholds in `../diagnose/calibration-tables.md`, not vibes. Expect one dominant bound plus one or two that surface after you fix it; if you are naming five, you are misattributing (top-down says memory, the real cause is coherence) or you have not measured carefully — re-measure, don't theorize.

---

## The bound-type fingerprint table

Each row is: how it shows up → the counter that confirms it → the lever family it forces. The levers live in `../optimize/` (catalog: `../optimize/interventions.md`); this table is the map from bound to lever.

| Bound | Defining symptom | Confirming signal | Lever family |
|---|---|---|---|
| **Compute (retiring)** | high IPC, core busy with useful work, no stalls | retiring > ~40%; IPC high *relative to the core's issue width* (≈1.5+ on a 4-wide core, proportionally higher on a wider one — read the two signals together, not as independent thresholds); LLC/branch/lock all clean | do **less** or **wider** work: better algorithm, SIMD, parallelism, strength reduction, precompute |
| **Branch / bad-speculation** | hot loop on data-dependent branches | bad-speculation > ~20%; branch-miss > 5% in the hot loop | make the branch predictable (sort/group input), branchless `cmov`/mask *only if* both sides cheap, PGO, hoist/devirtualize |
| **Front-end** | large hot code, heavy virtual dispatch, interpreter | front-end-bound > ~30%; high iTLB / I-cache misses; many indirect calls | shrink hot-code footprint, selective inlining, cut indirect dispatch, huge pages for code on huge binaries |
| **Memory-bandwidth** | streaming/scan over data larger than LLC; more threads stop helping | back-end-memory-bound high **and** bandwidth > ~80% of STREAM | move **fewer bytes**: SoA/column pruning, narrower types, compression, tiling for reuse, non-temporal stores, *fewer* threads |
| **Memory-latency** | pointer chasing, random access, low IPC despite low bandwidth | back-end-memory-bound high, IPC < 0.5–1, LLC-miss > 30%, **bandwidth low**; dTLB-miss > 1% adds TLB pressure | improve **locality**: array over linked list, open-addressed over chained, increase memory-level parallelism (batch independent chains), software prefetch (last resort), huge pages |
| **Core-bound** | high IPC-ish but a port or dependency chain serializes | back-end-bound, not memory; long-latency ops (div/sqrt), tight reduction chains | break dependency chains (multiple accumulators), rebalance ports, replace long-latency ops with approximations |
| **Lock / contention** | many threads, wall time barely scales or regresses with cores | high `futex` time, threads off-CPU waiting (`perf lock`, `offcputime`); scaling plateau/regression | shrink critical section, finer-grained locks, **less sharing** (per-thread + periodic reduce, sharding); lock-free only when proven and contention moderate |
| **Coherence / false sharing** | independent per-thread work, yet scaling regresses with cores | high HITM on a specific line (`perf c2c`; Linux-only — on macOS see `../environment/local-mac.md`); regression curve | pad to the cache line and use `std::hardware_destructive_interference_size` rather than a hardcoded 64 — the line is 64 B on x86 but **128 B on Apple Silicon** (confirm with `sysctl hw.cachelinesize`), so `alignas(64)` does not kill false sharing there; per-thread data, shard state |
| **NUMA** | multi-socket; latency spikes correlated with the remote socket | remote-DRAM fraction > 30% (`numastat`) | pin threads + memory (`numactl`), parallel first-touch, interleave for unpredictable access, shard per node |
| **I/O** | thread blocked on disk/network, not on CPU | off-CPU time on read/write/recv; disk queue depth, socket backlog; major faults | batch and enlarge I/O, async/overlap (Little's Law concurrency), cache/precompute, io_uring; reduce bytes read |
| **Syscall / kernel** | tiny per-op I/O, chatty kernel crossings | high kernel time; `strace -c` shows per-syscall time dominating; syscall-time > 20% | batch (`writev`, `sendmmsg`, bigger reads), io_uring, reduce context switches, kernel bypass only at extreme rates |
| **GC / allocator** | tail bumps at regular intervals; managed runtime | GC-pause > 5% of wall time (runtime log); high minor-faults; allocator lock/atomic time | cut allocation rate, pool/arena, move alloc off the hot path, tune heap/region, low-pause collector |
| **Coordination / network (distributed)** | one request crosses many services; tail set by a downstream | RED on the span tree: one hop's Duration dominates, or Errors/retries spike | cut round trips (batch/coalesce), parallelize independent hops, hedge requests for the tail, remove serial dependencies, move work off the critical path |

The lower rows are the ones top-down hides. The split that trips people most is **bandwidth vs latency** inside back-end-memory-bound: same bucket, opposite fixes. Bandwidth-bound near STREAM means *fewer bytes* and *fewer threads*; latency-bound (low bandwidth, high miss, pointer chasing) means *better locality* and *more independent work in flight*. Adding threads to a bandwidth-bound loop makes it worse; reducing bytes on a latency-bound loop does nothing.

---

## Pitfalls / misattribution

- **"100% CPU" is not "compute-bound."** A core pegged at IPC 0.4 is stalled on memory, not working. Check IPC and the top-down split before believing the utilization number. Compute-bound requires *high IPC and clean memory/branch/lock counters*, not just a busy core.
- **Back-end-bound is a category, not a diagnosis.** Always resolve it into bandwidth / latency / core. Stopping at "back-end bound" and reaching for SIMD when the loop is bandwidth-saturated is the classic wasted optimization.
- **Tail problems rarely have a CPU fingerprint.** A bad p99 with a fine mean IPC is almost always off-CPU: GC, page fault, lock spike, scheduler, or a downstream p99. Look at off-CPU and the runtime log, not flame-graph hot functions.
- **Folklore picks the bound before the counters do.** "Mutexes are slow / SoA is faster / branches are expensive" are bets on a workload, not facts. An uncontended mutex is ~20 ns; the usual fix for a contended one is *less sharing*, not lock-free. Let the counter name the bound.
- **Coherence wears a memory costume.** False sharing reports as back-end-bound and scales like contention. If an "embarrassingly parallel" job regresses with cores, run `perf c2c` (Linux; on macOS use the `../environment/local-mac.md` equivalents) before tuning the kernel — and remember the false-sharing pad is 128 B, not 64 B, on Apple Silicon.
- **Closed-loop benchmarks hide whole bounds.** Coordinated omission erases the tail, so GC, I/O, and coordination bounds vanish from the measurement. Use open-loop load if the tail is the target (`../diagnose/index.md` covers the load-vs-architecture and saturation-curve view).

---

## Worked examples

**JSON parsing, 40 MB/s/core, single-threaded.** Top-down: bad-speculation 28%, back-end 35%. Counters: IPC 1.1, LLC-miss 2%, dTLB 0.05%, branch-miss 12%. Memory is clean, branches are not. Data-dependent branch on each character. **Bound: branch/control-flow.** Lever family: branchless/SIMD parsing (simdjson-style), vectorized character classification. SIMD here is right because the bound is control-flow over contiguous data, not bandwidth.

**Matrix transpose, 4K×4K doubles, 200 ms.** Top-down: back-end-memory-bound 70%. Counters: IPC 0.3, LLC-miss 45%, dTLB-miss 3%, branch-miss 0.1%, bandwidth modest. Low IPC, huge miss rate, *low* bandwidth, pointer-free but giant stride. **Bound: memory-latency (with TLB pressure).** Lever family: tile/block the transpose, huge pages. (Non-temporal stores help here too, but as a *write-bandwidth* fix — they cut RFO traffic on the output side; they do not address load latency, which locality and MLP do. NT stores are a bandwidth lever, not a general latency lever.) Not bandwidth-bound on the read side, so not "add threads"; the column stride defeats every cache tier.

**Streaming scan, throughput plateaus at 8 threads.** Per-thread work is independent. Single-thread 18 GB/s, climbing to 112 GB/s at 16 threads then flat. Bandwidth at 85% of STREAM. **Bound: memory-bandwidth.** Lever family: narrow the element type, prune columns, compress — move fewer bytes. Adding threads past the knee only adds contention.

**Web service, p50 5 ms, p99 180 ms.** Average CPU modest, IPC fine; no CPU counter explains the tail. `perf sched` shows 100–150 ms off-CPU stretches; GC log shows young-gen pauses every ~30 s. **Bound: GC (tail).** Lever family: cut allocation rate, move allocation off the request thread, low-pause collector. No hot-path code change touches this.

Every case: the symptom (slow throughput, bad tail, pegged CPU) named the wrong layer until the counters named the bound.

---

## Where next

| You have… | Go to |
|---|---|
| a counter but don't know if it's bad | `../diagnose/calibration-tables.md` |
| the full locate procedure (USE/RED, load vs architecture, the saturation curve) | `../diagnose/index.md` |
| a named bound, ready to pick and apply the fix | `../optimize/` · catalog `../optimize/interventions.md` |
| unsure which stack layer the bound lives in | `software-stack.md` |
| sizing the latency floor / bytes before reasoning about a bound | `latency-numbers.md` |
| classifying the workload shape (latency vs throughput, dependency structure) | `work-taxonomy.md` |
