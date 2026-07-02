# Axis 6: Commitment reversibility

**Quick question.** What have you shipped that you can't take back? List every artifact whose
consumers you cannot force to upgrade and name those consumers. Empty list = FLUID. Then two riders:
who must move when an interface changes (even a forceable one), and what platform capability can a
landlord revoke underneath you?

## Full question (deep pass)

Classify by intended distribution: list every shipped artifact whose consumers you cannot force to
upgrade — wire protocols, on-disk formats, public APIs, firmware, certified builds — and name those
consumers. Empty list = FLUID. Hyrum surfaces enter on the first uncontrolled-consumer event; do not
stall enumerating hypothetical future scripters.

**Rider 1 — consumer cardinality** (same consumer walk; asked for internal, *forceable* interfaces
too — the main question's "cannot force" filter does NOT apply here): for each interface this
component exposes, count the call sites and independently-prioritizing teams that must move when its
shape or *semantics* change. Is a change one commit landable by you (**LOCAL**), or a campaign
across N owning teams' review queues (**CAMPAIGN**, record N)? Forceability and coordination cost
are independent: monorepo codemod / large-scale-change tooling mechanizes *syntactic* rewrites only,
while semantic changes (error-contract behavior, token meaning) cost per-call-site human judgment
times N owners regardless of forceability — a forceable interface can still be a campaign.

**Rider 2 — substrate capability regime** (same commitments pass — it inverts the dependency arrow:
the main question lists surfaces YOU froze toward consumers; this lists surfaces a counterparty can
break *underneath* you): name every platform capability this component requires that a counterparty
can remove or reshape without your agreement — host APIs, browser-extension surfaces, mobile OS
entitlements, app-store policy gates, a SaaS platform you build on — and that counterparty's
published deprecation calendar or policy cadence. Capabilities resting on versioned, decades-stable,
or self-controlled substrate (POSIX, ISO C/C++, JVM, SQL standard, your own OS image) =
**STABLE-SUBSTRATE**. Any required capability a named landlord can revoke unilaterally =
**LANDLORD** (record platform and calendar).

## Answers

- **FLUID** | **EDGED** (named short list of frozen boundaries) | **FROZEN**.
- Cardinality per interface: **LOCAL** | **CAMPAIGN(N teams)**.
- Substrate flag: **STABLE-SUBSTRATE** | **LANDLORD** (named platform, published calendar).

## Day-one checkability

A question about the distribution model, not hindsight: at project start you know whether you
control every deploy point. Rider 2 is checkable from the platform's own policy and deprecation
docs.

## Decides

- **Concern 8, design-phase weight (primary):** FROZEN/EDGED → heavy up-front design on exactly the
  frozen surfaces — a shipped bug on a surface with un-upgradeable consumers is kept forever. FLUID
  → ship-and-iterate. Via cardinality: CAMPAIGN → RFC/deprecation process, migration tooling, and
  staged-rollout design get real design weight even at FLUID — "FLUID → ship-and-iterate" is capped
  at LOCAL interfaces. Via substrate: LANDLORD → capability-degradation modes and dual-track builds
  (current + announced-next platform version) get design weight despite FLUID; the landlord's
  calendar, not your release train, sets the deadline.
- **Concern 7, abstraction timing (partial):** frozen-surface vocabulary (field names, message
  types, error codes) is designed before first ship — there is no second naming pass on a wire
  protocol. Via cardinality: CAMPAIGN → the interface's vocabulary is designed up front even where
  the volatility/horizon joint says extract-after-repetition, because a wrong noun costs a campaign
  per correction; LOCAL → extract-after-repetition stands. Via substrate: LANDLORD → an adapter seam
  isolating every landlord touchpoint is designed up front, before feature vocabulary — the platform
  boundary is the first abstraction, not an extracted one.
- **Concern 10, agent delegation (partial):** frozen surfaces keep a human carrying compatibility
  theory (what old consumers depend on is not machine-checkable from the current repo). Via
  cardinality: the deep-delegation zone narrows to the LOCAL+FLUID interior; shape or semantics
  changes to a CAMPAIGN interface keep a human carrying the migration-cost theory even when every
  consumer is technically forceable.
- **Concern 5, schema openness (via substrate flag):** LANDLORD → version/capability negotiation
  machinery toward the platform boundary (feature detection, graceful capability loss) — a boundary
  the data-gravity walk never records, because the API is called, not parsed.
- **Concern 6, test evidence (via substrate flag):** LANDLORD → a host-version test matrix across
  the landlord's release channels (stable/beta/canary or OS versions), tracking announced
  deprecations, is first-class evidence. STABLE-SUBSTRATE → such a matrix is speculative weight.

## Re-fire triggers

- **Main (the Hyrum event on this axis):** the moment any artifact ships to a deploy point you do
  not control — first external SDK user, first firmware flash, first third-party integration — that
  surface moves FLUID→EDGED and the design-weight decision re-fires for it. When the surface is a
  data sink, data gravity re-fires for that sink too.
- **Rider 1:** consuming-team count first crosses ~5, or the interface is published to an internal
  package registry or platform catalog.
- **Rider 2:** a new platform dependency is added, or the landlord announces a deprecation, manifest
  revision, or policy change touching a required capability.

## Translations and misfits

- **Small organizations:** "independently-prioritizing teams" gets fuzzy below ~50 people, where
  LOCAL vs CAMPAIGN(2) can be a coin flip. Record the coin flip as such — the rider's own trigger
  (team count crossing ~5) is the tiebreaker, and the cost of recording LOCAL wrongly is bounded by
  it.
- **Internal-only components:** an empty frozen list does not end the pass. Rider 1 still counts
  forceable consumers, and rider 2 still asks who owns the substrate — both riders deliberately
  survive a FLUID main answer, and skipping either is the failure its recorded promotion bet watches
  for.

## Skip when

The main question settles in one pass for most components — a service you deploy everywhere is FLUID
by inspection. Skip the per-interface cardinality count when the component exposes nothing beyond
its own process, and skip the substrate walk when everything sits on self-controlled or
standards-stable substrate you can name in one line. Never skip the riders on the strength of a
FLUID main answer alone.
