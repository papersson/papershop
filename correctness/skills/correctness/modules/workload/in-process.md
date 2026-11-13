# In-process workload

The SUT's code is called directly from the driver, in the driver's process, with every dependency
replaced by a fake. This is the run mode with exact replay: one seed fixes every choice.

## Pure functions

If the code under test has no state, skip the state machine. Write one property: generate the
inputs, call the function, assert the law. Good first laws: a round trip returns the original; an
invariant of the output holds for every input; two implementations agree; the function does not
crash. An existing example test with its inputs generated is a legitimate first property.

## The seam

A seam is a place where behaviour can be altered without editing the code there. The driver needs
one for each source of nondeterminism the SUT touches: stores, queues, clients of other services,
the clock, randomness, and concurrency.

- Find where the SUT reaches for each of these, and make the smallest change that lets a caller
  hand it in: a constructor parameter, a function argument, an interface with two implementations.
- Before changing any behaviour, record what the code does today with a characterization test, so
  the refactoring is checked against the present, not against intentions.
- If a type or effect system can show the seam in the function's signature, use it. A handler
  whose type names the stores it needs cannot quietly grow a new dependency.

## The state machine

Use the stateful API of the testing library for the SUT's language (`refs/tools.md`). Hegel has
the same shape in every language it supports:

- **The machine** holds the SUT, its fakes, and the model.
- **Rules** are the actions. Each takes the test case, draws what it needs, acts, and updates the
  model. A rule whose precondition does not hold rejects the step; count how often that happens.
- **Invariants** are the safety properties. Mark any that must see every intermediate state.
- **Pools** hold values created by earlier rules (keys, ids) for later rules to draw from.
- **Swarm testing** is built in: each test case enables a random subset of rules.

Shape, in pseudocode:

```
machine:
  sut    = new SUT(fakes...)
  model  = empty
  rule submit(tc):      x = tc.draw(inputs);  sut.handle(x);  model.record(x)
  rule deliver(tc):     m = tc.draw(queue.any());  queue.remove(m);  sut.receive(m)
  rule duplicate(tc):   m = tc.draw(queue.any());  queue.add(m)
  rule advance(tc):     clock.add(tc.draw(durations))
  invariant always:     check_property_a(sut.stores, model)
  invariant always:     check_property_b(sut.stores, model)
```

## Properties as plain functions

Write each safety property as a function from the stores (and the model, if needed) to a failure.
The same function then serves the workload, the mutation run and the audit of stored data. A
property that needs history ("this never changes") needs memory in the driver; one that reads only
the current state can also run against production.

## Replay

Every failure prints the minimal counterexample and a replay token. Keep the token with the
finding. A fix is not done until the token passes and a fresh run does too.

## What this mode does not show

One process and, unless the library's concurrent mode is used, one action at a time. A fake can be
wrong. Nothing here exercises the real network, the real stores or the real scheduler.
