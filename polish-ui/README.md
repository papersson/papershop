# polish-ui

Autonomously hill climb a UI you already like toward the best quality achievable within your
scope and budget. The plugin repeatedly finds weaknesses, tries focused changes, evaluates them,
and continues from the best accepted version. Screenshots, independent reviews and relevant
checks must support each improvement. Your existing design remains the reference throughout.

## Install and use

```sh
claude plugin marketplace add papersson/papershop
claude plugin install polish-ui@papershop
```

In the project you want to refine:

```text
/polish-ui:polish-ui Polish this app for up to two hours. Keep its compact layout and current colors.
```

The skill uses the current conversation to capture what you like, prepares a separate working copy
and preview, then starts the polisher in the background. With no duration, it chooses a ceiling
by scope: 30 minutes for a component, two hours for a screen or flow, six hours for a multi-screen
product. Explicit budgets can span hours or days; there is no hidden six-candidate cap. Setup,
reviews and final verification count toward the budget. A time budget is a cooperative deadline,
not an operating-system kill timer.

One successful improvement or a high rubric rating does not end the run. It continues through
ranked opportunities across screens and qualities. Two failed candidates trigger a broader
reassessment; early stopping needs evidence that no worthwhile next step remains. The final
report distinguishes that local plateau from running out of time or access.

For a larger scope:

```text
/polish-ui:polish-ui Hill climb the app for up to two days. Preserve its character and workflows; keep improving across screens while worthwhile gains remain.
```

Long runs checkpoint their best version, pending hypotheses and coverage so they can continue
across supported session handoffs within the same deadline. Multi-day budgets do not guarantee
unattended uptime: the host and agent runtime must support continuation. This plugin supplies no
scheduler and reports an interruption when the runtime stops.

For a shorter pass you can watch, or to inspect and continue a prior run:

```text
/polish-ui:polish-ui The settings dialog, foreground, at most two rounds.
/polish-ui:polish-ui status <run-directory>
/polish-ui:polish-ui resume <run-directory> for up to another 20 minutes.
```

Use `/tasks` in Claude Code to inspect the background subagent. Its launch message includes the
actual agent handle and run directory. Permissions or unavailable tools can interrupt unattended
progress; the plugin reports the blocker and preserves its checkpoint.

For a full Claude Code session that continues without an attached terminal, start one from your
project with a self-contained request:

```sh
claude --bg '/polish-ui:polish-ui Polish the settings UI for up to two hours. Preserve its current design direction.'
```

That new session has no previous conversation, so include the preferences it needs or point it to
an existing brief. Inspect it with `claude agents`. A normal background subagent is session-scoped;
the plugin does not promise it will survive closing its host. These execution distinctions follow
the [Claude Code subagent docs](https://code.claude.com/docs/en/sub-agents) and
[background-session docs](https://code.claude.com/docs/en/agent-view).

## What a run produces

The run directory contains a brief, current state, immutable captures and reviews, and `report.md`.
The handoff shows before/after images, accepted changes, the implementation diff or working copy,
checks performed, and the stop reason. An unchanged result is valid when no candidate improves the
UI convincingly. A blocked or interrupted run is labeled separately.

Background runs use a separate copy of the actual starting UI, including relevant local changes.
Results remain there for review; the plugin does not merge or publish them. Review artifacts stay
outside the implementation diff. By default they live under `.polish-ui/runs/` in the source
project; a project's existing artifact location takes precedence. They may contain screenshots of
your app, so keep them local unless you choose to share them.

The polisher changes one candidate at a time. The reviewer can read images and source files but
cannot edit files, execute shell commands, or use browser tools. It judges A/B evidence without
the implementer's pitch. Behavioral claims are checked by the polisher and reported separately.
This reduces self-endorsement; it does not turn visual preference into an objective measurement.

## What it optimizes

The six qualities are **task clarity and hierarchy, space and composition, typography and
readability, visual coherence, interaction clarity and feedback, and character and delight**.
The brief sets their priorities. Passing checks is the floor; the goal is continued improvement
across these qualities while useful gains remain. “As high as possible” refers to UI quality,
not maximizing raw contrast, whitespace, element counts or model scores. Clean means purposeful
grouping and breathing room; removing
useful context or the product's personality is not an improvement.

Baseline/final profiles use anchored 1–4 ratings (or unknown/not applicable); candidate reviews
use better/same/worse/unknown. These are model judgments, not objective scores. There is no total,
weighted average or percentage improvement. [The rubric](skills/polish-ui/references/rubric.md)
defines the anchors and the ways each dimension can be gamed.

Evidence is labeled **M** measured, **P** proxy, **J** model judgment or **H** human evidence.
Content, behavior and scoped accessibility checks are separate gates. Aesthetic preference cannot
compensate for lost content or a regression. Untouched baseline debt is disclosed, unknowns remain
unknown, and partial automated checks do not establish accessibility conformance.

The default judge is an **uncalibrated pilot**. Proposed acceptances get a fresh, blind A/B review
and a second fresh review with the order swapped. Disagreement retains the best version. Final
validation checks cumulative drift and reserved states where feasible. This costs more than one
self-review; the budget includes that cost. No-change is valid, but a run blocked on evidence is
reported as blocked rather than a design success. See the
[evaluation protocol](skills/polish-ui/references/evaluation.md).

## Supported environments

The workflow is framework-independent. Its practical requirement is an editable source tree plus
a preview the agent can render, inspect, and capture. Web apps with working browser automation
are the first supported path. Native and desktop UIs are conditional on usable build, app-control,
capture, and isolation tools in that session; the plugin includes no native automation adapter.
Screenshots alone support critique, not implementation or verified interaction behavior.

It uses available project tooling rather than bundling a browser, installing a framework, or
requiring another papershop plugin. Background operation also needs access to those tools and
nested subagents for independent review. If those are unavailable, the main session can own the
loop and call the reviewer directly; limitations must be reported before editing.

Claude Code 2.1.310 accepts the manifest and component metadata. Its directory audit separately
flags this repository's missing license and the plugin's missing listing icon; no license has
been selected on the owner's behalf. Foreground behavior was exercised in a Codex test harness;
native Claude background lifecycle remains unverified. Runtime behavior and available tools vary
by version and settings; see the [runtime notes](skills/polish-ui/references/runtime.md).

## Develop and verify

Load the local plugin for one session without installing it:

```sh
claude --plugin-dir ./polish-ui
```

Validate the manifest and both component directories:

```sh
claude plugin validate ./polish-ui
claude plugin validate ./polish-ui/skills
claude plugin validate ./polish-ui/agents
```

The plugin is Markdown and JSON, with nothing to build. The
[forward-test cases](evals/README.md) exercise the decisions that structural validation cannot
check. They use disposable fixtures and do not run a multi-hour polish pass on a real project.
