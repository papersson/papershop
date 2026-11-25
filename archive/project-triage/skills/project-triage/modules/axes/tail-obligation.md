# Axis 3: Tail obligation

**Quick question.** Is a latency distribution actually being *sold* to someone? Point at the
artifact — an SLA percentile clause, a frame/tick budget, a consumer-derived alert on your p99, or a
fan-out call site. No qualifying artifact = NONE (or SOFT) today.

## Full question (deep pass)

Is a latency distribution being sold? Point at the artifact: an SLA clause naming a percentile, a
frame/tick budget, an alerting rule someone else owns on your p99, or a fan-out call site where one
request awaits N of you.

**Qualification (on the alerting-rule artifact only):** it counts as SOLD only if its threshold was
chosen *for this component* by a party who consumes its latency — a caller's stated budget, a
contract clause, a product deadline, a frame budget. A template-provisioned or auto-onboarded alert
pack, whose threshold would read the same number regardless of what this component does or who calls
it, records SOFT — the alert measures the distribution but nobody consumes it. SLA percentile
clauses and fan-out call sites are inherently consumer-derived and always qualify.

## Answers

- **NONE** — no qualifying artifact.
- **SOFT** — treated as NONE with a watch trigger; includes template-provisioned alerts.
- **SOLD** — a qualifying artifact names the distribution as someone's dependency.

## Day-one checkability

Each artifact is a document or a call-graph edge, not a judgment call; absence is equally checkable.
Demand the call site, not a prophecy of future fan-out — "callers might fan out later" is SOFT with
the upgrade trigger watching, not SOLD.

## Decides

- **Concern 9, coordination and tail latency (primary for the tail half; writer topology decides the
  machinery half):** SOLD → the distribution is a shipped feature; restate first, budget machinery
  for the remainder. NONE → tail machinery is speculative weight.
- **Concern 3, values vs places (secondary, one-directional):** SOLD → pauses are the product
  defect; places win on the request path even at COOL heat (a 200-QPS gateway with a contracted p99
  has no heat but cannot tolerate pause spikes). NONE returns the decision to resource pressure.

## Re-fire trigger

The upgrade trigger, NONE/SOFT → SOLD: first contracted percentile, hard deadline, fan-out caller,
or an alert threshold re-derived from a named consumer's budget. **"Hard deadline" here means a
per-request or per-frame deadline** — a latency bound on individual operations — not a batch
completion time; see the translation below.

## Translations and misfits

- **Batch deadlines are not tails.** A nightly pipeline with a morning-dashboard deadline has a hard
  product deadline, but the concern this axis decides — pause behavior and tail machinery on a
  request path — is meaningless for a batch run. That deadline is *deadline pressure for concern 8
  (design-phase weight)*, not a sold tail: record NONE here and carry the deadline into the
  design-weight call, so the pressure is neither double-counted as tail machinery nor dropped
  between the two. A nightly pipeline is the canonical HOT-not-TAIL case.
- **Template alert packs:** an organization that auto-provisions p99 alerts on every service has not
  sold N latency distributions. Apply the qualification above; record SOFT and move on.

## Skip when

Never skip the quick question — it is one artifact lookup and decides half of concern 9. There is no
deeper pass to skip: the axis settles in one question for almost every component, and the only extra
work (the alerting-rule qualification) applies only when the sole artifact on offer is an alert.
