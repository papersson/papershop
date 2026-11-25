# Concern 8: Design-phase weight — blueprints vs ship-and-iterate

## The tension

- **Blueprints.** Thinking above the code level catches the errors that coding-and-patching never
  reaches: a specification is where you find out the design is wrong while it still costs a page
  edit, not a migration (Leslie Lamport, "Who Builds a House Without Drawing Blueprints?"). The
  cheapest defect is the one designed away before any code exists (Joran Dirk Greef, "TigerStyle")
  — and some artifacts genuinely allow no second attempt.
- **Ship and iterate.** Worse-is-better wins in the field: the simple, early, spreading thing
  beats the complete, late, correct thing, because contact with users is the only source of the
  information the design phase pretends to have (Richard P. Gabriel, "The Rise of Worse is
  Better"). Design weight spent on requirements that turn out wrong is pure loss, and a heavy
  process delays the moment of learning.

Neither pole is a temperament; each is correct under specific, checkable conditions — whether the
shipped artifact can be revised, and whether the requirements are actually known.

## Decided by

- **Commitment reversibility × requirements volatility (primary — the quadrant):**
  - FIXED-SPEC + FROZEN → maximum design weight: the spec is known and the surface is forever;
    this is Lamport's home regime.
  - FIXED-SPEC + FLUID → moderate: design what the signed spec makes designable, but iteration
    stays available and cheap, so speculative depth beyond the spec is waste.
  - DISCOVERING + FLUID → ship-and-iterate at full speed; this is Gabriel's home regime, and
    heavy design here formalizes guesses.
  - DISCOVERING + FROZEN → the trap cell. Heavy design cannot rescue it — designing hard against
    unknown requirements freezes a well-drawn wrong guess. The resolution is to *shrink the
    committed surface*: minimize what ships frozen (fewer endpoints, fewer promised fields,
    explicit versioning from day one) until discovery catches up.
- **Defect consequence (overrides):** UNRECOVERABLE/HARM forces design weight even when code is
  freely redeployable — the damage, not the artifact, is the irreversible thing (Knight Capital:
  fully reversible deploy, $440M unrecoverable loss). Material BOUNDED-LOSS reaches the same
  override — launch-readiness reviews, dry runs, validate-before-checkpoint-commit even at FLUID
  plus DISCOVERING. AUDITED makes the change-control pipeline itself a designed deliverable:
  enforced author/approver separation, tamper-evident break-glass, immutable audit trails,
  engineered up front because retrofitting controls under a failed audit is the expensive path.
- **Horizon flag (floor and ceiling):** THROWAWAY → zero design weight regardless of FIXED-SPEC,
  unless the consequence override fires. INSTITUTION → modest structural design pays even at
  FLUID.
- **Cardinality rider:** CAMPAIGN caps ship-and-iterate — RFC/deprecation process, migration
  tooling, and staged rollout get real design weight even at FLUID, because forceability does not
  erase coordination cost across N teams.
- **Substrate flag:** LANDLORD → capability-degradation modes and dual-track builds get design
  weight despite FLUID; the landlord's deprecation calendar, not your release train, sets the
  deadline.
- **Writer topology:** SESSION-MASS combined with a frozen client protocol → reconnect jitter,
  resume cursors, and backoff are designed into the protocol before first ship; they cannot be
  retrofitted onto deployed clients.

## What each pole implies concretely

**Blueprints:** a written spec or model of the frozen surfaces before code — state machines,
failure modes, versioning story; review at the design artifact, where a wrong decision costs an
edit; the irreversible paths (money movement, actuation, data deletion) walked on paper with
named interlocks; for AUDITED components, the change pipeline designed like a feature.

**Ship-and-iterate:** smallest shippable slice to real users; the committed surface kept
deliberately narrow so learning stays cheap; design effort spent on making change safe (feature
flags, staged rollout, reversible migrations) rather than predicting the endpoint; specs written
after stabilization, as records rather than bets.

## Default when undecided

Ship-and-iterate with the committed surface shrunk to the minimum — the trap-cell resolution is
also the safest general posture. Under-design on a small fluid surface is corrected next release;
over-design against unconfirmed requirements is sunk cost that also hardens the guess. The one
exception is decided elsewhere and stands: a consequence override (UNRECOVERABLE/HARM, material
BOUNDED-LOSS, AUDITED) buys design weight regardless.
