# Review

**Use when:** work under this skill is about to be reported as done.
**Emits:** `review.md` in the scratchbook.

This file is a brief for a reviewer who did not do the work. If you are that reviewer, you have
been given this brief, the glossary (`refs/terminology.md`), the checking script, the scratchbook,
the workload and the SUT (the system under test), and nothing of the conversation that produced
them. That is deliberate. The person who built a workload knows what they meant it to
cover and reads that into the artifacts; you can only see what is there.

Your job is to find what was skipped, what was claimed without being shown, and what does not
reproduce. Report it. Change nothing: not the SUT, not the workload, not the scratchbook apart
from adding `review.md`.

## Steps

1. **Form your own expectation first.** Before opening the scratchbook, read the SUT's entry
   points and state for a few minutes and write down the three to five properties you would
   expect, and the faults this SUT is exposed to. Compare once you have read the catalog. A
   property or fault you expected and the work lacks is a finding, or a question if you may be
   wrong.
2. **Run the mechanical check.** `python3 <script> <scratchbook>`, with
   `--require run-record.md --require fault-inventory.md` if a workload exists and
   `--require mutation-report.md` if `run-record.md` puts mutation testing in scope. Copy its
   output into the review verbatim, in a code block. Each failure is a finding.
3. **Rerun.** Run the workload with the command in `run-record.md` and keep the output. Replay
   every finding with the command in its `Replay` field. A finding that does not reproduce, or a
   run whose result differs from the one recorded, is a finding. So is a run record that does
   not let you do either.
4. **Go through the checklist below.** Give every line a verdict: `ok` with what you looked at,
   `finding`, or `not checked` with the reason. A line you did not check is never `ok`.
5. **Write `review.md`.** The script's output, the checklist with verdicts, then the findings,
   numbered, each with where it is, what is wrong, what you ran or read to see it, and what would
   close it. End with what you did not review.

## Checklist

**Faults**

- [ ] Every row of `fault-inventory.md` marked `action` names a rule that exists in the driver,
      and that rule took effect in your own run, not only in the recorded one. Taking effect
      means the SUT or a fake behaved differently because of it.
- [ ] `dependency call fails` and `crash mid-operation` are actions, or are truly not applicable.
      For every row marked `not tried`, the reason given is true of this SUT.
- [ ] Every row marked `not applicable` is right: open the SUT and look for the source it denies.
- [ ] Properties that may be false during recovery are checked again once the SUT is back up.

**Reach**

- [ ] The states the properties are about are asserted with `Sometimes` or `Reachable`, and those
      assertions fired in your run.
- [ ] The generation statistics show actions meeting on the same targets, not spread thin.
- [ ] Nothing is filtered silently: every rejected step is counted, and the counts are small.
- [ ] No generator was narrowed to avoid a known failure.

**Properties**

- [ ] Each property is one sentence stating one law, with the assertion type that matches it.
- [ ] Safety properties are checked after every step, with the library's sampling of invariants
      turned off.
- [ ] No sentence in the scratchbook says a property holds. It says what ran and what was seen.
- [ ] A property nobody confirmed is not reported as a defect when it fails, and is not dropped
      either: its counterexample is a question.

**Evidence**

- [ ] For every high-priority property, open the cited file and line. It shows what the evidence
      file says it shows.
- [ ] Claims taken from docs, comments or bug reports were validated against code, logs or a run,
      or are listed as open questions.
- [ ] Every behaviour of every fake cites evidence. Where the evidence allowed two behaviours,
      both variants exist and the workload ran against both.
- [ ] Every assumption has a fake that can make it false and an action that does so.

**Surface**

- [ ] List the SUT's operations from its code yourself. Each is exercised by an action or is
      listed as out of scope with a reason.
- [ ] Inputs include the malformed, the absent, the boundary and the already-finished.

**Mutation**

- [ ] Each mutant is a mistake a developer could make, placed in the code that maintains the
      invariant, with a marker at the point of divergence.
- [ ] Every survivor led to a repaired property, a repaired workload or an open question.
- [ ] No mutant is in the SUT: the working tree differs from the commit on the `SUT:` line only by
      seams (places where a test can supply a dependency).

**Findings and report**

- [ ] Every finding has a minimal counterexample, a replay that reproduces it, and a cause class.
      One classed as a SUT defect has both a guard and a statement on whether a redesign would
      remove the bad state.
- [ ] The scratchbook says what was not tried and what remains unverified (the fault inventory,
      the open questions, each finding's "Not investigated"), and none of these is empty without
      a reason.
- [ ] Changes to the SUT are limited to seams, or `run-record.md` records that the user agreed to
      more.

## Rules

- **Report, do not repair.** A reviewer who fixes things becomes an author, and the fix goes
  unreviewed.
- **Cite what you ran or read** for every verdict. "Looks fine" is `not checked`.
- **Prefer a rerun to a reading.** A replay token either reproduces or it does not.
- **No summary of strengths.** The review lists what is wrong, what is unknown, and what was not
  looked at.
