# Assumption register

SUT: path/to/component @ commit
Date: YYYY-MM-DD
References:

One row per thing the SUT relies on a dependency to do. A row is unverified until someone has
checked it against the dependency's real behaviour.

| # | The SUT assumes | Dependency | Where the SUT relies on it (file:line) | What is known about the real behaviour | How it would be noticed if false | Made false by (fake, action) | Confirmed by, when |
|---|---|---|---|---|---|---|---|

<!-- Assumptions that are common and seldom written down:
- every message is delivered at least once
- messages about one key are handled in order
- a taken job is not handed out again
- a deferred operation is applied exactly as requested
- a read reflects the latest write
- a write based on stale data is refused
- a failed or timed-out call had no effect
- every consumer of what the SUT writes understands it (compare deployed versions, not source)
-->
