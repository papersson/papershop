# Triage record — <component name>

**Project:** <project> · **Component:** <one-line scope: the state it owns, the surfaces it ships>
**Date:** <date> · **Classifier:** <who> · **Mode:** classify | recheck (diff vs <date>) | grade (of <date>)
**Run shape:** quick pass + deep passes on <axes>, ~<N> minutes, <M> questions answered.

> Every settled answer names its artifact. Every provisional answer names its re-fire trigger.
> Every concern call names its winning pole, its deciding fact, and its falsifier. "Both matter"
> does not appear in this document.

## 1. Axis answers

| # | Axis | Answer | Evidence artifact (or PROVISIONAL + trigger) | Confidence | Falsifier |
|---|---|---|---|---|---|
| 1 | Fault reproducibility | REPLAYABLE / SEEDED / ENVIRONMENTAL / <core>-core/<shell>-shell | | settled / assumed / deferred | |
| 2 | Resource pressure | heat: HOT/WARM/COOL/DEFERRED · envelope: ENVELOPED/UNBOUNDED | | | |
| 3 | Tail obligation | NONE / SOFT / SOLD | | | |
| 4 | Writer topology | SINGLE-WRITER / MULTI-WRITER-ONE-NODE / MULTI-NODE (essential/pre-sliced; CONVERGENT/EXCLUSIVE) · restart: PER-REQUEST / SESSION-MASS(N) | | | |
| 5 | Data gravity | IN-PROCESS / PERSISTED-SINGLE-OWNER / CROSSES-BOUNDARIES (+ per-format regimes if deep pass ran) · inputs: TRUSTED-ONLY / ADVERSARIAL · secrets: NONE / OBSERVED-SECRET | | | |
| 6 | Commitment reversibility | FLUID / EDGED(<surfaces>) / FROZEN · cardinality: LOCAL / CAMPAIGN(N) · substrate: STABLE / LANDLORD | | | |
| 7 | Requirements volatility | FIXED-SPEC / NEGOTIABLE-EDGES / DISCOVERING · horizon: THROWAWAY / SEASONS / INSTITUTION | | | |
| 8 | Oracle strength | STRONG(denominator: <surface>) / PARTIAL / TASTE-ONLY · theory: RESIDENT / ABSENT | | | |
| 9 | Defect consequence | HARM / UNRECOVERABLE / BOUNDED-LOSS(<bound>) / RETRY-AND-SHRUG · assurance: AUDITED / UNAUDITED | | | |

**Marked assumptions** (facts the brief lacked but a day-one engineer would have; assumed values):
- <assumption → plausible value → who can confirm>

**Translations applied** (question wordings that misfit this component's shape, and the leaf's
translation used instead): <none / list>

## 2. Concern weightings

Weight vocabulary: **dominant** (shapes the architecture; spend real effort), **default**
(follow the pole, no extra ceremony), **dormant** (machinery here is speculative weight).

| # | Concern | Pole that wins here | Weight | Deciding fact (axis answer) | Falsifier |
|---|---|---|---|---|---|
| 1 | Invariant placement | | | | |
| 2 | Types vs layout | | | | |
| 3 | Values vs places | | | | |
| 4 | Crash aftermath | | | | |
| 5 | Schema openness | | | | |
| 6 | Test evidence | | | | |
| 7 | Abstraction timing | | | | |
| 8 | Design-phase weight | | | | |
| 9 | Coordination & tail | | | | |
| 10 | Agent delegation | | | | |

## 3. The three sentences that matter

Forced summary — if the record redirects no effort, the run failed the listicle test:

1. **Spend effort on:** <the 1–3 concerns that dominate, and the first concrete act each implies>
2. **Explicitly skip:** <the machinery this component does NOT need, that a reasonable engineer
   might have built anyway>
3. **The call most likely wrong:** <which answer rests on the weakest artifact, and what watching
   it costs>

## 4. Re-fire triggers — this record's expiry conditions

| Trigger event (observable) | Re-opens | Likely direction |
|---|---|---|
| <e.g. second writer appears in deployment plan> | Axis 4 → concerns 3, 9 | |
| <e.g. first non-lockstep consumer of <table>> | Axis 5 → concern 5 | |
| <e.g. budget artifact signed / SLA clause lands> | Axis 2b / 3 | |
| <e.g. maintenance handed to agents / adjudicator leaves> | Axis 8 rider → concern 10 | |

## 5. Grading (filled by `grade` mode — leave empty at classify time)

**Graded:** <date> · **Against:** <what happened: milestones, incidents, changes>

| Call | Verdict: held / misread / question-was-wrong | What actually happened |
|---|---|---|
| | | |

**Lessons for the classifier:** <misreads — what artifact would have prevented each>
**Defects in the instrument:** <question-was-wrong findings — flag these for skill maintenance,
they are bugs in the axis leaves, not in this record>
