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
   later step should propose a check that is already there.
3. **Discover properties**, one attention focus at a time. Follow `property-discovery.md`.
4. **Separate guarantees from assumptions.** Follow `assumptions.md`.
5. **Validate anything taken from outside the code.** Follow `validating-claims.md`.
6. **Write the catalog and the evidence files** from `templates/property.md`. Give each property a
   kebab-case slug, one sentence, an assertion type with the reason for it, a priority, and its
   open questions.
7. **Investigate open questions** against the code. Resolve what the code settles. Tag the rest
   `(partial: what was found)` or `(needs human input)`. Never guess.
8. **Evaluate the catalog as a whole.** Which focuses produced nothing, and is that because the
   SUT has nothing there or because nobody looked? Which properties imply others? Which are too
   vague to fail?

## Guidance

- Prefer a specific guarantee ("an acknowledged write is never lost") to a goal ("test failover").
- Concentrate on timing, concurrency and partial failure. Those are the cases examples miss.
- A property found independently under two focuses is more likely to be real. A property found
  under only one is the reason to run them separately; do not drop it without cause.
- When a property needs internal state to be judged, say where in the SUT an assertion would have
  to sit. A check that only the workload can see may miss it.
- Mark a property invalidated, with the reason, when investigation shows it is wrong. Keep it in
  the catalog so nobody rediscovers it.

## Done when

- [ ] `sut-analysis.md` covers state, writers, concurrency, inputs, dependencies and failure-prone areas.
- [ ] Every property is one sentence, has a slug, an assertion type with a reason, and a priority.
- [ ] Every property has an evidence file naming code paths and the failure scenario.
- [ ] No sentence in any artifact says a guarantee holds.
- [ ] Guarantees and assumptions are in separate lists.
- [ ] Open questions are visible in the catalog, not buried in evidence files.
- [ ] Each claim taken from a doc or a report cites the detail that validates it.
