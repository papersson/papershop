# Prod / distributed: telemetry-first

**Status:** READY
**Loaded when:** the target is a production distributed system.

This is the environment leaf for the world where you usually *cannot* attach a profiler. On a
local host you reach for the instrument first (`local-mac.md`, `linux.md`); in production the order
inverts. You diagnose only what your telemetry already captured, so the observability has to be in
place *before* the incident, not bolted on during it. That is the telemetry-first stance, and it is
the prod half of SKILL.md's local-vs-prod decision.

The second fact that shapes everything here: in a distributed system the bottleneck is usually
*between* services, not inside one. A request fans out across tiers, and the time that hurts is
spent waiting on a downstream, queueing at a hop, or amplified by retries. A flame graph of one
process cannot see that. So the prod toolchain is built to attribute latency *across* the request
path first, then zoom into a single service only once you have localized to it.

Three pillars do this, each answering a different question:

| Pillar | Question | Granularity | Tools |
|---|---|---|---|
| Metrics (RED / USE) | *which service or resource is unhealthy?* | aggregate, per service/resource | Prometheus, Grafana |
| Distributed tracing | *which hop in this request is slow?* | per request, cross-service | OpenTelemetry, Jaeger, Tempo |
| Continuous profiling | *which line of code burns the time?* | per function, fleet-wide | Parca, Pyroscope, eBPF profilers |

They compose top-down: metrics localize to a service, traces localize to a hop, profiling
localizes to code. The "how to localize a prod problem" workflow below is just walking that ladder.

---

## Pillar 1 — Metrics: RED and USE

The two methods from `../diagnose/index.md` are how you instrument, not just how you think. Expose
both as metrics on every deploy.

- **RED for every service** on the request path: **R**ate (requests/sec), **E**rrors (failed
  requests/sec, and the retries they spawn), **D**uration (the latency *distribution*, never the
  mean). Service-centric; this is what tells you which tier is unhealthy.
- **USE for every resource** a service consumes: **U**tilization, **S**aturation (the queue depth —
  the real signal), **E**rrors. Resource-centric; this is what explains *why* a tier is unhealthy
  once you are on its host.

**Implement Duration as a histogram, not a summary.** Prometheus offers both; the difference
decides whether your fleet-wide p99 is real. A histogram ships bucket counts (`..._bucket{le=...}`);
a summary ships pre-computed quantiles per instance. Quantiles cannot be averaged — the p99 of ten
instances is not the mean of their ten p99s — so summary quantiles are useless the moment you
aggregate across replicas. Histogram buckets *add* correctly across instances, so you compute the
quantile server-side at query time over the whole fleet:

```promql
histogram_quantile(0.99,
  sum(rate(request_duration_seconds_bucket[5m])) by (le))
```

This is the one query to internalize: `rate()` over the bucket counters, `sum by (le)` to fold all
instances into one set of buckets, `histogram_quantile` to read the percentile off the merged
distribution. Choose bucket boundaries to straddle your SLO (a 50 ms target wants buckets near
25/50/75/100 ms), because the quantile is interpolated within a bucket and is only as precise as the
buckets are dense there.

**Recording and alerting rules.** Precompute hot expressions as recording rules so dashboards and
alerts read a cheap series instead of re-aggregating raw buckets every refresh. Alert on symptoms
the user feels — p99 over SLO, error-rate over budget, saturation climbing — not on causes like CPU%,
which is a poor proxy (see the tail section). Burn-rate alerts on an error/latency SLO budget beat
static thresholds: they fire fast on a sharp regression and slowly on a gradual one.

## Pillar 2 — Distributed tracing

Tracing is the only pillar that attributes latency *across* services, so it is the one that finds
the slow hop. A **trace** is one request's journey; it is a tree of **spans**, each span a timed
unit of work (an RPC, a DB query, a handler) carrying a parent link, start/end timestamps, and
attributes. Reading the span tree, you see exactly where the end-to-end budget went: a wide span is
time spent, a gap between a parent and its child is queueing or network, a fan-out of sibling spans
shows parallel calls and which straggler the parent waited on.

**OpenTelemetry (OTel) is the vendor-neutral standard** for producing this data. Instrument
services with the OTel SDKs (auto-instrumentation covers common HTTP/gRPC/DB libraries with little
code), emit spans via OTLP, and run them through the **OTel Collector** — a pipeline of receivers →
processors → exporters that batches, enriches, samples, and fans out to a backend without coupling
your services to a vendor. Store and query in **Jaeger** or **Grafana Tempo** (Tempo is
cheap object-storage-backed and pairs with the Prometheus/Grafana stack). Propagate context across
hops (W3C `traceparent` header) or the trace breaks at the first uninstrumented boundary.

**Sampling — you cannot keep every trace at volume.** Two strategies, different tradeoffs:

- **Head sampling**: decide at the start of the trace, from the trace ID, whether to keep it.
  Cheap and stateless, every service makes the same deterministic choice, but it is *blind to how
  the trace turns out* — it cannot preferentially keep the slow or failed ones because it decides
  before they happen.
- **Tail sampling**: buffer the trace's spans and decide once it completes, when you can see the
  whole thing. Costs memory and a stateful collector, but lets you **always keep what matters**:
  100% of error traces, 100% of traces over a latency threshold, and a small percentage of the
  normal ones for baseline.

A workable default: tail-sample to keep all errors and all slow traces, plus ~1% of the rest. One
percent of high-volume traffic is a statistically ample picture of the *normal* path, while the
all-errors / all-slow rule guarantees the pathological traces — the ones you actually open during an
incident — are never the ones you threw away.

## Pillar 3 — Continuous profiling in production

Once tracing names the slow service, you still need the slow *code*, and in prod you cannot stop to
attach `perf`. Continuous profiling solves this: a low-overhead sampler runs on every host all the
time, collecting stacks and storing them so you can pull a flame graph for any service over any past
window — line-level attribution with no code instrumentation and no redeploy.

It works because profiling is sampling, and sampling can be made nearly free. **Google-Wide
Profiling (GWP)** is the foundational fleet-wide system and the proof of concept: two-dimensional
sampling — sample a few machines at any moment, and sample lightly on each — gives a fleet-accurate
profile at **<0.01% aggregate overhead**. The modern open tools follow this model:

- **Parca** and **Grafana Pyroscope** — continuous-profiling backends that store stacks over time
  and render flame graphs across the fleet, queryable by service and version.
- **eBPF-based whole-fleet profilers** (the OpenTelemetry eBPF profiler, Parca's eBPF agent) sample
  stacks in the kernel with no per-app agent and no recompilation, across every language at once.
  This is the fleet-wide reappearance of the eBPF profilers from `linux.md`: the same `profile`/
  stack-sampling mechanism, run continuously over every host instead of once on one box.

Typical overhead is ~2–5% for periodic sampling, often **<1% with eBPF**. That is cheap enough to
leave on permanently, which is the whole point: when an incident starts you already have the profile
for the bad window and the good window, and the diff between them is the regression.

---

## How to localize a prod problem

The pillars compose into one descent. Each step narrows the search and hands a concrete target to
the next; do not skip down the ladder, because guessing at code before you have localized the tier
is how you profile a service that was only ever waiting on a downstream.

1. **RED dashboards → the slow service.** Start at the end-to-end SLO. Walk the per-service RED
   panels and find the tier where Duration dominates the end-to-end budget or Errors spike. This is
   the RED method from `../diagnose/index.md` read off a dashboard.
2. **Traces → the slow hop.** Open traces for the slow/failed requests (tail sampling kept them on
   purpose). Read the span tree of that service: which child span is wide, where is the gap, which
   downstream fan-out did it wait on. Now you know the exact operation, not just the service.
3. **Continuous profiling / eBPF → the slow code.** If the wide span is *in-service* compute, pull
   the flame graph for that service over the bad window and diff it against a healthy window. The
   widened tower is the function that regressed.
4. **USE on that host → the binding resource.** If the wide span is *waiting* (the service is slow
   but not burning CPU), the bottleneck is a resource, not code. Run USE on that node: which
   resource is *saturated* (queueing), not merely utilized. Off-CPU analysis and the per-resource
   commands live in `linux.md`.

The hand-off between steps 1–2 and 3–4 is the same RED→USE hand-off as single-host diagnosis, just
spread across a fleet: RED/traces localize to a tier and an operation, USE/profiling explain it.
The bottleneck being *between* services means you usually spend most of your time in steps 1–2.

---

## The methodology: "The Tail at Scale"

Everything above serves one hard truth from Dean & Barroso's *The Tail at Scale*: **at scale, tail
latency dominates end-to-end performance.** The arithmetic is brutal. If a request fans out to 100
leaf servers and waits for all of them, then a per-server p99 of 1 s means roughly `1 − 0.99^100 ≈
63%` of user requests wait on at least one slow leaf. A rare slowdown on one server becomes the
common case for the user. This is why a healthy-looking mean or even p99 *per service* can sit under
a miserable end-to-end experience, and why you instrument distributions, not averages.

Three consequences:

- **Engineer for tail tolerance, not just tail reduction.** You cannot eliminate variability at
  scale (shared resources, background tasks, queueing, GC, maintenance all guarantee it), so build
  systems that tolerate it. The signature technique is **hedged / backup requests**: send the
  request to a second replica if the first has not answered by, say, the 95th-percentile latency,
  take whichever returns first, cancel the other. A tiny extra load (you only hedge the slow few
  percent) collapses the tail, because the odds of *both* replicas being slow are the square of one
  being slow. Related moves: tied requests, micro-partitioning for faster rebalancing, and putting
  slow background work on a leash.
- **Measure the tail correctly or you are tuning a fiction.** The dominant measurement bug here is
  **coordinated omission** (Gil Tene): a closed-loop client that waits for a response before sending
  the next *does not issue* the requests it would have sent during a stall, so the stall is
  under-sampled and the reported p99 is a lie. Drive load open-loop, record latency from *intended*
  send time, and aggregate with a tool built for it (HdrHistogram for lossless percentiles, wrk2 /
  vegeta / k6 for open-loop generation). The full treatment of coordinated omission, tail CIs, and
  why a median's interval must never band a p99 is in `../measure/measurement-integrity.md`.
- **Telemetry is the prerequisite, not the afterthought.** You can only engineer a tail you can
  see. The histograms, traces, and profiles above are what make the tail visible per service, per
  hop, and per line; without them, "tail tolerance" is guesswork.

---

## Where next

| You have… | Go to |
|---|---|
| RED/USE as diagnostic *methods*, and the RED→USE hand-off | `../diagnose/index.md` |
| a tier localized, now read the host's resources | `linux.md` (eBPF, off-CPU, perf) |
| tails, coordinated omission, the right CI for a percentile | `../measure/measurement-integrity.md` |
| to size the fleet / find the scaling knee before it bends | `../design-and-lifecycle/capacity-scalability.md` |
| a Mac or single local process instead | `local-mac.md` |
