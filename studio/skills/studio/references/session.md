# Session videos

A session video explains something the user is learning or just did, for the user. It is a modest
cut they can watch the same day, not a polished master. This file is the one home of the `session`
delivery policy; the stages are still `explainer.md`'s, and this file says which of them shrink,
which staging rules replace the defaults, and when the work stops.

`video.json` `delivery` is `polished` (the default; nothing below applies) or `session`
(`studio new NAME --delivery session`). Choose `session` for a video of the user's own learning or
work session; choose `polished` when they ask for polish, a master, 1080p or a video for others.
Delivery is separate from level (assumed knowledge) and drive (who can judge the subject): a
learner-driven session still needs independent subject checks.

## The policy

- **Budget in review cycles: one.** Elapsed time is recorded (`studio stage`), not capped.
  `max_rounds` and `motion_rounds` default to 1 (`kit/src/studio_kit/reviews.py`); the user can
  raise them.
- **540p desk cut.** Drafts are enough (`studio cut` without `--final`); a final render and 1080p
  are on request. "Cheap" never means unreadable: when the code or a label is not legible at 540p
  (check a full-size crop), enlarge it or raise the resolution for that cut.
- **One beat preview** replaces separate boards and animatic: the beat table below, played as
  stills against the narration (`studio boards`, then `studio animatic`) in one pass, so pacing is
  read before scenes exist. Polish (stage 11), hero-event embellishments (weight, consequence,
  hitstop, shake), broad frame sweeps and further wording rounds are on request.
- **Kept in full:** source verification and Evidence rows, voice completeness (`studio voice-check`),
  duration and sync checks, critical legibility, the generated-timeline rule, and a recorded
  "unavailable" for any check that could not run. A preview is not allowed to be wrong.
- **Demoted from the defaults:** learner quotations, running ledgers of mistakes or notes, and
  repeated "simulated" labels. Keep one concise disclosure where a model or slowed demonstration
  would otherwise mislead, and full provenance in `research/`, off the stage. Keep captions
  available.

## The beat table comes before the prose

Write it under the Chain in SCRIPT.md, one row per beat, before any narration text:

| Beat | Question or concept | Becomes visible | What changes | Settles (hold) | The voice adds | Exit state |
|---|---|---|---|---|---|---|

Silence is a planned beat: a row may have no voice. The narration then explains the settled picture
instead of captioning movement.

## Staging

- **Introduce, settle, explain, move on.** A new mechanism appears with no voice over its motion,
  holds at least 1 s, and only then is explained. Voice over motion is allowed only for something
  already introduced, when the sentence describes exactly that motion (a replay of a familiar
  demonstration). Mark such an overlap in the beat table's "The voice adds" cell as `over:` and the
  beat it replays.
- **One new thing at a time.** A cause and its effect shown together count as one thing. Two
  unrelated introductions within the settle time are a conflict to fix.
- **A question gets room.** Pause about 2 s after a question the viewer should answer first.
- **A loop needs a subject and a stop.** An ambient or repeating demonstration freezes (or ends)
  when the next concept starts, unless the repetition is the subject.
- **No typing under speech.** Highlight the line to be discussed about 0.6 s before the sentence
  that refers to it; the voice never talks over keystrokes.
- **Declare it in `staging.json`** (beside cues.json; the format is at the top of
  `kit/src/studio_kit/staging.py`): intros, replays, typing, questions and loops with cues.json times.
  `studio check` (or `--only staging`) names each conflict with the narration, and a re-voiced
  narration reports what stopped fitting instead of passing.
- These numbers are starting values for this policy, tuned by watching, not universal laws. Other
  genres keep their own grammar.

## Narration

Full explanatory sentences in a collaborative "we" where it is natural ("now we give the loop a
clock"), written over a settled picture. Short clauses still, for the ear (`taste/narration.md`);
this is about completeness and stance, not length.

## Typed code

The default choreography for typed code (v5 of the two-clocks video, accepted by the user):

- the editor is **collapsed** between uses and opens when code is being written or read;
- **folds** hide declarations already discussed, in **source order**: the visible lines are the
  program's own lines, in its order;
- a **helper card** shows what a folded or external piece does, only when the sentence needs it;
- a line is **highlighted before** the sentence refers to it (about 0.6 s);
- the video ends on the **full-loop payoff**: the complete code, folds open, running.

Each is configurable per video in `video.json` `code` (`studio typing`, `code.md`). Code on screen
is self-contained: every name visible is defined, deliberately folded with its declaration, or an
introduced external API.

## The one review cycle

One pass of the roles the claim risk calls for, dispatched together, then scoped corrections
checked by a fresh reviewer on the changed material only (`reviews.md`). Separate factual
blockers (must be fixed or removed), staging failures, and optional copy edits (left alone). A
cap ends repeated grading; it never turns an open factual blocker into a pass. If one remains at
the limit, stop and ask the user. Never record a waiver on their behalf.

## The human pass

The final listen and view is the user's: they watch the important concept transitions and listen to
the cut. The receipt records who watched and listened, and when (`reviews.md`, listening and
approval); nothing infers it from automated checks. Checks the kit could not run are listed as
unavailable in the handoff, not omitted.
