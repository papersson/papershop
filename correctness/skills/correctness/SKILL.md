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

This skill takes you from "we have tests and still get surprised" to a workload that generates
the surprises on demand, and it stops when each finding is a replayable, minimal counterexample
with a property behind it. Every part emits an artifact into a scratchbook; understanding is not
a deliverable.

**Read this whole file before starting.** It holds the common path in one place: research, fakes,
the workload with its faults, triage and mutation testing. They lean on each other, and a step
kept in another file is a step that gets skipped. Only what belongs to a different run mode, a
different question or a different agent has a file of its own ("Other files", near the end).

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
  test ("Pure functions") and stop.
- **Use Antithesis's plugin instead** when the team has Antithesis. This skill is for when it does not.
- **Research and audit only** when nothing of the SUT can be built or run by you. Say so, and
  lower every claim accordingly.

## Orient: three decisions before anything is built

**1. Draw the SUT boundary.** Pick the one component whose code you can change. Everything it
talks to is a dependency. A property about a dependency's behaviour is an *assumption*, and
assumptions are tracked separately from guarantees ("Guarantees and assumptions"), because
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
"Validating claims" once before any research.

## Rules that hold everywhere

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

## Workflows

A free-form request is a chain of the parts below and the other files. Common shapes:

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

## Research

**Use when:** you need to know what should be true of the SUT before anything is built to test it.
**Emits:** `sut-analysis.md`, `property-catalog.md`, `properties/{slug}.md`, `assumptions.md`,
`questions/{id}.md`.

Research turns a codebase into a list of concrete, checkable properties, each with the evidence
behind it. It does not decide whether the properties hold. That is what the workload is for.

### Scope question first

Ask once, and record the answer verbatim in every artifact's provenance:

> Before I start: are there docs, design notes, related repositories, issue trackers, incident
> write-ups or chat channels outside this directory that I should also consult? "Just this
> directory" is fine.

If nobody can answer (an unattended run), record "not asked: unattended" in the provenance,
work from the directory alone, and list what you would have asked under open questions.

Beyond that, ask only what you cannot infer safely: which component is the SUT, and which known
incidents or failure modes matter most.

### Steps

1. **Analyse the SUT** and write `sut-analysis.md`: what it does, what state it keeps and where,
   who else writes that state, what runs concurrently, every input it receives (requests, messages,
   timers, configuration), every dependency it calls, and where failure is most likely. Read the
   code that receives inputs, not only the docs. Note what the real clients send, including their
   retries.
2. **List what exists.** Search for checks already in the code or tests that state a property
   (assertions, invariants, validation, existing property-based tests). Record file and line. No
   later step should propose a check that is already there. Ask for the alerts that would page
   someone, too: each is a property the team already cares about, checked after the fact.
3. **Discover properties**, one attention focus at a time ("Property discovery" below).
4. **Separate guarantees from assumptions** ("Guarantees and assumptions" below).
5. **Validate anything taken from outside the code** ("Validating claims" below).
6. **Write the catalog and the evidence files** from `templates/property.md`. Give each property a
   kebab-case slug, one sentence, an assertion type with the reason for it, a priority, and its
   open questions.
7. **Classify each property's enforceability**: by the data type alone, by an abstract type with
   a smart constructor, or not by types at all (the table in `modules/fix-by-design.md`).
   A property a compiler could guarantee is a design finding, not only something to test.
8. **Investigate open questions** against the code. Resolve what the code settles. Tag the rest
   `(partial: what was found)` or `(needs human input)`. Never guess.
9. **Evaluate the catalog as a whole.** Which focuses produced nothing, and is that because the
   SUT has nothing there or because nobody looked? Which properties imply others? Which are too
   vague to fail?
10. **Put the properties to a person.** You can propose a property; you cannot know that its
    owners want it. Turn each property's failure scenario into one question from
    `templates/question.md`: a few concrete steps ending in the state the property forbids, then
    "may the system end up here?". Ask the team that owns the SUT about a guarantee, and the team
    that owns the dependency about an assumption. Ask few questions: high priority first, and
    none about a property the code already asserts (step 2). A property is *proposed* (its
    `Confirmed` field is `no`) until someone has answered.

### Scale the artifacts to the SUT

For a component of a few hundred lines, keep each evidence file to its fields, a line or two
each, and write an investigation log only for a property with open questions or a long code
path. Record a focus that yields nothing in one line, with the reason.

### Guidance

- Prefer a specific guarantee ("an acknowledged write is never lost") to a goal ("test failover").
- Concentrate on timing, concurrency and partial failure. Those are the cases examples miss.
- A property found independently under two focuses is more likely to be real. A property found
  under only one is the reason to run them separately; do not drop it without cause.
- When a property needs internal state to be judged, say where in the SUT an assertion would have
  to sit. A check that only the workload can see may miss it.
- Mark a property invalidated, with the reason, when investigation shows it is wrong. Keep it in
  the catalog so nobody rediscovers it, and give the workload a `Sometimes` assertion for the
  state it wrongly forbade: other code may assume that state never occurs.

### Property discovery

Look at the same code with one attention focus at a time. Each focus finds properties the others
miss, so
treat each pass as a fresh examination and resist skipping one because an earlier pass "covered
that area". If sub-agents are available, run one per focus in parallel and merge; otherwise work
through the list in order. The wildcard always runs last.

#### Attention focuses

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

#### For each property found

Record, in the format of `templates/property.md`:

- the sentence, and the invariant or condition it checks
- the assertion type and why it fits (`refs/terminology.md`)
- the code paths examined, with file and line
- the scenario in which it would fail
- open questions, each with why it matters and what the answer would change

#### Merging

- **Deduplicate.** Note which focuses found each property.
- **Resolve disagreements** about assertion type or priority, and record the reasoning.
- **Write relationships.** Group properties that share a code path or a failure mechanism, and
  note where one implies another.

### Validating claims

Sources outside the code tell you things about the system. They are leads, not facts. A claim
earns a place in the analysis only when you have evidence that *exhibits* the behaviour (the code,
a log, a reproduction), not merely a source that *asserts* it.

Validate what you build on, not everything you read. The moment a claim needs validation is the
moment you would state it as something the system does, or turn it into a property.

#### Two kinds of input

**Claimed guarantees.** The system's own docs, design notes and comments stating intended
behaviour ("failed messages are retried"). Turn each into a property and let the workload test it.
The one discipline: do not write that the guarantee *holds*. Write that the system claims it and
that the property checks it. Docs drift, and comments describe the code someone meant to write.

**Reports of defects.** A ticket, an incident write-up, a message in a chat channel. One person's
account of their own problem, and the reporter is often wrong about the cause. It becomes a
property only after you have read the primary evidence (the logs, the reproduction, the mechanism
in the code, the fix) and ruled out the ordinary alternatives: configuration, environment,
misunderstanding. Ground the property in the mechanism you found, not in the report's wording.

#### What validation requires

1. **Name the competing explanation before you look.** For a reported bug it is nearly always
   "this was the reporter's environment or configuration, not the system".
2. **Read the evidence that tells the two apart**, past the title and first paragraph.
3. **Record the detail that settles it.** "The ticket says messages were lost" cites the claim.
   "The consumer's log shows the handler raising and the offset advancing in the same second"
   discriminates. If you cannot quote the discriminating detail, the claim is not validated.

If you cannot settle it, the claim does not become a property or a stated behaviour. Record it as
an open question tagged `(needs human input)`.

#### The same standard applies to people

An owner's statement about their own service is stronger evidence than a doc, and still a lead.
Where an owner's answer and the code disagree, record both and say which you observed.

### Guarantees and assumptions

Two kinds of statement come out of research, and they need different handling.

| | A guarantee | An assumption |
|---|---|---|
| What it is | something the SUT's own code must ensure | something the SUT relies on a dependency to do |
| Example | "each report is posted at most once" | "a job that was taken is not handed out again" |
| What you do | enforce it, and check it with the workload | detect when it is false, or stop relying on it |

Incidents that surprise a team usually sit in the second column, in an assumption nobody wrote
down. So write them down.

#### Finding assumptions

For each dependency the SUT calls or receives from, ask of the SUT's code:

- **Delivery.** Does it assume every message arrives? Exactly once? In order? Within some time?
- **Effect.** When it asks for something to be done, does it assume the thing is done as asked,
  immediately, and with nothing else done alongside?
- **Reads.** Does it assume a read reflects the latest write? That the state has not moved between
  a read and the write that depends on it?
- **Failure.** When a call fails or times out, does it assume the call had no effect? That it will
  be retried by someone?
- **Versions.** Does it assume every consumer of what it writes understands it?

Each "yes" is a row in the register.

#### The register

Write `assumptions.md` from `templates/assumption-register.md`. One row per assumption: the
statement, the evidence that the SUT relies on it (file and line), what is known about whether the
dependency really behaves that way, how its being false would be noticed, who confirmed it, and
when. A row with no confirmation is marked unverified, and stays that way until someone checks.

#### What each row feeds

- **The fake** of that dependency must be able to violate the assumption, or the workload will
  never test what happens when it is false ("Fakes").
- **The workload** gets an action for each way the assumption can fail ("Faults").
- **The audit** gets a check that finds, in stored data, the traces a false assumption leaves
  (`modules/audit.md`).

### Done when

- [ ] `sut-analysis.md` covers state, writers, concurrency, inputs, dependencies and failure-prone areas.
- [ ] Every property is one sentence, has a slug, an assertion type with a reason, and a priority.
- [ ] Every property has an evidence file naming code paths and the failure scenario.
- [ ] No sentence in any artifact says a guarantee holds.
- [ ] Guarantees and assumptions are in separate lists.
- [ ] Open questions are visible in the catalog, not buried in evidence files.
- [ ] Every confirmed property names who answered, when, and the question asked, and that
      question's scenario ends in a violation of the property, so "yes, that may happen" was a
      possible answer.
- [ ] Each claim taken from a doc or a report cites the detail that validates it.

## Fakes

**Use when:** a dependency cannot run where the workload runs, and the in-process run mode needs
something in its place.
**Emits:** the fake, and `fakes/{dependency}.md` recording the evidence for each behaviour and how
the fake was verified.

A fake is a working in-memory implementation of a dependency. A workload's verdict is only as
good as its fakes: the same driver and the same property can pass against a fake that does what
you assumed and fail against one that does what the real service does. Treat a fake as a claim
about someone else's system, and hold it to the evidence standard in
"Validating claims".

### What a fake must do

- **Implement the operations the SUT uses**, with real behaviour (state, return values, errors),
  not canned answers.
- **Be able to misbehave on request.** For every row in `assumptions.md` about this dependency,
  the fake needs a switch the driver can use to make the assumption false: deliver late, twice or
  out of order; fail a call; apply a request later than it was made; return a stale read.
- **Use the whole contract.** A dependency usually does better than it promises: it answers at
  once, never returns empty, applies requests in the order they were made. The SUT comes to rely
  on that. For each operation, list what the contract allows and the service rarely does, and
  give the fake a switch for each. The driver draws these with a low probability in every test
  case, not only when a fault is being injected. (FoundationDB does this inside its own code
  with `BUGGIFY`.)
- **Take all its choices from the driver.** No clock, randomness or threads of its own.
- **Stay small.** If a fake needs more than a few dozen lines per operation, it is modelling more
  than the SUT depends on.

### Three passes

**1. Propose, with evidence.** For each operation, write down what the real dependency does:
normally, on failure, on repeat, and when its inputs changed between request and effect. Sources,
strongest first: recorded requests and responses; logs; the dependency's source at the *deployed*
version; behaviour observed in a test environment; its docs. Every behaviour cites one. Pay most
attention to a deferred operation that is applied from the state at the time it runs, not the
state at the time it was requested: that is where a fake most often tells a kinder story than
the service.

**2. Confirm with the owners, by scenario.** Do not hand over the evidence file and ask for a
review. Where the evidence leaves more than one behaviour plausible for an operation, build each
as a variant of the fake, run the workload against every variant, and keep each minimal
counterexample that passes on one and fails on another. Those steps are a question. Variants the
workload cannot tell apart need no question yet; note them. If a test environment can be
reached, run the steps there first. Send the owning team only what is still open, one
`templates/question.md` per counterexample: the steps, and a yes or no question about the end
state. Record the variants, their verdicts and the answers in `fakes/{dependency}.md`. Until a
question is answered, report the workload's verdict for every variant, not only the one that
passes. An answer is stronger than a doc and still a lead; where an answer and the observed
behaviour differ, record both.

**3. Verify mechanically.** Send the same inputs to the fake and to the real dependency, and
compare the answers. A small set of such checks, run against both, is a contract test, and a fake
that passes it is a verified fake. Where the real dependency cannot be called, replay recorded
traffic against the fake instead. Record what was compared and what could not be.

### Where recorded behaviour is found

- the broker's own topics or queues, within their retention
- the version history of stores that keep one
- request logs and traces (often without bodies)
- a recording proxy in front of the dependency in a test environment
- past incidents: write-ups, tickets, chat channels, fix and revert commits

Production payloads may be sensitive. Prefer a test environment, or strip the data first.

### Done when

- [ ] Every behaviour of the fake cites evidence, or is listed as unverified.
- [ ] Every assumption about this dependency can be made false by the driver.
- [ ] Every switch has a `Sometimes` assertion, and each fired in the baseline run.
- [ ] Every question sent to the owners is a scenario on which two variants of the fake gave
      different verdicts, and both verdicts are recorded with it.
- [ ] The fake was compared with the real dependency or with recordings, and the result is recorded.
- [ ] The evidence file says what the fake does *not* model.

## Workload

**Use when:** you are building or extending the thing that exercises the SUT.
**Emits:** the driver, its model, and its assertions, in the target repository's test tree;
`run-record.md` and `fault-inventory.md` in the scratchbook.

A workload is everything added to exercise the SUT. Its centre is the **driver**: one program that
picks actions at random, sends them to the SUT, and records each outcome in a **model** of what
the SUT should now contain. Every random choice comes from the testing library, so a failure can
be replayed and shrunk.

### Steps

1. **Map what the workload must reach.** List the SUT's whole surface from the code that receives
   inputs: every operation, every input that sends a handler down a different branch, background
   work, configuration that changes behaviour, and what the real clients send, including their
   retries. For each item, name the action that exercises it or say why it is out of scope.
2. **Pick the run mode** ("Orient"):
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
8. **Hand failures to "Triage".**

### Rules

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

### The in-process run mode

The SUT's code is called directly from the driver, in the driver's process, with every dependency
replaced by a fake. This is the run mode with exact replay: one seed fixes every choice.

#### Pure functions

If the code under test has no state, skip the state machine. Write one property: generate the
inputs, call the function, assert the law. Good first laws: a round trip returns the original; an
invariant of the output holds for every input; two implementations agree; the function does not
crash. An existing example test with its inputs generated is a legitimate first property.

#### The seam

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

#### The state machine

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

#### Properties as plain functions

Write each safety property as a function from the stores (and the model, if needed) to a failure.
The same function then serves the workload, the mutation run and the audit of stored data. A
property that needs history ("this never changes") needs memory in the driver; one that reads only
the current state can also run against production.

#### Replay

Every failure prints the minimal counterexample and a replay token. Keep the token with the
finding. A fix is not done until the token passes and a fresh run does too.

#### What this mode does not show

One process and, unless the library's concurrent mode is used, one action at a time. A fake can be
wrong. Nothing here exercises the real network, the real stores or the real scheduler.

### Faults

A fault is a disruption injected on purpose. In a workload each one is an action the driver may
choose, so its timing is explored like any other input and a failure can be replayed.

#### The inventory

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

#### Rules

- **A fault needs a precondition that makes it meaningful.** An action that can always run and
  usually changes nothing soaks up test cases. Advancing time is the usual offender.
- **A crash is not an exception the SUT can catch.** Model it so that no handler in the code under
  test intercepts it, keep whatever was written before it, and run the SUT's recovery on restart.
- **Decide which properties must survive a fault at every instant**, and which may be false until
  recovery finishes. Write the second kind so they are checked only when the SUT is up.
- **A fault has taken effect when the SUT or a fake behaved differently because of it.** A rule
  that changes only the driver's own bookkeeping has injected nothing, however often it ran.
- **Count what happened.** Record, per test case, how often each fault actually took effect and
  how often the operation finished first. A fault rule that never takes effect is a `Sometimes`
  failure.
- **A timeout is not a failure of the effect.** After a timed-out call the effect may or may not
  have happened. Both must be acceptable to the model until evidence settles it.

#### Two writes

When an operation writes to two places, a crash between them leaves one of two bad states,
whichever order the writes are in. Find which property must hold at every instant, write that
side first, and make the second write a step that is safe to repeat and is repeated by recovery.
Where the second place can be computed from the first, compute it instead: then there is nothing
to leave half done.

### Done when

- [ ] Every item of the surface is exercised by an action or listed as out of scope with a reason.
- [ ] Every property in the catalog has an assertion, or a note saying why it cannot be checked here.
- [ ] `fault-inventory.md` is filled in: every row is an action of the driver that took effect, is not applicable, or is listed as not tried with a reason. Delivery faults alone are not enough: include a failing dependency and a crash mid-operation.
- [ ] `Sometimes` and `Reachable` assertions cover the states the workload exists to reach, and they fire.
- [ ] A failure prints a minimal counterexample and a replay token.
- [ ] The run's generation statistics have been read and are reported with the result.

## Triage

**Use when:** a run failed.
**Emits:** `findings/{id}.md`, one per distinct failure, in the form of `templates/finding.md`.

### Steps

1. **Replay it.** Use the replay token or seed. If it does not reproduce, say so, and record
   everything from the one occurrence you have.
2. **Read the minimal counterexample as a story.** Step by step, in plain words: who did what, and
   what the stores say at the end. If you cannot tell the story, shrink further by hand: remove a
   step, replay, keep the removal if it still fails.
3. **Classify the cause.** If the property that failed is still proposed, stop here: its
   counterexample goes to its owners as a question (`templates/question.md`), and the failure is
   classified once they have answered. Otherwise, one of:
   - *SUT defect*: the code violates a property that is right.
   - *False assumption*: a dependency does something the SUT relies on it not to do. The SUT's
     code may be exactly as written; the defect is in the dependency, or in relying on it. Record
     it against the row in `assumptions.md`, and say whether the SUT can defend itself.
   - *Unfaithful fake*: the fake does something the real dependency does not. Check against the
     fake's evidence (`fakes/{dependency}.md`) before blaming the SUT.
   - *Wrong property*: the property forbids something the system is meant to allow.
   - *Workload defect*: the driver or model is wrong.
4. **Find the mechanism.** Name the line or the interleaving. A finding is not done at "it fails".
5. **Check for siblings.** Would the same mechanism break another property, or another caller?
6. **Propose the fix and its kind**: a guard in code, or a change of design that makes the bad
   state unrepresentable. For a SUT defect, read `modules/fix-by-design.md` before settling on a guard.
   Say which, and what each would cost.
7. **Keep the counterexample as a regression test**, with its replay token.

### A finding contains

The property violated, in its one sentence, and its slug. What found it (the workload, a mutant,
the audit or a model check), and in which run mode. Whether it reproduces on replay, and the token
and command that replay it. The minimal counterexample, verbatim. The story. The cause and its
class. The fix. What was not investigated.

### Notes

- Shrinking is a search. A counterexample with steps that change nothing is common; say so, and
  do not present it as minimal.
- Several failures from one run are often one cause seen through different properties. Group them.
- A failure that will not replay in a deployed run is still a finding. Try to reduce it to an
  in-process reproduction, where it can be replayed.

## Mutation testing

**Use when:** you need to know whether the properties would catch a bug.
**Emits:** `mutation-report.md` (`templates/mutation-report.md`).

A workload that has never failed has shown nothing yet. Mutation testing breaks the SUT on
purpose, one small change at a time, and checks that the property meant to guard that behaviour
fails. A mutant is *killed* if it does and *survived* if every check still passes.

Only safety properties are mutated: those checked with `Always`, `AlwaysOrUnreachable` and
`Unreachable`. Properties checked with `Sometimes` and `Reachable` are validated by the baseline
run instead: those assertions must fire on the unmutated SUT.

### Before starting

Run the workload on the unmutated SUT and record the baseline: which properties pass, and that
the `Sometimes` and `Reachable` assertions fire.

A property that already fails on the baseline cannot be mutated: its counterexample is the
evidence that it can fail. Mutate only the properties that pass. If the user has agreed to fixes,
fix the defects first and take the baseline again; if not, say which properties were left out and
why. Apply mutants to a copy of the SUT, never to the working tree.

### Designing a mutant

One mutant per safety property. Read the property's evidence file first: the code paths and the
failure scenario recorded there are where a good mutant comes from.

- **A realistic mistake.** A dropped guard, `>` where `>=` belonged, an off-by-one, a check moved
  outside a lock, an error swallowed instead of propagated, two writes reordered. Not vandalism.
- **Subtle.** It should need a specific state to show. A mutant that breaks every request proves
  the assertion exists, not that the workload can find the interesting case.
- **In the code that maintains the invariant**, not in the code that checks it. Mutating the check
  disables the reporting along with the behaviour.
- **Not fatal.** It must not crash the SUT at startup or hang it.
- **With a marker.** Add a signal at the point of divergence (a log line or a `Reachable` assertion
  carrying the mutant's id), placed where the mutated branch is actually taken, so you can tell
  whether the broken code ran.

Research several candidates per property, apply the strongest, and record the rejected ones with
reasons.

### The verdict ladder

For each mutant, in this order:

1. **Did it build and start?** If not, fix the mutant.
2. **Did the marker fire?** If not, the workload never reached the mutated code. The finding is
   about the workload: go to `modules/review-inputs.md`.
3. **Did the target property fail?** If so: killed. Record the minimal counterexample.
4. **Did some other property fail instead?** Record it as collateral. The target property is still
   not shown to work.
5. **Nothing failed, and the marker fired:** survived. The property is too weak, or missing. Find
   what the mutant changes that no property observes, and repair the property.

### After a design fix

When a defect was fixed by redesigning the data (`modules/fix-by-design.md`), run the
same mutants against the new design and sort them:

- **Stillborn**: the mutant no longer compiles. The property it targeted is enforced by
  construction; its assertion can be retired or kept as a cheap backstop.
- **Killed**: the mutant compiles and the property fails. The types did not take this property
  over, and the workload is still needed for it.
- **Survived**: the mutant compiles and nothing fails. Neither the types nor the properties
  guard this behaviour.

Report the three lists. They are the evidence for which properties the redesign made redundant.

### Do not game it

- Never coarsen a mutant into obvious breakage to get it killed. Fix the workload or the property.
- Never write two mutants for one property "to be sure". Pick the strongest.
- A mutant whose wrong value is recomputed or clamped back before anything observes it is an
  equivalent mutant. Record it as such and design another.
- Zero survivors is a statement about the mutants you wrote, not about the properties.

### Done when

- [ ] The baseline is recorded, with its `Sometimes` and `Reachable` assertions firing.
- [ ] Every safety property in the catalog has one mutant, or a note saying why it cannot be mutated.
- [ ] Every verdict is one of the template's, which are the rungs of the ladder.
- [ ] Every survivor led to a repaired property, a repaired workload, or an open question.
- [ ] No mutant reached the working tree: every one was applied to a copy.

## Other files

Read each when the task reaches it. The first two add to "Workload" above; they do not replace it.

| File | Read it when | Emits |
|---|---|---|
| `modules/workload-deployed.md` | the run mode is a deployed SUT with the driver alongside | the same as "Workload" |
| `modules/workload-ui.md` | the run mode is a web or terminal interface | a Bombadil specification |
| `modules/fix-by-design.md` | a finding is a SUT defect and a fix is being chosen between a guard and a redesign of the data | the "Fix" section of the finding |
| `modules/audit.md` | you can read production stores or logs | `audit-report.md` |
| `modules/model-checking.md` | the question is whether a design or a proposed fix is sound | a specification and its checked result |
| `modules/review-inputs.md` | a workload passes and you doubt what it explored. A brief for a fresh agent | `workload-review.md` |
| `modules/review.md` | the work is about to be reported as done. A brief for a fresh agent | `review.md` |
| `refs/terminology.md`, `refs/tools.md`, `refs/anti-patterns.md`, `refs/sources.md` | a term, a library's API, or a source is needed | |
| `templates/` | an artifact with a fixed form is written | |

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
