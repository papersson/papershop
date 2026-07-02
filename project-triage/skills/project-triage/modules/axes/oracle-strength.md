# Axis 8: Oracle strength

**Quick question.** Can you state, in one sentence, a machine-checkable test of correct behavior —
or point at the artifact that embodies one? **An unnamed hypothetical oracle counts as absent** —
failure to name IS the answer. In the same pass, name the person who can adjudicate surprising
behavior from memory, and confirm they are reviewing changes this quarter.

## Full question (deep pass)

Write the oracle's property statement in one sentence now ("serialize(parse(x)) == x", "output
matches reference implementation on corpus C", "ledger balances to zero") or point at the existing
artifact (conformance suite, golden corpus, reference implementation, simulation harness). Record
the oracle's **coverage denominator** with the grade: name the surface the property statement
quantifies over — which inputs, which operations, which subset of shipped behavior the artifact can
actually adjudicate. **The grade applies only within that denominator**; surface outside it is
graded separately and defaults to TASTE-ONLY until its own oracle is named.

**Rider — theory presence** (carried in the same evidence pass — the written oracle and the living
adjudicator are the two **distinct evidence sources**; do not conflate them): name the person who
can adjudicate, from memory of why the code is shaped this way, whether a surprising behavior is a
bug or intended — and confirm that named person is actually reviewing changes this quarter. No name,
or the name is someone who left, or reviewers rotate through without predating the code =
**THEORY-ABSENT**.

## Answers

- **STRONG** | **PARTIAL** | **TASTE-ONLY** — each scoped to a recorded coverage denominator;
  per-surface grades where the denominator does not span the component.
- Theory flag: **THEORY-RESIDENT** (named, currently reviewing) | **THEORY-ABSENT**.

## Day-one checkability

Answerable by enumeration: the artifact either exists or the sentence is writable now. No deferral
needed for the main answer. The one-sentence test converts a speculative counterfactual ("we could
build an oracle") into an immediate pass/fail act.

## Decides

- **Concern 10, agent delegation depth (primary — capped by defect consequence's UNRECOVERABLE/HARM
  answer and by its external-assurance flag):** the posture is the JOINT of oracle grade and theory
  flag, scoped to the recorded coverage denominator — deep delegation never silently extends past
  what the oracle sees; on surface outside the denominator the effective grade is that surface's own
  (default TASTE-ONLY), so agent changes there revert to author-adjudicated diffs. STRONG+RESIDENT →
  deep delegation within the denominator; humans review the oracle, not the diff.
  PARTIAL/TASTE-ONLY+RESIDENT → the resident adjudicator makes author-adjudicated change the
  economical pole; heavier machine-checkable substrate is speculative weight. THEORY-ABSENT with
  oracle below STRONG → the human review gate is theater (reviewers cannot distinguish bug from
  load-bearing quirk); the dominant engineering work BEFORE any delegated change is substrate
  construction — characterization tests pinning current behavior, an executable spec of the rules —
  with interim changes conservatively small. STRONG+ABSENT → delegate against the oracle, treating
  behavior outside the oracle's coverage as frozen.
- **Concern 6, test evidence:** STRONG → generated property/differential tests within the recorded
  denominator. TASTE-ONLY → curated examples are the honest ceiling (generated tests against no
  oracle are theater). THEORY-ABSENT promotes the existing corpus from regression aid behind an
  author's judgment to primary and near-sole evidence, deliberately expanded toward characterization
  coverage — example-adjudication-by-author no longer exists.
- **Concern 1, invariant placement (conditional):** a type-encodable STRONG oracle makes
  compile-time proof pay rent; this flip fires only when the oracle happens to be type-encodable.

## Re-fire triggers

- **Main:** first shipped feature or surface the oracle artifact cannot adjudicate — the reference
  implementation lacks the operator, the corpus has no vectors for the new mode — re-fires this axis
  for that surface.
- **Rider:** departure or reassignment of the named adjudicator, or transfer of maintenance to AI
  agents or rotating reviewers.

## Translations and misfits

- **"We'd write property tests if we had time":** that is an unnamed hypothetical, and it grades
  TASTE-ONLY. The axis asks whether the property statement is writable in one sentence *now* —
  writing it costs a minute, and refusing the minute is the answer.
- **Partial oracles graded as whole-component:** a codec with roundtrip laws inside a product whose
  matching heuristics have no oracle is STRONG-on-the-codec, TASTE-ONLY elsewhere. Record
  per-surface grades with their denominators rather than averaging into a meaningless PARTIAL.

## Skip when

Never skip the quick question — the one-sentence attempt is the whole main pass, and the rider is
one name plus one calendar check in the same breath. There is no expensive enumeration here; the
only skippable work is per-surface denominator splitting on a component whose single oracle visibly
spans everything it ships.
