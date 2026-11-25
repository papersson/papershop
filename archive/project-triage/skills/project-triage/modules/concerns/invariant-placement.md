# Concern 1: Invariant placement — type-level proof vs crash-on-violation assertions

## The tension

Both poles share an architecture before they split: bugs and recoverable conditions are different
things deserving different mechanisms — abandonment for programming errors, typed errors for
expected conditions; routing both through one exception funnel gets reliability structurally wrong
(Joe Duffy, "The Error Model"). The dispute is *where* the bug-detection line runs:

- **Prove it in the types.** Make illegal states unrepresentable (Yaron Minsky), and convert
  validation into parsing: a check that returns a more-informative type cannot be forgotten
  downstream, because the evidence travels with the value (Alexis King, "Parse, Don't Validate").
  A violation prevented at compile time has zero runtime cost, zero crash window, and no
  reachability question — the invariant holds on paths no test ever executes.
- **Assert it, densely, and crash.** Runtime assertions state invariants the type system cannot
  reach — cross-field arithmetic, temporal ordering, resource bounds — and turn latent corruption
  into an immediate, attributable stop (Joran Dirk Greef, "TigerStyle": assertions on in
  production, paired positive/negative checks). Asserts are cheap to write, cheap to delete, and
  verify the *running* system, including the compiler's and hardware's own output.

The poles are complements over different invariant classes; the real decision is the intensity and
budget of each, which is a function of what a violation costs.

## Decided by

- **Defect consequence (primary — the severity ladder sets proof-vs-assert intensity):**
  UNRECOVERABLE/HARM → both at maximum: type-level proof *plus* independent runtime interlocks
  that crash before corruption reaches an actuation path. BOUNDED-LOSS → interlock intensity
  scales with the recorded loss bound (a rerun priced in millions buys per-step invariant guards
  and checksum gates on checkpoints). RETRY-AND-SHRUG → crashing assertions alone are the
  economical, adequate pole; proof engineering is optional polish.
- **Data gravity (draws the boundary-validation line, plus two flag rules):** boundary-crossing
  input can never be correct-by-construction — it is parsed at runtime into closed internal types,
  and type-level proof applies only inboard of that line. ADVERSARIAL → the boundary gets a total
  parser producing evidence-carrying types; crashing asserts *at the boundary* become a DoS vector
  an attacker replays at will. OBSERVED-SECRET → error behavior on the secret path must be uniform
  in timing and content with respect to secret bits: data-dependent crashing asserts are an oracle
  for the observer, so that path uses secret-independent checks (constant-time comparison,
  verify-after-sign, double-compute-and-compare) even where severity would prescribe rich asserts.
- **Fault reproducibility (partial):** REPLAYABLE → static proof pays extra, because every
  violation that does slip through is permanently fixable. ENVIRONMENTAL → runtime assertions
  crashing into a supervisor are the workable form; proofs cannot quantify over weather.
- **Resource pressure (modulates the mechanism):** HOT → construction-time invariants on the named
  hot types plus debug asserts at core entry, keeping per-iteration checks out of the loop.
  ENVELOPED → compile-time sizing proofs (static asserts on buffer, stack, and binary bounds)
  preferred over dynamic checks that themselves cost RAM.
- **Oracle strength (conditional):** a STRONG oracle that happens to be type-encodable flips
  compile-time proof from nicety to rent-payer; the flip fires only when it is encodable.

## What each pole implies concretely

**Proof:** smart constructors as the only way to obtain a domain type; parse raw input once into
refined types and pass evidence, never re-validate; sum types with exhaustive matching so a new
case is a compile error; phantom/branded types for units and states; the boundary parser is total
— every input either becomes a valid internal value or a typed rejection.

**Assert:** assertions enabled in production; preconditions, postconditions, and paired checks on
every state transition; crash before the corrupt write, never after; every assert names the
invariant it guards so the crash report is a diagnosis; independent interlocks (checksums,
balance-to-zero gates) that do not share code with the logic they check.

## Default when undecided

If defect consequence is contested: assert-dense with Duffy's partition, and record the proof
investment as pending the severity call. Assertions degrade gracefully when the call was wrong —
they are additive, deletable, and already crash before corruption if severity turns out high —
whereas a type-proof architecture adopted at the wrong intensity restructures the codebase and
still needs the asserts for everything types cannot say.
