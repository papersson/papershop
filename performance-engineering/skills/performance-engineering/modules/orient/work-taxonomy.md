# Classifying the work (the lenses)

**Status:** READY
**Loaded when:** naming or classifying a workload, or when vague terms ("CPU-bound", "scalable", "real-time", "embarrassingly parallel") are causing confusion.

This is an **orient** leaf: it sits mostly before the loop's *locate* step (lenses 1–4 are knowable from the design; lens 5 previews and feeds locate) and gives you the vocabulary to describe a workload precisely enough that the rest of the loop has something to act on. The core claim: there is no single clean taxonomy of computational work, and that is not a terminology failure, it reflects the problem. The same program is compute-bound on one machine, memory-bound on another, network-bound at scale, and tail-latency-bound in production. So a useful classification is not one tree but a set of complementary lenses, applied together.

The working question, every time:

> What kind of work is this, what shape does it impose on the machine or system, and what limit is actually binding?

A good classification is not a label. It is a compact causal model of why the work performs the way it does and what kind of intervention is likely to help. The output you want is a sentence like *"latency-sensitive fanout request path, dominant op is remote reads, dependency-light locally but tail-bound by a downstream p99,"* never *"it's CPU-bound."*

---

## The five lenses

Apply all five. Each answers a different question; the misdiagnoses below come from using one lens as if it explained the others. For each, the discriminating question is what you actually ask of a workload in front of you.

### Lens 1 — Workload contract: what must it deliver?

The first classification, because it determines what "performance" even means. A 2x throughput win that worsens p99 is a regression for an interactive service and a win for a batch job; the contract decides which.

Discriminate along these axes:

- **Latency-sensitive vs throughput-oriented.** A checkout request or autocomplete endpoint cares about response time; a batch ETL or transcode cares about total work per dollar. They pull in opposite directions.
- **Which percentile is the contract?** Almost never the mean. A 2 ms-mean / 500 ms-p99 service is a 500 ms service with noise.
- **Interactive vs batch.** Interactive exposes humans to latency and variance; batch can trade latency for throughput and cost.
- **Deadline-based vs best-effort.** Real-time means deadline-constrained, not fast (see debunking below).
- **Open-loop vs closed-loop load.** Open-loop traffic arrives independently and exposes overload honestly; closed-loop clients wait for a response before sending more and hide tail latency.
- **Steady vs bursty.** Steady provisions near average; bursty needs buffering, autoscaling headroom, admission control, or graceful degradation.
- **Read-heavy vs write-heavy.** Read-heavy invites caching and replication; write-heavy hits coordination, durability, and compaction limits.
- **Hot-keyed vs uniform.** A hot key, shard, or partition collapses apparent parallelism no matter how many cores you add.
- **Stateful vs stateless. Single- vs multi-tenant.** Stateless workers replicate freely; stateful ones bring placement, recovery, locality. Multi-tenancy adds noisy neighbors and tail risk.

**Discriminating question:** *what does this system have to deliver, to which percentile, under what arrival process?* Write it as one sentence before designing or diagnosing. This lens is what `../design-and-lifecycle/design-for-performance.md` calls Lever 1, and it prevents optimizing the wrong thing.

### Lens 2 — Algorithmic or operator motif: what operation is this?

The logical structure of the computation, before any machine. Useful for algorithm selection and recognizing known implementation strategies; weak by itself for diagnosis, because "graph workload" or "ML workload" is too broad to predict performance without the other lenses.

Recurring motifs: dense linear algebra (matmul, convolution: regular, SIMD/GPU-friendly), sparse linear algebra (irregular, memory-bound), stencil/grid (neighbor updates, cache-reuse dominated), FFT/spectral (structured all-to-all communication), N-body (compute- to memory-irregular), Monte Carlo (independent samples), map (independent per-element), reduce (associativity, contention, tree structure), scan/prefix-sum (parallelizable but dependency-shaped), sort (movement, branches, communication), join (hashing, skew, repartition), filter/projection/aggregation (scan-shaped, bandwidth-sensitive), graph traversal (irregular, pointer-heavy, load-imbalanced), dynamic programming (dependency graph, table layout), search/backtracking (irregular control flow, pruning), compression/parsing (branch-heavy, input-distribution-sensitive), crypto/hashing (compute-heavy, specialized instructions), ML tensor work (dense kernels, attention, KV cache, all-reduce, by phase).

**Discriminating question:** *is this a scan, join, sort, reduce, traversal, stencil, dense kernel, parser, search — and is its logical structure regular or input-dependent?* Knowing the motif tells you which known implementations and which of the remaining lenses to weight.

### Lens 3 — Dependency and parallel structure: how do the pieces depend on each other?

Classifies how units of work relate, which decides whether parallel hardware can help at all and what kind.

Categories: serial (each step needs the last; parallel hardware cannot help until the algorithm changes), embarrassingly parallel (logically independent tasks), data parallel (same op over many items, SIMD/GPU/partition-friendly), task parallel (different concurrent tasks), pipeline parallel (stages; throughput capped by the slowest stage, latency is the sum plus queueing), divide-and-conquer (critical path and merge cost), barrier-synchronized (slowest worker controls progress), reduction-heavy (converges into shared aggregation), shuffle-heavy (repartition; network, serialization, skew, spill dominate), coordination-heavy (locks, transactions, consensus, quorum, global metadata), straggler-sensitive (slowest shard sets completion time).

The quantitative vocabulary that makes "parallel" precise:

- **Work** = total computation. **Span** (critical path) = longest dependency chain. **Available parallelism** = work / span. If span is large, more cores cannot help no matter how much work there is.
- **Strong scaling** = fixed problem, more resources. **Weak scaling** = problem grows with resources.
- **Amdahl's limit:** the serial fraction caps strong scaling. If 5% is serial, max speedup is 20x however many cores you add.
- **Gustafson's effect:** larger problems can expose more parallel work, so weak scaling can stay near-linear where strong scaling stalls. Both are true; they answer different questions (fixed work vs growing work).

**Discriminating question:** *what is independent, what is serial, where are the barriers, reductions, shuffles, and coordination points, and what is the critical path?* This lens picks between single-node optimization, multithreading, GPU, distribution, and algorithm redesign (Lever 5 in `../design-and-lifecycle/design-for-performance.md`).

### Lens 4 — Data movement and locality: where are the bytes and do accesses cooperate with the hierarchy?

Modern performance is usually dominated by moving data, not computing on it (an arithmetic op is ~1 cycle, a DRAM load ~300). This lens asks where bytes are, where they need to go, and whether the access pattern helps.

**Working-set level — where it fits:** registers → L1 → L2 → LLC → DRAM → local SSD → network/object storage → remote memory/another service → distributed across machines. Crossing each boundary changes the performance model. A hash table in L3 is a different workload from the same table in DRAM; a scan from local NVMe differs from the same logical scan over object storage.

**Access pattern:** sequential streaming (best case for prefetchers, disks, vectorized execution), strided (good if small and predictable), random (latency-bound unless enough requests overlap), pointer chasing (worst case: each next address depends on the previous load), gather/scatter (limited by memory-level parallelism), blocked/tiled (reuse while cache-resident), coalesced vs uncoalesced GPU access.

**Locality vocabulary:** temporal locality (reuse soon), spatial locality (nearby bytes on the same line/page), cache-line utilization (fraction of fetched bytes actually used), reuse distance, prefetchability, TLB reach, NUMA locality.

**Latency hiding via Little's Law.** Some work is slow not for lack of bandwidth but because each access has high latency. The fix is keeping enough independent work in flight that completions arrive continuously:

```text
request_throughput = concurrency / latency
byte_throughput    = concurrency × bytes_per_request / latency
required concurrency = target_byte_throughput × latency / bytes_per_request
```

(Name the throughput's units: in requests/sec, `concurrency = request_throughput × latency`; the sizing form below is in bytes/sec, so divide by `bytes_per_request`. Matches `../design-and-lifecycle/latency-hiding.md`.)

S3 range reads hide 50 ms GET latency by keeping many GETs outstanding; CPUs hide cache-miss latency with out-of-order execution and MLP; GPUs hide it with resident warps. This works only when future work is knowable early (sequential scans, chunked files, batched lookups, independent shards). True pointer chasing and coordination-dependent RPC chains cannot be hidden this way, because the next address is not known in time. The engineering pattern is a producer-consumer pipeline with bounded, byte-sized queues and backpressure (full treatment: Lever 4 in `../design-and-lifecycle/design-for-performance.md`).

**Communication pattern (parallel/distributed):** none, nearest-neighbor, broadcast, fanout/fanin, gather, scatter, reduce, all-reduce, all-to-all, shuffle, quorum, consensus, gossip, pub/sub, request/response chain. This is often more predictive than the algorithm name: "LLM inference" can mean compute-heavy prefill, bandwidth-bound decode, KV-cache pressure, or distributed tensor communication.

**Discriminating question:** *what bytes move, where is the working set, is access sequential / strided / random / pointer-chasing, is reuse high or low, and are we moving bytes we could avoid?*

### Lens 5 — Resource and bottleneck diagnosis: what is actually binding?

The only lens that must be measurement-driven, and the most directly actionable. The first four describe the workload's shape; this one names the limit observed *now, on this machine, under this load*. Because it is the live-diagnosis lens, its full treatment lives in `bound-types.md` (defining symptom and confirming signal per bound class) and the measurement procedure in `../diagnose/index.md`. The classes, briefly:

compute-throughput bound, memory-bandwidth bound, memory-latency bound, cache-capacity/TLB bound, branch/speculation bound, frontend bound, core-execution bound (ports, dependency chains, divides), synchronization bound (locks, atomics, barriers, false sharing), kernel/syscall bound, storage bound, network bound, coordination bound (agreement, ordering, global metadata), tail-latency bound (GC, page faults, cold caches, lock convoys, queueing, retries, stragglers, noisy neighbors).

**Discriminating question:** *what resource is saturated, where are cycles going, where are queues forming, what does the latency distribution show, and what improves when you add CPU / bandwidth / network / parallelism?* The answer is a sentence with the resource and the pipeline stage named, not the word "CPU-bound."

---

## Imprecise and misleading terms

These are useful shorthand and bad diagnoses. Each hides several distinct causes with opposite fixes. When one shows up in a bug report or a design doc, replace it with the precise version before acting.

| Term | What it hides | Say instead |
|---|---|---|
| **CPU-bound** | "not obviously blocked on disk/network" — could be arithmetic, memory stalls, branch misses, frontend starvation, lock spinning, GC, interpreter/allocator overhead, kernel time | which CPU-side resource or pipeline stage is limiting (`bound-types.md`) |
| **Compute-bound** | "cores busy" vs "doing useful arithmetic" — a core can retire little while stalled on memory or speculation | distinguish retiring useful work from stalled cycles (top-down) |
| **Memory-bound** | DRAM bandwidth vs DRAM latency vs cache-capacity vs cache-conflict vs TLB vs NUMA vs allocator vs GC vs paging | name the hierarchy level and whether it's bandwidth, latency, capacity, translation, or locality |
| **I/O-bound** | disk bandwidth vs random IOPS vs fsync latency vs object-store request overhead vs network bandwidth vs RTT vs serialization | name the device, access pattern, and limiting metric |
| **Embarrassingly parallel** | tasks don't *communicate* — but may still be capped by input reads, output writes, shared storage bandwidth, scheduling, startup, hot partitions, stragglers, final aggregation | call it dependency-free, then separately analyze shared resources |
| **Scalable** | meaningless without dimension, metric, and regime | "throughput scales linearly to 32 workers, then memory bandwidth saturates" (see below) |
| **Real-time** | "fast" — it means deadline-constrained | a slower predictable system is real-time; a fast one with unbounded p999 is not |
| **Streaming** | unbounded event processing vs incremental bounded vs sequential access vs low-latency push vs media | specify boundedness, latency objective, state model, access pattern |
| **Batch** | offline vs bounded vs scheduled vs latency-tolerant vs non-interactive (microbatch blurs it) | specify data boundedness, when results are needed, periodic vs continuous |
| **OLTP / OLAP** | too coarse for mixed transaction + analytics + search + vector + streaming + inference | describe the operation mix and dominant operators |
| **Workload** | arrival process vs operation mix vs data distribution vs input size vs concurrency vs benchmark vs trace vs kernel | state which meaning is intended |

**"Scalable" needs three parts to mean anything:** (1) the *scaling input* — offered load, cores, nodes, data size, working set, tenants, regions; (2) the *measured output* that must stay acceptable — throughput, p50, p99, cost-per-unit, error rate, recovery time; (3) the *regime* — linear, near the knee, saturated, or collapsing. Say "p99 stays under 200 ms until 8k RPS, then queueing begins," never "it scales."

---

## When each lens earns its keep

No classification is universally best; pick by purpose, but the final answer combines all five.

| Purpose | Lead lens |
|---|---|
| Teaching / recognizing patterns | Algorithmic motif (2) |
| Choosing an algorithm | Motif + dependency + data movement (2, 3, 4) |
| Choosing hardware | Data movement + dependency (4, 3) — arithmetic intensity, communication |
| Parallelizing | Dependency + communication (3, 4) |
| Database / query tuning | Motif at operator level + data movement (2, 4) |
| Distributed-system design | Workload contract + dependency (1, 3) — state, coordination, topology |
| Low-level optimization | Resource/bottleneck (5) |
| Production diagnosis | Workload contract + bottleneck (1, 5) — queueing, saturation, tail |
| Capacity planning | Workload contract + bottleneck (1, 5) — arrival process, utilization |

Lenses 1–4 are mostly knowable from the design and the code (use them at design time and to *orient* before measuring). Lens 5 must be measured (it is the *locate* step). When the lenses disagree about where the limit is, lens 5 wins, because it is the only one reading the actual machine under the actual load.

---

## Worked examples

The point of a multi-lens classification is the combined sentence. Three:

**Fanout request path.** *Latency-sensitive, fanout-heavy request path whose dominant operation is remote reads (1: p99-contract; 2: gather; 3: fanout/fanin); dependency-light locally but tail-latency-bound by downstream p99s and retry amplification (4: request/response chain; 5: tail-bound).* Intervention space: reduce fanout, hedge carefully, cap queues, cache remote data — not CPU work.

**Analytics scan.** *Batch, scan-shaped, data-parallel Parquet workload with cheap predicates (1: throughput; 2: filter/projection; 3: data-parallel/dependency-free); currently object-storage-throughput-bound and sensitive to row-group layout, projection, and request concurrency (4: sequential streaming from object store; 5: storage-bound).* Intervention: project fewer columns, raise GET concurrency to the Little's-Law target, fix row-group layout — adding cores does nothing.

**Graph traversal.** *Irregular graph traversal with high pointer chasing and poor locality (2: traversal; 3: abundant theoretical parallelism; 4: pointer-chasing, low reuse); memory-latency-bound and load-imbalanced in practice (5: latency-bound).* Intervention: replace pointer structures with arrays, batch independent lookups, rebalance — more bandwidth won't help a latency bound.

Each sentence names the contract, the motif, the dependency shape, the data movement, and the measured bottleneck, and each points at a different fix. That is the whole job of this leaf: produce that sentence so the rest of the loop targets the binding constraint.

---

## Where next

| When you… | Go to |
|---|---|
| have a workload classified, ready to find the live limit | `../diagnose/index.md` |
| need the defining symptom + confirming signal per bound class | `bound-types.md` |
| are designing for the contract before any slowness exists | `../design-and-lifecycle/design-for-performance.md` |
| need the numbers for back-of-envelope sizing | `latency-numbers.md` |
| are unsure which stack layer to chase | `software-stack.md` |
