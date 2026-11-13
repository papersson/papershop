# Workload

**Use when:** you are building or extending the thing that exercises the SUT.
**Emits:** the driver, its model, and its assertions, in the target repository's test tree;
`run-record.md` and `fault-inventory.md` in the scratchbook.

A workload is everything added to exercise the SUT. Its centre is the **driver**: one program that
picks actions at random, sends them to the SUT, and records each outcome in a **model** of what
the SUT should now contain. Every random choice comes from the testing library, so a failure can
be replayed and shrunk.

## Steps

1. **Map what the workload must reach.** List the SUT's whole surface from the code that receives
   inputs: every operation, every input that sends a handler down a different branch, background
   work, configuration that changes behaviour, and what the real clients send, including their
   retries. For each item, name the action that exercises it or say why it is out of scope.
2. **Pick the run mode** (SKILL.md, "Orient"):
   - In-process: the SUT's code called directly, dependencies faked. The default; described
     below.
   - Deployed: the SUT running in containers, the driver alongside. Read
     `modules/workload-deployed.md`.
   - UI: a web or terminal interface, explored with Bombadil. Read `modules/workload-ui.md`.
3. **Pick the model.** For each property in the catalog, decide what the driver must remember so
   an assertion can judge the SUT's state or response. Keep it small enough to be obviously right.
4. **Write the actions.** One rule per action. Each draws its inputs, performs the action, and
   updates the model.
5. **Add the faults** as further actions ("Faults" below). This step is not optional: delivery
   faults alone leave failing dependencies and crashes untested.
6. **Write the assertions.** One per property, with the type the catalog gave it. When a
   property nobody has confirmed fails, do not report a defect: its minimal counterexample is the
   scenario to ask about (`templates/question.md`), and the check is kept as an expected failure
   until someone answers. Add `Sometimes` and `Reachable` assertions for the states the workload
   exists to reach, so a passing run can be told apart from one that never got there.
7. **Run, and read what was generated** before reading the result. Record the command, the
   result and the statistics in `run-record.md` (`templates/run-record.md`), so that someone
   else can run it again and compare. Then hand the workload to `modules/review-inputs.md`.
8. **Hand failures to `modules/triage.md`.**

## Rules

- **Every decision is made in the driver.** No fake, helper or fixture draws its own randomness or
  reads its own clock.
- **Record a request as sent before sending it.** A request that fails or times out is not known
  to have had no effect: it may still land. Keep it in the model as possible for a bounded window,
  and let the assertions accept either outcome until it resolves.
- **Check safety after every step.** Where the library samples invariants by default, turn
  sampling off for every safety invariant (`refs/tools.md`).
- **Aim several actions at the same few things.** Bugs need two actions to meet. Draw a small pool
  of targets per test case, and let its size vary.
- **Do not filter to "valid" actions** beyond what the harness physically requires. An action on a
  thing that does not exist, or is already finished, is an input the SUT must handle.
- **Use the library's stateful API.** A hand-written loop over actions cannot shrink its sequence
  and gives every run the same mix.

## The in-process run mode

The SUT's code is called directly from the driver, in the driver's process, with every dependency
replaced by a fake. This is the run mode with exact replay: one seed fixes every choice.

### Pure functions

If the code under test has no state, skip the state machine. Write one property: generate the
inputs, call the function, assert the law. Good first laws: a round trip returns the original; an
invariant of the output holds for every input; two implementations agree; the function does not
crash. An existing example test with its inputs generated is a legitimate first property.

### The seam

A seam is a place where behaviour can be altered without editing the code there. The driver needs
one for each source of nondeterminism the SUT touches: stores, queues, clients of other services,
the clock, randomness, and concurrency.

- Find where the SUT reaches for each of these, and make the smallest change that lets a caller
  hand it in: a constructor parameter, a function argument, an interface with two implementations.
- Before changing any behaviour, record what the code does today with a characterization test, so
  the refactoring is checked against the present, not against intentions.
- Once the seam exists, check every later refactoring of the SUT differentially: keep the old
  version, run old and new on the same generated sequences against the same fakes, and compare
  the stores after every step. A characterization test covers the examples someone thought of;
  this covers the orderings nobody did. The seam itself cannot be checked this way unless the old
  code can run against local dependencies, so keep that first change small enough to read.
- If a type or effect system can show the seam in the function's signature, use it. A handler
  whose type names the stores it needs cannot quietly grow a new dependency.

### The state machine

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

### Properties as plain functions

Write each safety property as a function from the stores (and the model, if needed) to a failure.
The same function then serves the workload, the mutation run and the audit of stored data. A
property that needs history ("this never changes") needs memory in the driver; one that reads only
the current state can also run against production.

### Replay

Every failure prints the minimal counterexample and a replay token. Keep the token with the
finding. A fix is not done until the token passes and a fresh run does too.

### What this mode does not show

One process and, unless the library's concurrent mode is used, one action at a time. A fake can be
wrong. Nothing here exercises the real network, the real stores or the real scheduler.

## Faults

A fault is a disruption injected on purpose. In a workload each one is an action the driver may
choose, so its timing is explored like any other input and a failure can be replayed.

### The inventory

Go through every source of nondeterminism the SUT touches: message delivery, time, calls to
dependencies, reads, the process itself, and concurrency. Record the decision per row in `fault-inventory.md` (`templates/fault-inventory.md`): an action,
not applicable, or not tried, each with its rule or its reason.

| Fault | What the driver does |
|---|---|
| message delivered out of order | delivers any pending message, not only the oldest |
| message delivered twice | delivers a message again |
| message held back | leaves a message pending while other actions run |
| clock advanced | advances the clock, only when something is waiting on it |
| dependency call fails | makes a call to a dependency fail |
| dependency call times out after taking effect | reports a timeout for a call whose effect has landed |
| deferred operation applied late | applies a pending request after other actions have happened |
| stale read | returns an old value, where the real store allows one |
| crash mid-operation | stops the SUT after the nth write of an operation, then restarts it |
| concurrent operations on one target | starts two operations on one target and lets the library order their steps |

### Rules

- **A fault needs a precondition that makes it meaningful.** An action that can always run and
  usually changes nothing soaks up test cases. Advancing time is the usual offender.
- **A crash is not an exception the SUT can catch.** Model it so that no handler in the code under
  test intercepts it, keep whatever was written before it, and run the SUT's recovery on restart.
- **Decide which properties must survive a fault at every instant**, and which may be false until
  recovery finishes. Write the second kind so they are checked only when the SUT is up.
- **Count what happened.** Record, per test case, how often each fault actually took effect and
  how often the operation finished first. A fault rule that never takes effect is a `Sometimes`
  failure.
- **A timeout is not a failure of the effect.** After a timed-out call the effect may or may not
  have happened. Both must be acceptable to the model until evidence settles it.

### Two writes

When an operation writes to two places, a crash between them leaves one of two bad states,
whichever order the writes are in. Find which property must hold at every instant, write that
side first, and make the second write a step that is safe to repeat and is repeated by recovery.
Where the second place can be computed from the first, compute it instead: then there is nothing
to leave half done.

## Done when

- [ ] Every item of the surface is exercised by an action or listed as out of scope with a reason.
- [ ] Every property in the catalog has an assertion, or a note saying why it cannot be checked here.
- [ ] `fault-inventory.md` is filled in: every row is an action of the driver that took effect, is not applicable, or is listed as not tried with a reason. Delivery faults alone are not enough: include a failing dependency and a crash mid-operation.
- [ ] `Sometimes` and `Reachable` assertions cover the states the workload exists to reach, and they fire.
- [ ] A failure prints a minimal counterexample and a replay token.
- [ ] The run's generation statistics have been read and are reported with the result.
