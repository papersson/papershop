# Workspace and execution

Read this before launching. Use the actual tools and permissions available in the session. This
plugin supplies the workflow and agent definitions; Claude Code supplies their execution.

## A faithful, separate starting point

Background work needs its own editable copy and preview. Record the source's absolute path,
current `HEAD`, tracked changes (including staged changes), and relevant untracked files. Build
the copy from that state, not from the repository's default branch. Native `isolation: worktree`
can start at the default branch and does not promise to copy uncommitted work, so the supplied
worker deliberately has no automatic isolation field.

For Git projects, prepare a new worktree and branch at the recorded `HEAD`, following project
branch conventions. Transfer the binary-capable diff from `HEAD` and the relevant untracked source
files into that worktree. Leave the original index, branch, and files untouched. Exclude the run
directory itself. Do not copy ignored files, dependencies, credentials, or local databases wholesale;
use the project's normal local setup for anything the preview needs. Resolve submodules or other
special repository state explicitly rather than silently dropping it.

Verify the transferred source matches the original and that the preview renders the UI the user
approved. Capture this starting tree as the immutable baseline, including existing user changes.
Use local checkpoint commits when the project supports them, or exact file snapshots with an
inventory that distinguishes an absent file from an empty one. Keep an independent checkpoint for
the best accepted version. A report diff must compare with this baseline, not raw source `HEAD`.

For non-Git projects, use a dedicated copy with the same baseline and file inventory. If a faithful
copy is impractical, foreground execution in an exclusively owned workspace is a supported fallback;
explain the limitation before starting. Never silently run a background writer in the user's active
checkout. Shared preview deployments, unsaved native-app state, and shared live databases may make
safe concurrent work impossible even when source files are isolated.

Use a dedicated preview port/profile or app instance. Verify its URL or executable belongs to the
working copy, not the user's original server. All worker shell calls must explicitly target the
working copy; a prior `cd` in another tool call is not a reliable working-directory setting. Record
the processes started by this run so cleanup cannot stop the user's servers.

Before testing actions that mutate data, verify the preview uses disposable fixtures or a test
backend whose effects are contained. A separate port does not isolate shared records or external
services. If that cannot be established, use read-only navigation and inspection, and report the
unverified interactions. Do not exercise real sends, purchases, or destructive actions to test polish.

## Background execution

The `polish-ui:polisher` agent has `background: true`. It inherits available tools and the session's
permissions; it does not grant permissions. Its read-only reviewer receives only local file-reading
tools and images captured by the worker. Check that the worker can use the required preview tools
and spawn a nested reviewer. Background agents can have fewer built-in tools than the parent.

If nesting is unavailable, keep the loop in the main session and dispatch the reviewer from there,
or use a separately authorized full Claude Code session. If backgrounding is disabled or required
tools are unavailable, report that limitation and use the foreground path when it still fulfills
the request. Do not disguise self-review as independent review, change permission settings, or
start a detached shell process to evade a runtime restriction.

Background subagents belong to their parent session. For a full session that can outlive its
terminal, Claude Code also supports `claude --bg` and its agent view. A user can start this plugin
there directly or background the running parent session. Treat that as a distinct execution mode;
do not promise a background subagent survives closing its host. Preserve the same isolated
workspace, handoff, evidence, and budget in either mode.

Check the actual tool return and status. A permission prompt can stop unattended progress. Record
`blocked` with the required action if the run cannot proceed; do not repeatedly retry or wait out
the time budget. A canceled agent or exhausted turn limit is `interrupted`, not a completed polish
pass. Keep its checkpoint for explicit resumption.

## Local state

Maintain `state.md` after each candidate and before any handoff or compaction. It records:

- Status: `preparing`, `running`, `verifying`, `completed`, `blocked`, or `interrupted`.
- Start/deadline, any round/cost caps, rounds attempted, and remaining verification reserve.
- Current work block, cumulative-review checkpoint, ranked opportunity queue and coverage gaps;
  the reassessment evidence behind any claimed plateau.
- Source and work paths, baseline and best checkpoint, and any unaccepted candidate.
- Owning parent-session identity, worker handle (or foreground owner), and ownership status.
- Capture manifest, preview address/process handles, reviewer handles, and completed checks.
- Accepted/rejected hypotheses with evidence paths, next useful opportunity, and stop reason.

Before edits, acquire exclusive ownership of the run with an atomic lock directory or equivalent
local mechanism and record the owner in it. The launcher persists the dispatched worker's handle;
the worker confirms its identity at startup. Release only your own lock on exit. A resume must
positively establish that an earlier owner has stopped before replacing a stale lock. If that
cannot be established, report the ownership blocker rather than launching a competing writer.

For multi-hour or multi-day requests, verify the chosen host/session can remain available or has
an actually supported continuation path. A longer deadline does not make a subagent durable or
install a scheduler. Record the available continuation mechanism and any known session limits;
when it is unavailable, preserve the run for explicit resumption rather than promising continuous
operation. A handoff within an authorized budget does not need a new budget, but must establish
that the previous writer stopped. Never reset the start time/deadline or counters at a checkpoint.

Resume from that evidence, not from memory. Preserve the original baseline through every round.
Before releasing an isolated worktree, retain the result and report somewhere accessible. Never
delete the only copy of an accepted result. Stop only preview processes owned by this run.

## Runtime references

Checked against Claude Code 2.1.310 and the official documentation on 2026-10-26. These are source
links, not a requirement to browse again on every invocation; recheck when runtime behavior differs.

- [Subagent tools, background behavior, nesting, and isolation](https://code.claude.com/docs/en/sub-agents)
- [Skill context and path substitution](https://code.claude.com/docs/en/skills)
- [Full background sessions and agent view](https://code.claude.com/docs/en/agent-view)
- [Plugin structure and discovery](https://code.claude.com/docs/en/plugins-reference)
