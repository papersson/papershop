# Thin-slice & concierge/WoZ pilot, stakes-gated

**Status:** READY
**Loaded when:** the slice branch, once one painful workflow is chosen and its riskiest assumption has been tested — the last step before anyone builds, and the loop back into discovery.

This leaf reduces the uncertainty that survives all the others: did we model the existing work correctly, and is the to-be path genuinely faster or safer than what the operator does today. Take the single most painful real workflow, end to end, and ship it manually first — a human standing in for the system, behind a thin facade. Ries's concierge/Wizard-of-Oz, re-pointed: in consumer-land the WoZ question is "does the need exist," but the need here is known. The question is whether your model of the work is right and whether the to-be is an improvement. You answer it before committing a line of production code.

The pilot is **gated by the reversibility dial**, because the wizard is not a demo — a human standing in for a real operational decision makes real errors with real consequences. A wrong dispatch, a wrongly closed case, a mis-routed payment is an operational failure, not a bounced metric. The more irreversible and high-stakes the first live action, the more as-is and integration understanding must clear the gate before the wizard touches anything live.

## The loop, for this leaf

1. **BEFORE** — propose the thinnest painful slice from the opportunity tree: one workflow, one role, end to end, no breadth. Sketch its to-be path (see the line you must not cross, below). Draft the concierge/WoZ operating procedure — what the operator sees, what the wizard does by hand behind the facade, how the hand-off works. Rate reversibility and stakes, and set the explicit gate: how much as-is understanding is *enough* before this goes live, tied to that rating (see the grid). Propose all of it for the human to confirm — you are prepping the pilot, not authorizing it.
2. **DURING PILOT** — where the stakes rating permits, **you can act as the backstage wizard**, executing the manual process behind the thin facade while the operator works the front. Where stakes do not permit a Claude-run wizard, the human runs it and you capture. Either way, log every real decision and every error the manual process makes — the errors are the highest-value data the pilot produces.
3. **AFTER** — structure the operator-side observations into the next round of snapshots, and feed them back: where the to-be path diverged from how the work actually went, where the wizard had to improvise (a new workaround, straight to `modules/as-is/`), where the model was wrong. This is the close that loops to discovery rather than ending it — the pilot is an interview that happens to ship value.

## The line you must not cross — a worked example

The pilot's emitted plan **sketches one workflow's to-be path**. It does not design the system. The seam is concrete and you can hold it: a path sketch names the *steps a person or operator moves through*; crossing into architecture names *how a system would implement them*. Both sides, for a case-closing workflow:

**Acceptable to-be path sketch** — the human-visible steps:
> Operator opens the case and reviews the resolution → operator confirms it's resolved → the close is filed and timestamped → the case owner is notified it's done → the case drops off the operator's open queue.

That is wayfinding: who moves through what, in what order, to what effect. It is exactly enough for a wizard to run by hand and for engineering to recognize the workflow.

**Crossing the line — production architecture the handoff forbids:**
> A `cases` table with a `status` enum and a `closed_at` column → a `CaseService.close()` endpoint that writes it → a row in an `audit_log` table → a webhook to the notifications service → a cache invalidation on the queue view.

The moment you name tables, columns, services, API contracts, endpoints, or a data model, you have stopped sketching the work and started designing the build. Stop. Mark the sketch "input to architecture, not the design," hand it over, and let engineering draw the schema. If you catch yourself reaching for a noun that is a system component rather than a step a person takes, you have crossed it — back up to the human-visible verb.

## The reversibility × stakes grid

A calibration aid for how much as-is and domain understanding is *enough* before the wizard goes live — set against the dial from Orient. Read it to locate the pilot, not to march through it: **this is a calibration aid, not a pipeline.** Most pilots sit in one cell and stay there.

| | Reversible (easily undone) | Costly to reverse | Irreversible (physical / legal / financial finality) |
|---|---|---|---|
| **Low stakes** | Ship the slice now, learn live. Bare as-is is enough. | Confirm the unhappy path before live; light integration check. | As-is + the one failure mode that bites must be understood first. |
| **Medium stakes** | Ship thin; wizard runs it, watch for week-one exceptions. | As-is workaround register must be solid before live. | As-is + integration-reality clear the gate; wizard runs supervised, never unattended. |
| **High stakes** | Ship thin but instrument heavily; a reversible mistake is still a trust hit. | As-is + people (route-around risk) + integration clear first. | **As-is and integration-reality must clear the gate before any live action; a Claude-run wizard is off the table — human wizard, supervised, with a rollback.** |

The bottom-right cell is the one the gate in SKILL.md's Orient read #2 protects: high-stakes and irreversible, you do not let a manual stand-in make the call live until the understanding is in hand. The top-left is its opposite — cheap and reversible earns "ship and learn." Everywhere between, the cell tells you which CORE artifacts must exist before the wizard touches anything real.

## The artifact

A thin-slice pilot plan. Four parts, filled for the one chosen workflow only.

**1. The workflow, specified end-to-end** — one workflow, one role, no breadth.
- *Chosen slice:* [the single most painful workflow, from the opportunity tree, in one line]
- *Why this one:* [its recurrence / pain evidence — point at the workaround register and the role map]
- *To-be path sketch:* [the human-visible steps, as above — verbs a person moves through, never system nouns]
- *Out of this slice:* [what the pilot deliberately does not touch]

**2. Concierge/WoZ operating procedure** — how the manual stand-in runs.
- *What the operator sees (the facade):* [the thin front]
- *What the wizard does by hand (backstage):* [the real manual steps behind it]
- *Who is the wizard:* [Claude, where the stakes cell permits — or the named human, supervised]
- *Error log:* [where every real decision and every mistake the manual process makes gets recorded — this is the pilot's primary output]

**3. Reversibility / stakes rating**
- *Reversibility:* [reversible / costly to reverse / irreversible — and the concrete reason]
- *Stakes:* [low / medium / high — what a wrong live action actually costs]
- *Grid cell:* [the cell this lands in]

**4. The enough-understanding gate, tied to the rating**
- *What must clear before live:* [the CORE artifacts the grid cell requires — name them: as-is register, integration-reality sheet, role-interest map, as applicable]
- *Status:* [cleared / not yet — and if not yet, the pilot does not go live]

Fill it for real. A pilot plan with no error log is a demo; a pilot plan whose gate is unfilled is a gamble. The plan earns its place by being runnable by hand this week and by naming, before anyone starts, exactly what would stop it.

## When to skip

Skip when the first deploy is high-stakes **and** irreversible — a wrong action carries physical, legal, or financial finality — until the as-is and integration-reality artifacts clear the calibration gate; running a manual wizard on a decision that can't be undone, before you've modeled the work, is the failure this leaf exists to prevent. Skip also when the team is not yet committing to build — a pilot plan with no one to run it is ceremony. And skip when the first deploy is cheap and fully reversible and the slice is small enough to simply ship and watch — at that corner of the grid the pilot apparatus is heavier than the problem; ship it, instrument it, and let the live signal do the work the wizard would have.
