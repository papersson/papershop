---
name: project-triage
description: >
  Classify a software project, component, or significant task to decide where engineering effort
  should go — which concerns dominate this particular thing, which recede, and why. Use when
  starting or inheriting a project ("what matters here?", "triage this project", "how careful do we
  need to be with this?"), when a component's circumstances change (new consumers, new writers, a
  budget or SLA appearing), or when revisiting an old triage record to grade it against what
  actually happened. NOT for deciding what to build (that is discovery), NOT for diagnosing a slow
  system (that is performance work), and NOT mid-implementation mechanics where no classification
  changes the answer — it gates on these and routes away.
---

# project-triage

This file is a router. Given one component, you answer nine questions about observable facts of
the thing itself; each answer resolves specific engineering tensions — it says which pole of a
contested trade-off wins *for this component* and why. The output is never "understanding": it is
a **triage record** — committal, falsifiable, with every answer naming the artifact it was read
from and every provisional answer carrying the concrete future event that reopens it.

The premise: almost every strong engineering opinion (make illegal states unrepresentable; let it
crash; design everything up front; just ship and iterate) is right in some regime and malpractice
outside it. The questions below are the regime tests. Most engineering doctrine fails by exporting
a rule out of the regime where it was earned — this skill exists to stop that at project start,
per component, in writing.

## Gate — is triage the right move?

Run first, every time:

- **Starting or inheriting a component, or scoping significant work on one?** Proceed.
- **"What should we build?"** — the problem itself is unframed → decline; that is discovery work
  (groundwork's territory), and triage of an unframed problem classifies a guess.
- **"Why is this slow?"** — reactive performance work → decline toward performance-engineering.
  (Triage tells you whether latency *machinery deserves effort*; it does not find bottlenecks.)
- **Mid-implementation question where no classification changes the answer** (how to name this
  function, which library API) → say so and just answer it.
- **Genuinely throwaway task?** Not a gate-out — it is the cheapest possible run. Say: "ephemeral
  regime, nearly everything recedes," confirm the one thing that still binds (see the
  requirements-volatility horizon: THROWAWAY is claimable only with a named decommission event and
  an enforcing mechanism), and record that one line. The characteristic failure is not the
  throwaway script — it is the throwaway script nobody notices acquiring durable state.

## Three modes

- **`classify`** (default) — full run on a new or never-triaged component. The loop below.
- **`recheck`** — a named re-fire trigger fired (second writer added, first external consumer,
  budget artifact signed, codebase going agent-maintained). Re-answer only the fired axis and
  anything downstream of it in the record; diff against the old record; the diff is the output.
- **`grade`** — revisit a record ≥3 months old or after a milestone. For every committal call:
  did reality agree? Score each axis answer held / misread / question-was-wrong. Misreads teach
  the classifier; question-was-wrong findings are defects in this skill — record them in the
  record's grading section AND flag them for the skill's own maintenance. Grading is the fluency
  engine: the instrument only compounds if reality gets to mark its homework.

## Orient — decompose before classifying

**The unit is the component, not the project.** Real projects are composites, and the most
expensive misclassification is treating a component by the rules of its surroundings — the payment
core inside a SaaS product engineered like the settings page next to it. First output is always
the component split (`templates/component-split.md`): distinct regimes get distinct records. When
in doubt, split along state boundaries (what it owns) rather than team or repo boundaries. A
single-service component with few integrations is usually one record; flag a composite when two
parts of it would answer any axis differently.

**Then run two passes, not one.** The nine axes in full — riders, sub-answers, per-format
enumerations — cost 25–35 answers and 20–45 minutes. Most components don't need full depth on most
axes:

1. **Quick pass (~10 minutes):** the headline question of each axis, in the order below. Each
   quick answer either settles the axis or flags it for a deep pass. Cheap-to-answer axes
   (tail obligation, requirements volatility, defect consequence) usually settle in one question.
2. **Deep passes (only where flagged):** data gravity's per-format enumeration only when the
   component is integration-heavy (3+ boundary-crossing formats); writer topology's contention
   sub-question only at MULTI-NODE; resource pressure's envelope arithmetic only when a budget
   artifact exists. The deep-pass conditions are stated per axis leaf.

Expect ~20 minutes for a single-service component, up to ~35 for a multi-format integration hub.
The time is carried or broken at data gravity — that axis alone can be a third of an
integration-heavy run, which is why it is gated.

## The loop

1. **Split** — components with distinct regimes (`templates/component-split.md`).
2. **Quick pass** — headline answer per axis, evidence artifact named or the answer marked
   provisional (`modules/axes/`, top section of each leaf).
3. **Deep passes** — descend only where the quick pass flagged (`modules/axes/`, lower sections).
4. **Resolve** — map answers to concern weightings via each axis's "decides" table; open
   `modules/concerns/` leaves only where the call needs the full argument or the poles are close.
5. **Record** — fill `templates/triage-record.md`: every call names its winning pole, the deciding
   fact, and its falsifier (what future observation would prove the call wrong).
6. **Schedule the re-fires** — the record lists its own expiry conditions: the named events that
   reopen each provisional answer. A triage record without re-fire triggers is a snapshot
   pretending to be a truth.

## Answer integrity — non-negotiable in every pass

Violating these produces a confident, wrong record:

- **Artifact or provisional — never vibes.** An answer is settled only by a named observable
  artifact: the SLA clause, the datasheet, the deployment plan, the signed acceptance paragraph,
  the fan-out call site. "It feels performance-sensitive" is not an answer; it is DEFERRED with a
  named trigger. Failure to name the artifact IS the answer (it means the pressure isn't real yet).
- **Committal calls only.** Every concern gets a pole and the fact that decided it. "Both matter"
  is a failed run — if the poles are genuinely balanced, the record says which fact would tip it
  and sets that as a watch trigger.
- **Falsifiable or worthless.** Each call is paired with the observation that would prove it
  wrong. This is what makes `grade` mode possible and what makes a wrong record *visibly* wrong
  later instead of quietly useless.
- **Unknowns are declared, not guessed.** A fact the brief lacks but a real engineer would have on
  day one: assume the plausible value and mark the assumption. A fact genuinely unknowable today:
  DEFERRED, with the trigger named. Defaults follow each axis's stated direction (e.g. longevity
  is never predicted, only shortness proven).
- **The listicle test.** If the finished record would read the same for any project, the run
  failed — say so rather than shipping generic output. The record's value is exactly the parts
  that would be different for a different component.
- **Translate, don't force.** Some question wordings misfit some system shapes (batch pipelines,
  standard web topologies). Each axis leaf carries its known translations — use them instead of
  forcing a bad literal fit, and note the translation in the record.

## Router — which axis are you answering?

| Quick question | Axis leaf |
|---|---|
| Do failures reproduce, or is the environment part of the fault model? | `modules/axes/fault-reproducibility.md` |
| Millions of instances on a measured path — or a hard RAM/flash/energy/size budget? | `modules/axes/resource-pressure.md` |
| Is a latency distribution actually *sold* to someone? | `modules/axes/tail-obligation.md` |
| How many writers touch the mutable state, at worst? | `modules/axes/writer-topology.md` |
| Who reads your data that you can't force to upgrade — and who can write to your inputs? | `modules/axes/data-gravity.md` |
| What have you shipped that you can't take back? | `modules/axes/commitment-reversibility.md` |
| Would a stakeholder sign the acceptance criteria as stable for 6–12 months? | `modules/axes/requirements-volatility.md` |
| Can you state, in one sentence, a machine-checkable test of correct behavior? | `modules/axes/oracle-strength.md` |
| What does a defect actually cost — harm, unrecoverable loss, bounded loss, or a shrug? | `modules/axes/defect-consequence.md` |

## The ten concerns the answers decide

Each concern leaf holds the tension's two poles with attribution, the axis mapping, and what each
pole implies concretely. Open a leaf when a call needs the full argument; the axis leaves carry
the short-form mapping for the common case.

| # | Concern | Decided primarily by |
|---|---|---|
| 1 | Invariant placement — type-level proof vs runtime assertion (`modules/concerns/invariant-placement.md`) | defect consequence, modulated by data gravity flags, fault reproducibility, resource pressure |
| 2 | Type safety vs memory layout (`modules/concerns/types-vs-layout.md`) | resource pressure (sole decider), overridden on flagged paths by data gravity |
| 3 | Values vs places (`modules/concerns/values-vs-places.md`) | resource pressure × writer topology jointly; tail obligation secondary |
| 4 | Crash aftermath — drain the bug vs supervise and restart (`modules/concerns/crash-aftermath.md`) | fault reproducibility; writer topology picks the supervision unit |
| 5 | Schema openness — closed types vs open maps (`modules/concerns/schema-openness.md`) | data gravity (class × per-format regime; adversarial flag reverses tolerant parsing) |
| 6 | Test evidence — examples vs properties vs simulation (`modules/concerns/test-evidence.md`) | fault reproducibility × writer topology, scoped by oracle strength |
| 7 | Abstraction timing — vocabulary first vs extract after repetition (`modules/concerns/abstraction-timing.md`) | requirements volatility × modification horizon |
| 8 | Design-phase weight — blueprints vs ship-and-iterate (`modules/concerns/design-phase-weight.md`) | commitment reversibility × requirements volatility (the quadrant) |
| 9 | Coordination and tail (`modules/concerns/coordination-and-tail.md`) | tail obligation + writer topology (the pair covers it) |
| 10 | Agent delegation depth (`modules/concerns/agent-delegation.md`) | oracle strength × theory presence, capped by defect consequence and frozen surfaces |

## Templates

- `templates/component-split.md` — the decomposition worksheet: state-boundary-first splitting,
  the composite flag, one record per regime.
- `templates/triage-record.md` — the deliverable: axis answers with artifacts and falsifiers,
  concern weightings with deciding facts, re-fire triggers, and the grading section that `grade`
  mode fills in later.

## Known limits — read before trusting a run

- **One documented hole:** on platforms where an adversary can purchase *execution ordering* (public
  blockchains are the clean case), the adversarial-exposure rider distinguishes only who can supply
  input bytes, not ordering/composition attackers. Two contracts classify identically while only one
  needs ordering-attack engineering. The candidate repair is recorded in `refs/validation.md` —
  unapplied, pending re-validation. If you classify smart contracts, apply extra judgment there.
- **Runtime honesty:** the ~20-minute target holds for single-service components; multi-format
  integration hubs run 30–45 minutes. The deep-pass gating above is the mitigation.
- **Batch systems and managed runtimes** carry known question-wording misfits; each axis leaf's
  "translations" section covers them (nightly-deadline vs tail, "one wrong run" vs "wrong for an
  hour", logical vs physical writers under Spark-style engines, platform memory quotas as budget
  artifacts).

## Where this stops

The record weights concerns; it does not design the system. No architecture, no stack choices, no
schemas. Downstream: performance-engineering when tail obligation lands SOLD and reactive work
begins; discovery/groundwork when the split reveals an unframed problem; ordinary engineering
skills for the build itself. The record is an input to design, not the design.

## Self-check before shipping a record

- Gate passed — this was a component triage, not discovery, not diagnosis?
- Component split done, and no two parts of one record would answer an axis differently?
- Every settled answer names its artifact; every unsettled one is DEFERRED with a named trigger —
  no vibes anywhere?
- Every concern got a committal pole + deciding fact + falsifier — no "both matter"?
- Deep passes ran exactly where flagged (and were skipped where not — no 45-minute run on a
  single-service component)?
- Known translations applied where the component shape misfits a question's wording?
- Re-fire triggers listed — the record knows its own expiry conditions?
- Would the record read differently for a different component (the listicle test)?
- If `grade` mode: every original call scored held / misread / question-was-wrong, and
  question-was-wrong findings flagged for skill maintenance?

If any answer is no, fix that one thing before handing the record over.
