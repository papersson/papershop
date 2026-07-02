# Axis 7: Requirements volatility

**Quick question.** Would a stakeholder sign one paragraph of acceptance criteria as stable for 6–12
months — today? Unsignable = DISCOVERING. In the same conversation, ask the horizon rider: who runs
or edits this code after this week, how many more times, per what calendar?

## Full question (deep pass)

Write one paragraph of acceptance criteria now and ask the stakeholder to sign it as stable for 6–12
months. Proxies: external fixation (law, RFC, prior system being replaced byte-for-byte),
last-quarter spec churn, purpose-is-the-hypothesis (the brief describes an experiment on users).
Unsignable = DISCOVERING. **The test is present-tense, not predictive** — inability to sign *today*
is the answer.

**Rider — modification horizon** (carried in the same stakeholder pass — ask it in the same
conversation as the signing test): after this week, who runs or edits this code, how many more
times, per what calendar? **THROWAWAY** is claimable only with a named decommission date or event
AND an enforcing mechanism outside team willpower (the meeting after which it is deleted, the
allocation that expires, a CI job that removes it). **SEASONS** = a bounded run of months in one
maintainer's hands. **INSTITUTION** = open-ended calendar or rotating/inheriting maintainers.
**Unknown defaults long: you never predict longevity, you only ever prove shortness.** (Recorded
bet: the first walk where the signing conversation fails to surface the horizon promotes this rider
to a standalone axis verbatim.)

## Answers

- **FIXED-SPEC** | **NEGOTIABLE-EDGES** | **DISCOVERING**.
- Horizon flag: **THROWAWAY** (gated as above) | **SEASONS** | **INSTITUTION**.

## Day-one checkability

The signing test is an act you perform now, not a forecast: either the paragraph is writable and the
stakeholder signs, or one of those fails today. A stakeholder who signs confidently and turns out
wrong is handled by the amendment trigger, not by second-guessing the signature.

## Decides

- **Concern 7, abstraction timing (primary, jointly with the horizon — the horizon caps the
  volatility answer):** THROWAWAY → never abstract, even at FIXED-SPEC — there is no "after
  repetition" before the decommission date. INSTITUTION → repetition is already on the calendar, so
  extracting the domain vocabulary pays at adoption. Between those caps: FIXED-SPEC → design the
  vocabulary up front; DISCOVERING → extract after repetition (early names will be wrong names).
- **Concern 8, design-phase weight (primary, jointly with commitment reversibility; horizon
  floor):** DISCOVERING+FROZEN is the trap quadrant — the resolution is to *shrink the committed
  surface*, not heavy-design the guess. FIXED-SPEC+FROZEN → maximum design weight. THROWAWAY → zero
  design weight regardless of FIXED-SPEC, unless defect consequence records UNRECOVERABLE/HARM.
  INSTITUTION → modest structural design pays even at FLUID.
- **Concern 6, test evidence (partial, with horizon floor/ceiling):** DISCOVERING → examples as
  discardable requirement docs. THROWAWAY → zero tests; eyeball verification is the economical pole
  regardless of oracle strength. INSTITUTION → a curated regression corpus becomes the contract that
  survives rotating maintainers.
- **Concern 5, schema openness (partial):** DISCOVERING → keep the moving periphery open even
  in-process; closing it into ADTs is premature.
- **Concern 10, agent delegation (partial, via horizon):** THROWAWAY → machine-checkable substrate
  construction is waste. INSTITUTION → substrate for future drive-by or agent maintainers is
  rational investment at adoption.

## Re-fire triggers

- **Main (the amendment trigger):** first material amendment to signed criteria demotes the answer
  and re-fires concerns 7 and 8.
- **Rider (the adoption event):** a second scheduled run, a second person inheriting the code, or
  the decommission date passing undeleted demotes THROWAWAY at that moment and re-fires concerns 6,
  7, 8, and 10.

## Translations and misfits

- **Mixed-signability components:** one label per component can lose real structure — a signable
  core pipeline next to unsignable matching heuristics. NEGOTIABLE-EDGES absorbs this shape, and
  concern 5's "keep the moving periphery open" clause catches the unsignable remainder; if the two
  parts would answer *other* axes differently too, that is a component-split signal, not a
  volatility nuance.
- **THROWAWAY claims:** the gate is deliberately hard to pass. "We'll delete it after the migration"
  without a named event and an enforcing mechanism is SEASONS at best — the characteristic failure
  is the throwaway script nobody notices acquiring durable state, and the adoption-event trigger
  exists to catch exactly that.

## Skip when

Never skip the quick question or the rider — together they are two questions in one conversation and
jointly decide concerns 7 and 8's primary inputs. There is no deeper enumeration to skip; the deep
pass is only the proxy checklist, needed when no stakeholder is reachable to sign.
