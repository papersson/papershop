# Per-language profilers

**Status:** READY
**Loaded when:** profiling a specific language runtime.

This specializes `profiling.md` to managed and native runtimes. The method does not change: decide on-CPU vs off-CPU, default to sampling, collect stacks at an off-round frequency, then cross-check the hot spot against counters before believing the cause. (The off-round frequency rule bites only where you set the rate yourself, i.e. the perf path below — most managed profilers fix it for you, e.g. Go's CPU profiler at 100 Hz.) What changes per runtime is *which* tool gives you stacks, whether it attaches to a live process without a restart, and what it costs in production. This file is the lookup for that. The OS-level instruments several of these wrap (perf, eBPF) are Linux-only and live in `../environment/linux.md`; on local macOS / Apple Silicon those have no direct equivalent — use Instruments/`xctrace`/`dtrace` per `../environment/local-mac.md` instead. The language-agnostic reading guide is `profiling.md`.

One distinction runs through everything below, because it decides whether a tool is usable on a box that is currently on fire:

- **Attach-without-restart, production-safe:** Go pprof endpoints, async-profiler, py-spy, JFR. You point them at a running PID (or scrape an HTTP endpoint) and get a profile with no redeploy and bounded overhead.
- **Dev-only / restart-required:** cProfile, scalene, memray, `node --prof`, clinic.js. These wrap the process at launch or add per-call instrumentation overhead too high to leave on in production.

When sampling a production fleet, profile random replicas one at a time, never the whole fleet at once.

---

## Go

`runtime/pprof` (in-process) and `net/http/pprof` (HTTP endpoints) are the standard. Import `net/http/pprof` for its side effect and you expose `/debug/pprof/` on your server; everything below scrapes a **live process without restart**.

| Profile | Endpoint / call | Notes |
|---|---|---|
| CPU | `/debug/pprof/profile?seconds=30` | sampling, ~100 Hz; measurable overhead while running |
| Heap (in-use + alloc) | `/debug/pprof/heap` | sampled allocations, cheap |
| Goroutine | `/debug/pprof/goroutine` | every goroutine's stack; finds leaks and blocked fan-out; briefly stops the world — costly with very large goroutine counts |
| Threadcreate | `/debug/pprof/threadcreate` | OS threads created |
| Block | `/debug/pprof/block` | **off by default**; enable with `runtime.SetBlockProfileRate(n)` |
| Mutex | `/debug/pprof/mutex` | **off by default**; enable with `runtime.SetMutexProfileFraction(n)` |

```
# CPU profile a live server for 30s, open interactive pprof
go tool pprof http://host:6060/debug/pprof/profile?seconds=30
go tool pprof http://host:6060/debug/pprof/heap        # heap snapshot
(pprof) top / list <func> / web / weblist <func>       # text / source / graph / annotated source
go tool pprof -http=:8080 profile.pb.gz                # browser UI with flame graph
```

`go tool pprof` renders text, callgraph, flame graph, and `weblist` (per-line source attribution). Block and mutex profiling are off by default because they cost; turn them on (a fraction, not every event) only while chasing contention, then off again.

Execution tracer — orthogonal to pprof, captures scheduling, GC, syscalls, and goroutine transitions over a window:

```
curl -o trace.out http://host:6060/debug/pprof/trace?seconds=5
go tool trace trace.out        # timeline, per-goroutine, GC and scheduler latency
```

Use pprof CPU for "where do cycles go," the tracer for "why is this goroutine waiting / why are pauses lumpy."

GC tuning: `GOGC` (default 100) sets heap growth between collections — doubling it roughly doubles heap and roughly halves GC CPU; `GOGC=off` disables GC. `GOMEMLIMIT` sets a soft total-memory ceiling the runtime collects harder to stay under; pair it with a high `GOGC` to get "collect lazily but never exceed N."

**Production-safe, attach-without-restart.** CPU profiling adds real overhead, so profile one replica at a time.

## JVM

Two complementary tools, both **attach to a running JVM**.

**async-profiler** — low-overhead sampling via `AsyncGetCallTrace` + `perf_events`, so it captures stacks **without safepoint bias** (the trap in `profiling.md` where safepoint-only profilers over-attribute to methods near safepoints). Attaches by PID; profiles CPU, allocations, locks, and wall-clock; emits flame graphs directly.

```
./asprof -d 30 -e cpu -f cpu.html <pid>     # 30s CPU flame graph of a live JVM
./asprof -d 30 -e alloc -f alloc.html <pid> # allocation profile
./asprof -e wall -d 30 -f wall.html <pid>   # wall-clock (catches off-CPU waits)
./asprof -e lock -d 30 -f lock.html <pid>   # lock contention
```

**JFR (JDK Flight Recorder)** — the built-in, always-on production recorder. Two templates: `default.jfc` (low overhead, leave it running) and `profile.jfc` (richer, more overhead). Controlled live with `jcmd`, viewed in JDK Mission Control.

```
jcmd <pid> JFR.start name=rec settings=profile duration=60s filename=rec.jfr
jcmd <pid> JFR.dump name=rec filename=snapshot.jfr     # dump without stopping
jcmd <pid> JFR.stop name=rec
```

Reach for async-profiler when you want a flame graph now and accurate stacks; reach for JFR when you want a continuous, low-overhead recording of GC, allocation, threads, and JIT that is already running when an incident starts. Both are **production-safe, attach-without-restart.** For GC itself, also enable unified GC logging (`-Xlog:gc*`) and read pauses against the tail in `index.md`.

## Python

| Tool | Kind | Attach live? | Use |
|---|---|---|---|
| **py-spy** | sampling (Rust, out-of-process) | **yes, by PID** | production-safe CPU profiling, no code change |
| cProfile | instrumenting (stdlib, deterministic) | no, wraps the run | exact call counts, **dev-only** (high overhead) |
| scalene | sampling, line-level | no, launches the script | CPU + GPU + memory together |
| memray | allocation tracing | mostly no (launches/wraps); `memray attach <pid>` exists (experimental, needs a debugger) | who allocated what, leaks, peak memory |

py-spy reads another process's stacks from outside it, so there is **no instrumentation in the target and no restart**:

```
py-spy top --pid <pid>                       # live top-like view of hot Python frames
py-spy record -o out.svg --pid <pid>         # sampled flame graph of a running process
py-spy dump --pid <pid>                       # one-shot stack dump of every thread
```

cProfile is deterministic and gives exact call counts and per-call time, but it instruments every call — its overhead distorts hot tiny functions (the observer effect from `profiling.md`) and it is **dev-only**:

```
python -m cProfile -o out.prof script.py
python -c "import pstats; pstats.Stats('out.prof').sort_stats('cumulative').print_stats(20)"
```

scalene (`scalene script.py`) separates Python from native time and attributes CPU/GPU/memory per line; memray (`memray run script.py` then `memray flamegraph out.bin`) is the allocation/leak profiler. Use py-spy first in production; reach for the others in development when you need counts, line detail, or memory attribution.

## Rust / C / C++

Native code has no runtime to query, so you profile it with the OS sampler. On Linux that is `perf` (`../environment/linux.md`); on local macOS / Apple Silicon `perf` does not exist — use Instruments / `xctrace` (Time Profiler) or `dtrace`, see `../environment/local-mac.md`. `cargo-flamegraph` wraps perf into one step for Rust (and any binary):

```
cargo flamegraph --bin myapp -- <args>       # builds, runs under perf, writes flamegraph.svg
perf record -F 99 -g ./myapp && perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg
```

Build with frame pointers or debug info (`debug = true` / `-g`) or the stacks collapse to a flat list. For cache and memory behavior, `valgrind --tool=cachegrind` (and `callgrind`) simulate the cache hierarchy and give exact miss counts — slow (~20-100x, callgrind with cache sim at the high end), instrumenting, **dev-only**, but precise where sampling counters are coarse. Sampling (perf) is the default; cachegrind is the deep zoom when you need exact miss attribution per line. None of these attach to a running native process the way the managed tools do; you launch the binary under the profiler.

## Node.js / V8

```
node --prof app.js                 # V8 writes isolate-*.log (tick samples)
node --prof-process isolate-*.log  # human-readable summary (JS vs C++ vs GC time)
node --inspect app.js              # attach Chrome DevTools / chrome://inspect for CPU + heap
clinic doctor -- node app.js       # diagnose; clinic flame / bubbleprof for flame graphs
```

`--prof` is the built-in sampling profiler; `--prof-process` splits time across JS, native, and GC. The DevTools inspector (`--inspect`) gives an interactive CPU profiler and heap snapshots and **can attach to an already-running process** if started with the inspector enabled. clinic.js is the higher-level workflow (doctor for triage, flame for flame graphs, bubbleprof for async). Treat these as **dev / staging** tools; leaving the inspector open in production is not safe.

## .NET

Cross-platform CLI tools that **attach to a running process by PID**:

```
dotnet-counters monitor -p <pid>                         # live counters: GC, alloc rate, thread pool, exceptions
dotnet-trace collect -p <pid> --duration 00:00:30        # sampled trace -> .nettrace (open in PerfView / Speedscope)
dotnet-gcdump collect -p <pid>                           # managed heap snapshot for leak analysis
```

`dotnet-counters` is the cheap always-watchable dashboard (start here); `dotnet-trace` captures CPU/allocation samples for offline flame graphs; `dotnet-gcdump` snapshots the managed heap to find what is retained. The trace tools are low-overhead sampling and reasonable in production for a bounded window; gcdump briefly pauses to walk the heap.

---

## Where next

| You have… | Go to |
|---|---|
| the method behind these tools (on/off-CPU, sample vs instrument, reading flame graphs) | `profiling.md` |
| picked a runtime, now picking the dominant bottleneck | `index.md` (step 3) |
| a counter value and don't know if it's bad | `calibration-tables.md` |
| native code, or need the raw perf / eBPF / off-CPU commands (Linux) | `../environment/linux.md` |
| profiling locally on macOS / Apple Silicon (Instruments, xctrace, dtrace — the macOS stand-in for perf/eBPF) | `../environment/local-mac.md` |
| measurement harness, benchmarking, statistics | `../measure/tools.md` |
| only 60 seconds on a Linux host | `triage-60s.md` |
