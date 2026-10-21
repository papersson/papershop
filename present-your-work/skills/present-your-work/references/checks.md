# The checks: steps 7 to 9

Three checks, each with a different kind of evidence. The script is deterministic and cheap, so it
runs first and again after every change. The teach-back tests the story's shape with a reader who
knows nothing of the work. The fact check tests every number against its source. None of them adds
text to the main body: their findings are fixed by replacing, moving or cutting.

## Step 7: the script

```
python3 scripts/check_draft.py DRAFT --size small|medium|large \
    [--glossary GLOSSARY.md] [--known TERM ...] [--known-file FILE] [--all]
```

For a small presentation in chat, write the text to a scratch file first. The script uses only
Python's standard library. It exits 0 when every rule holds, 1 when one is broken and 2 on a usage
error. `python3 scripts/test_check_draft.py` runs its tests.

| Rule | What it counts | What it leaves out |
|---|---|---|
| words | Words of prose in the main text: paragraphs, lists, captions, sidenotes | Headings, tables, figures, the appendix, notes, references, a table of contents, hidden elements |
| terms | Distinct terms first defined in the main text: `<dfn>`, a short italic or bold span, a `<dt>`, an acronym in "long form (ABC)" | Terms passed with `--known`; run-in headings ("*Scope.* The work..."); spans of more than five words |
| numbers | Distinct numerals in the main text, tables included, with units, percentages and clock times | Years, ISO dates, citation brackets, references such as "Section 4" or "Figure 2", spelled-out numbers, numerals inside labels |
| labels | The glossary's labels; letters mixed with digits (dev40, B8, r1-tcn5); snake_case; camelCase; file names and paths; acronyms neither common, known nor defined. Headings and figure text count | Numbers with units (35s, 1080p), ordinals, citation years (2019a), common acronyms (GPU, PDF, UEFA), terms passed with `--known` |
| order | A term used in the main text before its first definition, or used there and defined only in the appendix | Uses in headings, the appendix and the back matter |

What the draft does so the script can see it:

- Mark each new term once, where it is defined, and use italic and bold for nothing else.
- Start the appendix with a heading that begins "Appendix", a heading whose id begins `app-` or
  `appendix`, or the comment `<!-- appendix -->`. Name back matter "Notes" or "References".
- Write quantities the reader must weigh as numerals.

What it cannot see:

- A label that is an ordinary word ("the sheet", "the check") unless the glossary lists it. This is
  the main reason to keep `GLOSSARY.md` while the work runs.
- An everyday word used in a technical sense without a mark.
- A number spelled out, or a number with no comparison.
- Whether a definition is clear, or whether the chain is in the right order beyond first use.

How to fix what it reports:

| Finding | Fix |
|---|---|
| A label | Replace it with its plain words from the glossary, or move the passage to the appendix. Never add a definition. |
| A term before its definition | Move the definition to the first use, or replace the earlier use with plain words. A term defined only in the appendix is moved into the main text or replaced. |
| Too many terms | Replace terms with plain words, or drop the ideas the Answer does not need. |
| Too many numbers | Keep the numbers on the card and their comparisons; move the rest to the appendix. |
| Too many words | Repeat step 6 on the sections with the most words per line of the card. |

The script's thresholds are the skill's budgets. The word ranges are approximate, so ten percent
either side passes; the other budgets are maxima.

## Step 8: the cold-reader teach-back

Brief a fresh agent, not a fork, with this prompt and the draft's text pasted in place. For an HTML
draft, paste the visible text, not the markup.

```
Read the document below once, as someone who has never heard of this work. Use no tools and read
no files: everything you have is below.

<document>
[the draft's text]
</document>

Answer in this form:

1. Three sentences: what the goal of the work is; what it found; what should be done next.
2. Every term, abbreviation, name or step you had to guess at, each with your guess.
3. The first sentence at which you knew what the document was arguing, quoted.
```

Compare the three sentences with the card:

| Card | Teach-back | When they differ |
|---|---|---|
| Goal | sentence 1 | The goal is stated late, or stated as a task. Open with question 1 of the structure. |
| Answer | sentence 2 | The answer is buried behind method or chronology, or a secondary result is louder. Put the answer in the first paragraph and the results in the card's order. |
| Next | sentence 3 | The ending lists options without ranking them, or ends on results. End on the ranked next steps and the result that would change them. |

A finding retold with hedges ("it seems that", "may") points at caveats left in main-text
sentences. Many guessed terms point at a gap in the background chain or a budget overrun. The
quoted sentence in answer 3 should be in the first paragraph; if it is not, the opening does not
state the answer.

A structural fix is followed by a new teach-back with a new agent. The same agent remembers the
earlier draft and fills the new one's gaps from it.

The teach-back's limit. Model readers fill gaps from general knowledge and do not get lost, so a
model that retells the story correctly shows that the story is on the page and in order, not that a
person could follow it. In the eventlearn case three model readers scored 10 of 10 on a
comprehension quiz in every round while the first human reader could not follow the article
(`case-eventlearn.md`). The guess list is the teach-back's most useful output for that reason: it
records where even a gap-filling reader had to guess. When a person new to the work can read the
draft, ask them for the same three sentences after one reading, without help, and treat their
answer as the stronger evidence. The writer's own sense that the text is clear is no evidence: the
curse of knowledge makes a known meaning look obvious.

## Step 9: the fact check

Brief a separate agent that did not write the draft. Give it the draft, the list of every number in
the main text and the appendix with the source the writer used for each (a file, a run, a query),
and access to those sources. Ask it to recompute each number with its own code where it can, and to
return disagreements as findings, not fixes.

| Outcome | Action |
|---|---|
| Correct | none |
| Wrong | correct the number, and its comparison if that changes |
| No source | find one or remove the number |
| Correct but needs a qualification | the qualification goes to the limitations section, not into the sentence |

Rerun the script after the fixes. A fact check that leaves more caveats in the main text than it
found is the failure the case file describes: every check added and nothing subtracted.
