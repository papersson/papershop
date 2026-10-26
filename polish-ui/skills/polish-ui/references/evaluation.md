# Evidence, gates and comparison protocol · version 2

Read alongside [rubric.md](rubric.md). This protocol supports bounded improvement; it is not a
validated predictor of user preference. Adapt coverage to the touched surfaces and product risks.

## Freeze the evaluation profile

Before editing, record the primary task, explicit and inferred taste separately, useful content
and behavior to preserve, primary/supporting/preserve-only qualities, and relevant acceptance
checks. Keep the profile stable during a run. A changed product requirement creates a new profile
version and requires re-evaluating the baseline; never silently change the target to favor a result.

Choose repeatable development captures and a small reserve of relevant states/content for final
validation, when the budget allows. Shared-token changes require broader coverage. If a reserved
case informs a repair it becomes development evidence: replace it before calling later evidence
unseen, or report there is no untouched validation set. One fixture is not proof of transfer.

## What is being optimized

Use the six qualities to guide sustained search for the strongest UI within scope, including
improvements within an anchored rating. Passing gates establishes a floor, not a finish line.
Seek further gains across primary and supporting qualities while preserving the constraints and
preserve-only qualities in the brief. Do not sacrifice one dimension just to inflate another.

“As high as possible” means better evidenced task experience and visual quality, not maximizing
every measured number. Contrast thresholds are constraints, spacing/density have contextual
optima, and model ratings are noisy diagnostics. Keep evaluators, anchors and acceptance rules
fixed during the run. Candidate evidence and regression checks decide acceptance; the opportunity
queue, budget and supported plateau in [run.md](run.md) decide when the search ends.

## Gates are separate from aesthetic judgment

Record **pass / fail / unknown / NA (reason)** for each applicable gate and its evidence. Unknown
is never pass. Scope the claim to what was checked; a scanner pass is not accessibility conformance.
A known out-of-scope baseline failure can remain explicitly inherited. New or worsened failures
block acceptance, and failures in the changed surface must be fixed before calling that surface
verified. Essential unknowns block candidate acceptance. Untouched baseline debt prevents an
unqualified whole-product pass, but need not stop an unrelated bounded improvement.

- **Function and content:** preserve required information, states, primary workflows and useful
  feedback. Compare actual before/action/after outcomes, including unusual but relevant states.
- **Accessibility:** use the project's platform/standard. For web projects without a specified
  target, use applicable WCAG 2.2 AA checks as the default scoped baseline. Include:
  - Text contrast: 4.5:1 normally; 3:1 for qualifying large text (18 pt, or 14 pt bold). Check
    placeholders, metadata and states against actual composited backgrounds. Decide from
    unrounded ratios. Inactive controls and other criterion exceptions require explicit reasons.
  - Necessary control/state graphics: 3:1 where 1.4.11 applies. Decorative separators do not
    automatically require 3:1. Color must not be the only means of conveying essential information.
  - Keyboard reachability/activation, meaningful names, visible focus and focus not entirely
    obscured (2.4.7 / 2.4.11 AA). The stricter 2.4.13 focus appearance criterion is AAA, not a
    universal AA requirement. A DOM name existing does not establish its adequacy.
  - Pointer targets: 24×24 CSS px or a valid 2.5.8 exception, including spacing. Measure the
    actual clickable label/target, not only its checkbox glyph. 44×44 is enhanced AAA.
  - Reflow at the equivalent of 320 CSS px except content requiring two-dimensional layout.
    Inspect internal clipping/lost content as well as document overflow. Text resize and text
    spacing are separate checks; a narrow screenshot alone does not establish those passes.
- **Scope and identity:** preserve the frozen brief, useful context, semantic distinctions and
  approved design direction. Ask for human resolution of a material taste ambiguity; until then
  retain the best, without blocking unrelated authorized work.
- **Project constraints:** required checks and relevant performance/motion/platform budgets. Use
  repeatable comparable measurements for performance; do not invent universal timing targets.

Record baseline debt before changing it. Use cheap deterministic checks before costly visual
reviews. A failed candidate may be repaired within its focused hypothesis before review; once
reviewed, a revision is a new candidate. Do not hide extra attempts outside the round budget.

## Independent comparison

1. Freeze exact source snapshots and immutable captures. Record route, viewport, theme, fixture,
   state, source identity and capture time. Pair equivalent evidence and wait for fonts/assets.
   A mismatched or stale capture cannot support a preference.
2. Give a fresh `polish-ui:reviewer` the neutral product/taste/profile brief, both image sets,
   relevant interaction traces and gate evidence, and the rubric path. Use A/B labels and keep
   candidate mapping, author, hypothesis, implementation narrative, prior verdicts and scores out
   of its context. Preserve honest measurement provenance. Do not fork the worker's conversation.
3. Review the actual whole-screen images, relevant details and state transitions. Record six
   deltas, located benefits/regressions, materiality, missing evidence, and a holistic A/B/tie/
   insufficient verdict. The holistic verdict resolves tradeoffs; it is not a seventh score.
4. In the default **uncalibrated pilot**, repeat every proposed acceptance in a fresh context with
   A/B order swapped, without the first verdict. Map both back to source identity. Disagreement,
   ties or essential unknowns retain best. Do not ask repeatedly until a candidate wins. A future
   documented calibration may sample clear wins, but must retain swaps for close, consequential
   and final comparisons. Same-model reviews are correlated checks, not independent human votes.
5. Accept only a concrete benefit in the agreed priorities, passed applicable gates (with explicit
   inherited-debt exceptions), no unresolved material regression or forbidden drift, and a holistic
   result at least as good. Minor tradeoffs require stated impact and compatibility with the brief.
   Scores and amount of change never override gates. Resolve essential uncertainty with a specific
   check within budget; otherwise retain best.

For baseline/final comparisons include the six anchored profiles and cumulative drift. A candidate
comparison against baseline can also serve as final evidence if it covers the final source and
required states. Do not repeat identical reviews merely to fill paperwork. Record why evidence was
reused. An unchanged result is valid only when the evidence justifies no acceptance; distinguish
that from missing tools, exhausted review time or an incomplete run.

## Minimal record, not a ceremony

Use concise Markdown tables and ordinary files; no workflow service or database is required.
Keep `brief.md`, `state.md`, captures/manifest, reviews and `report.md`. State tracks current/best/
baseline snapshots, ownership, budget, round decisions and pending work. Evidence records the
profile/rubric version, known model/runtime/prompt versions, image/source identities, check method
and coverage, baseline debt, reviewer handles, private A/B mapping and stop reason. Unknown model
settings stay unknown. Do not claim a second review is independent if it inherited the first.

Report objective results and model judgments separately. Show both relative gains and remaining
absolute deficiencies. Human approval is not an automatic background requirement: request it only
for a material unresolved preference, and keep the verified best until it arrives.

## Basis and limits

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) defines the scoped accessibility checks;
  [WAI evaluation guidance](https://www.w3.org/WAI/test-evaluate/tools/selecting/) explains tool limits.
- [NN/g usability heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/) and
  [aesthetic/minimalist design](https://www.nngroup.com/articles/aesthetic-minimalist-design/) inform
  task clarity, feedback, relevance and economy, not a universal visual style.
- [HEART](https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/)
  grounds the separation of product goals, signals and metrics.
- [MT-Bench judge analysis](https://arxiv.org/abs/2306.05685) and
  [position-bias research](https://arxiv.org/abs/2406.07791) motivate blinding/order checks; their
  findings do not establish this UI judge's accuracy.
- [Adaptive data analysis](https://arxiv.org/abs/1506.02629) motivates reserved validation evidence;
  a few reserved states are a practical guard, not a statistical guarantee.

See [forward tests](../../../evals/README.md) for calibration and failure cases.
