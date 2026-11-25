# Concern 2: Type safety vs memory layout — evidence-carrying types vs cache-conscious layout

## The tension

- **Evidence in the types.** A boolean tells you *that* a decision was made, not *what* was
  learned; the fix is types that carry the evidence — an `Option<NonEmpty<T>>` instead of a flag
  plus an unchecked access (Robert Harper, "Boolean Blindness"). Rich domain types make whole bug
  classes unwritable, and their cost is invisible on code the machine barely notices.
- **The machine bills you for that richness.** A one-bit fact stored as a tagged union can cost a
  word of padding replicated across a million-element array — the difference between fitting in
  cache and thrashing it. Data-oriented design answers with struct-of-arrays, packed encodings,
  and integer indexes in place of pointers, cutting both memory and indirection (Andrew Kelley,
  "Practical Data-Oriented Design"). The cost of abstraction-heavy style is not folklore; it is
  measurable at integer multiples on real loops (Casey Muratori, "Clean Code, Horrible
  Performance").

Both poles are right about their own regime: evidence-carrying types are nearly free at CRUD
rates, and layout discipline is nearly mandatory at 10^6 instances. The mistake in each direction
is exporting the rule out of its regime — flattening a settings page, or shipping a pointer-chasing
particle system.

## Decided by

- **Resource pressure (primary — sole decider in the set; the heat × envelope joint):** HOT or
  ENVELOPED → flat/packed/index layout *on the named hot or budget-bound types only*; the
  prescription is scoped to the types and loop the axis named, never codebase-wide. COOL or WARM
  plus UNBOUNDED → evidence-carrying types everywhere; cache-conscious mutation buys nothing when
  the wire or the database dominates. No budget artifact means COOL, so "might need to scale"
  never licenses the layout pole.
- **Data gravity flags (override on named paths, in both directions):** ADVERSARIAL → never trade
  memory/type safety for layout on the parsing path, even where resource pressure licenses it —
  attacker-reachable index arithmetic is the classic exploit substrate. OBSERVED-SECRET → the
  named secret path must be branchless and flat regardless of heat or envelope: no
  secret-dependent branches, no secret-indexed memory access, fixed-size buffers, uniform-latency
  error paths — overriding "evidence-carrying types everywhere" on exactly that path, because
  Option/enum branching on secret-derived values is the defect being engineered out. The two
  overrides coexist; they govern different paths.

## What each pole implies concretely

**Evidence-carrying types:** domain newtypes instead of primitives; sum types over flag
combinations; `Option`/`Result` instead of sentinels; invariants captured at construction so
downstream code takes evidence as given; accept the padding, the tags, and the pointer
indirection, because on this path they are noise.

**Cache-conscious layout:** struct-of-arrays for the named hot type; enums packed to their real
bit-width; u32 indexes into arenas instead of pointers (halving reference size and enabling
relocation); existence encoded by array membership rather than a stored flag; layout changes
justified by a profile or a budget artifact, and confined to the named types. The bridge both
poles should take: branded/distinct index types (`EntityId(u32)` rather than bare `u32`) retain
the semantic evidence at zero layout cost — index-based layout does not require untyped indexes.

## Default when undecided

If heat is DEFERRED or the envelope unclear: evidence-carrying types everywhere — this is the
axis's own provisional output, and it degrades more gracefully. A typed-but-slow hot path
announces itself in the first profile and can be flattened type-by-type behind its interface;
a prematurely flattened codebase hides its lost invariants until they resurface as index-confusion
bugs, and re-deriving the type structure from bare integers is archaeology.
