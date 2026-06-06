# Template: rank

Sort or triage N items by a qualitative measure Claude is good at judging — support tickets by
severity, resumes by fit, bug reports by impact, ideas by quality. Use when there are too many
items to rank reliably in one prompt (quality degrades and it won't fit in context).

## Graph and verifier

Primitives: scatter-gather or a loop holding a tournament bracket → barrier (merge order) → diamond
(re-check the top K with fresh agents). Verifier: the rubric is the signal; it's a **soft** verifier,
so the stop condition is "every item placed and the top K survive an independent re-check," never a
fake boolean. BLOCKED: if the rubric proves underspecified mid-run (judges can't apply it
consistently), return that rather than ranking on a rubric you're inventing.

## Shape

Comparative judgment, because pairwise comparison is more reliable than absolute scoring. Two
viable structures:

- **Tournament / pairwise** — a deterministic loop holds the bracket; each comparison is its own
  agent judging two items. Only the running order stays in context. Best when you need a precise
  ordering of the top.
- **Bucket-rank then merge** — fan out: each agent scores a slice of items against a shared
  rubric into coarse buckets (e.g. P0–P3), then merge buckets and order within them. Faster for
  large N when you need tiers more than an exact 1..N order.

Then **double-check the top K** with a fresh agent, since that's where the decision actually lands.

## Fill these in

- **Items** — what's being ranked, and where the list is.
- **Rubric** — the explicit criteria for "higher." If the user can't articulate it, interview them (this is a good place for `AskUserQuestion` to build the rubric).
- **Output granularity** — full ordering, or tiers/buckets?
- **K** — how many of the top to re-verify carefully.
- **Stop condition** — every item placed; top K double-checked.

## Defaults

- Pairwise comparisons: Sonnet. Final top-K re-check: Opus.
- Always re-verify the top K with an agent that didn't produce the ranking.
- Budget scales with comparison count; for large N prefer bucket-rank to keep it bounded, and
  log the bucketing so a silent cap doesn't read as a full ordering.

## Ready-to-fire example

> Use a workflow to rank the 80 resumes in `./resumes/` for the backend role. First interview me
> with AskUserQuestion to build the rubric. Then bucket-rank in parallel — each agent scores a
> slice against the rubric into strong / maybe / no — merge, and order the strong bucket by
> pairwise comparison. Then have a separate agent carefully re-check the top 10 against the rubric.
> Output a ranked shortlist with one-line justifications.
