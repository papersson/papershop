---
name: worklog
description: >
  Reports and reconstructs your work history from Claude Code transcripts, and mines them for
  recurring corrections. Use when the user wants to (1) know what they worked on in a time period
  ("what did I do this week / since May 1"), (2) extract a coherent activity log for a task that
  spanned multiple sessions ("how did I deploy X", "trace the auth migration") — often to distill
  into a runbook, (3) surface recurring friction in how a task gets done ("where do we keep getting
  stuck deploying"), (4) assemble context to resume a task in a fresh session ("get me back up to
  speed on the CV work"), (5) locate and reopen a past session ("which dir was I in for the
  job-posting stuff?"), or (6) mine recent sessions for corrections the user keeps making and
  distill the recurring ones into CLAUDE.md rules.
---

# worklog

You reconstruct what the user worked on from their Claude Code transcript history. A deterministic
indexer (`worklog.py`) has already distilled every transcript into a queryable DuckDB index; the
engine drives it and synthesizes the results.

## Architecture: orchestrate, never query inline

**You are the orchestrator. You never run the `worklog` engine or read raw `.jsonl` transcripts in
your own context.** Those operations are noisy — ranked-list JSON, snippet dumps, transcript greps —
and that noise pollutes the conversation the user is reading and burns the context you need for
judgment. Every request is dispatched to a **subagent** that does the querying and reading in an
isolated context and returns a **clean, structured digest**. You relay the digest or act on it.

This split is the whole point: it lets the work be **thorough without being noisy**. The subagent
can over-collect — wide windows, many phrasings, liberal raw-transcript reads — because all that
intermediate noise is discarded when its context closes. Only the distilled digest comes back to
you.

Two dispatch shapes:

- **Single subagent** — for the focused requests: time report (1), activity log / runbook (2),
  resume pack (4), find & reopen (5). Spawn one `general-purpose` subagent; it runs the engine and
  reads transcripts, then returns the digest.
- **Workflow (many subagents)** — friction analysis (3) and rule-mining (6), and a very large
  activity log (2). Fan out one agent per session; each reads a raw transcript in a clean context;
  then synthesize (and, for rule-mining, adversarially verify). The Workflow already isolates the
  per-session noise, so it satisfies the same rule — the raw reading never lands in your context.

**Never** call `worklog` or `Read` a transcript from this context — not even to "double-check" a
digest. If a digest comes back thin, dispatch again with a wider brief; do not pull the raw
material into your own context.

## The engine (what the subagent drives)

`worklog <subcommand>` — every subcommand auto-refreshes the index first (incremental, ~0.2s), so
the index is never built manually. Add `--json` to any query for structured data to reason over.

- `report --since 7d [--until ISO] [--json]` — sessions in a window, grouped, with the user's
  asks, files edited, and git commands. `--since` accepts `7d`/`2w`/`12h` or an ISO date.
- `search "<topic>" [--since ISO] [--json]` — sessions matching a topic, ranked, with snippets.
- `task "<topic>" [--json]` — full dossier across ALL sessions for one task: ranked sessions, a
  merged chronological timeline, files read vs edited (with frequency), and commands.

Scoring is keyword-based (term-hit count), so longer sessions can over-rank — apply judgment, don't
trust the order blindly. Use `--json` when filtering or cross-referencing.

Important index limitation: the index does **not** store command/tool error output (`tool_result`
bodies are dropped at distill time). The real errors, failed attempts, and the user's exact
corrections live only in the raw transcripts at `~/.claude/projects/**/<session-id>.jsonl`. Any
analysis of *what went wrong* or *what the user re-instructed* must read those raw files — the index
alone undercounts both.

## Be thorough — over-collect, then distill

Because every read happens in a subagent whose context is thrown away, the subagent must err toward
over-collection. These directives go into every subagent brief:

- **Don't stop at one query.** Try **3–5 phrasings** of the topic (synonyms, the tool/vendor name,
  the file name, the error text). The keyword scorer misses synonyms, so each phrasing surfaces
  different sessions.
- **Widen the window** past the obvious. If the user says "last week," also glance back further —
  the task often started earlier than they remember.
- **Read raw `.jsonl` transcripts liberally**, not only as a last resort. The index drops tool and
  error output, so corrections, failures, and exact values (amounts, IDs, flags, addresses) live
  only in the raw files. Read every plausibly-relevant session's transcript, not just the top hit.
- **Prefer false positives to misses.** Surface a borderline session flagged as uncertain rather
  than drop it. The orchestrator/user can discard a wrong lead; they can't recover one that was
  never found.
- The noise cost is paid inside the subagent and discarded. **Bias hard toward thoroughness** — the
  only thing that escapes the subagent is the clean digest.

## Digest contract (what every subagent returns)

Clean structured markdown, and nothing else:

- Lead with the synthesis / answer for the mode.
- **Ground every claim** in a real source: short session id, date, and file/command. Never invent
  activity.
- Mode-appropriate sections (timeline, key files read vs edited, gotchas, exact values).
- **Flag uncertain or borderline findings explicitly** — over-collection means some leads are weak;
  say which.
- **No raw JSON, no ranked-list dumps, no multi-line transcript excerpts, no tool output.** If you
  must quote a transcript, one line maximum. The caller's context has to stay clean — that is the
  reason the subagent exists.

## Dispatching a single subagent

For modes 1, 2, 4, 5, spawn one `general-purpose` subagent with a **self-contained** prompt you
compose from this file — the subagent must NOT invoke the worklog skill (that would loop) and must
NOT spawn further subagents (it *is* the subagent; it runs the engine directly). Include:

1. **The engine reference** (the `worklog` subcommands above) and the index-limitation note.
2. **The thoroughness directives** ("over-collect, then distill" — paste them).
3. **The specific mode playbook** for this request (from "How to handle each request" below).
4. **The user's request verbatim**, plus any window/scope.
5. **The digest contract** — the exact clean structure to return.

Then relay the returned digest to the user (lightly framed), or use it as context for the next
action. For the two workflow modes, drive a dynamic workflow instead (see those modes below); the
per-session reads run in the workflow's own agents, so your context still stays clean.

## How to handle each request (the subagent's / workflow's playbook)

**1. Time report (single subagent).** Run `report` for the window. Synthesize a tight,
standup-style summary grouped by project/theme (not by session). Lead with what was accomplished,
past tense, no filler. Fold trivial sessions together or drop them. Cite dates.

**2. Activity log for a task (single subagent, default).** Run `task "<topic>"` (try several
phrasings — the first is often thin). Identify the genuinely-relevant sessions, group them into
distinct *instances* (a recurring task done separately over time), and reconstruct the actual
sequence — what was done, what broke, how it was fixed — from the timeline + commands + files. Read
the specific transcripts liberally to fill gaps (exact flags, amounts, error recovery); that is
where the real detail lives. The activity log is the primary deliverable, worth producing even for
a one-off. If the user wants it saved, the orchestrator `Write`s it where they specify.

**2b. Generalize to a runbook — only when warranted.** Promote an activity log into a reusable
step-by-step runbook ONLY when there are **enough instances to generalize safely** — ideally
several independent runs — and the pattern is clear. State how many instances were found. With only
one (or instances that diverge too much), do NOT invent a runbook: deliver the activity log and say
plainly it's a single instance, and that repeating the task a couple more times will let you build a
trustworthy runbook. When you do build one, note what varied and the gotchas.

**3. Friction analysis (workflow).** Surface *where a task keeps going wrong* — recurring errors,
retries, manual workarounds, deferred fixes, edge cases, frustration signals. Because the index
drops error bodies, this needs the raw transcripts, and there are usually too many to read well in
one context. Drive a workflow:

- **Queue** — `task "<topic>" --json` to get the relevant session ids and transcript paths.
- **Fan out** — one agent per session reads that raw `.jsonl` and extracts concrete friction points
  (the actual error, what was retried, what was worked around), each grounded in a real line.
- **Synthesize** — cluster pain points by recurrence and recency, rank them, separate quick fixes
  from deeper ones, and ground each in a concrete session/error. Drop anything not grounded.

The **verifier is rung-1 deterministic**: a pain-point must cite a real line in a `.jsonl`; one that
doesn't is **FAILED** and dropped (an agent error), not BLOCKED. **BLOCK** only on genuinely
unresolvable scope — an empty or ambiguous session list, or an ambiguous time window — rather than
fabricating friction.

**4. Resume a task (single subagent).** Run `task "<topic>"`. Assemble a briefing for a fresh
agent: current state (done vs in-flight, from the latest sessions), what was done (condensed
history), key files (both edited artifacts and *read* files — the frequency lists guide you; list
concrete paths), and domain knowledge (decisions, constraints, gotchas; read the top-relevance
transcripts for exact detail). Output a clean handoff document.

**5. Find & reopen a past session (single subagent).** Run `search "<topic>" --since <recent
window> --json`. The JSON gives each match's `session` (id), `project` (path), and `t1` (last
activity). Pick by **recency among relevant matches**, not raw score. Beware: the single newest hit
is often the *current* session (it matches because this very conversation is about the topic) —
discount any session whose activity is happening right now or whose content is this meta-request.
Return a ready-to-paste command:

    cd <project-path> && claude --resume <session-id>

If two or three are plausible, list each with title / dir / time / id and give the command for the
best guess.

**6. Mine recurring corrections into CLAUDE.md rules (workflow).** Find the corrections the user
keeps giving — re-instructions, "no, do X instead," reverts, the same ask repeated across sessions —
and distill the recurring ones into CLAUDE.md rules. These corrections live in the raw transcripts
(the user's own turns following an agent action), so this is a fan-out + generate-and-filter +
adversarial-verify workflow:

- **Queue** — `report --since <window> --json` (or the last N sessions) for the session list.
- **Fan out (generate)** — one agent per session reads the raw `.jsonl` and extracts candidate
  corrections: places where the user redirected, rejected, or re-specified the agent's behavior.
  Each candidate cites the session and the turn.
- **Cluster & dedupe** — merge candidates into recurring themes across sessions; a one-off
  correction is not a rule.
- **Adversarially verify (filter)** — for each candidate rule, a *separate* skeptic agent asks:
  would this have prevented a *real, recurring* mistake? Is it already covered by existing
  CLAUDE.md? Is it so broad it would cause false positives? Keep only survivors. Bias the skeptic
  toward rejection — a smaller set of true rules beats a long list of noise.
- **Distill** — write the survivors as CLAUDE.md rules at the right scope (global vs project vs
  subdirectory). The skeptic above **is the verifier** and the filter's stop condition; add a rung-1
  deterministic check that each candidate isn't already in CLAUDE.md (grep it). Presenting the rules
  for approval before writing is a **typed gate**: interactive = ask inline; autonomous or scheduled
  = return BLOCKED and resume on the user's decision. Never write CLAUDE.md without that gate
  clearing.

## Output

Be concrete and concise. The digest the subagent returns is already grounded in real
sessions/dates/files — relay it without re-deriving or re-querying. If a digest comes back empty,
say so and dispatch again with a different phrasing or window rather than padding. Match the depth
of synthesis to the request. For workflows, honor a token budget if the user gives one, and prefer
cheaper models (Sonnet/Haiku) for the per-session reads.
