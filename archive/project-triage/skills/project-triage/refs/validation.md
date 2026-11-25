# project-triage: the classification axis set

**Status:** validated draft — **Date:** 2026-07-02
**Method:** five independent derivations of a candidate axis pool; per-axis audit (checkability, decision relevance, aliasing, split/merge); judged construction of a 9-axis set; four adversarial validation rounds; round 5 validation-only attack (4 lenses, 12 claims, 1 survived independent refutation) and a dogfood runnability audit (3 real briefs: avg 29 questions, ~37 minutes — OVER the 20-minute budget). **1 unresolved breach** (listed verbatim at the end).

## What this is

Given a software project, component, or task, answer nine questions about observable facts of the thing itself. Each answer resolves specific engineering tensions — it says which pole of a contested trade-off wins *for this component* and why. The output is a committal, falsifiable record: every answer names the artifact it was read from, and every provisional answer carries a named re-fire trigger (the concrete future event that reopens the question). Target run time: ~20 minutes with the project brief in hand.

Several axes carry **riders**: cheap sub-questions asked in the same enumeration pass as the main question, harvesting a second fact at near-zero extra cost. Each rider carries a **recorded bet**: the named observable event that, if it occurs, promotes the rider to a standalone axis verbatim. Bets keep the compression honest — if the piggybacking ever causes the sub-question to be skipped in practice, the compression was wrong and the set self-corrects.

## The ten concerns the axes decide

Each is a genuine tension with two defensible poles held by serious practitioners. The axes are the conditions that decide which pole wins for a given component.

1. **Invariant placement** — enforce correctness via compiler/type-level proof vs runtime assertions that crash.
2. **Type safety vs memory layout** — evidence-carrying types vs cache-conscious struct/array layout that trades type safety away.
3. **Values vs places** — immutability everywhere vs bounded in-place mutation for the hot core.
4. **Crash aftermath** — hunt and eliminate every bug vs supervise-and-restart.
5. **Schema openness** — closed algebraic data types for in-process models vs open accreting maps for data crossing systems and versions.
6. **Test evidence** — human-readable examples vs generated property tests vs deterministic whole-system simulation.
7. **Abstraction timing** — design the domain vocabulary up front vs extract abstractions only after repetition.
8. **Design-phase weight** — heavy up-front design/specs vs ship-and-iterate.
9. **Coordination and tail latency** — eliminate coordination by restating the problem vs manage it with machinery; whether a latency distribution is part of the product.
10. **Agent delegation depth** — how much implementation can be delegated to AI agents vs held by humans who carry the system's theory.

---

## Axis 1: Fault reproducibility

**Question.** Inventory the component's nondeterminism sources (clock, RNG, scheduling, network peers, disk, third-party services, user timing). Classify each as capturable, injectable behind a seam, or not virtualizable at a cost you would pay — and for that last class, name the concrete source (partition, disk corruption, third-party semantics, human timing).

**Answers.**

- **REPLAYABLE** — failures replay bit-for-bit from captured inputs.
- **SEEDED** — every nondeterminism source is injectable; determinism is recorded as a *design commitment*, not a finding (the FoundationDB/TigerBeetle pattern: buy back determinism in a multi-node system by design).
- **ENVIRONMENTAL** — the fault population is not enumerable or virtualizable at acceptable cost.
- Layered systems are recorded as **SEEDED-core / ENVIRONMENTAL-shell**.

**Day one.** Answerable by inventory from the brief or architecture sketch — the dependency surface is observable before any failure occurs. SEEDED is a commitment you record now, so no hindsight is needed.

**Re-fire trigger.** First nondeterminism source added that is not injectable behind an existing seam (new third-party dependency, new hardware peripheral, new peer protocol).

**Decides.**

- **Concern 4, crash aftermath (primary — pole only; the supervision *unit* is decided by Axis 4's restart flag):** REPLAYABLE/SEEDED → hunt-and-eliminate, since each fix permanently shrinks the fault population. ENVIRONMENTAL → supervise-and-restart for the transient class. Layered → eliminate inside, supervise the shell.
- **Concern 6, test evidence (joint with Axis 4):** SEEDED + multi-node → deterministic whole-system simulation. REPLAYABLE with a simple input space → property tests. ENVIRONMENTAL without seams → examples plus fault injection, with coverage recorded as explicitly soft.
- **Concern 1, invariant placement (partial):** ENVIRONMENTAL → runtime assertions crashing into a supervisor. REPLAYABLE → static proof pays, because violations are permanently fixable.
- **Concern 10, agent delegation (partial):** a replay harness is substrate agents can iterate against; without it a human must adjudicate bug-vs-weather.
- **Concern 3, values vs places (partial):** SEEDED pushes event-sourced immutable inputs at the boundary.

---

## Axis 2: Resource pressure

**Question.** Two independently recorded sub-answers, read from two different artifacts.

**(a) Count heat:** name the most numerous data type this component owns and its innermost loop. Is there an artifact — budget document, written performance requirement, or a profile someone will hold you to — putting ~10^6+ live instances or ~10^6 ops/sec on that path? **No artifact means COOL provisionally.**

**(b) Envelope:** name the binding resource budget artifact (RAM bytes, flash bytes, energy per day, binary-size ceiling — read off the datasheet, BOM, or product spec) and estimate the component's working set. Budget within ~10× of the working set = ENVELOPED; otherwise UNBOUNDED.

**Answers.**

- Heat: **HOT** | **WARM** (IO/network-dominated) | **COOL** | **DEFERRED**.
- Envelope: **ENVELOPED** (named budget artifact within ~10× of working set) | **UNBOUNDED**.

**Day one / deferral.** Domain arithmetic usually settles heat immediately (10^5 entities × 60 Hz is HOT by multiplication; back-office CRUD is COOL by inspection). The artifact-or-COOL rule is the anti-inflation guard: "we might need to scale someday" does not make a component HOT. DEFERRED emits COOL's output provisionally — evidence-carrying types everywhere — rather than emitting nothing, and the named trigger re-fires the axis.

**Re-fire triggers.** For (a): first representative profile, or first written performance requirement. For (b), **decision-time**: a resource budget artifact newly attaching to the component — an SOW clause, a customer product spec, or the datasheet of a new deployment target — re-fires (b) *at signing time*, before any port or build begins. The envelope's outputs are day-one architectural commitments, so the trigger must fire when the commitment is made, not when it is missed. Incident-time backstops: first linker-map overflow, stack-depth failure, or battery-life/binary-size budget miss.

**Decides.**

- **Concern 2, type safety vs memory layout (sole decider in the set; joint of heat and envelope):** HOT or ENVELOPED → flat/packed/index layout *on the named hot or budget-bound types only*. COOL/WARM + UNBOUNDED → evidence-carrying types everywhere.
- **Concern 3, values vs places (the motive half; Axis 4 supplies the safety half):** HOT → bounded in-place mutation behind a value-semantics interface. ENVELOPED → in-place mutation wherever copies do not fit the budget: static pools sized at compile time, no heap after init, ring-buffer reuse — the envelope forces the places pole *by arithmetic, not taste*. COOL + UNBOUNDED → immutability everywhere. WARM resolves to COOL: cache-conscious mutation buys nothing when the wire dominates.
- **Concern 1, invariant placement (modulates):** HOT → construction-time invariants and debug asserts at core entry. ENVELOPED → compile-time sizing proofs (static asserts on buffer, stack, and binary bounds) preferred over dynamic checks that themselves cost RAM.
- **Concern 10, agent delegation (partial):** ENVELOPED adds the resource model to the machine-checkable substrate — the linker map, stack-depth analysis, and energy budget are artifacts a delegated agent must iterate against; without them delegated code is correct-but-unlinkable and a human must adjudicate fit-vs-doesn't.

---

## Axis 3: Tail obligation

**Question.** Is a latency distribution being sold? Point at the artifact: an SLA clause naming a percentile, a frame/tick budget, an alerting rule someone else owns on your p99, or a fan-out call site where one request awaits N of you.

**Qualification (on the alerting-rule artifact only):** it counts as SOLD only if its threshold was chosen *for this component* by a party who consumes its latency — a caller's stated budget, a contract clause, a product deadline, a frame budget. A template-provisioned or auto-onboarded alert pack, whose threshold would read the same number regardless of what this component does or who calls it, records SOFT — the alert measures the distribution but nobody consumes it. SLA percentile clauses and fan-out call sites are inherently consumer-derived and always qualify.

**Answers.** **NONE** | **SOFT** (treated as NONE with a watch trigger; includes template-provisioned alerts) | **SOLD**. No qualifying artifact = NONE/SOFT today.

**Day one.** Each artifact is a document or a call-graph edge, not a judgment call; absence is equally checkable. Demand the call site, not a prophecy of future fan-out.

**Upgrade trigger.** First contracted percentile, hard deadline, fan-out caller, or an alert threshold re-derived from a named consumer's budget.

**Decides.**

- **Concern 9, coordination and tail latency (the tail half; Axis 4 decides the machinery half):** SOLD → the distribution is a shipped feature; restate first, budget machinery for the remainder. NONE → tail machinery is speculative weight.
- **Concern 3, values vs places (secondary, one-directional):** SOLD → pauses are the product defect; places win on the request path even at COOL heat (a 200-QPS gateway with a contracted p99 has no heat but cannot tolerate pause spikes). NONE returns the decision to Axis 2.

---

## Axis 4: Writer topology

**Question.** From the deployment plan, take the maximum over all mutable state: one logical writer; multiple threads/tasks in one process; or network-separated writers. Two replicas behind a load balancer sharing a row count as MULTI-NODE — each replica looks single-threaded, and engineers reliably miss this unless prompted.

**If MULTI-NODE:** essential (write rate × state size exceeds one node, or survive-node-loss is required) or pre-sliced?

**If MULTI-NODE (either kind), contention sub-question:** pick the most contended object and ask: if two partitioned sides both accept a write to it, is there a merge that violates no business rule (**CONVERGENT**), or does some invariant require exclusivity or a single agreed order — a unit reserved at most once, a balance never negative, a lock with one holder (**EXCLUSIVE**)?

**Rider — Restart blast radius** (carried in the same deployment-plan pass): for each process, inventory what dies with it — live sessions/connections, accumulated in-memory state and where it rebuilds from — and write down the survivors' next 60 seconds: do N clients synchronously reconnect, re-authenticate, or recompute through a shared dependency? **PER-REQUEST** if a process death loses at most in-flight requests that retry through a balancer; **SESSION-MASS(N)** if one process death drops a nameable population of live sessions or discards state whose synchronized rebuild stampedes a shared dependency.

**Answers.** **SINGLE-WRITER** | **MULTI-WRITER-ONE-NODE** | **MULTI-NODE** (essential | pre-sliced; contention: **CONVERGENT** — with falsifier: first exclusivity/single-order rule attaching to this state — | **EXCLUSIVE**). Restart flag: **PER-REQUEST** | **SESSION-MASS(N named)**.

**Day one.** Read the topology *forced by requirements* (availability, geography, offline, data volume), not the topology someone sketched by habit — the essential-vs-pre-sliced sub-question is the guard against circularity, since topology is partly a design choice the triage output could itself inform.

**Re-fire triggers.** Main: any writer-count change in the deployment plan — a second writer process added, replication enabled, or the component newly deployed multi-region. Contention (invariant-side, distinct from the topology-side trigger, because the contention answer is a joint of topology AND business rules, and invariants change on the product calendar, not the deployment plan): a new business rule requiring exclusivity or a single agreed order — reservation, quota, balance, or lock semantics — attaching to already-replicated state re-fires the contention question *at feature-decision time*, before the feature ships. A CONVERGENT record carries this as its explicit falsifier. Rider: sessions-per-process grows 10×, or a new shared dependency enters the reconnect/rebuild path.

**Recorded bet (rider).** The rider form is correct only if the mutable-state walk reliably surfaces per-process ephemeral state; the first walk where writer-counting causes session mass to be skipped promotes Restart blast radius to a standalone axis verbatim.

**Decides.**

- **Concern 3, values vs places (the safety half; Axis 2 supplies the motive):** SINGLE-WRITER → in-place mutation safe wherever heat wants it. MULTI-WRITER → immutable values at sharing boundaries. MULTI-NODE → state moves as values.
- **Concern 9, coordination (the machinery half):** essential → restate before machinery, then the contention answer picks *which* machinery is load-bearing. EXCLUSIVE → agreement machinery IS the component once restatement fails: single-order commit, leader leases, fencing tokens on failover, bounded unavailability during partition. CONVERGENT → agreement machinery is the wrong move (it kills availability under partition, which is the product); build convergence instead: CRDT or three-way merge semantics per field, causality metadata (vector clocks / dotted versions), tombstone GC, conflict-surfacing UX. Pre-sliced → un-slice (the pattern of the well-documented Segment microservices-to-monolith reversal). SINGLE-WRITER → machinery is dead weight. State containing both kinds of object splits per object — the reservation ledger goes EXCLUSIVE while the cart stays CONVERGENT.
- **Concern 4, crash aftermath (partial):** MULTI-NODE → partial failure is a normal input; restart-and-recover paths are mandatory, and the contention answer picks their kind — CONVERGENT → resume cursors and anti-entropy merge on reconnect; EXCLUSIVE → lease expiry, leadership handoff, fencing on failover.
- **Concern 4, crash aftermath (granularity, joint with Axis 1):** Axis 1 picks the pole; the restart flag picks the supervision *unit*. PER-REQUEST → process-granularity crash-freely: assert liberally, let the supervisor restart the process, blast radius is one request. SESSION-MASS → the fault domain must shrink to the session: assertion failures in per-session code kill the session, never the process; drain-and-handoff on planned restarts; the supervisor restarts connections, and process death is an incident, not a recovery action.
- **Concern 8, design-phase weight (partial):** SESSION-MASS combined with an EDGED/FROZEN client protocol (Axis 6) → reconnect jitter, resume cursors, and backoff must be designed into the frozen protocol surface before first ship — they cannot be retrofitted onto deployed clients.
- **Concern 6, test evidence (joint with Axis 1):** MULTI-NODE + SEEDED → whole-system simulation pays, and the contention answer picks the first-class scenario family — CONVERGENT → partition-heal merge storms and multi-day divergence-then-reconcile runs; EXCLUSIVE → split-brain fencing races and failover under partition. SESSION-MASS adds mass-reconnect (thundering herd) as a first-class simulated scenario.

---

## Axis 5: Data gravity

**Question.** For every sink this component writes, name one concrete reader NOT deployed in lockstep with you — another team or organization, clients upgrading on their own schedule, or a future version reading old data. **Lockstep is the test; persistence is the amplifier** (old data is an eternal reader of your schema). Cannot name one = IN-PROCESS.

**Per-format evolution regime** (for each boundary-crossing format, input or output): who can change this format, and does the change arrive without your agreement?

- **FROZEN-STANDARD** — fixed by an external published standard with no unknown-field mechanism (fixed-width or CRC-framed binary: Modbus, CAN, most industrial and avionics buses). Nobody accretes fields, ever.
- **NEGOTIATED-STABLE** — changes only by bilateral agreement or an explicit version negotiation you participate in.
- **ACCRETING-PRODUCER** — a counterparty adds fields on its own release schedule and expects tolerant readers (partner JSON/EDI, webhook payloads).

**Rider 1 — Adversarial exposure** (carried at zero extra enumeration cost while tracing channels): for each INPUT, name the least-trusted party who can produce bytes this component parses. The deciding test is **enrollment and leverage, NOT authentication**: if any writer belongs to an open-enrollment population (self-serve signup, public internet, marketplace, anyone with an email and a credit card), or is a party over whom you hold no employment or contractual leverage, the boundary is **ADVERSARIAL** — a login page in front of open enrollment does not make its writers trusted. Untraceable provenance — content transitively embedded in inputs arriving from elsewhere (the Log4Shell pattern: log-message content assumed trusted) — defaults to ADVERSARIAL. Before recording TRUSTED-ONLY, name the attacker payoff reachable through the input (credentials, money movement, host foothold, denial); a named high-value payoff does not flip the flag while leverage holds, but is recorded as the answer's falsifier: first evidence of an untrusted party reaching that channel re-fires the rider.

**Rider 2 — Secret observability** (carried in the same trust pass; asked **unconditionally** — a TRUSTED-ONLY input answer does not skip it, because the observer need not be a writer): does this component compute over material that must remain confidential from any party who can observe its execution or error behavior? Name the secret (device/private key, password or its hash input, session token, plaintext under encryption) and the observer channel (network-measurable timing, co-tenant cache or branch predictor, power/EM or induced faults on hardware an attacker holds, error-message or error-timing differences). No nameable secret-plus-observer pair = NO-OBSERVED-SECRET.

**Answers.** **IN-PROCESS** | **PERSISTED-SINGLE-OWNER** (falsifier: first non-lockstep reader on the sink — the Hyrum event) | **CROSSES-BOUNDARIES** (with per-format regime: FROZEN-STANDARD | NEGOTIATED-STABLE | ACCRETING-PRODUCER). Input flag: **TRUSTED-ONLY** (with named payoff falsifier) | **ADVERSARIAL**. Secret flag: **OBSERVED-SECRET** (named secret and observer channel) | **NO-OBSERVED-SECRET**.

**Day one.** Enumerate sinks from the brief (DB table, file format, queue topic, wire response); the "name one concrete reader" clause makes the answer falsifiable, not vibes.

**Re-fire triggers.**

- Regime: first field addition observed on a format recorded FROZEN-STANDARD or NEGOTIATED-STABLE demotes it to ACCRETING-PRODUCER.
- Egress-side (**the Hyrum event**, after Hyrum's Law): first non-lockstep reader observed on an existing sink — a same-org team pointing a new reader at your path, a field/column request from a party you do not deploy with, discovery of an unknown reader, or historical partitions being read by anyone at all — re-fires this axis for that surface. PERSISTED-SINGLE-OWNER carries this as its explicit falsifier: its premise is "cannot name one non-lockstep reader," and the first nameable reader kills the premise. Readers of already-written history are non-lockstep *by construction* — no coordinated redeploy can un-break a rename across old data.
- Axis 6's uncontrolled-consumer trigger, when it fires on a data sink, ALSO re-fires this axis for that sink, not only the design-weight decision.
- Rider 1: any deployment-boundary change — component newly exposed outside the org, new ingestion channel, new accepted format.
- Rider 2: key material or confidential inputs newly enter the computation, or deployment moves onto observable substrate (co-tenant cloud hardware, devices attackers physically hold).

**Recorded bets (riders).** Rider 1 is correct as a rider only if channel enumeration here reliably surfaces input-side writers; the first walk where the output-oriented gravity question causes an input channel to be skipped promotes it to a standalone Adversarial exposure axis verbatim. Rider 2 is correct as a rider only if the trust pass reliably asks the secret question even when every input is TRUSTED-ONLY; the first walk where a TRUSTED-ONLY answer causes the secret question to be skipped promotes Secret observability to a standalone axis verbatim.

**Decides.**

- **Concern 5, schema openness (primary):** IN-PROCESS → closed ADTs with exhaustive matching. PERSISTED-SINGLE-OWNER → closed types plus owned, tested migrations. CROSSES-BOUNDARIES splits by regime: FROZEN-STANDARD → exhaustive closed ADTs over the standard's cases, a strict total parser that rejects malformed input, and *zero* versioning/tolerant-reader machinery (accretion machinery on a frozen standard is dead weight and a silent-misparse source); ACCRETING-PRODUCER → open accreting maps, must-ignore-unknown, version negotiation, tolerant readers; NEGOTIATED-STABLE → closed types per negotiated version with explicit version negotiation at the boundary. A Hyrum-flipped sink moves from owned migrations to additive-only evolution with explicit versioning. The ADVERSARIAL flag reverses Postel: strict closed parsing, reject unknown fields. Where ADVERSARIAL meets ACCRETING-PRODUCER: tolerate contract-mandated unknown fields but strictly validate every field actually read, and bound total input size.
- **Concern 1, invariant placement (boundary line):** boundary-crossing input cannot be correct-by-construction; it is validated at runtime into closed internal types, and type-level proof applies only inboard of that line. Parser style follows the regime — FROZEN-STANDARD → parse-don't-validate with a strict total parser; ACCRETING-PRODUCER → tolerant reader that normalizes and carries unknowns. ADVERSARIAL flag → total parser producing evidence-carrying types; crashing boundary asserts become a DoS vector.
- **Concern 1, via the secret flag:** OBSERVED-SECRET → error behavior on the secret path must be uniform in timing and content with respect to secret bits. Rich crash-early asserts whose reachability or timing varies with the secret are an oracle for the observer, so invariants on that path move to secret-independent checks — double-compute-and-compare, verify-after-sign, constant-time comparison — instead of data-dependent crashing asserts, even where Axes 1 and 9 (fault reproducibility, defect consequence) would otherwise prescribe them.
- **Concern 6, test evidence (partial):** FROZEN-STANDARD → conformance corpus against the published standard, malformed-frame rejection tests. ACCRETING-PRODUCER → round-trip and cross-version tests first-class (new reader on old data, old reader on new data). A Hyrum-flipped sink acquires cross-version tests at flip time. ADVERSARIAL flag → fuzzing mandatory on the parsing path, overriding whatever posture Axis 8 (oracle) otherwise suggests — attackers sample the worst case, not the distribution (Heartbleed). OBSERVED-SECRET adds observer-channel evidence — statistical timing-leak tests (dudect-style) and, on physically held hardware, fault-injection countermeasure tests — as first-class, since no functional oracle sees a side channel.
- **Concern 2, layout, via flags (overrides Axis 2):** ADVERSARIAL → never trade memory/type safety for layout on the parsing path, even where Resource pressure licenses it. OBSERVED-SECRET → the named secret path must be branchless and flat regardless of heat or envelope: no secret-dependent branches, no secret-indexed memory access, fixed-size flat buffers, uniform-latency error paths — overriding the COOL/UNBOUNDED "evidence-carrying types everywhere" output on exactly that path (Option/enum branching on secret-derived values is the defect being engineered out). The two overrides coexist because they govern different paths: parsing stays type-safe, the secret computation goes flat.
- **Concern 3, values vs places, via the secret flag:** OBSERVED-SECRET → zeroization is an obligatory places discipline: key material lives in pinned, overwritable places and is scrubbed in place at end of use. Every value-semantics copy of the secret is an un-scrubbable leak, so "immutability everywhere" is the wrong pole on the secret path even at COOL, UNBOUNDED, and SINGLE-WRITER.
- **Concern 4, crash aftermath (partial, via flag):** ADVERSARIAL → malicious input is a first-class fault population; sandbox-and-supervise the parsing stage for containment, but the faults themselves move to hunt-and-eliminate even when they look environmental — the attacker replays the crashing input at will, so supervise-and-restart alone is insufficient (crash-loop DoS).

---

## Axis 6: Commitment reversibility

**Question.** Classify by intended distribution: list every shipped artifact whose consumers you cannot force to upgrade — wire protocols, on-disk formats, public APIs, firmware, certified builds — and name those consumers. Empty list = FLUID. Hyrum surfaces enter on the first uncontrolled-consumer event (do not stall enumerating hypothetical future scripters).

**Rider 1 — Consumer cardinality** (carried in the same consumer walk; asked for internal, *forceable* interfaces too — the main question's "cannot force" filter does NOT apply to this rider): for each interface this component exposes, count the call sites and independently-prioritizing teams that must move when its shape or *semantics* change. Is a change one commit landable by you (**LOCAL**), or a campaign across N owning teams' review queues (**CAMPAIGN**, record N)? Forceability and coordination cost are independent: monorepo codemod / large-scale-change tooling mechanizes *syntactic* rewrites only, while semantic changes (error-contract behavior, token meaning) cost per-call-site human judgment times N owners regardless of forceability — a forceable interface can still be a campaign.

**Rider 2 — Substrate capability regime** (carried in the same commitments pass — it inverts the dependency arrow: the main question lists surfaces YOU froze toward consumers; this lists surfaces a counterparty can break *underneath* you): name every platform capability this component requires that a counterparty can remove or reshape without your agreement — host APIs (browser-extension surfaces, mobile OS entitlements, app-store policy gates, a SaaS platform you build on) — and that counterparty's published deprecation calendar or policy cadence. Capabilities resting on versioned, decades-stable, or self-controlled substrate (POSIX, ISO C/C++, JVM, SQL standard, your own OS image) = **STABLE-SUBSTRATE**. Any required capability a named landlord can revoke unilaterally = **LANDLORD** (record platform and calendar).

**Answers.** **FLUID** | **EDGED** (named short list of frozen boundaries) | **FROZEN**. Cardinality per interface: **LOCAL** | **CAMPAIGN(N teams)**. Substrate flag: **STABLE-SUBSTRATE** | **LANDLORD** (named platform, published calendar).

**Day one.** A question about the distribution model, not hindsight: at project start you know whether you control every deploy point. Rider 2 is checkable from the platform's own policy and deprecation docs.

**Re-fire triggers.** Main: the moment any artifact ships to a deploy point you do not control (first external SDK user, first firmware flash, first third-party integration), that surface moves FLUID→EDGED and the design-weight decision re-fires for it; when the surface is a data sink, Axis 5 re-fires for that sink too. Rider 1: consuming-team count first crosses ~5, or the interface is published to an internal package registry or platform catalog. Rider 2: a new platform dependency is added, or the landlord announces a deprecation, manifest revision, or policy change touching a required capability.

**Recorded bets (riders).** Rider 1 is correct as a rider only if the consumer walk enumerates internal forceable consumers; the first walk where the "cannot force" framing causes internal consumers to be skipped promotes Consumer cardinality to a standalone axis verbatim. Rider 2 is correct as a rider only if the frozen-artifact walk reliably prompts the inverted question; the first walk where an empty frozen list (FLUID) ends the pass without asking who owns the substrate promotes Substrate capability regime to a standalone axis verbatim.

**Decides.**

- **Concern 8, design-phase weight (primary):** FROZEN/EDGED → heavy up-front design on exactly the frozen surfaces (a shipped bug on a surface with un-upgradeable consumers is kept forever). FLUID → ship-and-iterate.
- **Concern 7, abstraction timing (partial):** frozen-surface vocabulary (field names, message types, error codes) is designed before first ship — there is no second naming pass on a wire protocol.
- **Concern 10, agent delegation (partial):** frozen surfaces keep a human carrying compatibility theory (what old consumers depend on is not machine-checkable from the current repo); the fluid interior is the deep-delegation zone.
- **Concern 7, via cardinality:** CAMPAIGN → the interface's vocabulary — names, shapes, token taxonomy, error contracts — is designed up front even where Axis 7's volatility/horizon joint says extract-after-repetition, because a wrong noun costs a campaign (N review queues, per-call-site judgment) per correction. LOCAL → extract-after-repetition stands.
- **Concern 8, via cardinality:** CAMPAIGN → RFC/deprecation process, migration tooling, and staged-rollout design get real design weight even at FLUID — forceability does not erase coordination cost, so "FLUID → ship-and-iterate" is capped at LOCAL interfaces.
- **Concern 10, via cardinality:** the deep-delegation zone narrows to the LOCAL+FLUID interior; shape or semantics changes to a CAMPAIGN interface keep a human carrying the migration-cost-and-compatibility theory even when every consumer is technically forceable.
- **Concern 7, via substrate flag:** LANDLORD → an adapter seam isolating every landlord touchpoint is designed up front, before feature vocabulary — the platform boundary is the first abstraction, not an extracted one. STABLE-SUBSTRATE → no such seam is owed.
- **Concern 8, via substrate flag:** LANDLORD → capability-degradation modes and dual-track builds (current + announced-next platform version) get design weight despite FLUID — the landlord's calendar, not your release train, sets the deadline.
- **Concern 5, via substrate flag:** LANDLORD → version/capability negotiation machinery toward the platform boundary (feature detection, graceful capability loss) — a boundary the Axis 5 walk never records, because the API is called, not parsed.
- **Concern 6, via substrate flag:** LANDLORD → a host-version test matrix across the landlord's release channels (stable/beta/canary or OS versions), tracking announced deprecations, is first-class evidence. STABLE-SUBSTRATE → such a matrix is speculative weight.

---

## Axis 7: Requirements volatility

**Question.** Write one paragraph of acceptance criteria now and ask the stakeholder to sign it as stable for 6–12 months. Proxies: external fixation (law, RFC, prior system being replaced byte-for-byte), last-quarter spec churn, purpose-is-the-hypothesis (the brief describes an experiment on users). Unsignable = DISCOVERING. The test is present-tense, not predictive — inability to sign *today* is the answer.

**Rider — Modification horizon** (carried in the same stakeholder pass — ask it in the same conversation as the signing test): after this week, who runs or edits this code, how many more times, per what calendar? **THROWAWAY** is claimable only with a named decommission date or event AND an enforcing mechanism outside team willpower (the meeting after which it is deleted, the allocation that expires, a CI job that removes it). **SEASONS** = a bounded run of months in one maintainer's hands. **INSTITUTION** = open-ended calendar or rotating/inheriting maintainers. Unknown defaults long: you never predict longevity, you only ever prove shortness.

**Answers.** **FIXED-SPEC** | **NEGOTIABLE-EDGES** | **DISCOVERING**. Horizon flag: **THROWAWAY** (gated as above) | **SEASONS** | **INSTITUTION**.

**Re-fire triggers.** Main: first material amendment to signed criteria demotes the answer and re-fires concerns 7 and 8. Rider (**the adoption event**): a second scheduled run, a second person inheriting the code, or the decommission date passing undeleted demotes THROWAWAY at that moment and re-fires concerns 6, 7, 8, and 10.

**Recorded bet (rider).** The rider form is correct only if the signing conversation reliably surfaces the horizon; the first walk where it is skipped promotes Modification horizon to a standalone axis verbatim.

**Decides.**

- **Concern 7, abstraction timing (joint: horizon caps the volatility answer):** THROWAWAY → never abstract, even at FIXED-SPEC — there is no "after repetition" before the decommission date. INSTITUTION → repetition is already on the calendar, so extracting the domain vocabulary pays at adoption. Between those caps: FIXED-SPEC → design the vocabulary up front; DISCOVERING → extract after repetition (early names will be wrong names).
- **Concern 8, design-phase weight (joint with Axis 6, with horizon floor):** DISCOVERING+FROZEN is the trap quadrant — the resolution is to *shrink the committed surface*, not heavy-design the guess. FIXED-SPEC+FROZEN → maximum design weight. THROWAWAY → zero design weight regardless of FIXED-SPEC, unless Axis 9 records UNRECOVERABLE/HARM. INSTITUTION → modest structural design pays even at FLUID.
- **Concern 6, test evidence (partial, with horizon floor/ceiling):** DISCOVERING → examples as discardable requirement docs. THROWAWAY → zero tests; eyeball verification is the economical pole regardless of Oracle strength. INSTITUTION → a curated regression corpus becomes the contract that survives rotating maintainers.
- **Concern 5, schema openness (partial):** DISCOVERING → keep the moving periphery open even in-process; closing it into ADTs is premature.
- **Concern 10, agent delegation (partial, via horizon):** THROWAWAY → machine-checkable substrate construction is waste. INSTITUTION → substrate for future drive-by or agent maintainers is rational investment at adoption.

---

## Axis 8: Oracle strength

**Question.** Write the oracle's property statement in one sentence now ("serialize(parse(x)) == x", "output matches reference implementation on corpus C", "ledger balances to zero") or point at the existing artifact (conformance suite, golden corpus, reference implementation, simulation harness). **An unnamed hypothetical oracle counts as absent** — failure to name IS the answer. Record the oracle's **coverage denominator** with the grade: name the surface the property statement quantifies over — which inputs, which operations, which subset of shipped behavior the artifact can actually adjudicate. The grade applies only within that denominator; surface outside it is graded separately and defaults to TASTE-ONLY until its own oracle is named.

**Rider — Theory presence** (carried in the same evidence pass — the written oracle and the living adjudicator are the two distinct evidence sources; do not conflate them): name the person who can adjudicate, from memory of why the code is shaped this way, whether a surprising behavior is a bug or intended — and confirm that named person is actually reviewing changes this quarter. No name, or the name is someone who left, or reviewers rotate through without predating the code = **THEORY-ABSENT**.

**Answers.** **STRONG** | **PARTIAL** | **TASTE-ONLY** (each scoped to a recorded coverage denominator; per-surface grades where the denominator does not span the component). Theory flag: **THEORY-RESIDENT** (named, currently reviewing) | **THEORY-ABSENT**.

**Day one.** Answerable by enumeration: the artifact either exists or the sentence is writable now. No deferral needed for the main answer.

**Re-fire triggers.** Main: first shipped feature or surface the oracle artifact cannot adjudicate (the reference implementation lacks the operator; the corpus has no vectors for the new mode) re-fires this axis for that surface. Rider: departure or reassignment of the named adjudicator, or transfer of maintenance to AI agents or rotating reviewers.

**Decides.**

- **Concern 10, agent delegation depth (primary — capped by Axis 9's UNRECOVERABLE/HARM answer and by Axis 9's External assurance flag):** the posture is the JOINT of oracle grade and theory flag, scoped to the recorded coverage denominator — deep delegation never silently extends past what the oracle sees; on surface outside the denominator the effective grade is that surface's own (default TASTE-ONLY), so agent changes there revert to author-adjudicated diffs. STRONG+RESIDENT → deep delegation within the denominator; humans review the oracle, not the diff. PARTIAL/TASTE-ONLY+RESIDENT → the resident adjudicator makes author-adjudicated change the economical pole; heavier machine-checkable substrate is speculative weight. THEORY-ABSENT with oracle below STRONG → the human review gate is theater (reviewers cannot distinguish bug from load-bearing quirk); the dominant engineering work BEFORE any delegated change is substrate construction — characterization tests pinning current behavior, an executable spec of the rules — with interim changes conservatively small. STRONG+ABSENT → delegate against the oracle, treating behavior outside the oracle's coverage as frozen.
- **Concern 6, test evidence:** STRONG → generated property/differential tests within the recorded denominator. TASTE-ONLY → curated examples are the honest ceiling (generated tests against no oracle are theater). The THEORY-ABSENT flag promotes the existing corpus from regression aid behind an author's judgment to primary and near-sole evidence, deliberately expanded toward characterization coverage — example-adjudication-by-author no longer exists.
- **Concern 1, invariant placement (conditional):** a type-encodable STRONG oracle makes compile-time proof pay rent; this flip fires only when the oracle happens to be type-encodable.

---

## Axis 9: Defect consequence

**Question.** If this component silently does the wrong thing for one hour, trace every actuation path (rewritable row, ledger entry, email sent, public statement, physical actuator) and ask two yes/no questions per path: does rerunning fix it; if not, does a NAMED compensation mechanism exist (who replays, from what log)? The answer is the **MAX over all paths** — stop enumerating at the first UNRECOVERABLE/HARM path.

**Priced rerun rule:** where rerunning fixes it, price the rerun before recording SHRUG — burn rate × expected detection latency, plus calendar time to redo, read off the project's existing budget or schedule artifact. If the priced rerun exceeds 10% of the project budget or two weeks of a schedule carrying a named external commitment, the rerun IS the compensation mechanism: record BOUNDED-LOSS with the rerun's priced cost as the recorded loss bound. (A $30M three-month model retraining answers BOUNDED-LOSS; tonight's Spark job answers RETRY-AND-SHRUG.)

**Rebuild-source falsifier:** RETRY-AND-SHRUG additionally records its falsifier — name the rebuild source the rerun depends on (which upstream system, log, or snapshot), its retention window, and who owns its decommission. An answer that cannot name its rebuild source is BOUNDED-LOSS at best, and a rerun against a dead or truncated source is undefined, not merely more expensive.

**Rider — External assurance** (carried in the same consequence pass; asked **unconditionally** — a RETRY-AND-SHRUG or BOUNDED-LOSS answer does not skip it, because audit scope attaches by law and money flow, not by defect severity: PCI change control can bind a component whose defects are shrug-level, and SOX ITGC binds honestly-BOUNDED-LOSS components): name the outside authority that inspects this component's CHANGE PROCESS or evidence — external financial auditor (SOX 404 ITGC), assessor (PCI-DSS), certification body or regulator (ISO 27001, DO-178C, GxP/FDA) — and the scoping artifact that puts this component in their sample (SOX scoping memo, PCI SAQ/ROC scope, ISO Statement of Applicability, PSAC, validation plan). This is a *process inspector*, not a consumer of a shipped artifact — it does not make the component EDGED on Axis 6, and it is not a reader of any data sink on Axis 5. None nameable = UNAUDITED. Answerable on day one from scoping documents.

**Answers.** **RETRY-AND-SHRUG** (rerun fixes it AND rerun priced below threshold AND rebuild source named with retention window and decommission owner as the recorded falsifier) | **BOUNDED-LOSS** (compensation mechanism named, not imagined — including the priced-rerun case, with the rerun cost as the recorded loss bound) | **UNRECOVERABLE** | **HARM** (bodily harm). Assurance flag: **UNAUDITED** | **AUDITED** (named authority, named scoping artifact).

**Re-fire triggers.** Any new actuation path attached (new downstream consumer, side-effecting integration, money movement); a 10× growth in rerun price (burn rate or expected detection latency); for RETRY-AND-SHRUG: loss, truncation, retention shortening, or announced decommission of the named rebuild source (including a legacy system's strangler-fig cutover date and calendar expiry of a retention window), or a detection-latency estimate first exceeding that retention window. Rider: the component newly enters an audit scope — IPO or SOX scoping change, cardholder-data flow attaches, regulated-market entry, certification pursuit announced.

**Recorded bet (rider).** The rider form is correct only if the consequence pass reliably asks the authority question even when every actuation path is shrug-level; the first walk where a RETRY-AND-SHRUG answer causes the audit question to be skipped promotes External assurance to a standalone axis verbatim.

**Decides.**

- **Concern 1, invariant placement (primary):** UNRECOVERABLE/HARM → type-level proof plus independent runtime interlocks that crash before corruption. BOUNDED-LOSS → interlock intensity scales with the recorded loss bound — a rerun priced in the millions buys per-step runtime interlocks (loss-spike halts, invariant guards, checksum gates on checkpoints) that crash BEFORE corrupting last-good state. RETRY-AND-SHRUG → crashing assertions are the economical, adequate pole.
- **Concern 4, crash aftermath (override):** supervise-and-restart is rational only when the crash window's damage is recoverable and cheap. UNRECOVERABLE/HARM forces bug-extinction plus redundancy even for environmental faults, overriding what Axis 1 alone would recommend. BOUNDED-LOSS prices the hunt: silent-wrongness faults are hunted to extinction before launch when each undetected occurrence burns a priced slice of the loss bound, while transient shell faults stay supervised.
- **Concern 8, design-phase weight (override):** UNRECOVERABLE/HARM raises design weight even when code is freely redeployable — the damage, not the artifact, is the irreversible thing (Knight Capital: fully reversible deploy, $440M unrecoverable loss). BOUNDED-LOSS with a bound material to the project reaches the same override — burned budget and calendar are damage rerunning cannot restore — mandating launch-readiness review, dry runs, and validate-before-checkpoint-commit design even at FLUID plus DISCOVERING.
- **Concern 10, agent delegation (cap):** UNRECOVERABLE/HARM caps delegation below what Axis 8 permits — the oracle itself may be wrong; a human review gate stays.
- **Concern 10, via assurance flag (a cap INDEPENDENT of both oracle grade and consequence level):** AUDITED → a second named human approver distinct from the author is mandatory on every production change regardless of Axis 8's output — "PARTIAL+RESIDENT → author-adjudicated change" is legally unavailable, and agent-autonomous deploys stay off the table even if the oracle later reaches STRONG. The delegation ceiling becomes agent-authors/human-approves, with the approval gate technically enforced, not conventional. UNAUDITED → no externally mandated gate; Axis 8 and the UNRECOVERABLE/HARM cap govern alone.
- **Concern 6, via assurance flag (the evidence's CONSUMER changes its required FORM, not its kind):** AUDITED → whatever evidence the other axes prescribe must additionally be produced as signed, immutably retained, auditor-sampleable packets (test-run records tied to change tickets, retention per the authority's window); CI logs that rotate and undocumented local runs do not count as evidence at all under this flag. UNAUDITED → evidence form is the team's own choice.
- **Concern 8, via assurance flag (partial):** AUDITED → the change-control pipeline itself is a designed deliverable — technically enforced author/approver separation, production write access removed from developers with tamper-evident break-glass logging, immutable multi-year audit trails, periodic access reviews — engineered up front even at FLUID, because retrofitting controls under a failed audit is the expensive path.

---

## Coverage table

| # | Concern | Primary decider | Contributing axes / flags |
|---|---------|-----------------|---------------------------|
| 1 | Invariant placement | **Defect consequence** (severity ladder sets proof-vs-assert intensity) | Data gravity (draws the boundary-validation line; ADVERSARIAL parser rule; OBSERVED-SECRET uniform-error rule); Fault reproducibility (partial); Resource pressure (modulates: construction-time invariants at HOT, compile-time sizing proofs at ENVELOPED); Oracle strength (conditional, type-encodable oracle) |
| 2 | Type safety vs memory layout | **Resource pressure** (sole decider: heat × envelope joint) | Data gravity flags override on named paths (ADVERSARIAL: never trade safety on the parsing path; OBSERVED-SECRET: branchless-flat secret path) |
| 3 | Values vs places | **Resource pressure** (motive) × **Writer topology** (safety) — jointly | Tail obligation (SOLD → places on the request path even at COOL); Fault reproducibility (SEEDED → immutable event inputs at the boundary); Data gravity secret flag (zeroization is a places discipline) |
| 4 | Crash aftermath | **Fault reproducibility** (picks the pole) | Writer topology (MULTI-NODE recovery paths; restart flag picks the supervision unit); Defect consequence (UNRECOVERABLE/HARM override; BOUNDED-LOSS prices the hunt); Data gravity ADVERSARIAL flag (attacker replays: eliminate, sandbox for containment) |
| 5 | Schema openness | **Data gravity** (gravity class × per-format regime; ADVERSARIAL Postel reversal) | Requirements volatility (DISCOVERING keeps the periphery open in-process); Commitment reversibility substrate flag (LANDLORD → capability negotiation toward the platform) |
| 6 | Test evidence | **Fault reproducibility × Writer topology** (simulation vs property vs examples+injection) with **Oracle strength** (examples vs generated; denominator scoping) | Data gravity (regime-specific corpora; fuzzing under ADVERSARIAL; timing-leak tests under OBSERVED-SECRET); Requirements volatility horizon (THROWAWAY floor, INSTITUTION corpus-as-contract); Defect consequence assurance flag (auditor-sampleable form); Commitment reversibility substrate flag (host-version matrix) |
| 7 | Abstraction timing | **Requirements volatility × Modification horizon** (horizon caps volatility) | Commitment reversibility (frozen-surface vocabulary up front; CAMPAIGN vocabulary up front; LANDLORD adapter seam first) |
| 8 | Design-phase weight | **Commitment reversibility × Requirements volatility** (the quadrant, incl. the DISCOVERING+FROZEN trap) | Defect consequence (UNRECOVERABLE/HARM and material BOUNDED-LOSS overrides; AUDITED change-control pipeline as deliverable); horizon flag (THROWAWAY zero, INSTITUTION floor); cardinality rider (CAMPAIGN caps ship-and-iterate); substrate flag (landlord calendar sets deadlines); Writer topology (SESSION-MASS × frozen protocol → reconnect designed before ship) |
| 9 | Coordination and tail latency | **Tail obligation** (tail half) + **Writer topology** (machinery half, incl. CONVERGENT/EXCLUSIVE machinery choice) | — (the pair covers the concern without overlap) |
| 10 | Agent delegation depth | **Oracle strength × Theory presence** (joint, scoped to the coverage denominator) | Defect consequence (UNRECOVERABLE/HARM cap; AUDITED author/approver cap, independent of oracle grade); Commitment reversibility (frozen surfaces and CAMPAIGN interfaces stay human-held; LOCAL+FLUID interior is the deep zone); Fault reproducibility (replay harness as substrate); Resource pressure (ENVELOPED resource model as substrate); horizon flag (THROWAWAY: substrate is waste; INSTITUTION: substrate pays) |

Every concern has at least one decider; every axis and every rider flips at least one concern (criterion: decision relevance). No two axes co-vary across essentially all realistic cases (criterion: non-aliasing — counterexample pairs recorded in the provenance appendix).

---

## Runnability audit (round 5)

Three real project briefs classified end-to-end by an engineer with the brief in hand, against the ~20-minute target. In all three runs the resulting weighting would have redirected engineering effort.

### Brief 1: saas-feature — 30 questions, ~35 minutes, weighting would have redirected effort: YES

Friction (verbatim):

- Axis 4 (checkability/fit): the most common SaaS topology — N stateless app instances + one transactional Postgres — is forced to MULTI-NODE by the LB-replica sentence, but the essential-vs-pre-sliced sub-question fits neither branch (coordination is delegated to a serializable shared store, not sliced, not node-exceeding). The EXCLUSIVE prescriptions (leader leases, fencing tokens, bounded unavailability) read overweight when 'single-order commit' is just Postgres transactions; the classifier must translate the output down. Cost ~4 minutes of the run.
- Axis 5 gravity class (ambiguity): 'a future version reading old data' as a nameable non-lockstep reader threatens to collapse PERSISTED-SINGLE-OWNER into CROSSES-BOUNDARIES for every persisted table — unclear whether owning the store and its migrations keeps ledger tables SINGLE-OWNER when the data is permanent financial history that migrations should not rewrite.
- Axis 5 evolution regime (ambiguity): camt.053 — a published standard, but XML, version-namespaced, and loosely implemented by banks — sits between all three regime values; FROZEN-STANDARD's definition (fixed-width/CRC binary) excludes it while 'published standard' pulls toward it. Answered ACCRETING-PRODUCER with low confidence.
- Axis 5 regime (fit): the who-changes-this-format question is input-oriented and near-vacuous for egress sinks you own (the ledger tables' 'regime' is trivially 'us') — the sub-question burns a pass without deciding anything there.
- Axis 2b (checkability): whether a PaaS instance memory quota counts as a 'named budget artifact' is unclear against datasheet/BOM/product-spec examples, and estimating the working set of unwritten code against the ~10x band is guesswork; a 512MB dyno vs a 300MB uploaded camt file is a real constraint the arithmetic only barely resolves.
- Axis 6 rider 1 (ambiguity at small scale): 'independently-prioritizing teams' is fuzzy at a 40-person monolith company — LOCAL vs CAMPAIGN(2) for ledger semantics was a coin flip.
- Axis 7 (granularity): one label per component loses the real structure — signable core pipeline vs unsignable matching heuristics; NEGOTIABLE-EDGES absorbs it only because the concern-5 'keep the moving periphery open' clause exists to catch the remainder.
- Brief gaps a real engineer would have day one (all assumed and marked, so checkability held): warehouse/BI readers on prod Postgres (axis 5 Hyrum status), enrollment model self-serve vs sales-led (adversarial flag), template alert packs (axis 3), audit scope (axis 9 rider), PaaS instance count (axis 4). None blocked the run.
- Runtime: ~35 min against the ~20 min target for a classifier already familiar with the instrument (first-time spec reading adds ~15 more). The overage concentrates in Axis 5 (3 formats x regime + 2 riders, ~8 min), Axis 4 translation friction, and Axis 9's path trace.

### Brief 2: embedded-fw — 24 questions, ~45 minutes, weighting would have redirected effort: YES

Friction (verbatim):

- Axis 3 (Tail obligation): 'latency distribution being sold' maps awkwardly onto embedded hard real-time. The qualifying artifact exists (LoRaWAN RX-window tick budget) but belongs to the MAC layer sharing the CPU, not to any consumer of this component's latency — SOLD vs NONE turned on an architecture fact (superloop vs preemptive isolation) the axis never asks for. Longest single deliberation of the run (~6 min).
- Axis 4 rider (Restart blast radius): vocabulary is server-shaped. A device reset loses buffered readings that do NOT 'retry through a balancer' — they are destroyed unless persisted — so neither PER-REQUEST nor SESSION-MASS fits without translation. The embedded-critical outputs (persist frame counters and unsent data across watchdog reset; fleet-correlated reboots stampede the join server) were reachable only by bending the rider's terms; also ambiguous whether 'the process' is one device or the fleet.
- Axis 9 main: the 'silently wrong for one hour' trace under-captures the dominant embedded defect mode — slow cumulative physical damage (battery drain, flash wear) whose detection latency is months because units report rarely and some are unreachable. The priced-rerun rule's detection-latency term recovers the answer, but only by applying rerun-pricing logic to a non-rerunnable physical loss; the rubric had to be bent to record BOUNDED-LOSS honestly.
- Axis 9 rider (External assurance): RF type approval (ETSI RED/FCC, LoRaWAN cert) sits between 'process inspector' and 'artifact consumer' — recertification binds the change process for tx-affecting changes but is per-version conformance, not SOX-style audit sampling. AUDITED vs UNAUDITED was a genuine coin-flip; recorded AUDITED(qualified). The rider's examples (SOX, PCI, DO-178C) gave no purchase on the most common embedded assurance regime, radio type approval.
- Axis 6 main: OTA-capable-but-costly-with-months-unreachable sits between EDGED and FROZEN; 'cannot force to upgrade' is temporally graded here (forceable eventually, partially, at battery cost). Chose FROZEN-leaning-EDGED — the instrument's binary framing forced a judgment call it claims to avoid.
- Mild double-enumeration: the battery budget is walked twice — as Axis 2's envelope artifact and again as Axis 9's drain-consequence path. Not aliasing (they flip different concerns: layout/places vs interlocks/design weight) but the same artifact is priced twice in one run.
- Checkability gaps in the brief that a real engineer WOULD have day one (assumed and marked): superloop-vs-RTOS execution model (Axis 3), network-server ownership self-hosted vs managed (Axis 6 rider 2 — flips STABLE/LANDLORD), theory residency (Axis 8 rider). None are instrument defects, but three assumptions in one run is worth noting.
- Runtime: honest first-run estimate ~45 min against the ~20 min target. The long passes are Axis 5's per-format regime loop (3 formats), Axis 9's per-path trace (5 paths x 2 questions), and the four judgment-call frictions above at 3-6 min each. A second run by the same engineer on a sibling component would likely hit ~25 min; the 20-minute claim holds only for practiced users on well-mapped (server-shaped) domains.

### Brief 3: data-pipeline — 34 questions, ~30 minutes, weighting would have redirected effort: YES

Friction (verbatim):

- Axis 1: the layered answer value is defined only as SEEDED-core/ENVIRONMENTAL-shell; this project is REPLAYABLE-core/ENVIRONMENTAL-shell — I had to extend the answer vocabulary. Batch pipelines (replay from captured files, environmental ingestion shell) are common enough that the layered form should admit REPLAYABLE cores.
- Axis 3: batch-completion deadlines fit the axis awkwardly. The 'morning dashboard' is a hard product deadline, and the upgrade trigger's list includes 'hard deadline', which nearly pulls SOLD — but the concern it decides (pause behavior on the request path, tail machinery) is meaningless for a nightly batch. Only the provenance appendix ('nightly pipeline is HOT-not-TAIL') settled it; the axis text alone is ambiguous for batch systems, and deadline pressure then risks being double-counted or dropped between Axis 3 and concern 8.
- Axis 4: 'one logical writer' vs Spark's physically multi-node execution caused a genuine wobble — the word 'logical' saves it, but an engineer who doesn't know Delta's commit protocol could record MULTI-NODE and cascade wrong outputs into concerns 3/4/9. Also a concurrent backfill+nightly run is a realistic second-writer case the deployment-plan framing did not naturally surface; I had to think of it unprompted.
- Axis 5: the per-format regime taxonomy is producer-oriented; for a sink the component itself owns (the Delta table), 'who can change this format without your agreement' answers 'me', which maps to no regime value — I routed it through PERSISTED-SINGLE-OWNER/Hyrum instead, but the instruction to record a regime 'for each boundary-crossing format, input or output' reads as if it applies. Also ACCRETING-PRODUCER's clause 'expects tolerant readers' fits legacy systems poorly (they expect nothing); the without-your-agreement test decided it, but the value's description created hesitation.
- Axis 5 volume: this axis alone was ~8 of my 34 answers and ~7-8 of the ~30 minutes (5 formats × regime + 2 riders + per-sink reader naming). For any integration-heavy component the 20-minute target is carried or broken here.
- Axis 6 rider 2 / Axis 9 rider: two answers (LANDLORD vs STABLE-SUBSTRATE — managed or self-hosted Spark; AUDITED vs UNAUDITED — public company or not) are absent from the brief. Both are day-one knowable by a real engineer (checkability holds), but a brief-only run forces marked assumptions, and the AUDITED fork materially changes three concerns' outputs — the single highest-leverage fact the brief omitted.
- Axis 9: 'silently wrong for one hour' reads oddly for a nightly batch — the natural unit is 'one wrong run'; I translated silently. Minor wording friction, same answer.
- Overall runtime: 34 answered questions in ~30 minutes for a competent engineer (including writing the record with named artifacts and falsifiers). The ~20-minute target is optimistic for a multi-format, multi-sink component; realistic for a single-service component. Not a failure, but the target should say 20-35 depending on boundary count.

### Aggregate verdict

Average 29 questions and ~37 minutes per run — **OVER the ~20-minute budget** (criterion 5, RUNNABLE, as stated: not met). The weighting output was decision-useful in 3 of 3 runs, and checkability held throughout — every brief gap was a fact a real engineer would have on day one, assumed and marked rather than blocking. The overage concentrates in Axis 5's per-format regime loop (the dominant cost on any integration-heavy component), Axis 9's per-path trace, and 3–6-minute judgment-call frictions where the instrument's vocabulary is server-shaped (Axis 4's restart rider and Axis 9's one-hour trace on embedded and batch systems, Axis 3 on batch deadlines and shared-CPU real-time, Axis 5's producer-oriented regime on owned egress sinks, Axis 1's missing REPLAYABLE-core layered value). A practiced classifier on a well-mapped server-shaped, single-boundary component can plausibly hit ~20 minutes; the honest range is ~20–45 depending on boundary count and domain fit. No revisions applied this round.

---

## Provenance appendix

### Derivation and merge

Five independent derivations (reverse-engineering from the ten concerns; repair of a seed axis set; first-principles; failure-case-driven; practitioner-segment-driven) produced overlapping candidate pools, merged as follows.

**Unanimous or near-unanimous merges** (five proposals asking the same question, one kept):

- **Fault reproducibility** — all five derivations proposed it. Kept the three-way REPLAYABLE/SEEDED/ENVIRONMENTAL answer because SEEDED captures the buy-back-determinism case (TigerBeetle, FoundationDB) that a binary answer loses, plus the layered-core refinement. One derivation's ADVERSARIAL value was *extracted out* of this axis: an adversary searches for the worst case while an environment samples a distribution, and they flip different test-evidence poles (fuzzing vs simulation) — SQLite is deterministic yet adversarial, a telecom switch environmental yet unattacked.
- **Instance heat** — merged five proposals operationalizing the same fact (10^6-scale instances or ops on a path with a stated budget, deferral at first profile). Later widened into **Resource pressure**; see the attack changelog.
- **Tail obligation** — merged five proposals: a promised percentile, frame deadline, or fan-out amplification.
- **Writer topology** — merged five proposals: identical countable fact (writers per mutable datum, and whether they span nodes) with identical three-way answers.
- **Requirements volatility** — merged five proposals, all operationalizing "is the problem still being discovered" via a signable-criteria check. Kept the sign-the-criteria phrasing with the three-way answer (NEGOTIABLE-EDGES is a real middle case).
- **Oracle strength** — merged four proposals. Kept the writable-*before*-the-change test.
- **Defect consequence** — merged severity components from all five. Kept the worst-hour-with-traced-actuation-path phrasing (sharpest operational test; Knight Capital is the anchor case) with the four-way ladder ordered by recoverability, which is what keeps the axis from degenerating into unfalsifiable "criticality."
- **Lifespan and hands** — merged five proposals; all independently folded team scale into the "hands" answer, so the candidate-gap question "is team scale its own axis" was answered *no* unanimously. Later compressed to the Modification horizon rider; see below.

**Rejected merges** (compound proposals split back apart because the bundled facts fail co-variation):

- **Heat + tail as one "performance" axis** (proposed twice): a low-QPS trading/payments gateway is TAIL-not-HOT; a batch particle simulator or nightly pipeline is HOT-not-TAIL. They flip different concerns (2/3 vs 9). Both halves preserved; the bundling undone.
- **Data gravity + commitment reversibility as one "boundary permanence" axis** (proposed twice): counterexamples in both directions — an internal warehouse has real data gravity yet remains migratable; fielded firmware, a scripted-against CLI, or a stateless public API is pinned forever with zero persisted data (libcurl, a DNS server: zero data gravity, maximally frozen surface). They decide different concerns (5 vs 8) by different mechanisms (what evolution discipline the data's readers force vs whether the shipped artifact can change).
- **Consequence severity + adversarial exposure as one "stakes" axis** (proposed three times): the facts do not co-vary — a game server's packet parser is adversarial yet low-stakes; an actuarial batch job is high-stakes yet unattacked. Adversary flips concerns independently of severity: fuzzing becomes mandatory (concern 6) and the layout-for-safety trade is banned on the parsing path (concern 2) even at RETRY-AND-SHRUG stakes. The claim that no concern flips on adversary alone was refuted, so the bundle fails the alias test.

**Splits:**

- One derivation's **"Spec source"** was split into Requirements volatility + Oracle strength: the fusion conflates spec stability with machine-checkability, and the two do not co-vary — a decades-stable design system or medical-triage UI is FIXED-SPEC yet TASTE-ONLY, while a discovering product can carry strong local oracles (roundtrip laws on its codecs).

### Per-axis audit

All eleven pooled axes (the nine merge survivors above, plus standalone Adversarial exposure and Lifespan-and-hands) received **keep** verdicts on checkability, decision relevance, and non-aliasing, with hostile counterexample pairs recorded in all suspect quadrants (Fault reproducibility vs Writer topology: FoundationDB is MULTI-NODE yet SEEDED, a single-writer CLI faces disk corruption; heat vs tail; gravity vs reversibility; consequence vs adversary; volatility vs reversibility: DISCOVERING+FROZEN is the classic startup-API trap, FIXED-SPEC+FLUID is the statutory-rule reimplementation; and so on). Audit-mandated tightenings adopted into the final wording:

- ENVIRONMENTAL defined cost-bounded ("not enumerable or virtualizable at acceptable cost, name the source"), since virtualization is almost never impossible in the absolute.
- Heat: "plausibly hit" struck in favor of the artifact test alone; no artifact = COOL provisionally. The memory-hot vs loop-hot conflation was examined and judged tolerable: both sub-forms issue the same instructions on the concerns they flip, and the prescription is already scoped to the named hot types/loop.
- Tail: SOFT kept only as an anti-inflation guard, treated as NONE-with-a-watch-trigger, not a third weighting. The contracted-percentile vs fan-out split was rejected: both are mechanisms by which this component's p99 becomes someone else's user-visible median, and they demand the same engineering response.
- Writer topology: lead with "from the deployment plan," since day-one answerers cannot count writers in code that does not exist; keep essential-vs-pre-sliced as the guard against reading a habit-sketched topology as a requirement.
- Data gravity: rephrased so lockstep-deployment of readers is primary and persistence the amplifier — a request/response wire API whose payloads die instantly but whose clients upgrade on their own schedule is CROSSES-BOUNDARIES.
- Commitment reversibility: explicit day-one rule "classify by intended distribution; Hyrum surfaces enter on the first uncontrolled-consumer event."
- Requirements volatility: the false-FIXED-SPEC weakness (a stakeholder can sign confidently and be wrong) closed with the first-material-amendment demotion trigger.
- Oracle strength: "could you write one this week" replaced with "write the property statement in one sentence now" — converts a speculative counterfactual into an immediate pass/fail act; unnamed hypothetical oracles count as absent.
- Defect consequence: answer is explicitly the MAX over actuation paths; BOUNDED-LOSS requires naming the actual compensation mechanism (who replays, from what log), not an imagined backup.
- Adversarial exposure: money-adjacency dropped from the question's example list (stakes belong to Defect consequence); the incentive clause kept purely as "name the attacker's payoff."
- Lifespan: THROWAWAY claimable only with enforced expiry; unknown defaults long — prove shortness, never predict longevity.

### Judged construction: 11 → 9

The audited pool held eleven axes against a 6–9 runnability budget. Two compressions, both into riders with recorded promotion bets rather than cuts (the facts remain distinct; only the *slot* is shared):

- **Adversarial exposure** → rider on Data gravity: the input-channel walk needed to answer it is the same enumeration pass as the sink walk, so the fact is harvested at zero extra cost. Bet: the first walk where the output-oriented gravity question causes an input channel to be skipped promotes it back to a standalone axis verbatim.
- **Lifespan and hands** → the **Modification horizon** rider on Requirements volatility: the horizon question is asked in the same stakeholder conversation as the signing test. Bet: the first walk where the signing conversation fails to surface the horizon promotes it back verbatim. The pool's unanimous finding that team scale folds into "hands" carries over; the machine-checkability half lives in Oracle strength, which the horizon only feeds (agent-maintained intent raises the required substrate strength).

Of the candidate gaps raised before derivation: consequence-of-defect, state distribution, requirements volatility, and adversarial exposure all entered the set (as axes 9, 4, 7, and the Axis 5 rider respectively); team scale folded into the horizon rider.

### Attack-loop changelog

Four adversarial rounds against acceptance criteria 1–5, each round hunting counterexample pairs that classify identically while demanding materially different engineering, dead axes, aliases, and unanswerable questions. Axis count stayed at nine throughout; all repairs were answer-value additions, question sharpenings, trigger additions, riders on existing passes, or one axis-widening.

**Round 1 — 2 verified breaches fixed.**

- *Authenticated-but-untrusted writers invisible to the ADVERSARIAL rider* (an internal doc-preview service lifted into a self-serve product classified identically before and after): the rider's operational test rewritten from "outside the authenticated perimeter" to the **enrollment-and-leverage** test — open-enrollment populations and parties over whom you hold no employment or contractual leverage are ADVERSARIAL regardless of login pages — plus the named-payoff falsifier on TRUSTED-ONLY answers.
- Second breach closed by question sharpening in the same round.

**Round 2 — 4 verified breaches fixed** (answer-value additions, question sharpenings, and riders on the existing evidence pass).

- *Schema-evolution regime invisible* (a Modbus gateway and a partner-order JSON ingestion classified identically as CROSSES-BOUNDARIES, yet one must reject unknown fields on a frozen standard while the other must tolerate accretion): added the per-format **evolution-regime** sub-answer to Data gravity (FROZEN-STANDARD | NEGOTIATED-STABLE | ACCRETING-PRODUCER) with the demotion trigger on first observed field addition.
- Remaining breaches closed by the **Theory presence** rider on Oracle strength (the written oracle and the living adjudicator are distinct evidence sources; THEORY-ABSENT with a weak oracle makes the review gate theater) and further answer-value/sharpening repairs, including the coverage-denominator scoping that stops a STRONG grade from silently extending past what the oracle sees.

**Round 3 — 5 verified breaches fixed** (two riders, one axis-widening, two trigger additions from a refuter note).

- *Side-channel breach* (an Ed25519 signing terminal and an XML-DSig verifier classified identically, yet one must be branchless, zeroizing, uniform-latency): added the **Secret observability** rider to Data gravity, asked unconditionally in the trust pass — explicitly NOT gated on the input-trust answer, because the observer need not be a writer. It overrides layout, invariant, and values-vs-places outputs on exactly the named secret path.
- *Resource-envelope breach*: **Instance heat widened into Resource pressure** — the envelope sub-answer (ENVELOPED | UNBOUNDED, read off datasheet/BOM/product spec) captures the component that is nowhere near 10^6 ops/sec yet lives inside a RAM/flash/energy/binary budget, which forces the places pole by arithmetic and moves invariants to compile-time sizing proofs. DEFERRED heat was also made to emit COOL's output provisionally rather than emitting nothing.
- Remaining sufficiency breaches absorbed by the second rider and widening; two re-fire triggers added per the refuter's note (including the decision-time envelope trigger: the budget artifact re-fires the axis at signing time, before any port begins, because envelope outputs are day-one architectural commitments).

**Round 4 — 7 verified breaches fixed** (two question sharpenings, three trigger additions, three new riders, each rider with a recorded promotion bet per the set's established discipline).

- *External assurance invisible* (a SOX/PCI-scoped component and its unscoped twin classified identically, yet one legally cannot do author-adjudicated change): added the **External assurance** rider to Defect consequence, asked unconditionally in the consequence pass — audit scope attaches by law and money flow, not by defect severity. AUDITED caps agent delegation independently of both oracle grade and consequence level, changes the required *form* of test evidence (auditor-sampleable packets), and makes the change-control pipeline a designed deliverable.
- *Coordination cost without unforceable consumers* (a monorepo platform interface with 40 consuming teams classified FLUID/ship-and-iterate): added the **Consumer cardinality** rider to Commitment reversibility, asked for internal forceable interfaces too — LSC tooling mechanizes syntactic rewrites only; semantic changes cost per-call-site judgment × N owners regardless of forceability.
- *Platform-landlord breach* (a browser extension / mobile app whose required capabilities a platform vendor can revoke on its own calendar classified STABLE): added the **Substrate capability regime** rider to Commitment reversibility, inverting the dependency arrow — surfaces a counterparty can break underneath you, checkable day one from the platform's published deprecation policy.
- *Session-mass restart breach* (a stateless request service and a 100k-connection session server classified identically on crash aftermath): the **Restart blast radius** rider on Writer topology (PER-REQUEST | SESSION-MASS(N)) — Axis 1 picks the crash-aftermath pole, the restart flag picks the supervision unit, and SESSION-MASS adds thundering-herd reconnect as a first-class simulated scenario.
- *Convergent-vs-exclusive machinery breach* (a collaborative-editing store and a seat-reservation ledger, both MULTI-NODE-essential, prescribed the same "machinery"): the **contention sub-question** on Writer topology (CONVERGENT | EXCLUSIVE) with the invariant-side re-fire trigger — invariants change on the product calendar, not the deployment plan — and per-object splitting (the reservation ledger goes EXCLUSIVE while the cart stays CONVERGENT).
- *Alert-artifact inflation* (template-provisioned alert packs upgrading every service to SOLD): the Tail obligation **qualification** — an alerting rule counts only if its threshold was chosen for this component by a party who consumes its latency.
- *Rerun-priced-in-millions breach* (a $30M model-training run classified RETRY-AND-SHRUG because rerunning technically fixes it): the **priced-rerun rule** on Defect consequence (rerun cost above 10% of budget or two weeks of externally committed schedule records BOUNDED-LOSS with the rerun as the loss bound) plus the **rebuild-source falsifier** (a rerun against a dead or truncated source is undefined, not merely more expensive), with retention-window and strangler-fig-cutover triggers.
- Egress-side **Hyrum-event trigger** formalized on Data gravity: PERSISTED-SINGLE-OWNER carries "first nameable non-lockstep reader" as its explicit falsifier, and Axis 6's uncontrolled-consumer trigger cross-fires into Axis 5 when the surface is a data sink.

**Cap hit after round 4.** The final round's refuter produced no counterexample pair surviving verification.

**Round 5 (validation-only) — 12 claims across 4 lenses; 11 refuted, 1 survived. No revisions applied.**

Run against the final revision, which had never itself been attacked. Four adversarial lenses (including an odd-software lens hunting domains whose dominant defect class the set's vocabulary was not written for) produced 12 breach claims against acceptance criteria 1–5; every claim went to independent refutation. Eleven were refuted — the claimed identical classification broke on a cell-by-cell walk, or an existing rider, sub-question, or trigger already separated the pair. One sufficiency breach survived refutation: the Adversarial exposure rider records WHO can supply bytes but not the adversary's *capability class*, so on shared-ordering platforms (public blockchains with open mempools as the clean case) a payload-adversary and an ordering/composition-adversary classify identically while demanding different evidence and interlocks — an AMM pair contract and a token-vesting vault both peg the instrument's maxima (FROZEN, UNRECOVERABLE, ADVERSARIAL, REPLAYABLE) yet only one needs ordering-attack engineering, and every ADVERSARIAL prescription is textually payload-scoped. The refuter confirmed the walk cell-by-cell and noted the "practitioner supplies the attack catalog" defense is unavailable under the set's own Round 2–4 precedent. Full record, with its candidate repair recorded but not applied, under UNRESOLVED BREACHES. The round also ran a dogfood runnability audit on three real briefs; results in the Runnability audit section.

---

## UNRESOLVED BREACHES

One surviving breach from round 5 (validation-only). Its candidate repair is **recorded, not applied — re-validation required after applying**.

### Breach 1 (sufficiency, round 5, odd-software lens): adversary capability class invisible to the Adversarial exposure rider

**Claim.** The Adversarial exposure rider records WHO can supply bytes but not the adversary's capability class. On shared-state platforms where the adversary can also buy scheduling — public blockchains with open mempools are the clean case — a payload-adversary and an ordering/composition-adversary demand different evidence and different interlocks, and the set cannot separate them: two deployed contracts classify identically (both already peg the instrument's maxima — FROZEN, UNRECOVERABLE, ADVERSARIAL, REPLAYABLE) while only one needs ordering-attack engineering. The ADVERSARIAL flag's prescriptions (strict total parsing, fuzz the parsing path, sandbox, never trade safety on parsing) all target the payload channel; fuzzing an AMM's calldata parser finds zero of the attack class that has actually cost this domain nine figures.

**Project A.** Constant-product AMM pair contract (Uniswap-v2 class): swap/mint/burn against pooled reserves, price emerges from reserve ratio within a block.

**Project B.** Token-vesting vault contract: fixed beneficiary list, schedule-driven release, no price-dependent or shared-market state.

**Identical classification walk.** Axis 1: both REPLAYABLE (EVM execution replays bit-for-bit from chain state). Axis 2: both COOL (no 10^6 artifact) and ENVELOPED (24KB bytecode ceiling and per-transaction gas budget are named artifacts within 10x). Axis 3: NONE both. Axis 4: both SINGLE-WRITER — consensus totally orders all state transitions, one logical writer — restart flag PER-REQUEST (reverts are atomic; no session mass exists). Axis 5: both CROSSES-BOUNDARIES with the same regime (post-deploy ABI is fixed for both; integrators upgrade on their own schedule). Rider 1: both ADVERSARIAL by the enrollment test — anyone with gas can produce calldata. Rider 2: both NO-OBSERVED-SECRET — no confidential material exists on a public chain. Axis 6: both FROZEN (immutable deployed bytecode, un-forceable integrators), cardinality CAMPAIGN(N integrators) both, substrate flag identical (protocol hard-fork deprecations, e.g. SELFDESTRUCT, land on both equally). Axis 7: both FIXED-SPEC, horizon INSTITUTION. Axis 8: both STRONG within a recorded denominator (writable one-sentence invariants: k non-decreasing under fees; vested-amount monotone and bounded by schedule), THEORY-RESIDENT; both have symmetric out-of-denominator surface defaulting TASTE-ONLY, so the coverage-denominator defense yields the same-shaped record for each. Axis 9: both UNRECOVERABLE (misdirected funds are gone on-chain), rider UNAUDITED both.

**Misweighted concerns.** The AMM's correctness depends on shared state the adversary can move and on transaction ordering the adversary can purchase: it needs sandwich/front-run analysis, slippage bounds as runtime interlocks (concern 1), manipulation-resistant price sources (TWAP) if anything downstream reads its spot price, and agent-based economic attack simulation as first-class test evidence (concern 6). The vesting vault's transitions depend only on time and its own frozen schedule; ordering-attack machinery on it is dead weight. The instrument emits the same maximal-but-payload-oriented posture for both.

**Candidate repair (recorded, not applied — re-validation required after applying).** Add a capability sub-answer to the Adversarial exposure rider, recorded per adversarial channel: PAYLOAD (adversary supplies bytes you parse) | ORDERING/COMPOSITION (adversary can additionally schedule, front-run, or atomically compose calls around yours, or move shared state your invariants read — test: is there a public queue or shared-state platform where execution order is purchasable or adversary-influenced?). ORDERING adds economic/ordering attack simulation to concern 6 and value-dependent runtime interlocks (slippage/deviation bounds, staleness checks on read shared state) to concern 1. Checkable day one from the deployment target's execution model; re-fire on first deployment to a shared-ordering platform.

**Refuter confirmation.** The claimed identical classification is faithful cell-by-cell, and every contestable cell (e.g. reading a public chain as MULTI-NODE-essential instead of SINGLE-WRITER) reclassifies both projects together — even then the contention sub-question yields EXCLUSIVE for both (AMM reserves need a single agreed order; vault accounting is the spec's own canonical balance-style EXCLUSIVE case), with concern-9 machinery supplied identically by the platform. No axis, rider, or trigger records ordering purchasability or adversary-movable shared state: the Adversarial exposure rider's test is "who can produce bytes this component parses," and every ADVERSARIAL prescription is textually payload-scoped (fuzz the parsing path, never trade safety on the parsing path, sandbox the parsing stage, total parser). Axis 8's coverage denominator does not rescue it — no question elicits the ordering surface, so it defaults symmetrically for both. The projects are realistic stock artifacts and the engineering delta is material (value-dependent slippage/deadline interlocks, TWAP-style manipulation-resistant reads, multi-transaction ordering/economic attack simulation — this domain's dominant, nine-figure loss class; all dead weight on the vault). The "instrument decides poles, practitioner supplies the attack catalog" defense is unavailable under the set's own precedent: Round 4 accepted the CONVERGENT/EXCLUSIVE breach in exactly this shape (same classification word, different machinery class, decided by a checkable fact), and Rounds 2–3 accepted Modbus-vs-JSON and the side-channel pair despite competent practitioners knowing the fixes. The distinguishing fact is checkable day one from the deployment target's execution model, so a rider-style repair fits the set's discipline. Sufficiency breach confirmed.
