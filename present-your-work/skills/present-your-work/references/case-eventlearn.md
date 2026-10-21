# Case: the eventlearn article and video (2026-10-21)

The failure this skill was built from, condensed from a diagnosis written from the records of how
the article and video were made.

## What was asked and what was made

eventlearn was three weeks of autonomous research: a lead agent and its subagents built and measured
a language-model agent that logs every touch of the ball in broadcast football clips. The owner asked
for a conference-quality presentation for an undergraduate audience, then a video. Both passed every
check the process had, and both failed the one reader who mattered: the owner could not follow them.

## The six causes, and the rule each left

| Cause | What happened | The rule in this skill |
|---|---|---|
| No story before writing | The research kept a chronological journal of 45 numbered decisions and a ledger of 930 verified claims, and nothing else. The writer built the article bottom-up from them, so the text followed the order and grain of the work. No one-sentence answer or chain of ideas was agreed before a word was written. | The story card and the background chain come before any prose (steps 2 and 3); the research keeps `EXPLAINER.md` and `GOAL.md` as it goes. |
| Internal labels leaked | The work coined names (dev40, test40, E1, B8, the spotter, the sheet, receipt timing, crowded misses) and used them for weeks; the writer could not tell which ones an outsider lacks. The article defined many of them, which added length instead of removing the need. | Labels are replaced with plain words, never defined (steps 3 and 7); `GLOSSARY.md` records each label when it is coined; a script finds them. |
| Recency outweighed importance | The last two days (the owner's audit, the magnified ball) took a whole section and much of the abstract; three weeks of earlier work shared the rest. | The three results are chosen by weight across the whole period, with a recency check (step 2). |
| Every check added, nothing subtracted | Three figure checks, a scope review and two review rounds each found real errors, and each fix added a caveat, a qualifier, an interval or a number. The article grew to 6,500 words in the main text and 19,600 with appendices; the video script grew from a planned 7:45 to 10:15 over six review rounds. | A subtraction pass with no other job (step 6); budgets for words, terms and numbers; caveats go to one limitations section (step 9). |
| The comprehension gate was invalid | Three model readers scored 10 of 10 on a comprehension quiz in each round. Model readers fill gaps from what they already know and do not get lost, so the gate measured recall of facts on the page, not whether an outsider could follow the argument. The owner was the first real reader, and he saw nothing between the request and the finished article. | The teach-back asks for the story's shape and a list of guesses, and a human reader new to the work is the stronger check (step 8); the delivering reply leads with the card. |
| It ended on results | The outlook listed what might be tried. It did not say how far the work is from its goal, a human-level tagger, what stands in the way, or what to do next, ranked. | The five questions end on the obstacles and the ranked next steps, and the card names the result that would change the plan (step 4). |

## The script on the article

`scripts/check_draft.py --size large` on the published article (`paper/article/index.html` in the
football-analytics repository, as of commit 5fe6db1 of 2026-10-21) breaks all five rules:

| Rule | The article | The large budget |
|---|---|---|
| Words in the main text | 8,506 | 2,500 to 4,000 |
| New terms | 30 | 10 |
| Distinct numbers | 242 | about 25 |
| Internal labels | 16, among them dev40 (37 uses), dev20 (26), test40 (13), B8 and six audit item codes | none |
| Terms used before their definition | 36, of which 24 are defined only in the appendix glossary | none |

The script's word count includes figure captions, sidenotes and the header, which the diagnosis's
6,500 did not. Two of its labels are names from outside the project (GPT-6, FOOTPASS) that an
outsider also lacks, and F1 is a standard measure the undergraduate reader would need explained. It
does not see the labels that are ordinary words (the sheet, the check, receipt timing), because the
project kept no glossary; that is the case for `GLOSSARY.md`.
