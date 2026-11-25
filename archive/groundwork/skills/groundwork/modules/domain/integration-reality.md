# Integration & data-quality reality sheet

**Status:** CORE
**Loaded when:** the design depends on reading from or writing to a system someone else owns, and
nobody has yet checked whether that is actually possible or whether the data is clean enough to use.

This leaf reduces the bluntest uncertainty in the branch: **is the thing you want to build even
buildable?** In ops this question frequently dominates the whole design. The plan assumes the legacy
system has an API; it has a nightly CSV export and a DBA who guards it. The plan assumes the status
field is reliable; it is free text where three operators each invented their own codes. Establish this
**before design starts**, not after the architecture has been drawn around a capability that isn't
there. Per system the tool must touch: who owns it, whether you can write to it or only read or export,
where a model mismatch will force an anti-corruption layer, and what the data quality actually is.

This is the one leaf where you can stop assisting and **probe directly**. Where access exists, Claude
runs the feasibility test itself: pull a sample of roughly 50 real records and measure the quality —
null rates, duplicates, free-text where the design needs structure. That is fact, not an account from
memory, and it is the strongest evidence the branch produces. Where access does not exist, prep the
validation questions for the system owner and mark the data-quality cells as unverified claims to
confirm — a **proposal, not an assertion**, like everything else in this branch.

## In the loop — BEFORE / DURING / AFTER

1. **BEFORE.** List the systems to probe from the systems-of-record map, and prep the access and
   ownership questions: "Can we write back, or only read?", "Is there an API, or is it an export?",
   "Who controls that export and how often does it run?", "Who do we ask when a field is wrong?"
2. **DURING.** Structure the human's notes into access constraints and data-quality horror stories as
   they surface — the "oh, that field is a mess, nobody fills it in right" asides are the gold here,
   so capture them verbatim enough to verify later.
3. **AFTER.** Synthesize the sheet, flag where an anti-corruption layer is required, and name which
   planned features are **blocked by data reality**. Where you have access, run the ~50-record sample
   and write the measured numbers into the data-quality column. This sheet **feeds the reversibility
   dial directly**: clean writable data argues for shipping thin and reversible; export-only legacy
   with 40% null keys argues for front-loading hard before the first live action.

## Artifact — integration & data-quality reality sheet

One row per system the tool must touch.

| system | owner | access reality (API / export / read-only / write) | model mismatch needing an ACL | data-quality findings (nulls, dupes, free-text-where-structure-needed) | resulting buildability constraint |
|---|---|---|---|---|---|
| | | | | | |
| | | | | | |
| | | | | | |

Where a data-quality cell comes from a real sample, cite the number and the sample size ("38% of 50
sampled records had a null delivery date"). Where it comes from an account, mark it unverified and
confirm with the owner.

Mark the artifact **"input to architecture, not the design."** It tells the design what is reachable
and what the ACL must absorb; it does not draw the ACL, the schema, or the bounded contexts.

## When to skip

Skip when the tool is fully standalone — no integrations, no inherited data, the new tool is the only
system in play. Confirm that explicitly, since ops tools rarely are; an unexamined "oh, it's
standalone" is how a hard integration constraint gets discovered after the design is committed.
