# Setting performance budgets & SLOs

**Status:** READY
**Loaded when:** defining the target — turning "fast enough" into a defended number. The gate in SKILL.md sends here whenever a task arrives without one.

This is step 1 of the loop (**target** → measure → locate → fix → prove → defend) and the first lever of design (`design-for-performance.md` Lever 1 is the same act seen from the design side). The gate refuses "make it fast"; this leaf is how you replace it with a number you can measure against, decompose across teams, and defend in CI. The core rule: **a target is a specific metric, at a specific percentile, over a specific window, tied to a real consequence.** Anything vaguer is not a target, it is a wish.

A budget is that number made ownable: an end-to-end objective sliced so each component, service, and team holds a piece and knows when they have spent it.

---

## The method: from "fast enough" to per-owner budgets

Run these in order. The output is a table of component budgets plus an error-budget policy, both of which feed straight into `regression-ci.md` (the gate that enforces them) and design (the target each component builds to).

### 1. Pick the metric that matters (the SLI)

Decide *what* you are measuring before *how fast*. A Service Level Indicator is a measured quantity about the service, expressed as a ratio of good events to total events. Pick the one your users actually feel:

- **Latency** — request duration. For anything user-facing this is usually the contract.
- **Throughput** — work completed per unit time (RPS, rows/s, tokens/s). The contract for batch and ingest.
- **Availability / correctness** — fraction of requests that succeed. Often paired with latency ("fast *and* correct"; a fast error is not a served request).
- **Resource / cost** — memory ceiling, $/request, $/million rows. The contract when the limit is a budget line, not a clock.

Most services need two or three SLIs, not ten. Choose the few that, if violated, mean the service failed its users. Workload-shape lens: `../orient/work-taxonomy.md`.

### 2. Pick the percentile, not the average

"Fast" for an interactive path is almost never the mean. A service with a 5 ms mean and a 500 ms p99 is a 500 ms service for one request in a hundred, and that request is often the user with the fullest cart. Choose the statistic from the consequence:

- **Latency SLI → a tail percentile.** p99 is the common default for user-facing requests; p99.9 when a single slow request fans out or blocks a session; p95 when the path is cheap and tolerant. State which: "p99 of checkout latency."
- **Throughput / cost → a total or a floor**, not a percentile of per-request rate (throughput is a ratio of totals, not an average of windows; see SKILL.md measurement integrity).

The percentile is load-bearing in everything downstream, because tails compound across components in ways means do not (step 5).

### 3. Derive the end-to-end objective (the SLO)

A Service Level Objective is the target value for an SLI over a window: *"99% of checkout requests complete in under 200 ms, measured over a rolling 28 days."* Three parts, all required:

- **The threshold** (200 ms) — where does the consequence start? Anchor it in something real: a user-research number ("above ~250 ms feels sluggish"), a competitor, a contractual SLA, a conversion-vs-latency curve, or a cost line. Do not invent a round number and call it a target.
- **The objective** (99% of requests meet the threshold) — how often must you hit it? This is the reliability target, and it implies the error budget (step 6).
- **The window** (28 days, rolling) — over what horizon? Short windows are noisy and alert-happy; long windows hide sustained degradation. 28 days is a common compromise.

Sanity-check the threshold against the latency floor *before* committing. Sum the irreducible costs — RTTs, serial cross-service hops, the minimum bytes that must move — from known numbers (`../orient/latency-numbers.md`). A 200 ms p99 over a path with 20 serial 15 ms hops is physically impossible, and you can know that on a whiteboard instead of discovering it in load test. If the floor exceeds the objective, the objective or the architecture has to change now.

### 4. Map the call graph

You cannot decompose a budget without the graph it flows through. List every component a request traverses: gateway, app server, auth, the databases and caches, downstream services, the network hops between them. The distributed-tracing span tree gives you this directly (`../diagnose/index.md`, RED method). For each edge mark whether it is **serial** (must finish before the next starts), **parallel/fanout** (issued together), **conditional** (cache hit vs miss), or **retried**. The structure decides the arithmetic in step 5.

### 5. Decompose the objective into component budgets

Split the end-to-end SLO into a ceiling each owner holds. The arithmetic depends on the edge type. The one principle behind all of it: **percentiles do not add cleanly, and under load tails compound** — so summing per-stage p99s does not reliably hold the end-to-end p99, and you must reserve headroom.

- **Serial chain — budgets sum, plus headroom.** End-to-end latency is the sum of stage latencies, so allocate each stage a ceiling whose sum is *below* the SLO. Reserve 10-30% slack, because budgeting each stage at p99 and summing does *not* hold the end-to-end p99 in practice. If the stages were independent the summed p99s would actually be conservative — the chain rarely hits every stage's tail at once, so the p99 of the sum sits *below* the sum of the p99s. But real serial stages are positively correlated and bursty (shared GC pauses, load spikes, noisy neighbors), and under positive correlation the end-to-end tail rises toward the worst case, where it *equals* the sum of the per-stage p99s. To *guarantee* an end-to-end p99 from per-stage budgets regardless of correlation, budget each stage to a tighter percentile: by the union bound, holding each of N stages to the (1 − 1/(100N)) percentile caps total violation at 1% (≈ p99.9 for ~10 stages). Or keep explicit headroom. Example: a 200 ms p99 over four serial stages is not 50 ms each at p99; it is closer to 40 ms each at p99.9 with 40 ms of reserve.
- **Fanout / parallel — budget the max, and tighten hard for N.** End-to-end is the slowest leaf, and the tail of the slowest-of-N is far worse than any single leaf's tail. With N independent parallel calls each meeting p99, the chance *all* are fast is 0.99^N: at N=100 that is ~37%, so the parent sees a slow leaf ~63% of the time. This is the tail-at-scale effect (Dean & Barroso, *The Tail at Scale*, CACM 2013). Consequence: a leaf serving a high-fanout parent must be budgeted at a much tighter percentile than the parent's tail — p99.9 or p99.99 leaves to hold a parent p99. Reducing fanout width is itself a budget lever.
- **Retries — add the retry cost, then cap it.** A path that retries once on failure budgets for the extra attempt's latency in the tail. Pair every retry with a retry budget (a cap on retry volume) so a bad day cannot turn into a retry storm that burns the whole latency budget at once.
- **Cache — blend by hit rate, but the tail is the miss path.** Mean latency ≈ hit_rate × hit_latency + miss_rate × miss_latency. For the *tail*, the miss path dominates the moment miss_rate exceeds (1 − target percentile): if you promise p99 and miss 5% of the time, your p99 *is* the miss latency. Budget the miss path to the percentile, not the blended mean.
- **Network / RTT floor — subtract first.** The irreducible RTTs and serial hops are not anyone's to optimize; subtract them off the top and decompose only the remaining budget across the components that can move.

Write the result as a table: component, edge type, budget (metric @ percentile), owner. That table is the contract. Each row is a target someone builds to (`design-for-performance.md`) and a threshold CI enforces (`regression-ci.md`).

### 6. Set the error budget and its policy

The SLO's complement is the **error budget**: the amount of failure you are *allowed*. A 99.9% objective permits 0.1% bad events — roughly 43 minutes per 30-day month, or for a latency SLO, 0.1% of requests allowed over threshold. The error budget converts reliability from an argument into arithmetic: you are not "as fast as possible," you are "allowed to be slow exactly this much, and not more."

Two numbers drive it:

- **Budget remaining** — how much of the allowed failure you have left in the current window.
- **Burn rate** — how fast you are spending it. A burn rate of 1 spends the whole budget exactly over the window; a burn rate of 10 spends it in a tenth of the window and is an emergency. Fast-burn and slow-burn alerts (multiwindow) are how SRE pages on it.

The **error-budget policy** is the part that has teeth, and it must be agreed *before* you need it (Google SRE practice, *Site Reliability Engineering*, ch. 3–4): **when the budget is spent, risky changes freeze.** Concretely:

- **Budget healthy** → ship features, take normal risk. Spare budget is permission to move fast; an unspent budget is not a trophy, it means the SLO is too loose or you are over-investing in reliability.
- **Budget low / high burn rate** → slow down, prioritize reliability and performance work, scrutinize releases.
- **Budget exhausted** → hard gate: feature freeze, only reliability- and performance-fixing changes ship until the service is back inside its SLO over the window.

This policy is the whole reason budgets are worth setting. Without it an SLO is a dashboard nobody acts on; with it, the number decides what the team is allowed to do this week. It only works if it is a prior commitment between the people who own reliability and the people who own features, not a negotiation held during the incident.

---

## SLI vs SLO vs error budget (the three terms, kept straight)

| Term | What it is | Example | Who uses it |
|---|---|---|---|
| **SLI** | a measured ratio of good to total | "fraction of checkout requests under 200 ms" | the metric pipeline; the thing CI measures |
| **SLO** | the target for an SLI over a window | "99% of those, over 28 days" | the contract; the design target |
| **Error budget** | `1 − SLO`, the allowed failure | "1% of requests may be slow ≈ X/month" | the release gate; what the policy spends |
| **SLA** | an SLO with a contractual penalty | "below 99% → service credits" | legal / commercial, looser than the internal SLO |

Keep the internal SLO tighter than any external SLA: you want to notice and act on the error budget well before a customer can claim a penalty.

---

## Pitfalls / over-engineering signals

- **A target with no consequence.** If nothing happens when the number is missed, it is not a target; the gate should have stopped you. Either attach a consequence (the error-budget policy) or admit there is no work here.
- **Budgeting the mean for a tail contract.** The mean hides the tail that hurts. If the SLI is user-facing latency, every budget in the decomposition is a percentile, not an average.
- **Summing p99s for a serial chain.** Summing per-stage p99s only holds the end-to-end p99 under independence assumptions that real, correlated stages violate; the tail rises toward the sum-of-p99s worst case under load. Reserve headroom or budget stages to a tighter percentile.
- **Ignoring fanout amplification.** Giving a high-fanout leaf the same percentile as its parent guarantees the parent misses. Tighten leaves by fanout width.
- **An SLO nobody can act on.** No burn-rate alert, no freeze policy, no owner per component → a dashboard, not a budget. The policy is the point.
- **Too many SLOs.** Ten SLIs per service means none of them gates anything. Pick the two or three that mean "the service failed its users."
- **A 100%-style objective.** Chasing 100% (or 99.999% when the product does not need it) spends enormous effort and leaves zero error budget, which means zero room to ship. The right objective is the loosest one users do not notice. An *unspent* budget is a signal to tighten the SLO or take more risk, not to celebrate.
- **Round-number thresholds.** 100 ms because it is round, not because the consequence starts there. Anchor in research, a curve, a competitor, or a cost.

---

## Worked example: a checkout path, decomposed

**Product consequence (step 1–3):** conversion drops measurably above ~250 ms at the tail. SLI = checkout request latency. SLO = **p99 < 200 ms over a rolling 28 days**, with a 50 ms safety margin under the 250 ms cliff. Availability SLI alongside it: **99.9% of checkouts succeed**, error budget ≈ 43 min/month.

**Latency floor check (step 3):** client↔gateway RTT ~5 ms, gateway↔region serial. Irreducible serial RTT + minimum work ≈ 30 ms. Budget left to distribute: ~170 ms. Feasible — proceed.

**Call graph (step 4):** gateway → checkout service (serial) → {pricing, inventory, fraud} fanout of 3, parallel → payment (serial, with one retry) → write to order DB (serial). Cache in front of pricing.

**Decomposition (step 5):**

| Component | Edge | Budget (latency @ pct) | Owner | Note |
|---|---|---|---|---|
| Network / RTT | serial floor | 30 ms (fixed) | platform | subtracted off the top, not optimizable |
| Gateway | serial | 10 ms @ p99.9 | edge team | |
| Checkout orchestrator | serial | 15 ms @ p99.9 | checkout | own logic only, excludes fanout |
| Fanout {pricing, inventory, fraud} | parallel, N=3 | slowest leaf 60 ms @ **p99.9** | three teams | each leaf tightened to p99.9 so the max holds p99 |
| Payment (1 retry) | serial + retry | 50 ms @ p99, retry budget 10% | payments | budgets the second attempt into the tail |
| Order DB write | serial | 20 ms @ p99.9 | data | |
| **Reserve** | — | ~15 ms | — | headroom because serial tails compound |

The serial ceilings (10 + 15 + 60 + 50 + 20 = 155 ms) plus the 30 ms floor and ~15 ms reserve sit under 200 ms. The fanout leaves are budgeted at p99.9 because at N=3 the slowest-of-three tail is worse than any single leaf's p99; the cache in front of pricing means pricing's *miss* path must meet 60 ms, not its blended mean.

**Error-budget policy (step 6):** burn-rate alerts at 14× (fast burn, pages) and 1× (slow burn, ticket). When the 28-day latency budget is exhausted, checkout enters feature freeze: only latency- and reliability-fixing changes ship until back in SLO. Agreed by checkout eng and product *now*, in writing.

**Hand-off:** each table row becomes a design target (`design-for-performance.md` Lever 1 contract for that component) and a CI threshold (`regression-ci.md` fails the build if the component's benchmarked p99 exceeds its budget). The end-to-end SLO becomes the production burn-rate alert. The number set here is now enforced in three places: design, CI, and prod.

---

## Where next

| After setting the budget… | Go to |
|---|---|
| build a component to its budget | `design-for-performance.md` (Lever 1 is this contract) |
| enforce budgets so they don't regress | `regression-ci.md` |
| size the latency floor before committing a threshold | `../orient/latency-numbers.md` |
| measure a real path against the budget / find which hop is slow | `../diagnose/index.md` (RED localizes the slow tier) |
| decide how many machines hold the throughput SLO under load | `capacity-scalability.md` |
| classify the workload shape behind the SLI choice | `../orient/work-taxonomy.md` |
