# Triage

**Use when:** a run failed.
**Emits:** `findings/{id}.md`, one per distinct failure.

## Steps

1. **Replay it.** Use the replay token or seed. If it does not reproduce, say so, and record
   everything from the one occurrence you have.
2. **Read the minimal counterexample as a story.** Step by step, in plain words: who did what, and
   what the stores say at the end. If you cannot tell the story, shrink further by hand: remove a
   step, replay, keep the removal if it still fails.
3. **Classify the cause.** One of:
   - *SUT defect*: the code violates a property that is right.
   - *False assumption*: a dependency does something the SUT relies on it not to do. The SUT's
     code may be exactly as written; the defect is in the dependency, or in relying on it. Record
     it against the row in `assumptions.md`, and say whether the SUT can defend itself.
   - *Fake infidelity*: the fake does something the real dependency does not. Check against the
     fake's evidence file before blaming the SUT.
   - *Wrong property*: the property forbids something the system is meant to allow.
   - *Workload defect*: the driver or model is wrong.
4. **Find the mechanism.** Name the line or the interleaving. A finding is not done at "it fails".
5. **Check for siblings.** Would the same mechanism break another property, or another caller?
6. **Propose the fix and its kind**: a guard in code, or a change of design that makes the bad
   state unrepresentable. For a SUT defect, read `modules/fix-by-design.md` before settling on a guard.
   Say which, and what each would cost.
7. **Keep the counterexample as a regression test**, with its replay token.

## A finding contains

The property violated, in its one sentence. The minimal counterexample, verbatim. The replay
token. The story. The cause and its class. Whether it reproduces on replay. What was not
investigated.

## Notes

- Shrinking is a search. A counterexample with steps that change nothing is common; say so, and
  do not present it as minimal.
- Several failures from one run are often one cause seen through different properties. Group them.
- A failure that will not replay in a deployed run is still a finding. Try to reduce it to an
  in-process reproduction, where it can be replayed.
