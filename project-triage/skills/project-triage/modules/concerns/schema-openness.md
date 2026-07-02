# Concern 5: Schema openness — closed types vs open accreting maps

## The tension

- **Closed.** Ten lines of algebraic data types can be a hologram of the whole system: every case
  enumerated, every combination either meaningful or unrepresentable, and the compiler flags every
  site a new case must touch. Exhaustive matching turns schema change from a grep into a
  checklist, and illegal states stop existing rather than being tested for.
- **Open.** Rich Hickey's counter ("Effective Programs", "Maybe Not"): requiredness is contextual,
  not a property of the data — the same aggregate is "complete" for one consumer and partial for
  another, so baking one context's requirements into a closed record is a category error. Data
  that crosses systems and versions grows by accretion; closed records for sparse, changing
  information are an anti-pattern, and a reader that breaks on a field it never reads has
  manufactured its own fragility. Names should be self-standing; growth should never be breakage.

Both are right about different data: the closed pole describes an in-process model one compiler
sees whole; the open pole describes information flowing between parties who do not deploy
together. The concern is deciding which regime a given format actually lives in.

## Decided by

- **Data gravity (primary — gravity class × per-format evolution regime):** IN-PROCESS → closed
  ADTs with exhaustive matching. PERSISTED-SINGLE-OWNER → closed types plus owned, tested
  migrations; the first non-lockstep reader (the Hyrum event) flips that sink to additive-only
  evolution with explicit versioning. CROSSES-BOUNDARIES splits by the format's regime:
  FROZEN-STANDARD → exhaustive closed ADTs over the standard's cases, a strict total parser that
  rejects malformed input, and *zero* versioning/tolerant-reader machinery — accretion machinery
  on a frozen standard is dead weight and a silent-misparse source; NEGOTIATED-STABLE → closed
  types per negotiated version with explicit version negotiation at the boundary;
  ACCRETING-PRODUCER → open accreting maps, must-ignore-unknown, tolerant readers. The
  ADVERSARIAL flag *reverses* Postel: strict closed parsing, reject unknown fields — tolerance
  toward an attacker is attack surface. Where ADVERSARIAL meets ACCRETING-PRODUCER: tolerate the
  contract-mandated unknown fields, but strictly validate every field actually read and bound
  total input size.
- **Requirements volatility (contributing):** DISCOVERING → keep the moving periphery open even
  in-process; closing a model still being discovered into ADTs is premature, and each wrong
  closure costs a refactor of every exhaustive match.
- **Commitment reversibility's substrate flag (contributing):** LANDLORD → capability negotiation
  toward the platform boundary — feature detection, graceful capability loss — a boundary the
  gravity walk never records, because the platform API is called, not parsed.

## What each pole implies concretely

**Closed:** sum types enumerating every case; exhaustive matches with no default arm, so additions
are compile errors; parse boundary input once into these types; schema change lands as one commit
plus an owned migration; unknown input is a rejection, not a passenger.

**Open:** map/dictionary representations with namespaced, self-standing keys; must-ignore-unknown
readers that carry unrecognized fields through round-trips untouched; additive-only schema
evolution — new fields, never repurposed ones; per-consumer requiredness checked at the point of
use, not baked into the type; explicit version negotiation where a counterparty offers it.

## Default when undecided

If the gravity class is contested — you cannot confirm whether a non-lockstep reader exists —
default closed, and treat the first foreign field or unknown reader as the recorded falsifier
that flips the surface open. A wrongly closed schema fails loudly at the exact moment the
assumption breaks (the parser rejects, the migration collides) and the fix is localized; a wrongly
open schema fails silently forever — lost exhaustiveness, misspelled keys, and requiredness bugs
that no compiler ever flags.
