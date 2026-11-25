# Counter calibration tables (ignore / investigate / dominant)

**Status:** READY
**Loaded when:** you have a counter value and need to know whether it is fine, suspicious, or the bottleneck.

This is the lookup table behind step 3 of the locate loop (`index.md`). You arrive with a number off `perf stat` or a profiler and one question: *is this band ignore, investigate, or dominant?* The rule the whole page enforces: **decide dominance against thresholds, not vibes.** Almost every counter has a benign range that looks alarming and an alarming range that looks benign, so the raw value alone tells you nothing until you place it in a band.

Two cautions before the numbers. First, a counter is only meaningful **in the hot region** — a 12% branch-miss rate averaged over a whole process means nothing; the same rate inside the loop that owns 70% of cycles is the bottleneck. Always scope the counter to the code that dominates the profile. Second, these bands are anchors for modern big cores (issue width 4–8), not laws of physics; a number near a boundary means *measure the next thing*, not *act*. The dominance call is cross-checked against top-down bound type in `../orient/bound-types.md`, and the commands that read each counter are in `../environment/linux.md`.

**Environment scope.** The bands are platform-neutral, but the instruments that produce them (`perf stat --topdown`, `perf c2c`, `perf lock`, `perf sched`) are Linux/x86 — `perf` and eBPF do not exist on macOS. If you are working LOCAL on macOS / Apple Silicon, read counters through Instruments / dtrace instead and map them back to these bands via `../environment/local-mac.md`. Two numbers below also shift on Apple Silicon: the cache line is 128 bytes, not 64 (`sysctl hw.cachelinesize`; prefer `std::hardware_destructive_interference_size` over a hardcoded 64), and peak IPC is higher on its wider cores.

---

## The master dominance table

This is the table `index.md` step 3 points into. After characterization most numbers land in **Ignore**. The ones in **Dominant** are your bottleneck; the ones in **Investigate** are candidates that become dominant after you fix the first.

| Signal | Ignore | Investigate | Dominant |
|--------|--------|-------------|----------|
| Fraction of a top-down *stall/waste* bucket (front-end-, back-end-, bad-speculation-bound; **not** retiring) | < 20% | 20–40% | > 40% |
| Branch miss rate (in hot loop) | < 1% | 1–5% | > 5% |
| LLC miss rate (of LLC loads) | < 10% | 10–30% | > 30% |
| dTLB miss rate | < 0.1% | 0.1–1% | > 1% |
| Bandwidth vs STREAM | < 50% | 50–80% | > 80% (saturated) |
| Lock wait / total time | < 1% | 1–10% | > 10% |
| Remote DRAM fraction (NUMA) | < 10% | 10–30% | > 30% |
| Syscall time / total | < 5% | 5–20% | > 20% |
| GC pause / wall time | < 1% | 1–5% | > 5% |

A reading in the Dominant column is a located bottleneck: name it, then go to the matching intervention family in `../optimize/`. A reading in Investigate is a hypothesis to hold while you confirm the dominant one — most real workloads have **one** dominant bottleneck plus one or two that surface after you fix it. If you are reading five counters all in the Dominant column, you are misattributing (top-down reports coherence traffic as "back-end bound") or you have not measured carefully — re-measure, do not theorize.

---

## Per-profile calibration

The six characterization profiles from `index.md` step 2, each with the numeric bands that turn its raw counters into a verdict. Walk them in this order when you have a full `perf stat` dump and don't yet know which profile owns the problem.

### 1. Work profile — IPC

Instructions per cycle on a wide core. Low IPC means the core is stalled, not working; that is the signal to go hunting in the memory and concurrency profiles for *what* it is stalled on.

| IPC | Interpretation |
|-----|---------------|
| < 0.5 | Severely stalled — almost certainly memory- or synchronization-bound |
| 0.5 – 1.5 | Typical for mixed workloads; stalled somewhere |
| 1.5 – 3.0 | Good — the core is mostly working |
| 3.0+ | About as good as real code gets — further wins require algorithmic or SIMD changes (note: this is well below the 4–8 issue width, and below the 6–8 IPC a wide Apple Silicon core can hit; it is a practical ceiling for typical code, not the hardware peak) |

IPC is a smoke alarm, not a diagnosis. A low number sends you to the back-end profiles; a high number means the only remaining lever is doing less work or wider work (`../orient/bound-types.md`, retiring-bound).

### 2. Memory profile — cache, TLB, bandwidth

What bytes move and how far. This profile carries the most counters and the most false alarms, so the bands matter.

| Signal | Benign | Suspicious | Bad |
|--------|--------|------------|-----|
| L1 miss rate | < 5% | 5–15% | > 15% |
| LLC miss rate (of LLC loads) | < 10% | 10–30% | > 30% |
| dTLB miss rate | < 0.1% | 0.1–1% | > 1% |
| Cache-line utilization | > 50% | 25–50% | < 25% |
| Bandwidth vs STREAM | < 50% | 50–80% | > 80% (saturated) |

Read these together, not one at a time. High LLC miss with **low** bandwidth vs STREAM means memory-*latency*-bound (waiting on individual round trips — fix locality, MLP, data structure). High LLC miss with bandwidth **near STREAM** means memory-*bandwidth*-bound (moving bytes as fast as the bus allows — fix by moving fewer bytes; more threads will not help). High dTLB miss with a large random working set points at huge pages. Low cache-line utilization (8 useful bytes of a 64-byte line — 128 bytes on Apple Silicon, check `sysctl hw.cachelinesize`) is a layout problem the byte count hides. The bandwidth-vs-STREAM number is the single most decisive one in this profile: above 80% you are saturated and wider SIMD or more threads buy nothing.

### 3. Control-flow profile — branches

Mispredict penalty is ~15–20 cycles; on a hot branch that dominates fast.

| Branch miss rate (in hot loop) | Interpretation |
|---|---|
| < 1% | Predictor has it; ignore |
| 1–5% | Worth investigating — data-dependent branch, indirect dispatch |
| > 5% | Dominant; > 10% usually means effectively unpredictable |

Above ~10% the branch is effectively a coin flip: the data needs reordering (sort/group so like cases cluster) or the branch needs to become a data operation (branchless, mask, table). Below that, leave it alone — a correctly predicted branch that skips expensive work is free, and making it branchless executes the expensive side every iteration. Indirect branches (virtual calls, interpreter dispatch, function pointers) feed a weaker predictor and front-end-bound easily even at modest miss rates; count them per unit of work, not just their miss rate.

### 4. Concurrency profile — the scaling curve

There is no single counter here; the diagnosis is the **shape** of wall-time vs thread count. Plot it.

| Shape | Interpretation |
|-------|---------------|
| Near-linear to many cores | Work is genuinely independent; memory system not saturated |
| Linear then plateau | Hit a shared resource — usually DRAM bandwidth or coherence |
| Linear then regression | Added contention — lock, false sharing, or cross-socket traffic |
| Barely moves | Almost entirely serial; look for one lock or one shared counter |

The supporting counters that say *which* shared resource: lock-wait fraction (> 10% of time = dominant, from `perf lock` / futex time), HITM rate on hot lines (true or false sharing, from `perf c2c`), and remote-DRAM fraction on NUMA (> 30% = placement is wrong). A plateau plus near-STREAM bandwidth is the bandwidth knee; a regression plus high HITM is coherence. These are exactly the orthogonal bottlenecks top-down hides under "back-end bound," so check them explicitly whenever scaling disappoints.

### 5. System-boundary profile — kernel, faults, GC

What crosses into the kernel or the runtime. The numeric anchors live in the master table (syscall time / total, GC pause / wall time); the qualitative reads:

- **Syscalls per unit work** — each is hundreds of ns minimum; a million small ones per second is real CPU. One-byte-at-a-time I/O pays the syscall cost per byte. Batch (`writev`, larger reads, io_uring).
- **Context switches** — voluntary = blocking on I/O or a lock; involuntary = preemption. Both burn cache warmth.
- **Page faults** — minor (zero-fill, COW) are microseconds; major (backing store) run ~10–100 µs on NVMe and into the milliseconds on spinning disk, and can own the tail by themselves.
- **GC / runtime pauses** — a 5 ms pause at 1% frequency is invisible in the mean and dominant in the tail. Confirm against the runtime's own log.

### 6. Latency-distribution profile — the tail

| Question | What it tells you |
|---|---|
| p50 / p99 / p99.9 / max | User-visible performance is the tail; the mean hides the system you have |
| Source of each tail bump | GC, page fault, JIT, scheduler, lock spike, TLB shootdown — each has a fingerprint |
| Open- or closed-loop benchmark? | Closed-loop hides tails via coordinated omission; measure open-loop |
| Observation window | A 5-min run can miss a GC that runs every 10 min |

No CPU counter explains a tail by itself. When p99 ≫ p50 but average IPC and CPU look fine, the bottleneck is almost always off-CPU (a pause, a fault, queueing), and the off-CPU profile (`perf sched`) plus the runtime log locates it.

---

## Pitfalls

- **Reading a counter outside its hot region.** A process-wide average dilutes the hot loop into noise. Scope every number to the code that owns the cycles, or the band is meaningless.
- **One counter, one verdict.** LLC-miss alone does not distinguish latency-bound from bandwidth-bound; you need the STREAM ratio next to it. dTLB-miss alone does not tell you huge pages will help; you need the access pattern. Read the profile, not the cell.
- **Treating boundaries as cliffs.** 79% vs 81% of STREAM is the same situation. A near-boundary value means measure the adjacent counter, not act.
- **Counting orthogonal bottlenecks as back-end-bound.** Coherence, lock contention, NUMA, page faults, and GC all show up as "back-end bound" or "off-CPU" in a naive read. The concurrency and system-boundary bands above exist to pull them out explicitly.
- **Trusting a counter that never changed.** After a fix, re-read the same counter. If huge pages were supposed to drop dTLB-miss and it did not move, the optimization is not actually engaged (the allocator silently fell back to 4 KB pages — verify with `/proc/meminfo`, `pmap -XX`). A counter that moves in the predicted direction is the proof; one that does not means the model was wrong.

---

## Worked example

`perf stat --topdown` on a JSON log parser, single-threaded, 40 MB/s/core, 3.5 GHz. Raw readings placed in bands:

| Counter | Reading | Band | Read |
|---|---|---|---|
| IPC | 1.1 | typical, stalled somewhere | go to back-end profiles |
| LLC miss | 2% | Ignore | memory is not the problem |
| dTLB miss | 0.05% | Ignore | translation fine |
| Branch miss (hot loop) | 12% | **Dominant** (> 5%) | branches own it |
| Bad-speculation bucket | 28% | Investigate (20–40%) | corroborates control flow (high for this bucket — it rarely tops 40% even when branches dominate) |
| Back-end bound | 35% | Investigate | secondary, core-bound on branchy flow |

Verdict: control-flow-bound. The 12% branch-miss is well into Dominant and is effectively unpredictable (data-dependent branch on each character), corroborated by the 28% bad-speculation bucket. Memory bands are all Ignore, so layout work would buy nothing. Hand off to `../optimize/` for the matching family: SIMD/branchless parsing, vectorized character classification. The back-end-bound 35% is the secondary bottleneck that will surface once the branches are gone — note it, do not chase it yet.

Contrast: a web service at p50 5 ms, p99 180 ms. Every CPU band is Ignore (IPC fine, miss rates low) — because the bottleneck is not on-CPU at all. The off-CPU profile shows 100–150 ms stretches; the GC band (pause / wall time) lands Dominant. No on-CPU counter would ever have found it; the latency-distribution profile is what pointed off-CPU.

---

## Where next

| You have… | Go to |
|---|---|
| the overall locate procedure these tables serve | `index.md` |
| a dominant band and need to know what *kind* of bound it is | `../orient/bound-types.md` |
| a counter to read but not the command | `../environment/linux.md` |
| a 60-second first pass before full characterization | `triage-60s.md` |
| a located bottleneck, ready to fix | `../optimize/` |
| a fix applied, need to confirm the counter moved | `../measure/verify.md` |
