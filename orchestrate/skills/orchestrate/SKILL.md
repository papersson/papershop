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

You turn a rough task into a **dynamic-workflow invocation**: a natural-language prompt that gives
Claude enough structure to write its own multi-agent harness. You do not write the harness
JavaScript — you decide *whether* a workflow is warranted, *what shape* it takes, and you phrase
the invocation so the harness comes out right.

Two mental models, held together:

- **A workflow is multi-threaded code.** A serial step queues independent units, a threadpool runs
  them with no dependencies between them, a serial step merges the results.
- **A workflow is a graph of typed nodes** — workers, barriers, loops, gates — built by composing a
  few primitives, **parameterized by interaction mode** (interactive vs autonomous), with
  **verification-first as the spine**: you write the check that proves the task is done before you
  pick any shape, and the workflow is finished when that check passes, not when the agents stop.

The gate (Step 1) stays the first and loudest thing. Everything this skill adds — the topology
catalog, the verifier machinery — is a ladder the gate authorizes climbing, never a default to reach
for. Most warranted workflows are a single fan-out plus one verify node.

## Step 1 — Gate: does this even need a workflow?

Run this first, every time. Most tasks, including most coding, do not need a workflow.

A workflow earns its cost only when the task is one of:

- **Scale beyond one context** — too many items to hold at once (hundreds of tickets/files/rows, dozens of sessions, every callsite).
- **Don't-trust-the-first-answer** — you need verification from an agent that did *not* do the work: check every claim in a doc, audit security, confirm rule adherence.
- **Unknown-size discovery** — bugs, flaky-test root cause, recurring patterns; you don't know how much work there is, so you loop until done.
- **Taste / exploration** — naming, design, approach selection where a rubric plus competition beats one shot.
- **Parallel mutation** — migrations/refactors where each unit is independent: port every file, fix every finding, get every module to compile.
- **Recurring / unattended** — triage, briefings, drift detection on a cadence (pair with `/loop` or `/schedule`).

If the task is none of these, **say so and offer to just do it directly.** Do not build a workflow
to look thorough. A "quick workflow" (one fan-out, single-vote verify) is a valid middle option for
small-but-parallel asks. The richer catalog and verifier machinery below are opt-in escalation, not
defaults; passing the gate authorizes the *simplest* topology that fits.

## Step 2 — Define the verifier first

The spine. Before posture or shape, answer: **what prompt, command, or test, run by an agent that
did not do the work, decides this task is done?** Make passing it the goal, and derive the stop
condition and the verify nodes from it. Produce three artifacts:

1. **The verifier** — the concrete check. ("Every claim has a supported/refuted verdict with a
   file:line." "The build is green and these tests pass." "A fresh reader can't find an AI tell.")
2. **Hard or soft** — pass/fail boolean (compiles, tests, a tool confirms render), or taste (is this
   explanation good), which needs a rubric plus an adversarial panel and **must never be faked as a
   green check**. Be honest when something is only softly verifiable.
3. **The signal rung** — climb the **signal hierarchy** and take the highest rung with ground truth:
   1. **deterministic** — tests, types, lint, build, a regex, or a *tool the agent drives*
      (agent-browser, `/verify`, `/code-review`). Prefer a tool/command over an LLM judge whenever
      ground truth exists.
   2. an installed **domain verification-harness** skill.
   3. an **adversarial-LLM rubric**.
   4. a **human gate**.

Apply three guards inline. **Goodhart:** once "pass the verifier" is the goal, the agent overfits;
keep the verifier adversarial and outcome-focused, not a gameable checklist, and hide its internals
from the doer where you can. **Verify the verifier:** one quick pass — would it fail a known-bad
input and pass a known-good one? A weak verifier is worse than none. **Mode constraint:** if the run
will be autonomous (Step 3), rung 4 compiles to a BLOCKED return, not a live question — don't spec a
verifier that assumes mid-run interactivity you won't have.

A sharp verifier is the strongest anti-over-engineering force here: once the check is precise, ask
"does a single agent driving this verifier already suffice?" If yes, **decline the workflow.**
Verifier-first shrinks topologies more often than it grows them.

The verifier also outlives the run: it is what the report (Step 8) hands the human to re-check the
work, so phrase it as something a person can actually paste and re-run — a named command with an
expected result — not just an internal gate.

## Step 3 — Read the posture, set the interaction mode

Detect the posture and apply its pre-flight:

- **Mid-session pivot** — subagents start with empty context; they do not inherit this conversation.
  *Externalize* what's in your head (the file, the constraint, the thing just learned) into the
  invocation. Fire in the background; they'll be notified.
- **Cold start, workflow-first** — no context yet, so **scout the work-list inline first**, then
  fire. When the work-list lives in one document, split it into per-unit inputs first (one file per
  finding) so each agent gets one unit and the same prompt with different arguments.
- **Scheduled / unattended** — runs with nobody watching; the invocation must be **self-contained**:
  no follow-up questions, success criterion and output destination spelled out.

Then set an explicit **interaction mode**: `interactive` (a human is available during the run) or
`autonomous` (backgrounded, scheduled, or "just go"). It defaults from posture (mid-session/cold =
interactive, scheduled = autonomous) but is overridable, and it sets every gate node's behavior
(Step 6). Posture is about context availability; mode is about whether a human can answer mid-run —
keep them distinct.

## Step 4 — Front-load the interview

A workflow runs without you, and a backgrounded run can't come back to ask, so resolve
outcome-*changing* ambiguity now via `AskUserQuestion`. Triage with one bar (reused for blocking in
Step 6): escalate only what (a) can't be decided from the brief, (b) materially changes the outcome,
and (c) is costly to reverse. Below the bar, pick a sensible default and state it — not a question,
and not a mid-run block later.

Pin down: the **unit of work** (what fans out), the **output** (deliverable and destination), and
**isolation** (do fan-out agents mutate files?). The stop condition and verification already come
from Step 2 — don't re-derive them; point back at the verifier.

## Step 5 — Select and wire the topology

Compose from typed **node primitives**:

- **worker** — does one unit. Fields: role, input contract, output schema (must include the BLOCKED variant), model, retry policy.
- **barrier** — a `parallel()`/synthesis join that awaits all and merges. The **only** place stateful/git/build/test commands run.
- **loop** — do → check → revise around a body. Carries three mandatory fields or it is malformed (below).
- **gate** — a typed human-decision node; behavior set by interaction mode (Step 6).
- **diamond** — fan-out then converge at one barrier.
- **scatter-gather** — map a heterogeneous unit-list to workers, gather verdicts.
- **report** — terminal node of a non-trivial graph: reads the run manifest and writes a self-contained, pedagogical HTML report that foregrounds the *task and its outcome* (orchestration machinery subordinate) and lets the human verify it. Scaled to the work; a trivial map+barrier skips it for a one-line verdict. See Step 8 and `templates/report.md`.

A node's **output contract is the next node's input contract** — that is what lets primitives nest.
The named compounds are built from these: fan-out+synthesize (diamond), adversarial-verify (worker →
separate refuter → loop/gate), generate-and-filter, tournament, loop-until-done, classify-and-act.
They nest: a pipeline whose stages are fan-out→verify diamonds; a tournament whose comparison node is
an adversarial panel. The `templates/` files (`deep-verify`, `rank`, `root-cause`, `migrate`) are
worked instances — adapt them. Spell out per-node wiring fields only when composing across a boundary
or when the graph is non-trivial; a two-agent fan-out doesn't need a written schema.

**Every loop node carries three fields or it is malformed:**

1. **Signal** — the verifier from Step 2 (one concept, not two), at its hierarchy rung.
2. **Stop condition** — concrete, derived from the verifier (count / convergence / threshold, e.g. "two consecutive clean passes"). Ends when the verifier passes, not when agents tire.
3. **Divergence guard** — detect oscillation (fixing A breaks B) with a checkable diff/hash between rounds, cap iterations, and **on cap escalate** (emit BLOCKED or surface the honest best attempt) rather than silently shipping the last try.

**The one-barrier rule for mutation:** every fan-out converges at exactly one barrier where stateful
work happens; inside fan-out, git/build/test/package-managers are banned (they collide on a shared
branch and exhaust the machine); pick one isolation strategy — worktree-per-agent OR
shared-branch-with-stateful-banned — never mixed. A "quarantined worker" is just a worker plus that
ban, not a new primitive.

**Phrase against the three failure modes:** agentic laziness → the explicit stop condition from
Step 2, pair with `/goal`; self-preferential bias → verification by a *separate* agent, adversarial
refuters, diverse lenses; goal drift → restate the goal in each agent's prompt, demand structured
output, keep contexts narrow.

Selection discipline: **simplest graph that fits.** One primitive is a valid topology. Escalate only
when the task earns it.

## Step 6 — The blocking model

Subagents are headless: they return data, they cannot prompt the human, and `AskUserQuestion` is
unavailable to them. So "return to the human at a decision point" is a **state, not an interaction.**
Every worker can emit:

```
{ status: BLOCKED, decision_needed, options[], why_cannot_proceed, work_already_done }
```

A real handoff, never a guess dressed as progress. Distinguish **BLOCKED** (needs a human;
halt-and-surface) from **FAILED** (item errored; drop-and-continue or retry per policy). A BLOCKED on
the **critical path** is fail-fast: halt that branch/run immediately; do **not** keep spending, do
**not** fabricate-and-continue, do **not** finish-everything-then-confess. Independent branches
already in flight may finish. Then **return early** with the block surfaced; the main interactive
loop brings it to the human via `AskUserQuestion`; the run **resumes via `resumeFromRunId`** so the
cached prefix replays instantly and only the unblocked tail runs live.

**Resume-cache rule** (not a footnote): resume is cheap only when the human's decision *unlocks a new
branch* without changing inputs to already-cached nodes. If the decision changes the brief or an
upstream input, the affected nodes must be **re-run, not replayed from cache** — otherwise resume
serves silently stale results, the exact fabricate-and-continue failure this protocol prevents.

A **gate** is a typed node whose behavior follows the interaction mode: `interactive` = ask inline
before proceeding; `autonomous` = emit BLOCKED and return. Edge case: an interactive run whose human
has gone (terminal closed, session timed out) must still emit BLOCKED at a gate rather than hang.

## Step 7 — Render (conditional) and fire

If the graph is **non-trivial** (more than one node type, or it contains a loop or a gate), print it
before firing: nodes, edges, barriers, loops (with their signal + stop + guard), gates (with their
mode), and the estimated agent count — for approval or trim. A graph that looks oversized for the
task is the cue to drop down or decline. A plain map+barrier skips render; the assembled invocation
already shows its shape.

Then show the invocation and fire (this skill is your authorization to use the Workflow capability).
Mid-session, run in the background and say they'll be notified. Honor any token budget; cap runaway
loops. Pair with `/loop` for a project too large for one run. Instruct the harness to emit BLOCKED on
the critical path and return early rather than push past a real decision.

## Step 8 — Report the work (open the black box)

A non-trivial workflow runs dozens of agents the human never sees, then hands back a deliverable with
the *how* and the *why-trust-it* locked in transcripts. The terminal **report node** unlocks both:
after the verifier passes, one barrier reads the run manifest and writes a single self-contained HTML
file (inline CSS + SVG, zero external requests) beside the deliverable.

**It is a report about the work, not about the workflow.** The reader's first question is "what
happened to *my* problem, and is it right?" — not "how did your agents coordinate?" So the task and
its concrete outcome **lead and dominate**: what was asked, what was actually done (the real diffs /
findings / answer, each carrying its `file:line` provenance), how to verify it, and what still needs a
human call. The orchestration machinery — topology diagram, why-this-shape, agent/token/model
accounting — is demoted to **one compact, collapsible "How this was produced" section** near the end,
present for trust and the curious, never the spine. The topology earns its place only as evidence the
result is trustworthy. The pedagogy owed is **task-pedagogy** (teach what the *task* required), not a
tour of the harness.

Two jobs, both from the spine: **teach** (a teammate who didn't watch can follow the work and learn
how each case was handled) and **verify** (surface the Step-2 verifier and its verdict *attributed to
the separate node that ran it*; print the exact re-run command plus a completeness/residual command
whose expected count equals the deliberately-excluded items; link every claim to `file:line`).
Verification-honest: a BLOCKED/sampled/capped result is shown as such with a scope caveat and a resume
handle (worktree path + branch + "retries: 0 by design"), never repainted green.

It needs material, so nodes **accumulate a run manifest** as they go — task + outcome, the substantive
findings with provenance, the verifier + verdict + rung, the exception ledger, and accounting. Scaled
to the work: on for non-trivial runs; **a trivial map+barrier emits a one-line verdict instead**;
richness tracks run size; overridable. Diagrams use the Anthropic-minimal outline-only style. And
because it's frontend, it self-verifies on the deterministic rung — drive `agent-browser` (start at
`--help`) to confirm it renders, is self-contained (HAR shows one request), diagrams are visible and
unclipped at ~390px and 1280px, and the console is clean; a failing check is a blocking defect, not a
warning. Full contract, the task-first section order, and a render-verified reference implementation:
`templates/report.md` and `templates/report.example.html`.

## Self-check before firing

- Gate passed — this genuinely needs a workflow, not a single agent driving the verifier?
- Verifier defined first, and the stop condition derived from it (done = verifier passes)?
- Signal on the highest available rung (a tool over an LLM judge where ground truth exists)?
- Every fan-out unit independent; every loop has signal + stop + divergence guard?
- Every gate has a mode set by the interaction mode?
- Critical-path BLOCKED wired to fail-fast + return + resume, with the resume-cache rule honored?
- Topology rendered (if non-trivial) and no bigger than the task earns?
- Mid-session context externalized / scheduled prompt self-contained?
- Non-trivial run — report node appended, **task-first** (the work leads, machinery in a subordinate aside), verdict attributed to the separate verifier, self-verified with agent-browser (trivial map+barrier emits a one-line verdict)?

If any answer is no, fix the invocation before firing.
