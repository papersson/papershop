# Run record

SUT: path/to/component @ commit
Date: YYYY-MM-DD
References:

<!-- What ran, so that someone else can run it again and compare. Guidance is in comments:
replace each with the content. -->

## Scope

<!-- Which modules of the skill were in scope. What the user agreed to beyond adding seams to
the SUT. Which environments may be touched. -->

## Command

<!-- The exact command that runs the workload, and the one that replays a failure from its
token or seed. The testing library and its version, and the settings that matter (number of
test cases, steps per case, whether the run is derandomized). -->

## Result

<!-- Verbatim, in a code block: what passed and what failed, per variant of each fake. -->

## What was generated

<!-- The statistics: in how many test cases each action and each fault took effect, how many
steps were rejected by a precondition, and which `Sometimes` and `Reachable` assertions fired.
Count generated test cases only: the attempts a library makes to shrink a failing case are not
test cases, and a run that stops at its first failure has explored little past it. -->
