# Finding the dominant bottleneck

**Status:** READY
**Loaded when:** you have a concrete slowdown and a number to beat, and need to locate *where* and *why* before changing anything.

This is the **locate** step of the SKILL.md loop (target → measure → **locate** → fix → prove → defend). You arrive here with a target and at least one measurement saying something is slow. You leave with a named, located bottleneck and a one-sentence causal model the `../optimize/` branch can act on. Do not optimize before you finish this leaf; a fix that doesn't target the binding constraint buys nothing.

The whole method is one rule: **measure your way down the stack instead of guessing where the problem is.** Your intuition about where time goes is wrong often enough that it's not a starting point. Measurement is the substrate.

> **Live regression? Route here first.** If the system got *slower after a specific change* (deploy, config flip, dependency bump, traffic shift), don't open a profiler yet — go to `regression-incident.md` first and correlate the onset of the slowdown with what changed (bisect by version, diff against the last-good window). Deep profiling answers *why it's slow*; a live regression is usually faster to crack by finding *what made it slower*. Come back here once you've localized the change but still need the mechanism. (The *defend* leaf `../design-and-lifecycle/regression-ci.md` is a different thing — it prevents future regressions in CI; it does not diagnose one already in prod.)

> **Platform scope.** The `perf`-based steps below (the `perf` family, `strace`, eBPF) and the 60-second triage are **Linux/x86 host-scoped**. On macOS / Apple Silicon `perf` and eBPF don't exist — use the Instruments / `dtrace` / `xctrace` equivalents in `../environment/local-mac.md`, and note that hardware constants differ: the cache line is **128 bytes** on Apple Silicon (read it with `sysctl hw.cachelinesize`, and in C++ use `std::hardware_destructive_interference_size` rather than a hardcoded 64). The USE/RED methods and bound-type reasoning are platform-independent; only the commands change.

---

## Procedure

Run these in order. Each step has an exit you can check before moving on.

### 0. Confirm preconditions
- A target exists (a budget, SLO, p99, cost line). No number → go back to the gate in SKILL.md; "make it fast" is not a task.
- You can observe the system. Local single process: attach a profiler (`../environment/local-mac.md`). Prod/distributed: you need telemetry first — metrics, tracing, continuous profiling (`../environment/prod-distributed.md`).
- You know which world you're in, because it picks the lens in step 1.

### 1. Pick the lens
- **Single host / one process / "is this box's resources the limit?"** → use the **USE method** (below). Resource-centric.
- **A request path crossing services / "which hop is slow?"** → use the **RED method** (below). Service-centric.
- They compose. In a distributed system the bottleneck is usually *between* services, not inside one, so start with RED to find the slow tier, then run USE on that tier's host(s) to find the binding resource. Going straight to USE on a random box is how you spend an afternoon profiling a service that was only ever waiting on a downstream.

If you only have 60 seconds and a Linux host, run the fast first pass first: `triage-60s.md`. It tells you which of the steps below to spend time on. (On macOS / Apple Silicon that triage doesn't apply — `vmstat`/`mpstat`/`pidstat`/`iostat` aren't there; use the local first-pass tools in `../environment/local-mac.md`.)

### 2. Characterize the workload
Take one measurement pass that produces *numbers*, not adjectives. Walk down the stack — application → your libraries → syscalls → kernel → hardware (`../orient/software-stack.md`) — and at each layer ask what the machine is physically doing. Six profiles cover it:

| Profile | The question | How you see it |
|---|---|---|
| Work | Which functions dominate? What's the IPC? User vs kernel vs runtime? | flame graph + `perf stat` (`profiling.md`, `../environment/linux.md`) |
| Memory | Working set fits which cache tier? Access pattern? Bandwidth vs STREAM? Miss rates (L1/LLC/TLB)? | `perf stat -d`, `likwid` |
| Control flow | Branch miss rate in the hot loop? Indirect calls per unit work? | `perf stat -e branches,branch-misses` |
| Concurrency | How does wall time scale with threads? Lock-wait fraction? False sharing (HITM)? NUMA-remote fraction? | scaling curve, `perf c2c`, `perf lock` |
| System boundary | Syscalls per unit work? Context switches (voluntary/involuntary)? Minor vs major faults? GC pauses? | `strace -c`, `perf stat -e ...faults`, runtime GC log |
| Tail | p50 / p99 / p99.9 / max, and the source of each tail bump? | latency histogram, `perf sched` / off-CPU |

Don't skip this because you "already know" the cause. You're wrong about half the time, and the other half you miss the *second* bottleneck that bites right after you fix the first. To see where time actually goes, use `profiling.md` (sampling vs instrumenting) and `per-language.md` for managed runtimes.

### 3. Identify the *dominant* bottleneck
After characterization most numbers are unremarkable. The dominant bottleneck is whatever is **consuming most of the cycles (or wall-time) that are not doing useful work**. Pin it down two ways:

- **Top-down, on CPU:** attribute cycles to retiring / bad-speculation / front-end-bound / back-end-bound (and split back-end into memory-bound vs core-bound). One bucket usually dominates. `perf stat --topdown`. Bound-type reasoning: `../orient/bound-types.md`.
- **Orthogonal bottlenecks top-down hides:** coherence/false sharing, lock contention, NUMA, syscall/kernel time, page faults, GC pauses, frequency throttling. Top-down reports these as "back-end bound" while hiding the cause, so check them explicitly when scaling is bad or the tail is lumpy.

Decide *dominant vs noise* against thresholds, not vibes. Every counter has an ignore / investigate / dominant band — those live in `calibration-tables.md`. Rough anchors: top-down bucket > 40%, branch-miss > 5% in a hot loop, LLC-miss > 30%, lock-wait > 10% of time, GC > 5% of wall time. Most real workloads have **one** dominant bottleneck plus one or two that surface after you fix it. If you're listing five, you're misattributing (top-down says memory but the real cause is coherence) or you haven't measured carefully enough — re-measure, don't theorize.

### 4. Classify it: load or architecture? (see below)

### 5. Name it and hand off
Write the causal model as one sentence with all the facts in it, e.g. *"latency-sensitive request path, dominant op is remote reads, locally dependency-light but tail-bound by a downstream p99 and retry amplification."* or *"scan-shaped data-parallel kernel, currently DRAM-bandwidth-bound at 80% of STREAM, so more threads won't help."* That sentence is the input to `../optimize/`. Then confirm the win the same way: re-run this procedure after the fix and check the counter you targeted actually moved (`../measure/verify.md`).

---

## The USE method (resources)

For **every resource**, check three things. A resource is anything finite the work consumes: CPU, memory capacity, memory bandwidth, disk/storage, network, and the software-side ones people forget — thread pools, connection pools, file descriptors, mutexes, queue slots.

For each resource, in order:

1. **Utilization** — what fraction of the time (or capacity) is it busy? High utilization alone is not a problem; a CPU at 100% doing useful work is healthy.
2. **Saturation** — how much work is *queued* waiting for it? This is the real signal. Run-queue length for CPU, swap/page-fault activity for memory, disk queue depth, socket backlog, threads blocked on a pool. Saturation means demand exceeds the resource right now.
3. **Errors** — error counts for that resource: dropped packets, disk I/O errors, failed allocations, ECC events. Errors are easy to overlook and sometimes *are* the latency story (a retry behind every error).

Procedure: enumerate the resources, fill the U/S/E cell for each, and the bottleneck is the resource that is **saturated** (queueing), not merely the one that is most utilized. A resource can be 100% utilized with no queue (fine) or 70% utilized with a deep queue feeding it intermittently (not fine). For the Linux commands that read each cell, see `triage-60s.md` and `../environment/linux.md` (macOS / Apple Silicon equivalents: `../environment/local-mac.md`); for what the numbers mean, `calibration-tables.md`.

Use USE when you're on a host and asking "which resource is the limit?"

---

## The RED method (services)

For **every service** on the request path, check three things:

1. **Rate** — requests per second it's handling.
2. **Errors** — failed requests per second (and the retries they spawn; retry storms are a collapse mode).
3. **Duration** — the *distribution* of request latency, p50/p95/p99, never just the mean.

Procedure: enumerate the services a request traverses (the distributed-tracing span tree gives you this directly), pull R/E/D for each, and find the hop where **Duration dominates the end-to-end budget** or where **Errors spike**. Follow that span down. When the slow hop is a leaf (a database, a cache), switch to USE on that node to find the resource behind its latency. The handoff between RED and USE is the whole reason a distributed diagnosis works: RED localizes to a tier, USE explains the tier.

Use RED when you're tracing a request across services and asking "which hop is slow?" Tooling: `../environment/prod-distributed.md`.

---

## Load vs architecture

Two systems with the same symptom (a growing queue, a rising p99) need opposite fixes. Separate them before choosing an intervention:

| | **Load problem** | **Architecture problem** |
|---|---|---|
| Meaning | demand exceeds capacity that's being used reasonably | capacity exists but can't be used — work is serialized, contended, imbalanced, or misrouted |
| Signal | *all* relevant workers/resources busy; queues grow uniformly | *some* resources saturated while others sit idle; one narrow point backs up |
| First fix | add capacity, autoscale, shed/rate-limit load, reduce demand, raise per-unit efficiency | remove serialization, shard, parallelize, rebalance, cut coordination, change the request/data path |

Examples that look identical until you look: all 16 cores busy with a growing request queue (**load** — another instance ~doubles throughput) vs one core pegged while 15 idle because the hot path is single-threaded (**architecture** — more cores do nothing). Many threads all blocked on one lock / one connection-pool / one hot DB row / one skewed shard is **architecture** wearing a load costume.

**The test:** add capacity in the dimension you think is limiting. If throughput rises roughly proportionally and latency falls, it was load. If throughput barely moves, it's architecture (or a different shared resource downstream). This is also the resource-scaling curve: linear = added resource became useful work; plateau = a fixed bottleneck dominates; regression = you added contention (locks, coherence, retry storms).

---

## The saturation curve

As offered load rises, throughput moves through four regions. Knowing which one you're in *is* the diagnosis for a service under load:

| Region | What happens | Meaning |
|---|---|---|
| **Linear** | throughput tracks load 1:1, latency flat | spare capacity |
| **Knee** | throughput stops rising linearly, latency/queueing climb faster | contention has started to bite |
| **Saturation** | a resource hits effective capacity, extra load mostly waits | at or past safe operating point |
| **Collapse** | throughput *falls* as load rises | overload overhead (retries, context switches, lock contention, GC, coherence, timeout churn) now exceeds useful work |

Two things to internalize. First, **latency degrades before throughput plateaus** — queueing delay grows nonlinearly as utilization approaches saturation, so the useful capacity limit is the load at which p99 breaks your objective, not the load at which throughput maxes out. Second, **"CPU is only 70%" is not a safety signal**: the saturated resource may be a lock, a thread pool, a shard, a disk queue, or a downstream p99 rather than aggregate CPU. Measure the curve, not one point — plot offered load against completed throughput, latency percentiles, queue depth, and error/retry rate together. Use open-loop load generation; closed-loop clients hide overload because slow responses throttle the client's own send rate. Deeper: `../design-and-lifecycle/capacity-scalability.md`.

---

## Worked sketches

**JSON parsing, 40 MB/s/core, single-threaded.** Measured IPC 1.1, LLC-miss 2%, branch-miss 12%, bad-speculation 28%. Memory is fine; branches dominate. Data-dependent branches on each character. → control-flow problem; the optimize branch points at SIMD parsing or a branchless state machine.

**Web service, p50 5 ms, p99 180 ms.** Average CPU and IPC are fine, so no CPU counter explains the tail. `perf sched` shows 100–150 ms off-CPU stretches; GC log shows young-gen pauses every ~30 s. → tail is GC, not code; no hot-path work fixes it. Tune the collector / cut allocation rate.

Both show the same lesson: the symptom (slow throughput, bad tail) named the wrong layer until measurement located the real one.

---

## Where next

| After locating… | Go to |
|---|---|
| it got slower after a change/deploy (live regression) | `regression-incident.md` (correlate onset with the change first) |
| need the 60-second first pass on a Linux host | `triage-60s.md` |
| a counter and you don't know if it's bad | `calibration-tables.md` |
| need to see where time/resources go | `profiling.md`, `per-language.md` |
| unsure what *kind* of bound it is | `../orient/bound-types.md` |
| unsure which stack layer to chase | `../orient/software-stack.md` |
| the actual tools for your environment | `../environment/` (local-mac · linux · prod-distributed) |
| bottleneck named, ready to fix | `../optimize/` |
| fix applied, prove it | `../measure/verify.md` |
