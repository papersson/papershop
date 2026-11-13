# Mutation testing

**Use when:** you need to know whether the properties would catch a bug.
**Emits:** `mutation-report.md`.

A workload that has never failed has shown nothing yet. Mutation testing breaks the SUT on
purpose, one small change at a time, and checks that the property meant to guard that behaviour
fails. A mutant is *killed* if it does and *survived* if every check still passes.

Only safety properties are mutated. Liveness and reachability properties are validated by the
baseline run: their `Sometimes` and `Reachable` assertions must fire on the unmutated SUT.

## Before starting

Run the workload on the unmutated SUT and record the baseline: it passes, and its reach
assertions fire. A mutation run against a failing or unreached baseline tells you nothing.

## Designing a mutant

One mutant per safety property. Read the property's evidence file first: the code paths and the
failure scenario recorded there are where a good mutant comes from.

- **A realistic mistake.** A dropped guard, `>` where `>=` belonged, an off-by-one, a check moved
  outside a lock, an error swallowed instead of propagated, two writes reordered. Not vandalism.
- **Subtle.** It should need a specific state to show. A mutant that breaks every request proves
  the assertion exists, not that the workload can find the interesting case.
- **In the code that maintains the invariant**, not in the code that checks it. Mutating the check
  disables the reporting along with the behaviour.
- **Not fatal.** It must not crash the SUT at startup or hang it.
- **With a marker.** Add a signal at the point of divergence (a log line or a reach assertion
  carrying the mutant's id), placed where the mutated branch is actually taken, so you can tell
  whether the broken code ran.

Research several candidates per property, apply the strongest, and record the rejected ones with
reasons.

## The verdict ladder

For each mutant, in this order:

1. **Did it build and start?** If not, fix the mutant.
2. **Did the marker fire?** If not, the workload never reached the mutated code. The finding is
   about the workload: go to `modules/review-inputs/`.
3. **Did the target property fail?** If so: killed. Record the minimal counterexample.
4. **Did some other property fail instead?** Record it as collateral. The target property is still
   not shown to work.
5. **Nothing failed, and the marker fired:** survived. The property is too weak, or missing. Find
   what the mutant changes that no property observes, and repair the property.

## After a design fix

When a defect was fixed by redesigning the data (`modules/triage/fix-by-design.md`), run the
same mutants against the new design and sort them:

- **Stillborn**: the mutant no longer compiles. The property it targeted is enforced by
  construction; its assertion can be retired or kept as a cheap backstop.
- **Killed**: the mutant compiles and the property fails. The types did not take this property
  over, and the workload is still needed for it.
- **Survived**: the mutant compiles and nothing fails. Neither the types nor the properties
  guard this behaviour.

Report the three lists. They are the evidence for which properties the redesign made redundant.

## Do not game it

- Never coarsen a mutant into obvious breakage to get it killed. Fix the workload or the property.
- Never write two mutants for one property "to be sure". Pick the strongest.
- A mutant whose wrong value is recomputed or clamped back before anything observes it is an
  equivalent mutant. Record it as such and design another.
- Zero survivors is a statement about the mutants you wrote, not about the properties.

## Done when

- [ ] The baseline is recorded, with its reach assertions firing.
- [ ] Every safety property in the catalog has one mutant, or a note saying why it cannot be mutated.
- [ ] Every verdict names the rung of the ladder it stopped on.
- [ ] Every survivor led to a repaired property, a repaired workload, or an open question.
- [ ] All mutants are removed from the SUT.
