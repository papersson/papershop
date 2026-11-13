# Review inputs

**Use when:** a workload passes, or has stopped finding things, and you doubt what it explores.
**Emits:** `workload-review.md`. This module is read-only: it reports, and changes nothing.

The question is how well the workload uses randomness to drive the SUT into different regions of
behaviour. The SUT is treated as a black box; the review works from the workload's code and from
the statistics of what it generated.

## Core principle

Randomize the *policy* per run, not only the *choices under a fixed policy*. If every test case
uses every action in the same proportions on the same pool of targets, every case explores about
the same region. Each case should draw its own configuration: which actions are enabled, how they
are weighted, how many targets there are, how long the run is, how the system starts.

## Steps

1. **Locate the workload** and read it: the actions, the generators, the preconditions, the
   starting state.
2. **Read `refs/anti-patterns.md`.**
3. **Get the statistics of a run**, if the workload can be run: which actions ran together, how
   often each precondition rejected a step, how often each fault took effect, and the distribution
   of whatever the bugs you fear would need (the most actions on one target, the longest queue).
   If the workload reports none of this, that is the first finding.
4. **Match what you see against the anti-patterns.** For each match: name it, point to file and
   line, say what region of behaviour is left unexplored, and what the workload could reach if it
   changed. Make it specific to this workload. "Your three actions are always all enabled with
   equal weight, so no run does only deletes" is a finding; "all actions are always active" is not.
5. **Tier the findings.**
   - *High signal*: a structural limit that puts whole regions out of reach.
   - *Worth considering*: more could be explored, but the limit is contextual.
   - *Observation*: might matter, depending on the SUT.
   When severity depends on domain knowledge you lack, state the structural fact and let the user
   judge.
6. **Report**, in this order: what the workload does, as you understand it, so the user can
   correct you; the findings by tier; what the workload already does well.

## Who reviews

Do not review a workload you wrote in the same session; you will find what you already know. Give
it to a fresh agent with this module, or skip the review and say it was skipped.

## Tone and scope

Findings are ceilings on what the workload can reach, not defects. A workload with several of
these patterns may still be finding bugs. Do not review whether the assertions would notice a bug
(that is `modules/mutation.md`), whether the SUT is correct, or whether the workload's code has bugs.
