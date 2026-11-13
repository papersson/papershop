# Tools

What each tool is, what it needs, and what was checked. "Run" means run by the author of this
skill on 2026-11-13, on Linux x86-64; everything else is from the tool's own docs or source, and
versions move. Check the current docs before relying on a detail.

## Hegel: the default driver library

A family of property-based testing libraries with one native engine (libhegel) and a frontend per
language, inspired by Hypothesis and developed in part by Hypothesis developers at Antithesis. MIT
licence. It needs no Antithesis account. In beta: breaking changes are possible.

| Language | Package | Notes |
|---|---|---|
| TypeScript | `@hegeldev/hegel` | Node 20.11 or later. Run: 0.5.3. |
| Java, and other JVM languages | `dev.hegel:hegel` (Java 22+) or `dev.hegel:hegel-jna` (Java 17+) | Same API in both. Run: `hegel-jna` 0.12.1 from Scala 2.12.20 on Java 21. |
| Python | `hegeltest`, imported as `hegel` | Hypothesis itself is the mature alternative here. |
| Rust | `hegeltest` crate | |
| Go | `hegel.dev/go/hegel` | |
| C++ | CMake library `hegel` | |
| OCaml | `hegel` opam package | |

Stateful testing, as run in TypeScript and Java:

- A machine with **rules** (actions) and **invariants** (properties); `Stateful.run(machine, tc)`
  in Java, `hegel.stateful.run(tc, machine, state)` in TypeScript.
- **Swarm testing is built in**: each test case enables a random subset of rules.
- **Invariants are sampled by default in Java**: checked in full on the first and last state, and
  after any given rule with probability one over the step count. Write
  `@Invariant(alwaysRun = true)` for any invariant that must see every state. TypeScript has the
  same switch as `alwaysCheck: true`.
- Default step count is 50 in Java. `@Rule(weight = n)` offers a rule more often.
- **Pools** pass values created by one rule to later rules.
- **Concurrency** (Java): `Stateful.options().maxConcurrency(n)` runs rules on several workers;
  `@Rule(groups = ...)` says which may overlap.
- **Preconditions**: `tc.assume(condition)` skips the step without counting it. Count the skips
  yourself with an event.
- **Replay**: a failure prints a token; `@HegelTest(reproduceFailure = "...")` in Java,
  `.reproduceFailure("...")` in TypeScript.
- **Statistics**: `tc.event(...)` with `showStatistics` in TypeScript prints the share of test
  cases in which each event occurred.

A Scala 2.12 machine is an ordinary class with `@Rule def name(tc: TestCase): Unit` methods, run
with `Hegel.test((tc: TestCase) => Stateful.run(new Machine, tc))`.

## Bombadil: interfaces

Property-based testing for web and terminal user interfaces. MIT licence. Runs locally and in CI;
running inside Antithesis is optional. Run: 0.7.10, installed from npm, against a local page in
headless mode, where its default "no uncaught exceptions" property found a planted exception in
about five seconds.

- Install: `npm install --save-dev @antithesishq/bombadil`, or a single binary for macOS and Linux.
- Run: `bombadil browser test <url> [spec.ts]` or `bombadil terminal test --specification=spec.ts <command>`.
- Useful options: `--headless`, `--exit-on-violation`, `--time-limit=1m`, `--output-path <dir>`.
- Specifications are TypeScript or JavaScript modules exporting properties (`always`,
  `eventually`, `next` over extracted state) and action generators.
- After a violation: `bombadil browser inspect <dir>`, and `--reproduce <dir>` to replay. A
  `shrink` command exists and is marked experimental.

## Other libraries with a stateful API

Use these when Hegel does not fit the stack. Facts are for the versions named.

- **Hypothesis** (Python), 6.170: `RuleBasedStateMachine`. Swarm testing over rules is built in.
  Invariants run after every step. Keep all invariants in one machine: a test case stops at its
  first failing invariant, so fix or mark that one as expected and run again, instead of building
  a machine per property. A `@precondition` filters a rule before it runs and cannot be counted
  from inside it; the statistics report cases that could make no progress as invalid, and a
  condition that must be counted belongs inside the rule, with an event. `event()` with `--hypothesis-show-statistics` shows what was
  generated. Failures replay from a local database, from `--hypothesis-seed`, or from a
  `@reproduce_failure` token.
- **fast-check** (TypeScript), 4.10: `fc.commands` with `fc.modelRun`. No swarm testing: every
  position draws uniformly from all commands. The default size caps a sequence at ten commands;
  raise it. Replaying a commands failure needs the seed, the path and the `replayPath`. Its
  scheduler orders real promises, for check-then-act races in async code.
- **ScalaCheck** (Scala): has a stateful `Commands` API. Not run by the author.
- **ZIO Test** (Scala), 2.1: no stateful API. Its test clock controls time for code that sleeps.

## Model checking

- **TLA+** with PlusCal, checked by TLC. One jar (`tla2tools.jar`) from the tlaplus releases; needs
  Java. Translate with `java -cp tla2tools.jar pcal.trans Spec.tla`, check with
  `java -cp tla2tools.jar tlc2.TLC -deadlock Spec.tla`. `-deadlock` turns the deadlock check off,
  for models that are allowed to stop.

## What only the Antithesis platform provides

Deterministic replay of a whole deployed system, including its threads, network and clocks;
system-level fault injection; and guided exploration across many branched timelines. Hegel
drivers written for the deployed mode are the same programs their plugin runs on the platform, so
work done here carries over if the platform becomes available.
