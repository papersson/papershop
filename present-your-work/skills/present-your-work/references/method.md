# From records to a draft: steps 1 to 6

Read this when a step in SKILL.md needs more than its paragraph. One invented example runs through
the file: a nightly data load that finished too late for the analysts, made faster in an afternoon.
`scripts/samples/pass-small.md` is its small presentation.

## 1. The reader model

Three lines, and two more when the reader commissioned the work:

```
Reader:   the head of analytics, who asked for the change
Knows:    what the load produces and when the analysts start; not how it reads its files
Cares:    whether mornings are safe, and what it costs to keep them safe
Goal set: "the data ready when the analysts arrive"
Last saw: the request, a week ago
```

The model decides three things later on. A term the reader knows needs no definition and does not
count against the budget (pass it to the check with `--known`). A comparison must be on a scale the
reader has: the analysts' start time, not seconds per file. Material the reader does not care about
goes to the appendix, however much it cost.

When the reader is unknown, take the intelligent outsider from a neighbouring field. They read
carefully and know their own field's methods, but none of the project's history, names or tools.

## 2. The story card

| Line | Rule | The failure it prevents |
|---|---|---|
| Goal | The ultimate goal, not the task; one sentence in the reader's words | A presentation of activity with no measure of success |
| Question | What this stretch asked, phrased so that it has an answer | Sections that report without arguing |
| Answer | One sentence a reader could repeat to a colleague; it holds the main number and its comparison | An answer spread across sections |
| Results | Three, by weight across the whole period | Recency, and lists of everything |
| Distance | The goal's own measure, now, against the goal's level; if unmeasured, say so and name the measurement | A checkpoint that cannot be compared with the next |
| Obstacles | What stands in the way, one sentence each; known ones apart from suspected ones | Next steps that do not follow from anything |
| Next | Ranked by expected gain and cost, each with its evidence | An outlook that lists ideas |
| Would change the plan | The result that would reorder the next steps | A plan nobody could prove wrong |

The recency check. Before choosing the results, list everything the period did:

| Date | What was done | What it changed |
|---|---|---|
| day 1 | measured where the load spends its time | located the slow step: rereading unchanged files |
| day 1 | tried a faster disk | nothing measurable; dropped |
| day 1 | skipped unchanged files by fingerprint | moved the finish from 08:50 to 05:40 |
| day 1 | found that a format change resets every fingerprint | named the remaining obstacle |

"What it changed" is one of: the answer, the distance, the plan, or nothing. Choose the three
heaviest. If all three come from the last fifth of the period, write one line saying why the
weights put them there. Over a three-week project the last two days will feel heavier than they
are, because the writer remembers them best and the commissioner discussed them last.

The card for the example, 126 words:

```
Goal:      the data ready before the analysts start at 07:00
Question:  why the nightly load finished late, and what makes it finish early
Answer:    the load spent its time rereading files that had not changed; skipping them moved the
           finish from 08:50 to 05:40
Results:   the slow step located; unchanged files skipped; a format change still forces a full reload
Distance:  goal met on five of five nights, with more than an hour to spare
Obstacles: a provider format change resets every fingerprint, without warning
Next:      1. a test for the fingerprint check (an hour, protects the gain)
           2. reload by season (a day, limits a format change to one season)
Would change the plan: an earlier start for the analysts makes step 2 the first
```

## 3. The background chain

Start from the Answer. Mark every idea in it that the reader model does not hold, then ask what each
of those depends on, until you reach what the reader knows. Order the links so that nothing is used
before it is introduced.

| # | Idea | The example that introduces it | Name, if one is needed | Needed for |
|---|---|---|---|---|
| 1 | Most files do not change from one night to the next | last night, 12 of 3,400 files changed | none | why rereading is waste |
| 2 | A file's contents can be summarized in a short code that changes when they change | two copies of one file give the same code; one changed byte gives another | fingerprint | how the skip works |

Rules for the chain:

- The example comes first and the name second, and a name is given only when the text uses it
  again. Most links need no name.
- A label from `GLOSSARY.md` never enters the chain; its plain words do.
- A term defined only in the appendix but needed in the main text is either moved into the main
  text, at its first use, or replaced with plain words.
- If the chain does not fit the budget of new terms, shorten the Answer before stretching the
  budget. The budget is the fixed side; the Answer adapts to it.

## 4. The structure

| Question | small | medium | large |
|---|---|---|---|
| 1. The goal and why it matters | one or two sentences | a short paragraph | a section, with the reader's stake in it |
| 2. Where the work stands | the Answer and the Distance | a paragraph with the main comparison and at most one figure | a section with the main figure |
| 3. What was learned | the three results in a sentence each | a section, one paragraph per result | a section per result, each with its evidence |
| 4. What stands in the way | one or two sentences | a short section | a section |
| 5. What to do next | the ranked steps | a short ranked list with gain and cost | a ranked table with gain, cost, evidence, and what would change it |
| Limitations | a clause, if any | a short section | a section, each limitation once |

A test for method text: for each sentence about how something was done, name the result that needs
it. A sentence that no result needs moves to the appendix.

The appendix, in the order a checker uses it: a glossary from the work's labels to the plain words
the main text uses, so that a reader can cross from the appendix to the article; the runs and their
names; methods in full; everything tried; full tables; the chronology; how to reproduce.

## 5. Drafting

- The answer comes first, at every level: in the summary, in each section's first paragraph, in
  each paragraph's first sentence (Minto). Support follows the point it supports.
- Within a sentence, the topic position (the start) holds what the reader already has, and the
  stress position (the end) holds what is new. Keep the subject close to its verb (Gopen and
  Swan).
- A number sentence has three parts: the number, its comparison, and what the comparison means for
  the goal. A number that has no comparison worth giving goes to the appendix.
- A figure serves one line of the card, and its caption says what to see in it, not only what it
  shows.
- A heading in a large presentation may state its section's finding rather than its topic: "The
  load is now an hour early" rather than "Results".
- A new term is marked once, where it is defined, with `<dfn>`, italic or bold. Italic and bold are
  not used for emphasis, so every mark the check finds is a definition.

## 6. The subtraction pass

Read the draft against the card, paragraph by paragraph, and ask which line of the card each
paragraph serves. A paragraph that serves none is cut or moved whole to the appendix. Then go
through the draft once for each of these, in this order:

1. Chronology. "First", "then", "after that", "on Tuesday" and dated sentences mark it. Rewrite in
   the order of the argument; keep a date only where the order is the finding.
2. Everything tried. Attempts that did not change the answer become one sentence with a pointer:
   "Four other changes were tried and none helped (Appendix C)."
3. Internal detail. Run names, file paths, parameters, command lines and tool names move to the
   appendix; the main text says what the thing does.
4. Repeated caveats. Each limitation is stated once, in the limitations section. A qualifier in a
   main-text sentence ("may", "in this setting", "on these clips") goes there unless the claim is
   false without it.
5. Unneeded definitions and numbers. Anything the background chain does not list, and every number
   beyond the budget, moves to the appendix.

The pass adds nothing except pointers to the appendix. Record the word count before and after it;
the delivering reply reports both. A pass that finds a structural fault, such as an answer that
first appears in the third section, sends the draft back to step 4.
