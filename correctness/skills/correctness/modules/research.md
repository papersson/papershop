# Research

**Use when:** you need to know what should be true of the SUT before anything is built to test it.
**Emits:** `sut-analysis.md`, `property-catalog.md`, `properties/{slug}.md`, `assumptions.md`.

Research turns a codebase into a list of concrete, checkable properties, each with the evidence
behind it. It does not decide whether the properties hold. That is what the workload is for.

## Scope question first

Ask once, and record the answer verbatim in every artifact's provenance:

> Before I start: are there docs, design notes, related repositories, issue trackers, incident
> write-ups or chat channels outside this directory that I should also consult? "Just this
> directory" is fine.

If nobody can answer (an unattended run), record "not asked: unattended" in the provenance,
work from the directory alone, and list what you would have asked under open questions.

Beyond that, ask only what you cannot infer safely: which component is the SUT, and which known
incidents or failure modes matter most.

## Steps

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

## Scale the artifacts to the SUT

For a component of a few hundred lines, keep each evidence file to its fields, a line or two
each, and write an investigation log only for a property with open questions or a long code
path. Record a focus that yields nothing in one line, with the reason.

## Guidance

- Prefer a specific guarantee ("an acknowledged write is never lost") to a goal ("test failover").
- Concentrate on timing, concurrency and partial failure. Those are the cases examples miss.
- A property found independently under two focuses is more likely to be real. A property found
  under only one is the reason to run them separately; do not drop it without cause.
- When a property needs internal state to be judged, say where in the SUT an assertion would have
  to sit. A check that only the workload can see may miss it.
- Mark a property invalidated, with the reason, when investigation shows it is wrong. Keep it in
  the catalog so nobody rediscovers it, and give the workload a `Sometimes` assertion for the
  state it wrongly forbade: other code may assume that state never occurs.

## Property discovery

Look at the same code with one attention focus at a time. Each focus finds properties the others
miss, so
treat each pass as a fresh examination and resist skipping one because an earlier pass "covered
that area". If sub-agents are available, run one per focus in parallel and merge; otherwise work
through the list in order. The wildcard always runs last.

### Attention focuses

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

### For each property found

Record, in the format of `templates/property.md`:

- the sentence, and the invariant or condition it checks
- the assertion type and why it fits (`refs/terminology.md`)
- the code paths examined, with file and line
- the scenario in which it would fail
- open questions, each with why it matters and what the answer would change

### Merging

- **Deduplicate.** Note which focuses found each property.
- **Resolve disagreements** about assertion type or priority, and record the reasoning.
- **Write relationships.** Group properties that share a code path or a failure mechanism, and
  note where one implies another.

## Validating claims

Sources outside the code tell you things about the system. They are leads, not facts. A claim
earns a place in the analysis only when you have evidence that *exhibits* the behaviour (the code,
a log, a reproduction), not merely a source that *asserts* it.

Validate what you build on, not everything you read. The moment a claim needs validation is the
moment you would state it as something the system does, or turn it into a property.

### Two kinds of input

**Claimed guarantees.** The system's own docs, design notes and comments stating intended
behaviour ("failed messages are retried"). Turn each into a property and let the workload test it.
The one discipline: do not write that the guarantee *holds*. Write that the system claims it and
that the property checks it. Docs drift, and comments describe the code someone meant to write.

**Reports of defects.** A ticket, an incident write-up, a message in a chat channel. One person's
account of their own problem, and the reporter is often wrong about the cause. It becomes a
property only after you have read the primary evidence (the logs, the reproduction, the mechanism
in the code, the fix) and ruled out the ordinary alternatives: configuration, environment,
misunderstanding. Ground the property in the mechanism you found, not in the report's wording.

### What validation requires

1. **Name the competing explanation before you look.** For a reported bug it is nearly always
   "this was the reporter's environment or configuration, not the system".
2. **Read the evidence that tells the two apart**, past the title and first paragraph.
3. **Record the detail that settles it.** "The ticket says messages were lost" cites the claim.
   "The consumer's log shows the handler raising and the offset advancing in the same second"
   discriminates. If you cannot quote the discriminating detail, the claim is not validated.

If you cannot settle it, the claim does not become a property or a stated behaviour. Record it as
an open question tagged `(needs human input)`.

### The same standard applies to people

An owner's statement about their own service is stronger evidence than a doc, and still a lead.
Where an owner's answer and the code disagree, record both and say which you observed.

## Guarantees and assumptions

Two kinds of statement come out of research, and they need different handling.

| | A guarantee | An assumption |
|---|---|---|
| What it is | something the SUT's own code must ensure | something the SUT relies on a dependency to do |
| Example | "each report is posted at most once" | "a job that was taken is not handed out again" |
| What you do | enforce it, and check it with the workload | detect when it is false, or stop relying on it |

Incidents that surprise a team usually sit in the second column, in an assumption nobody wrote
down. So write them down.

### Finding assumptions

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

### The register

Write `assumptions.md` from `templates/assumption-register.md`. One row per assumption: the
statement, the evidence that the SUT relies on it (file and line), what is known about whether the
dependency really behaves that way, how its being false would be noticed, who confirmed it, and
when. A row with no confirmation is marked unverified, and stays that way until someone checks.

### What each row feeds

- **The fake** of that dependency must be able to violate the assumption, or the workload will
  never test what happens when it is false (`modules/fakes.md`).
- **The workload** gets an action for each way the assumption can fail (`modules/workload.md`, "Faults").
- **The audit** gets a check that finds, in stored data, the traces a false assumption leaves
  (`modules/audit.md`).

## Done when

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
