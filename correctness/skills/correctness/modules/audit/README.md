# Audit

**Use when:** you can read production stores, or logs.
**Emits:** `audit-report.md`.

A workload checks the states its generators can build. An audit checks the one state production
actually reached, which may be one no generator would produce: data from old versions of the code,
bulk imports, manual repairs, bugs fixed long ago. It is read-only, needs no seam and no harness,
and is often the cheapest first step on an existing system.

## Steps

1. **Pick the properties a snapshot can express.** A property that reads only current state can be
   audited as it stands. One that says "never changes" needs history: use logs or an append-only
   record if there is one, and say so if there is not.
2. **Rewrite what depends on things you cannot see.** In a test, "this item is still on its way"
   is answered by looking in a queue. In production the queue belongs to someone else, so ask the
   clock instead: an item that has waited far longer than normal is treated as lost. That needs a
   threshold. State it, and state that it can be wrong in both directions.
3. **Write each check as a query or a function over the stores** that returns violations, and run
   it read-only. Collect every violation; do not stop at the first.
4. **Classify every finding.** One of: a defect still present; damage left by a defect since fixed
   (fixing code does not repair data); legitimate data the property did not anticipate, such as
   records that predate a process; a wrong property.
5. **Say what should happen to each class**: a fix, a backfill or migration, an explicit exception
   written into the property, or a corrected property. A check that is left to complain forever
   will be ignored.

## Rules

- Read-only, always. Sample first, on a copy or replica where there is one.
- Stored data may be sensitive. Report counts and identifiers, not contents, unless told otherwise.
- An audit says nothing about states production has not reached. That remains the workload's job.

## Done when

- [ ] Each audited property is stated in one sentence, with the query or function that checks it.
- [ ] Every finding is classified, with the evidence for the class.
- [ ] Properties that could not be audited are listed, with what would make them auditable.
- [ ] Thresholds are stated, with the reason for each value.
