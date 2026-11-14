# Mutation report

SUT: path/to/component @ commit
Date: YYYY-MM-DD
References:

## Baseline

<!-- Which properties pass on the unmutated SUT, and which `Sometimes` and `Reachable`
assertions fired. -->

## Mutants

One row per safety property in the catalog (assertion `Always`, `AlwaysOrUnreachable` or
`Unreachable`). The verdict starts with one of:

- `killed`: the target property failed. Give the minimal counterexample or its replay token.
- `survived`: the marker fired and nothing failed. Say what was done about it.
- `collateral`: another property failed instead. Name it.
- `not reached`: the marker never fired. A finding about the workload.
- `equivalent`: the wrong value never became observable. Say why.
- `stillborn`: after a design fix, the mutant no longer compiles.
- `not mutated`: say why (fails on the baseline, or lives in code that cannot be changed).

| Property | Mutant | Verdict | Counterexample, or the reason |
|---|---|---|---|

<!-- A filled row looks like this:
| post-at-most-once | worker.py:8, the check of posted reports removed | killed | token AXkB3 |
-->

## Rejected candidates

<!-- Per property, the mutants considered and not used, with reasons. -->
