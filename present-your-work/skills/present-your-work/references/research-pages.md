# The research-time pages

A project that runs for days keeps three short pages beside its records, brought up to date at every
checkpoint. They exist because the hardest parts of a presentation are hardest at the end: by then
the writer can no longer tell which of the work's names an outsider lacks, the last days outweigh
the first in memory, and the distance to the goal has to be reconstructed from a journal. Written
while the work runs, each page costs minutes; reconstructed at the end, it costs the presentation
its shape (`case-eventlearn.md`). Olah and Carter call the cost of unexplained work research debt,
paid by every later reader; these pages pay it down as the work goes.

| Page | Holds | Updated | present-your-work uses it for |
|---|---|---|---|
| `GOAL.md` | the ultimate goal, the measured distance, obstacles, ranked next steps, what would change the plan | at every checkpoint, and when a decision changes the distance or the ranking | the card's Goal, Distance, Obstacles, Next and the last line |
| `GLOSSARY.md` | every label the work coins, with the plain words a presentation uses instead | when a label is coined | the labels the check refuses (`--glossary`), and the plain words that replace them |
| `EXPLAINER.md` | one page, in plain words, of what the project is and what it has found | rewritten, not appended to, at every checkpoint | the background chain and the reader-facing wording |

None of them is a presentation. They are working pages for the people and agents inside the work,
written so that a presentation can start from them.

## GOAL.md

```
# Goal

The ultimate goal: [one sentence, in the commissioner's words]
How it is measured: [the measure, the set it is measured on, and the level that counts as reached]

## Where the work stands ([date], [the run or file the figure comes from])
[The measure now, against the goal's level and against the last checkpoint.]

## What stands in the way
- [obstacle]: [the evidence for it; known or suspected]

## Next steps, ranked
| Rank | Step | Expected gain | Cost | Evidence for the gain |
|---|---|---|---|---|
| 1 | | | | |

## What would change the plan
- [a result, and the reordering it would cause]
```

The distance is the goal's own measure, not a proxy for it. When the goal cannot yet be measured,
the page says so and names the measurement that would do it; that measurement is often the first
next step.

## GLOSSARY.md

```
# Glossary

| Label | Plain words in a presentation | Meaning in the records |
|---|---|---|
| dev40 | the 40 clips used during development | fixed subset of development clips, splits/subsets_v1.json |
| the spotter | a first pass that marks the moments where the ball may have been touched | the touch-time model r1-tcn5 |
```

A label is any name the work coins: run names, set names, stage, tool and file names, nicknames for
an effect ("crowded misses"), and ordinary words used in a private sense ("the sheet", "the check").
The last kind matters most, because no heuristic can find it: the check script sees an ordinary word
as a label only when this page lists it. The first column is what the script reads; several labels
in one cell are separated by commas. Add the row when the label is coined, not at the end, when
the writer no longer notices it as a label.

## EXPLAINER.md

One page, about 600 to 900 words, for the default reader: an intelligent outsider from a
neighbouring field. It follows the five questions in brief: what the project is for, where it
stands, what it has learned, what stands in the way, what comes next. It uses no label from the
glossary and passes the medium check:

```
python3 scripts/check_draft.py EXPLAINER.md --size medium --glossary GLOSSARY.md
```

Rewrite it whole at each checkpoint rather than appending to it, so that its emphasis follows the
weight of the findings and not their order. An agent that did not do the latest work is the better
writer for it, from `GOAL.md`, the records' standing summary and the glossary.
