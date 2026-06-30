# Systems-of-record / source-of-truth map

**Status:** CORE
**Loaded when:** the same entity lives in more than one system and someone is about to pick one and
call it the truth.

This leaf reduces one uncertainty: **for each thing the tool touches, which system do you actually
believe — and where is that question genuinely unresolved?** The trap is the single-source-of-truth
myth: the org chart says the ERP owns the customer, the operators tell you the spreadsheet is more
current and they stopped trusting the ERP last spring. Refuse the myth and map the federation
honestly. Per entity: which system *creates* it, which is authoritative for *which fields*, which hold
stale copies, and where they disagree — the golden-record gap. **The contested entities are the
riskiest things to automate**, because automating on top of a field nobody trusts ships wrong actions
at machine speed.

Carry the integrity rule in front of you the whole time. Every contradiction you infer is a
**proposal for the human to confirm, never an assertion**. "The spreadsheet is the real source of
truth for delivery status" is exactly the kind of confidently-wrong claim that is the worst outcome
here — it reads as authoritative, it gets built on, and it is dear to unwind. Write it as "operators
*report* trusting the spreadsheet over the ERP for delivery status — confirm with [who]."

## In the loop — BEFORE / DURING / AFTER

1. **BEFORE.** Inventory the candidate systems from the org and process description, and build the
   per-entity question set: "For a *[customer / case / order]* — where is it born, where does it live
   after, and when those two disagree, who do you actually believe?" The last clause is the one that
   surfaces the golden-record gap; the official answer hides it.
2. **DURING.** Structure the human's notes into system names, field-level ownership, and contradiction
   signals as they surface ("the ERP has the address but it's always six months stale; we phone to
   confirm"). Capture the disagreement without forcing a premature single answer — the unresolved
   state *is* the finding.
3. **AFTER.** Reconcile into the map and list the entities where authority is genuinely unsettled.
   **Propose** the contradictions and the who-you'd-trust call for the human to confirm; do not assert
   them. These contested entities feed straight into integration-reality and the reversibility dial.

## Artifact — source-of-truth map

One row per core entity the tool touches.

| entity | creating system (SOR) | authoritative-for-which-fields | downstream stale copies | known disagreements / golden-record gaps | who you'd actually trust on conflict |
|---|---|---|---|---|---|
| | | | | | |
| | | | | | |
| | | | | | |

The last column is a **proposal, not a ruling** — it records who the people on the ground say they
believe, flagged for confirmation, not a decree about which system wins.

Mark the artifact **"input to architecture, not the design."** This map tells the data model where
authority is federated and where it is contested; it does not draw the schema, and it does not name
the bounded contexts that resolve the federation.

## When to skip

Skip when the tool owns all its own data end to end and touches no upstream system — then the new tool
is the source of truth by construction, and there is no federation to map. This is rare in ops;
confirm it explicitly rather than assuming it. And **never skip both this and ubiquitous-language**:
one of source-of-truth or language is almost always what decides whether the build is even possible.
