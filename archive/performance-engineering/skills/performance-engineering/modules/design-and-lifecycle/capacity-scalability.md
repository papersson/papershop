# Capacity & scalability (Little's Law, USL)

**Status:** READY
**Loaded when:** planning for growth, or answering "will it scale / how far?"

This leaf sizes a system for sustained load and predicts how far it goes before it stops getting faster. It is the design-and-lifecycle counterpart to the reactive loop: instead of locating a bottleneck that already hurts (`../diagnose/index.md`), you model the curve in advance and find the knee on paper. The core rule: a scalability claim is meaningless until you name the **scaling input**, the **measured output**, and the **regime**. "It scales" is not an answer; "throughput scales linearly to 32 workers, then memory bandwidth saturates and p99 breaks the SLO at 8k RPS" is.

Two laws do most of the work. **Little's Law** sizes capacity (how much concurrency a throughput-and-latency target demands). The **Universal Scalability Law (USL)** predicts the shape of the resource-scaling curve and, critically, the point where adding resources makes things *slower*. Everything else is reading curves and not lying to yourself with closed-loop load tests.

---

## Procedure: answer "will it scale / how far?"

Run these in order. Each step yields a number you can defend.

### 1. Name the scaling dimension and the metric
Never reason about "scaling" in the abstract. State all three parts:

- **Scaling input** — what increases: offered load, cores/threads, instances/nodes, disks, partitions, replicas, data size, tenants, geography, or operational surface. These have *different* curves; a system that scales on load can fail to scale on data.
- **Measured output** — what must stay acceptable: throughput, p50, p99, cost per unit, error rate, recovery time.
- **Regime** — where on the curve you operate: linear, near the knee, saturated, or collapsed.

If the question is "can we handle 3x traffic?" the input is offered load and the output is p99 under SLO. If it is "should we add nodes?" the input is resources and the output is throughput per dollar. Pick the pair that matches the actual decision before computing anything.

### 2. Establish the per-unit numbers
Get service time and the irreducible floor from measurement or back-of-envelope. You need: mean service time per request at low load, the latency floor (RTT, fixed round trips), bytes moved per request, and the serial fraction of the work (the part that cannot run concurrently). These feed every model below. Without them you are curve-fitting noise.

### 3. Size concurrency with Little's Law
For a capacity target, `concurrency L = throughput λ × latency W`. This is the floor on how many requests must be in flight, how many threads/connections/permits you need, and how deep a pipeline must run. See the Little's Law section for the three rearrangements and the saturation trap.

### 4. Predict the resource-scaling curve with the USL
If the question is how far adding workers/cores/nodes helps, fit the USL to a handful of measured points and read off the peak. The USL gives you the throughput maximum and the regime *before* you provision. A pure Amdahl model only flattens; the USL can predict that you go backward. See the USL section.

### 5. Locate the knee, not the maximum
The useful operating limit is the knee, not the theoretical peak. Provision to run *before* the knee, because latency degrades nonlinearly as utilization approaches saturation (queueing delay grows like `1/(1-ρ)`). The capacity limit you ship against is "the load at which p99 violates the objective," which arrives earlier than "the load at which throughput maxes out."

### 6. Validate with open-loop load
Confirm the model with a load generator that holds a **constant arrival rate**, not one that waits for responses. A closed-loop client throttles itself when the system slows, hides the tail (coordinated omission), and reports a capacity that does not exist under real traffic. See the load-generation section.

### 7. State the claim with its constraint
Write the result as one sentence naming input, output, regime, and the binding constraint, e.g. *"throughput scales near-linearly to 24 cores (α≈0.03, β≈0.0008), peaks at ~35 cores, and the next limit is DRAM bandwidth; p99 holds under SLO to 8k RPS open-loop."* That sentence is the deliverable, and it tells the next engineer exactly what to re-measure.

---

## The scalability curve: four regions

As the scaling input rises (offered load or added resources), throughput moves through four regions. Reading which one you are in *is* the capacity diagnosis.

| Region | What happens | Meaning | What to do |
|---|---|---|---|
| **Linear** | throughput tracks the input ~1:1; latency flat | spare capacity, no shared limit binding | safe; you have headroom |
| **Knee** | throughput growth bends below linear; latency/queueing climb faster | contention or coordination has started to bite | this is your operating ceiling; provision below it |
| **Saturation** | a resource hits effective capacity; extra input mostly waits | at or past the safe point | shed load, add capacity, or remove the bottleneck |
| **Collapse / retrograde** | throughput *falls* as input rises | overhead (retries, context switches, lock contention, coherence traffic, GC, timeout churn) now exceeds useful work | back off; this is an architecture problem, not a load problem |

Two facts to internalize. First, **latency degrades before throughput plateaus**, so the knee in the latency curve precedes the knee in the throughput curve. Second, **"CPU is only 70%" is not a safety signal**: the saturated resource may be a lock, a thread pool, a connection pool, a hot shard, a disk queue, or a downstream p99 rather than aggregate CPU. Measure the whole curve together: offered load vs completed throughput vs latency percentiles vs queue depth vs error/retry rate. One point tells you nothing about the shape.

---

## Types of scalability

A system scales on one axis and not another. Name the axis explicitly.

| Type | Question it answers |
|---|---|
| **Load** | what happens as offered traffic increases? |
| **Resource** | what happens as you add cores, threads, nodes, disks, GPUs, partitions, replicas? |
| **Data** | what happens as dataset, index, or working set grows? |
| **Tenant** | what happens as users, tenants, keys, shards, connections, topics grow? |
| **Geographic** | what happens as clients, replicas, data spread across zones/regions? |
| **Operational** | can humans still deploy, debug, secure, and cost-manage it as it grows? |

A complete claim names: scaling input · measured output · regime · the constraint that limits the next step.

---

## Strong vs weak scaling, Amdahl and Gustafson

Two ways to add resources, two different questions.

- **Strong scaling:** fixed problem size, more workers. Measures latency-to-solution. Governed by **Amdahl's Law**: if a fraction `s` of the work is serial, speedup with `N` workers is `1 / (s + (1-s)/N)`, which is capped at `1/s` no matter how many workers you add. A workload that is 5% serial cannot exceed 20x however many cores you throw at it. Strong scaling hits a wall.
- **Weak scaling:** grow the problem with the workers (fixed work *per* worker). Measures whether you can solve bigger problems in the same time. Governed by the **Gustafson effect**: larger problems often expose more parallel work, so the serial fraction shrinks relative to total work and scaled speedup grows roughly linearly, `N - s(N-1)`. Many systems that scale terribly under Amdahl scale fine under Gustafson because in practice you grow the dataset, not just the machine.

Which one you are doing decides whether the news is good. "Can I make this one query faster with more cores?" is strong scaling (Amdahl, pessimistic). "Can I serve 10x the data at the same latency with 10x the nodes?" is weak scaling (Gustafson, often optimistic). Stating which question you are answering prevents the common error of quoting an Amdahl wall to dismiss a system that will actually be deployed in the Gustafson regime.

Useful vocabulary: **work** (total computation), **span / critical path** (longest dependency chain), **available parallelism** = work / span. The critical path is the hard floor; no amount of hardware beats it.

---

## The Universal Scalability Law

Amdahl only flattens. Real systems often **go backward**: add nodes and total throughput drops. Amdahl cannot express that, the USL can, because it adds a second penalty term. Neil Gunther's USL models relative capacity (speedup) as a function of `N` (workers, cores, nodes, or concurrency):

```text
            N
C(N) = ───────────────────────────
        1 + α(N − 1) + β·N(N − 1)
```

- **α — contention** (serialization). The fraction of work that must serialize on a shared resource: a lock, a queue, the serial section. This is the Amdahl term. With α alone the curve saturates at `1/α` and flattens.
- **β — coherency** (crosstalk). The cost of keeping workers *consistent with each other*: cache-line coherence traffic, cross-node gossip, distributed-lock chatter, the all-to-all of N workers each having to agree. This term grows as `N²`, so past a point it *dominates* and pulls the curve down. **β is what makes scaling retrograde.**

Two limits worth knowing:

- **β = 0 reduces the USL to Amdahl's Law.** Coherency is the only thing the USL adds; with no crosstalk you are back to a curve that merely plateaus.
- **The throughput peak is at** `N* = sqrt((1 − α) / β)`. Beyond `N*` more workers make the system *slower*. If β is tiny but nonzero, `N*` is large but finite, so "it scaled linearly in our test" can still hide a wall a few multiples past where you stopped measuring.

**How to use it:** measure throughput at several values of `N` (e.g. 1, 2, 4, 8, 16, 32 workers under the same per-worker load), normalize to C(N) = throughput(N)/throughput(1), and fit α and β by regression (Gunther's books give the procedure; most fits are a quadratic regression on `N/C − 1`). The fitted α and β then **predict the peak you have not yet provisioned**. This is the payoff: a six-point test predicts whether buying 4x the nodes helps, does nothing, or backfires, before you spend the money. A fit with non-negligible β is a design warning, find and cut the coherency source (shard state, give single writers ownership, batch reductions) before scaling out.

---

## Little's Law for capacity

A queueing identity that holds for any stable system, independent of distribution: the average number of items in a system equals arrival rate times time spent.

```text
L = λ · W           items in system = throughput × latency
```

Three rearrangements, three sizing questions:

- **Concurrency you need:** `L = λ · W`. To sustain `λ` = 8000 req/s at `W` = 20 ms mean latency, you must keep `L = 160` requests in flight, so thread pools, connection pools, and permit counts below 160 cap your throughput regardless of CPU headroom.
- **Throughput you can get:** `λ = L / W`. With `L` = 64 outstanding I/Os against a store at `W` = 5 ms each, ceiling is `λ` = 12 800 IOPS. Want more? Raise concurrency or cut latency; nothing else moves it.
- **Latency implied:** `W = L / λ`. If the queue holds `L` = 500 items and you complete `λ` = 1000/s, items spend `W` = 0.5 s inside. A growing `L` at fixed `λ` *is* rising latency.

The same law sizes a latency-hiding pipeline: required in-flight depth = target throughput × per-op latency / per-op size. That use (overlapping high-latency operations so completions arrive continuously) is the subject of `latency-hiding.md`; here the concern is steady-state capacity.

**The saturation trap:** Little's Law is an *identity*, not a license to drive utilization to 1. As utilization `ρ` → 1, latency `W` blows up nonlinearly (`W ∝ 1/(1−ρ)` for simple queues), so `L` explodes and the system enters the knee. The law tells you the concurrency a target *demands*; it does not promise the system stays stable there. Size for the knee, leave headroom.

---

## Load generation: open-loop and coordinated omission

Your capacity model is a hypothesis. Validate it with load that mimics the real arrival process, which for most services is **open-loop**: requests arrive on their own schedule regardless of whether the system has kept up. A **closed-loop** generator (and a closed-loop client) waits for each response before sending the next, so when the system slows it *automatically sends less*. That feedback hides overload and produces **coordinated omission**: the slow requests that should dominate your tail never get issued, the long stalls go unsampled, and the reported p99 is a fiction. A system measured closed-loop can report a healthy p99 while being unusable under real open-loop traffic.

Rules for trustworthy load tests:

- **Hold a constant arrival rate**, decoupled from response completion. The generator must keep issuing at the target rate even while responses are slow, and record latency from *intended* send time, not from when it actually got to send.
- **Run long enough** to catch periodic events. A 5-minute run misses a GC or compaction that fires every 10 minutes; the tail you care about may only appear in a longer window.
- **Use realistic data and contention.** Cold caches, production key distribution (including hot keys), realistic payload sizes. Microbenchmarks are upper bounds on production wins.
- **Plot the curve, not a point.** Sweep offered load and record completed throughput, p50/p99/max, queue depth, and error/retry rate together, so you can see the knee.

Tooling: prefer generators built for the open-loop / constant-throughput model with corrected latency recording. `wrk2` (constant throughput, coordinated-omission-corrected), `vegeta` (constant request rate, good for HTTP), and `k6` (scriptable, supports arrival-rate executors) all do this; classic `ab` does not and will lie about the tail. Whichever tool, confirm it records latency against intended schedule.

---

## Pitfalls and over-engineering signals

- **Claiming "scalable" without the three parts.** No dimension, no metric, no regime means no claim. Reject it from yourself and others.
- **Fitting a single point.** One throughput number cannot tell linear from knee from collapse. You need the curve.
- **Reading an Amdahl wall as fatal when you will deploy in Gustafson.** If the dataset grows with the machine, the serial fraction shrinks relative to total work; quoting strong-scaling pessimism is the wrong model.
- **Provisioning to the theoretical peak.** The peak is past the knee, where latency is already broken. Ship below the knee.
- **Trusting a closed-loop test.** The most common way to certify a capacity that evaporates in production. If you cannot rule out coordinated omission, you do not have a tail number.
- **Driving utilization to 100% "because there's headroom in CPU."** The binding resource is rarely aggregate CPU; queueing latency explodes before CPU saturates.
- **Modeling β when β is zero.** If a clean fit gives β ≈ 0, you have an Amdahl system; do not invent coherency complexity. Conversely, ignoring a small nonzero β because "it scaled in our range" hides a finite peak you have not reached yet.
- **Scaling out before removing coherency.** A non-negligible β means more nodes eventually hurt. Buying nodes to outrun crosstalk funds the thing that is slowing you down. Cut the crosstalk first.

---

## Worked example: capacity-planning a read service

**The decision.** A read-heavy API serves 4k RPS today at p99 = 35 ms. Product forecasts 12k RPS in two quarters. Question: does the current fleet hold, and if we add nodes, how far does it go? Scaling inputs are *load* (now) and *resources* (the add-nodes option); output is p99 under a 50 ms SLO; we want the regime at 12k.

**Per-unit numbers (step 2).** Mean service time at low load `W` = 8 ms. Each node runs a pool of 200 worker permits. Measured serial fraction (config lookup + a shared metrics counter) is small but real.

**Little's Law sizing (step 3).** At 12k RPS and 8 ms, required concurrency `L = λ·W = 12000 × 0.008 = 96` in flight. One node's 200 permits covers that on paper, so permits are not the cap. But that assumes `W` stays at 8 ms, which it will not near saturation, so this is a floor, not a verdict.

**USL fit (step 4).** Per-node throughput measured at N = 1, 2, 4, 8, 16, 24 cores under saturating per-core load, normalized and regressed, yields α ≈ 0.04, β ≈ 0.0006. Peak at `N* = sqrt((1 − 0.04)/0.0006) ≈ sqrt(1600) = 40` cores. The 24-core nodes sit below the peak, good, but β is nonzero: a 64-core node would be *past* `N*` and slower per core. The coherency source is the shared metrics counter (cache-line bouncing); sharding it per-core would shrink β and push `N*` out.

**Knee, not max (step 5).** Single-node sweep shows throughput near-linear to ~3.5k RPS/node, knee around 4k, p99 crossing the 50 ms SLO at ~4.3k RPS/node. So the *operating* ceiling is ~3.8k RPS/node (below the knee), not the ~4.5k throughput max. For 12k RPS: `12000 / 3800 ≈ 3.2`, so 4 nodes, not 3.

**Open-loop validation (step 6).** Drive 12k RPS constant-arrival with `wrk2` against a 4-node staging fleet, 20-minute run to catch GC. p99 measured at 41 ms, under SLO. A closed-loop `ab` run had earlier reported p99 = 22 ms at the same nominal load, the coordinated-omission fiction that would have justified 3 nodes and a pager at peak.

**The claim (step 7).** *"Read path scales near-linearly to ~3.8k RPS/node before the latency knee; 4 nodes hold 12k RPS at p99 = 41 ms (open-loop, SLO 50 ms). Per-node USL fit α≈0.04, β≈0.0006 gives a core peak at ~40, so do not move to 64-core nodes without sharding the metrics counter; the next constraint past 12k is that counter's coherency term."* Every number is defended, and the next engineer knows exactly what to re-measure.

---

## Where next

| You need… | Go to |
|---|---|
| a bottleneck that already hurts, located | `../diagnose/index.md` |
| the saturation curve as a live diagnosis under load | `../diagnose/index.md` (saturation curve section) |
| to size and overlap high-latency operations in one request | `latency-hiding.md` |
| to catch a scaling/capacity regression before it ships | `regression-ci.md` |
| the design-time levers this sizing feeds (Lever 4/5) | `design-for-performance.md` |
