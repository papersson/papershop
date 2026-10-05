# Propose an explainer

Read `pedagogy.md` and `levels.md`. Settle what the viewer should learn before investing in narration
and scenes. Use existing user authorization; a routine correction to an approved direction does
not require another permission loop.

1. Create the folder with `studio new NAME --drive author|learner [--source REPO] [--level …]`.
   Read `research/house.md` if present, the learner model, and any existing Decisions. House style
   is a creation-time snapshot; explicit video choices and the current user's instructions win.
2. Record the topic/question in the user's words, audience and prior knowledge. Ask about the
   drive only if it cannot be inferred: author knows the subject; learner needs correctness checked.
3. Gather evidence before settling the answer. A specified repo is the primary source: read the
   implementation, record paths and commit/content hashes, and run it where possible. For an
   unfamiliar general subject, use independent research passes with neutral questions: standard
   examples, prerequisites, mechanisms, assumptions, misconceptions, disputed claims and sources.
   Use fresh contexts when available; record uncertainty rather than inventing independent review.
4. Draft one learning brief and causal chain. For exhaustive requests, split main-story and
   reference coverage explicitly. Estimate both durations and justify scope against the target.
5. Show the narrative and risks for the user's approval, unless they already authorized proceeding
   without that gate. Author corrections are binding; learner drive additionally needs subject
   verification. A narrative review may use `studio review VIDEO 1 --narrative FILE`; competing
   narratives are for an explicit thorough investigation, not the default.

## research/narrative.md

Use this structure in either drive:

```
# Working title
Audience: background and prerequisites
Target: N minutes main story; M minutes optional reference

## Learning brief
- Model delta: Before … After …
- Opening question and payoff: …
- Key ideas: …
- Recurring example: …
- Wrong model or missing link: …
- Transfer questions: three new cases (answers kept separately)

## Chain
| Chapter | Question/limitation | New idea | New prediction | Local closure | Evidence | Time |
|---|---|---|---|---|---|---|

## Cut on purpose
- What is omitted or moved to reference, and why

## Vocabulary
- Canonical terms and any misleading substitutes to avoid

## Evidence plan
- What will be run, captured or verified

## Decisions
- Date, authorization, changes and reasons
```

The build gets this narrative, sources and the learner model. SCRIPT.md's Argument snapshots the
learning brief. Keep them consistent; record material direction changes in Decisions. Append
“After cut N” decisions rather than erasing old ones. A reviewer may flag a wrong claim, but
requests to add interesting detail are declined unless a learning dependency breaks without it.
