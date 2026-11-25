# macOS instruments: Instruments + xctrace

**Status:** READY
**Loaded when:** working locally on macOS (single machine).

This is the instrument reference the method points into when the context is a developer's own Mac. `../diagnose/profiling.md` decides *what* to measure (on-CPU vs off-CPU, sample vs instrument) and `../diagnose/index.md` decides *which* counter answers your question; this file is *how* to read each one on macOS. It does not re-teach the method and it does not judge the numbers — every value here gets its ignore / investigate / dominant band from `../diagnose/calibration-tables.md`. Linux is `linux.md`; production and distributed observability is `prod-distributed.md`.

One toolchain covers most of the ground: **Instruments**, Apple's tracing GUI, plus **xctrace**, its command-line front-end. Around it sit a handful of focused CLIs — `powermetrics` for energy, the `dtrace` family for syscalls and ad-hoc tracing, and `vm_stat` / `fs_usage` for memory and filesystem activity. Read the "Gaps versus Linux" section before you expect this to do everything perf and eBPF do; it does not.

**Managed runtime? Stop here and use a language profiler.** Instruments is native tooling: it profiles the machine code actually executing. For a program running in a managed runtime — Python, the JVM, Node/V8, .NET — a native sampler (Time Profiler, CPU Profiler) lands on interpreter, JIT, and runtime frames, not your source-level functions. A Time Profiler trace of a slow Python function shows the CPython eval loop, not the function. Use the runtime's own profiler (py-spy, cProfile, async-profiler, `node --prof`, dotnet-trace, …); see `../diagnose/per-language.md`. The Instruments path below is for native code (C/C++/Rust/Swift/Obj-C) and for the native layer underneath a runtime.

Prerequisite: `xctrace` ships with the **full Xcode**, not the Command Line Tools. `xcode-select -p` should point inside `Xcode.app`; if it points at `CommandLineTools`, install Xcode and `sudo xcode-select -s /Applications/Xcode.app`.

---

## xctrace: the CLI front-end to Instruments

`xctrace` (the front-end to Instruments since **Xcode 12** (2020), which requires macOS Catalina 10.15.4+, replacing the old `instruments` command) records a `.trace` bundle you can open in the Instruments GUI or export. One command records, three list what is available.

```
xctrace list templates          # the named recording templates
xctrace list instruments        # individual instruments you can compose
xctrace list devices            # attachable devices (this Mac + connected iOS)
```

Recording takes a template and a target. The target is exactly one of: every process, an attach by pid or name, or a launched command.

```
xctrace record --template 'Time Profiler' --all-processes --time-limit 5s --output run.trace
xctrace record --template 'Time Profiler' --attach <pid|name>  --time-limit 5s --output run.trace
xctrace record --template 'Allocations'   --output run.trace --launch -- /path/to/prog arg1 arg2
```

- `--time-limit 5s` bounds the capture; without it, recording runs until you interrupt it. Keep captures short — trace bundles grow fast and the high-fidelity templates (System Trace, Processor Trace) are seconds-only by design.
- `--output run.trace` names the bundle; open it with `open run.trace` or `xed run.trace`.
- `--attach` takes a pid or a process name; `--launch -- <cmd>` starts the process under the recorder so you catch startup. Everything after `--` is the launched command and its arguments, so put `--output` (and every other xctrace option) **before** `--launch --`; a trailing `--output run.trace` would be passed to your program, not to xctrace.

The templates worth knowing, indexed by what they answer:

| Template | Answers |
|---|---|
| **Time Profiler** | where on-CPU time goes (sampled call stacks) — the default flame-graph source |
| **CPU Profiler** | same question, sampled per-CPU by clock (Apple-preferred; see ladder below) |
| **Allocations** | heap allocations by call site, live vs transient, growth over time |
| **Leaks** | unreferenced allocations (leaks) alongside Allocations |
| **System Trace** | syscalls, VM faults, thread state transitions, scheduling — the off-CPU-ish picture |
| **Game Performance** | GPU + Display + Metal Resource + Metal Application together (see GPU below) |
| **Counters** | raw PMU hardware counters (cycles, instructions, cache events) |

---

## CPU profiling: the accuracy ladder

Three on-CPU instruments trade overhead for fidelity. Climb only as far as the question needs.

1. **Time Profiler** — samples the on-CPU thread every **1 ms**. The familiar default: cheap, always available, fine for "which function is hot." Its blind spot is sampling bias on asymmetric Apple silicon (P-cores and E-cores run at different frequencies), where a fixed-time tick can alias.
2. **CPU Profiler** — Apple's current preference. Samples **each CPU independently, driven by that core's clock frequency** rather than a wall-clock tick, so it does not alias against frequency changes on big.LITTLE-style Apple silicon. Prefer it over Time Profiler when the workload spans P- and E-cores or scales across many threads. (Attributed to a recent Apple WWDC session; verify the exact instrument name and session number against your installed Instruments/Xcode before you lean on the label — both have drifted across releases.)
3. **Processor Trace** — on **M4 / A18 and newer**, with Instruments 16.3+, records **every user-space instruction** at roughly **1% overhead**. It is exact, not sampled, so it sees short-lived functions and rare paths a sampler misses — but it can only capture a few seconds per trace because the data rate is enormous. Use it when sampling is too coarse for the hot path you are chasing.

The general rule: start at Time Profiler, move to CPU Profiler when core asymmetry or thread scaling makes the sampler suspect, and reach for Processor Trace only when you need instruction-exact attribution over a short window.

## GPU / Metal

For GPU and Metal work, use the **Game Performance** template, which bundles the GPU, Display, Metal Resource, and Metal Application instruments in one recording. From an app target in Xcode, **Product > Profile (Cmd-I)** launches Instruments with the right template selected. It shows per-frame GPU time, the Display pipeline (where frames miss vsync), Metal resource allocations, and the Metal command stream — the GPU-side analogue of a CPU flame graph.

## powermetrics: per-subsystem energy

`powermetrics` reports power and activity per subsystem (CPU, GPU, Apple Neural Engine, thermal). It needs root.

```
sudo powermetrics                                  # default: every 5000 ms, forever
sudo powermetrics -i 1000 -n 5                     # five samples, 1 s apart
sudo powermetrics -s cpu_power,gpu_power,thermal   # only these samplers
```

- `-i <ms>` sampling interval (default 5000).
- `-n <count>` number of samples (0 = run until interrupted).
- `-s <samplers>` which subsystems: `cpu_power`, `gpu_power`, `ane_power`, `thermal`, `tasks`, `network`, `battery`, `disk`, `interrupts`.

Use it to answer "is this work CPU-, GPU-, or ANE-bound, and is the machine throttling?" The `thermal` sampler reports throttling state — a frequency cap on a hot laptop is a real and easily-missed bottleneck, exactly the "frequency throttling" the diagnose procedure tells you to check explicitly.

## The dtrace family

DTrace underlies the lightweight CLIs and supports ad-hoc tracing. Reach for the canned tool first.

```
sudo dtruss -c -p <pid>          # count syscalls for a process (strace -c analogue)
sudo dtruss -- /path/to/prog     # trace a launched command's syscalls
sample <pid> 5 -mayDie           # sample a running process for 5 s -> text call-tree report
sudo spindump <pid> 5            # sample a hung or system process (the report a hang dialog uses)
sudo dtrace -n 'syscall:::entry /pid==<pid>/ { @[probefunc] = count(); }'   # ad-hoc
```

- `dtruss` is the `strace` analogue: per-syscall tracing, `-c` for a count summary.
- `sample` produces a quick on-CPU call-tree without opening Instruments — good for a fast "what is this stuck process doing right now."
- `spindump` is the tool for a *hung* process; it is what the macOS "application not responding" machinery runs.

**System Integrity Protection (SIP) constrains all of these.** Tracing Apple-shipped binaries (system daemons, framework code) is blocked by default. To trace them you must boot into Recovery OS and run `csrutil enable --without dtrace`, then reboot. Your own binaries trace without this; only Apple-signed targets need the SIP relaxation. Do not disable SIP wholesale on a machine you care about.

## Memory and filesystem CLIs

```
vm_stat 1                        # paging activity each second: free/active/inactive, page-ins/outs
fs_usage -w -f filesys <pid>     # live filesystem + syscall activity for a process
sudo latency                     # scheduling / interrupt latency on the running system
sysctl hw.memsize hw.cachelinesize hw.l1dcachesize hw.l2cachesize hw.perflevel0.physicalcpu
```

- `vm_stat` is the memory-pressure first look: rising page-outs and high "pageins" mean you are spilling, the macOS face of the "memory saturated" USE cell.
- `fs_usage` shows every filesystem operation and syscall a process makes, with timing — the closest thing to a live I/O trace without setting up Instruments.
- `sysctl` exposes the machine facts back-of-envelope work needs: total RAM, cache sizes, and per-perflevel core counts (P-cores under `hw.perflevel0`, E-cores under `hw.perflevel1`). Note `hw.cachelinesize` is **128 bytes on Apple Silicon, not the x86 64** — so false-sharing padding and per-line packing math must use this value (or `std::hardware_destructive_interference_size`), not a hardcoded 64.

## Flame graphs on macOS

There is no `perf script | stackcollapse | flamegraph` pipeline, but you can get the same SVG:

- Record with the **Time Profiler** or **CPU Profiler** template, then convert the `.trace` to folded stacks or pprof with **instrumentsToPprof**, and render with `flamegraph.pl` or `pprof`'s flame view.
- For Rust (and any cargo project), **cargo-instruments** wraps `xctrace` end to end: `cargo instruments -t time --bin <name>` records and opens the trace.
- For a quick, GUI-free graph, `sample <pid>` output can be folded into a flame graph as well.

Reading the result — width is cost, top edge is on-CPU, drill the widest box — is in `../diagnose/profiling.md`, same as on Linux.

---

## Gaps versus Linux

The corpus and the rest of this skill are Linux-centric, and macOS genuinely cannot match it on two fronts: **off-CPU analysis** and **fleet-wide / hardware-counter** work are weaker here. There is **no eBPF**, and there is no easy `perf`-style hardware-counter access by default. Map each common Linux task to its closest macOS route, and know what you are giving up.

| Linux task | macOS route | Honest caveat |
|---|---|---|
| CPU flame graph (`perf record` + flamegraph) | xctrace **Time Profiler** / **CPU Profiler**, convert to folded/pprof | works well; just a different export path |
| Off-CPU profile (eBPF `offcputime`) | Instruments **System Trace** (thread-state + scheduling) | **no direct equivalent.** System Trace shows blocked/waiting states but there is no one-command off-CPU flame graph; you reconstruct it from the trace. This is the biggest gap. |
| Syscall tracing (`strace`, eBPF) | `dtruss` (counts/trace) or `fs_usage` (filesystem-focused) | works, but SIP blocks tracing Apple binaries without `csrutil --without dtrace` |
| Hardware / cache-miss counters (`perf stat -d`) | Instruments **Counters** template, or **Processor Trace** on M4+ | available but GUI-centric; no casual `perf stat` one-liner, and raw PMU access is gated |
| Microarchitectural top-down (`perf stat --topdown`) | **Counters** template with a CPU-specific counter set | no packaged top-down breakdown; you assemble the events yourself |
| System-wide ad-hoc tracing (`bpftrace` one-liners) | `dtrace` one-liners | DTrace is capable but SIP-constrained; the bcc/bpftrace tool catalog has no macOS twin |
| Fleet / always-on profiling | — | not a local concern; for production go to `prod-distributed.md` |

The practical summary: for on-CPU profiling, allocations, GPU/Metal, and energy, the Mac toolchain is excellent and in places (Processor Trace, per-CPU sampling) ahead of stock Linux. For off-CPU "slow but the CPU is idle" analysis and for cheap scriptable hardware counters, Linux is meaningfully better — if that is the question and you have the choice, reproduce it on a Linux host and use `linux.md`.

---

## Where next

| You have… | Go to |
|---|---|
| a program in a managed runtime (Python, JVM, Node, .NET) | `../diagnose/per-language.md` |
| the method (what to measure, how to read a flame graph) | `../diagnose/profiling.md` |
| a counter value, unsure if it's bad | `../diagnose/calibration-tables.md` |
| the locate step and need to pick a lens | `../diagnose/index.md` |
| a Linux host | `linux.md` |
| a production distributed system | `prod-distributed.md` |
