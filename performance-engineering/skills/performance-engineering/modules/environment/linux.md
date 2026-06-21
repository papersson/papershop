# Linux instruments: perf + eBPF

**Status:** READY
**Loaded when:** the diagnose procedure has put you on a Linux host and you need the actual commands.

**Scope: Linux host.** `perf` and eBPF (`bpftrace`/`bcc`) are Linux-only, and the 60-second triage and every perf-based step below assume a Linux kernel. On macOS / Apple Silicon — the common LOCAL case — these binaries do not exist; use the Instruments / `dtrace` / `xctrace` equivalents in `local-mac.md` instead.

This is the instrument reference the method points into. `../diagnose/profiling.md` decides *what* to measure (on-CPU vs off-CPU, sample vs instrument) and `../diagnose/index.md` decides *which* counter answers your question; this file is *how* to read each one on Linux. It does not re-teach the method, and it does not judge the numbers — every value here gets its ignore / investigate / dominant band from `../diagnose/calibration-tables.md`. macOS is `local-mac.md`; production and distributed observability is `prod-distributed.md`.

Two tools cover almost everything on Linux: **perf** for CPU counters, sampling, and microarchitectural attribution, and **eBPF** (`bpftrace` / `bcc`) for kernel-side and off-CPU behavior. `ftrace` sits underneath for raw function tracing.

---

## perf: the four modes

`perf` is one binary with subcommands that fall into four jobs. Know which job you are doing.

| Mode | Command | Answers | Cost |
|---|---|---|---|
| **Count** | `perf stat` | how many of event X over the whole run (or `-a` for the whole system) | negligible, no samples |
| **Capture** | `perf record` | *where* the samples land (writes `perf.data`) | low at 99 Hz, tunable |
| **Report** | `perf report` / `perf annotate` / `perf script` | browse the capture by function, by source line, or as raw stacks | offline |
| **Live** | `perf top` | a `top`-like view of the hottest functions right now | low |

**Run `perf stat` before `perf record`.** Counting is cheap and whole-run; it tells you the shape of the problem (memory-bound? branch-bound? front-end-bound?) before you spend effort capturing stacks. A flame graph shows you *where* the program counter sits; `perf stat` is what tells you whether that spot is busy or stalled. Characterize first, localize second.

```
perf stat ./prog                      # cycles, instructions, IPC, branches, branch-misses, task-clock
perf stat -a sleep 10                 # system-wide for a 10s window
perf stat -p <pid> -- sleep 10        # attach to a running process
```

## perf stat: cache tiers with -d

`-d` adds detailed memory counters in tiers; stack them as you narrow:

```
perf stat -d ./prog          # + L1-dcache loads/misses, LLC loads/misses
perf stat -d -d ./prog       # + dTLB and iTLB loads/misses (translation)
perf stat -d -d -d ./prog    # + L1-icache and prefetch counters
```

Read top-down: IPC first (are we retiring work at all?), then LLC-miss% (is the working set spilling to DRAM?), then dTLB-miss% (is translation the tax, not the data?). An IPC near the machine's peak with low miss rates is healthy; a low IPC with a high LLC-miss% is the classic memory-latency-bound shape. The bands that turn these percentages into a verdict are in `../diagnose/calibration-tables.md`.

## perf stat --topdown

When IPC is low and you do not yet know *why*, attribute every cycle to one of four buckets instead of reasoning counter-by-counter:

```
perf stat --topdown -a sleep 10
perf stat --topdown --td-level 2 ./prog    # drill the dominant bucket one level deeper (Icelake+)
```

- **Retiring** — useful work; more is better.
- **Bad speculation** — cycles on instructions later squashed (branch mispredicts, machine clears).
- **Front-end bound** — the back-end was ready but instructions could not be fetched/decoded fast enough.
- **Back-end bound** — instructions ready but could not execute; splits into *memory-bound* (waiting on loads) and *core-bound* (port/execution-unit pressure, long dependency chains).

One bucket usually dominates; drill only into that one. Top-down needs a supported PMU. Skylake/Cascadelake expose only **Level 1** (the four top buckets, via legacy events); hierarchical drill-down (`--td-level 2` and deeper, via the perf-metrics/slots PMU) requires **Icelake+** — on a Skylake host `--td-level 2` errors out, so stop at Level 1 there. AMD Zen has native top-down; on still-older parts perf approximates Level 1 from raw events. Note that top-down hides orthogonal problems — false sharing, lock contention, NUMA — under "back-end bound"; check those explicitly with the tools below when scaling is bad.

## perf: PMU event selection

The default events are a starting set. Name the event you actually want with `-e`:

```
perf stat -e cycles,instructions,branches,branch-misses ./prog
perf stat -e LLC-load-misses,dTLB-load-misses ./prog
perf list                                   # what this CPU exposes (named + raw aliases)
```

- **Named events** — portable aliases (`cycles`, `cache-misses`, `branch-misses`).
- **Raw events** — `rNNNN` (e.g. `r01a8`) or the verbose `cpu/event=0xa8,umask=0x01/` form, for microarch events with no alias. Get the codes from `perf list` or the vendor's PMU reference.
- **Modifiers** — append `:u` (user space only), `:k` (kernel only), `:p`/`:pp`/`:ppp` (precise / PEBS — anchors the sample to the right instruction; use the highest precision the event supports for memory and branch sampling).
- **Event groups** — `-e '{cycles,instructions}'` measures the bracketed set *together on the same counters*, so their ratio is exact rather than smeared across multiplexed windows.

## Counter multiplexing

A CPU has only a handful of physical PMU counters (commonly 4–8 general-purpose). Ask for more events than there are counters and the kernel **time-multiplexes**: each event runs for a fraction of the run, and perf **scales** the result up to a full-run estimate. perf prints the fraction it actually measured, e.g. `[83.33%]`. Scaling adds error, and it breaks ratios between events that were never live at the same instant. Two fixes: keep your event count within the physical counters, or use event groups (`{...}`) so the events whose ratio you care about are guaranteed co-resident. When a number looks impossible, check its measured-percentage first.

## perf: the 99 Hz flame-graph pipeline

The standard on-CPU flame graph. 99 Hz (not 100) avoids lockstep with the scheduler tick; `-a` samples all CPUs, `-g` captures call graphs:

```
perf record -F 99 -ag -- sleep 30
perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg
```

For one process, drop `-a` and use `-p <pid>` or run the command under `perf record`. You need usable stacks: build with frame pointers, or add `--call-graph dwarf` when frame pointers are missing (heavier, but works on optimized binaries). Reading the result — width is cost, top edge is what was on-CPU, drill only into the widest box — is in `../diagnose/profiling.md`.

## perf record / report / annotate

Localize after capturing:

```
perf record -F 99 -g ./prog          # capture with call graphs
perf report                          # interactive tree, by symbol, self vs children
perf report --stdio                  # same, dumped to stdout
perf annotate <symbol>               # per-instruction cost, source interleaved with asm
```

`perf annotate` is the last zoom: it shows which *instruction* in a hot function carries the samples, which is how you tell an expensive load apart from the arithmetic next to it.

## perf c2c: false sharing

Cache-to-cache analysis (Linux 4.10+). The tool for the false-sharing bug a flame graph cannot see — two threads writing different variables that share one cache line (64 bytes on x86; **Apple Silicon is 128** — query it with `sysctl hw.cachelinesize` rather than assuming, and pad with `std::hardware_destructive_interference_size` instead of a hardcoded 64). `perf c2c` itself is Linux-only; on macOS reach for Instruments' counters per `local-mac.md`:

```
perf c2c record ./prog
perf c2c report -NN                   # ranked by HITM
```

It reports **HITMs** — loads that hit a *modified* line in another core's cache — grouped by cache line and by source line. A hot line with HITMs from multiple CPUs is almost certainly false sharing (or true sharing that should not be there); the fix is padding/alignment to separate the variables onto their own lines.

## perf mem / perf lock / perf sched

Three targeted captures for bottlenecks top-down hides:

```
perf mem record ./prog && perf mem report      # load/store sampling with access latency and data source
perf lock record ./prog && perf lock report    # kernel lock contention (acquire wait, hold time)
perf sched record -- sleep 10 && perf sched latency   # scheduler: run-queue delay per task
perf sched timehist                             # per-event scheduling timeline
```

`perf mem` tells you *which level* each sampled access came from (L1/L2/L3/DRAM/remote), the bridge to memory-latency attribution. `perf lock` quantifies contention. `perf sched` is the on-CPU side of off-CPU analysis — it shows run-queue latency (time runnable but not scheduled), which a CPU profiler is blind to. For deeper off-CPU work (blocked on I/O, locks, sleeps), use eBPF below.

---

## eBPF: bpftrace

`bpftrace` is the high-level tracer. Every program is **probe / filter / action**:

```
probe /filter/ { action }
```

```
# count syscalls by process
bpftrace -e 'tracepoint:raw_syscalls:sys_enter { @[comm] = count(); }'

# read() return size as a power-of-2 histogram
bpftrace -e 'tracepoint:syscalls:sys_exit_read { @bytes = hist(args->ret); }'

# time a kernel function: kprobe entry stamps, kretprobe measures, lhist buckets it
bpftrace -e 'kprobe:vfs_read { @s[tid] = nsecs; }
             kretprobe:vfs_read /@s[tid]/ { @us = lhist((nsecs - @s[tid]) / 1000, 0, 10000, 100); delete(@s[tid]); }'
```

Probe types: **kprobe / kretprobe** (any kernel function, entry/return), **uprobe / uretprobe** (user-space functions in a binary or library), **tracepoint** (stable, documented kernel events — prefer these over kprobes when one exists), **usdt** (user statically-defined probes), **profile / interval** (timer-driven, for sampling), **software / hardware** (PMU events).

Aggregation happens in **maps** (`@name[key]`). The aggregating functions — `count()`, `sum()`, `avg()`, `min()`, `max()`, `hist()` (power-of-2 buckets), `lhist()` (linear buckets) — run **in the kernel**, so only the compact summary crosses to user space, not every event. That in-kernel aggregation is why these tools are low-overhead enough to run in production: you are not shipping a million events to be counted in userland, you are shipping one histogram.

## eBPF: the bcc tool catalog

`bcc` ships pre-built tools, each answering one question. Reach for the tool, not a one-liner, when one exists. Indexed by what it answers:

| Tool | Answers |
|---|---|
| `execsnoop` | what processes are being exec'd (short-lived ones a `ps` snapshot misses) |
| `opensnoop` | which files are being opened, by whom |
| `biolatency` | block-I/O latency as a histogram |
| `biosnoop` | per-I/O latency, one line each, with process and offset |
| `ext4slower` / `xfsslower` | filesystem operations slower than a threshold |
| `runqlat` | scheduler run-queue latency (time runnable but not on-CPU) |
| `runqlen` | run-queue length over time |
| `funclatency` | latency distribution of a chosen kernel/user function |
| `funccount` | call counts for functions matching a pattern |
| `offcputime` | **off-CPU** time aggregated by blocked stack — the core off-CPU profiler |
| `wakeuptime` | who woke a blocked thread, and after how long |
| `profile` | timed on-CPU stack sampler (flame-graph input, eBPF-native) |
| `tcplife` | lifespan and bytes of each TCP session |
| `tcpconnect` / `tcpretrans` | active connections / retransmits with addresses |
| `cachestat` | page-cache hit/miss ratio |
| `llcstat` | last-level-cache hit ratio by process |

**Off-CPU analysis** is the half of wall-clock a CPU profiler cannot see (blocked on a lock, I/O, a syscall, a sleep, the run queue). `offcputime` captures the stack at the moment a thread is scheduled off and weights it by how long it stayed off; render it as a flame graph the same way as an on-CPU one. When the symptom is "slow but the CPU is idle," this is the tool. The method behind it is in `../diagnose/profiling.md`.

---

## ftrace / trace-cmd

Underneath perf and eBPF sits **ftrace**, the kernel's built-in function tracer (the `function` and `function_graph` tracers, plus tracepoint events). `trace-cmd` is the friendlier front-end:

```
trace-cmd record -p function_graph -g vfs_read   # trace a function and its callees
trace-cmd report
```

Reach for it when you want a literal ordered trace of kernel function calls (causality and timing of a specific path), rather than the aggregated picture perf and bpftrace give. KernelShark visualizes the result. For most performance work, perf and bpftrace come first; ftrace is the deep kernel-path tool.

---

## Where next

| You have… | Go to |
|---|---|
| the method (what to measure, how to read a flame graph) | `../diagnose/profiling.md` |
| only 60 seconds and a host | `../diagnose/triage-60s.md` |
| a counter value, unsure if it's bad | `../diagnose/calibration-tables.md` |
| a Mac / local single process | `local-mac.md` |
| a production distributed system | `prod-distributed.md` |
