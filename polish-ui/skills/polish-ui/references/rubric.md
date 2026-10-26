# Evaluation rubric · version 1

Use this as a diagnostic profile, not a leaderboard. Choose primary, supporting, and preserve-only
qualities for the actual product in the brief; all six remain regression checks. Do not assign
universal weights, sum ratings, average them, or claim percentage improvements. One observation
can affect several qualities, but do not count it as several independent benefits.

## Evidence types

- **M — measured/observed:** reproducible quantities or assertions, with method, state, scope and
  result. Examples: contrast on the actual background, a preserved title, keyboard activation.
- **P — proxy:** an observable correlate, not the desired quality. Token reuse, element count,
  whitespace percentage and clicks are not scores for beauty, coherence or ease of use.
- **J — model judgment:** perceived hierarchy, balance, optical consistency, interaction clarity
  or aesthetic fit. Explain what in the evidence supports it; confidence is not a probability.
- **H — human evidence:** identify whose preference or observed task performance, under what
  conditions. Owner taste is valuable but does not establish preference for all target users.

An accessible-name presence check is M; whether the name is understandable requires J/H. An
interaction script passing is M, not proof of intuitive use. A screenshot cannot verify keyboard,
screen-reader, timing or motion behavior. Attribute supplied test results to their producer.

## Anchors

Rate baseline and final states with ordinal anchors: **1** obstructive/contrary to brief,
**2** usable but unresolved, **3** deliberate and appropriate, **4** exceptional across inspected
evidence, **U** insufficient evidence, **NA** not applicable with reason. Use the specific anchors
below. A 4 requires supporting breadth, not a beautiful default screenshot. These anchors are an
uncalibrated starting rubric until checked against human examples.

During iteration report **better / same / worse / unknown** against the current best. An improvement
can occur within an anchor; do not inflate ratings to justify an edit. Final absolute adequacy,
relative improvement, and human preference are separate conclusions.

## Task clarity & hierarchy

Can I tell what matters, understand the labels, and find the next action?

Evidence: Matched full screens, real task and content, labels and visible action states. Human comprehension and task observation when available.

Measurement boundary: Label presence, DOM order and content preservation are measurable. First-click success and search time require observed people; font size is only a proxy for prominence.

1. The task or next action is obscured or misleading.
2. The task is discoverable, but competing emphasis or ambiguous wording causes searching.
3. Task content, supporting context, and actions have clear, appropriate priorities.
4. Priority stays effortless across complex content and states; precision is supported by reference examples or user observation.

Avoid gaming: Make every title bold, enlarge the hero, or hide necessary secondary information.

Owns attention and meaning. Do not also award the same title-weight change as a separate spacing benefit.

## Space & composition

Do proximity, rhythm, alignment, and density make the screen feel composed and easy to use?

Evidence: Full screens at actual working size; narrow and wide layouts; long, empty, and dense content.

Measurement boundary: Bounding boxes, overflow, alignment offsets and row heights are measurable. Whitespace percentage and token conformity do not measure good composition.

1. Crowding, disconnection, or overlap obscures relationships.
2. Usable arrangement, but gaps, alignment, or density feel arbitrary.
3. Related elements group naturally; whitespace provides breathing room and a clear rhythm.
4. Composition remains balanced and economical under stressful content and viewport changes, with purposeful exceptions.

Avoid gaming: Increase every margin, remove half the content, or force every gap onto an identical grid.

Owns spatial relationships. Adequate density is a contextual range, not a quantity to maximize.

## Typography & readability

Is text comfortable to read, with deliberate type roles and wrapping?

Evidence: Actual-size text, long titles, metadata, localization, zoom/text-spacing tests, and representative fonts.

Measurement boundary: Contrast, font properties, wrapping/clipping and resize behavior can be checked. Reading comfort and typographic quality need judgment or human testing.

1. Text is materially difficult to read or essential wording is lost.
2. Readable enough in ordinary cases, but scale, line length, wrapping or emphasis is awkward.
3. Type roles are clear and the size, line height, weight and wrapping suit the task.
4. Type feels precisely resolved across content extremes and retains its quality with supported user adaptations.

Avoid gaming: Increase all type, maximize contrast without hierarchy, or hide overflow with ellipses.

Owns reading and type craft. Record threshold failures in gates; do not convert contrast ratios into beauty points.

## Visual coherence

Do components, icons, color roles, borders, and surfaces feel like one intentional system?

Evidence: Repeated components and all their relevant states, including menus/dialogs and responsive variants when present.

Measurement boundary: Token use, exact dimensions and repeated styles are measurable proxies. Semantic appropriateness and optical consistency are judgments.

1. The same appearance implies different behavior, or conflicting treatments impede understanding.
2. The system is mostly recognizable but has arbitrary component or icon inconsistencies.
3. Repeated roles share a coherent treatment; meaningful differences remain visible.
4. The system feels unified across states and surfaces, including deliberate optical corrections and distinctive exceptions.

Avoid gaming: Make everything identical or gray, erase status distinctions, or reward token reuse regardless of the result.

Owns relationships among components. Semantic correctness of status colors is also a constraint.

## Interaction clarity & feedback

Are actions discoverable and are their outcomes, progress, errors, and recovery understandable?

Evidence: Before/action/after traces, keyboard and pointer use, focus, validation and recovery; motion needs temporal evidence.

Measurement boundary: Expected state transitions, keyboard reachability, timing, target geometry and labels can be checked. Discoverability, reassuring feedback and perceived responsiveness need judgment and users.

1. An essential action is misleading, its outcome is lost, or recovery is unavailable.
2. Basic actions work, but an important state or outcome is easy to miss.
3. Relevant controls and states are legible; feedback and recovery keep the user oriented.
4. Feedback is precise, timely and satisfying even in unusual states, without adding friction or overriding user control.

Avoid gaming: Add tooltips everywhere, animate every change, or equate a successful automation script with intuitive use.

Owns the action–response experience. A correctness pass is necessary evidence, not a usability rating.

## Character & delight

Does this feel thoughtfully made for this product and audience, with details worth keeping?

Evidence: Frozen taste brief, owner-approved reference details, whole-screen composition and relevant interaction moments.

Measurement boundary: There is no objective beauty score. Model preference is a prediction; target-user preference and satisfaction are direct human evidence.

1. The visual treatment contradicts the brief or removes character the user values.
2. The direction is plausible, but generic, overdecorated or unresolved.
3. Distinctive details and restraint reinforce the intended character without competing with the task.
4. Memorable, appropriate beauty and satisfying details remain effective in ordinary and difficult states; positive reference calibration supports the judgment.

Avoid gaming: Paste in fashionable gradients, serif headings, mascots or animation; alternatively remove all personality to appear minimal.

Owns aesthetic and emotional fit. Fewer decorations, more colors, or novelty are not rewards.

## Clean without erasure

Economy is part of clarity and composition, not a seventh score. Remove redundant decoration,
duplicate labels or unnecessary containers when the evidence supports it. Preserve task context,
controls, status distinctions and valued personality. Neither fewer elements nor more whitespace
is intrinsically better. Color and icons belong to coherence and accessibility checks;
responsiveness cuts across all six qualities. Do not turn one successful fixture into a universal
style recipe.
