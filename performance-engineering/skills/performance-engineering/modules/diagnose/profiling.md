# Profiling: sampling vs instrumenting, flame graphs

**Status:** READY
**Loaded when:** you need to see WHERE time or resources actually go inside a run.

This is a tool inside the **locate** step of the SKILL.md loop (`index.md`, step 2 "characterize the workload" and step 3 "identify the dominant bottleneck"). A profiler answers one question well — *where in the code do the samples land?* — and one question badly. The badly-answered question is *why was that spot slow?*, and the whole method below exists to keep you from mistaking the first answer for the second. The method is tool-agnostic; for the actual commands see `../environment/linux.md` (perf/eBPF) and `per-language.md` (managed-runtime profilers).

*Scope: the method here is platform-independent, but the concrete commands and counter steps below (`perf stat`, PMU-event sampling, eBPF off-CPU, the `triage-60s.md` flow) assume a Linux host — `perf` and eBPF are Linux-only. On macOS / Apple Silicon the discipline is identical but the tooling differs (Instruments, `xctrace`, `sample`, `sysctl`); see `../environment/local-mac.md` for the equivalents.*

The core rule: **a profiler attributes cost to the instruction at the program counter, not to the cause of the stall.** An arithmetic op at the top of the profile for 40% of samples may be a one-cycle `add` waiting hundreds of cycles for the load that feeds it. The cost is the load, but the sample is charged to a nearby PC — and *which* PC is only approximate: interrupt skid means the recorded address often lands a few instructions past the stalling load, not exactly on the consuming op. So trust the principle (cost is attributed to a PC, not to the cause) rather than the exact line; read the flame graph to find *where*, then cross-check counters to learn *why* — never the flame graph alone.

---

## Procedure

### 1. Decide what you are accounting for: on-CPU or off-CPU
Wall-clock time splits cleanly into two halves, and an ordinary profiler only sees one of them.

- **On-CPU** — the thread was running on a core. A sampling CPU profiler captures this: where the cycles went.
- **Off-CPU** — the thread was blocked, not scheduled: waiting on I/O, a lock, a syscall, a sleep, a GC pause, the run queue. A CPU profiler is blind here because nothing is executing to sample.

If the symptom is "high CPU / low throughput," profile on-CPU. If the symptom is "latency / bad tail / it's slow but the CPU is idle," the time is almost certainly off-CPU and an on-CPU flame graph will look clean and tell you nothing. On-CPU plus off-CPU together account for the full wall clock. Pick by symptom; when unsure, do both.

### 2. Pick the mode: sampling or instrumenting
Default to **sampling**. Reach for instrumenting only when you need exact counts or per-call timing of a specific, not-ultra-hot region. The contrast is in the table below.

### 3. Collect with stacks, at a fixed off-round frequency
For sampling, collect full call stacks (you cannot read a flame graph without them — that means frame pointers, DWARF unwinding, or a runtime that gives stacks). Sample at a **fixed odd frequency, conventionally 99 Hz**, not 100 Hz. The odd number avoids lockstep with periodic system activity (the 100 Hz scheduler tick, timers firing on round boundaries); sampling in phase with a recurring event biases every sample toward or away from it. 99 Hz across all CPUs for tens of seconds gives thousands of samples, enough to resolve anything that costs more than ~1% without measurable overhead. Raise the rate for short runs, lower it if overhead shows.

### 4. Read the flame graph top-down (see the reading guide below)
Find the widest top edges. Those are where the cycles actually went.

### 5. Cross-check the hot spot against counters before believing the cause
This is the step people skip. The flame graph told you *which* function. Now confirm *why* with `perf stat` / top-down (`../environment/linux.md`; macOS / Apple Silicon equivalents in `../environment/local-mac.md`): a "hot" function with IPC ~0.4 and a 40% LLC-miss rate is not compute-bound, it is memory-bound and stalled — optimizing its arithmetic does nothing. Map the answer back to a bound type with `../orient/bound-types.md`, then hand the named bottleneck to step 3 of `index.md`.

---

## Sampling vs instrumenting

| | **Sampling** | **Instrumenting** |
|---|---|---|
| How | periodically interrupt (timer or PMU event), record the stack | insert probes at function entry/exit (or via a tracer) that count and time every call |
| Cost | low, roughly fixed, tunable by frequency; production-safe | proportional to call frequency; can dominate and distort hot tiny functions (observer effect) |
| Bias | statistical: blind between samples, misses anything rarer/shorter than the interval; can suffer safepoint bias in managed runtimes | skews toward frequently-called cheap functions; per-call overhead inflates exactly the hottest leaves; can defeat inlining |
| Gives you | a proportional picture of where the bulk of time goes | exact call counts and exact per-call timing, no statistical blind spots |
| Use when | always, as the default first pass | you need an exact count, or to time a specific low-to-moderate-frequency region deterministically |

The trap with instrumenting is the observer effect at its worst: instrument a function called a billion times per second and the per-call probe overhead becomes the profile, inflating that leaf and slowing the whole run. Never instrument an ultra-hot leaf; sample it. Conversely, sampling cannot tell you a function was called 3 million times instead of 3 — for that you instrument. Managed runtimes have their own sampling-vs-safepoint subtleties (a profiler that only samples at GC safepoints over-attributes to functions near safepoints); the per-runtime details and which profiler to trust are in `per-language.md`.

## On-CPU vs off-CPU profiling

**On-CPU** profiling is the familiar kind: sample the running thread, build a flame graph of where cycles burned. It explains throughput and compute-bound latency.

**Off-CPU** profiling captures a stack at the moment a thread is scheduled *off* a core, weighted by how long it stayed off. It is built from scheduler tracepoints (eBPF `offcputime` and friends, `../environment/linux.md`), not from a timer. It explains the time a CPU profiler cannot see: blocking on locks, I/O waits, syscalls, sleeps, runqueue latency. The off-CPU flame graph reads the same way as an on-CPU one, except a wide box means "spent a long time blocked here," not "burned cycles here."

Some latency lives in neither cleanly: GC pauses and large allocator stalls may show as off-CPU or as a runtime-internal thread, and are most reliably found in the runtime's own pause log plus a latency histogram (this is the tail trap from `index.md`'s second worked sketch — a clean CPU flame graph hiding a 100 ms GC stall). When the tail is the problem, measure the tail directly; do not expect an averaged CPU profile to show a pause that happens 1% of the time.

## Reading a flame graph

A flame graph is merged stack samples drawn as nested rectangles. The two axes do not mean what people assume.

- **x-axis is NOT time.** Stacks are merged and sorted alphabetically, then drawn left to right. There is no left-to-right time progression; position carries no meaning. What carries meaning is **width**: a box's width is the fraction of samples (hence fraction of cost) in which that frame was present.
- **y-axis is stack depth.** The bottom frame is the entry point / root; each frame above is a callee of the one below.
- **The top edge is what was on-CPU at sample time** — the leaf where the program counter actually sat. Sum the top-edge width of a function across the graph and you get its **self (exclusive) cost**. The full width of a box is its **inclusive cost**: itself plus everything it called.

How to read one:

1. Scan the **top edge** for the widest plateaus. A wide flat top is a single function eating self time — your hot leaf. Start there.
2. A **tall narrow tower** is a deep call chain that is not individually expensive; depth is just nesting, not cost. Don't be distracted by tall — be drawn to wide.
3. Work **top-down as a search**: the dominant box at one level tells you which subtree to descend into; ignore the narrow siblings. This is the same discipline as the rest of the loop — find what dominates, drill only into that, recurse — and it is why you profile broad before zooming into any one function.
4. For before/after, use a **differential flame graph**: it colors what grew and what shrank, so a fix's effect (and any regression it caused elsewhere) is visible at a glance. This pairs with `../measure/` proof.

The one thing a flame graph will not tell you is on its own whether a wide leaf is busy or stalled. Two functions with identical width can be one that retires 3 instructions per cycle and one stuck at 0.3 IPC waiting on DRAM. That distinction comes from counters, not from the picture (step 5).

## What to profile for each bound type

The bound type (`../orient/bound-types.md`) decides which profiling instrument actually localizes the cause. Using the wrong one produces a confident, wrong answer.

| Suspected bound | Profile with | Why the obvious tool misleads |
|---|---|---|
| Compute / core-bound | on-CPU flame graph + top-down (retiring / core-bound) | this is the case the plain flame graph handles well |
| Memory-bound (latency or bandwidth) | counters first (IPC, LLC-miss, bandwidth), then **PMU-event sampling** on cache-miss events | timer-sampled flame graph blames the instruction consuming the load, not the load; you must sample on the miss event to attribute it |
| Branch / bad-speculation | `perf stat` branch-miss rate, then PMU sampling on branch-misses | the mispredict cost is smeared across the flushed path, not on one line |
| Off-CPU: I/O wait, lock contention, sleep, runqueue | off-CPU profiler (scheduler tracepoints / eBPF) | nothing is on-CPU to sample; the CPU flame graph is empty where the time is |
| Tail / pauses / GC | latency histogram + runtime GC log + off-CPU | averaged CPU profile cannot show a rare pause |
| Syscall / kernel time | syscall summary (`strace -c`, `perf trace`) + off-CPU | the time is across the user/kernel boundary, often blocked |

PMU-event-based sampling (sample on "every N cache misses" rather than "every N microseconds") is the bridge from "where the time is" to "where the misses are." The exact event names and invocations are in `../environment/linux.md`.

## Pitfalls

- **Trusting the leaf as the cause.** The widest top edge is *where the PC sat*, not *why it was slow*. Always pair with counters (step 5). This is the single most common profiling error.
- **No stacks, or broken stacks.** Without frame pointers / unwinding, the flame graph is a flat list with no call context and is nearly useless. Build with frame pointers or DWARF; verify the stacks look sane before drawing conclusions.
- **Reading width as time-order.** Left/right is alphabetical, not chronological. A flame graph does not show *when* things happened, only *how much*. For ordering, you need a trace, not a profile.
- **Sampling in lockstep.** 100 Hz against a 100 Hz tick biases samples; use 99 Hz (or another off-round rate).
- **Instrumenting a hot leaf.** The probe overhead becomes the measurement. Sample hot code; instrument only colder, count-critical code.
- **On-CPU profiling a latency problem.** If the CPU is idle and it's still slow, the time is off-CPU; an on-CPU profile will be clean and you will conclude, wrongly, that there is nothing to fix.

## Worked examples

**Hash-map lookup, flame graph says `probe()` is 55% of samples.** Naive reading: optimize `probe()`'s arithmetic. Cross-check (step 5): IPC 0.6, LLC-miss 45%. `probe()` is not computing, it is pointer-chasing an arena larger than L3 — memory-latency-bound. The fix is data layout (open addressing, smaller entries), not faster code in `probe()`. (Mirrors the loop in `index.md`.)

**Web service, p99 180 ms, on-CPU flame graph looks healthy.** The CPU profile shows ordinary request handling, nothing dominant — because the tail is not on-CPU. Off-CPU profiling shows 100-150 ms stacks parked in the allocator / collector; the runtime GC log confirms young-gen pauses. No on-CPU optimization touches this. The tool choice, on-CPU vs off-CPU, *was* the diagnosis.

**A function you suspect is called too often.** Sampling shows it as a thin sliver, so it looks cheap. But you suspect call *count*, not per-call cost. Instrument just that function: it turns out called 4 million times where 4 was expected. Sampling could never have shown the count; instrumenting that one (not-ultra-hot) function did.

## Where next

| You have… | Go to |
|---|---|
| a managed runtime (JVM, Go, .NET, Node, Python) | `per-language.md` |
| need the actual perf / eBPF / off-CPU commands | `../environment/linux.md` |
| a Mac / local single process | `../environment/local-mac.md` |
| a hot spot but don't know the bound type | `../orient/bound-types.md` |
| a counter value and don't know if it's bad | `calibration-tables.md` |
| the profile, ready to pick the dominant bottleneck | `index.md` (step 3) |
| only 60 seconds on a Linux host | `triage-60s.md` |
