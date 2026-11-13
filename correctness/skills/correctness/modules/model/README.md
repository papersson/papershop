# Model

**Use when:** the question is whether a design, or a proposed fix to ordering logic, is sound.
**Emits:** a specification, the configuration it was checked with, and the result.

A model checker explores every reachable state of a small specification and checks an invariant
in each. Where a workload samples orderings of the real code, a model check covers all orderings
of a small design. It can run before any code exists.

## When it earns its cost

- Logic where order and concurrency matter: handlers, retries, hand-offs between components.
- A fix is proposed and you want to know, in minutes, whether it closes the hole.
- A known incident you want to understand: write the model so that it reproduces the incident
  first. A model that catches a bug you already had is one the team will trust.

Not for sequential logic, and never for a whole system. Model one handler or one protocol.

## Steps

1. **Choose the smallest world that can show the problem**: one record, two or three messages.
2. **Write the state** as a few variables and **the steps** as the things that may happen, each as
   its own process: the producer, the consumer taking *any* pending message, whoever else acts.
   Model "delivered twice" and "out of order" by making the pending messages a set and letting the
   consumer leave a message in it.
3. **Write the invariant**, the same sentence as in the property catalog.
4. **Run the checker.** A violation comes with a shortest trace: read it as the story of a
   counterexample.
5. **Change one line for the fix, and run again.** Then grow the world by one, and run again.

TLA+ with PlusCal and the TLC checker is the usual choice (`refs/tools.md`).

## Limits to state every time

- The model is not the code. A defect in the implementation that the model does not describe is
  invisible to it.
- The result holds for the configuration checked: this many records, this many messages.
- A model checker needs the invariant written down as much as a workload does. A missing property
  is missed by both.
