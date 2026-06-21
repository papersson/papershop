# Performant by construction

**Status:** READY (priority)
**Loaded when:** designing a system/component for speed, before any slowdown exists.

This is the proactive counterpart to the reactive loop. Bottleneck-chasing fixes a system that
is already slow; this module is about not building the slowness in the first place. It still obeys
the gate in SKILL.md: design for the target you actually have, not for a speed nobody asked for.

## The stance: mechanical sympathy

Write code against an accurate model of the machine that runs it. The abstract machine your
language implies (sequential instructions, flat memory where every access costs the same, free
arithmetic) has not existed for decades. The real machine has a cache hierarchy where a register
is ~300x closer than DRAM (the ~1-cycle vs ~300-cycle gap below), an out-of-order core that runs
hundreds of instructions in flight, a
branch predictor, a TLB, coherence traffic between cores, and an OS underneath. Design that fights
those mechanisms is slow no matter how clean the source looks; design that cooperates with them is
fast almost by accident.

Two facts do most of the work here, and they are the through-line of this whole module:

- **An arithmetic op is ~1 cycle; a DRAM load is ~300 cycles.** Most code that looks CPU-bound is
  actually waiting on memory. So "fast by construction" is rarely about clever arithmetic tricks.
  It is about **not doing work** and **moving less data**.
- **There is no universally fast code.** Every technique below has an "except when." A layout,
  a data structure, a concurrency scheme is fast *for a workload, on a machine, with this data*.
  Cargo-culting SoA or lock-free or huge pages without that context is how you ship slow code that
  looks optimized. Design choices are hypotheses; the loop in SKILL.md is how you confirm them.

What follows are the design-time levers in priority order. The order matters: it goes from highest
leverage (decide what "fast" means, then avoid the work entirely) to lowest (make unavoidable work
cheaper). Spend your design budget top-down. The cookbook rule is *tune as high as you can*:
removing a query beats tuning the database that runs it; returning fewer columns beats a faster
disk; doing one pass beats caching repeated passes.

---

## Lever 1 — Define the workload contract first

You cannot design for "fast" until you have decided what fast means here. The same component is a
different engineering problem depending on its contract, and the contract decides which of the
later levers even apply. Pin these down before drawing any boxes (full lens set:
`../orient/work-taxonomy.md`):

- **Latency-sensitive or throughput-oriented?** A checkout request optimizes response time; a
  nightly ETL optimizes total work per dollar. These pull in opposite directions. Large batches
  help throughput and hurt latency; the same knob is right for one and wrong for the other.
- **Which percentile is the contract?** "Fast" for a user-facing path is almost never the mean.
  A service with a 2 ms mean and a 500 ms p99 is a 500 ms service with noise. Design for the tail
  you have to meet, and know that tails come from pauses, queueing, retries, and stragglers, not
  from the average instruction.
- **Open-loop or closed-loop load?** Open-loop traffic arrives on its own schedule and exposes
  overload honestly; closed-loop clients wait before sending more and hide it. Design (and later
  load-test) for the real arrival process, or your headroom is a fiction.
- **Read-heavy or write-heavy?** Read-heavy invites caching and replication. Write-heavy hits
  coordination, durability, and compaction limits that caching cannot paper over.
- **Stateful or stateless? Steady or bursty? Hot-keyed or uniform?** Stateless workers replicate
  freely; stateful ones bring placement and recovery. Bursty load needs buffering or admission
  control. A hot key collapses apparent parallelism no matter how many cores you add.

Write the contract down as one sentence before designing, e.g. *"latency-sensitive read path,
p99 < 50 ms under open-loop 8k RPS, read-heavy, uniform keys, stateless."* That sentence tells you
which levers to pull and, just as usefully, which to ignore.

Size it with arithmetic, not vibes. At design time, back-of-envelope the data volumes and the
latency floor from known numbers (`../orient/latency-numbers.md`) before committing to a shape:
how many bytes must move per request, how many round trips, what the irreducible RTT is. A design
that needs 20 serial cross-service hops at 1 ms each cannot meet a 10 ms p99, and you can know that
on a whiteboard.

## Lever 2 — Avoid work (the highest lever)

The largest wins come from work that never happens. Before making anything cheaper, ask what you
can stop doing. This lever lives in the design, not in tuning, because it is about the shape of the
system:

- **Don't read what you won't use.** Reading 100 columns to use 3 is read amplification baked into
  the schema. Project early. Store data so the common query touches a narrow slice (this is also
  why Lever 3 exists). A columnar layout that reads 3 columns moves a fraction of the bytes a
  row-store does for the same query.
- **Batch instead of chattering.** 20 serial RPCs to assemble one response is 20 round trips of
  latency stacked end to end; one batched call is one. The same applies to syscalls, small I/Os,
  and per-row database round trips. Coalesce at design time.
- **Cache / precompute what is reused.** If many requests recompute the same aggregate, compute it
  once. But caching is a freshness-vs-load tradeoff, not free speed: a TTL is a staleness budget,
  and staleness is a product decision, not a performance detail. Decide it deliberately.
- **Pick the algorithm and data structure that does less.** Asymptotics still matter; an indexed
  lookup beats a full scan, a hash join beats a nested loop on large inputs. This is the cheapest
  win there is because it is a decision, not an investment.
- **Do one pass.** Scanning the same data five times for five derived values, when one pass
  produces all five, is 5x the memory traffic for the same result.

Over-engineering signal: you are micro-optimizing a function that runs once per request while the
request makes a redundant network call. Fix the call. Effort spent making waste faster is wasted.

## Lever 3 — Lay out data for locality

Once the work is minimal, the next cost is moving its data. Memory moves in cache lines (64 bytes
on x86-64; **128 bytes on Apple Silicon / M-series**, which is the local environment this skill
foregrounds — confirm with `sysctl hw.cachelinesize`, not a hardcoded constant); the unit of
"fast" is *the fraction of each fetched line you actually use*. Layout is a design decision because
it is painful to change later.

**AoS vs SoA.** Array-of-structs stores each object's fields together; struct-of-arrays stores
each field's values together.

```c
// AoS: good when a phase touches MOST fields of each object
struct Particle { float x,y,z, vx,vy,vz, mass; uint32_t flags; };
Particle ps[N];

// SoA: good when a phase touches a NARROW subset across MANY objects
struct Particles { float x[N], y[N], z[N], vx[N], vy[N], vz[N]; /* ... */ };
```

A loop that updates position from velocity under AoS drags the whole struct through cache to touch
six floats, wasting most of every line. Under SoA the same loop reads tight stride-1 streams where
every byte pulled is used, and the hardware prefetcher sees clean patterns it can run ahead of.
The identical algorithm can run several times faster from this flip alone. **Except when** a phase
touches most fields of each object together: then AoS wins, because the "came along for the ride"
bytes are the bytes you wanted and there is one fewer array to index. Mixed reality gets hybrid
layouts (AoSoA). The right answer is the layout under which fetched bytes are used bytes, which
depends on the access pattern, which you got from Lever 1.

**Access pattern beats cleverness.** Sequential stride-1 access is the prefetcher's best case;
pointer chasing is its worst (each `node->next` is a full-latency dependent load with no stride to
predict). Same big-O, wildly different wall-clock. Prefer arrays over linked structures, flat /
open-addressed hash tables over chained ones, and B-tree-like layouts over scattered pointer trees.
Match loop order to memory order (row-major arrays: iterate the last index innermost).

**Narrow the types.** Memory-bandwidth-bound code goes faster when each element is smaller. Use
the narrowest type that is correct (int32 over int64, float over double where precision allows),
pack fields, and drop ones the hot path never reads. Fewer bytes per element is more elements per
cache line and per unit of bandwidth.

Over-engineering signal: you are hand-packing structs and switching to SoA for a path that runs a
few thousand times and is nowhere near a bandwidth or latency limit. Layout work pays off on hot,
data-heavy loops. Elsewhere it is complexity for no measurable gain.

## Lever 4 — Structure for latency hiding and parallelism

Some latency is irreducible: a DRAM miss, an SSD read, an S3 GET, a remote service call. You cannot
make a single one faster, but you can stop waiting on them one at a time. The design move is to
keep enough independent work in flight that completions arrive continuously, which converts a
latency problem into a throughput problem.

The sizing rule is Little's Law: `concurrency = throughput x latency`. To hit a target throughput
over an operation with a fixed latency, you need that many operations outstanding. A 50 ms S3 GET
at 1 GB/s of desired throughput with 8 MB objects needs roughly `1e9 x 0.05 / 8e6 ≈ 6` GETs in
flight; design the pipeline to keep that many going. The engineering pattern is a producer-consumer
pipeline with **bounded** queues and backpressure: deep enough to absorb variance, bounded by
bytes so it cannot exhaust memory. The full treatment, with the S3 case study, is in
`latency-hiding.md`.

This only works when future work is known early: sequential scans, chunked files, batched lookups,
and independent shards prefetch cleanly. **Except when** the next address or request depends on the
current result: true pointer chasing and coordination-dependent RPC chains cannot be hidden this
way, because you do not know what to prefetch. For those, the fix is back at Lever 3 (change the
structure so accesses become independent) or Lever 5 (remove the dependency).

For sustained-load and growth sizing (how many machines, where the scaling knee is, how
contention and coordination cap speedup), go to `capacity-scalability.md`.

## Lever 5 — Choose the architecture from the dependency structure

The biggest structural decision (single-thread, multi-thread, GPU, distributed) follows from how
the work depends on itself, not from fashion. Read the dependency and communication shape, then
pick the machine (lens detail: `../orient/work-taxonomy.md`):

- **Serial / dependency-bound** (each step needs the last): parallel hardware cannot help until
  the algorithm changes. Don't reach for threads; rethink the dependency or accept one core.
- **Embarrassingly parallel / data-parallel** (same op over independent items): scales across
  cores, SIMD, GPU, or nodes, limited by I/O, scheduling, and stragglers, not by the algorithm.
  This is the case GPUs and vector units want.
- **Pipeline-parallel** (work flows through stages): throughput is capped by the slowest stage;
  latency is the sum of stages plus queueing. Balance the stages.
- **Reduction / shuffle / coordination-heavy** (work must converge, repartition, or agree): the
  bottleneck moves to contention, network, and coordination. More workers can make it *slower*.
  Design to shard state, give single writers ownership, and reduce periodically rather than share
  a hot counter.

A critical caution that shapes the choice: adding cores or nodes exposes shared bottlenecks that
were invisible single-threaded. A shared counter incremented by every thread becomes the slowest
instruction in the program through cache-line bouncing; two unrelated variables on one cache line
cause false sharing that looks like a mystery slowdown. Pad to a full line to kill it, but size the
pad from the platform: 64 bytes on x86-64, 128 on Apple Silicon. Use
`std::hardware_destructive_interference_size` (or `sysctl hw.cachelinesize` at runtime) rather than
hardcoding 64, or the padding silently under-protects on M-series. "Embarrassingly parallel" means the tasks
are logically independent, not that they scale; they still contend for memory bandwidth, the LLC,
allocators, and NUMA links. Design *less sharing* (per-thread data, sharding, batching) before
designing clever sharing (lock-free). Distributed last: it adds the most capability and the most
ways to be slow, so reach for it only when one node provably cannot meet the contract.

---

## Don't cargo-cult: the contextuality rule

Every lever above is conditional. The honest framing is that a performance technique is a bet on a
specific workload and machine, and applying it blind is how systems get *more* complex and not
faster. SoA loses to AoS for object-at-a-time work. Branchless code loses to a branch the predictor
nails. Huge pages cut TLB misses and can spike tail latency. Lock-free beats a mutex under
contention and loses to it under none. More threads help until memory bandwidth saturates, then
hurt latency.

So at design time, for any technique you are about to commit to, be able to name both sides of its
tradeoff and the regime where it pays (the seven recurring tradeoff patterns and their failure
modes are in `../optimize/tradeoff-knobs.md`). If you cannot say what the technique costs and which
workload shape it favors, you do not understand the knob yet; pick the simple design and let the
loop tell you whether you need the complex one.

Over-engineering signals, in one place:
- Reaching for lock-free / custom allocators / kernel bypass / manual SIMD before any measurement
  says the simple version is the bottleneck.
- Optimizing a path that is not on the contract's critical path or hot loop.
- Adding a cache, a thread pool, or a shard before the single, simple, correct version is shown to
  miss the target.
- Permanent complexity bought for a bottleneck that was never measured or no longer matters.

The default is the simplest design that could meet the contract. Complexity is earned by a number.

---

## Worked example: a recent-events aggregate service

Contract (Lever 1): return a per-user aggregate over the last 24 h of events. Latency-sensitive,
**p99 < 50 ms** under open-loop ~8k RPS, read-heavy, keyed by user (roughly uniform), stateless.
Back-of-envelope: a hot user has ~10k events/day; at ~40 bytes each that is ~400 KB to touch per
request if computed from raw events.

Avoid work (Lever 2): most requests ask for the same few aggregates, so precompute rolling
aggregates and serve those; fall back to raw scan only on a miss. Project only the 3 fields the
aggregate needs, not the full event. One pass produces all the needed aggregates together. The TTL
on the precomputed value is set from the product's staleness tolerance (say 60 s), making the
freshness cost explicit rather than accidental.

Data layout (Lever 3): store events columnar (SoA) so a scan reads three tight streams instead of
dragging whole event rows through cache; use narrow types for the fields. The fallback scan now
moves a fraction of 400 KB and runs stride-1 where the prefetcher helps.

Latency hiding (Lever 4): on a cache miss the raw events live in object storage with ~tens-of-ms
GET latency. Issue the range reads concurrently sized by Little's Law rather than serially, behind
a byte-bounded queue, so a miss costs roughly one GET latency instead of N.

Architecture (Lever 5): the read path is data-parallel and stateless, so replicate workers freely,
partition by user so there is no shared mutable state and no hot counter. Coordination stays out of
the request path; the precompute job is a separate pipeline. Distributed only because the dataset
exceeds one node, not for its own sake.

Result: the design moves few bytes, waits on few round trips, contends on nothing in the hot path,
and meets a tail target, and every choice traces back to a clause in the contract. Whether it
actually hits p99 < 50 ms is then a measurement, not a hope: build the simple version, run the loop.

---

## Worked example: a push/streaming ingest-and-aggregation pipeline

The example above is **pull** (request/response): the client asks, the service answers. The other
common shape is **push**: a high-volume event stream arrives continuously and you must ingest it
durably and keep a running aggregate. Same levers, different bottleneck — the contract is now
write-heavy and the latency objective is *freshness of the aggregate*, not per-request response.

Contract (Lever 1): ingest ~500k events/s, durable (no loss on crash), expose per-key windowed
aggregates fresh to within a few seconds. Write-heavy, bursty (peaks 3–4x baseline), keyed by user.
The contract words "durable" and "bursty" decide the whole design.

- **Durable partitioned log (Lever 5, dependency structure).** Land events first in an append-only
  partitioned log (Kafka/Kinesis/Pulsar-shaped). The log is the durability boundary and the unit of
  parallelism: partition by the aggregation key so each consumer owns a key range and no two
  consumers touch the same aggregate (single-writer-per-partition, no shared mutable counter — the
  same anti-false-sharing principle one level up). Partition count is the scaling knob; see
  `capacity-scalability.md`.
- **Producer batching (Lever 2, avoid work + Lever 4).** Producers accumulate events and append in
  batches, not one record per RPC. This is the same "batch instead of chattering" lever: it trades a
  few ms of buffering latency for an order-of-magnitude fewer round trips and far higher write
  throughput. The batch-size/linger knob is the latency-vs-throughput tradeoff from Lever 1, named
  explicitly.
- **Admission control / backpressure under burst (Lever 4).** Push has no natural flow control: if
  producers outrun consumers the buffer grows without bound. Bound the queue by bytes and propagate
  backpressure — block or shed the producer when the log/consumer lag exceeds budget, rather than
  buffering until OOM. Under sustained overload, shed deliberately (drop, sample, or 429) instead of
  collapsing. This is the bounded-queue+backpressure pattern in `latency-hiding.md`, applied to the
  ingest path; size the bound to "a few seconds of consumer throughput," not by feel.
- **Stateful windowed aggregation (Lever 2, do one pass + incremental).** Maintain the aggregate
  incrementally: each event folds into a per-key window state in one pass, never a re-scan of the
  window. Keep the window state in a local store (in-memory with periodic checkpoints, or an
  embedded LSM like RocksDB) keyed by the partition so recovery rebuilds only that partition. Choose
  the delivery/consistency semantics deliberately — at-least-once with idempotent folds is the
  cheap, common choice; exactly-once (transactional offsets + state commit) costs throughput, so buy
  it only if double-counting actually violates the contract.

Result: writes land durably and cheaply (batched, partitioned), bursts are absorbed without
unbounded memory (bounded queue + backpressure), and the aggregate stays fresh in one incremental
pass with bounded recovery. As ever, whether it hits the freshness target under peak load is a
measurement: build the simple single-partition version, then run the loop.

---

## Design-time checklist

- [ ] Contract written as one sentence (latency/throughput, percentile, load model, read/write,
      state, distribution).
- [ ] Volumes and latency floor sized on paper from known numbers before committing to a shape.
- [ ] Every avoidable unit of work removed: no unread columns, no chatty round trips, reuse cached,
      one pass, right algorithm.
- [ ] Hot data laid out so fetched bytes are used bytes; access patterns sequential/independent
      where they can be; types as narrow as correctness allows.
- [ ] Irreducible latency hidden with bounded, sized concurrency where future work is knowable.
- [ ] Architecture chosen from the dependency structure; sharing minimized before sharing is made
      clever; distribution only when one node cannot meet the contract.
- [ ] For every non-trivial technique committed to, both sides of its tradeoff named and the
      simplest viable design kept until a number earns the complex one.

## Where to go next

- `latency-hiding.md` — the Little's Law pipeline pattern and the S3 case study (Lever 4).
- `capacity-scalability.md` — sustained-load sizing, scaling knees, contention limits (Lever 4/5).
- `../orient/work-taxonomy.md` — the five lenses for the workload contract and dependency structure.
- `../orient/latency-numbers.md` — the numbers for back-of-envelope sizing at design time.
- `../optimize/tradeoff-knobs.md` — the named tradeoff patterns behind the contextuality rule.
