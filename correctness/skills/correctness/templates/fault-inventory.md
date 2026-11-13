# Fault inventory

SUT: path/to/component @ commit
Date: YYYY-MM-DD

One row per source of nondeterminism. Keep every row and the first column as written:
`scripts/check_scratchbook.py` looks the rows up by name. Status is one of:

- `action`: the driver has a rule for it. Name the rule, and give how often it took effect in the
  last run. A rule that never took effect is not a fault that was tried.
- `not applicable`: the SUT has no such source. Say why.
- `not tried`: it applies and the workload does not do it. Say why. This is a gap to report, and
  the workload is not done while a failing dependency call or a crash is in this state.

| Source | Status | Rule in the driver, or the reason | Took effect in |
|---|---|---|---|
| message delivered out of order | | | |
| message delivered twice | | | |
| message held back | | | |
| clock advanced | | | |
| dependency call fails | | | |
| dependency call times out after taking effect | | | |
| later effect applied late | | | |
| stale read | | | |
| crash mid-operation | | | |
| concurrent operations on one target | | | |

Example of a filled row:

```
| message delivered twice | action | `duplicate` | 187 of 300 test cases |
| stale read | not applicable | the store is a single node with read-your-writes | |
```
