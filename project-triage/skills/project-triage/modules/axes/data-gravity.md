# Axis 5: Data gravity

**Quick question.** For every sink this component writes, can you name one concrete reader NOT
deployed in lockstep with you? Always ask both riders: who is the least-trusted party who can write
to your inputs, and is a secret observable through execution behavior? **Deep-pass gate — the
expensive axis:** quick pass = gravity class + both riders only; run the per-format regime
enumeration only for integration-heavy components (3+ boundary-crossing formats).

## Full question (deep pass)

For every sink this component writes, name one concrete reader NOT deployed in lockstep with you —
another team or organization, clients upgrading on their own schedule, or a future version reading
old data. **Lockstep is the test; persistence is the amplifier.** Cannot name one = IN-PROCESS.

**Per-format evolution regime** (for each boundary-crossing format, input or output): who can change
this format, and does the change arrive without your agreement? **FROZEN-STANDARD** — fixed by an
external published standard with no unknown-field mechanism (fixed-width or CRC-framed binary:
Modbus, CAN); nobody accretes fields, ever. **NEGOTIATED-STABLE** — changes only by bilateral
agreement or a version negotiation you participate in. **ACCRETING-PRODUCER** — a counterparty adds
fields on its own release schedule and expects tolerant readers (partner JSON/EDI, webhooks).

**Rider 1 — adversarial exposure** (same channel walk, zero extra cost): for each INPUT, name the
least-trusted party who can produce bytes this component parses. The test is **enrollment and
leverage, NOT authentication**: any writer from an open-enrollment population, or over whom you
hold no employment or contractual leverage, makes the boundary **ADVERSARIAL** — a login page in
front of open enrollment does not make its writers trusted, and untraceable provenance (the
Log4Shell pattern) defaults to ADVERSARIAL. Before recording TRUSTED-ONLY, name the attacker payoff
reachable through the input — it does not flip the flag while leverage holds, but is the recorded
falsifier.

**Rider 2 — secret observability** (same trust pass; asked **unconditionally** — TRUSTED-ONLY does
not skip it, because the observer need not be a writer): is there material that must stay
confidential from anyone who can observe execution or error behavior? Name the secret (private key,
password material, session token, plaintext) and the observer channel (network timing, co-tenant
cache/branch predictor, power/EM or faults on attacker-held hardware, error-timing/content
differences). No nameable pair = NO-OBSERVED-SECRET.

## Answers

- **IN-PROCESS** | **PERSISTED-SINGLE-OWNER** (falsifier: the Hyrum event — first non-lockstep
  reader) | **CROSSES-BOUNDARIES** (per-format regime as above).
- Input flag: **TRUSTED-ONLY** (named payoff falsifier) | **ADVERSARIAL**. Secret flag:
  **OBSERVED-SECRET** (named secret and channel) | **NO-OBSERVED-SECRET**.

## Day-one checkability

Enumerate sinks from the brief (DB table, file format, queue topic, wire response); the "name one
concrete reader" clause makes the answer falsifiable, not vibes.

## Decides

- **Concern 5, schema openness (primary):** IN-PROCESS → closed ADTs, exhaustive matching.
  PERSISTED-SINGLE-OWNER → closed types plus owned, tested migrations. CROSSES-BOUNDARIES splits by
  regime: FROZEN-STANDARD → exhaustive closed ADTs, a strict total parser, and *zero*
  versioning/tolerant-reader machinery — accretion machinery on a frozen standard is dead weight;
  ACCRETING-PRODUCER → open maps, must-ignore-unknown, version negotiation; NEGOTIATED-STABLE →
  closed types per negotiated version. A Hyrum-flipped sink moves to additive-only evolution with
  explicit versioning. ADVERSARIAL reverses Postel: strict closed parsing, reject unknown fields;
  where it meets ACCRETING-PRODUCER, tolerate contract-mandated unknowns but strictly validate every
  field read, and bound total input size.
- **Concern 1, invariant placement (boundary line):** boundary-crossing input is validated at
  runtime into closed internal types; type-level proof applies only inboard of that line.
  ADVERSARIAL → total parser producing evidence-carrying types; crashing boundary asserts become a
  DoS vector. OBSERVED-SECRET → error behavior on the secret path must be uniform in timing and
  content with respect to secret bits — secret-independent checks (double-compute-and-compare,
  constant-time comparison) replace data-dependent crashing asserts there.
- **Concern 6, test evidence (partial):** FROZEN-STANDARD → conformance corpus, malformed-frame
  rejection tests. ACCRETING-PRODUCER → cross-version round-trip tests first-class. ADVERSARIAL →
  fuzzing mandatory on the parsing path, overriding the oracle axis — attackers sample the worst
  case, not the distribution (Heartbleed). OBSERVED-SECRET → dudect-style timing-leak tests, plus
  fault-injection tests on physically held hardware.
- **Concern 2, layout (overrides resource pressure on named paths):** ADVERSARIAL → never trade
  memory/type safety for layout on the parsing path. OBSERVED-SECRET → the secret path goes
  branchless and flat regardless of heat or envelope: no secret-dependent branches or indexing,
  fixed-size buffers, uniform-latency errors.
- **Concern 3, values vs places (via the secret flag):** OBSERVED-SECRET → zeroization is an
  obligatory places discipline; every value-semantics copy of the secret is an un-scrubbable leak.
- **Concern 4, crash aftermath (partial, via flag):** ADVERSARIAL → sandbox-and-supervise the
  parsing stage for containment, but hunt the faults to extinction — the attacker replays the
  crashing input at will (crash-loop DoS).

## Re-fire triggers

- **Regime:** first field addition observed on a FROZEN-STANDARD or NEGOTIATED-STABLE format demotes
  it to ACCRETING-PRODUCER.
- **Egress (the Hyrum event, after Hyrum's Law):** first non-lockstep reader on an existing sink — a
  new reader pointed at your path, a field request from a party you do not deploy with, or
  historical partitions read by anyone — re-fires this axis; PERSISTED-SINGLE-OWNER carries this as
  its explicit falsifier. Commitment reversibility's uncontrolled-consumer trigger, firing on a data
  sink, ALSO re-fires this axis.
- **Rider 1:** any deployment-boundary change — newly exposed outside the org, new ingestion
  channel, new accepted format. **Rider 2:** secrets newly enter the computation, or deployment
  moves onto observable substrate.

## Translations and misfits

- **Sinks the component itself owns:** the regime taxonomy is producer-oriented — for your own
  tables, "who can change this without your agreement" answers "me"; no regime value fits. Skip the
  regime question there; route owned sinks through PERSISTED-SINGLE-OWNER plus the Hyrum trigger.
- **"A future version reading old data"** makes a sink PERSISTED-SINGLE-OWNER; it does NOT alone
  make it CROSSES-BOUNDARIES while you own the store and its migrations.
- **Loosely implemented published standards** (camt.053-style XML) sit between regimes. Classify by
  the without-your-agreement test — counterparties shipping divergence on their own schedule read
  as ACCRETING-PRODUCER — note low confidence, and let the demotion trigger arbitrate.

## Skip when

Skip the per-format regime enumeration below 3 boundary-crossing formats — read the regime off the
formats directly. Never skip the two riders: they ride the same channel walk at near-zero cost,
rider 2 is unconditional by design, and a skipped rider is its promotion bet's recorded failure.
