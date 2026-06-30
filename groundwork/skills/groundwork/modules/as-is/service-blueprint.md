# As-is backstage & fail-point blueprint

**Status:** CORE
**Loaded when:** the as-is branch, when the process is long or multi-role enough that the workaround register alone won't hold its shape — and especially when a documented SOP exists to overlay.

The one uncertainty this leaf reduces: *where, along the real spine of the work, the value and the breakage actually sit.* Shostack's line of visibility was drawn for customer-facing service — onstage above, support below. Re-point it for operations: here the work, the value, and the workarounds nearly all live **backstage** — the legacy-dependent steps, the silent handoffs, the support systems no one demos. The register catches each workaround as a discrete event; the blueprint puts them back on one spine so you can see the official process and the observed-real process diverge in place.

## The loop, for this leaf

1. **BEFORE** — draft a skeleton blueprint with the four lanes below. Where an official SOP exists, pre-load it as the baseline so the human walks in knowing which steps are *supposed* to happen — and can therefore catch the ones being silently skipped or improvised. Add a fail-point-hunting probe bank: "what do you do that the system doesn't know about?", "where does this wait on someone else?", "which step do people get wrong?", "what's the hand-off that happens by email?"
2. **DURING** — drop the human's narration into the correct lane as it comes, so they keep eye contact and you keep the structure. Tag the smells inline as you hear them: a wait, a manual touch, a silent step the SOP omits, an informal hand-off, a fail point, a workaround. You are filing typed or dictated notes into lanes, not structuring live during sustained eye contact.
3. **AFTER** — diff the blueprint across interviewees. Where the official backstage forks from the real one, that fork *is* the finding. List the recurring fail points as the highest-value targets, and propose — for the human to confirm — which gaps between SOP and reality are the build's actual job versus local habit.

## The artifact

A two-layer as-is service blueprint. The lanes run top to bottom through each process step; every smell is flagged inline with a tag, and the **OFFICIAL** row records what the SOP claims for that step so the gap reads at a glance. Tags: `[FAIL]` fail point · `[WAIT]` queue or blocked-on-someone · `[MANUAL]` manual touch · `[SILENT]` step the SOP omits · `[HANDOFF]` informal hand-off · `[WORKAROUND]` routes to the register.

| Lane | Step 1 | Step 2 | Step 3 |
|---|---|---|---|
| **Operator action** (what the person does) | Receives case in queue | Validates address | Assigns to field team |
| **Onstage** (system the operator sees) | Ticket UI list view | — `[SILENT]` no validation screen exists | Dispatch board |
| **Backstage** (steps/systems hidden from the operator) | Ticket created by intake API | `[MANUAL]` hand-checks against external map `[WORKAROUND]` | `[HANDOFF]` pings team lead on chat to confirm availability |
| **Support systems** (legacy, exports, the things no one demos) | Intake API, ERP | maps.example, team spreadsheet | Chat tool, the lead's memory `[FAIL]` |
| **OFFICIAL (SOP says)** | Same | "System validates address automatically" — *does not* | "Auto-assign by zone" — *overridden in practice* |

Render the real lanes first; the **OFFICIAL** row is the overlay that makes each divergence legible. A column with three tags is a hotspot — that step is where the current system abandons the operator, and where the to-be design earns its keep. Carry the `[FAIL]` and `[WAIT]` columns into `modules/frame/` as candidate problems, and every `[WORKAROUND]` tag back to the register so the two as-is artifacts stay in sync.

## When to skip

Skip when the process is short and linear enough that `workaround-register.md` already captures it whole — a three-step, single-role task does not need a blueprint. Skip too when there is no documented SOP *and* few backstage steps: with nothing to overlay and nothing hidden, the register is the lighter, truer record. The moment a process crosses roles, waits on other people, or leans on systems the operator never sees, the blueprint is what keeps those handoffs from vanishing into "and then it just gets done."
