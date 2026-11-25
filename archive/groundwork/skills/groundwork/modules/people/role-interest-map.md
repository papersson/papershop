# Role-interest & metric-ownership map

**Status:** CORE
**Loaded when:** the commissioner who asked for the tool is not the operator who will run it, and you need to know whose metric it serves versus whose hands it lives in before the first deploy.

This is the people branch's one artifact and its whole job. The uncertainty it reduces is narrow and load-bearing: a tool can satisfy the person who bought it and still be routed around by the person who runs it, and that gap does not show up in a feature list — it shows up at rollout, as quiet non-adoption, when the metric the tool optimizes is the commissioner's and the friction it adds is the operator's. You resolve the persona question structurally, not by imagination. **Never synthesize an archetype of a person you can name.** You have a dozen real users segmented by organizational function — operator, commissioner, and usually a third (auditor, admin, downstream consumer) — each measured on a different metric. Map the real roles and the real metrics; do not invent a composite.

The one axis with no consumer-product analogue is surveillance-versus-enablement. A consumer either wants the app or doesn't; an operator handed a tool that reports their numbers upward reads it as a watcher, and a watched operator routes around it — keeps the real work in the spreadsheet and feeds the tool the sanitized version. That read is what predicts route-around behavior, so it earns its own column.

## Run the loop around this branch

The three beats restated for the role map, with concrete probes.

1. **BEFORE — draft the candidate role set and two distinct question banks.** Propose the roles from the org and process description, name the metric you think each is measured on (mark it a proposal to confirm), and carry **two banks that do not blur into each other**:
   - *Operator bank (friction / workarounds):* "Walk me through the last case that fought you — where did the current way slow you down?" "What do you keep in your own spreadsheet because the system can't hold it?" "When this tool exists, what would make you quietly keep doing it the old way?"
   - *Commissioner bank (metric / visibility):* "What number are you on the hook for, and to whom?" "What can't you see today that you need to?" "If this tool showed you everything, what would you do with it that you can't now?"
   Keep the banks physically separate so an operator interview never drifts into a status report and a commissioner interview never invents operator pain.
2. **DURING — tag each statement to a role and a metric.** Structuring the human's typed, dictated, or recorded notes, attach every claim to who said it and what they're measured on, and flag in the moment when an operator's pain contradicts a commissioner's stated goal — that contradiction is the divergence row, captured live so it isn't lost.
3. **AFTER — assemble the map and write the tensions.** Draft the rows, write the explicit divergence row for each role pair that conflicts, name the single most likely route-around, and read whether the tool currently lands as surveillance (attrition risk) or enablement (adoption). Every divergence and every route-around is **a proposal for the human to confirm**, not an asserted fact about a colleague.

## The artifact

One page. One row per real, named role — not per archetype. The divergence and route-around columns are where the branch pays for itself.

| role | mission (functional job) | metric measured on | what it wants from the tool | veto/block power | explicit divergence vs other roles | route-around / shadow-system risk | surveillance-vs-enablement read |
|---|---|---|---|---|---|---|---|
| | | | | | | | |
| | | | | | | | |
| | | | | | | | |

Column notes, so the map stays honest:
- **metric measured on** — the number this role is actually judged on, not the one they'd cite as the goal. If you don't yet know it, write "unconfirmed" rather than guess.
- **veto/block power** — can this role stop the tool, starve it of data, or refuse to adopt? This is the column that would otherwise tempt a second leaf; keep it here, beside the metric that explains the veto.
- **explicit divergence vs other roles** — name the pair and the conflict: "operator's per-case speed vs commissioner's audit completeness." A blank here means you haven't found the tension yet, not that there is none.
- **route-around / shadow-system risk** — the specific old habit or shadow tool this role will fall back to. Tie it to the surveillance read in the next column.
- **surveillance-vs-enablement read** — does this role experience the tool as a watcher or as a help? Surveillance predicts route-around; enablement predicts adoption.

## When to skip

- Skip when the commissioner and the operator are the **same person** — a tool someone builds for their own work. Note that explicitly and move on; there is no metric divergence to surface.
- **Never skip when the commissioner is not the user.** The tension is structural and does not go away by being ignored — it surfaces at rollout as non-adoption if you don't surface it now. A single-team tool with one role still gets one honest row; the cost is minutes.
