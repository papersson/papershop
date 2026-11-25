# Latency hiding (Little's Law pipelines)

**Status:** READY
**Loaded when:** an irreducible latency (DRAM / SSD / S3 / RPC) can be converted into a throughput problem.

This is Lever 4 of `design-for-performance.md` worked in full: the design move that takes a latency you
cannot shrink and makes it stop costing you. The core claim is one sentence. **You cannot make a single
slow operation faster, but you can keep enough independent operations in flight that completions arrive
continuously**, at a rate set by your concurrency rather than by any one operation's latency. Done right,
the slow tier disappears behind the pipeline; done wrong, you pay full price for it on every access.

The arithmetic that makes "enough" precise is Little's Law, and it is not a heuristic, it is a theorem of
queueing. Once you have it, the question is never *whether* concurrency hides latency (it does), only
whether you have *enough* concurrency to hide it at your target throughput, and whether three physical
preconditions hold.

---

## Procedure

Run these in order. Each step has a number you compute or a precondition you check; do not skip to code.

### 1. Confirm the latency is irreducible and the work is hideable
- The per-operation latency is a floor you do not control: a DRAM miss (~300 cycles), an SSD/NVMe read
  (tens of µs), an S3 GET (~20-100 ms), a remote RPC (RTT plus service time). Numbers: `../orient/latency-numbers.md`.
  If the latency is *avoidable* (you are reading data you do not need, or making a round trip you could
  batch away), fix that first in Lever 2 of `design-for-performance.md`. Hiding is for what is left.
- Future work is **knowable early**. Sequential scans, chunked/range-readable files, batched lookups, and
  independent shards let you name the next N operations now, so you can start them now. If the next address
  or request depends on the current *result*, you cannot prefetch it. See "Where it cannot apply" below
  before committing to this pattern.

### 2. Size the pipeline with Little's Law
The completion rate of any queueing system is `concurrency / latency`. Rearranged for what you control:

```text
request_throughput = concurrency / latency
byte_throughput    = concurrency × bytes_per_request / latency

required concurrency = target_byte_throughput × latency / bytes_per_request
```

Read it as: to keep completions arriving fast enough to feed the consumer, you need that many operations
outstanding *continuously*. Plug in real numbers from step 1, do not guess the depth. This single
calculation is the difference between a pipeline that saturates the consumer and one that starves it.

### 3. Build the producer-consumer pipeline
The structural realization of the law is four moving parts:

1. A pool of **producers** (IO workers) issues asynchronous requests against the slow tier, many at a time
   (the concurrency from step 2). As each completes, it decodes/decompresses into the in-memory unit the
   consumer wants (a tile, batch, record group, chunk).
2. Completed units land in a **bounded queue** in RAM.
3. The **consumer** (the kernel: a GPU step, a vectorized scan, a simulation update) pulls units off the
   queue and processes them at full hardware speed.
4. When the consumer finishes a unit, the freed slot lets another producer request proceed.

The two sides run independently. The producer side is bounded by the slow tier's aggregate bandwidth and
your link; the consumer side by your compute rate. As long as the producer delivers units at least as fast
as the consumer drains them, the consumer never sees the slow tier's latency: some other operation is
always finishing while it works. The individual operations still take their full latency. The consumer just
never waits on any one of them.

### 4. Bound the queue by bytes and apply backpressure
The queue **must** have a fixed maximum, and bound it by **bytes**, not item count, whenever unit sizes
vary. This is not optional polish, it is the difference between a stable system and a latent OOM.

- Producers **block when the queue is full** and resume when the consumer frees a slot. This propagates the
  consumer's rate back to the producers automatically: when the consumer slows, IO slows to match. That
  feedback is **backpressure**.
- Without a bound, a producer faster than the consumer (even briefly) piles completed units in RAM until the
  process dies. Slow-tier latencies have long tails, so completions are bursty: 50 fetches outstanding can
  all land within a few hundred ms, dumping gigabytes into memory at once. Any consumer hiccup (a long
  batch, a GC pause, a noisy neighbor) then grows the queue without limit.

Mechanism per runtime: `asyncio.Queue(maxsize=N)`, Java `BlockingQueue` with capacity, Go buffered channel
`make(chan T, N)`, Tokio `mpsc::channel(N)`. The pattern is universal because the problem is.

### 5. Size the queue depth (a separate number from concurrency)
Concurrency (step 2) controls whether completions arrive fast enough. Queue depth controls how much
producer-rate *variance* you can absorb before the consumer stalls. They are different knobs:

- **Too shallow** (one or two units) and any IO hiccup stalls the consumer, because there is no buffer to
  ride over it. You lose the hiding you paid for.
- **Too deep** and you waste memory and add end-to-end latency, since units sit longer before processing.
- Rule of thumb: hold **a few seconds of consumer throughput**. Consumer at 1 GB/s, want to ride out 2 s of
  IO stalls → ~2 GB queue. The minimal case, exactly two buffers (one filling, one processing), is
  **double buffering**; deeper N-buffer pipelines are the generalization, and Little's Law sets N.

### 6. Verify the three preconditions actually hold
The pattern only hides latency when all three are true. If one fails, it fails in a recognizable way (see
Failure modes), and recognizing which one tells you what to fix.

| Precondition | Meaning | Symptom when it fails | Fix |
|---|---|---|---|
| **Enough concurrency** | outstanding ops ≥ Little's-Law floor | consumer idles waiting for data (GPU util drops, cores idle) | more in-flight requests, more workers, larger units |
| **Enough bandwidth** | link + client + service deliver ≥ consumer's draw | producer side can't keep the queue non-empty | bigger NIC/instance, better client, scale out, fewer bytes |
| **Enough compute per byte** | consumer spends enough time per unit for IO to prep the next | IO saturated, consumer still starved | you are genuinely IO-bound; raise arithmetic intensity or accept the ceiling |

The third precondition is **arithmetic intensity** (useful work per byte fetched), the roofline lever. High
intensity (a transformer layer, a complex query, a physics update) means the consumer is the bottleneck and
hiding works beautifully. Low intensity (summing bytes, a trivial filter) means you are fundamentally
limited by the slow tier's bandwidth, and no pipeline depth buys more than the tier can supply.

---

## Where it cannot apply

Pipelining hides latency only when you can start the next operation before you have the current result.
Two shapes break that, and for them the fix is structural, not more concurrency:

- **True pointer chasing.** Each `node->next` is a full-latency dependent load; the next address *is* the
  current result. Linked lists, chained hash tables, scattered pointer trees. You cannot prefetch what you
  cannot name. Fix is back at Lever 3 of `design-for-performance.md`: change the structure so accesses
  become independent (arrays, open-addressed tables, B-tree-like layouts), or batch many independent chases
  so their latencies overlap even though each chain is serial.
- **Coordination-dependent RPC chains.** Request B's contents depend on request A's response: a serial
  dependency graph across services, a read-modify-write that must see the prior write, a consensus round.
  No window of independent work exists to fill. Fix is to remove the dependency (Lever 5): make operations
  commutative or idempotent, fetch the graph in one batched call, or restructure so the hops are
  independent and *then* pipeline them.

The tell is the same in both cases: ask "can I name the next N operations right now?" If no, you are
dependency-bound, and the lever is to change the dependency, not to add buffers.

## The same trick, every tier

This is not an S3 technique. It is one principle that recurs at every level of the memory and network
hierarchy; only the slow tier changes:

- **CPU** hides cache-miss latency with out-of-order execution and memory-level parallelism (multiple
  independent loads outstanding). Same law, concurrency measured in in-flight loads.
- **GPU** hides DRAM latency by keeping thousands of warps resident; when one warp stalls on memory, the
  scheduler runs another. Concurrency measured in resident warps.
- **TCP** fills a long-fat link by allowing a window of unacknowledged bytes proportional to
  bandwidth × RTT. That window *is* Little's Law: it is exactly the in-flight data needed to keep the pipe
  full despite round-trip latency.
- **Databases** prefetch pages so the scan never waits on a single disk read.

Recognizing the shape means you can size any of them with the same formula and debug them with the same
three preconditions.

## Failure modes

The pattern underperforms, or quietly gives back its gains, in recognizable ways:

- **Count-bounded queue with variable unit sizes.** A queue capped at 16 items holds wildly different memory
  if units are sometimes 10 MB and sometimes 200 MB. Bound by bytes.
- **Decompression amplification.** A 10 MB compressed unit may be 100 MB decompressed. Sizing buffers by
  compressed size while holding decompressed data is off by 10x. Size by decompressed size, or stream
  decompression so the full inflated unit never exists at once.
- **Multiple pipelines in one process.** One loader per GPU, each with its own queue: per-pipeline limits
  multiply. Track total process memory, not one queue.
- **Framework defaults.** PyTorch DataLoader, Ray Data, Spark readers all have buffer knobs tuned for modest
  units. Large images, long sequences, or custom decoders make defaults too generous (OOM) or too stingy
  (stalls). Read the knobs.
- **Memory leak in the IO path.** A stray reference in a logging callback, a circular reference, a debug
  accumulator: memory grows even with a bounded queue. Insidious because nothing is structurally wrong.
- **Over-engineering.** Building a deep async pipeline for a path that runs a few thousand times and is
  nowhere near a latency or bandwidth limit. Hiding is for hot, data-heavy, latency-floored loops. Elsewhere
  it is concurrency complexity for no measured gain. The default is the simple serial version until a number
  says it misses the target.

## Worked example: hiding S3 latency for a streaming kernel

Setup: terabytes in S3, an expensive cluster (GPUs training, or CPUs running a vectorized scan). Data does
not fit in RAM, so it streams from S3 as the kernel runs.

**The naive cost.** Kernel processes 64 MB units at 5 GB/s → ~13 ms compute each. Each S3 fetch → ~50 ms
latency. Serial fetch-then-process: every iteration is 50 ms waiting + 13 ms working. Effective throughput
= 64 MB / 63 ms ≈ 1 GB/s. The GPU runs at ~20% utilization; a 12 GB/s NIC runs under a tenth of capacity.
The two underused resources are *independent*: the GPU sits idle during the fetch, the network sits idle
during the compute, and they are never both busy. You are paying cluster prices to wait on the network.

**Why it is fixable.** S3 has two characteristics pulling opposite ways. Per-request latency is high and
fixed (~20-100 ms, longer tail); no client tuning removes the round-trip floor. But aggregate bandwidth is
enormous *if you issue enough independent requests*, spread across prefixes and objects, up to your NIC line
rate. The whole pattern exploits the second property to hide the first.

**Step 2, size it.** Target the consumer's drain rate (5 GB/s here, per the precondition that bandwidth
delivers ≥ the consumer's draw): 5 GB/s at 10 MB per fetch → 500 fetches/s.
`concurrency = 500 × 0.05 = 25` fetches in flight, continuously. (Equivalently
`5 GB/s × 0.05 s / 10 MB = 25`.) That 25 is the Little's-Law floor; provision ~2x it (50 in flight) as
headroom for latency tails and bandwidth variance. A consumer twice as fast (10 GB/s) would double the
floor to 50. The formula gives the pipeline depth exactly.

**Steps 3-5, build it.** IO workers issue ~50 async range-GETs at once against a chunked, range-readable
format (Parquet/ORC/Zarr/WebDataset, so ranges are meaningful and columns are skippable). Completed,
decoded units land in a queue bounded by bytes (say ~10 GB ≈ 2 s of kernel throughput at 5 GB/s) with producers
blocking when full. The kernel pulls from the queue at 5 GB/s and never sees the 50 ms latency, because
some other GET is always finishing while it computes. Use an in-process in-memory queue, *not* Redis or
Kafka, which add network round-trips inside the fastest part of the system.

**Step 6, check preconditions.** Concurrency 50 sits at ~2x the Little's-Law floor of 25 (consumer drain 5 GB/s), the extra absorbing latency tails and burst variance. Bandwidth: a properly
configured client (AWS CRT, s5cmd, Rust `object_store`) on a right-sized instance pulls near NIC line rate,
and S3 scales out server-side, so spread requests across prefixes and *check* the NIC is not 80% idle from
an under-concurrent default client. Compute-per-byte: a training step or complex query has high arithmetic
intensity, so the kernel is the bottleneck and hiding works; a kernel that merely sums a column is IO-bound
by definition, capped at S3 aggregate bandwidth no matter the pipeline.

**Scaling and tiers.** The single-machine ceiling is the NIC. Scale horizontally (more instances, each its
own NIC) rather than vertically, because S3 is horizontally scaled server-side, the compute cluster already
scales out, and price-per-Gbps worsens on the largest instances. If the job makes repeated passes over a
working set (most ML training, many epochs), stage once from S3 to local NVMe (~30+ GB/s vs ~10 GB/s from
S3) and read from NVMe thereafter; each tier hides the one below it with the same pattern. Single-pass jobs
skip the NVMe stage; there is nothing to cache.

Result: the kernel sees a steady stream of in-RAM data at hardware speed, the IO subsystem absorbs all of
S3's latency in the background, and S3 behaves like the slowest tier of the memory hierarchy rather than a
wall. The same machinery that frameworks (PyTorch DataLoader, NVIDIA DALI, Ray Data) implement under the
hood, now sized and debuggable by hand when the defaults do not fit.

## Where next

| When you need… | Go to |
|---|---|
| the design-time context (this is Lever 4) | `design-for-performance.md` |
| sustained-load sizing, scaling knees, contention limits | `capacity-scalability.md` |
| the latency floors to plug into Little's Law | `../orient/latency-numbers.md` |
| to confirm which bound you are actually hitting | `../orient/bound-types.md` |
| the five lenses for workload + dependency shape | `../orient/work-taxonomy.md` |
