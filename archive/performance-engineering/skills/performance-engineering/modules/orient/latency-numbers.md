# Latency & bandwidth numbers, and back-of-envelope estimation

**Status:** READY (consolidated)
**Loaded when:** estimating whether a design can meet a target, or sizing a system on paper before building.

This leaf is the arithmetic the gate and the design module lean on. Before you build (or before
you chase a slowdown), you can often rule a design in or out on a whiteboard: count the bytes it
moves, count its round trips, multiply by the numbers below, and compare to the target. A design
that needs 20 serial 1 ms hops cannot meet a 10 ms p99, and you can know that without writing a
line of code. The core rule: **the irreducible latency floor and the bytes-moved floor are both
computable from known constants; if either floor exceeds your budget, no amount of tuning saves the
design — change the shape.**

These are order-of-magnitude numbers. The exact values drift by hardware generation, vendor, and
load. The *ratios* and the *gaps between tiers* are stable, and the gaps are what the arithmetic
turns on. Treat every number as "good conditions, recent server-class hardware"; production under
load is worse, which is why an estimate that's close is already a fail.

---

## The latency ladder

One operation, time to complete, on a ~3 GHz core where one cycle is ~0.3 ns. Read it top to
bottom as the cost of reaching successively farther from the core.

| Operation | Latency | In cycles | Note |
|---|---|---|---|
| Integer op / register access | ~0.3 ns | ~1 | the "free" baseline |
| L1 cache hit | ~1–1.5 ns | 4–5 | 32–48 KB/core |
| L2 cache hit | ~3–5 ns | 12–15 | 256 KB–1 MB/core |
| L3 / LLC hit | ~10–20 ns | 30–60 | shared on socket, 4–64 MB |
| Branch mispredict | ~5 ns | 15–20 | full pipeline flush |
| DRAM load (local socket) | ~60–100 ns | 200–350 | the "memory wall" |
| DRAM load (remote NUMA socket) | ~130–250 ns | 400–600+ | one interconnect hop |
| Uncontended atomic (`lock` op) | ~5–10 ns | 15–30 | more than a store |
| Uncontended mutex lock/unlock | ~15–25 ns | — | ≥ two atomic RMWs even on the fast path |
| Syscall (no-op, mitigations on) | ~100–500 ns | — | user/kernel transition |
| Context switch | ~1–5 µs | — | plus cache/TLB warmth loss (can dominate) |
| Minor page fault | ~1–several µs | — | zero-fill or COW remap, no I/O |
| Contended mutex (slow path) | ~1 µs+ | — | futex syscall + scheduler delay |
| Local NVMe read | ~10–100 µs | — | ~7 GB/s sequential per drive |
| Major page fault (swap / demand page-in) | ~milliseconds | — | hits disk; tail-latency killer |
| Same-datacenter network RTT | ~0.1–0.5 ms | — | within an AZ |
| Cross-AZ / cross-region RTT | ~1–100 ms | — | physics: ~1 ms per 100 km, round trip |
| S3 GET (first byte) | ~20–100 ms | — | fixed floor, longer tail |

Anchors worth memorizing: **arithmetic ~1 cycle, DRAM ~300 cycles, mispredict ~15–20 cycles,
syscall ~hundreds of ns, S3 GET ~tens of ms.** The register-to-DRAM gap alone (~1000x) is why most
"CPU-bound" code is really memory-bound (see `bound-types.md`), and why the design module's Lever 2
is "move fewer bytes" rather than "do cleverer arithmetic" (`../design-and-lifecycle/design-for-performance.md`).

## The bandwidth tiers

Throughput, once you keep the pipe full. A latency floor caps a *single* operation; a bandwidth
floor caps *sustained bytes/sec* no matter how much concurrency you add.

| Path | Bandwidth | Note |
|---|---|---|
| L1/L2 cache | hundreds of GB/s/core | the prefetcher's happy place |
| DRAM (per socket, STREAM) | ~20–100+ GB/s | shared across all cores on the socket |
| Cross-socket (NUMA interconnect) | lower than local, shared | remote bandwidth is the scarce one |
| Local NVMe (single drive) | ~7 GB/s seq read | array of them: 30–80+ GB/s |
| Network-attached storage (e.g. EBS) | over the network | adds RTT vs local NVMe |
| NIC, small instance | a few Gbps | ~0.1–0.5 GB/s |
| NIC, mid-tier instance | 25–50 Gbps | ~3–6 GB/s |
| NIC, large/network-optimized | 100–400 Gbps | ~12–50 GB/s; the single-box ceiling |
| S3 aggregate (well-sharded) | ~NIC line rate | high *only* with enough concurrent requests |

Two facts the tiers hide. First, **DRAM bandwidth is shared**: a 32-core box does not get 32x one
core's bandwidth, so a memory-bound parallel scan plateaus well before all cores are busy (the
streaming-scan curve flattens around the socket's STREAM number; more threads then hurt latency
without raising throughput). Second, **S3's two numbers pull opposite ways**: each GET is slow
(~50 ms) but aggregate bandwidth is near your NIC's line rate *if* you issue enough GETs at once.
That tension is the whole reason for the latency-hiding pipeline (`../design-and-lifecycle/latency-hiding.md`).

## Two constants that turn the numbers into a method

**Cache line = 64 bytes (x86-64; 128 bytes on Apple Silicon).** The unit of memory movement.
Reading one byte that misses fetches the whole line. So "bytes moved" in the back-of-envelope is
*lines touched x line size*, not the size of the fields you actually read — under a bad layout you
pay for the whole line and use a fraction. Confirm the size on the host rather than hardcoding it:
on Linux/x86 `getconf LEVEL1_DCACHE_LINESIZE`; on macOS / Apple Silicon that parameter does not
exist — use `sysctl hw.cachelinesize` (returns 128). See `../environment/local-mac.md` for the
macOS-local tooling. In code, prefer `std::hardware_destructive_interference_size` over a hardcoded
64 so padding tracks the target. The *lines touched x 64* shorthand used below assumes a 64-byte
line; on a 128-byte-line machine it is *x 128*, so the byte estimate doubles.

**Little's Law:** `concurrency = throughput x latency`. The bridge between the latency ladder and
the bandwidth tiers. To sustain a target throughput over an operation with a fixed latency, you
need that many operations in flight. It is how you size a prefetch pipeline, a connection pool, a
thread count, or a TCP window — same equation every time.

---

## The back-of-envelope method

Five steps. Produce numbers, then compare to the target. Each step has a tier of the tables behind
it.

### 1. State the target as a number
A budget you can compare against: p99 latency, throughput (RPS or GB/s), or a cost line. No number
means no estimate is possible — go back to the gate in SKILL.md. "Fast" is not a target;
"p99 < 50 ms at 8k RPS" is.

### 2. Count the bytes moved per unit of work
For one request (or one item, one batch), how many bytes must physically move, and across which
tier? Walk the path: bytes read from S3 / disk, bytes streamed from DRAM, bytes shuffled between
nodes. Use **lines touched x 64** for memory-resident structures, and account for read
amplification (reading 100 columns to use 3 moves ~33x the necessary bytes; a row-store dragging
whole rows through cache to touch one field is the same tax at the cache-line level). Then:
`time_floor = bytes / bandwidth_of_that_tier`, picking the bandwidth row the bytes actually cross.

### 3. Count the round trips and find the latency floor
How many *serial*, dependent operations sit on the critical path? Serial RTTs, serial S3 GETs,
serial dependent DRAM loads (pointer chasing), serial cross-service hops. The latency floor is
their sum:
`latency_floor = sum of (each serial dependent op's latency from the ladder)`.
Operations that can run *concurrently* do not add — they overlap, and their cost is governed by
step 4, not this sum. The whole game is moving operations from "serial, so they add" to "concurrent,
so they overlap."

### 4. If throughput is the target, size concurrency with Little's Law
`concurrency = target_throughput x per_op_latency`. This tells you how many operations must be in
flight to hit the rate, and therefore how deep the pipeline, how many connections, how many
threads. If the required concurrency exceeds what the tier allows (S3 prefix limits, NIC saturation,
pool ceiling), the target is infeasible at this design — and you've found the binding constraint on
paper.

### 5. Compare to the target and sanity-check
- If `latency_floor > p99 budget`: the design **cannot** meet latency. No tuning closes a floor.
  Cut serial hops (batch, parallelize, precompute) or change the path.
- If `bytes / bandwidth > budget`: you are bandwidth-bound. Move fewer bytes (project, compress,
  narrower types, better layout); adding cores or concurrency will not help.
- If both floors sit comfortably under budget: the design is *plausible*. The estimate cannot prove
  it hits the target (queueing, contention, tails, and the second bottleneck are not in the
  arithmetic), so build the simple version and run the loop. A floor under budget is permission to
  build, not a guarantee.

Sanity-check the magnitude before trusting it: does the dominant term make sense? An estimate is a
ranging shot, good to a factor of 2–3. Its job is to rule designs *out* cheaply, not to predict the
final number.

---

## Pitfalls

- **Adding concurrent latencies.** The most common error: summing operations that actually overlap.
  20 S3 GETs issued together cost ~one GET latency, not 20. Only *serial dependent* operations add.
  Conversely, do not assume things overlap that are actually dependent (pointer chasing, RPC chains
  where each call needs the last result) — those are serial and do add.
- **Using a latency number where a bandwidth number belongs (or vice versa).** "It's a 50 ms GET"
  bounds one fetch; it says nothing about sustained ingest, which is a bandwidth-and-concurrency
  question. Size single-shot critical paths with the ladder, sustained streams with the tiers plus
  Little's Law.
- **Forgetting bandwidth is shared.** Per-core DRAM bandwidth, cross-socket links, and a single
  NIC are shared resources. Multiplying one core's number by core count overstates a parallel
  design's ceiling, often by a lot.
- **Trusting microbenchmark numbers as production numbers.** Every value here is "good conditions."
  Production adds queueing, cold caches, noisy neighbors, and tails. An estimate that *barely* fits
  the budget is a fail; you need margin.
- **Estimating the wrong term.** Find the dominant cost first. If one S3 GET dominates a request's
  budget, the cache-line arithmetic inside the kernel is noise — do not polish it.

---

## Worked examples

**1. 20 serial hops vs a 10 ms p99.** A request fans through 20 services in a chain, each a
same-datacenter RPC at ~0.5 ms RTT, each waiting on the previous one's result. Latency floor =
20 x 0.5 ms = 10 ms of pure network, before any service does a microsecond of work. Against a 10 ms
p99 budget this is already over, and that's the *floor* under perfect conditions — real p99 includes
each hop's own processing and tail. Verdict: infeasible by construction. The fix is structural:
collapse the chain (batch the calls, parallelize the independent ones so they overlap instead of
add, or precompute the assembled result). No per-service tuning can recover a floor that already
exceeds the budget.

**2. Sizing an S3 ingest pipeline.** Target: feed a GPU kernel at 10 GB/s. S3 GET latency ~50 ms,
chunk size 10 MB. Bytes step: 10 GB/s / 10 MB = 1000 GETs/s required. Little's Law:
`concurrency = 1000 GET/s x 0.05 s = 50` GETs in flight, continuously. So design a pipeline with
~50 outstanding range-GETs behind a bounded queue. Check the floors: 50 concurrent GETs across
enough prefixes is within S3's per-prefix limits, and 10 GB/s is ~80 Gbps, so you need a
large/network-optimized NIC (a mid-tier 25–50 Gbps box cannot do it — there's your binding
constraint). Feasible on the right instance; the full pattern is `../design-and-lifecycle/latency-hiding.md`.

**3. Bandwidth floor on an in-memory scan.** Aggregate over 1 GB of events per request, stored
row-major as 64-byte rows where the aggregate needs one 4-byte field. Bytes moved (bad layout):
you touch one field per row but drag the whole 64-byte line, so ~1 GB crosses DRAM. At ~50 GB/s
STREAM that's 20 ms per request from memory bandwidth alone — and it doesn't parallelize away,
because the bandwidth is shared. Switch to columnar (SoA) so the scan reads only the needed field:
~1/16 the lines, ~62 MB, ~1.2 ms. The layout flip, not more cores, is what moves the floor under a
tight budget. (Layout reasoning: `../design-and-lifecycle/design-for-performance.md`, Lever 3.)

**4. Is this path memory-bound or compute-bound, on paper?** A kernel does ~10 arithmetic ops per
8-byte element streamed from DRAM. Compute: 10 ops x ~0.3 ns ≈ 3 ns/element. Memory: 8 bytes /
50 GB/s ≈ 0.16 ns/element of bandwidth, but if accesses miss to DRAM at ~80 ns latency and don't
overlap, latency dominates. With sequential access the prefetcher overlaps the loads and you're
compute-bound (~3 ns/element); with pointer chasing each element is a serial ~80 ns DRAM round trip
and you're 25x slower for the identical op count. Same big-O, same arithmetic, floor set entirely by
access pattern. The envelope tells you which regime before you build it.

---

## Where next

| You're doing… | Go to |
|---|---|
| sizing a design from these numbers | `../design-and-lifecycle/design-for-performance.md` (Lever 1 sizing, Lever 2 bytes) |
| hiding the latency you just estimated | `../design-and-lifecycle/latency-hiding.md` (the Little's Law pipeline) |
| sustained-load / scaling-knee sizing | `../design-and-lifecycle/capacity-scalability.md` |
| turning a budget into an SLO | `../design-and-lifecycle/budgets-slos.md` |
| deciding what *kind* of bound a path hits | `bound-types.md` |
| placing a cost on a specific stack layer | `software-stack.md` |
| classifying the workload before sizing | `work-taxonomy.md` |
| you have a real system and want measured numbers | `../diagnose/` (estimate ends where measurement begins) |
