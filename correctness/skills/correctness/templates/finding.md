# Finding {id}

<!-- Guidance is in comments: replace each with the content. -->

**Property violated:** <!-- the sentence, and its slug from the catalog -->
**Found by:** <!-- workload | mutation | audit | model checking, with the run mode -->
**Reproduces on replay:** <!-- yes | no | not applicable -->
**Replay:** <!-- the token or seed, and the command that replays it -->

## Minimal counterexample

<!-- The verbatim output, in a code block. -->

## The story

<!-- Step by step, in plain words: who did what, and what the stores say at the end. -->

## Cause

**Class:** <!-- SUT defect | false assumption | unfaithful fake | wrong property | workload defect -->
**Mechanism:** <!-- the line or the interleaving -->

## Fix

<!-- For a SUT defect, both of these. For the other classes, what changes: the fake, the
property, the workload, or how the SUT defends itself against the dependency. -->

**A guard:** <!-- the smallest change in code -->
**A design change:** <!-- what would make the bad state impossible to construct, and what it would cost -->

## Not investigated

<!-- What was not looked at, and why. -->
