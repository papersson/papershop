# Concern 6: Test evidence — examples vs properties vs simulation

## The tension

Three poles, not two, and each is the strongest form of evidence in some regime:

- **Readable examples.** Concrete cases with human-judged diffs — snapshot/expect tests — are
  documentation that executes: cheap to write, legible to the next maintainer, and the only form
  that works when correctness is a judgment call. Their weakness is the author's imagination:
  they sample the inputs someone thought of.
- **Generated properties.** State the law once — "serialize(parse(x)) == x", "output matches the
  model" — and let the generator sample thousands of inputs nobody imagined, shrinking failures to
  minimal counterexamples; one property against a model catches what dozens of hand-picked
  examples miss (John Hughes, "Testing the Hard Stuff and Staying Sane"). Their precondition is an
  oracle: without a statable law, generation has nothing to check.
- **Deterministic simulation.** Make every nondeterminism source injectable, then run the whole
  system through compressed decades of scheduled faults — partitions, crashes, disk errors — with
  every failure replayable from a seed (the FoundationDB pattern; Joran Dirk Greef, "TigerStyle").
  The only form that reaches distributed-timing bugs; also the most expensive, because determinism
  is a design commitment bought up front, not a test style bolted on.

## Decided by

- **Fault reproducibility × writer topology (primary — picks the form):** SEEDED + MULTI-NODE →
  whole-system simulation pays, and the contention answer picks the first-class scenario family
  (CONVERGENT → partition-heal merge storms and divergence-then-reconcile runs; EXCLUSIVE →
  split-brain fencing races and failover under partition); SESSION-MASS adds mass-reconnect
  thundering herds as a simulated scenario. REPLAYABLE with a simple input space → property tests.
  ENVIRONMENTAL without seams → examples plus fault injection, with coverage recorded as
  explicitly soft.
- **Oracle strength (scopes the choice):** STRONG → generated property/differential tests *within
  the recorded coverage denominator*; surface outside it is graded separately. TASTE-ONLY →
  curated examples are the honest ceiling — generated tests against no oracle are theater.
  THEORY-ABSENT promotes the corpus from regression aid to primary and near-sole evidence,
  deliberately expanded toward characterization coverage.
- **Data gravity (regime-specific corpora and flags):** FROZEN-STANDARD → conformance corpus
  against the published standard plus malformed-frame rejection tests; ACCRETING-PRODUCER →
  round-trip and cross-version tests first-class (new reader on old data, old reader on new);
  ADVERSARIAL → fuzzing mandatory on the parsing path, overriding whatever the oracle grade
  suggests — attackers sample the worst case, not the distribution; OBSERVED-SECRET →
  observer-channel evidence — statistical timing-leak tests, and fault-injection countermeasure
  tests on attacker-held hardware — since no functional oracle sees a side channel.
- **Requirements volatility's horizon flag:** THROWAWAY → zero tests is the economical pole;
  eyeball verification suffices before a named decommission date. INSTITUTION → a curated
  regression corpus becomes the contract that survives rotating maintainers.
- **Defect consequence's assurance flag:** AUDITED changes the evidence's required *form*, not its
  kind — signed, immutably retained, auditor-sampleable packets tied to change tickets; rotating
  CI logs and undocumented local runs do not count as evidence at all.
- **Commitment reversibility's substrate flag:** LANDLORD → a host-version matrix across the
  landlord's release channels, tracking announced deprecations, is first-class evidence;
  STABLE-SUBSTRATE → that matrix is speculative weight.

## What each pole implies concretely

**Examples:** expect/snapshot tests with reviewable diffs; each example named for the requirement
it witnesses; the corpus doubles as documentation and, under DISCOVERING, as discardable
requirement records.

**Properties:** a one-sentence law per surface, generators biased toward edges, shrinking on by
default; a reference model where one exists; coverage claims scoped to the oracle's denominator.

**Simulation:** nondeterminism behind seams from day one; a scheduler that explores interleavings
and injects faults; every failure a seed that replays bit-for-bit; scenario families chosen by the
topology's contention answer.

## Default when undecided

Curated examples. They are the cheapest to start, never claim more than they show, and remain
useful under every later escalation — properties and simulation both *add to* an example corpus
rather than replacing it. Wrongly defaulting to generation fakes confidence without an oracle;
wrongly defaulting to simulation spends the determinism purchase before knowing it pays.
