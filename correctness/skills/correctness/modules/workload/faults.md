# Faults

A fault is a disruption injected on purpose. In a workload each one is an action the driver may
choose, so its timing is explored like any other input and a failure can be replayed.

## The inventory

Go through every source of nondeterminism the SUT touches and decide how the driver controls it.

| Source | Actions to give the driver |
|---|---|
| Message delivery | deliver any pending message (not only the oldest); deliver one again; hold one back |
| Time | advance the clock, only when something is waiting on it |
| A dependency call | fail it; time it out after it took effect; answer late |
| A request for a later effect | apply any pending request now, after other actions have happened |
| A read | return a stale value, where the real store allows one |
| The process | crash after the nth write of an operation, then restart |
| Concurrency | start two operations on the same target and let the library order their steps |

## Rules

- **A fault needs a precondition that makes it meaningful.** An action that can always run and
  usually changes nothing soaks up test cases. Advancing time is the usual offender.
- **A crash is not an exception the SUT can catch.** Model it so that no handler in the code under
  test intercepts it, keep whatever was written before it, and run the SUT's recovery on restart.
- **Decide which properties must survive a fault at every instant**, and which may be false until
  recovery finishes. Write the second kind so they are checked only when the SUT is up.
- **Count what happened.** Record, per test case, how often each fault actually took effect and
  how often the operation finished first. A fault rule that never bites is a `Sometimes` failure.
- **A timeout is not a failure of the effect.** After a timed-out call the effect may or may not
  have happened. Both must be acceptable to the model until evidence settles it.

## Two writes

When an operation writes to two places, a crash between them leaves one of two bad states,
whichever order the writes are in. Find which property must hold at every instant, write that
side first, and make the second write a step that is safe to repeat and is repeated by recovery.
Where the second place can be computed from the first, compute it instead: then there is nothing
to leave half done.
