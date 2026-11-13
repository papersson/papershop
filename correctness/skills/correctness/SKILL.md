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

This file is the entry point. It takes you from "we have tests and still get surprised" to a workload
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
- **Assertion**: how a property is checked: `Always`, `AlwaysOrUnreachable`, `Sometimes`,
  `Reachable`, `Unreachable`.
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
  test (`modules/workload.md`, "Pure functions") and stop.
- **Use Antithesis's plugin instead** when the team has Antithesis. This skill is for when it does not.
- **Research and audit only** when nothing of the SUT can be built or run by you. Say so, and
  lower every claim accordingly.

## Orient: three decisions before any module

**1. Draw the SUT boundary.** Pick the one component whose code you can change. Everything it
talks to is a dependency. A property about a dependency's behaviour is an *assumption*, and
assumptions are tracked separately from guarantees (`modules/research.md`, "Guarantees and assumptions"), because
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
`modules/research.md`, "Validating claims" once before any research.

## Modules

Each module is one file. For any task that ends in a workload, read `modules/research.md`,
`modules/fakes.md`, `modules/workload.md` and `modules/review-inputs.md` in full before starting:
they are short, and each leans on the others (the fault inventory is part of the workload file
so that it cannot be skipped). Read the rest when the task reaches them.

| Module | Use when | Emits |
|---|---|---|
| `modules/research.md` | you need to know what should be true of the SUT | `sut-analysis.md`, `property-catalog.md`, `properties/{slug}.md`, `assumptions.md`, `questions/{id}.md` |
| `modules/fakes.md` | a dependency cannot be run where the workload runs | `fakes/{dependency}.md` and the fake itself |
| `modules/workload.md` | you are building or extending the thing that exercises the SUT | the driver, its model, its assertions, `run-record.md`, `fault-inventory.md` |
| `modules/workload-deployed.md` | the run mode is a deployed SUT with the driver alongside | additions to the workload |
| `modules/workload-ui.md` | the run mode is a web or terminal interface | a Bombadil specification |
| `modules/review-inputs.md` | a workload passes and you doubt what it explored | `workload-review.md` |
| `modules/mutation.md` | you need to know whether the properties would catch a bug | `mutation-report.md` |
| `modules/triage.md` | a run failed | `findings/{id}.md`, one per distinct failure |
| `modules/fix-by-design.md` | a fix is being chosen between a guard and a redesign of the data | the "Fix" section of a finding |
| `modules/audit.md` | you can read production stores or logs | `audit-report.md` |
| `modules/model-checking.md` | the question is whether a design or a proposed fix is sound | a specification and its checked result |
| `modules/review.md` | the work is about to be reported as done | `review.md`, written by a reviewer who did not do the work |

## Workflows

A free-form request is a chain of modules. Common shapes:

- **A system new to this:** research, fakes (if needed), workload, review-inputs, mutation,
  audit. Where the stores can be read, the audit can run straight after research: it needs no
  harness.
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
- You propose properties and fakes; people confirm them, by answering a concrete scenario
  (`templates/question.md`). Until then a property is proposed (`Confirmed: no`), and its
  violation is a question for its owners, not a defect.
- Give every property the assertion type that matches its meaning, and say why
  (`refs/terminology.md`, "Assertion types").
- Check safety properties after every step, not once at the end. A check at the end misses a
  violation that later steps repair. Several libraries sample invariants by default; turn that off
  for every safety invariant (`refs/tools.md`).

**Inputs**

- Use the library's stateful API, never a hand-written loop over actions.
- Build choices from the library's combinators, and put the simplest alternative first, so the
  minimal counterexample is also the easiest to read.
- Randomize the configuration per test case (which actions are enabled, their weights, the pool
  of targets), not only the choices under one fixed configuration (`modules/review-inputs.md`).
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
  unrepresentable, next to the guard that would catch it (`modules/fix-by-design.md`).
- Do not invent an answer. An open question tagged `(needs human input)` is a deliverable.

**Limits of authority**

- A seam (a place where the test can supply a dependency) may be added to SUT code. Anything
  beyond that needs the user's agreement.
- Production is read-only. Shared environments are touched only with explicit permission.

## The scratchbook

Write artifacts under `correctness/scratchbook/` in the target repository unless the user names
another place. Begin each top-level file with provenance: a line `SUT: path @ commit`, a line
`Date: YYYY-MM-DD`, and the external references consulted.

```
correctness/scratchbook/
  sut-analysis.md          architecture, state, concurrency, failure-prone areas
  property-catalog.md      every property: slug, sentence, assertion type, priority, open questions
  properties/{slug}.md     evidence file per property
  assumptions.md           what the SUT relies on from its dependencies
  questions/{id}.md        one concrete scenario put to a person, and the answer
  fakes/{dependency}.md    evidence for each fake's behaviour, and how it was verified
  run-record.md            scope, the command that runs the workload, its result and statistics
  fault-inventory.md       every fault: an action, not applicable, or not tried
  workload-review.md       findings on input generation
  mutation-report.md       mutant per property, verdict, what was done about survivors
  audit-report.md          findings on stored data
  findings/{id}.md         one per distinct failure
  review.md                the independent reviewer's checklist and findings
```

Templates are in `templates/`. If scratchbook files already exist, extend them; do not rewrite
them unless asked.

## Before declaring done

Three steps, in this order.

1. **Run the mechanical check** and fix what it reports:

   ```
   python3 SKILL_FOLDER/scripts/check_scratchbook.py TARGET_REPO/correctness/scratchbook \
     --require run-record.md --require fault-inventory.md
   ```

   `SKILL_FOLDER` is the folder this file is in. Leave the two `--require` options out for a
   task that built no workload, and add `--require mutation-report.md` when mutation testing was
   in scope. The script checks form and cross-references: that every property has its evidence
   file, that every row of the fault inventory is accounted for, that every safety property has a
   row in the mutation report, and that every finding that reproduces says how to replay it. It
   cannot tell whether any of it is right.

2. **Have someone else review it.** Start a fresh sub-agent and give it the absolute paths of
   `modules/review.md`, `refs/terminology.md`, the script, the scratchbook, the workload and the
   SUT, and nothing else: no summary of what you
   did and no list of what you think is fine. It reruns the workload, replays the findings, goes
   through a checklist of what tends to be skipped (fault injection first), and writes
   `review.md` without changing anything. If no sub-agent is available, go through
   `modules/review.md` yourself as a separate pass, and say in the report that the review was
   not independent.

3. **Close or carry each of the reviewer's findings.** Fix what can be fixed and run step 1
   again. Whatever stays open goes into the report as it was written.

Then tell the user, in this order: what was found, what was not tried, what remains unverified,
and what the review left open.
