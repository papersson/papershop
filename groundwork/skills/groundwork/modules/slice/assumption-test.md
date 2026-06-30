# Assumption map & smallest feasibility test

**Status:** READY
**Loaded when:** the slice branch, once a candidate solution exists and before any build commitment — the de-risking pass that runs before the pilot.

This leaf reduces one uncertainty: of everything this solution silently assumes, which single belief, if false, sinks it — and what is the cheapest thing that would prove it false today. In consumer discovery the riskiest assumption is almost always desirability ("people want this"). Here the need is known; the work already exists. So the risk tilts to **feasibility and integration**: the assumption most likely to be quietly wrong is "the source-of-truth system actually exposes clean data we can act on," not "anyone wants the tool." Find that assumption and test it before code, not after.

Torres's assumption mapping gives the four risk types to sort against — desirability, viability, feasibility, usability — but the weighting is inverted for ops. Run the map so the feasibility column is where you look first.

## The loop, for this leaf

1. **BEFORE / BETWEEN** — for each candidate solution coming out of the opportunity tree, extract the assumptions it rests on and write each as a falsifiable claim, not a hope. "The ERP exposes balances over an API we can read" is testable; "integration will be fine" is not. Rank them by risk: how likely is this wrong, and how badly does the build break if it is. Isolate the single riskiest. Then specify the cheapest test that would falsify it — the smallest probe whose failure tells you to stop. In ops this is usually a data/integration probe, and where access exists **you can often run it directly**: pull 50 real records from the system of record and measure quality. Where access does not exist, you do not get to assume — prep the validation questions for the system owner instead and mark the assumption untested.
2. **AFTER** — record the test result against the assumption, and propose the consequence for the human to confirm: assumption held (proceed to the pilot), assumption broke (the solution needs rework, an anti-corruption layer, or a different source), or untested (carry it into the pilot as a known live risk, do not bury it). Feed a broken feasibility assumption back to `modules/domain/integration-reality.md` — it is a buildability constraint now, not a hypothesis. Update the reversibility dial: an assumption you could not test raises the stakes of the first deploy.

## The artifact

One assumption map per candidate solution. Sort by risk so the thing most likely to sink the build sits at the top, and the single riskiest is isolated with its test fully specified.

**Solution under test:** [the candidate from the opportunity tree, in one line]

| Assumption (as a falsifiable claim) | Type (desirability / viability / feasibility / usability) | Likelihood it's wrong | Damage if wrong | Risk (high/med/low) |
|---|---|---|---|---|
| The SOR exposes current balances over a readable API | feasibility | med | build can't start | **HIGH — riskiest** |
| Operators will trust an auto-filled location field | usability | med | adoption stalls, route-around | med |
| Free-text "status" notes parse into the 3 states we need | feasibility | high | core logic unbuildable | med |
| The commissioner's cycle-time target survives this quarter | viability | low | scope re-opens | low |

**Single riskiest assumption:** [restate the top-risk claim verbatim]

**Cheapest falsifying test:**
- *What you'll do:* [the smallest probe — e.g. "pull 50 real records from the SOR export and measure null rate, dupes, and free-text-where-structure-is-needed"]
- *Who runs it:* [Claude directly, where access exists — or the validation questions prepped for the named system owner where it doesn't]
- *What result kills the assumption:* [the concrete threshold — e.g. ">20% of records missing the field the workflow depends on"]
- *Status:* [held / broke / untested-carried-as-live-risk]

Fill it for real. An assumption map with no test specified is a worry list, not a de-risking pass. The row that matters is the one whose test you can run this afternoon — run it, and let the result, not the optimism, decide whether the pilot proceeds.

Hand a broken feasibility result to `modules/domain/integration-reality.md` as a constraint, and a held result to `thin-slice-pilot.md` as a green light for the workflow it covers.

## When to skip

Skip when feasibility is already proven — the data has been sampled, the integration path is confirmed readable — and the stakes are low enough that a wrong call costs little. Do not skip when the riskiest assumption sits in a system you have not yet touched: an untested integration assumption is exactly the thing that turns a confident pilot into a week-one failure. If you cannot name a single riskiest assumption, you have not looked hard enough at feasibility yet — that is a signal to look, not to skip.
