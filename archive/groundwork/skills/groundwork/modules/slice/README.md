# slice — close: de-risk and ship the thinnest real workflow, stakes-gated

Mid-level index (progressive disclosure). Enter when understanding is converging on one workflow and the question is no longer "what's broken" but "what's the smallest real thing we can put in front of an operator, and what could make it blow up."

## Leaves
- `assumption-test.md` — map the assumptions behind each candidate solution, sort by risk, isolate the single riskiest, and specify the cheapest test that would falsify it — in ops, usually a data/integration probe Claude can often run directly. [READY]
- `thin-slice-pilot.md` — take the single most painful real workflow end to end and ship it manually first, gated by the reversibility dial; carries the worked to-be/architecture line and the reversibility × stakes grid that Orient read #2 points to. [READY]

## Fit
The forward-motion close. The CORE branches (as-is, people, domain) recover what is true; `modules/frame/` picks the one problem worth solving and writes the line you'll be held to. slice converts that decision into a shippable, watchable first step — without betting the operation on it. `assumption-test.md` finds the one belief that, if wrong, sinks the build, and kills it cheaply before code; `thin-slice-pilot.md` runs the chosen workflow by hand behind a thin facade so you learn whether you modeled the existing work correctly before any system makes the call for real. Both feed the operator-side observations straight back into the next round of snapshots — this is where discovery loops into delivery rather than ending. Pull the candidate solutions from `modules/frame/`'s opportunity tree, the integration findings from `modules/domain/integration-reality.md`, and the reversibility dial from Orient. Stop clean at the engineering handoff: the slice sketches one workflow's to-be path, never the production architecture.
