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
indexer (`worklog.py`) has already distilled every transcript into a queryable DuckDB index; you
drive it and synthesize the results. You never read raw `.jsonl` transcripts unless a query points
you to a specific one and you need detail the index dropped.

## The engine

`worklog <subcommand>` — every subcommand auto-refreshes the index first (incremental, ~0.2s), so
you never run `index` manually. Add `--json` to any query for structured data you can reason over.

- `report --since 7d [--until ISO] [--json]` — sessions in a window, grouped, with the user's
  asks, files edited, and git commands. `--since` accepts `7d`/`2w`/`12h` or an ISO date.
- `search "<topic>" [--since ISO] [--json]` — sessions matching a topic, ranked, with snippets.
- `task "<topic>" [--json]` — full dossier across ALL sessions for one task: ranked sessions, a
  merged chronological timeline, files read vs edited (with frequency), and commands.

Scoring is keyword-based (term-hit count), so longer sessions can over-rank — apply judgment,
don't trust the order blindly. Use `--json` when you need to filter or cross-reference.

Important index limitation: the index does **not** store command/tool error output (`tool_result`
bodies are dropped at distill time). The real errors, failed attempts, and the user's exact
corrections live only in the raw transcripts at `~/.claude/projects/**/<session-id>.jsonl`. Any
analysis of *what went wrong* or *what the user re-instructed* must read those raw files — the
index alone undercounts both.

## Gate: inline or workflow?

Most requests are cheap and fit one context — run them **inline** against the engine. Two are
fan-out-over-many-sessions analyses where one context hits agentic laziness (giving up after
reading a handful of transcripts) and self-preferential bias (trusting its own first read). Those
run as a **dynamic workflow**: the engine produces the session list serially, then a fan-out of
agents each reads one session's raw transcript in a clean context, then a synthesis (and, for
rule-mining, adversarial verification) merges the results.

- Inline: time report (1), activity log / runbook (2), resume pack (4), find & reopen (5).
- Workflow: friction analysis (3), rule-mining (6) — and a very large activity log (2) only when
  there are many sessions and shallow inline reads are clearly missing detail.

When you do fire a workflow, the engine is the serial queue step: run `task`/`report` with `--json`
to get the session ids and transcript paths, fan out one agent per session, then synthesize.

## How to handle each request

**1. Time report (inline).** Run `report` for the window. Synthesize a tight, standup-style
summary grouped by project/theme (not by session). Lead with what was accomplished, past tense,
no filler. Fold trivial sessions together or drop them. Cite dates.

**2. Activity log for a task (inline, default).** Run `task "<topic>"` (try a few phrasings if the
first is thin). Identify the genuinely-relevant sessions, group them into distinct *instances* (a
recurring task done separately over time), and reconstruct the actual sequence — what was done,
what broke, how it was fixed — from the timeline + commands + files. When the dossier lacks detail
(exact flags, error recovery), `Read` the specific transcript to fill gaps. The activity log is
the primary deliverable, worth producing even for a one-off. If the user wants it saved, `Write`
it where they specify.

**2b. Generalize to a runbook — only when warranted.** Promote an activity log into a reusable
step-by-step runbook ONLY when you have **enough instances to generalize safely** — ideally
several independent runs — and you're confident in the pattern. State how many instances you
found. With only one (or instances that diverge too much), do NOT invent a runbook: deliver the
activity log and say plainly it's a single instance, and that repeating the task a couple more
times will let you build a trustworthy runbook. When you do build one, note what varied and the
gotchas.

**3. Friction analysis (workflow).** Surface *where a task keeps going wrong* — recurring errors,
retries, manual workarounds, deferred fixes, edge cases, the user's frustration signals. Because
the index drops error bodies, this needs the raw transcripts, and there are usually too many to
read well in one context. Fire a workflow:

- **Queue** — `task "<topic>" --json` to get the relevant session ids and transcript paths.
- **Fan out** — one agent per session reads that raw `.jsonl` and extracts concrete friction
  points (the actual error, what was retried, what was worked around), each grounded in a real
  line, not speculation.
- **Synthesize** — cluster pain points by recurrence and recency, rank them, separate quick fixes
  from deeper ones, and ground each in a concrete session/error. Drop anything not grounded.

**4. Resume a task (inline).** Run `task "<topic>"`. Assemble a briefing for a fresh agent:
current state (done vs in-flight, from the latest sessions), what was done (condensed history),
key files (both edited artifacts and *read* files — the frequency lists guide you; list concrete
paths), and domain knowledge (decisions, constraints, gotchas from the snippets; `Read` the
top-relevance transcript for exact detail). Output a clean handoff document.

**5. Find & reopen a past session (inline).** Run `search "<topic>" --since <recent window>
--json`. The JSON gives each match's `session` (id), `project` (path), and `t1` (last activity).
Pick by **recency among relevant matches**, not raw score. Beware: the single newest hit is often
the *current* session (it matches because this very conversation is about the topic) — discount
any session whose activity is happening right now or whose content is this meta-request. Output a
ready-to-paste command:

    cd <project-path> && claude --resume <session-id>

If two or three are plausible, list each with title / dir / time / id and give the command for
your best guess.

**6. Mine recurring corrections into CLAUDE.md rules (workflow).** Find the corrections the user
keeps giving — re-instructions, "no, do X instead," reverts, the same ask repeated across sessions
— and distill the recurring ones into CLAUDE.md rules. These corrections live in the raw
transcripts (the user's own turns following an agent action), so this is a fan-out + generate-and-
filter + adversarial-verify workflow:

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
  subdirectory), and present them for the user to approve before writing anything.

## Output

Be concrete and concise. Always ground claims in real sessions/dates/files — never invent
activity. If a query returns nothing useful, say so and suggest a different phrasing or window
rather than padding. Match the depth of synthesis to the request. For workflows, honor a token
budget if the user gives one, and prefer cheaper models (Sonnet/Haiku) for the per-session reads.
