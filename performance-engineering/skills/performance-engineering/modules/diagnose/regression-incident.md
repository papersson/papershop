# Diagnosing a live regression

**Status:** READY
**Loaded when:** something got slower (a live regression), and you need to find what changed.

A metric that was fine is now worse: p99 stepped up, throughput stepped down, cost per request crept, a queue that used to drain now grows. Something *changed* and the system degraded after it. This leaf is the playbook for that incident. The job is not "why is this code slow" in the abstract — it is **what made it slower, and when** — and that reframes the whole approach.

> **Not the same as the CI sibling.** `../design-and-lifecycle/regression-ci.md` *prevents* future regressions: it gates commits and watches a benchmark history so "it got slower" becomes a build event. This leaf *diagnoses* one that already escaped — it is live in production (or staging) right now and you are under incident pressure. Prevention runs forever in CI; diagnosis runs once, against a clock. If you came here to set up gates, you want the CI leaf. If the p99 is bad *right now*, stay.

The core move that separates a regression from an ordinary slowdown: **correlate before you profile.** A slowdown with no known onset is the `index.md` job — measure down the stack, find the binding constraint. A regression has a timestamp, and that timestamp is worth more than any flame graph. The fastest path to the cause is usually to line the onset up against what changed in the same window, not to characterize the workload from scratch. Profiling answers *why it is slow*; correlation answers *what made it slower*, and on a regression the second question is both narrower and faster.

---

## Procedure

Run these in order. Don't open a profiler until step 4.

### 1. Pin the onset in time
Find the moment the metric changed level, as precisely as the data allows. Pull the regressed metric (p99, throughput, error rate, cost) on a dashboard over a window wide enough to show both the healthy stretch and the bad one, and locate the **step** — the point where the level shifts and stays shifted. You are looking for a level change, not a single spike; a one-off spike is an event, a sustained step is a regression. Note whether it was a sharp step (points at a discrete change — a deploy, a flag flip) or a gradual ramp (points at something that grows — data volume, a leak, traffic creep). The onset timestamp is the key you will join everything else against.

If you can't see a clean step, widen the window and coarsen the metric (hourly p99 instead of per-minute) until the level change is unambiguous. "It feels slower lately" with no locatable onset is not yet a regression you can bisect — get the onset first.

### 2. Line the onset up against what changed
Take the onset timestamp and ask what crossed it. Walk the usual suspects, most-likely first:

| Suspect | How you check it against the onset |
|---|---|
| Deploy / release | deploy markers on the dashboard; release log. Did a rollout land at the onset? |
| Config / feature-flag flip | flag-change audit log, config-management history. A flag flip leaves no deploy marker but is just as causal. |
| Dependency / version bump | lockfile diff, image digest change, base-image or sidecar update in the onset window. |
| Data-volume / cardinality change | table/partition growth, a backfill, a key whose cardinality exploded, a cache that stopped fitting. |
| Traffic-mix change | request-type ratios, a new client, a new region, a retry storm, payload-size shift. |
| Hardware / instance change | autoscaler moved you to a different instance type, a node pool rolled, a noisy neighbor, a spot reclaim. |

The discipline here is to **diff the two windows**, not to theorize. Whatever you suspect, confirm it landed in the onset window and not before or after. A deploy two hours before the step is not your cause no matter how suspicious it looks. In prod, the deploy markers, config audit log, and trace metadata that make this join possible are exactly the telemetry that has to be in place *before* the incident — see `../environment/prod-distributed.md`.

### 3. Bisect to the single change
Step 2 usually leaves a few candidates. Isolate the one that did it by bisecting along whichever axis is cheapest:

- **By commit/release.** If the onset brackets a range of commits, `git bisect` (or a deploy bisect: redeploy successive releases to a canary and watch the metric) collapses N commits to one in log₂(N) steps. This is the highest-confidence bisect when you can reproduce the regression on demand.
- **By time window.** When you can't redeploy, narrow the onset itself — finer-grained metrics, per-minute instead of per-hour — until only one change sits inside the bracket.
- **By toggling the suspect.** A feature flag is the fastest bisect there is: flip it off and watch the metric recover (then back on to confirm it returns). A flag that toggles the regression cleanly *is* the proof; no profiling needed. Same logic for routing a fraction of traffic to an old image, or rolling one node pool back.

Stop when toggling/reverting one thing moves the metric and nothing else does. That change is the regression's cause. (If a revert is safe and cheap, do it now to stop the bleeding — diagnosing the mechanism and mitigating the incident are separate clocks, and the second one is usually more urgent.)

### 4. Compare against the pre-regression baseline, then enter the normal loop
Now — and only now — profile. But the question is not "is this slow against the target," it is **"what got worse, and by how much, versus the healthy window."** The baseline is the *same metric before the onset*, not an absolute SLO. A path can be miles inside its budget and still have regressed 40%; the regression is the delta, and the delta is what you chase.

So run the `index.md` diagnose loop (USE/RED, then profiling) on the **delta between good and bad**, not on the bad state alone:

- Capture the same profile / counters / traces in the healthy window and the regressed window, and **diff them**. A differential flame graph (before vs after) points straight at the frames that grew. A trace from before and after the onset shows which span got longer.
- Read the delta with the same bound-type reasoning as any diagnosis (`../orient/bound-types.md`), but anchored to the comparison: the counter that *moved* is the lead, not the counter that is merely large. A 30% LLC-miss rate that was 30% before the regression is not your story; a lock-wait that went 2% → 25% is.

This is why correlation comes first: by the time you profile, you already know which change to attribute the delta to, so the profile confirms the *mechanism* of a known cause instead of searching blind. You leave with a sentence like *"the v2.4 deploy swapped the JSON codec; allocation rate tripled, young-gen GC went 2% → 14% of wall time, and that is the p99 step."*

---

## Doing this in production

A live regression is almost always a prod-distributed problem, so the telemetry leaf is your toolbox (`../environment/prod-distributed.md`):

- **Metric onset on dashboards.** The fleet-wide histogram quantile over time (the `histogram_quantile` query) is how you pin step 1; make sure you're reading an aggregable histogram, not averaged per-instance summaries, or the onset will be smeared.
- **Deploy markers / change events overlaid on the metric.** This is what makes step 2 a glance instead of an investigation. If your dashboards don't carry deploy and config-change annotations, that gap is the first thing to fix after the incident.
- **Traces before and after.** Pull a sample of traces from the healthy window and the regressed window for the same endpoint and diff the span tree — the hop that grew is the regressed tier, and you switch to USE on that tier's host to explain it (the RED→USE handoff from `index.md`).
- **Continuous profiling diffed across releases.** If you run always-on profiling, you can diff "where the cycles went" between the last-good release and the bad one directly, which collapses steps 3 and 4 into one comparison.

---

## Worked example: the checkout p99 step

**Symptom.** PagerDuty fires: checkout p99 breached its 200 ms SLO, sitting at 320 ms. It was ~150 ms yesterday.

1. **Onset.** Hourly p99 over three days shows a flat ~150 ms, then a clean step to ~320 ms at 14:10 on 2026-06-19, sustained since. Sharp step, not a ramp → a discrete change, not growth or a leak.
2. **Correlate.** Overlay change events on that window. No deploy at 14:10. But the config audit log shows a feature flag `checkout.new_pricing_engine` flipped to 100% at 14:08. Two minutes before the step — inside the bracket.
3. **Bisect.** The flag is the cheapest possible bisect: flip it back to 0% on a canary. p99 drops to 150 ms within a minute. Flip to 100% again — back to 320 ms. The flag *is* the cause; no profiling was needed to localize it. Mitigate now: hold the flag at 0% to stop the bleeding while diagnosing the mechanism.
4. **Baseline delta.** The question is not "why is pricing 320 ms" but "what got 170 ms worse." Diff traces for the checkout endpoint before and after 14:08: the `price_quote` span went 8 ms → 178 ms. Diff continuous-profiling between flag-off and flag-on: the new pricing path issues a per-line-item DB query (an N+1) where the old one issued one batched query. The delta is round-trip count, not CPU.

Outcome sentence: *"the new pricing engine flag turned one batched price query into N+1 per-item queries; at ~30 items the added round trips are the 170 ms p99 step."* The fix (batch the query) lives in `../optimize/`; the flag stays off until it ships; `../measure/verify.md` confirms the metric returns to ~150 ms; and this is exactly the kind of N+1 a `../design-and-lifecycle/regression-ci.md` query-count gate would have blocked at the PR.

---

## Pitfalls

- **Profiling before correlating.** Opening a flame graph on the bad state alone throws away the timestamp, the single most valuable fact you have. Pin the onset and find the change first; profile to confirm the mechanism, not to find the cause.
- **Comparing against the target instead of the baseline.** "It's still under SLO" hides a real regression that spent your whole margin in one commit. The question is the delta from the healthy window, not the distance to the budget.
- **Blaming the nearest deploy.** Correlation is not "a deploy happened recently"; it is "a change landed *in the onset window* and reverting it recovers the metric." Confirm the bracket, then bisect.
- **Mistaking a spike for a step.** A transient spike (a backfill, a one-off GC, a deploy blip) is not a regression. Require a *sustained* level change before you bisect.
- **Chasing the largest counter instead of the one that moved.** On a regression the lead is always the counter that changed between windows, not the one that is biggest in absolute terms.

---

## Where next

| After… | Go to |
|---|---|
| you've localized the change but still need the mechanism | `index.md` — run USE/RED + profiling on the delta |
| the change is found and reverted; prove the recovery | `../measure/verify.md` — confirm the metric returned to baseline |
| you want this caught at the PR next time, not in prod | `../design-and-lifecycle/regression-ci.md` — the prevention sibling |
| the regression spent error budget and you need the policy | `../design-and-lifecycle/budgets-slos.md` — what the regression cost, and the freeze trigger |
| you need the prod telemetry to do any of the above | `../environment/prod-distributed.md` — metrics, traces, deploy markers, continuous profiling |
| unsure what *kind* of bound the delta is | `../orient/bound-types.md` |
