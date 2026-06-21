# 60-second first-response triage

**Status:** READY (drop-in)
**Loaded when:** the very first pass on a (Linux) host that is misbehaving.

This is the fast on-ramp to the **locate** step of the SKILL.md loop. `index.md` step 1 says: if you only have 60 seconds and a Linux host, run this first pass first, then spend your real diagnostic time on whatever it implicates. You are *not* finding root cause here. You are narrowing the problem to a subsystem so the next tool is targeted instead of speculative. The structure follows Brendan Gregg's 60-second checklist (Netflix Tech Blog, 2015; expanded in *Systems Performance*, 2nd ed.), written here for an agent driving a shell.

The whole pass is ten read-only commands in a fixed order, each interpreted by column with concrete thresholds, ending in one structured report whose conclusion is a bottleneck *class* and a single copy-pasteable next step.

> **Scope: Linux host.** This procedure (sysstat tooling, `perf`/eBPF next steps) is Linux-specific. On a macOS / Apple Silicon box — the common case for LOCAL work — the ten commands and the `perf`/`bpftrace` follow-ups do not exist; use the macOS equivalents in `../environment/local-mac.md` instead (`vm_stat`, `iostat`/`fs_usage`, `nettop`, `powermetrics`, Instruments). Numeric thresholds below are x86-oriented; on Apple Silicon the cache line is 128 bytes, not 64 (`sysctl hw.cachelinesize`).

---

## Operating rules

You have shell access on the affected host. Run the ten commands below **in order**. Each is fast: a single snapshot, or a brief 3–5 second window for the `1`-interval (per-second) ones. The whole pass completes inside a minute.

- **Read-only.** Run nothing that changes system state. No restarts, no `kill`, no config writes, no package installs.
- **Tolerate missing tools.** `sysstat` (`mpstat`, `pidstat`, `iostat`, `sar`) may be absent on minimal images. If a command fails, note it and continue. Do not install packages.
- **Note privilege limits.** `dmesg` may require root on hardened kernels. If denied, say so rather than guessing.
- **Sample once, not in a loop.** For the `1`-interval commands, capture one interval (or a 3–5 s window) and stop. The point is a snapshot, not monitoring.
- **If output was pasted instead of shell granted,** parse what is provided and explicitly list which checklist commands are missing from the paste.

---

## The checklist

### 1. `uptime`
Three load averages: 1, 5, 15 minutes. The *trend* matters more than the absolute number.
- 1-min much higher than 15-min → load rising; the incident is currently arriving.
- 1-min much lower than 15-min → load falling; incident may be resolving.
- All three high and similar → sustained load.
- High load with low CPU usage usually means processes blocked in uninterruptible sleep (D-state, typically I/O wait).

### 2. `dmesg -T | tail`
Recent kernel ring-buffer messages. Any hit here localizes the problem and short-circuits the rest of the checklist. Scan for:
- **OOM killer** (`Out of memory: Killed process …`)
- **Disk errors** (`I/O error`, `ata`, `nvme`, `medium error`)
- **Filesystem errors** (`EXT4-fs error`, `XFS: …`)
- **Network/NIC events** (link up/down flaps, driver resets)
- **Hardware events** (MCE, thermal throttling, ECC)
- **TCP/socket pressure** (`TCP: out of memory`, `nf_conntrack: table full`)

### 3. `vmstat -SM 1` (a few seconds)
System-wide snapshot in megabytes.
- `r` (run queue): sustained value greater than CPU count → CPU saturation.
- `b` (blocked on I/O): persistent non-zero → I/O wait.
- `si` / `so` (swap in / out): non-zero with active page-in/out → memory pressure plus swap activity (bad).
- `us` / `sy` / `id` / `wa` / `st` CPU breakdown: high `wa` → I/O-bound; high `sy` → kernel-heavy (syscalls, locks, network stack); high `st` → hypervisor stealing cycles (noisy neighbor on a VM).
- `free` / `buff` / `cache`: idle memory vs page cache (page cache is good, not waste).

### 4. `mpstat -P ALL 1` (a few seconds)
Per-CPU breakdown. Reveals patterns invisible to system-wide aggregates.
- One CPU at 100% while others idle → single-threaded bottleneck (or interrupt pinned to one core).
- All CPUs evenly loaded → parallel work; if it isn't scaling, suspect memory bandwidth or coherence.
- High `%irq` / `%soft` concentrated on one CPU → interrupt steering issue (check `/proc/interrupts`, `irqbalance`).
- Non-trivial `%steal` on any CPU (VM only) → hypervisor contention.

### 5. `pidstat 1` (a few seconds)
Per-process CPU, sampled each second. Better than a `top` snapshot for catching bursty processes.
- Unexpected processes burning CPU.
- User vs system time per process: a userland app showing high `%system` often means syscall storms or kernel-side contention.
- Kernel threads (`kworker`, `ksoftirqd`, `migration`) at the top → kernel-side work dominating.

### 6. `iostat -sxz 1` (a few seconds)
Per-device disk stats, idle devices skipped. (The extended columns below come from `-x`; `-z` skips idle devices. If `-s` is rejected by your sysstat version, drop it — `iostat -xz 1` produces the same columns. `aqu-sz` is the recent-sysstat name; older releases call it `avgqu-sz`.)
- `r/s`, `w/s`: IOPS. `rMB/s`, `wMB/s`: throughput.
- `await` / `r_await` / `w_await`: average completion time including queue. Compare to device class: NVMe ~0.05–0.5 ms, SATA SSD ~0.2–1 ms, HDD ~5–20 ms.
- `aqu-sz`: average queue depth. Sustained high depth with high `await` → device overwhelmed.
- `%util`: fraction of time the device had ≥1 outstanding request. Above ~80% suggests saturation on single-queue devices; less informative on multi-queue NVMe, which can have many requests in flight without being saturated.

### 7. `free -m`
Memory in megabytes. Read three things.
- **`available`** (not `free`): the kernel's estimate of memory reclaimable for new allocations without swapping. This is the number that matters.
- **`Swap used`**: any non-zero deserves a glance. Cross-reference vmstat's `si`/`so` — used swap with no current swap I/O is mostly inert; used swap with active swap I/O is bad.
- **`buff/cache`**: filesystem cache. Large values are normal and healthy.

### 8. `sar -n DEV,EDEV 1` (a few seconds)
Per-interface network throughput (`DEV`) and error/drop counters (`EDEV`). The error/drop columns live in `EDEV`; `sar -n DEV` alone reports only throughput/packet rates.
- Saturation against link rate (1 GbE ≈ 125 MB/s ≈ 128000 kB/s, 10 GbE ≈ 1.25 GB/s, 25 GbE ≈ 3.1 GB/s). Note `sar` reports `rxkB/s`/`txkB/s` in kB/s, so convert before comparing.
- Packet rate vs throughput: many small packets stress the CPU/kernel more than fewer large ones.
- Errors / drops (`rxerr/s`, `txerr/s`, `rxdrop/s`, `txdrop/s`, from `EDEV`): non-zero is suspicious.

### 9. `sar -n TCP,ETCP 1` (a few seconds)
TCP-level statistics.
- `active/s`, `passive/s`: outbound and inbound connection establishment rates — context for what the workload is doing.
- `retrans/s`: retransmissions. Sustained non-zero indicates loss somewhere (network path, peer overload, or local TX/RX buffer pressure).
- `iseg/s`, `oseg/s`: total segments — needed to put `retrans/s` in proportion (retrans as a fraction of segments beats the raw count).

### 10. `top` (one screen, then quit)
Final sanity check. Confirms the picture from the previous nine and surfaces anything missed: a runaway process, a kernel thread eating CPU, unexpected memory growth, an unfamiliar process name.

---

## The triage report

Produce a single report in this shape. The conclusion is a bottleneck *class* plus one concrete next step, which is exactly the handoff `index.md` expects.

```
## Triage summary
<one sentence: subsystem implicated and severity, or "no anomaly detected">

## Findings
- CPU: <observation with the specific number that drove it, or "no anomaly">
- Memory: <...>
- Disk: <...>
- Network: <...>
- Kernel: <dmesg findings, or "no recent kernel events">

## Most likely bottleneck class
<one of: cpu-saturation, cpu-imbalance, memory-pressure, swap-thrashing,
disk-io-bound, network-saturation, kernel-error, hypervisor-contention,
no-anomaly-detected, mixed (specify)>

## Recommended next step
<a single concrete command or methodology, with one-sentence rationale.
Examples:
- "Run `perf stat --topdown -a sleep 10` to attribute the saturated CPU
  cycles to retiring / bad speculation / front-end / back-end."
- "Capture a 30s flame graph: `perf record -F 99 -ag -- sleep 30 &&
  perf script | flamegraph.pl > flame.svg` to localize the hot path."
- "Investigate the OOM event: `journalctl -k --since '1 hour ago' |
  grep -iE 'oom|kill'` to identify the killed process and its peak RSS."
- "Diagnose retrans source with `ss -tin` per-socket and `tcpdump` on
  the affected interface."
- "Apply the USE method per resource (brendangregg.com/usemethod.html) —
  the fast-path metrics are clean, so the next step is structured
  per-resource interrogation.">
```

### Rules for the report
- **Cite the number.** For each anomaly, include the observed value and the threshold or normal range you compared against. "Run queue of 47 on a 16-CPU box" beats "high run queue." The bands to compare against live in `calibration-tables.md`.
- **No speculation past the data.** If `%steal` is high, say "hypervisor contention is the likely cause." Do not name the noisy neighbor you cannot see.
- **A clean pass is a result.** "No obvious bottleneck in the fast-path metrics" is a valid conclusion. It points away from steady-state CPU/IO/memory and toward latency tails, application-level profiling, or transient events outside the sample window.
- **Hand off cleanly.** The next step must be specific enough to copy-paste. Vague advice ("look into memory") is not a recommendation.

---

## What this pass misses

The checklist is biased toward steady-state, machine-wide issues. It is weak on, and will not catch:

- **Tail latency** — a 5 ms p99 spike every 30 s does not show up in a 5 s aggregate.
- **GC pauses** in managed runtimes — use the runtime's own logs (`per-language.md`).
- **Lock contention** in user code — needs `perf lock` or `bpftrace`.
- **Cache / TLB / branch-prediction** issues — need `perf stat` with counter events (`profiling.md`, `../orient/bound-types.md`).
- **False sharing** — needs `perf c2c`.

If the symptom description points at one of these, say the 60-second pass may be insufficient and recommend the deeper tool directly rather than reporting a clean steady-state result as the answer.

The deeper tools named above (`perf lock`, `bpftrace`, `perf stat`, `perf c2c`) are Linux-only. On macOS / Apple Silicon, reach for Instruments, `dtrace`, or `powermetrics` per `../environment/local-mac.md`; and for false-sharing/cache reasoning use `std::hardware_destructive_interference_size` (or `sysctl hw.cachelinesize` → 128 on Apple Silicon) rather than assuming a 64-byte line.

---

## Worked example

Symptom: a service's p99 latency doubled an hour ago. Running the pass:

- `uptime`: `load average: 38.2, 31.0, 18.4` on a 16-CPU box → 1-min well above 15-min, load rising and already past CPU count.
- `dmesg -T | tail`: nothing relevant.
- `vmstat -SM 1`: `r` hovering at 35–40, `wa` ~1%, `si`/`so` zero, `sy` ~12%, `st` 0.
- `mpstat -P ALL 1`: all 16 CPUs at 90–100% `%usr`, evenly loaded, no `%steal`.
- `pidstat 1`: one application process accounts for ~1500% CPU (15 cores); no kernel threads near the top.
- `iostat -sxz 1`, `free -m`, `sar -n DEV/TCP`: all unremarkable — `available` healthy, `await` sub-millisecond, no retrans.
- `top`: confirms the single process pegging the box.

Report conclusion: bottleneck class **cpu-saturation** (run queue ~38 on 16 CPUs, all cores at ~95% user, one process consuming 15 cores). Disk, memory, and network are clean. Recommended next step: `perf stat --topdown -a sleep 10` to attribute the saturated cycles, then a 30 s flame graph to localize the hot path. That feeds straight into `index.md` step 2 (characterize the workload) with the lens already narrowed to on-CPU work — no time wasted on the I/O or network branches the pass ruled out.

---

## Where next

| After the pass… | Go to |
|---|---|
| a counter and you don't know if it's bad | `calibration-tables.md` |
| full locate procedure (USE/RED, load vs architecture) | `index.md` |
| deeper Linux tooling beyond the ten commands | `../environment/linux.md` |
| need to see where time/cycles actually go | `profiling.md`, `per-language.md` |
| unsure what *kind* of bound it is | `../orient/bound-types.md` |
