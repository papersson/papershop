# The lever hierarchy

**Status:** READY
**Loaded when:** the dominant bottleneck is known and you must choose what to change.

This is the **fix** step of the SKILL.md loop (target → measure → locate → fix → prove → defend). You arrive with a named bound from `../orient/bound-types.md` and a one-sentence causal model from `../diagnose/index.md`. You leave having chosen one change to make. The governing rule is older than any counter: **remove work before you make waste faster.** A faster disk under an application that reads 100 columns to use 3 has accepted the waste and optimized its execution; the win was higher up, in not reading the 97.

Two axes decide the change, and they are orthogonal. The **lever** is *what kind* of change (the priority order below, highest leverage first). The **layer** is *how high in the stack* you apply it (product down to hardware). The bound type picks the lever; the layer rule says apply it at the highest layer that can still eliminate the work. This leaf is the chooser. The concrete fixes for each bound live in `interventions.md`; the configuration knobs and their tradeoffs live in `tradeoff-knobs.md`.

---

## The levers, highest leverage first

Spend your effort top-down through this list. Each lever is cheaper-per-unit-win than the ones below it, and each can make the lower ones unnecessary. Stop as soon as the change you have meets the target; the correct amount of optimization is what the workload requires, not the maximum the hardware allows.

### 1. Remove the work entirely

The largest wins come from work that never happens. Before making anything faster, ask what you can stop doing. This is a design and code-shape decision, not a tuning one:

- **Don't read what you won't use.** Project early; return fewer columns; touch a narrow slice. Read amplification baked into a schema is paid on every query.
- **Don't chatter.** 20 serial RPCs to assemble one response is 20 stacked round trips; one batched call is one. Same for syscalls, small I/Os, per-row DB round trips.
- **Don't recompute the reused.** Cache or precompute a shared aggregate once. But a cache is a freshness-vs-load tradeoff and a TTL is a staleness budget, so this is a product decision, not free speed (`tradeoff-knobs.md`, freshness-vs-load-reduction).
- **Don't pass over the same data twice.** Five scans for five derived values, when one pass yields all five, is 5x the traffic for the same result.

This lever is almost always available at a higher layer than the bound appears at. Reach for it first regardless of which bound you measured.

### 2. Fix the algorithm / data structure (asymptotics)

If the work is necessary, do less of it per unit of input. O(n^2) at n=10^6 is a different problem than O(n log n), and no micro-optimization recovers that gap. An indexed lookup beats a full scan; a hash join beats a nested loop on large inputs; an open-addressed table beats a chained one for probes. This is the cheapest *engineering* win because it is a decision about which structure to use, not an investment in tuning a fixed one. It is the first question for a compute-bound (retiring) workload and the standing background question for every other bound.

### 3. Improve memory / cache locality

Once the work is minimal and the algorithm is right, the next cost is moving the data the work touches. An arithmetic op is ~1 cycle; a DRAM load is ~300. Memory moves in 64-byte lines, so the unit of fast is the fraction of each fetched line you actually use. The moves here:

- **Move fewer bytes** (bandwidth-bound): SoA / column pruning, narrower types, compression, non-temporal stores, and *fewer* threads past the bandwidth knee.
- **Improve locality** (latency-bound): array over linked list, contiguous over pointer-chased, tile/block for reuse, huge pages for TLB reach, software prefetch as a last resort.

The bandwidth-vs-latency split inside this lever is the one that trips people; they are the same top-down bucket with opposite fixes (`../orient/bound-types.md`). Adding threads to a bandwidth-bound loop makes it worse; shrinking bytes on a latency-bound loop does nothing.

### 4. Exploit concurrency / parallelism and hide latency

Now the per-unit work is small and its data is laid out well. To go faster still, do independent units at the same time, or stop waiting on irreducible latency one item at a time. A DRAM miss, an SSD read, an S3 GET, a remote call: you cannot make a single one faster, but you can keep enough in flight that completions arrive continuously, converting a latency problem into a throughput one. Size the concurrency with Little's Law (`concurrency = throughput x latency`); bound the queue by bytes so it cannot exhaust memory.

This lever ranks below the first three for a reason: it adds the most ways to be slow. Adding cores exposes shared bottlenecks that were invisible single-threaded (a shared counter becomes the slowest instruction through cache-line bouncing; two variables on one line cause false sharing). Design *less sharing* (per-thread data, sharding, batching) before designing clever sharing (lock-free). It also only hides latency when future work is knowable; true pointer chasing and coordination-dependent RPC chains cannot be prefetched, and the fix for those is back at lever 2 or 3.

### 5. Micro-tuning last

Branchless rewrites, port rebalancing, dependency-chain breaking, intrinsics, custom allocators, kernel bypass. These are real wins on the right bound (control-flow-bound, core-bound, syscall-bound) but the smallest per unit of effort and complexity, and they foreclose the levers above (hand-written SIMD makes the next algorithm change expensive). Reach here only when measurement says the simpler levers are exhausted and the remaining bound is genuinely at the instruction or boundary level. Check what `-O3 -march=native` already does before hand-writing anything.

---

## Cross-cut: tune as high as you can (the layer rule)

The lever hierarchy says *what* to change. The layer rule says *where*. The same lever applied at a higher layer of the stack usually wins, because a higher layer can make the work disappear while a lower layer can only execute it faster.

```text
Tune where work can be eliminated or reshaped.
Observe wherever the cost becomes visible.
```

| Layer | What tuning can eliminate here | Win shape |
|---|---|---|
| **Product / workload** | features, requests, freshness/consistency requirements, data retained | enormous; the work disappears |
| **Application** | algorithms, queries, RPCs, serialization, allocations, duplicate work, batching | often the largest engineering win |
| **Query / database** | scans, joins, locks, indexes, materialization, transaction scope | large when data access dominates |
| **Runtime** | GC pressure, allocation, scheduling, JIT behavior | medium-large when runtime overhead is visible |
| **Syscall / I/O API** | syscall count, synchronous waits, copying, tiny reads/writes | medium when boundary crossing dominates |
| **Filesystem / storage** | record size, readahead, queue depth, device choice | workload-specific; large for I/O-heavy |
| **Network** | buffer sizes, batching, compression, connection reuse, placement | large for chatty / bandwidth-heavy |
| **Kernel / hardware** | scheduler, NUMA, huge pages, interrupts, frequency, kernel bypass | important near hardware limits |

The two axes compose: **pick the lever the bound forces, then apply it at the highest layer that can avoid the work.** "Remove work" at the product layer beats "remove work" at the kernel layer; "improve locality" in the application's data layout beats it in the page cache. Drop to a lower layer only when one of these holds: the higher layer is already doing the necessary minimum, the workload contract forbids changing it, the measured bottleneck genuinely lives low, or the low-layer change is simpler/safer/reversible and benefits many workloads at once.

The anti-pattern this rule names: tuning a lower layer that only makes waste faster. App reads 100 columns to use 3 → fix projection, not the disk. Service makes 20 needless serial RPCs → fix request shape, not TCP buffers. Job scans the same data 50 times → fix scan sharing, not the worker count. The full layer table with knob-by-knob tradeoffs is in `tradeoff-knobs.md`.

---

## The bound type selects the lever

You do not choose the lever by taste. The named bound from `../orient/bound-types.md` forces a lever family; this table is the routing.

| Bound (from `../orient/bound-types.md`) | Lever tier | Concrete fixes |
|---|---|---|
| **Compute / retiring** | 2 (algorithm), then 4 (wider/parallel), then 5 (SIMD) | do less or wider work |
| **Branch / bad-speculation** | 5 (micro), but 1 first if the branch guards avoidable work | sort/group input, branchless only if both sides cheap, PGO, devirtualize |
| **Front-end** | 5 (micro) | shrink hot-code footprint, cut indirect dispatch, selective inlining |
| **Memory-bandwidth** | 3 (locality: fewer bytes) | SoA/column pruning, narrow types, compression, fewer threads |
| **Memory-latency** | 3 (locality), then 4 (MLP) | array over linked, tiling, batch independent chains, huge pages |
| **Core-bound** | 5 (micro) | break dependency chains, rebalance ports, cheaper long-latency ops |
| **Lock / contention** | 4 (less sharing) | shrink critical section, finer locks, per-thread + reduce, sharding |
| **Coherence / false sharing** | 4 (less sharing) | pad to 64-byte lines, per-thread data, shard state |
| **NUMA** | 4 (placement) | pin threads+memory, parallel first-touch, shard per node |
| **I/O** | 1 (remove), then 4 (overlap) | batch/enlarge I/O, async via Little's Law, cache, io_uring |
| **Syscall / kernel** | 1 (remove), then 5 (bypass) | batch syscalls, io_uring, fewer context switches |
| **GC / allocator** | 1 (allocate less), then knob (`tradeoff-knobs.md`) | cut allocation rate, pool/arena, move off hot path, tune heap |
| **Coordination / network (distributed)** | 1 (remove round trips), then 4 (parallelize/hedge) | batch/coalesce, parallelize independent hops, hedge the tail |

Two reads of this table. First, almost every bound has lever 1 available above it: even a memory-latency bound is moot if the data did not need touching. Always ask "remove the work" before applying the bound's native lever. Second, a structural fix (levers 1-4) routes to `interventions.md`; a configuration change (a knob with a tradeoff) routes to `tradeoff-knobs.md`. If the change is "stop doing X" or "change the shape of X," it is an intervention. If it is "set parameter X from A to B," it is a knob, and you owe both sides of its tradeoff before turning it.

---

## Pitfalls / over-engineering signals

- **Optimizing waste instead of removing it.** Micro-tuning a function that runs once per request while the request makes a redundant network call. Fix the call. Effort spent making waste faster is wasted.
- **Skipping straight to lever 5.** Reaching for lock-free, custom allocators, kernel bypass, or hand SIMD before any measurement says the simple version is the bottleneck. These are the lowest-leverage levers wearing the most impressive clothes.
- **Tuning a knob at the wrong layer.** A faster disk, bigger TCP buffer, or larger connection pool under an application that is doing unnecessary work. The leverage was at the application layer; the knob just paid for the waste.
- **Wrong lever for the bound.** SIMD on a bandwidth-saturated loop, more threads on a bandwidth-bound loop, lock-free on an uncontended lock. The bound, not folklore, picks the lever. "Mutexes are slow / SoA is faster / branches are expensive" are bets on a workload, not facts.
- **Permanent complexity for a transient or unmeasured bottleneck.** Every lever-4 and lever-5 change is complexity you carry forever. Complexity is earned by a number, and only the number that is still binding.

The default is the highest, simplest lever that could meet the target. Earn each step down the hierarchy with a measurement.

---

## Worked example

**Bound handed off:** *"latency-sensitive read path, dominant cost is a per-request DB query returning a 100-column row to compute a 3-field aggregate; p99 760 ms against a 200 ms target; query is back-end-I/O-bound on a full scan."* (from `../diagnose/index.md` and `../orient/bound-types.md`.)

Walk the levers top-down, highest layer first.

1. **Remove the work (lever 1, application + query layer).** The request needs 3 fields; the query returns 100 columns and full-scans to get them. Project to the 3 fields and add the index the predicate needs. This is lever 1 (don't read what you won't use) applied at the highest layer that can avoid the work (the query). Expected: the scan disappears, bytes moved drop ~30x.
2. **Algorithm / data structure (lever 2).** The full scan was the algorithm; the indexed lookup replaces O(rows) with O(log rows). Already covered by step 1's index; nothing more to do.
3. **Locality (lever 3).** Not needed yet. If, after the index, the row store still drags 100-column pages through cache to read 3 fields, a columnar layout would be the locality fix. Defer until measurement says so.
4. **Concurrency / latency hiding (lever 4).** Not needed. The request makes one query, not a fan-out; there is no serial chain to parallelize.
5. **Micro-tuning (lever 5).** Not reached.

The whole win came from levers 1-2 at the application and query layers. Note what was *not* done: no connection-pool tuning, no faster disk, no read-replica (`tradeoff-knobs.md` knobs), all of which would have made the wasteful scan faster while leaving the waste in place. Then prove it: re-measure that the scan-time counter dropped and p99 moved under target, and confirm the projected query still returns the right aggregate (`../measure/verify.md`). If p99 dropped but a second bound (say, a downstream call) is now binding, the loop runs again on the new dominant bound.

---

## Where next

| You have… | Go to |
|---|---|
| a bound and need the concrete fix for it | `interventions.md` |
| a configuration knob to set and want its tradeoff | `tradeoff-knobs.md` |
| not yet named the *kind* of bound | `../orient/bound-types.md` |
| not yet located the dominant bottleneck (USE/RED, load vs architecture) | `../diagnose/index.md` |
| a change applied, ready to prove it (perf delta AND correctness) | `../measure/verify.md` |
