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
was asked, what was actually done, how to check it, and what still needs a human call. The
orchestration machinery is subordinate and mostly optional (see below). A report where half the
sections are about worktrees and barriers has lost the plot — the reader came for their result, not
your plumbing.

## Write it for someone who did not watch the run

This is the rule that most often gets broken, and it is what makes a report feel busy and
hard-to-read even when the structure is fine. The report is the reader's **first** look at work they
did not see. Write it as a **re-grounding, not a continuation of your working thread.**

- **Lead with the outcome.** One plain sentence on what happened or what was produced, before any
  detail. Not the topology, not the agent count — the result.
- **Drop the working shorthand.** The vocabulary you built up while running the workflow is yours,
  not the reader's. No arrow chains (`a → b → c`), no hyphen-stacked compounds
  (`observation-from-memory confidence`), no labels you coined mid-run and never defined. Spell terms
  out in full sentences.
- **Give every identifier its own plain clause.** A file, a flag, a commit, a metric — name it and
  say what it is, rather than dropping it in as a token the reader is assumed to recognize.
- **Cut anything that repeats.** If two sections carry the same point (a common one: the verifier's
  suggestions and the "open questions" list), merge them. When a report says "as noted above," that
  is the duplication showing — remove it.
- **If you must choose between short and clear, choose clear** — but a re-grounded, plain report is
  almost always *shorter* than one written in working notes, because the padding was machinery and
  repetition.

The `prose` pass (below) is the safety net for this, not the substitute. Write the re-grounding
version first.

## The required spine — small, and all that is mandatory

Every report, however simple, does exactly these four things, in this order. Nothing else is
required.

1. **The outcome.** The task in one line, and what was accomplished against it, in plain language,
   above the fold.
2. **The result.** The substantive thing produced — the real diffs, findings, answer, or design —
   each item cited to its provenance (`file:line`, commit, source URL) where it has any, so the
   report *shows* rather than asserts. This is the bulk of the report. The one item that matters most
   is expanded, not buried.
3. **The verdict and its honest caveat.** What the **separate verifier node** concluded, named with
   its rung (deterministic > domain harness > adversarial rubric > human), and — stated plainly — what
   that verdict does **not** cover. Where a real re-run command exists, print it so the human can
   reproduce the check. Where the result is soft, partial, sampled, or capped, say so here; never
   paint it green.
4. **What is left to the human.** Any blocked, escalated, or deliberately-deferred decision: the
   choice, the options (recommendation marked but *not* applied), and a resume handle where one
   applies.

A simple run — one fan-out and a single verify — is **done at these four.** It should land close to a
single screen of plain prose plus the result, and look much more like the lean reference than the
rich one.

## Everything else is conditional — include only what earns the reader's trust *for this run*

These are **off by default.** Add one only when this specific run is rich enough that it genuinely
helps the reader trust or follow the result — not because the template has a slot for it. When in
doubt, leave it out; a tight report beats a complete one.

- **A topology diagram** — only when the *shape of the run* is itself part of why the result can be
  trusted (e.g. a deep adversarial verification where "a separate panel graded it" is the whole
  point), and only for a genuinely complex run. A two-agent fan-out does not need a drawing of itself.
- **Accounting** (agents, tokens, wall-clock, models) — only if the numbers are real and the reader
  has a reason to care. Otherwise one line, or omit. Never invent or estimate them to fill the table.
- **Dual-command / residual-scan verification** — only when there is deterministic ground truth (code
  that compiles, tests that pass, a residual grep). For a taste or design run there is no exit code;
  say that honestly in the verdict instead of dressing it in an apparatus it doesn't have.
- **Per-unit verifier telemetry** (score grids, per-voter breakdowns) — almost never. A sentence
  carries the verdict; a grid is decoration. Show the breakdown only if a reader genuinely needs to
  audit a specific dimension.

When you do include the machinery, it lives in **one collapsible "How this was produced" section near
the end** — subordinate, for trust and the curious, never the spine.

## The two jobs, restated

- **Teach** — a teammate who wasn't watching can follow the *work* (the wrinkles, the cases, the one
  ambiguity) and learn from it. The pedagogy owed is task-pedagogy, not a tour of the harness.
- **Verify** — the human can confirm it's right without trust: the verifier and its verdict
  *attributed to the separate node that produced it*, a re-run command where one exists, claims linked
  to provenance.

## Honesty rules (non-negotiable, even in the leanest report)

- **Verdict attribution.** The verdict is written by the *separate verifier node*, never by a worker
  or the dispatcher, and names its rung. A verdict the doer could have written is worthless. Keep its
  wording exactly as that node produced it.
- **Never fabricate a green.** A partial / soft / sampled / capped result is rendered as such with a
  plain caveat — never a deterministic-looking green badge. A blocked item is excluded from any "done"
  count.
- **Numbers must be real or labeled.** If a count isn't independently verifiable from the page, either
  the verifier actually produced it or the report labels it as unverified. Don't print accounting you
  didn't capture.

## Diagrams — when you include one

Outline-only, editorial, warm (full conventions: `anthropic-minimal-diagram-html`). Canvas `#F2EFE8`;
node stroke `#5F5A54` (`fill="none"`, `rx="8"`); dashed panel borders `#B9B3AB`; text `#2D2B28`, muted
`#7A756E`; **one** meaningful accent (success `#71AE88`, warn `#C88E6A`, error `#D96B63`). Orthogonal
routing, small filled-triangle heads, coords snapped to 10, `viewBox` + CSS `width:100%` (never fixed
px). It goes in the "How this was produced" aside, as evidence, never the headline — and per the rule
above, only when the run is complex enough to warrant it.

## Prose pass — hand the narrative to `prose`

After writing the re-grounding version, run the narrative through the **`prose` skill in `rewrite`
mode**, scoped to the prose only — never the numbers, the `file:line` citations, the command blocks,
or the verdict wording. `prose` is style-only and cannot alter a fact or soften a verdict. If it isn't
installed, apply its principles inline.

## Self-verification — drive `agent-browser`

The report is frontend, so it self-checks on the **deterministic rung**. A final step runs
`agent-browser --help`, then drives it to confirm, as hard pass/fail: it renders; it is self-contained
(a HAR capture shows exactly one request — the document); any SVG is visible and unclipped at **both
~390px and 1280px**; the console is clean; no horizontal overflow. A failing check is a **blocking
defect**, not a warning — loop once to fix before handing back.

## When it fires (scaled to the work)

Default **on**, scaled to the run: most runs land at the **lean** shape (the required spine, plain
prose); only a genuinely rich run pulls in the conditional machinery. An *extremely trivial*
single-agent run drops to a one-line verdict. Always overridable.

## What the node consumes — the run manifest

The report is only as good as the trace it's handed, so nodes **accumulate a run manifest** as they
execute. Ordered by how much the reader cares: **task + outcome** (the ask verbatim, what was
accomplished); **substantive findings** (the real per-unit results with provenance — the bulk of the
report); **verifier** (the check, its rung, its verdict, and a re-run command where one exists);
**exceptions** (every `BLOCKED`/`FAILED`/retry/sample/cap with a resume handle); **accounting** (only
if real). If the manifest is thin, the report says so rather than inventing a narrative.

## Reference implementations

- `templates/report.example.simple.html` — **the default shape.** A design/research run with no
  deterministic verifier: plain-language outcome, the result as a scannable table, a four-sentence
  verdict-and-caveat, the human's open decisions, and a single collapsed "how this was made"
  paragraph with no diagram and no accounting. This is what most runs should look like. Lift its CSS
  scaffold and section structure.
- `templates/report.example.html` — **the rich shape.** A code migration where the machinery earns
  its place: substantive edits as the lead section, dual-command verification with a residual scan and
  a scope caveat, a blocked case as a decision section, and a topology diagram + summing accounting in
  the collapsed aside. Use this only when the run is genuinely this complex.

## Fill these in

- **Deliverable** — what the run produced and where it lives (the report itself always lands in
  `/tmp/orchestrate-reports/`).
- **Audience** — a teammate who never saw the run? a reviewer who must sign off? Tilt the teach/verify
  balance; "reviewer" weights the verify section and the resume handles heavier.
- **Depth** — defaults to lean; only opt into the rich shape when the run earns it.

## Ready-to-fire example

Append a clause like this to any workflow invocation:

> As the final node, after the verifier passes, write a self-contained HTML report to
> `/tmp/orchestrate-reports/<name>-<runid>.html` (a run artifact — keep it out of the repo). Report the
> WORK, not the workflow, and write it for a reader who did not watch the run: lead with a plain
> one-sentence outcome, then the substantive result (each change/finding/answer cited to its
> provenance, the most important one expanded), then a short verdict-and-caveat that states what the
> *separate verifier node* concluded, its rung, and honestly what the verdict does NOT cover (print a
> re-run command only if a real deterministic one exists), then any blocked or deferred decision as a
> short "what's left to you" section with options (recommendation marked, not applied). Drop the
> working shorthand — no arrow chains, no coined compound labels, spell terms out, give every file or
> flag its own plain clause, and cut anything that repeats. Include a topology diagram and an
> agent/token accounting table ONLY if this run is complex enough that the shape itself is evidence the
> result can be trusted; otherwise omit them, or fold a one-paragraph "how this was made" into a single
> collapsed section near the end. Never paint a partial result green. Warm Anthropic-minimal palette
> (`#F2EFE8` canvas, one accent), inline CSS + SVG, no external requests, system fonts. Then pass the
> narrative prose through the `prose` skill (`rewrite` mode), scoped to prose only — never the numbers,
> cites, command blocks, or verdict wording. Finally run `agent-browser --help` and drive it to confirm
> the file renders, is self-contained (HAR shows one request), any diagram is visible and unclipped at
> 390px and 1280px, and the console is clean; loop once to fix if not.
