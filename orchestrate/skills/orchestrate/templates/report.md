# Template: report

The terminal node of essentially every workflow (skipped only for an extremely-trivial single-agent
run). A workflow runs dozens of agents the human never sees, then hands back a deliverable with the
*how* and the *why-it-can-be-trusted* locked in transcripts nobody reads. The report node unlocks
both: one self-contained HTML file, written to `/tmp/orchestrate-reports/<name>-<runid>.html` (a run
artifact, not a repo deliverable — kept out of the working tree), that explains the run and lets the
human verify it without taking anyone's word for anything.

## The governing principle: report the work, not the workflow

The reader's first question is **"what happened to *my* problem, and is it right?"** — not "how did
your agents coordinate?" So the **task and its concrete outcome lead and dominate** the report: what
was asked, what was actually done (the real diffs / findings / answer, each carrying its `file:line`
provenance), how to verify it, and what still needs a human call.

The **orchestration machinery** — topology diagram, why-this-shape, agent/token/model accounting — is
**demoted to a single compact, collapsible "How this was produced" section**, near the end. It is
present for trust and for the curious, and it is never the spine. The topology earns its place only as
*evidence the result is trustworthy*, not as the subject. A report where half the sections are about
worktrees and barriers has lost the plot — the reader came for their code, not your plumbing.

The pedagogy the run still owes the reader is **task-pedagogy**: teach what the *task* actually
required (the wrinkles, the cases, the one ambiguity), so a teammate who didn't watch can follow the
*work* and learn from it. Teaching how the agent system decomposed things is a compressed bonus in the
aside, not the lesson.

## Two jobs

- **Teach** — a teammate who wasn't watching can follow the work and understand how each case was
  handled. Narrative leads, structure and detail support.
- **Verify** — the human can confirm it's right without trust. Surface the Step-2 verifier and its
  verdict *attributed to the separate node that produced it*, print the exact re-run command, link
  every claim to its `file:line`. Verification-honest: never paint a soft or partial result green.

## When it fires (scaled to the work)

Default **on** — almost every run gets a report, scaled to its size: a **short** HTML report for a
simple run (one fan-out, a single verify), a **full** one for anything richer. Only an *extremely
trivial* single-agent run drops to a one-line verdict. Richness scales with the run; always
overridable.

## What the node consumes — the run manifest

The report is only as good and as honest as the trace it's handed, so nodes **accumulate a run
manifest** as they execute (each appends; the report barrier reads it). Minimum contents, ordered by
how much the reader cares:

- **task + outcome** — the original ask verbatim, and what was actually accomplished against it.
- **substantive findings** — the real per-unit results (edits, bugs, claims, answers), each with
  provenance (`file:line`, commit, source URL) so the report can *cite* rather than assert. This is
  the bulk of what the report shows.
- **verifier** — the Step-2 check, its rung, its **verdict**, and the literal command/prompt to
  reproduce it, plus a completeness/residual command whose expected count equals the deliberately
  excluded items.
- **exceptions** — every `BLOCKED`/`FAILED`/retry/sample/cap, each with a resume handle (worktree
  path + branch + state). The honesty ledger.
- **accounting** — agents, tokens, wall-clock, models. The machinery; goes in the aside.

If the manifest is thin, the report says so rather than inventing a narrative.

## What it produces — the HTML, task-first

One self-contained `.html` (inline CSS + inline SVG, zero external requests, system fonts), written to
**`/tmp/orchestrate-reports/<name>-<runid>.html`** (a run artifact, not a repo deliverable — keep it
out of the working tree), that reads top-to-bottom as the *story of the work*. Section order, task
substance first:

1. **Masthead + verdict** — the task and **what was accomplished** in the headline (not how — keep the
   topology out of the title), the verdict (did the verifier pass?), and the few numbers that bear on
   the outcome (done / blocked / scope). The "did it work, on my thing" answer, above the fold.
2. **What was done** — the substantive results as the first and largest section: the real changes /
   findings / answer, each a row keyed by `file:line` with before→after, scannable by eye. The one
   finding that matters most is expanded, not buried. A blocked item shows no success diff.
3. **Verify it yourself** — the verifier, foregrounded and attributed to the separate node that ran
   it: the check, its verdict and rung, a copyable command block on a named branch with expected exit
   codes, **and a second completeness command** (e.g. a residual scan whose expected hit count equals
   the blocked items, so a leftover reads as expected proof, not a missed edit). A scope-caveat box
   states what the green does *not* cover, in its own visible box.
4. **What needs your decision** — any blocked/escalated case as a first-class section: the ambiguity,
   the options (with a recommendation marked but *not* applied), an explicit "retries: 0 — by design"
   note, and a resume handle (worktree path + branch). Task-substantive, not an error footnote.
5. **How this was produced** — *collapsible, subordinate, near the end.* The Anthropic-minimal SVG of
   the topology that ran with a few sentences on why this shape, and an accounting table whose rows
   visibly **sum to a printed total**. For trust and the curious. This is the only machinery section.
6. **Footer** — self-contained note; restate the scoped verdict.

Delight is in restraint: warm calm canvas, generous whitespace, one clear narrative line, diagrams
that reward a second look — not animation or chrome. The reader finishes understanding their result
*and* trusting it.

## Diagrams — Anthropic-minimal inline SVG

Outline-only, editorial, warm. Condensed conventions (full skill:
`anthropic-minimal-diagram-html`):

- **Canvas** `#F2EFE8`; **node stroke** `#5F5A54` (`fill="none"`, `rx="8"`); **panel border** dashed
  `#B9B3AB` with an uppercase fieldset/legend label; **primary text** `#2D2B28`; **muted** `#7A756E`.
- **One accent only**, carrying meaning: success `#71AE88` on the verifier/verdict, warn `#C88E6A` or
  error `#D96B63` on the blocked path, muted dashed for a "no retry" note.
- Strictly orthogonal routing, small filled-triangle heads, no two arrows on one centerline, coords
  snapped to 10. `viewBox` + CSS `width:100%` (never fixed px), viewport meta tag.
- The topology diagram lives **in the "How this was produced" aside**, not at the top. It maps the run
  directly (workers→nodes, barrier→join, loop→muted dashed feedback arrow, verifier→accent node,
  blocked→error peel-off) — but it is evidence, not the headline.

## Prose pass — hand the narrative to `prose`

The report's value is its narrative, and a report that reads like AI undercuts its own credibility.
Before the render self-check, run the prose sections through the **`prose` skill in `rewrite` mode**,
scoped to the narrative only — never the numbers, the `file:line` citations, the command blocks, or
the verdict. `prose` is style-only and cannot alter a fact or soften a verdict, so it is safe on a
report; it just strips the slop. If `prose` isn't installed, apply its principles inline. Keep the
verdict's wording exactly as the separate verifier node produced it.

## Self-verification — drive `agent-browser`

The report is frontend, so it self-checks on the **deterministic rung**, not on vibes. A final step
runs `agent-browser --help`, then drives it to open the file and confirm, as hard pass/fail: it
renders; it is self-contained (a HAR capture shows exactly one request — the document); every SVG is
visible with non-zero size and unclipped at **both ~390px and 1280px**; the console is clean; no
horizontal overflow. A failing check is a **blocking defect**, not a warning — loop once to fix
(malformed SVG, a `nowrap` table with no scroll wrapper) before handing back. The two killed
candidates in this template's own design tournament failed exactly here: findings tables that
overflowed at 390px.

## Honesty rules (non-negotiable)

- **Verdict attribution.** The verdict is written by the *separate verifier node*, never by a worker
  or the dispatcher, and names its rung (deterministic build/test > domain harness > adversarial
  rubric > human). A verdict the doer could have written is worthless.
- **Never fabricate a green.** A PARTIAL/soft/sampled/capped result is rendered as such with a scope
  caveat — never a deterministic-looking green badge. A blocked item appears as its own row/card with
  no success diff and is excluded from the headline count's "done".
- **Numbers must be real or labeled.** If a count isn't independently verifiable from the page (token
  totals, test tallies), either the verifier actually produced it or the report labels it. Accounting
  visibly sums so cost is auditable, not asserted.

## Fill these in

- **Deliverable** — what the run produced and where it lives (the report itself always lands in
  `/tmp/orchestrate-reports/`).
- **Audience** — a teammate who never saw the run? a reviewer who must sign off? future-you? Tilt the
  teach/verify balance; "reviewer" weights the verify section and the resume handles heavier.
- **Depth** — one-screen summary vs full narrative (defaults from run size).

## Defaults

- Report barrier: one Opus/Sonnet agent reading the manifest and writing the file to
  `/tmp/orchestrate-reports/`; a `prose` rewrite pass on the narrative; one agent-browser self-check
  pass after.
- Runs **after the final verifier passes** — it states the verdict, it doesn't substitute for the
  check. If the run ended BLOCKED, the report leads with the block, not a false all-clear.
- Budget: small relative to the run (one writer + a prose pass + one checker). Drop to a one-line
  verdict only on an extremely trivial single-agent run.

## Reference implementation

`templates/report.example.html` is a render-verified worked instance (the `oldFetch → newFetch`
migration fixture): task-first ordering, the substantive edits as the lead section, dual-command
verification with a scope caveat, the blocked case as a decision section, and the topology + summing
accounting folded into the collapsible "How this was produced" aside. Lift its CSS scaffold and
section structure; swap in the real run's substance.

## Ready-to-fire example

Append a clause like this to any workflow invocation:

> As the final node, after the verifier passes, write a self-contained HTML report to
> `/tmp/orchestrate-reports/<name>-<runid>.html` (a run artifact — keep it out of the repo). Report the
> WORK, not the workflow: lead with the task and what was actually
> accomplished, then the substantive results (every change/finding as a `file:line` row with
> before→after, the most important one expanded), then a "verify it yourself" section that foregrounds
> the verifier and its verdict *attributed to the separate node that ran it* — a copyable command on a
> named branch with expected exit codes, plus a completeness command whose expected count equals the
> blocked items — with a scope-caveat box for what the green doesn't cover, then any blocked case as a
> decision section with options (recommendation marked but not applied), "retries: 0 by design", and a
> worktree+branch resume handle. Fold the topology diagram, why-this-shape, and the agent/token
> accounting (rows that visibly sum to a total) into ONE collapsible "How this was produced" section
> near the end — subordinate, for trust, never the spine. Anthropic-minimal outline-only SVG, warm
> palette (`#F2EFE8` canvas, dashed phase panels, one accent), inline CSS + SVG, no external requests,
> system fonts. Never paint a partial result green. Then pass the narrative prose through the `prose`
> skill (`rewrite` mode), scoped to prose only — never the numbers, `file:line` cites, command blocks,
> or verdict. Finally run `agent-browser --help` and drive it to confirm the file renders, is
> self-contained (HAR shows one request), the diagrams are visible and unclipped at 390px and 1280px,
> and the console is clean; loop once to fix if not.
