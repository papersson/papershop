---
name: elicit
description: Do a task the way a leading practitioner of its domains would, without being told what they would care about. Write a short brief before the work (purpose, audience and the effect wanted, a map of the domains the result depends on plus the fields best at that effect, their standards and best works, unstated requirements, a pre-mortem, the best version, the few items that matter, cuts of scope but not craft, yes/no acceptance checks) and the verifier prompts, both as files before the work; then either stop and show the elicited prompt, or do the work against it and run fresh verifier subagents from those files to check it achieved its purpose and its effect. Use when asked to "elicit", "do this like an expert would", "bring your full ability", or for any substantial task whose quality depends on craft or domain knowledge the request does not spell out. Not for one-line fixes, lookups, or work a project skill already covers in depth; use that skill.
---

<!-- Written by AI on 2026.10.21 by model claude opus 5.5. Why each part is there: DESIGN.md; the evidence: references/sources.md. -->

# Elicit

A capable model usually knows what a leading practitioner would do here. It fails to do it for
four reasons: it works in one pass with no standard in view; it answers only the question asked
instead of the questions an expert raises unprompted; when it reviews, it checks what is easy to
check (does it run, is it coherent) instead of what the work is for; and it aims at avoiding
mistakes rather than at the best version, so it ships work that is correct and plain. Generic
fixes do not help: "act as an expert" measurably adds nothing or harms, and "double-check your
work" without criteria rarely finds the error. What helps is the content of an expert's attention,
both what they guard against and what they reach for, written down before the work, and a check
against it by someone who did not do the work.

## Two modes

Decide which case you are in.

- The user gave a prompt or task to improve and has not started it. Write the brief and the
  verifier prompts (sections 1 and 2), show the brief, and stop. It is the elicited version of
  their prompt; they may edit it, approve it, or keep it for later.
- The user wants the task done. Write the brief and the verifier prompts, then do the work
  (section 3) and run the verifiers (section 4). For a task of days, show the brief and wait for
  approval before the work.

Writing the verifier prompts before the work is the point: what they check is fixed before the
work exists, so the work cannot shape it.

## Size it to the task

- Minutes: think through steps 1 to 9 in a few lines, no files, no verifiers.
- An hour or more: the files below, one or two verifiers.
- Days: full brief, a verifier per kept domain, and the user approves the brief.

## Where the files go

One folder per task in the session scratchpad (from the system prompt; if none is listed, the
system temp directory): `<scratchpad>/elicit/<task-slug>/`.

```
brief.md            the elicited prompt: the original request, then steps 1 to 9
verifiers/<lens>.md one complete prompt per verifier (section 2)
checks/             executable checks written before the work: scripts, tests, measurements
```

Nothing goes elsewhere unless the user asks. In a code project, a check worth keeping becomes a
real test in the repo as part of the work, not a file left in the scratchpad.

## 1. Write the brief, before any work

Write it to `brief.md`. One page. Each step is short.

1. Purpose, audience and effect. Who uses the result, for what, in what situation, and the
   effect it should have on them: understood, persuaded, trusted, delighted, kept safe. Be
   specific: "a site lead reading it on a phone at 6am before the crew arrives", not "users".
   Taste words in the request ("cool", "fun", "beautiful", "feels right") name the effect to
   pursue, not a preference to leave to the user.
2. Domain map. Every field that could matter to the result, especially the ones the request does
   not name. List generously: a missed domain is the commoner failure, and listing one costs a
   line. A lesson plan depends on the subject, on how children learn to read and on the learners'
   needs; a login form depends on security and accessibility; an invoice depends on bookkeeping.
   Rank by how much each moves the effect from step 1, not by how obvious it is, and keep the top
   three or four for depth; the rest stay on the map for step 7. Then name one or two fields
   outside these that are best at producing the effect from step 1, and what you would borrow
   from them: a report can borrow a newspaper editor's inverted pyramid, a checkout flow a
   retailer's queue design, a lesson a stage magician's control of attention.
3. Standards and exemplars. For each kept domain, what the field itself treats as authoritative,
   by name: a standard (OWASP ASVS, WCAG 2.2, the AP Stylebook), a canonical work (Tufte's The
   Visual Display of Quantitative Information), a method (threat modelling, a pre-registered
   analysis). Name only what you are sure exists; a verifier will check. Where a field has no
   formal standard, its best works are the standard: name one or two exemplars, say what makes
   them land, and write your own rubric from that. Taste is never handed to the user unexamined.
4. Unstated requirements. List the questions a practitioner would ask before starting and answer
   each from the context. Ask the user only where two plausible answers lead to materially
   different work; otherwise write the assumption down.
5. Pre-mortem. A leading practitioner reviews the finished work and calls it amateur. Write the
   five most likely reasons.
6. The best version. The same practitioner sees the finished work and is impressed, or the
   audience stops and shows it to someone. Write what they saw: three to five qualities beyond
   correctness that make it exceptional for this audience, using what you borrowed in step 2 and
   the exemplars in step 3.
7. The few items. From steps 3 to 6, keep the items that are critical and commonly missed, and
   the items that make it exceptional. This is the checklist. It carries at least as many items
   from step 6 as from step 5: the floor items are often quick and checkable, so the ceiling items
   are where the effort goes. Every listed domain not kept for depth adds its single most critical
   floor item, so no domain on the map goes unchecked (for a report whose statistics were not kept
   for depth: "every number traces to its source"). Choosing these few is most of what an expert
   contributes.
8. Cuts. Name what you will deliberately not add, though an eager agent might. Cut scope (topics,
   features, formats, variants), never craft on the main moments: fewer things, each done fully.
   Every addition must make the result better for the audience in step 1.
9. Acceptance checks. For each item, a yes/no check. Use the highest rung available: executable
   (a test, a script, a measurement, an exploit, a render you inspect), then instrumented (a
   screenshot, a frame grab, a recording), then a rubric line a stranger could apply. Ceiling
   items get checks too, as rubric lines drawn from the exemplars ("a stranger can restate the
   main point after one read"); an item without a check quietly drops out. Pair each hardening
   check with a functional one so the hardening does not break the feature.

## 2. Write the verifier prompts, before any work

One file per verifier in `verifiers/`. Each verifier must earn its cost: at most one per kept
domain, none for small tasks. Pick lenses from: the audience, the master of the top domain, an
adversary (what breaks, what is wrong), the maintainer. Do not spend every verifier on what is
easy to check; executable checks largely check themselves. When step 1 names an effect, one
verifier is the audience judging that effect.

A verifier is a fresh subagent that sees nothing of this conversation, so each file is a complete
prompt on its own. It contains:

- its lens, and the brief's purpose, audience, effect, standards and exemplars;
- what an excellent result contains for this lens, written now, before the work exists;
- its checklist items, with the commands for any executable checks in `checks/`;
- when it runs: at a cheap stage (a script before a render, a schema before a migration) or on
  the finished work;
- its instructions: judge whether the work achieves its purpose and its effect, not only whether
  it runs or holds together; go through the items one by one, run the executable checks itself,
  and cite evidence for every finding (command and output, a frame, a line); report findings
  with severity and do not fix them; the effect verifier also says what would raise the work
  toward the step 6 version;
- `{{ARTIFACT}}`, where the paths to the work are filled in at run time.

It does not contain your reasoning or who will make the work.

## 3. Do the work against the brief

Keep the brief in front of you while working and run the cheap checks as you go. Spend the effort
where the step 6 items live; the verifiers judge more than the checklist, so meet the purpose,
not only the letter of the items. When you find yourself arguing an item away, or a new
instruction collides with one, stop and say so instead of dropping it quietly.

## 4. Run the verifiers

At each verifier's stage, spawn a fresh subagent (not a fork) whose prompt is its file verbatim,
with `{{ARTIFACT}}` replaced by the paths to the work. Use a different model when one is
available. Do not edit a verifier's file after the work has started; if it turns out wrong, say so
in the report.

Fix what is confirmed and re-run the checks that failed. Two rounds at most; anything still open
is reported as open, never as passed.

## 5. Report

Which checks passed and on what evidence, how the work meets the step 6 qualities and where it
falls short of them, what is open, the assumptions you made, and what you cut.
