# The software stack as a where-map

**Status:** READY
**Loaded when:** orienting at the start of any perf task, to decide where to look before measuring.

This is the **orient** step that precedes the loop's *measure* and *locate* (SKILL.md: target → measure → locate → fix → prove → defend). Performance does not live "in the program" in general; it lives at a specific layer of a specific machine, or in a specific hop between services. This leaf gives you the map so you can place a hypothesis on it. The one rule: **put a pin on the map, then measure your way *down* it. Do not guess your way to a fix.** Your intuition about which layer is slow is wrong often enough that it is a starting hypothesis, never a conclusion.

The map exists so that when a measurement comes back, you know what it rules in and what it rules out. Without the map you collect numbers with nowhere to put them.

---

## The single-host stack

Every running program sits on a stack of layers, each of which can be the thing that is slow. Top is closest to your code; bottom is the silicon. Each layer can cost time the layer above it cannot see.

```
application logic        your algorithm, request handling, business rules
  your libraries         frameworks, parsers, serializers, ORMs, allocators
    language runtime      GC, JIT warmup, interpreter dispatch, async scheduler
      system calls        the user→kernel boundary (read/write/futex/mmap)
        kernel            scheduler · filesystem · network stack · virtual memory
          hardware        cores (pipeline, branch predictor, SIMD) · cache
                          hierarchy · DRAM/bandwidth · TLB · coherence · NUMA
```

What each layer can cost, and the signal that points at it:

| Layer | What goes wrong here | Telltale signal |
|---|---|---|
| Application logic | wrong algorithm (O(n²)), redundant work, work that didn't need doing | time scales with input the way a bad complexity class would; flame graph dominated by your own functions doing real work |
| Your libraries | a hot parser/serializer/ORM, accidental copies, an allocator under churn | flame graph dominated by library frames, not yours; allocation rate high |
| Language runtime | GC pauses, JIT not warmed, interpreter/virtual dispatch, async scheduler overhead | latency tail with clean average; GC log bumps; cold-start slowness that disappears after warmup |
| System calls | a syscall per byte/row, chatty I/O, lock contention bouncing into `futex` | `strace -c` shows millions of tiny calls; high kernel-time fraction |
| Kernel | scheduler preemption, page faults, filesystem/network-stack cost, swap | context switches, major faults, off-CPU time, `iowait` |
| Hardware | memory-bound (cache/DRAM/bandwidth), branch misprediction, TLB misses, false sharing, NUMA-remote access | low IPC at 100% CPU, high LLC/branch/TLB miss rates, scaling that stalls or regresses with cores |

Two facts make the bottom of this stack the usual surprise. **An arithmetic op is ~1 cycle; a DRAM load is ~300 cycles** (the memory wall). And **a process at 100% CPU in `top` is often not compute-bound at all** — it is stalled waiting on memory, running past pipeline bubbles. So "the CPU is busy" does not place the pin at the hardware-compute layer; it could be memory, and only a counter (IPC, LLC-miss) tells you which. Bound-type reasoning for the bottom layers lives in `bound-types.md`.

The layering also encodes leverage. A cost at a high layer is usually cheaper to remove than one below it: deleting a query beats tuning the database; returning fewer rows beats a faster disk; one pass beats a warmer cache. So when two layers both look plausible, suspect the higher one first — the fix is cheaper and it often makes the lower-layer symptom disappear.

## The distributed tier map

A request in a distributed system traverses services, and the time is usually spent *between* them, not inside any one. Draw the second map before measuring:

```
client → edge / LB → app server → ┬→ database
                                   ├→ cache
                                   ├→ queue / worker
                                   └→ downstream service → (its own stack…)
            ↑ the network (RTT, retries, connection setup, TLS) sits on every arrow ↑
```

Each tier is itself a single-host stack (the first map), so a distributed diagnosis is two maps nested: find the slow *tier*, then descend its *layers*. Where time accrues across tiers:

| Tier / arrow | What goes wrong | Telltale signal |
|---|---|---|
| Network arrow | RTT floor, too many serial round trips, retries/timeouts, TLS/connection setup | end-to-end latency ≈ N × RTT; latency tracks geography; retry storms |
| App server | the request's own logic/runtime (its single-host stack) | span time spent in-process, not waiting on a child |
| Database | slow query, missing index, lock/row contention, connection-pool exhaustion | DB span dominates; pool saturation; query plan does a scan |
| Cache | low hit rate, hot key, stampede on expiry | latency bimodal (hit vs miss); one key's traffic dominates |
| Queue / worker | backlog growth, slow consumer, head-of-line blocking | queue depth rising; age of oldest message climbing |
| Downstream service | a slow dependency's own p99 amplified by fan-out and retries | your tail tracks a downstream's tail; fan-out multiplies it |

The arithmetic constraint to carry into design and triage alike: a path of 20 serial cross-service hops at 1 ms each cannot meet a 10 ms budget, and you can know that before measuring anything (latency floors: `../orient/latency-numbers.md`). The RTT floor is the one cost no amount of in-service tuning removes.

---

## How to orient: form the layer hypothesis

Run this before you attach an instrument. It produces a *ranked* hypothesis, not a fix.

1. **Pick the map.** One process on one box → the single-host stack. A request crossing services → the tier map first, then the single-host stack of whichever tier you land on. If you are unsure which world you're in, that is the local-vs-prod question from SKILL.md and it also decides your tools (`../environment/`).

2. **Read the symptom into a layer band.** The shape of the complaint already narrows the map:
   - *Time grows with input size faster than linear* → application algorithm (top layer), before anything microarchitectural.
   - *Bad average throughput, CPU pegged* → compute or memory at the hardware layer; check IPC to split them.
   - *Good average, bad tail (p99 ≫ p50)* → pauses and waits, not hot code: GC (runtime), scheduling/faults (kernel), queueing or a downstream p99 (tiers). Tails almost never come from the average instruction.
   - *Slowness that scales with concurrency (worse with more threads/cores)* → contention: locks (syscall/kernel), coherence/false sharing/NUMA (hardware), or a hot shared resource (a DB row, a cache key) one tier over.
   - *Slowness that tracks geography or hop count* → the network arrows, not any service's internals.

3. **Place the pin at the highest plausible layer.** Given two candidate layers, start high. The leverage argument above means the high-layer fix is cheaper, and confirming or killing a high-layer hypothesis is usually a faster measurement.

4. **Plan to measure *down*, not sideways.** The discipline is descent: confirm or eliminate the current layer with one measurement, and only drop to the next layer when the evidence sends you there. RED across tiers localizes to a slow tier; USE on that tier's host localizes to a resource; counters on that host localize to a microarchitectural cause. Each step down is justified by the step above it. Jumping straight to a `perf` counter on a random box — or rewriting an algorithm because it "feels" slow — is guessing sideways, and it is how an afternoon disappears into profiling a service that was only ever waiting on a downstream.

5. **Hand the pin to diagnose.** You leave orientation with a sentence like *"distributed read path; tier map says the DB span dominates; within that host I expect a missing index, i.e. an application/query-layer cost, not a hardware one."* That is the input to `../diagnose/index.md`, which turns the hypothesis into a located, measured bottleneck.

---

## Pitfalls

- **Optimizing the layer you understand best.** Engineers reach for the layer they know — the app dev rewrites the algorithm, the kernel dev blames the scheduler. The map is there to make you consider layers outside your comfort zone before committing.
- **Treating "100% CPU" as "compute-bound."** It usually means memory-stalled. The pin goes at the hardware layer either way, but the *fix* (do less arithmetic vs move less data) is opposite. Resolve it with a counter, not the `top` reading.
- **Skipping the tier map in a distributed system.** Going straight to single-host profiling assumes the slow thing is inside *this* process. In distributed systems the bottleneck is usually a hop or a downstream, so the tier map comes first.
- **Confusing the map with the territory.** This leaf tells you *where to look*; it does not measure. Do not conclude a layer is the bottleneck because the map made it plausible. Plausibility ranks the hypotheses; measurement decides. Every claim here is "check this," never "it is this."
- **Pinning five layers at once.** If your hypothesis spans the whole stack, you have not read the symptom. Most real slowdowns have one dominant layer (plus one that surfaces after you fix the first). A five-layer hypothesis means re-read the symptom in step 2.

---

## Worked example

**Symptom:** a checkout endpoint, p50 40 ms, p99 900 ms. Target is p99 < 200 ms.

1. *Map:* request crosses services → tier map first.
2. *Symptom band:* good p50, terrible p99 → pauses/waits/queueing, not hot code. The tail points at GC, scheduling, queueing, or a downstream p99 — not at any function's instruction count.
3. *Pin, high first:* trace spans show the endpoint's own in-process time is flat at ~35 ms across percentiles; the p99 blowup lives entirely in the span calling the inventory service. Pin the inventory *tier*, not our app's algorithm.
4. *Measure down:* RED on the inventory service shows its own p99 is ~850 ms while its p50 is 8 ms. Drop a layer into that host: USE finds the connection pool saturated, threads queued waiting for a slot. The hardware is idle; this is an architecture/contention cost at the syscall/pool layer, not a memory or CPU one.
5. *Hand off:* "tail is a downstream inventory tier; within it, connection-pool saturation under fan-out, not slow code." That sentence goes to `../diagnose/index.md` and then to `../optimize/`. Note what the map *prevented*: rewriting our checkout logic, which would have moved the 35 ms floor and done nothing to the 900 ms tail.

The lesson matches the loop everywhere: the symptom named the wrong layer (it looked like "our endpoint is slow") until the map plus one measurement at each level located the real one, a pool two tiers away.

---

## Where next

| After orienting… | Go to |
|---|---|
| pin placed, ready to measure and locate | `../diagnose/index.md` |
| need the 60-second first pass on a host | `../diagnose/triage-60s.md` |
| unsure what *kind* of bound the bottom layers are (compute vs memory vs branch…) | `bound-types.md` |
| need the numbers to size a layer/hop on paper | `latency-numbers.md` |
| need the shape of the work (latency vs throughput, dependency structure) | `work-taxonomy.md` |
| pick the instrument for your machine or prod system | `../environment/` (local-mac · linux · prod-distributed) |
