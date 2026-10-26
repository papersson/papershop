---
name: polish-ui
description: >
  Refine an existing UI whose design direction the user already likes. Use for visual polish,
  finishing passes, or sustained autonomous hill climbing over hours or days, within an agreed
  budget. Preserve
  the product's character, compare rendered states, and retain only verified improvements.
  Not for creating a new UI or choosing a new design direction.
argument-hint: "[target] [time or round budget] [background|foreground|resume <run-directory>]"
---

# Polish UI

Hill climb an existing UI toward the best evidenced quality achievable within the agreed scope
and budget. Repeatedly find weaknesses, try focused changes, evaluate, retain improvements, and
continue from the best version. One accepted change, passing gates, or a good rubric rating is
not a completion condition while worthwhile opportunities remain. Preserve the design direction
and reject unconvincing changes without abandoning the search.

This entrypoint runs in the current conversation so the handoff preserves the user's taste and
recent decisions. Do not set `context: fork`: a forked skill would lose that conversation context.

## Establish the handoff

Read the target project's instructions and infer the scope from the request and conversation.
Use the actual interface, its source and design tokens, and any supplied references. Record a
short brief in the run directory; ask only when a missing answer would materially change the work.

The brief must convey:

- The product, users, primary task, and target screens or components.
- What the user likes: density, tone, typography, palette, layout, distinctive details. Separate
  user-stated preferences from your inferences. References are optional; the existing UI anchors taste.
- The changes that are in scope and the behavior and design choices to preserve.
- The exact source checkout, starting revision and local changes, working copy, run directory,
  preview command or surface, capture tools, and relevant verification commands.
- An evaluation profile: primary, supporting and preserve-only qualities from
  [rubric.md](references/rubric.md), applicable gates, known baseline debt, and repeatable
  development captures plus reserved validation states where feasible. Clean means intentional
  grouping and breathing room, not removing useful context or personality.
- The execution mode, start time, wall-clock deadline, any round/cost caps, and final-check reserve.
  For long runs, record intermediate checkpoints and the runtime's continuation limitations.

Honor the user's budget, including requests for hours or days. When no duration is supplied,
choose and announce a bounded default by scope: 30 minutes for a component, two hours for a screen
or flow, six hours for a multi-screen product. These are ceilings, not time to fill; multi-day work
requires a requested duration. Honor explicit round/cost limits as well. Do not impose a hidden
six-round cap on a longer run; absent a round cap, the deadline and plateau rule bound the search.
A round is one focused candidate and its evaluation, including rejection or failure.

Start the clock before setup. Reserve roughly the last fifth for final verification and delivery;
checkpoint during long runs as well. The budget includes setup, reviews, repairs and tool waits.
Time is a cooperative limit, not a process kill timer; report in-flight overruns honestly. See
[run.md](references/run.md) for continued exploration and plateau criteria, and the runtime
reference for recoverable long runs. Never represent an interrupted session as ongoing work.

Read [evaluation.md](references/evaluation.md) for evidence and acceptance rules, and
[runtime.md](references/runtime.md) before preparing the workspace or starting a background
run. Establish a working preview and a restorable starting snapshot before handing off edits.
If the interface cannot be rendered and inspected, report what is missing and make no speculative
polish edits. A screenshot-only request can receive a clearly labeled critique, not a claimed
implementation or interaction verification.

Create `brief.md` and `state.md` in the run directory. Use the project's existing artifact location
when available; otherwise use `.polish-ui/runs/<unique-run-id>/` under the source project. Keep run
artifacts out of the implementation diff; do not change shared ignore rules just to hide them.
Record absolute paths so another agent can resume without the conversation.

## Run or delegate

Default to a background run once setup is ready, unless the user asks for foreground execution.
For a background run, use the plugin agent `polish-ui:polisher`, supplying:

1. The absolute run directory and its `brief.md`.
2. The exact permitted working copy; the source checkout is read-only except for the run directory.
3. The absolute workflow path `${CLAUDE_SKILL_DIR}/references/run.md`.
4. The absolute runtime reference `${CLAUDE_SKILL_DIR}/references/runtime.md`.
5. The evaluation and rubric paths, frozen profile, budget, and requirement to use
   `polish-ui:reviewer` for fresh visual comparisons and order-swapped checks before acceptance.

Use the Agent tool's supported background mode. Do not launch a second worker on an active run.
Persist the returned worker handle and owning parent-session identity in `state.md` immediately
after dispatch; report that handle, run directory, scope, and budget. Say it has started only
after the tool confirms dispatch; a queued launch or permission wait is not active progress.
Keep the parent out of the worker's files and browser session while it runs.

For foreground work, follow [run.md](references/run.md) yourself and delegate only the visual
review. The same evidence and acceptance rules apply. This skill does not require other papershop
plugins, a workflow service, or a particular browser plugin.

## Resume and status

For a status request, read the existing state and available agent status; do not start new work.
For a resume request, read the brief, state, and last report, verify the working copy still matches
the recorded checkpoint, and confirm the recorded owner has stopped before taking ownership.
An unavailable status is not proof of termination. Finish or roll back an
unreviewed candidate before starting another. Preserve the original budget unless the user
explicitly extends it. Reconcile changed source files before applying results back.

## Deliver

On completion, give the visible outcome first, followed by matched before/after images, the
reviewable diff or working-copy location, verification results, the six-dimensional baseline/final profile, and any limitations.
Keep measured checks, proxies, model judgments and human evidence distinct; never present a
combined quality score or turn an unknown into a pass. Include the
run directory and actual stop reason. Attribute aesthetic judgments to the reviewer; passing
checks does not establish that the user will prefer the design. The detailed report lives in the
run directory. Do not merge, push, publish, or change cross-project preferences as part of polishing.
