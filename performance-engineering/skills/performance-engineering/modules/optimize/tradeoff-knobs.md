# Tuning knobs & tradeoff patterns

**Status:** READY (drop-in)
**Loaded when:** tuning configuration knobs, or weighing a performance tradeoff.

This is the knob branch of the **fix** step in the SKILL.md loop (target → measure → locate → fix → prove → defend). You arrive from `index.md` having decided the change is a *configuration* change ("set parameter X from A to B"), not a structural one ("stop doing X" / "change the shape of X" — those route to `interventions.md`). You leave with a knob set to a value you can defend, a named expected win, a named expected cost, and a rollback condition.

The governing rule: **a knob is rarely a pure improvement.** It moves pressure from one resource, percentile, failure mode, or workload shape to another. Bigger batches buy throughput and cost latency. A smaller cache saves memory and costs hit rate. A safer fsync cadence costs write throughput. The job is not to memorize "right" values; it is to name *both sides* of the tradeoff each knob encodes. If you cannot name both sides, you do not understand the knob yet.

---

## Tuning a knob: the procedure

Run these before turning anything. Each step produces a written fact; the set of facts is the tuning note you defend later.

### 0. Confirm the bottleneck makes this knob relevant
You should be here from `../diagnose/index.md` with a named dominant bottleneck, not a hunch. A knob that helps the bound you measured is worth tuning; a knob chosen by folklore is noise. If you have not located the bottleneck, go back; tuning before locating buys nothing.

### 1. Identify the load regime
A knob that helps in the linear region can be irrelevant at saturation and harmful during collapse (the regions are in `../diagnose/index.md`, the saturation curve). Increasing queue depth smooths bursts *before* the knee; past saturation it only hides overload and worsens p99. Increasing retries rescues rare transient failures; during collapse it amplifies load and cuts throughput. Name the region first.

### 2. Distinguish a load problem from an architecture problem
If all relevant resources are busy and adding capacity helps, a capacity/admission/efficiency knob is in scope. If requests queue while capacity sits idle, no knob helps; the real fix is removing serialization, contention, imbalance, or coordination, which is an intervention (`interventions.md`), not a knob.

### 3. Write down the tradeoff before turning the knob
Six facts. If you cannot fill all six, stop.

1. **Workload shape.** Latency-sensitive, throughput-oriented, batch, interactive, random-access, streaming, read-heavy, write-heavy, or coordination-heavy?
2. **Current bottleneck.** Which measurement says this knob is relevant?
3. **Expected win.** Which metric should improve?
4. **Expected cost.** Which metric might worsen, or which headroom gets consumed?
5. **Safety bound.** What prevents runaway memory, retries, cost, or queueing? (See "bound everything that can grow," below.)
6. **Rollback condition.** Which observation means the tuning was wrong?

### 4. Change one knob, then re-measure
Tuning moves the bottleneck. Raise I/O concurrency and the limit may shift from request latency to bandwidth, then to decompression CPU, then to memory bandwidth. That is success, not failure, but it means a single change invalidates the prior measurement. Change one thing, re-run the loop, re-locate the new dominant bound. The good tuning note reads:

```text
We changed X from A to B because workload shape W is dominated by bottleneck Y.
We expect metric M to improve and metric N to get worse or consume more headroom.
We will keep the change only if production-like measurement confirms that tradeoff.
```

### 5. Keep it only if production-like measurement confirms the tradeoff
A knob proved on a synthetic or closed-loop benchmark is not proved. Verify against the objective in the real load model (`../measure/verify.md`), and do not let benchmark noise pass for a win (`../measure/measurement-integrity.md`).

---

## Principles behind the knobs

- **A knob usually favors a workload shape.** Small batches favor latency; large favor throughput. Small blocks favor random access; large favor streaming. More concurrency favors latency hiding; less favors memory, fairness, and stability. Do not ask "is bigger better?" Ask "bigger is better for *which* workload?"
- **Defaults are policies, not truths.** They optimize for safety, broad compatibility, and moderate resource use. They are often wrong for extreme workloads: high-throughput scans, low-latency services, huge working sets, GPU pipelines.
- **Bound everything that can grow.** Queues, buffers, retries, caches, connection pools, thread pools, logs, and metric cardinality all need a cap. Unbounded systems fail by turning a transient mismatch into memory exhaustion, a retry storm, or a cost explosion.
- **Tune against the objective, not the average.** For services p99 may matter more than the mean; for batch, total cost or wall-clock; for real-time, deadline misses over throughput.
- **Prefer removing work over making waste faster.** The largest wins come from the highest layer that can avoid work entirely. Tune as high as you can; observe as low as you must. This is the layer rule below, and the spine of `index.md`.

---

## Where to tune vs where to observe (the layer rule)

Tuning is most effective closest to where work is created; for application-driven workloads that is usually the application. Observation is best from lower layers, where the cost becomes physically visible (CPU profiles, syscall counts, block-device latency, retransmits, execution plans, lock waits, cache-miss counters). A slow query is often *caused* by application behavior but *understood* through database and OS measurements.

```text
Tune where work can be eliminated or reshaped.
Observe wherever the cost becomes visible.
```

| Layer | What tuning can eliminate or reduce | Typical win shape | Common tradeoff |
|---|---|---|---|
| **Product / workload** | features, requests, freshness/consistency requirements, data retained | enormous; the work disappears | requires product/business decision |
| **Application** | algorithms, queries, RPCs, serialization, allocations, duplicate work, request batching | often the largest engineering win | requires code change and correctness testing |
| **Query / database** | scans, joins, locks, indexes, materialization, transaction scope | large when data access is the bottleneck | storage, write amplification, freshness, migration cost |
| **Runtime** | GC pressure, allocation, thread scheduling, async behavior, JIT behavior | medium-large when runtime overhead is visible | memory footprint, complexity, pause behavior |
| **Syscall / I/O API** | syscall count, synchronous waits, copying, tiny reads/writes | medium when boundary crossing or blocking dominates | more complex flow control and error handling |
| **Filesystem** | record size, journaling, cache behavior, readahead, metadata overhead | workload-specific; large for I/O-heavy systems | may help scans while hurting random I/O, or vice versa |
| **Storage device** | queue depth, RAID layout, disk type, device cache, IOPS/bandwidth limits | percentage wins unless storage is the dominant bottleneck | cost, durability semantics, operational complexity |
| **Network** | buffer sizes, batching, compression, connection reuse, routing, placement | large for chatty or bandwidth-heavy systems | memory, CPU, locality, fairness, cross-zone cost |
| **Kernel / hardware** | scheduler, NUMA placement, huge pages, interrupts, CPU frequency, kernel bypass | important near hardware limits | portability, complexity, isolation, debuggability |

Low-level tuning is essential when the measured bottleneck is low-level. The warning is about leverage: if a higher layer can avoid the work, that usually beats optimizing the lower layer that executes it. Removing an unnecessary query beats tuning the buffer cache; returning fewer columns beats bigger network buffers; an indexed lookup beats faster disks; reducing fanout beats tuning downstream pools.

Drop to a lower layer only when one of these holds: the higher layer already does the necessary minimum; the workload contract forbids changing the higher-level behavior; the measured bottleneck genuinely lives low; the low change is simpler, safer, or more reversible than the app change; or the same low change benefits many workloads at once. Avoid low-level tuning that only makes waste faster: 100 columns read to use 3 is a projection problem, not a disk problem; 20 needless serial RPCs is a request-shape problem, not a TCP-buffer problem; the same data scanned 50 times is a scan-sharing problem, not a worker-count problem.

---

## The knob tiers

Each row reads the same way: what the **smaller** setting favors, what the **larger** favors, what to **watch for**, and what to **measure** to know which side you landed on.

### Tier 1: Universal knobs

These appear in almost every system.

| Knob | Smaller / lower favors | Larger / higher favors | Watch for | Measure |
|---|---|---|---|---|
| **Batch size** | lower latency, faster first result, lower memory | higher throughput, better amortization of fixed overhead | head-of-line blocking, bursty memory, worse p99 | throughput, p50/p99, memory per worker |
| **Chunk / block / record size** | random I/O, selective reads, cache efficiency | sequential scans, compression, fewer metadata ops | wasted reads for point lookups; too many requests if too small | bytes read per useful byte, IOPS, scan rate, hit rate |
| **Buffer size** | lower memory per connection/task, more scalable fanout | higher per-flow throughput, fewer stalls | per-connection memory explosion, longer queueing | memory per connection, throughput, retransmits/stalls |
| **Queue depth** | lower memory, lower waiting time, less tail amplification | latency hiding, smoother producer/consumer mismatch | OOM, stale queued work, hidden overload | queue length, age of oldest item, drops, p99 |
| **In-flight requests** | lower memory, less downstream pressure | higher bandwidth, latency hiding | thundering herd, retries, downstream saturation | request rate, concurrency, error rate, saturation, p99 |
| **Worker / thread count** | less contention, less memory, less scheduling overhead | more parallelism, better CPU/I/O utilization | lock contention, cache thrash, context switches, bandwidth saturation | CPU utilization, run queue, context switches, scaling curve |
| **Connection pool size** | protects DBs/downstreams, lower memory | more concurrent work, better utilization | overwhelming downstream, idle connection overhead | pool wait time, active connections, downstream CPU/locks/p99 |
| **Cache size** | lower memory/cost, less eviction impact elsewhere | higher hit rate, lower backend load | stale data, memory pressure, poor eviction | hit rate, miss penalty, memory use, eviction rate |
| **Cache TTL** | freshness, correctness, faster invalidation | fewer backend calls, lower latency | stale reads, synchronized expiry storms | staleness, backend QPS, hit rate, error rate after deploys |
| **Compression level** | lower CPU, lower latency | fewer bytes, lower network/storage cost | CPU saturation, decompression amplification | CPU time, compressed size, wall time, network bytes |
| **Timeout duration** | faster failure, fewer held resources | fewer false timeouts, better success under transient slowness | premature failure or resource pileup | timeout rate, duration distribution, retry rate |
| **Retry count / budget** | less load amplification, faster fault surfacing | more resilience to transient failures | retry storms, duplicate work, tail amplification | attempts per request, downstream QPS, success-after-retry, p99 |
| **Prefetch distance** | less wasted work and cache pollution | better latency hiding | fetching unused data, memory blowup | stall time, hit rate, queue fill, wasted fetched bytes |
| **Admission limit** | stable latency, protected dependencies | more accepted work, higher peak throughput | user-visible rejection vs overload collapse | rejection rate, queue length, p99, downstream saturation |

### Tier 2: Storage and data-system knobs

When the workload moves large volumes, serves mixed read/write, or maintains durable state.

| Knob | Smaller / lower favors | Larger / higher favors | Watch for | Measure |
|---|---|---|---|---|
| **File or object size** | fine-grained skipping, faster rewrites, easy parallelism | streaming throughput, fewer requests, less metadata | small-file metadata tax; large-file rewrite cost | files per partition, request count, scan throughput, planning time |
| **File / partition count** | lower metadata overhead, simpler planning | more parallelism, selective reads, easy incremental writes | too many tiny files or too little parallelism | scheduler time, request rate, bytes skipped, task skew |
| **Filesystem block / record size** | random I/O, cache efficiency for small reads | sequential throughput, backup throughput | wasted cache and read amplification | IOPS, read amplification, hit rate, sequential bandwidth |
| **Database page size** | point lookups, less wasted cache per row | range scans, fewer page reads, better sequential | poor fit for mixed workloads | buffer-pool hit rate, rows per page, read amplification |
| **Parquet row-group size** | predicate skipping, lower memory per group | compression, scan throughput, fewer metadata ops | poor skipping if too large; request overhead if too small | row groups skipped, bytes read, scan throughput, memory per task |
| **Column chunk / page size** | fine-grained filtering and decoding | compression and sequential decode throughput | metadata overhead or wasted reads | page skips, decode CPU, bytes touched |
| **Index count** | faster writes, less storage, less maintenance | faster reads, more access paths | write amplification, planner complexity, stale unused indexes | read latency, write latency, index size, index usage |
| **Index granularity** | smaller index, lower write cost | more precise pruning and lookup | false positives vs index bloat | rows scanned after index, index memory, update cost |
| **Materialized views** | lower storage, simpler freshness | fast reads, predictable query latency | staleness, rebuild cost, invalidation complexity | query latency, refresh lag, storage overhead, rebuild duration |
| **Replication factor** | lower write cost, lower storage | availability, read locality, failover safety | write amplification, consistency lag | write latency, replica lag, read locality, failover time |
| **Consistency level / quorum size** | lower latency, higher availability under failure | stronger read/write guarantees | stale reads or reduced availability | read/write latency, stale-read rate, failed-quorum rate |
| **WAL / fsync frequency** | higher throughput, lower write latency | stronger durability, smaller data-loss window | lost acknowledged writes after crash | fsync latency, commits/sec, recovery point objective |
| **Checkpoint interval** | faster recovery, bounded replay | higher steady-state throughput | long recovery or checkpoint interference | recovery time, checkpoint duration, write stalls |
| **LSM compaction aggressiveness** | higher write throughput now | better reads, lower read amplification, space cleanup | background I/O storms, write stalls | read/write/space amplification |
| **Compaction target file size** | faster compactions, finer skipping | fewer files, better scan throughput | small-file buildup or expensive rewrites | file count, compaction backlog, planning time |
| **Local NVMe cache size** | lower cost, simpler statelessness | faster repeated reads, less remote I/O | cache invalidation, warmup time, ephemeral loss | hit rate, warmup time, remote bytes avoided |
| **Object-store request concurrency** | lower memory, lower request cost, fewer bursts | higher throughput, hides request latency | client throttling, prefix hot spots, memory pressure | in-flight GETs, bytes/sec, p99 GET latency, error/retry rate |
| **Object-store chunk size** | more parallelism, better retry granularity | better per-request efficiency, fewer requests | too many tiny range requests or poor skip granularity | request count, bytes/request, retry cost, throughput |

### Tier 3: Networking and distributed-system knobs

When work crosses process, host, zone, region, or service boundaries.

| Knob | Smaller / lower favors | Larger / higher favors | Watch for | Measure |
|---|---|---|---|---|
| **Socket send/receive buffer** | lower memory per connection | higher throughput on high-latency links | per-connection memory blowup | throughput, retransmits, memory per connection |
| **TCP / protocol window** | lower memory, faster feedback | fills long-fat pipes | bufferbloat, unfairness | bandwidth-delay-product utilization, RTT, drops |
| **Request batch size** | lower latency, finer failure isolation | higher throughput, fewer round trips | head-of-line blocking, retrying large batches | RPC rate, bytes/RPC, p99, partial-failure rate |
| **RPC fanout width** | lower downstream pressure, lower tail amplification | lower wall-clock for parallel remote work | p99 grows with dependency count | fanout count, slowest-dependency latency, error rate |
| **Hedging delay** | lower extra load | better p99 when stragglers dominate | duplicate work, overload during incidents | hedge rate, winner distribution, downstream QPS, p99 |
| **Load-balancing policy** | simplicity and even spread | locality, cache warmth, specialized routing | hot spots, unfairness, stale endpoint state | per-backend load, hit rate, queue time |
| **Shard count** | less metadata, fewer cross-shard ops | more parallelism, smaller per-shard working sets | rebalancing cost, tiny shards, cross-shard queries | per-shard load, hot-shard ratio, rebalance time |
| **Partition key granularity** | simpler queries, fewer partitions | better distribution, selective reads | hot partitions or too many partitions | skew, partition count, bytes skipped, metadata time |
| **Replica placement spread** | lower network cost, better locality | failure isolation, availability | correlated failure vs cross-zone latency/cost | cross-zone bytes, failover safety, read latency |
| **Rate limit** | backend protection, stable latency | more user-visible capacity | rejections vs overload collapse | reject rate, p99, backend saturation, error rate |
| **Circuit-breaker threshold** | faster isolation of failing dependency | fewer false opens | premature degradation or cascading failure | open rate, dependency errors, fallback success, recovery time |
| **Keepalive interval** | lower background traffic | faster dead-peer detection | connection churn or slow failure detection | dead-connection duration, keepalive traffic, reconnects |
| **Serialization format** | human readability, compatibility | compactness, speed, schema control | debuggability vs CPU/bytes | encode/decode CPU, payload size, schema error rate |
| **Compression on network payloads** | lower CPU, lower latency for small payloads | lower bandwidth and egress cost | CPU saturation, added latency on small messages | payload bytes, CPU per request, p99, egress cost |
| **Cross-region replication lag target** | lower write cost, simpler operation | better recovery point, fresher remote reads | write amplification, cross-region cost | lag, cross-region bytes, failover data loss |

### Tier 4: Runtime, OS, and hardware knobs

When CPU, the memory hierarchy, scheduler behavior, runtime pauses, or kernel boundaries dominate.

| Knob | Smaller / lower favors | Larger / higher favors | Watch for | Measure |
|---|---|---|---|---|
| **GC heap size** | lower memory footprint, sometimes shorter pauses | fewer collections, higher throughput | long pauses, memory pressure, container OOM | allocation rate, GC time %, pause distribution, RSS |
| **GC pause target** | lower tail latency | higher throughput, less collector overhead | CPU overhead, reduced allocation throughput | p99/p999, GC CPU, allocation stalls |
| **Allocator arena count** | lower memory fragmentation | less allocator lock contention | RSS growth, fragmentation | allocation latency, lock contention, RSS, fragmentation |
| **Thread stack size** | more threads in same memory | safer deep call stacks | stack overflow or wasted memory | thread count, memory per thread, stack faults |
| **Spin before sleep** | lower CPU waste | lower wakeup latency under short waits | burning cores, power, noisy-neighbor effects | idle CPU utilization, wakeup latency, lock wait |
| **CPU affinity / pinning** | scheduler flexibility, easy load balance | cache locality, lower jitter, NUMA control | imbalanced cores, operational complexity | migrations, cache misses, run queue per core, p99 |
| **NUMA interleaving** | simpler placement, balanced bandwidth | locality when access is unpredictable | remote access for localizable workloads | remote DRAM %, bandwidth per socket, latency |
| **NUMA binding** | scheduler flexibility | local memory latency, deterministic placement | imbalance, bad placement after reschedule | NUMA misses, per-socket CPU/memory, p99 |
| **Huge pages** | memory flexibility, less fragmentation risk | fewer TLB misses, better large-working-set throughput | compaction stalls, internal fragmentation | dTLB misses, page-fault latency, RSS, p99 |
| **Page-cache pressure / dirty ratio** | lower writeback stalls, safer memory headroom | higher write-buffering throughput | sudden flush storms, memory pressure | dirty bytes, writeback time, stalls, major faults |
| **Readahead size** | random access, less cache pollution | sequential scan throughput | wasted reads on random workloads | readahead hits, wasted bytes, scan bandwidth |
| **Polling vs interrupts** | lower idle CPU, power efficiency | lower latency, high packet/I/O rate | dedicated spinning cores, wasted CPU | interrupt rate, packet latency, CPU idle %, drops |
| **Kernel bypass** | OS integration, safety, simpler ops | extreme packet/storage throughput and latency | lost tooling/isolation, dedicated cores | packets/sec, syscall time, CPU/core, tail latency |
| **Async I/O depth** | lower memory, simpler flow control | higher device/network utilization | harder backpressure, bursty completions | I/O queue depth, device utilization, completion latency |
| **SIMD width / vectorization** | portability, simpler code, less downclock risk | higher arithmetic throughput | memory-bound loops do not improve; code complexity | IPC, vector utilization, bandwidth, frequency |
| **JIT warmup threshold** | faster time-to-steady-state, less profiling overhead | better-optimized hot code | cold-start latency from earlier compile work, deoptimized paths | warmup time, steady-state throughput, compile time |

### Tier 5: Operations and observability knobs

In production, where reliability, debuggability, and cost are part of performance.

| Knob | Smaller / lower favors | Larger / higher favors | Watch for | Measure |
|---|---|---|---|---|
| **Autoscaling target utilization** | headroom, lower latency, resilience | lower cost, higher utilization | paying for idle or scaling too late | CPU/memory utilization, p99, cost, scale events |
| **Autoscaling cooldown** | faster adaptation | stability, less oscillation | thrashing or slow response | scale frequency, pending work, p99 during bursts |
| **Minimum replica count** | lower baseline cost | warm capacity, failure tolerance | cold starts vs idle spend | cold-start latency, cost, failover behavior |
| **Deployment batch size** | smaller blast radius, easier rollback | faster rollout, less operational overhead | slow deploys or large incidents | rollout duration, error rate during deploy, rollback time |
| **Health-check interval** | lower overhead | faster failure detection | false positives, unnecessary restarts | detection time, check load, restart rate |
| **Health-check timeout** | faster removal of bad instances | fewer false removals during transient slowness | flapping or slow failure isolation | failed checks, false positives, user errors |
| **Log verbosity** | lower cost, less noise, less I/O | debuggability, incident forensics | missing evidence or log storms | log volume, ingestion cost, useful events per incident |
| **Metric cardinality** | TSDB stability and cost | debug precision, per-tenant visibility | cardinality explosions or blind aggregation | series count, query latency, storage cost |
| **Trace sampling rate** | lower cost and overhead | better forensics and rare-event capture | missing critical traces or too much cost | sampled traces/sec, storage, incident usefulness |
| **Tail-based sampling buffer** | lower memory and latency | better decision quality for trace retention | dropping traces before knowing they matter | buffer occupancy, late-decision drops, retained error traces |
| **Histogram bucket count** | lower storage/cardinality | more accurate percentile/SLO analysis | coarse p99 or metric bloat | bucket series count, quantile error, query cost |
| **Retention period** | lower storage cost | longer trend analysis and incident history | losing needed history or keeping expensive noise | storage cost, query use by age, compliance needs |
| **Alert threshold sensitivity** | fewer pages, less fatigue | faster detection | missed incidents or noisy alerts | page count, false positives, time to detect |
| **SLO window length** | faster feedback | stability, less noise | flappy alerts or slow burn detection | burn rate, alert duration, incident correlation |

### Tier 6: ML, GPU, and data-loader knobs

When accelerators, model quality, and input pipelines interact.

| Knob | Smaller / lower favors | Larger / higher favors | Watch for | Measure |
|---|---|---|---|---|
| **Training batch size** | generalization, lower memory, more frequent updates | GPU utilization, throughput, stable kernels | quality regression, optimizer changes, OOM | tokens/samples per sec, loss curve, memory, utilization |
| **Inference batch size** | lower latency, simpler scheduling | higher throughput, lower cost per request | p99, head-of-line blocking | p50/p99, throughput, GPU utilization, queue age |
| **Microbatch size** | pipeline responsiveness, lower activation memory | better kernel efficiency | pipeline bubbles, overhead | bubble %, step time, memory, utilization |
| **Gradient accumulation steps** | more frequent optimizer updates | larger effective batch without more memory | longer feedback loop, stale gradients | step time, convergence, memory, samples/sec |
| **Sequence / context length** | lower memory, faster inference/training | better quality for long context | quadratic attention cost, KV-cache growth | latency by length, memory/token, quality metrics |
| **Precision** | higher throughput, lower memory | numerical stability, simpler debugging | accuracy loss, overflow/underflow | throughput, memory, validation quality, numerical errors |
| **Activation checkpointing** | faster compute, simpler execution | lower memory, larger models/batches | extra recompute CPU/GPU time | memory saved, step time, utilization |
| **Data-loader worker count** | lower CPU and memory overhead | better accelerator feeding | CPU contention, duplicated memory, startup overhead | GPU idle %, loader queue, CPU utilization, RSS |
| **Data-loader prefetch batches** | lower memory | fewer accelerator stalls | memory blowup, stale shuffled data | queue fill, GPU idle %, memory, batch age |
| **Shuffle buffer size** | lower memory, faster startup | better randomness/statistical quality | poor randomness or memory pressure | sample distribution, training quality, memory |
| **Checkpoint frequency** | higher training throughput | less lost work after failure | expensive pauses or large recovery loss | checkpoint time, lost work on failure, storage bytes |
| **All-reduce bucket size** | earlier overlap with backprop, lower per-bucket latency | better bandwidth efficiency | poor overlap or delayed gradient sync | communication overlap %, step time, network utilization |
| **Tensor parallel degree** | less communication, simpler runtime | fits larger models, uses more GPUs | all-reduce/all-gather overhead | step latency, communication time, memory per GPU |
| **Pipeline parallel depth** | lower scheduling complexity | fits larger models, uses more GPUs | pipeline bubbles, complex balancing | bubble %, stage imbalance, step latency |
| **KV-cache size / retention** | lower memory, more concurrent sessions | longer context reuse, faster decoding | memory fragmentation, eviction quality | tokens/sec, memory/session, eviction rate, p99 |

---

## The seven tradeoff patterns

Most knobs above are instances of one of these. Naming the pattern is naming both sides of the knob.

| Pattern | Example knobs | The common failure |
|---|---|---|
| **Latency vs throughput** | batch size, microbatch interval, request batching, compression level, queue depth, inference batch size | optimizing throughput with large batches, then finding p99 unacceptable |
| **Memory vs speed** | cache size, prefetch buffers, queue depth, connection pools, data-loader workers, huge pages | hiding latency by storing more in memory until the system is fragile under bursts |
| **Locality vs fairness** | CPU pinning, NUMA binding, sticky load balancing, shard affinity, cache-aware routing | improving one worker's locality while creating hot spots or starving others |
| **Freshness vs load reduction** | cache TTL, materialized views, async replication, batch-ETL interval, metric scrape interval | treating stale data as a performance detail when it is a product/correctness question |
| **Durability vs write throughput** | fsync frequency, replication factor, quorum size, checkpoint interval, commit batching | improving benchmark throughput by silently growing the data that can be lost or replayed after a crash |
| **Tail latency vs resource efficiency** | autoscaling target utilization, admission limits, GC pause targets, hedged requests, overprovisioning, worker isolation | running everything near saturation, then being surprised when p99 explodes |
| **Simplicity vs peak performance** | kernel bypass, lock-free algorithms, manual SIMD, custom allocators, explicit NUMA placement, hand-rolled caches | paying permanent complexity for a bottleneck that was never measured or no longer matters |

---

## Glossary

Use these terms consistently when discussing tradeoffs.

### Measurement
| Term | Meaning |
|---|---|
| **Latency** | time for one unit of work to complete (send→response for a request; issue→first-byte or completion for an I/O) |
| **Throughput** | work per unit time: requests/sec, rows/sec, bytes/sec, tokens/sec, jobs/hour |
| **Bandwidth** | data throughput, usually bytes/sec or bits/sec; network and memory bandwidth are both throughput measures |
| **IOPS** | I/O operations per second; matters for small random I/O where op count beats bytes/sec |
| **Utilization** | fraction of a resource's capacity in use (90% CPU = busy 90% of the time) |
| **Saturation** | more work queued than can be served immediately; stronger than utilization (90%-utilized disk may be fine; a persistently queued one is saturated) |
| **Headroom** | spare capacity before saturation; low headroom means better cost efficiency but worse burst tolerance and tail |
| **p50 / p95 / p99 / p999** | percentiles; p99 = 99% of observations at or below this value, 1% worse |
| **Tail latency** | high-percentile latency; in user-facing systems p99 can matter more than the average |
| **Jitter** | variation in latency over time; low jitter is more predictable |
| **Wall-clock time** | real elapsed time, vs CPU time summed across threads |
| **CPU time** | time executing on cores; ten threads one second each ≈ ten CPU-seconds |

### Queueing and concurrency
| Term | Meaning |
|---|---|
| **Concurrency** | units of work active at the same time (in-flight requests, running threads, scheduled tasks, outstanding I/Os) |
| **Parallelism** | work actually executing simultaneously on multiple cores/devices/machines; concurrency can exist without it |
| **In-flight work** | issued but not completed; consuming capacity even if the caller waits asynchronously |
| **Queue depth** | items waiting or allowed to wait; deeper queues hide latency but raise memory and waiting time |
| **Backpressure** | slows producers when consumers/downstreams cannot keep up; bounded queues are a common mechanism |
| **Admission control** | rejecting or delaying new work before entry to prevent overload collapse |
| **Head-of-line blocking** | a slow item blocks later items that could otherwise complete quickly |
| **Little's Law** | `concurrency = throughput × latency`; for byte streams, `concurrency = target_byte_throughput × latency / bytes_per_request` |
| **Open-loop load** | requests arrive on an external schedule independent of response time; reveals overload and tail honestly |
| **Closed-loop load** | client waits for a response before sending the next; hides overload because slow responses cut offered load |

### Data movement
| Term | Meaning |
|---|---|
| **Batch** | logical work items processed together to amortize overhead; larger usually helps throughput, hurts latency |
| **Chunk / block / record / page** | a physical unit of data movement or storage; naming varies by layer |
| **Working set** | data actively touched over a time window; performance shifts sharply when it no longer fits a tier |
| **Cache hit / miss** | requested data found / not found in a faster tier |
| **Hit rate** | fraction of accesses served from cache; matters only if misses are expensive enough |
| **Eviction** | removing data to make room; a bad policy can make a cache harmful |
| **TTL** | time to live; longer TTLs cut load but raise staleness |
| **Freshness / staleness** | how up-to-date a value is / how old it may be while still served; a correctness and product requirement, not just a perf detail |
| **Prefetch / readahead** | fetching before demand / storage-level sequential prefetch; help predictable and sequential access, waste work otherwise |
| **Read amplification** | reading more physical data than the query needs (4 MB block to use 4 KB) |
| **Write amplification** | writing more physical data than the update implies (indexes, replication, compaction, copy-on-write) |
| **Metadata overhead** | cost of listing, planning, opening, stat-ing, scheduling many small objects vs processing payload bytes |
| **Locality** | how close needed data is in time, address space, topology, or layout |

### Storage and durability
| Term | Meaning |
|---|---|
| **Sequential / random I/O** | adjacent in-order access (maximizes bandwidth) / scattered access (limited by latency or IOPS) |
| **fsync** | forces buffered writes to durable storage; improves durability, can dominate write latency |
| **WAL** | write-ahead log: durable log written before applying changes; used for crash recovery |
| **Checkpoint** | durable point-in-time state that bounds how much log/work is replayed after failure |
| **Compaction** | rewriting data into a more efficient layout; common in LSM stores and columnar lakes |
| **Replication factor** | number of copies; higher improves availability and read locality, raises write and storage cost |
| **Quorum** | minimum replicas that must acknowledge; larger improves consistency/durability, raises latency, lowers availability under failure |
| **RPO / RTO** | recovery point objective (acceptable data loss) / recovery time objective (allowed recovery time) |

### Network and distributed
| Term | Meaning |
|---|---|
| **RTT** | round-trip time; the latency floor for request/response protocols |
| **Bandwidth-delay product** | data needed in flight to fill a link, `bandwidth × RTT`; windows and concurrency must be large enough on high-latency links |
| **Fanout** | one request creates many downstream requests; can cut median latency via parallelism while worsening the tail (slowest dependency dominates) |
| **Retry amplification / budget** | retries raise total load, often when already unhealthy / a cap so retries cannot overwhelm |
| **Hedged request** | a duplicate sent after a delay; first success wins; cuts tail at the cost of extra load |
| **Circuit breaker** | stops calling a failing dependency for a period, serving errors or fallbacks |
| **Rate limit** | cap on accepted request rate; protects from overload but can reject legitimate work |
| **Hot shard / partition / key** | a partition takes disproportionate traffic, capping scale despite spare aggregate capacity |
| **Cross-zone / cross-region traffic** | traffic crossing AZ/region boundaries; often slower and more expensive than local |

### Runtime and hardware
| Term | Meaning |
|---|---|
| **Context switch** | CPU switches threads/processes; too many waste CPU and harm cache locality |
| **Syscall** | user code enters the kernel; high rates dominate small operations |
| **GC pause** | collector pauses application work; even short pauses can dominate p99 |
| **Allocation rate** | how fast a program allocates; high rates create allocator and GC pressure |
| **RSS** | resident set size: physical memory currently held by a process |
| **NUMA** | non-uniform memory access; local-socket memory is faster than remote |
| **TLB** | translation lookaside buffer; misses can dominate large random working sets |
| **Huge pages** | larger pages (2 MB / 1 GB vs 4 KB on x86/Linux; Apple Silicon uses a 16 KB base page); raise TLB reach, can complicate memory management and tail |
| **Polling / interrupts** | repeatedly checking for work (low latency, burns idle CPU) / device notifies CPU (efficient idle, overhead at high rates) |
| **Kernel bypass** | avoiding normal kernel paths for extreme throughput/latency; costs complexity and lost OS services |
| **SIMD** | single instruction, multiple data; helps regular compute-heavy loops, not memory-bound ones |

### Observability
| Term | Meaning |
|---|---|
| **Metric cardinality** | distinct time series from label combinations; more improves slicing, can overload metrics systems |
| **Sampling** | keeping only some events/traces/logs; cuts cost, can hide rare failures |
| **Histogram bucket** | a boundary counting observations into ranges; more buckets improve percentile accuracy, raise volume |
| **Retention** | how long telemetry/data is kept; longer helps investigations, costs storage |
| **SLO** | service-level objective: target reliability/performance users can expect |
| **Error budget** | allowed unreliability under an SLO; converts reliability into an explicit tradeoff against release speed/risk |

---

## Pitfalls / over-engineering signals

- **Tuning before locating.** Turning a knob chosen by reputation rather than by the measured dominant bound. The knob makes a number move; that number was not the bottleneck.
- **Tuning a knob at the wrong layer.** A faster disk, bigger TCP buffer, or larger connection pool under an application doing unnecessary work. The leverage was higher up; the knob just paid for the waste. Tune as high as you can.
- **Tuning by benchmark noise.** Keeping a setting that "won" on a closed-loop or synthetic run that hid overload. Prove against the objective under the real load model (`../measure/measurement-integrity.md`).
- **Forgetting the second side.** Setting a knob for its expected win without naming or measuring its expected cost. If you only measured M, you do not know N got worse.
- **Unbounded growth.** A queue, retry budget, cache, or pool tuned up without a cap. The win shows in the benchmark; the failure shows in production as OOM, retry storm, or a cost spike.
- **Wrong regime.** A knob that helps in the linear region applied at saturation or collapse, where it only hides overload. Name the load region first.
- **Permanent complexity for a transient bottleneck.** The simplicity-vs-peak pattern. Kernel bypass, lock-free, custom allocators bought for a bound that was never measured or no longer binds.

If you cannot name both sides of the tradeoff, you do not understand the knob yet.

---

## Worked example

A batch scan feeds a GPU pipeline from object storage; `../diagnose/index.md` reports the GPU is idle a large fraction of each step, waiting on input, while CPU has slack. The candidate knob is object-store range-read concurrency. Filling in the procedure:

```text
Change:        Increase S3 range-read concurrency from 16 to 64.
Workload:      Batch scan, sequential range reads, CPU idle waiting on input (latency vs throughput; memory vs speed).
Bottleneck:    GPU idle % high; in-flight GETs far below the byte-form Little's-Law floor (concurrency = target_byte_throughput × latency / bytes_per_request), so the read path is under-filled.
Expected win:  Higher read throughput, lower GPU idle time.
Expected cost: More memory in in-flight buffers, higher request rate, possible client throttling.
Safety bound:  Queue capped by bytes (not by count), retry budget capped, per-worker memory alert.
Keep if:       GPU idle time falls AND S3 errors/retries do not rise materially.
Rollback if:   RSS or retry rate grows, or p99 GET latency worsens enough to offset the throughput gain.
```

Turn the one knob, re-measure (`../measure/verify.md`). Two outcomes worth expecting. If GPU idle drops and retries stay flat, keep it, then re-run the loop: the bottleneck has likely moved (to decompression CPU, to memory bandwidth, or to the GPU itself), and the next knob is chosen against the *new* dominant bound. If retries climb or RSS grows toward the alert, the byte-bounded queue and retry budget contain the blast radius while you roll back. Either way the tradeoff was named before the change, so the result is a decision, not a surprise.

---

## Where next

| You have… | Go to |
|---|---|
| a knob set, ready to prove the win and the cost | `../measure/verify.md` |
| a "win" that might be benchmark noise | `../measure/measurement-integrity.md` |
| realized the fix is structural, not a knob | `interventions.md` |
| not yet chosen lever vs layer | `index.md` |
| not yet located the dominant bottleneck (USE/RED, load vs architecture, load regime) | `../diagnose/index.md` |
| designing for these tradeoffs before any slowdown exists | `../design-and-lifecycle/design-for-performance.md` |
