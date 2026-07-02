# Concern 3: Values vs places — immutability everywhere vs bounded in-place mutation

## The tension

- **Values.** An immutable value is a fact: it can be shared without coordination, cached without
  invalidation, compared by content, and reasoned about without asking who else holds a reference
  (Rich Hickey, "The Value of Values"). State-in-state-out signatures make time explicit — the
  function that takes a world and returns a new world is testable by construction, and most
  concurrency bugs are impossible against data that never changes.
- **Places.** Copying is not free: at scale the allocator, the copies, and the GC pauses *are* the
  workload, and a hard memory envelope may not fit two generations of the state at all. A bounded
  mutable core — one writer, preallocated storage, in-place updates — is how data-oriented systems
  hit their arithmetic. The two poles meet at the boundary: an immutable, append-only log gives
  the system value semantics *between* components while each component mutates freely inside
  (Jay Kreps, "The Log"). Mutation is not the danger; unowned, shared mutation is.

## Decided by

- **Resource pressure × writer topology (jointly primary — motive and safety):** resource pressure
  supplies the motive: HOT → bounded in-place mutation behind a value-semantics interface;
  ENVELOPED → places wherever copies do not fit the budget — static pools sized at compile time,
  no heap after init, ring-buffer reuse — forced *by arithmetic, not taste*; COOL + UNBOUNDED →
  immutability everywhere; WARM resolves to COOL (mutation buys nothing when the wire dominates).
  Writer topology supplies the safety: SINGLE-WRITER → in-place mutation is safe wherever heat
  wants it; MULTI-WRITER-ONE-NODE → immutable values at every sharing boundary; MULTI-NODE →
  state moves between nodes as values, whatever happens inside a node. Places win only where
  motive and safety agree.
- **Tail obligation (secondary, one-directional):** SOLD → pauses are the product defect, so
  places win on the request path even at COOL — a 200-QPS gateway with a contracted p99 has no
  heat but cannot tolerate allocation or GC spikes. NONE returns the decision to resource
  pressure.
- **Fault reproducibility (partial):** SEEDED → immutable event inputs at the boundary; the replay
  substrate depends on inputs being values, whatever the core does with them.
- **Data gravity's OBSERVED-SECRET flag:** zeroization is obligatorily a places discipline — key
  material lives in pinned, overwritable buffers and is scrubbed in place at end of use. Every
  value-semantics copy of a secret is an un-scrubbable leak, so "immutability everywhere" is the
  wrong pole on the secret path even at COOL, UNBOUNDED, and SINGLE-WRITER.

## What each pole implies concretely

**Values:** persistent/immutable collections as the default; state transitions as pure functions
old-state → new-state; snapshots are free, undo is a pointer, and test fixtures are literals;
sharing across threads without locks; identity modeled as a succession of values, not a mutating
place.

**Places:** a single-writer core owning preallocated storage; updates in place with no allocation
on the steady-state path; the mutable region fenced behind an interface that accepts and returns
values, so callers never see a half-updated place; an append-only log at the boundary absorbing
value semantics for everyone downstream; explicit scrub-on-release where secrets live.

## Default when undecided

If heat is DEFERRED or the topology unsettled: values, with mutation confined to whatever core the
first profile actually names. A values codebase that turns out to need places degrades into a
measurable performance problem, fixable by fencing one hot core behind its existing value
interface; a places codebase that turns out to have a second writer degrades into aliasing and
race bugs — the failure mode that is silent, unreproducible, and paid for at the worst time.
