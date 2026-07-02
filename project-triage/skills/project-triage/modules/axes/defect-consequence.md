# Axis 9: Defect consequence

**Quick question.** If this component silently does the wrong thing for one hour (for batch systems:
one wrong run), what does it cost — bodily harm, unrecoverable loss, a priced bounded loss, or a
shrug? In the same pass: does any outside authority inspect this component's change process?

## Full question (deep pass)

If this component silently does the wrong thing for one hour, trace every actuation path (rewritable
row, ledger entry, email sent, public statement, physical actuator) and ask two yes/no questions per
path: does rerunning fix it; if not, does a NAMED compensation mechanism exist (who replays, from
what log)? The answer is the **MAX over all paths** — stop enumerating at the first
UNRECOVERABLE/HARM path.

**Priced-rerun rule:** where rerunning fixes it, price the rerun before recording SHRUG — burn rate
× expected detection latency, plus calendar time to redo, read off the project's existing budget or
schedule artifact. If the priced rerun exceeds ~10% of the project budget or two weeks of a schedule
carrying a named external commitment, the rerun IS the compensation mechanism: record BOUNDED-LOSS
with the rerun's priced cost as the recorded loss bound. (A $30M three-month model retraining
answers BOUNDED-LOSS; tonight's Spark job answers RETRY-AND-SHRUG.)

**Rebuild-source falsifier:** RETRY-AND-SHRUG additionally records its falsifier — name the rebuild
source the rerun depends on (which upstream system, log, or snapshot), its retention window, and who
owns its decommission. An answer that cannot name its rebuild source is BOUNDED-LOSS at best, and
**a rerun against a dead or truncated source is undefined, not merely more expensive.**

**Rider — external assurance** (same consequence pass; asked **unconditionally** — a RETRY-AND-SHRUG
or BOUNDED-LOSS answer does not skip it, because **audit scope attaches by law and money flow, not
by defect severity**: PCI change control can bind a component whose defects are shrug-level, and SOX
ITGC binds honestly-BOUNDED-LOSS components): name the outside authority that inspects this
component's CHANGE PROCESS or evidence — external financial auditor (SOX 404 ITGC), assessor
(PCI-DSS), certification body or regulator (ISO 27001, DO-178C, GxP/FDA) — and the scoping artifact
that puts this component in their sample (SOX scoping memo, PCI SAQ/ROC scope, ISO Statement of
Applicability, PSAC, validation plan). This is a *process inspector*, not a consumer of a shipped
artifact — it does not make the component EDGED on commitment reversibility, and it is not a reader
of any data sink on data gravity. None nameable = UNAUDITED. (Recorded bet: the first walk where a
shrug-level answer causes the audit question to be skipped promotes this rider to a standalone axis
verbatim.)

## Answers

- **RETRY-AND-SHRUG** (rerun fixes it AND rerun priced below threshold AND rebuild source named with
  retention window and decommission owner as the recorded falsifier) | **BOUNDED-LOSS**
  (compensation mechanism named, not imagined — including the priced-rerun case, with the rerun cost
  as the recorded loss bound) | **UNRECOVERABLE** | **HARM** (bodily harm).
- Assurance flag: **UNAUDITED** | **AUDITED** (named authority, named scoping artifact).

## Day-one checkability

Actuation paths enumerate from the brief; the two per-path questions are yes/no against named
mechanisms, not severity vibes — the recoverability ladder is what keeps this axis from degenerating
into unfalsifiable "criticality." The rider is answerable on day one from scoping documents.

## Decides

- **Concern 1, invariant placement (primary):** UNRECOVERABLE/HARM → type-level proof plus
  independent runtime interlocks that crash before corruption. BOUNDED-LOSS → interlock intensity
  scales with the recorded loss bound — a rerun priced in the millions buys per-step runtime
  interlocks (loss-spike halts, invariant guards, checksum gates on checkpoints) that crash BEFORE
  corrupting last-good state. RETRY-AND-SHRUG → crashing assertions are the economical pole.
- **Concern 4, crash aftermath (override):** supervise-and-restart is rational only when the crash
  window's damage is recoverable and cheap. UNRECOVERABLE/HARM forces bug-extinction plus redundancy
  even for environmental faults, overriding what fault reproducibility alone would recommend.
  BOUNDED-LOSS prices the hunt: silent-wrongness faults are hunted to extinction before launch when
  each undetected occurrence burns a priced slice of the loss bound.
- **Concern 8, design-phase weight (override):** UNRECOVERABLE/HARM raises design weight even when
  code is freely redeployable — the damage, not the artifact, is the irreversible thing (Knight
  Capital: fully reversible deploy, $440M unrecoverable loss). BOUNDED-LOSS with a bound material to
  the project reaches the same override — mandating launch-readiness review, dry runs, and
  validate-before-checkpoint-commit design even at FLUID plus DISCOVERING. Via the flag: AUDITED →
  the change-control pipeline itself is a designed deliverable — enforced author/approver
  separation, production write access removed from developers with tamper-evident break-glass
  logging, immutable multi-year audit trails — engineered up front even at FLUID.
- **Concern 10, agent delegation (cap):** UNRECOVERABLE/HARM caps delegation below what oracle
  strength permits — the oracle itself may be wrong; a human review gate stays. Via the flag (a cap
  INDEPENDENT of both oracle grade and consequence level): AUDITED → a second named human approver
  distinct from the author is mandatory on every production change; author-adjudicated change is
  legally unavailable, and agent-autonomous deploys stay off the table even if the oracle later
  reaches STRONG — the ceiling is agent-authors/human-approves, technically enforced.
- **Concern 6, test evidence (via the flag — the evidence's CONSUMER changes its required FORM, not
  its kind):** AUDITED → whatever evidence the other axes prescribe must additionally be produced as
  signed, immutably retained, auditor-sampleable packets (test-run records tied to change tickets,
  retention per the authority's window); CI logs that rotate and undocumented local runs do not
  count as evidence at all under this flag.

## Re-fire triggers

- Any new actuation path attached (new downstream consumer, side-effecting integration, money
  movement); a 10× growth in rerun price (burn rate or expected detection latency).
- **For RETRY-AND-SHRUG:** loss, truncation, retention shortening, or announced decommission of the
  named rebuild source (including a legacy system's strangler-fig cutover date and calendar expiry
  of a retention window), or a detection-latency estimate first exceeding that retention window.
- **Rider:** the component newly enters an audit scope — IPO or SOX scoping change, cardholder-data
  flow attaches, regulated-market entry, certification pursuit announced.

## Translations and misfits

- **Batch systems:** read "silently wrong for one hour" as **"one wrong run"** — the run, not the
  hour, is the natural unit; the two per-path questions apply unchanged.
- **Slow cumulative physical damage** (battery drain, flash wear on rarely-reporting devices): the
  hour-trace under-captures it, but the priced-rerun rule's detection-latency term recovers the
  answer — months of undetected drain price out as BOUNDED-LOSS even though nothing "reruns."

## Skip when

Stop the path trace at the first UNRECOVERABLE/HARM path — the answer is the MAX, and further
enumeration buys nothing. Skip the rerun pricing when every path is trivially cheap to redo tonight.
Never skip the assurance rider: it is one question against scoping documents, it binds independently
of severity, and skipping it on a shrug-level answer is the failure its recorded bet watches for.
