# Assumption register

One row per thing the SUT relies on a dependency to do. A row is unverified until someone has
checked it against the dependency's real behaviour.

| # | The SUT assumes | Dependency | Where the SUT relies on it (file:line) | What is known about the real behaviour | How we would notice it is false | Confirmed by, when |
|---|---|---|---|---|---|---|
| 1 | every message is delivered at least once | broker | | | an item older than a threshold with no trace of handling | unverified |
| 2 | messages about one key are handled in order | broker | | | | unverified |
| 3 | a request for a later effect is applied exactly as requested | | | | compare the result with the request after it lands | unverified |
| 4 | a read reflects the latest write | store | | | | unverified |
| 5 | a write based on stale data is refused | store | | | two concurrent writers in a test environment | unverified |
| 6 | a failed or timed-out call had no effect | | | | | unverified |
| 7 | every consumer of what the SUT writes understands it | | | | compare deployed versions, not source | unverified |

Replace the example rows. For each row, also record which fake can make it false and which action
of the workload does so.
