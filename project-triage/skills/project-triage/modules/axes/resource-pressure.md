# Axis 2: Resource pressure

**Quick question.** Is there an artifact putting ~10^6+ live instances or ops/sec on a path this
component owns — or a hard RAM/flash/energy/binary-size budget within ~10× of its working set? No
artifact on either count means COOL and UNBOUNDED provisionally.

## Full question (deep pass)

Two independently recorded sub-answers, read from two different artifacts.

**(a) Count heat:** name the most numerous data type this component owns and its innermost loop. Is
there an artifact — budget document, written performance requirement, or a profile someone will hold
you to — putting ~10^6+ live instances or ~10^6 ops/sec on that path? **No artifact means COOL
provisionally.** "We might need to scale someday" is not an artifact; the artifact-or-COOL rule is
the anti-inflation guard.

**(b) Envelope:** name the binding resource budget artifact — RAM bytes, flash bytes, energy per
day, binary-size ceiling — read off the datasheet, BOM, or product spec. **A PaaS instance memory
quota counts as a named budget artifact**, same standing as a datasheet line. Then estimate the
component's working set. Budget within ~10× of the working set = ENVELOPED; otherwise UNBOUNDED.

## Answers

- Heat: **HOT** | **WARM** (IO/network-dominated) | **COOL** | **DEFERRED**.
- Envelope: **ENVELOPED** (named budget artifact within ~10× of working set) | **UNBOUNDED**.
- **DEFERRED emits COOL's output provisionally** — evidence-carrying types everywhere — rather than
  emitting nothing; the named trigger re-fires the axis.

## Day-one checkability

Domain arithmetic usually settles heat immediately: 10^5 entities × 60 Hz is HOT by multiplication;
back-office CRUD is COOL by inspection. For the envelope, the working set of unwritten code is
estimated from the dominant data the component must hold at once — largest input it must process,
largest resident structure times its count. The ~10× band only asks for order-of-magnitude
arithmetic: a 512 MB instance quota against a 300 MB largest-input file is inside the band
(ENVELOPED); the same quota against a 5 MB working set is not. When the estimate straddles the band,
record ENVELOPED with the estimate written down — the arithmetic is the falsifier, and a wrong
estimate surfaces at first measurement.

## Decides

- **Concern 2, type safety vs memory layout (primary — sole decider in the set; joint of heat and
  envelope):** HOT or ENVELOPED → flat/packed/index layout *on the named hot or budget-bound types
  only*. COOL/WARM + UNBOUNDED → evidence-carrying types everywhere.
- **Concern 3, values vs places (the motive half; writer topology supplies the safety half):** HOT →
  bounded in-place mutation behind a value-semantics interface. ENVELOPED → in-place mutation
  wherever copies do not fit the budget: static pools sized at compile time, no heap after init,
  ring-buffer reuse — the envelope forces the places pole by arithmetic, not taste. COOL + UNBOUNDED
  → immutability everywhere. WARM resolves to COOL: cache-conscious mutation buys nothing when the
  wire dominates.
- **Concern 1, invariant placement (modulates):** HOT → construction-time invariants and debug
  asserts at core entry. ENVELOPED → compile-time sizing proofs (static asserts on buffer, stack,
  and binary bounds) preferred over dynamic checks that themselves cost RAM.
- **Concern 10, agent delegation (partial):** ENVELOPED adds the resource model to the
  machine-checkable substrate — the linker map, stack-depth analysis, and energy budget are
  artifacts a delegated agent must iterate against; without them delegated code is
  correct-but-unlinkable and a human must adjudicate fit-vs-doesn't.

## Re-fire triggers

- **(a):** first representative profile, or first written performance requirement.
- **(b), decision-time:** a resource budget artifact newly attaching to the component — an SOW
  clause, a customer product spec, or the datasheet of a new deployment target — re-fires (b) *at
  signing time*, before any port or build begins. The envelope's outputs are day-one architectural
  commitments, so the trigger fires when the commitment is made, not when it is missed.
- **Incident-time backstops:** first linker-map overflow, stack-depth failure, or
  battery-life/binary-size budget miss.

## Translations and misfits

- **PaaS and container deployments:** the platform's memory quota (dyno size, container limit) is a
  real budget artifact even though nobody wrote a datasheet — components processing large inputs
  under small quotas are ENVELOPED and get the envelope's outputs on the affected path.
- **"Performance-sensitive by reputation":** heat without an artifact is DEFERRED, not HOT. DEFERRED
  costs nothing — it emits COOL's output provisionally and re-fires at the first profile or written
  requirement, so recording it honestly loses no safety.

## Skip when

The envelope arithmetic can be skipped when no budget artifact exists — UNBOUNDED by inspection, and
inventing one is exactly the inflation the artifact rule guards against. Heat settles in one
question for most components: COOL by inspection for back-office CRUD, HOT by multiplication for
simulation-style loops. The deep pass is only for components where a named artifact exists and the
working-set arithmetic is genuinely close.
