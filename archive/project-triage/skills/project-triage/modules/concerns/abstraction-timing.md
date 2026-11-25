# Concern 7: Abstraction timing — vocabulary first vs extract after repetition

## The tension

- **Design the vocabulary up front.** The data model is the design medium: get the domain's nouns,
  states, and relationships into types first, and the code that follows is largely forced — a
  correct vocabulary makes wrong programs hard to write and reviews fast, because disputes happen
  at the model, where they are cheap. Naming late means every early module bakes in a private,
  slightly-wrong ontology that must be unpicked at the moment of maximum entanglement.
- **Extract only after repetition.** Abstraction is compression, and you cannot compress a signal
  you have only seen once: factor only when the second concrete occurrence shows you what actually
  varies (Casey Muratori, "Semantic Compression"). Premature vocabulary is a guess that hardens —
  callers accrete against the wrong noun, and the wrong abstraction is harder to remove than the
  duplication it replaced. Optimize for deletability: code that was never abstracted can simply be
  thrown away when its assumption dies (tef, "Write code that is easy to delete, not easy to
  extend").

Both poles agree the vocabulary matters; they disagree on when the evidence for it exists. The
axes answer that question: how stable are the requirements, and how many repetitions does the
calendar even hold?

## Decided by

- **Requirements volatility × modification horizon (primary — the horizon caps the volatility
  answer):** THROWAWAY → never abstract, even at FIXED-SPEC — there is no "after repetition"
  before the decommission date, so extraction is pure cost. INSTITUTION → repetition is already on
  the calendar; extracting the domain vocabulary pays at adoption, and FIXED-SPEC + INSTITUTION is
  the full up-front-design cell. Between the caps: FIXED-SPEC → design the vocabulary up front
  (the signal is already complete — the signed criteria are the second occurrence); DISCOVERING →
  extract after repetition, because early names will be wrong names and each one taxes every
  pivot.
- **Commitment reversibility (contributing, three rules):** frozen-surface vocabulary — field
  names, message types, error codes — is designed before first ship regardless of volatility;
  there is no second naming pass on a wire protocol with un-upgradeable consumers. CAMPAIGN
  interfaces get up-front vocabulary even where the volatility/horizon joint says extract: a wrong
  noun in names, shapes, token taxonomy, or error contracts costs a campaign across N teams'
  review queues per correction, while LOCAL interfaces leave extract-after-repetition standing.
  LANDLORD → the adapter seam isolating every landlord touchpoint is designed first, before any
  feature vocabulary — the platform boundary is the first abstraction, not an extracted one.

## What each pole implies concretely

**Vocabulary first:** a written domain model — the entities, their states, the legal transitions —
before feature code; types named in the domain's own terms and reviewed with the stakeholder who
signed the criteria; interface nouns, error contracts, and token taxonomies fixed before the first
consumer; the model treated as the artifact that code merely elaborates.

**Extract after repetition:** write the first occurrence concretely, inline, with no speculative
parameters; on the second occurrence, diff the two and factor exactly what repeated — nothing
that varied; prefer duplication over a wrong abstraction, since duplication's cost is visible and
linear while a wrong abstraction's cost compounds through every caller; keep modules deletable —
few cross-references, dependencies pointing one way — so a dead assumption exits as a directory
removal.

## Default when undecided

Extract-after-repetition for the interior, with the one exception already decided elsewhere: any
surface known frozen gets its vocabulary pass before ship. Waiting degrades gracefully — the cost
of lateness is visible duplication, refactorable when the pattern confirms itself. Guessing early
degrades badly: the wrong abstraction recruits callers, and unwinding it costs more than the
duplication it prevented ever would.
