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
3. **Discover properties**, one attention focus at a time. Follow `property-discovery.md`.
4. **Separate guarantees from assumptions.** Follow `assumptions.md`.
5. **Validate anything taken from outside the code.** Follow `validating-claims.md`.
6. **Write the catalog and the evidence files** from `templates/property.md`. Give each property a
   kebab-case slug, one sentence, an assertion type with the reason for it, a priority, and its
   open questions.
7. **Classify each property's enforceability**: by the data type alone, by an abstract type with
   a smart constructor, or not by types at all (the table in `modules/triage/fix-by-design.md`).
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
    none about a property the code already asserts (step 2). A property stays `proposed` until
    someone has answered.

## Scale the artifacts to the SUT

For a component of a few hundred lines, put the evidence in the catalog entry and write a separate
evidence file only for a property with open questions or a long code path. Record a focus that
yields nothing in one line, with the reason. The full set of files is for a system too large to
hold in mind.

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
