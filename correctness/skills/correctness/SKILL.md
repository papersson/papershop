---
name: correctness
description: >
  Find the bugs example tests cannot reach in stateful, concurrent or message-driven code. Research
  a system under test into a catalog of testable properties and assumptions, fake the dependencies
  that cannot be run and verify the fakes, build a workload that explores the system with faults (a
  Hegel state machine driver, or Bombadil for web and terminal UIs), review how well its inputs
  explore, check the properties with mutation testing, and audit stored data against them. Use when
  asked to "test this properly", "find race, ordering or retry bugs", "write property-based or
  stateful tests", "what are the invariants here", "fake this dependency", "would our tests catch
  X", or after an incident with late, duplicated, reordered or lost messages, a crash mid-operation,
  or a stale read. Follows the terminology and strategies of Antithesis's public agent skills and
  needs no Antithesis account. NOT for ordinary example-based unit tests, performance testing, or
  proofs.
---

# correctness

This file is a router. It takes you from "we have tests and still get surprised" to a workload
that generates the surprises on demand, and it stops when each finding is a replayable,
minimal counterexample with a property behind it. Every module below emits one artifact into a
scratchbook; understanding is not a deliverable.

It borrows its vocabulary and much of its method from Antithesis's public skills (see
`refs/sources.md`). The product itself is not required. What it would add, deterministic replay of
a whole deployed system and system-level fault injection, is named wherever its absence matters.

## Terms

Used throughout, defined in full in `refs/terminology.md`.

- **SUT**: the system under test. Here, usually one component you can change.
- **Property**: a statement that must hold. Safety (a bad thing never happens), liveness (a good
  thing eventually happens), reachability (a state is, or is never, reached).
- **Assertion**: how a property is checked: `Always`, `Sometimes`, `Reachable`, `Unreachable`.
- **Workload**: everything added to exercise the SUT. Its **driver** picks actions at random,
  sends them, and records outcomes in a **model** of what the SUT should contain.
- **Fault**: a disruption injected on purpose: delay, duplication, reordering, a failing
  dependency, a crash.
- **Fake**: a working in-memory replacement for a dependency. One kind of test double.
- **Property catalog** and **evidence file**: the list of properties, and for each one the code
  paths, observations and open questions behind it.

## Gate: is this the right tool?

Run first, every time.

- **Yes** when the SUT keeps state and at least one of these is true: messages or requests can
  arrive late, twice or out of order; several writers touch the same state; work can fail or crash
  halfway; behaviour depends on time.
- **A smaller thing will do** when the code is a pure transformation. Write one property-based
  test (`modules/workload/in-process.md`, "Pure functions") and stop.
- **Use their plugin instead** when the team has Antithesis. This skill is for when it does not.
- **Research and audit only** when nothing of the SUT can be built or run by you. Say so, and
  lower every claim accordingly.

## Orient: three decisions before any module

**1. Draw the SUT boundary.** Pick the one component whose code you can change. Everything it
talks to is a dependency. A property about a dependency's behaviour is an *assumption*, and
assumptions are tracked separately from guarantees (`modules/research/assumptions.md`), because
you cannot enforce them, only detect when they are false.

**2. Find out which run modes are open.** Ask; do not assume. Deployment environments are often
owned by another team, and "it runs in containers" does not mean you may start, stop or reach them.

| Run mode | You need | You get | You give up |
|---|---|---|---|
| In-process, dependencies faked | to build and call the component's code | exact replay from a seed, every fault a choice of the test | the real dependencies: a fake can be wrong |
| Deployed, driver alongside | a place to run the SUT's containers and a driver, and network reach to them | the real services and their real interactions | exact replay; faults limited to what you may disrupt |
| UI, with Bombadil | a URL or a terminal program | exploration of a real interface against temporal properties | anything not visible through the interface |
| Stored data, audited | read access to the stores (and logs, for history) | the one state production actually reached | states it has not reached yet |
| Design, model checked | nothing but the design | every ordering of a small model | any statement about the code |

Most work starts in the first row and adds the fourth. Choose the second only once access is
confirmed in writing.

**3. Hold the evidence standard.** A sentence in a doc, a comment, or a bug report is a lead, not
a fact. A claimed guarantee becomes a property to test; never write that it holds. Read
`modules/research/validating-claims.md` once before any research.

## Modules

Read only the module the task needs. Each has a `README.md` and, where listed, leaves.

| Module | Use when | Emits |
|---|---|---|
| `modules/research/` | you need to know what should be true of the SUT | `sut-analysis.md`, `property-catalog.md`, `properties/{slug}.md`, `assumptions.md` |
| `modules/fakes/` | a dependency cannot be run where the workload runs | `fakes/{dependency}.md` and the fake itself |
| `modules/workload/` | you are building or extending the thing that exercises the SUT | the driver, its model, its assertions |
| `modules/review-inputs/` | a workload passes and you doubt what it explored | `workload-review.md` |
| `modules/mutation/` | you need to know whether the properties would catch a bug | `mutation-report.md` |
| `modules/triage/` | a run failed, or a fix is being chosen between a guard and a redesign | `findings/{id}.md`, one per distinct failure |
| `modules/audit/` | you can read production stores or logs | `audit-report.md` |
| `modules/model/` | the question is whether a design or a proposed fix is sound | a specification and its checked result |

## Workflows

A free-form request is a chain of modules. Common shapes:

- **A system new to this:** research, fakes (if needed), workload, review-inputs, mutation, audit.
- **One feature or handler:** targeted research, workload, mutation.
- **After an incident:** validate the report, reproduce it as a failing property (workload or
  model), confirm with mutation that the property would have caught it, audit for damage already
  done.
- **Tests exist and find nothing:** review-inputs, then mutation. Change no SUT code.

If a task will run unattended for long, ask up front, in one message, for what you can foresee
needing: scope, permission to change SUT code beyond adding a seam, which environments may be
touched, and where findings should be reported.

## Rules that hold in every module

**Properties**

- State each property in one sentence before writing its check. One property, one law.
- Give every property the assertion type that matches its meaning, and say why
  (`refs/terminology.md`, "Assertion types").
- Check safety properties after every step, not once at the end. A check at the end misses a
  violation that later steps repair. Several libraries sample invariants by default; turn that off
  for any invariant that keeps memory between steps (`refs/tools.md`).

**Inputs**

- Use the library's stateful API, never a hand-written loop over actions.
- Build choices from the library's combinators, and put the simplest alternative first, so the
  minimal counterexample is also the easiest to read.
- Randomize the policy per test case, not only the choices under a fixed policy
  (`modules/review-inputs/`).
- Never skip a case silently. Count what was filtered, and print it. Where the library filters
  before a rule runs and gives no count, move the condition inside the rule and record an event.
- Never narrow a generator to step around a known bug. Keep the bug as an expected failure.
- Before believing a passing run, print what it generated and check that the states that matter
  were reached (`Sometimes` and `Reachable` assertions).

**Reporting**

- Say what ran and what was observed. "Not observed in 300 test cases" is not "does not happen".
- Every failure is reported with its minimal counterexample, its replay token or seed, and the
  story of the steps in plain words.
- For a defect in the SUT, say whether a redesign of the data would make the bad state
  unrepresentable, next to the guard that would catch it (`modules/triage/fix-by-design.md`).
- Do not invent an answer. An open question tagged `(needs human input)` is a deliverable.

**Limits of authority**

- A seam (a place where the test can supply a dependency) may be added to SUT code. Anything
  beyond that needs the user's agreement.
- Production is read-only. Shared environments are touched only with explicit permission.

## The scratchbook

Write artifacts under `correctness/scratchbook/` in the target repository unless the user names
another place. Begin each top-level file with provenance: the path and commit of the SUT, the
date, and the external references consulted.

```
correctness/scratchbook/
  sut-analysis.md          architecture, state, concurrency, failure-prone areas
  property-catalog.md      every property: slug, sentence, assertion type, priority, open questions
  properties/{slug}.md     evidence file per property
  assumptions.md           what the SUT relies on from its dependencies
  fakes/{dependency}.md    evidence for each fake's behaviour, and how it was verified
  workload-review.md       findings on input generation
  mutation-report.md       mutant per property, verdict, what was done about survivors
  audit-report.md          findings on stored data
  findings/{id}.md         one per distinct failure
```

Templates are in `templates/`. If scratchbook files already exist, extend them; do not rewrite
them unless asked.

## Before declaring done

Review the output against the module's own checklist. If sub-agents are available, give a fresh
one the module file and the artifacts and have it do the review; a reader without your context
catches what you no longer see. Then tell the user, in this order: what was found, what was not
tried, and what remains unverified.
