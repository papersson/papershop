# Property discovery

Look at the same code through one lens at a time. Each lens finds properties the others miss, so
treat each pass as a fresh examination and resist skipping one because an earlier pass "covered
that area". If sub-agents are available, run one per focus in parallel and merge; otherwise work
through the list in order. The wildcard always runs last.

## Attention focuses

1. **Data integrity.** Invariants on stored state, write ordering, constraints that must hold
   across records or across stores, ways data can be lost or corrupted under concurrent access.
2. **Concurrency.** Shared mutable state, read-then-write sequences that something can interleave,
   lock ordering, atomicity that is assumed but not enforced.
3. **Failure recovery.** Operations cut short by a crash, restart correctness, retries, recovery
   code that assumes a clean state, errors that are caught and only logged.
4. **Protocol contracts.** What the SUT promises its callers and what it expects of its
   dependencies: ordering, delivery, response codes that hide an error.
5. **Resource boundaries.** Queues without bounds, backlogs, lag, exhaustion, missing backpressure.
6. **Security boundaries.** Checks that a sequence of valid operations can bypass.
7. **Distributed coordination.** Leadership, quorum, partitions, replication lag, stale reads. May
   yield nothing for a single process; say so.
8. **Lifecycle transitions.** Startup before dependencies are ready, shutdown with work in flight,
   migrations and upgrades under traffic.
9. **Idempotency and replay.** Duplicate delivery, at-least-once processing, an operation applied
   twice, a message about an older state arriving late.
10. **Version compatibility.** What happens when the deployed version of a component differs from
    the source you are reading, or two versions run side by side.
11. **Wildcard.** Told only what the other ten cover, look for what they will all miss: a property
    at the intersection of two focuses, a guarantee the system gives without ever stating it, a
    failure nobody would think to check. A vague but specific suspicion is worth recording.

## For each property found

Record, in the format of `templates/property.md`:

- the sentence, and the invariant or condition it checks
- the assertion type and why it fits (`refs/terminology.md`)
- the code paths examined, with file and line
- the scenario in which it would fail
- confidence, and the evidence for it
- open questions, each with why it matters and what the answer would change

## Merging

- **Deduplicate.** Note which focuses found each property.
- **Resolve disagreements** about assertion type or priority, and record the reasoning.
- **Write relationships.** Group properties that share a code path or a failure mechanism, and
  note where one implies another.
