# Concern 10: Agent delegation depth — delegate to the substrate vs human-held theory

## The tension

- **Delegate where the substrate checks.** Where a machine-checkable substrate exists — types,
  tests, a replay harness, a reference oracle — an agent can iterate against ground truth faster
  than a human, and the human's job moves up a level: review the oracle, not the diff. A
  type-checked pure refactor is trustworthy for reasons that have nothing to do with who wrote
  it; withholding delegation there buys nothing but latency.
- **The theory lives in people.** A program is not its text: it is a theory held by its builders —
  why the code is shaped this way, which behaviors are load-bearing, what a surprising output
  means — and that theory cannot be recovered from the artifact alone (Peter Naur, "Programming as
  Theory Building"). An agent rebuilds its picture from zero each session and retains nothing;
  and where the feedback signal is soft, agents optimize the signal rather than the intent —
  reward hacking decouples green checks from quality precisely where checks are weakest. Deep
  delegation without an oracle produces plausible text no one holds a theory of.

Both poles are conditional on the same two facts: how strong the machine-checkable oracle is, and
whether a living adjudicator still holds the theory.

## Decided by

- **Oracle strength × theory presence (primary — joint, scoped to the oracle's coverage
  denominator):** deep delegation never silently extends past what the oracle sees; on surface
  outside the denominator the effective grade defaults to TASTE-ONLY and agent changes revert to
  author-adjudicated diffs. STRONG + THEORY-RESIDENT → deep delegation within the denominator;
  humans review the oracle, not the diff. PARTIAL/TASTE-ONLY + RESIDENT → the resident adjudicator
  makes author-adjudicated change the economical pole; building heavier substrate is speculative
  weight. THEORY-ABSENT with an oracle below STRONG → the human review gate is theater (reviewers
  cannot tell a bug from a load-bearing quirk); the dominant work *before* any delegated change is
  substrate construction — characterization tests pinning current behavior, an executable spec —
  with interim changes conservatively small. STRONG + ABSENT → delegate against the oracle,
  treating all behavior outside its coverage as frozen.
- **Defect consequence (caps that apply independently of oracle grade):** UNRECOVERABLE/HARM caps
  delegation below what the oracle permits — the oracle itself may be wrong, so a human review
  gate stays. AUDITED → a second named human approver distinct from the author is mandatory on
  every production change, technically enforced; agent-autonomous deploys stay off the table even
  if the oracle later reaches STRONG.
- **Commitment reversibility:** frozen surfaces keep a human carrying compatibility theory — what
  old consumers depend on is not machine-checkable from the current repo; CAMPAIGN interfaces keep
  a human carrying migration-cost theory even when consumers are forceable. The LOCAL + FLUID
  interior is the deep-delegation zone.
- **Fault reproducibility:** a replay harness is substrate an agent can iterate against; without
  it, a human must adjudicate bug-vs-weather on every failure the agent hits.
- **Resource pressure:** ENVELOPED adds the resource model — linker map, stack-depth analysis,
  energy budget — to the substrate an agent must iterate against; without those artifacts,
  delegated code is correct-but-unlinkable and a human adjudicates fit.
- **Horizon flag:** THROWAWAY → building substrate for delegation is waste; INSTITUTION →
  substrate for future drive-by or agent maintainers is rational investment at adoption.

## What each pole implies concretely

**Delegate:** invest in the substrate first — oracles, characterization corpora, replay seams,
resource-model artifacts — then hand agents the loop against it; scope each delegation to the
oracle's denominator and say so in the task; human attention moves to oracle quality, coverage
gaps, and the diffs the substrate cannot grade.

**Hold:** named humans own the frozen surfaces, the CAMPAIGN interfaces, and every path under a
consequence or audit cap; review stays diff-level where no oracle adjudicates; agent output there
is treated as a draft from a contributor with no memory — useful, never authoritative; the theory
is deliberately kept resident (the adjudicator actually reviews changes this quarter, and
succession is planned, not discovered).

## Default when undecided

Hold with humans, delegating only what the *existing* substrate already checks — no delegation on
credit against substrate not yet built. Under-delegation degrades gracefully: the cost is
throughput, recoverable the day the oracle lands. Over-delegation degrades badly: unreviewed
plausible changes accumulate where no one holds the theory, and rebuilding a theory from text is
the one cost Naur says you cannot pay down cheaply.
