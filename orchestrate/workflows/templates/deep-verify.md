# Template: deep-verify

Check and source every factual or technical claim in a document, report, or PR description. Use
when shipping something where being wrong is expensive and the author (human or agent) can't be
trusted to catch their own errors.

## Shape

Fan-out and synthesize, with adversarial verification per claim:

1. **Extract** — one agent reads the document and lists every checkable claim as a discrete item. No verifying yet, just enumeration.
2. **Verify (fan-out)** — one agent per claim, each with a clean context, checks that single claim against ground truth (the codebase, the cited sources, the data). Each returns: claim, verdict (supported / refuted / unsupported), evidence, and a confidence.
3. **Source-check (optional second layer)** — a separate agent confirms each *source* is real and high-quality, catching confident citations of things that don't exist.
4. **Synthesize** — merge into a claim-by-claim report, surfacing every refuted or unsupported claim with its evidence.

## Fill these in

- **Document** — what's being checked, and where it is.
- **Ground truth** — what each claim is checked *against* (this repo? specific files? web sources? a dataset?).
- **Claim scope** — all claims, or only technical/factual ones (skip opinion and forward-looking statements).
- **Stop condition** — every extracted claim has a verdict.
- **Output** — inline annotations, a separate report, or PR comments on the offending lines.

## Defaults

- Extraction: one Opus/Sonnet agent. Per-claim verification: Sonnet (Haiku if checks are shallow lookups).
- Separate verifier per claim — never let the extractor also judge.
- Budget: scales with claim count; cap it and log if you sample rather than check all.

## Ready-to-fire example

> Use a workflow to verify my blog draft at `draft.md`. First extract every technical claim about
> the codebase as a list. Then, for each claim, spawn a separate agent that checks it against the
> actual code in this repo and returns supported / refuted / unsupported with the file:line
> evidence. Don't let the extracting agent judge its own list. Synthesize a claim-by-claim report
> and flag everything not fully supported. Use about 80k tokens.
