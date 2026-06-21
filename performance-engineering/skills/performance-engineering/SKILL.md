---
name: performance-engineering
description: >
  Make software faster, prove it, and keep it fast — a performance-engineering router. Use when
  the user wants to know why something is slow, make a specific thing faster, decide whether it's
  fast enough, benchmark or compare alternatives, design a system to be fast by construction, plan
  capacity ("will it scale?"), or stop performance from regressing. Covers local single-machine
  work (often macOS) and production distributed systems (Linux, telemetry-first). NOT for
  "just make it fast" on speculation — it gates on whether the work is warranted, insists on
  measuring before changing, and loads deep modules only on demand.
---

# Performance engineering

This file is a router. It holds the orientation and the loop you always need, and points to deep
modules you load only when the task reaches them. Read this, orient, then descend one branch.

## Gate — do you even need this?

Most code does not need optimizing. Before anything:

- Is a real target being missed — a budget, an SLO, a user complaint, a cost line? If not, stop.
  Say so and don't optimize on speculation (Knuth's "97% of the time" caution).
- "Make it fast" with no number is not a task. Get or set the target first
  (→ `modules/design-and-lifecycle/budgets-slos.md`).

## Orient first — two questions before you touch a tool

**1. Where on the stack could it be?** Performance lives somewhere specific. Place the hypothesis
on the map before measuring:

```
single machine:  application → your libraries → system calls → kernel
                  (scheduler · filesystem · network · virtual memory) → hardware
distributed:      which service / tier — app server · database · queue · cache ·
                  and the network between them
```

You won't know yet, and that's fine — the discipline is to measure your way *down* the stack, not
to guess. Deep: `modules/orient/software-stack.md`, `modules/orient/bound-types.md`.

**2. Where are you — local or prod?** This decides your tools and your prerequisites:

- **LOCAL** (your machine, often macOS, a single process): attach a profiler directly; reproduce
  and iterate in seconds. Caveats: no Linux `perf`/eBPF, and your laptop is not prod hardware.
  → `modules/environment/local-mac.md` (and for a managed runtime — Python, JVM, Node, .NET —
  the profiler is language-specific: `modules/diagnose/per-language.md`)
- **PROD** (distributed, Linux, customer-facing): you usually cannot just attach a profiler. You
  need telemetry **first** — metrics, distributed tracing, continuous profiling — to learn which
  service is slow; the bottleneck is often *between* services, not inside one. eBPF shines here.
  → `modules/environment/prod-distributed.md`, then `modules/environment/linux.md`

Establish both before picking an instrument.

## The loop

All reactive work runs the same loop. Don't skip steps:

1. **Target** — what "fast enough" means, as a number.
2. **Measure** — observe reality; never guess (→ `modules/measure/`, `modules/environment/`).
3. **Locate** — find the dominant bottleneck on the stack (→ `modules/diagnose/`).
4. **Fix** — pull the biggest lever, in order (→ `modules/optimize/`).
5. **Prove** — faster AND still correct, and the gain is real, not noise (→ `modules/measure/verify.md`).
6. **Defend** — keep it from regressing (→ `modules/design-and-lifecycle/regression-ci.md`).
   Diagnosing a regression that *already happened* is a different task → `modules/diagnose/regression-incident.md`.

Proactive work (design, capacity, budgets) is the same discipline applied *before* the slowdown
exists (→ `modules/design-and-lifecycle/`).

## Measurement integrity — non-negotiable in every branch

Violating these produces confident wrong answers:

- Measure before you change, and after. Intuition about what's slow is usually wrong.
- Discard warmup; the first runs are not representative.
- One run is noise — look at a distribution over many runs.
- Pick the right statistic: median over mean for typical cost; for anything user-facing the **tail**
  (p99) is what hurts, banded with its *own* interval, not the median's.
- Know what your metric is: throughput is a ratio of totals, not an average of per-window rates.
- Keep correctness: a fast wrong answer is not an optimization.

Deep: `modules/measure/measurement-integrity.md`.

## Router — intent → branch

| You want to… | Go to |
|---|---|
| understand the terrain / vocabulary | `modules/orient/` |
| find why something is slow | `modules/diagnose/` |
| measure, benchmark, or prove a change | `modules/measure/` |
| apply a fix / choose the lever | `modules/optimize/` |
| design for speed, plan capacity, or set/defend a budget | `modules/design-and-lifecycle/` |
| pick the right tool for your machine or your prod system | `modules/environment/` |

## Branch index

- `modules/orient/` — mental models: the stack as a where-map, the work taxonomy, latency numbers, bound types.
- `modules/diagnose/` — find the bottleneck: USE/RED, the 60-second triage, calibration tables, profiling.
- `modules/measure/` — honest measurement: benchmarking, the harness, verify faster-and-correct, integrity.
- `modules/optimize/` — the lever hierarchy, intervention catalog, tradeoff knobs.
- `modules/design-and-lifecycle/` — design-for-performance, latency hiding, budgets/SLOs, capacity & scalability, regression CI.
- `modules/environment/` — instruments indexed by where you are: local (macOS), Linux (`perf`/eBPF), prod/distributed (telemetry).
