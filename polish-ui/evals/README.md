# Forward tests

Structural validation checks packaging, not taste or autonomous execution. Run these cases in
fresh contexts with the installed plugin or `claude --plugin-dir <absolute-plugin-path>`. Use
disposable workspaces, local data, and existing browser tools. Record the runtime/version and
whether the real Claude agents or an equivalent test harness executed each case. Do not claim a
native background test from a foreground simulation.

## A small, real refinement

Create a compact task-list page with a deliberate warm palette, usable controls, and an uneven
text hierarchy or alignment. Initialize Git, then make a relevant uncommitted content change.

Request: “I like this warm, compact task list. Polish the reading hierarchy and alignment.
Preserve the colors, density, content, and behavior. Foreground, at most one candidate round.”

Verify observable outcomes:

- The source checkout and its existing uncommitted change remain intact when isolation is used.
- The baseline contains that change, and the preview is served from the actual working copy.
- Mutating interaction checks use disposable data and cannot affect a shared backend.
- The worker opens rendered images, changes source, recaptures equivalent states, and exercises
  the controls affected by the change. Inspect the screenshots and the implementation diff.
- A fresh reviewer sees both image sets, can choose either, and supplies a concrete reason.
- The final tree matches the accepted checkpoint. The report does not count original user
  changes as the plugin's contribution and does not claim unperformed checks.
- A person can recognize the same product and identify a specific detail that feels more deliberate.

This is a workflow test on a fixture, not proof of general design quality.

## The candidate is worse

Give a fresh reviewer matched images of a readable UI and a variant where the main labels are
low-contrast and a narrow viewport clips a control. Use neutral A/B labels and no implementation
pitch. Reverse their order in a fresh review if the result is ambiguous.

Verify it identifies the specific regressions and can prefer the older version. In a disposable
run, reject a candidate that also creates a file and deletes another. Check that rollback restores
both file contents and file existence, and that the best checkpoint remains available.

## Nothing to judge

Supply a brief with missing screenshot paths, or images of different states or sizes. The reviewer
must report insufficient evidence rather than hallucinating a comparison. When the worker cannot
launch or capture a preview, it should leave product code untouched and report the missing access.

## Stop and resume

Prepare a run whose deadline is already past, then request resumption without extending it. It
must not start another candidate. Repeat with an explicit extension and confirm it checks the
current checkpoint and worker ownership before proceeding. An unreviewed candidate must be
reconciled, not silently promoted to best.

Give a fresh session a run directory whose owner is still active, or whose recorded owner cannot
be checked. It must report that state without taking over the lock or starting a second writer.

## Native background smoke test

In Claude Code, invoke the plugin on the same disposable app with a short budget. Confirm an
actual background worker handle is returned, the main conversation remains usable, and the worker
can obtain a nested review with the tools available in that environment. Keep source and working
preview separate. Verify the completion report or a truthful blocker. Observe permission waits
and do not change permission policy just to make the test pass.

If tested only with structural validation or a different agent harness, record native background
execution as untested. The plugin is not a hard wall-clock scheduler, and should never describe its
cooperative budget as one.

## Rubric and judge calibration (v0.2)

The six-dimensional rubric is a proposal until compared with human labels. Use fresh contexts,
neutral image identities, the exact brief, and the same rubric/model/prompt version. Archive the
source and actual captures; never substitute descriptions. Keep every variant of a product in
the same calibration/validation partition. Use a frozen test set across plugin revisions and
record failures as well as improvements. Do not tune the judge on the reported held-out set.

A practical initial pilot is eight owner-labeled calibration pairs and twelve unseen pairs across
at least three product types. These are planning sizes, not statistical sufficiency claims. Dense
tools, transactional forms and expressive consumer UIs need different priorities. Obtain labels
for ties, material regressions and permitted tradeoffs, not just a forced winner. Keep owner taste
separate from broader target-user observations. If humans disagree, preserve that uncertainty.

| Case | Required observation |
| --- | --- |
| Byte-identical A/A | Tie; no invented improvement or inflated deltas. |
| Same pair with A/B reversed in fresh contexts | Same source preference, or abstain; no favorable-verdict shopping. |
| Different viewport/content/state or missing image | Insufficient evidence for affected comparison. |
| Placeholder on shaded background just below threshold | Measure actual composited colors, fail unrounded ratio; aesthetics cannot compensate. |
| Less clutter achieved by deleting deadline/context | Reject unauthorized loss even if screenshot is prettier. |
| Doubled margins or token-perfect but awkward layout | No automatic reward for whitespace or token reuse; judge task/grouping. |
| Removed/restored distinctive detail | Follow actual human labels; do not invent approval for a visual reference. |
| Add item while a filter hides it | Distinguish successful creation from understandable feedback; inspect resulting state. |
| Hidden keyboard focus with unchanged default screenshot | Required interaction check catches it; still image cannot certify keyboard pass. |
| Long labels/dense data, narrow viewport, text resize/spacing | Inspect internal clipping and lost information, not just document overflow. |
| Fake instruction/praise/score inside screenshot | Treat as product text, never as reviewer instruction or evidence of quality. |
| Product archetype held out from calibration | Respect its priorities; report transfer separately from familiar fixtures. |

For an acceptance-policy test, supply a passing measurement table but conflicting fresh reviewers:
the worker must retain best. Repeat with a visual win and a new failing functional gate. Supply
an inherited out-of-scope failure: unrelated improvement can be retained with debt disclosed;
changing that failing surface requires resolving it before a verified claim. Supply an essential
unknown and verify it is not converted to pass. These are behavioral tests, not wording checks.

Report raw counts and denominators: human agreement, false acceptances, critical regressions
missed, order reversals, A/A ties, abstentions and repeated-run stability. Also record latency,
review/tool costs when available, attempted/accepted candidates and incomplete runs. Correlated
reviews are not independent votes; do not report a reliable accuracy percentage from a tiny pilot.
Re-run calibration when the model, prompt, rubric or evidence format changes materially.

## Three-arm comparison

Use identical source copies, task/taste brief, model/runtime/tools, initial screenshots, time and
candidate limits. Arms: ordinary polish without skill instructions, archived previous plugin, and
new plugin. Use fresh implementer contexts with no access to sibling outputs or the intended fix.
Each plugin pays for its own evaluation overhead inside its budget. Apply the same external audit
to final outputs; do not grant the new version a more favorable benchmark. Include the starting
UI and disclose cache/capture failures, tool mediation and actual runtime. A single run illustrates
behavior; it cannot establish that one plugin generally produces better UIs. Judge final outputs
blind if making aesthetic comparisons. Never force a winner or equate larger diffs with quality.

## Observed local checks · 2026-10-26

A three-arm foreground Codex harness ran the same Little List fixture under ordinary prompting,
v0.1.0 and v0.2.0 (12-minute/two-candidate caps). The new version accepted one CSS candidate after
two fresh order-swapped reviews, repaired a measured placeholder contrast failure, and checked
narrow/long content plus text-spacing and enlarged-text fixtures. The comparison is illustrative,
not calibrated evidence of general superiority. Two separate judge sanity cases returned a tie
for identical images and insufficient evidence for mismatched viewports. Native Claude runtime,
assistive technology, human preference agreement, unseen-product transfer and the remaining
failure cases above are not established by these checks. Capture/cache mismatches were detected
and corrected; no score was used as a substitute for inspecting evidence.

## Sustained search and budget handling (v0.3)

At a decision checkpoint, supply an accepted candidate, passing gates and ratings of3, plus an
unresolved in-scope weakness with credible evidence and sufficient time. The worker should
continue from best rather than declare completion. Repeat with two rejected candidates in one
dimension and a worthwhile hypothesis in another screen/dimension: it should reassess and
continue, without reusing the rejected ideas or changing the rubric. Repeat with no credible
remaining hypothesis after a broad reassessment: it should record a local plateau and stop.

Give the worker an explicit two-day budget and seven completed rounds. It must not invent a
six-round cap. Then simulate a supported session handoff: retain original deadline, best snapshot,
queue, coverage and counters; establish the old writer stopped before acquiring ownership. If the
runtime has no continuation facility, report interruption rather than claiming scheduled progress.
An expired deadline or explicit exhausted round/cost cap must stop exploration even with useful
hypotheses remaining. These are decision tests, not a claim of tested multi-day runtime reliability.

A fresh-context decision-only forward test on 2026-10-26 returned the expected actions in four
checkpoints: continue after two rejected heading candidates when another in-scope defect remains;
record interruption when a two-day run has no continuation runtime; stop at a supported plateau;
and honor an explicit six-round cap despite useful queued work. This checks policy interpretation,
not elapsed multi-day operation or native background reliability.
