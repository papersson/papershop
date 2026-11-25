# Bottleneck → intervention catalog

**Status:** READY (drop-in)
**Loaded when:** a specific bottleneck class is named and you want the candidate fixes for it.

This is the lookup table for the **fix** step of the SKILL.md loop. You arrive from `../diagnose/` with one named, located bottleneck and a one-sentence causal model; `index.md` has already told you which *lever tier* to spend in. This leaf turns the bottleneck class into a short list of candidate interventions, each with the regime where it pays.

The rule that orders everything here: **the intervention is dictated by the binding constraint, not by which technique is fashionable.** A well-vectorized loop the memory system cannot feed is not faster. A lock-free queue that lives in CAS retries under contention is not faster. Pick from the table that matches your bound, not from the technique you already wanted to use. If you do not yet have a single named bound, go back to `../diagnose/index.md` and `../orient/bound-types.md` first; a catalog is useless without a diagnosis.

How to use a row: read the **When it applies** column as a precondition, not a suggestion. If your measurement does not satisfy it, skip the row. After applying one, re-measure (`../measure/verify.md`) before reaching for the next, because the first fix moves the bottleneck.

**Platform scope.** The interventions are portable, but the commands, counter names, and numbers below are written for a Linux/x86 host (`perf` and eBPF counters, `numactl`, `/proc`, `MAP_HUGETLB`, a 64-byte cache line). When you are working LOCAL on macOS / Apple Silicon, the candidates still apply but the tooling and constants differ — `perf`/eBPF are Linux-only, the cache line is 128 bytes, and several knobs map to different APIs. See `../environment/local-mac.md` for the macOS equivalents; per-item caveats are inlined where they bite.

---

## The intervention tables (one per bound class)

### 1. Retiring-dominant (compute-bound on useful work)

You are already doing useful work nearly every cycle. To go faster you must do *less* work or *wider* work.

| Intervention | When it applies |
|---|---|
| **Better algorithm** | Always the first question. O(n²) at n=10⁶ is a different problem than O(n log n); no micro-optimization recovers the gap. |
| **SIMD / vectorization** | Inner loop is uniform arithmetic over contiguous data, no loop-carried dependencies, no function calls. |
| **Parallelism** | The work decomposes and the memory system is not already saturated. |
| **Strength reduction** | Replacing expensive ops (divide, modulo, transcendentals) with cheaper equivalents. |
| **Precomputation / memoization** | Results are reused across calls. |

### 2. Bad-speculation-dominant (branch misprediction)

The pipeline is constantly flushing speculative work.

| Intervention | When it applies |
|---|---|
| **Sort or group input** | The branch becomes predictable because like cases cluster. Often the highest-leverage single change. |
| **Branchless code (`cmov`, masks)** | Both branches are cheap to execute unconditionally *and* the branch was genuinely unpredictable. |
| **Profile-guided optimization (PGO)** | The compiler needs to know the common path to lay out code correctly. |
| **Reduce indirect dispatch** | Devirtualize, inline, replace virtual calls with switches over small enums, hoist dispatch out of inner loops. |
| **Specialized versions** | Split one generic loop into two specialized loops where the branch is hoisted out. |

Do not reach for branchless code when the branch was already well-predicted. A correctly predicted branch that skips expensive work is often the fastest option; making it branchless executes the expensive work every time.

### 3. Front-end-bound

The back-end can execute but the front-end cannot supply µops fast enough.

| Intervention | When it applies |
|---|---|
| **Shrink the hot code footprint** | Excessive inlining, large switch statements, or unrolled loops overflowing the µop cache. |
| **Reduce indirect calls in the hot path** | Virtual dispatch and function pointers feed the weaker indirect predictor. |
| **Selective inlining** | Inline small leaf functions; stop inlining at the point where code size starts to hurt. |
| **Huge pages for code** | On very large binaries, iTLB misses can front-end-bound the program. |

### 4. Back-end memory-bandwidth bound

You are moving bytes as fast as the memory system allows (near STREAM).

| Intervention | When it applies |
|---|---|
| **Reduce bytes moved** | SoA layout when scanning narrow fields; quantization to smaller types (float32 → int8); compression. |
| **Increase reuse** | Tile/block the computation so each cache line is touched many times before eviction. |
| **Streaming stores (non-temporal writes)** | Writing data that will not be re-read soon; bypasses cache, frees bandwidth. |
| **Fewer threads, not more** | Above the bandwidth knee, additional threads add contention without throughput. |

### 5. Back-end memory-latency bound

Bandwidth is fine; the CPU is waiting on the round-trip for individual loads.

| Intervention | When it applies |
|---|---|
| **Improve locality** | Move related data together; reorder traversal; replace pointer chains with arrays. |
| **Increase memory-level parallelism** | Batch multiple independent chains of dependent loads so the CPU can overlap them. |
| **Software prefetch** | Last resort; effective only when prefetch distance is computable and the pattern truly defeats the hardware prefetcher. |
| **Huge pages** | Cuts TLB misses when the working set is large and random. |
| **Change data structure** | Linked list → array; chained hash table → open-addressed; pointer tree → implicit heap. |

### 6. Back-end core-bound

An execution port is saturated or a dependency chain serializes.

| Intervention | When it applies |
|---|---|
| **Break dependency chains** | Multiple accumulators in reductions; independent iteration streams. |
| **Rebalance port pressure** | Replace two shifts with a shift and an add; the scheduler has freedom when ports differ. |
| **Reduce long-latency ops** | Divides, square roots, FP transcendentals are multi-dozen-cycle; replace with approximations if semantics allow. |

### 7. Coherence / false sharing

Threads are correct but the cache line holding their "independent" data is ping-ponging.

| Intervention | When it applies |
|---|---|
| **Pad to cache-line boundaries** | `alignas(64)` on per-thread structures — but 64 is x86. Apple Silicon uses a 128-byte cache line; prefer `std::hardware_destructive_interference_size` over a hardcoded 64, or query at runtime with `sysctl hw.cachelinesize`. |
| **Per-thread data with periodic reduction** | Replace shared counter with per-thread counter summed occasionally. |
| **Sharding** | Partition state so each partition is touched by one thread. |

### 8. Lock contention

Threads are blocking on each other.

| Intervention | When it applies |
|---|---|
| **Reduce critical section** | Move work out of the lock; the lock protects the update, not the computation. |
| **Finer-grained locks** | Per-bucket, per-key, per-partition instead of global. |
| **Lock-free data structures** | Blocking is unacceptable *and* measurement proves the lock is the bottleneck *and* contention is moderate. |
| **Eliminate sharing** | Per-thread accumulators, single-writer ownership, message passing. |

Reach for lock-free last. Most "lock contention" problems are really "too much shared state" problems and disappear when you reduce sharing.

### 9. NUMA

The data is on the wrong socket for the thread that needs it.

| Intervention | When it applies |
|---|---|
| **Pin threads and memory** | `numactl --cpunodebind=N --membind=N` for per-socket workers. |
| **Parallel first-touch** | Each worker initializes its own region, so first-touch places pages locally. |
| **Interleave** | `numactl --interleave=all` for workloads whose access pattern is unpredictable across sockets. |
| **Shard by NUMA node** | Treat each socket as an independent instance, like separate machines. |

### 10. Kernel / syscall-bound

Time is in the kernel, not in your code.

| Intervention | When it applies |
|---|---|
| **Batch I/O** | `writev`, `sendmmsg`, larger `read`/`write` sizes; one syscall for many operations. |
| **io_uring** | Submit and complete I/O in bulk through a shared ring; closes most of the gap with kernel bypass for storage (vs SPDK) and moderate rates, less so at the extreme packet rates where DPDK's polled user-space drivers still win (see the kernel-bypass card). Linux-only. |
| **Kernel bypass (DPDK, SPDK)** | Only when syscall overhead truly dominates and you can dedicate cores to polling. |
| **Reduce context switches** | Pin threads; avoid blocking primitives in hot paths; use lock-free producer-consumer where appropriate. |

### 11. Tail-latency-bound

The average is fine; the tail is the problem.

Unlike tables 1–9, this is not a top-down microarchitectural bound. Tail latency is a cross-cutting *symptom*, so it has no row in `index.md`'s bound→lever table or in `../orient/bound-types.md`; do not expect a 1:1 mapping from this table number back to those. It is included here because the same fixes recur, but you reach it from a tail observation, not from a top-down classification.

| Intervention | When it applies |
|---|---|
| **Identify the pause source** | GC, page fault, JIT, scheduler, lock spike — each has a specific fix. |
| **Reduce allocation rate** | Fewer collections; often the single most effective change for managed-runtime tails. |
| **Pin memory (`mlock`)** | Eliminates major faults for latency-critical regions. |
| **Pretouch / warm up** | First access to a page costs; touch everything before timing starts. |
| **Low-pause collectors** | ZGC, Shenandoah (Java); Go's concurrent collector; carefully tuned G1. |
| **Move heavy work off the request path** | Pre-compute, precompile, pre-allocate; the request thread does only latency-critical work. |
| **Hedged requests** | Send a second request after a timeout; return the first response. Trades throughput for tail. |

---

## Technique cards: emerges-when / over-engineering signal

The rows above name interventions; some of them resolve to a specific technique that recurs across bound classes. Each technique is *forced* by a particular bottleneck combination and is *over-engineering* outside it. Recognizing which case you are in is most of the skill. Read the "over-engineering signal" before you commit: if it describes your situation, you are about to add permanent complexity for no measured gain.

**SoA (struct of arrays).** *Emerges when* phases scan narrow subsets of fields across many objects and cache-line utilization under AoS would be low. *Looks like* each field as its own contiguous array; hot loops become stride-1 streams the prefetcher handles trivially. *Real examples* particle sims, ECS in games, columnar engines (Parquet, DuckDB, ClickHouse). *Over-engineering signal* converting to SoA when each phase touches most fields of each object anyway — the bytes came along for the ride and were going to be used; SoA buys nothing and loses the one-pointer convenience of AoS.

**Branchless code.** *Emerges when* a hot branch is genuinely unpredictable (miss rate 20%+) and both sides are cheap to execute unconditionally. *Looks like* a `cmov`, mask-and-add, table lookup, or predicated SIMD lane; control flow becomes data flow. *Real examples* sorting-network primitives, bit-parallel string matching, vectorized filters where a predicate selects lanes. *Over-engineering signal* making every branch branchless. A predictable branch that skips expensive work is often the fastest option; the predictor already made it free and now you execute the expensive side every iteration.

**SIMD / vectorization.** *Emerges when* the workload is retiring- or core-bound on arithmetic, the inner loop is uniform, and memory can keep the vector units fed. *Looks like* contiguous stride-1 access, no calls in the loop, no aliasing (via `restrict`), reductions with multiple accumulators, predicated lanes instead of branches. *Real examples* numerical kernels (BLAS, FFT), image/video codecs, JSON parsing (simdjson), hashing/compression (CRC, zstd). *Over-engineering signal* SIMD on a bandwidth-bound loop. If the loop already saturates DRAM, wider arithmetic buys nothing — the data is not arriving faster. Vectorize after fixing layout, not before.

**Lock-free data structures.** *Emerges when* blocking is unacceptable (latency-sensitive or progress-required), measurement shows the lock is the bottleneck, and contention is moderate enough that CAS retries do not dominate. *Looks like* atomics with acquire/release ordering, epoch-based or hazard-pointer reclamation, carefully paired fences; correctness is hard and high-contention wins over a mutex are not guaranteed. *Real examples* per-CPU run queues, lock-free queues in trading systems, hazard pointers in DBMS buffer pools, RCU in the Linux kernel. *Over-engineering signal* reaching for lock-free because "mutexes are slow." Uncontended mutexes are ~20 ns; the usual fix for a contended mutex is less sharing, not more sophisticated synchronization.

**Huge pages.** *Emerges when* the working set is large (tens of MB+) and randomly accessed, making the 4 KB TLB the binding constraint. *Looks like* a TLB entry covering 2 MB or 1 GB instead of 4 KB; random access over a multi-GB heap becomes tractable. *Real examples* databases with multi-GB buffer pools, JVMs with large heaps, scientific sims with GB working sets, in-memory caches (Redis, memcached) on large instances. *Over-engineering signal* enabling transparent huge pages on a latency-sensitive service without understanding THP compaction. THP can cause seconds-long stalls as the kernel defragments to form a 2 MB page; many latency-sensitive shops disable THP and use explicit `hugetlbfs` only.

**Kernel bypass (DPDK, SPDK, XDP).** *Emerges when* syscall and kernel-stack overhead demonstrably dominate, often at 10M+ packets/sec or 1M+ IOPS per core. *Looks like* user-space drivers, polled I/O, huge pages for DMA buffers, dedicated cores spinning at 100%, zero syscalls on the data path. *Real examples* HFT, software load balancers (Katran at Meta), packet-processing appliances, NVMe-heavy storage. *Over-engineering signal* DPDK for a web service doing 10K req/sec. The kernel network stack is not your bottleneck at that rate; your application logic is. You pay the cost of bypass (dedicated cores, complexity, lost isolation) for no benefit.

**Sharding and per-thread data.** *Emerges when* a shared data structure is the bottleneck on a multi-core system but the work itself is independent per partition. *Looks like* each thread owning a slice of state, periodic (not per-op) aggregation, no coherence traffic on the hot path. *Real examples* ScyllaDB's shard-per-core, Redis Cluster hash slots, per-CPU counters in the Linux kernel, sharded maps. *Over-engineering signal* sharding a workload with no actual shared-state bottleneck. Sharding adds rebalancing and cross-shard query cost; if single-threaded or lock-free would have worked, you paid for complexity you did not need.

**Software prefetch.** *Emerges when* the access pattern is data-dependent (hash probes, tree walks, index lookups) but the *next* address is computable several iterations in advance. *Looks like* `__builtin_prefetch(next)` issued at a tuned distance ahead of use, overlapping the load with unrelated work. *Real examples* B+-tree traversals, hash-join probes, graph algorithms with a known frontier. *Over-engineering signal* sprinkling prefetches into a sequential loop. The hardware prefetcher already handles stride-1 and extra hints add pollution; the hardware is smarter than your hints there.

**NUMA pinning.** *Emerges when* measurement shows substantial cross-socket DRAM access on a multi-socket machine and latency or bandwidth is the bottleneck. *Looks like* `numactl --cpunodebind=N --membind=N`, parallel first-touch init, per-socket instances. *Real examples* databases on multi-socket servers (Postgres, Oracle), JVM services sharded per-socket, scientific codes with domain decomposition. *Over-engineering signal* NUMA pinning on a single-socket machine. There is no NUMA; pinning there just costs you load balancing.

---

## Technique selection, once a row is chosen

A bound class usually offers several rows. Order the candidates by these criteria, not by appeal:

1. **Data change or code change?** Layout and access-pattern changes are usually higher-leverage and lower-risk than instruction changes. Explore those first.
2. **Is a simpler intervention sufficient?** A 10% win from huge pages with no code change beats a 15% win from hand-written SIMD. Operational cost counts.
3. **Does it compose with the rest of the system?** SIMD inside a virtual call gains nothing (the compiler can't see through dispatch); lock-free inside a single-writer path is pointless.
4. **Can you measure whether it worked?** The counter you expect to move must actually move. If it does, but wall time does not follow, a secondary bottleneck is now binding.

Common intervention → technique mappings, with the regime to deviate:

| Intervention | Typical technique | When to deviate |
|---|---|---|
| Reduce bytes moved | SoA layout, narrower types, column pruning | AoS when every field is touched in the phase |
| Improve locality | Tiling, space-filling curves, arena allocation | Tiling overhead exceeds benefit below certain sizes |
| SIMD | Compiler auto-vectorization (`restrict`, inline, `-O3 -march=native`) | Intrinsics/hand SIMD when the compiler can't see enough; ISPC for portable SIMD |
| Branchless | Ternary lowering to `cmov`; mask ops | Keep the branch when well-predicted and it skips expensive work |
| Reduce sharing | Per-thread state, thread-local allocators, sharded maps | Pay coordination cost only where threads must agree |
| Lock-free | `std::atomic` acquire/release on a proven bottleneck | A padded mutex under low contention is simpler and often equal |
| Huge pages | THP or explicit `hugetlbfs` | Disable THP on latency-sensitive services that see compaction spikes |
| Kernel bypass | io_uring first; DPDK/SPDK only at extreme rates | Batching inside standard syscalls often closes most of the gap |
| GC tuning | Adjust heap/region size before changing collectors | Change collectors when pauses can't be met by tuning |

---

## Worked example: in-memory columnar analytics, p99 = 4× median

**Diagnosis handed over** (from `../diagnose/`): scan-shaped, 16 threads, ~20 GB working set beyond L3. Top-down 55% back-end memory-bound, mostly DRAM *latency* (bandwidth 72% of STREAM — substantial, not saturated). dTLB miss 2% of memory accesses (walks ÷ loads+stores; name the denominator, since "2%" per-instruction or as MPKI means something different), branch miss 0.4%, IPC 1.6. Scaling linear to 8 threads, sublinear to 16. Tail bumps correlate with queries scanning newly-loaded data regions. Primary bound: **memory latency, specifically TLB pressure on large scans.** Secondary: bandwidth saturation will surface at higher thread counts. Tail driver: minor faults and cold TLB on recently loaded pages.

**Catalog lookup.** The primary bound is *back-end memory-latency* (table 5) plus a *tail-latency* component (table 11):

- From table 5, the **huge pages** row fits: working set large and the dTLB miss at 2% of memory accesses is in the dominant band. A 2 MB entry covers 512× the address space of a 4 KB entry, so it should cut the dTLB-walk cycles driving the latency bound.
- From table 11, **pretouch / warm up**: a background warmer that reads one byte per 2 MB page after load eliminates the first-query minor-fault spike on the serving thread.
- Holding for later, from table 4 (bandwidth, the secondary bound): **reduce bytes moved** via narrower types — the kernel uses int64 aggregates for counts that fit in int32 — applied only *after* confirming the TLB fix.

**Rows deliberately not taken.** Hand-written SIMD (compiler already vectorizes the inner loops), lock-free coordinator state (coherence traffic minor, not the bottleneck), NUMA pinning (single-socket), kernel bypass (I/O is not the issue). Each is an over-engineering signal here.

**Technique within the chosen rows.** Allocate the columnar arena from explicit huge pages rather than THP, precisely because THP compaction would land in the tail metric the team cares about (technique card: huge pages). Either an anonymous `mmap` with `MAP_HUGETLB`, or an `mmap` of a file on a `hugetlbfs` mount — both reserve from the explicit pool and bypass THP; the mount is needed only for the file-backed route, not for the anonymous one. (Linux; on Apple Silicon see `../environment/local-mac.md` for the macOS large-page story.)

**Predicted counters, to confirm in `../measure/verify.md`.** dTLB miss 2% → ~0.1% of memory accesses; back-end memory-bound 55% → ~35% as TLB-walk cycles vanish; LLC miss roughly unchanged (still doesn't fit L3 — we addressed translation, not capacity); p99 drops because the cold-page tail is gone. If dTLB misses drop but wall time doesn't, the secondary bandwidth bound is now binding (apply the type-narrowing row). If dTLB misses *don't* drop, the allocator silently fell back to 4 KB — verify with `/proc/meminfo` and `pmap -XX <pid>` (Linux; this whole worked example is Linux-host-scoped — top-down counters via `perf`, `/proc`, `pmap`. On Apple Silicon, see `../environment/local-mac.md` for the counter and large-page equivalents).

The discipline the example shows: one named bound selected one table, the table's preconditions filtered the rows, and every untaken row was rejected by an over-engineering signal, not by taste.

---

## Where next

| Situation | Go to |
|---|---|
| Unsure which lever tier this bottleneck lives in | `index.md` |
| The chosen intervention is a knob with a cost to weigh | `tradeoff-knobs.md` |
| Don't yet have a single named bound | `../diagnose/index.md`, `../orient/bound-types.md` |
| Intervention applied, need to prove it | `../measure/verify.md` |
| Counter moved but wall time didn't (secondary bound surfaced) | re-run `../diagnose/index.md`, then back here |
