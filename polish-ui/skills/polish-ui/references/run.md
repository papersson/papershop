# The hill-climbing loop

Read the run's brief and state and acquire run ownership before editing. The worker is the sole
writer in the designated working copy. The reviewer judges evidence; it does not implement changes. Use the runtime
reference supplied by the launcher for workspace, lifecycle, and recovery details.

## See the product

Actually open the baseline screenshots as images. Read the components and shared tokens behind
them. Exercise the primary user task and relevant interaction states using disposable test data
for mutations, as required by the runtime reference. Choose a small set that
exposes the likely consequences of a change: for example, a populated screen and its empty state,
a narrow layout, and a dialog or keyboard focus state. Add coverage when a shared token affects
other screens; the initial capture set is not permission to ignore those effects.

Save a capture manifest with image paths, source checkpoint, screen/route, viewport or device,
theme, content fixture, and interaction state. Wait for fonts, assets, and the intended rendered
revision. Keep content and capture conditions stable across comparisons. An image of the wrong
server or state invalidates the comparison.

Inspect the interface at its actual working size. Zoomed crops help diagnose a detail but cannot
establish that the whole screen works. Use both when useful. Do not claim keyboard, screen-reader,
motion, or timing behavior from a still screenshot.

## Evaluate this product

Read [rubric.md](rubric.md) and [evaluation.md](evaluation.md). Freeze the brief's evaluation
profile: task and taste, priorities among the six qualities, required content/behavior, scoped
gates and baseline debt. Use the six qualities to find opportunities and check regressions:
clarity, composition, typography, coherence, interaction feedback, and character. Preserve useful
content and meaningful differences. Clean can involve subtraction, but never optimize element
count or whitespace quantity. Density and expressiveness must fit the actual product.

Record measurable assertions separately from proxies, model judgments and human evidence. Check
baseline interactions and applicable constraints; unavailable evidence is unknown, not pass.
Keep a small reserve of relevant states/content for final validation if feasible. Do not call
cases unseen after using them to tune a candidate. Prefer existing components and tokens; feature
work, brand changes and broad restructuring need their own scope.

## Make one convincing improvement at a time

1. **Select.** Maintain a ranked queue of opportunities across the six qualities and in-scope
   screens/states. Rank by expected user benefit, confidence, cost and blast radius; prioritize
   unresolved weaknesses over already-strong details. Choose a
   focused hypothesis: what visible or usable relationship will improve, where, and why? Record
   it before implementation. Do not spend a round on a change you cannot meaningfully evaluate.
2. **Checkpoint.** Confirm the best accepted version is restorable, including new/deleted files.
   Record the candidate's touched paths. Never restore whole source-repository files over the
   user's concurrent work. Keep any checkpoint commits local to the isolated run.
3. **Implement.** Make the smallest cohesive change that can test the hypothesis. Run cheap applicable gates first and reproduce important interactions, including relevant
   edge states. Record inherited debt separately from new/worsened failures. Resolve failures or reject the candidate
   before beginning unrelated improvements.
4. **Capture.** Render the same states at the same dimensions and content. Save immutable
   candidate images and the exact source checkpoint. If capture conditions changed, recapture
   both sides or call the comparison inconclusive.
5. **Review.** Ask a fresh `polish-ui:reviewer` to compare the best accepted version with the
   candidate. Give it the product, taste, and constraints from the brief, a neutral matched capture
   manifest, actual images, recorded gate/interaction evidence, rubric path and evaluation profile. Keep operational checkpoint history
   and the candidate mapping out of that handoff. Label the image sets A and B; vary which side
   contains the candidate. Keep the mapping in the worker's log. Omit the implementation pitch, prior verdicts, and
   desired score. Retain enough product context for a useful judgment. Supply a separate copy
   of the original baseline for an explicit cumulative drift check when best has diverged.
6. **Decide.** Apply the evaluation protocol: concrete benefit in agreed priorities, applicable
   gates passed with explicitly scoped inherited-debt exceptions, no unresolved material
   regression or forbidden drift, and holistic quality at least as good. In the default
   uncalibrated pilot, obtain a second fresh review with A/B order swapped for every proposed
   acceptance. Neither reviewer sees the other's verdict. Disagreement, tie or essential unknown
   retains best; do not shop for a favorable verdict. A justified minor tradeoff must be explicit.
   A numerical rating alone never accepts a change. A revision after review is another candidate
   within the budget, not an uncounted repair. Do not edit a candidate after its review and reuse
   the verdict as if it covered the changed source.
7. **Record.** Save reviews, private A/B mapping and acceptance decision with source/image identities,
   evidence paths, check methods/coverage, rubric/profile version and known runtime/model settings.
   Checkpoint an accepted version. Restore a rejected candidate to the exact previous best,
   including removal of files created only by that candidate, and verify the restoration before
   continuing. Mark the round attempted even when the candidate failed. Update `state.md` and
   the opportunity queue. After an acceptance, re-evaluate the remaining weaknesses and continue
   while worthwhile, testable hypotheses fit the remaining budget. Ratings can stay unchanged
   while a detail improves; neither a 3 nor a 4 ends the run by itself.

The reviewer needs only the brief and immutable evidence, so it may work while the worker performs
independent checks. Do not edit or overwrite the reviewed candidate during that review, or start
another candidate before the decision. Keep the original baseline and best accepted snapshots
separate: the latest version is not automatically the best.

## Continue until the budget or a supported plateau

Check the deadline and any round/cost cap before each candidate, review and repair. Preserve the
final-verification reserve; do not start a candidate that cannot reasonably finish in the work
window. Bound tool waits and check the clock afterward. An accepted improvement is a checkpoint,
not a reason to end an otherwise productive run.

Two consecutive non-improvements trigger a reassessment, not automatic termination. Reinspect the
current best across the in-scope surfaces and all six qualities, using existing development
evidence first. Consider a different weakness, state or hypothesis instead of nudging the same
property repeatedly. Keep the rubric and taste brief frozen. Do not consume reserved validation
cases to hunt for a win or change scores/thresholds to manufacture progress.

If the reassessment finds a concrete, worthwhile and testable opportunity, continue with it.
Otherwise record a local plateau: what was tried, which dimensions/surfaces were considered, and
why remaining ideas have low expected benefit or unacceptable tradeoffs. If credible opportunities
remain but cannot fit the remaining time or require unavailable tools, classify the stop as budget
or capability limited, not a quality plateau.
Do not claim a global optimum or that every metric is maximized. Reopen a stalled direction only
when new evidence supports a materially different hypothesis; do not cycle through rejected
variants or repeatedly ask the judge for a better verdict. Exploration stays within the budget.

Stop when the budget/cap is reached, the supported reassessment finds no worthwhile next step,
the user stops the run, or a necessary capability is blocked. State which condition applies.
A high score or one successful candidate alone is not a plateau. Do not invent edits or sleep to
consume time; an exhausted hypothesis queue is a valid early finish when supported by evidence.

For runs lasting hours or days, use recoverable work blocks: checkpoint accepted work and update
the queue/coverage after each candidate, and perform a cumulative baseline check at meaningful
milestones such as completing a screen or before a session handoff. Continue across blocks within
the original deadline without requesting a fresh budget each time. Compaction or a supported
session handoff is not completion; persist what the next owner needs. If the runtime cannot
continue, mark the run interrupted/blocked with the last verified best and an exact resume point.
Do not claim the plugin schedules itself or guarantees unattended uptime.

At the deadline or cap, retain the best verified version and roll back an unreviewed candidate.
If restoration or final verification cannot finish, mark the result incomplete and identify the
last verified checkpoint; never label the current tree verified. On resumption, check ownership,
source changes, current tree and remaining original budget before doing anything else.

## Final evidence and handoff

Compare the best version against the original baseline using the frozen intent and representative
states, including reserved validation cases. If a reserved case prompts a repair, mark it as
development evidence and replace it before claiming unseen validation. Obtain a fresh independent final visual review if the final cumulative result has not
already been reviewed against the baseline. Fix or revert material regressions within the budget.
Use the order-check policy for the final comparison; a prior baseline/candidate pair can serve
when source, states and coverage match. If the cumulative result cannot be validated, deliver
the last version that passed the cumulative
check, or the baseline. Check required project commands, relevant interactions, and the final diff.

Write `report.md` in the run directory. Include:

- The visible outcome and a few matched before/after images, with paths to the rest.
- The original intent, accepted changes and their reasons, and any preserved distinctive details.
- The baseline/best checkpoint and the exact diff or working-copy location. Exclude pre-existing
  user changes and run artifacts from the claimed implementation diff.
- The six anchored baseline/final profiles and evidence-backed deltas, without a combined score.
  Distinguish relative improvement, remaining absolute weaknesses and actual human preference.
- Checks actually performed, method, coverage and pass/fail/unknown/NA results. Separate M measured
  observations, P proxies, J model judgments and H human evidence. Disclose inherited debt and
  inaccessible or untested states; do not imply full accessibility conformance from partial checks.
- Rejected ideas worth remembering, the remaining ranked opportunities, dimension/state coverage,
  and evidence for any plateau. Separate “no worthwhile improvement found” from a budget stop.
- Elapsed time, attempted/accepted rounds, stop reason, and
  concrete instructions for viewing or resuming the result.

An unchanged result can be successful if the comparisons failed to justify a change; a blocked
run is not that outcome. Keep reviewer-inferred taste separate from preferences the user actually
expressed. Record feedback in the run's brief for future use; project-wide or cross-project taste
memory requires a separate request. Finish by stopping only this run's preview processes, unless
the user requested a live preview, and preserve the result for review. Do not apply it over a
changed source checkout or merge it automatically.
