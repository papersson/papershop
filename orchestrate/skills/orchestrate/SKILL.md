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

The gate (Step 1) stays the first thing — but its job is to decide *whether* a workflow is warranted
at all, and it still turns trivial work away. Once a task is through the gate, the bias flips: a
workflow is the moment to **spend inference-time compute well**, so feedback loops, adversarial
verification, and diverse lenses are the defaults, not opt-in escalations. The discipline is not
*fewer nodes* — it is that **every node earns decorrelated signal** (independent verification,
diversity, or adversarial pressure); compute that just repeats the same doer buys nothing. Reach for
the richest topology whose every node clears that bar.

## Step 1 — Gate: does this even need a workflow?

Run this first, every time. Most tasks, including most coding, do not need a workflow.

A workflow earns its cost only when the task is one of:

- **Scale beyond one context** — too many items to hold at once (hundreds of tickets/files/rows, dozens of sessions, every callsite).
- **Don't-trust-the-first-answer** — you need verification from an agent that did *not* do the work: check every claim in a doc, audit security, confirm rule adherence.
- **Unknown-size discovery** — bugs, flaky-test root cause, recurring patterns; you don't know how much work there is, so you loop until done.
- **Taste / exploration** — naming, design, approach selection where a rubric plus competition beats one shot.
- **Parallel mutation** — migrations/refactors where each unit is independent: port every file, fix every finding, get every module to compile.
- **Recurring / unattended** — triage, briefings, drift detection on a cadence (pair with `/loop` or `/schedule`).

If the task is none of these, **say so and offer to just do it directly.** The gate is real:
genuinely trivial work should not be wrapped in a harness. But the gate is a threshold, not a dial
toward minimal — **passing it authorizes the richest topology whose every node earns decorrelated
signal** (Step 5), not the thinnest one that technically works. A "quick workflow" (one fan-out,
single-vote verify) is the floor for a small-but-parallel ask, not the target for a hard one.

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

A sharp verifier still settles the gate: if a single agent driving this verifier already suffices and
the task is trivial, **decline the workflow.** But once a workflow *is* warranted, the verifier is
something to **layer, not minimize** — adversarial refuters, diverse lenses, and do→verify→revise
loops around it are how spent tokens become correctness. A precise verifier tells you *what* done
means; it is not an argument for the fewest nodes that reach it.

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

A workflow runs without you, and a backgrounded run can't come back to ask, so resolve ambiguity
**now**, before firing — and how freely you ask depends on interaction mode. **Interactive:** a
workflow is expensive enough that a clarifying question is almost always cheaper than a misframed run,
so ask via `AskUserQuestion` whenever the brief leaves *reasonable* ambiguity about scope, the unit of
work, or what "done" means — not only when it is outcome-changing and irreversible. **Autonomous /
scheduled:** you can't ask mid-run, so apply the strict bar — escalate only what (a) can't be decided
from the brief, (b) materially changes the outcome, and (c) is costly to reverse; below it, pick a
sensible default and state it. Either way the questions are front-loaded here so the run never blocks
on something you could have asked first.

Pin down: the **unit of work** (what fans out), the **output** (deliverable and destination), and
**isolation** (do fan-out agents mutate files?). The stop condition and verification already come
from Step 2 — don't re-derive them; point back at the verifier.

## Step 5 — Select and wire the topology

Compose from typed **node primitives**:

- **worker** — does one unit. Fields: role, input contract, output schema (must include the BLOCKED variant), model, retry policy.
- **barrier** — a `parallel()`/synthesis join that awaits all and merges. The **only** place stateful/git/build/test commands run.
- **loop** — do → check → revise around a body. Carries four mandatory fields or it is malformed (below).
- **gate** — a typed human-decision node; behavior set by interaction mode (Step 6).
- **diamond** — fan-out then converge at one barrier.
- **scatter-gather** — map a heterogeneous unit-list to workers, gather verdicts.
- **report** — terminal node of essentially every workflow (skipped only for an extremely-trivial single-agent run): reads the run manifest and writes a self-contained, pedagogical HTML report that foregrounds the *task and its outcome* (orchestration machinery subordinate) and lets the human verify it. Scaled to the work; only an extremely-trivial single-agent run drops to a one-line verdict. See Step 8 and `templates/report.md`.

A node's **output contract is the next node's input contract** — that is what lets primitives nest.
The named compounds are built from these: fan-out+synthesize (diamond), adversarial-verify (worker →
separate refuter → loop/gate), generate-and-filter, tournament, loop-until-done, classify-and-act.
They nest: a pipeline whose stages are fan-out→verify diamonds; a tournament whose comparison node is
an adversarial panel. The `templates/` files (`deep-verify`, `rank`, `root-cause`, `migrate`) are
worked instances — adapt them. Spell out per-node wiring fields only when composing across a boundary
or when the graph is non-trivial; a two-agent fan-out doesn't need a written schema.

**Every loop node carries four fields or it is malformed:**

1. **Signal** — the verifier from Step 2 (one concept, not two), at its hierarchy rung.
2. **Stop condition** — concrete, derived from the verifier (count / convergence / threshold, e.g. "two consecutive clean passes"). Ends when the verifier passes, not when agents tire.
3. **Divergence guard** — detect oscillation (fixing A breaks B) with a checkable diff/hash between rounds, cap iterations, and **classify every failure as transient or permanent**: a permanent/unrecoverable error (a server-side `*Failed`, an eligibility/quota/subscription denial, a 4xx that won't change on retry) **breaks the loop and emits BLOCKED at once** — never grind a create→fail→delete→recreate retry against it, since a cap alone will burn the whole budget thrashing on something no retry can fix. And **any loop or serial chain that depends on an external platform (deploy, provision, onboard, partner-model access) must be gated behind a cheap parallel preflight probe** — a dry-run deploy, a capability/eligibility/quota check — that proves feasibility in seconds *before* the expensive body fires; a failed probe returns BLOCKED instead of committing the chain. **On cap, on a failed preflight, or on a permanent failure, escalate** (emit BLOCKED or surface the honest best attempt) rather than silently shipping the last try or thrashing.
4. **Binding verdict — the corrective arm is not optional.** A non-passing verdict (`needs_revision`, unsupported claims, below threshold) *fires the fix→re-verify body and re-runs the verifier*; the loop is self-driving and the run **may not terminate while the verdict is non-sound**. A verifier that returns `needs_revision` with zero fix rounds is a **malformed run, not a result** — the expensive adversarial pass must buy enforced correction, never a flagged opinion left for the human to reconcile by hand. The body re-runs until `verdict == sound` or the cap escalates (field 3); a one-shot finish on a failing verdict is the bug, not the design. Where adversarial lenses produce a synthesized output, that synthesis is itself a doer and needs its own verify→fix loop — lenses that flag are not a substitute for a verdict that is validated and looped.

**The one-barrier rule for mutation:** every fan-out converges at exactly one barrier where stateful
work happens; inside fan-out, git/build/test/package-managers are banned (they collide on a shared
branch and exhaust the machine); pick one isolation strategy — worktree-per-agent OR
shared-branch-with-stateful-banned — never mixed. A "quarantined worker" is just a worker plus that
ban, not a new primitive.

**Phrase against the three failure modes:** agentic laziness → the explicit stop condition from
Step 2, pair with `/goal`; self-preferential bias → verification by a *separate* agent, adversarial
refuters, diverse lenses; goal drift → restate the goal in each agent's prompt, demand structured
output, keep contexts narrow.

Selection discipline: **the most expressive graph whose every node earns decorrelated signal.**
Default to the load-bearing topological ideas — feedback loops (do→verify→revise), adversarial loops
(a separate agent trying to refute), and diverse lenses (the same unit seen N independent ways) —
rather than treating them as escalations. One primitive is a valid topology for a small ask; a hard
one should *use* these patterns, not ration them. Trim only nodes that add no signal (redundant
doers, theater) — never trim verification or diversity to look lean.

**Best-of-N is a lever, not redundant doing.** "Repeating the same doer buys nothing" rules out naive
self-consistency — N identical calls voting on themselves — but not its productive cousin: a
**temperature-diversified candidate pool** generated wide, then narrowed by a *separate* selector. The
decorrelation comes from sampling diversity (varied temperature, seeds, or framing lenses) plus an
independent judge, not from re-running one prompt. It earns its tokens when the task is taste-based or
admits many viable forms (naming, outline, structure, narrative, draft), the candidates are genuinely
different rather than paraphrases, and a separate node scores them on a rubric and actually filters.
Set **N deliberately and scale it to the size of the design space**: a handful of ad-hoc candidates
under-samples a large one — for high-taste work over-generate (N≈8–12) behind a **hard selection bar**
(top-k or a score threshold, expect to cut) rather than a lenient judge that passes everything. A
selector that never rejects is theater; tune the bar until the over-generation pays.

**Default magnitudes — what "rich" and "wide" actually mean.** "Richest topology" and "scale fan-out
width to what discovery finds" need an operational floor, or every run silently lands thin. Take these
as defaults — scale *up* on discovery, *down* only with a stated reason:

- **Fan-out width** — ≥ one agent per discovered unit (file / finding / claim / section). Never batch independent units into one agent to look lean: 40 findings is 40 doers, not 8 doing 5 each.
- **Independent lenses** — ≥ 3 when the same unit is seen N ways (diverse-lens, design/naming exploration); more when the call is high-stakes or taste-driven.
- **Adversarial verification** — ≥ 1 separate refuter per claim; for soft/taste verdicts a panel of ≥ 3 voters (odd, to break ties). A single LLM judge is the floor only for hard, deterministic-rung checks.
- **Tournament** — a bracket of ≥ 4 candidates for taste/selection; fewer is not a tournament.
- **Verifier-to-doer ratio** — budget roughly **one verify agent per doer** for don't-trust-the-first-answer work (each unit gets its own checker), not one verifier auditing the whole batch; a shared verifier is acceptable only for cheap deterministic gates.

These compose multiplicatively: 7 candidates × 4 claims × 3 votes is ~84 verify agents — the *expected*
magnitude for a deep-verify run, not an overrun. A hard task whose graph lands under ~15–20 agents is
the cue to check whether width or verification was silently rationed, not a sign of a tidy plan.

**Prefix caching is the spend amplifier — front-load one shared, cacheable contract.** A wide or deep
fan-out is affordable only when the heavy front-matter (purpose, vocabulary, framings, schemas, prior
verified findings) is written **once as a stable prefix** and replayed across every worker, not
re-sent per agent. Zero-context subagents force this anyway — everything load-bearing must live in the
prompt — so make that contract the *first, identical, byte-stable* block of every worker, and put the
variable unit-input strictly *after* it, never interleaved. Then prefix caching amortizes the contract
across the width: a 14+14 drafter/harmonizer fan-out pays for it roughly once, not 28 times, which is
what lets you afford the most-expressive graph above rather than rationing it to dodge per-agent
context cost. Carry established results across runs the same way: inject a prior run's verified findings
as a "fold in, do not re-derive" prefix so the next phase doesn't re-spend agents rederiving what an
earlier run already proved. Account for this in the agent/token envelope you render at Step 7
(cached-prefix vs live tokens), and note it composes with the resume-cache rule (Step 6): same
mechanism — a stable prefix replayed cheaply — applied across the fan-out instead of across a resume.

**Dynamic shape — the graph is code, not a frozen DAG.** When the work-list or the difficulty isn't
known up front, don't fix the topology at launch. Encode decision points where intermediate results
choose what runs next: scout first and **scale fan-out width to what discovery finds**; **escalate on
a finding** (a low-confidence verdict spawns a panel; a failing unit spawns a root-cause loop); **loop
until a signal**, not for a fixed count. For work too large or too uncertain for one shot, **chain
workflows** — run a phase, read its manifest, author the next phase from what you learned, staying in
the loop between fan-outs. This reconciles with the approval gate (Step 7): the human signs off on the
**strategy, the decision rules, and the bounds** (caps, budget, escalation thresholds), not on a node
count that is meant to change — though a newly-authored phase that changes the strategy re-renders and
re-approves in interactive mode; only in-bounds adaptation runs without a fresh go.

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

## Step 7 — Render, get approval, then fire

**Always render the plan before firing.** Print the strategy in a sentence, then the topology — nodes,
edges, barriers; loops with their signal + stop + guard; gates with their mode; and the adaptive
decision points with their bounds — plus the estimated agent/token envelope. A node that earns no
decorrelated signal is the cue to drop a rung; a hard task whose graph looks thin is the cue to add a
feedback or adversarial loop.

**Then stop for approval — a hard gate in interactive mode.** Present the plan and **wait for an
explicit go** before spending anything; never render-and-fire in one motion. Even when nothing needed
clarifying, a one-line "here's the shape and the cost — launch it?" is required. The human may trim,
redirect, or approve.

**The plan you render is already the heavy one.** Default to the deep, research-fronted, many-agent
shape the task warrants — sized by signal, not caution. The gate exists for the human to dial *down*,
never for you to under-spec and wait to be licensed up: do **not** render a safe ~7–18-agent shape on
the theory they'll ask for more if they want it. "Spend more tokens / use more agents" is something
you should never make the user say — warranted depth is the default and the approval is permission to
*trim*. A thin plan for a hard task is a defect to fix before rendering, not a conservative starting
bid.

Only an **autonomous / scheduled** run skips this gate (no human to ask), and such a run must be
self-contained per Step 3. Because dynamic shapes change mid-run, what gets approved is the **strategy
+ decision rules + bounds**, not a frozen node count.

On approval, fire (this skill is your authorization to use the Workflow capability). Mid-session, run
in the background and say they'll be notified. Honor any token budget; cap runaway loops. Pair with
`/loop` for a project too large for one run. Instruct the harness to emit BLOCKED on the critical path
and return early rather than push past a real decision.

## Step 8 — Report the work (open the black box)

Almost every workflow earns a report — its agents are invisible and the *why-trust-it* is locked in
transcripts nobody reads — so the default is **on**, scaled to the run (a short report for a simple
one, a full one for a rich one); skip it only for the *extremely* trivial single-agent case. After the
verifier passes, one barrier reads the run manifest and writes a single self-contained HTML file
(inline CSS + SVG, zero external requests) to **`/tmp/orchestrate-reports/<name>-<runid>.html`** — the
report is a run artifact, not a repo deliverable, so it lives in /tmp and never clutters the working
tree.

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
to the work: full for rich runs, a **short HTML report** for simple ones; only an *extremely trivial*
single-agent run drops to a one-line verdict. Richness tracks run size; overridable. Diagrams use the
Anthropic-minimal outline-only style. Before the self-check, pass the report's **narrative prose
through the `prose` skill (rewrite mode)** — scoped to the prose only, never the numbers, `file:line`
cites, command blocks, or verdict — so the report reads like a person wrote it; `prose` is style-only
and cannot corrupt the facts (if it isn't installed, apply its principles inline). And because it's
frontend, it self-verifies on the deterministic rung — drive `agent-browser` (start at `--help`) to
confirm it renders, is self-contained (HAR shows one request), diagrams are visible and unclipped at
~390px and 1280px, and the console is clean; a failing check is a blocking defect, not a warning. Full
contract, the task-first section order, and a render-verified reference implementation:
`templates/report.md` and `templates/report.example.html`.

**Hand it back where the user actually looks — the chat, not the tool result.** The report lives in
/tmp and the path returned inside the task-completion tool result is invisible to the user; a path
buried there reads as "no report." So the final assistant message that closes the run must do two
things, every time: (1) print the report path verbatim on its own line as a clickable
`file:///tmp/orchestrate-reports/<name>-<runid>.html`; and (2) lead with a 2–4 sentence plain-English
hand-back — **what ran** (the shape, in words), **on which target** (the concrete project / dir /
repo), **what changed or was produced** (the real diffs / findings / answer), and **the verifier's
verdict** (attributed to the separate node). No machinery, no agent counts — just what happened to the
user's problem and whether it's right. If the report was downgraded or skipped at all (HTML →
markdown, full → one-line, or omitted), say so explicitly *in that hand-back* and why; a silent
downgrade reads as a skipped deliverable and the user will ask where it went.

## Self-check before firing

- Gate passed — a workflow is genuinely warranted (not trivial work in disguise)?
- Once warranted, the shape is as **expressive as its signal earns** — feedback/adversarial/diverse loops used, not rationed — with every node adding decorrelated signal and no redundant doers?
- Verifier defined first, the stop condition derived from it (done = verifier passes), and verification **layered** (adversarial/diverse) rather than minimized?
- Signal on the highest available rung (a tool over an LLM judge where ground truth exists)?
- Dynamic where the work-list/difficulty is unknown — shape adapts to intermediate findings; multi-workflow chaining considered for large/uncertain work?
- Every fan-out unit independent; every loop has signal + stop + divergence guard + binding verdict (loops until `verdict == sound` or the cap escalates, never one-shots a failing verdict)?
- Every gate has a mode set by the interaction mode?
- Critical-path BLOCKED wired to fail-fast + return + resume, with the resume-cache rule honored?
- Plan rendered as the **heavy shape the task warrants** (the gate is for the human to dial *down*, not for you to under-spec and wait to be licensed up), and in **interactive mode an explicit approval obtained before firing** (autonomous runs self-contained instead)?
- Mid-session context externalized / scheduled prompt self-contained?
- Report on by default — written to **/tmp**, scaled to run size, **prose-passed**, task-first, verdict attributed to the separate verifier, agent-browser self-verified (only an extremely-trivial single-agent run drops to a one-line verdict)?
- Report **handed back in the chat** — closing message leads with the plain-English what-ran / on-what / what-changed / verdict, prints the `file://` path verbatim, and declares any downgrade or skip?

If any answer is no, fix the invocation before firing.
