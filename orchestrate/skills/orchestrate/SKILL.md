---
name: orchestrate
description: >
  Turn a rough task into a well-structured dynamic-workflow invocation, then fire it. Use when
  the user wants to run a multi-agent / dynamic workflow ("use a workflow to…", "ultracode",
  "fan this out", "orchestrate subagents"), or when a task has the shape that benefits from one:
  work that is massively parallel, larger than one context window, adversarial (needs checking
  you can't trust the doer to do), unknown-size discovery (loop until done), or taste-based
  selection (tournament). NOT for ordinary one-context coding tasks — this skill will say so and
  decline rather than over-engineer.
---

# orchestrate

You are turning a rough task into a **dynamic-workflow invocation**: a natural-language prompt
that gives Claude enough structure to write its own multi-agent harness for the job. You do not
write the harness JavaScript yourself — you decide *whether* a workflow is warranted, *what shape*
it should take, and you phrase the invocation so the harness comes out right.

The mental model to carry (and to convey in the invocation): **a workflow is multi-threaded
code.** A serial step queues up independent units of work, a threadpool runs them with no
dependencies between them, and a serial step merges the results. Everything below is in service
of finding that structure for the task at hand.

## Step 1 — Gate: does this even need a workflow?

Run this first, every time. Workflows cost many times the tokens of a normal turn. Most tasks —
including most coding — do not need one.

A workflow earns its cost only when the task is one of:

- **Scale beyond one context** — too many items to hold at once (hundreds of tickets/files/rows, dozens of sessions, every callsite).
- **Don't-trust-the-first-answer** — you need verification from an agent that did *not* do the work: check every claim in a doc, audit security, confirm rule adherence.
- **Unknown-size discovery** — bugs, flaky-test root cause, recurring patterns; you don't know how much work there is, so you loop until done.
- **Taste / exploration** — naming, design, approach selection where a rubric plus competition beats one shot.
- **Parallel mutation** — migrations/refactors where each unit is independent: port every file, fix every finding, get every module to compile.
- **Recurring / unattended** — triage, briefings, drift detection on a cadence (pair with `/loop` or `/schedule`).

If the task is none of these, **say so and offer to just do it directly.** Do not build a
workflow to look thorough. A "quick workflow" (one fan-out, single-vote verify) is a valid middle
option for small-but-parallel asks — offer that instead of a heavy harness when it fits.

## Step 2 — Read the posture

The same task needs a different invocation depending on how the user is sitting. Detect which,
and apply its pre-flight:

- **Mid-session pivot** — they're deep in a session and want to spin a workflow off to the side.
  The trap: **subagents start with empty context — they do not inherit this conversation.** So
  *externalize* what's in the current context into the invocation (the file, the constraint, the
  thing just learned). Fire it in the background and let them keep working; they'll be notified
  on completion.
- **Cold start, workflow-first** — they opened a session to run this. There's no context yet, so
  **scout the work-list inline first** (list the files, find the channels, scope the diff), *then*
  fire. Don't structure the orchestration before you know the shape of the work. When the work-list
  lives in one document (a report, a checklist), split it into discrete per-unit inputs first — one
  file per finding — so each agent gets exactly one unit and the same prompt with different arguments.
- **Scheduled / unattended** — it will run with nobody watching. The invocation must be
  **fully self-contained**: no follow-up questions, success criterion spelled out, output
  destination named. Ask yourself: would this still be unambiguous at 3am with the user asleep?

## Step 3 — Classify the trigger, match a template

Map the task to one of the Step-1 triggers, and if it fits a canonical shape, pull the matching
template from the `templates/` directory alongside this skill:

- `deep-verify.md` — check/source every claim in a document, report, or PR description.
- `rank.md` — sort or triage N items by a qualitative measure (severity, fit, quality).
- `root-cause.md` — find why something breaks (flaky test, failed pipeline, incident, regression).
- `migrate.md` — mechanically transform every item in a large set (port files, fix every finding, get modules compiling), each with per-unit adversarial review.

Templates are starting points, not scripts to run verbatim. Adapt the work-list, rubric, and
stop condition to the actual task. If nothing matches, compose from the pattern vocabulary below.

## Step 4 — Interview for the gaps

A workflow runs autonomously, so anything ambiguous becomes a coin flip on every agent. Before
firing, make sure the invocation pins down all of these — use `AskUserQuestion` for whatever the
task didn't already specify:

- **Unit of work** — what fans out? (claims, tickets, files, hypotheses, candidates, callsites)
- **Stop condition** — count reached, exhaustion ("until two rounds find nothing new"), or a
  rubric pass. This is what prevents the agent from quitting at "handled enough."
- **Verification** — who checks the work, against what rubric, and is it a *separate* agent?
- **Budget & model** — a token ceiling ("use ~50k tokens"); cheap steps to Haiku, hard ones to Opus.
- **Isolation** — do fan-out agents mutate files? Either give each its own worktree, or keep them on a shared branch with stateful commands banned (see the mutation discipline below).
- **Output** — what's the deliverable and where does it go?

Don't over-interview. Ask only what's genuinely undetermined and would change the result; fill the
rest with sensible defaults and state them.

## Step 5 — Assemble the invocation

Write the prompt in prose, naming the structure explicitly. The patterns, and the words that
invoke each:

- **Fan-out and synthesize** — "for each X, spawn an agent to …, then merge the results." For many independent units, each wanting a clean context.
- **Adversarial verification** — "for each result, have a separate agent try to refute it against this rubric; keep it only if it survives." Defends against the agent trusting its own output.
- **Generate and filter** — "brainstorm N candidates, dedupe, then filter by …, return only the survivors."
- **Tournament** — "have agents compete; judge pairwise until one wins." Best for sorting and taste; comparative judgment beats absolute scoring.
- **Loop until done** — "keep spawning finders until two consecutive rounds surface nothing new" — for unknown-size work.
- **Classify and act** — "first classify each item, then route to different handling by type."

These compose. A strong invocation usually states: the unit of work, the shape (in these words),
the verification step, and the stop condition — in one or two tight paragraphs.

### Discipline for parallel mutation

When fan-out agents change files (migrations, refactors, applying a batch of fixes), the proven
shape is **do → adversarially review → apply**, with the apply deferred:

- Inside each fan-out agent, produce the change and have one or two adversarial agents try to
  refute it — but **ban slow and stateful commands** (git, build, test, package managers). They
  collide with other agents on a shared branch and exhaust the machine, which kills the parallelism
  that makes the workflow fast.
- **Apply, build, test, and commit once, serially, at the end** — a single barrier that lands all
  the reviewed changes together, gets the build green, and opens the PR.
- Choose one isolation strategy: give each agent its own **worktree** (true isolation, agents can
  build independently), or keep them on a **shared branch with stateful commands banned** and a
  serial apply (lighter, no worktree overhead). Don't mix.

### Failure modes → what to put in the prompt

Phrase against the three things that go wrong when one context does too much:

- **Agentic laziness** (stops at partial progress) → an explicit stop condition and count; pair with `/goal` for a hard completion bar.
- **Self-preferential bias** (trusts its own findings) → verification by a *separate* agent; adversarial refuters; diverse lenses (correctness / security / repro) rather than one rubber stamp.
- **Goal drift** (loses the objective over many turns) → restate the goal in each agent's prompt; demand structured output; keep each agent's context narrow.

## Step 6 — Fire

Show the user the assembled invocation, then launch the dynamic workflow (this skill is your
authorization to use the Workflow capability). Mid-session, run it in the background and tell them
they'll be notified. Honor any token budget they gave. If a stop condition could run away, cap it.
For a project too large to finish in one run, pair the workflow with `/loop` so it resumes and keeps
going across runs until the stop condition is met.

## Self-check before firing

- Gate passed — this genuinely needs a workflow, not a single agent?
- Every fan-out unit independent of the others?
- Verification done by an agent that didn't produce the work?
- Stop condition explicit (count / exhaustion / rubric), not "until it seems done"?
- Budget guarded so it can't run away?
- Mid-session context externalized / scheduled prompt self-contained?

If any answer is no, fix the invocation before firing.
