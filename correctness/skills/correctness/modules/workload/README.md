# Workload

**Use when:** you are building or extending the thing that exercises the SUT.
**Emits:** the driver, its model, and its assertions, in the target repository's test tree.

A workload is everything added to exercise the SUT. Its centre is the **driver**: one program that
picks actions at random, sends them to the SUT, and records each outcome in a **model** of what
the SUT should now contain. Every random choice comes from the testing library, so a failure can
be replayed and shrunk.

## Steps

1. **Map what the workload must reach.** List the SUT's whole surface from the code that receives
   inputs: every operation, every input that sends a handler down a different branch, background
   work, configuration that changes behaviour, and what the real clients send, including their
   retries. For each item, name the action that exercises it or say why it is out of scope.
2. **Pick the run mode** (SKILL.md, "Orient") and read its leaf:
   - `in-process.md`: the SUT's code called directly, dependencies faked. The default.
   - `deployed.md`: the SUT running in containers, the driver alongside.
   - `ui.md`: a web or terminal interface, explored with Bombadil.
3. **Pick the model.** For each property in the catalog, decide what the driver must remember so
   an assertion can judge the SUT's state or response. Keep it small enough to be obviously right.
4. **Write the actions.** One rule per action. Each draws its inputs, performs the action, and
   updates the model.
5. **Add the faults** as further actions. Follow `faults.md`.
6. **Write the assertions.** One per property, with the type the catalog gave it. Add `Sometimes`
   and `Reachable` assertions for the states the workload exists to reach, so a passing run can be
   told apart from one that never got there.
7. **Run, and read what was generated** before reading the result. Then hand the workload to
   `modules/review-inputs/`.
8. **Hand failures to `modules/triage/`.**

## Rules

- **Every decision is made in the driver.** No fake, helper or fixture draws its own randomness or
  reads its own clock.
- **Record a request as sent before sending it.** A request that fails or times out is not known
  to have had no effect: it may still land. Keep it in the model as possible for a bounded window,
  and let the assertions accept either outcome until it resolves.
- **Check safety after every step.** Turn off invariant sampling for any invariant that keeps
  memory between steps (`refs/tools.md`).
- **Aim several actions at the same few things.** Bugs need two actions to meet. Draw a small pool
  of targets per test case, and let its size vary.
- **Do not filter to "valid" actions** beyond what the harness physically requires. An action on a
  thing that does not exist, or is already finished, is an input the SUT must handle.
- **Use the library's stateful API.** A hand-written loop over actions cannot shrink its sequence
  and gives every run the same mix.

## Done when

- [ ] Every item of the surface is exercised by an action or listed as out of scope with a reason.
- [ ] Every property in the catalog has an assertion, or a note saying why it cannot be checked here.
- [ ] `Sometimes` and `Reachable` assertions cover the states the workload exists to reach, and they fire.
- [ ] A failure prints a minimal counterexample and a replay token.
- [ ] The run's generation statistics have been read and are reported with the result.
