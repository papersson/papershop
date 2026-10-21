---
name: present-your-work
description: >
  Present a stretch of work to a reader who was not there, at the size the work earned: a few
  paragraphs in chat after a task of an hour or two, a one-page memo after a day, an article with
  an appendix and a story for a studio video after a multi-day milestone. The story is fixed on a
  card before any prose; the text answers a thesis defense's five questions (the goal, where the
  work stands against it, what was learned, what stands in the way, what to do next); a separate
  pass cuts; a script checks labels and budgets; a cold reader checks the shape. Use when asked to
  "present your work", "what did you do", "write it up", "report", "make a video of this", or at
  the end of an autonomous task. Not for a changelog, a commit message, or a style edit of
  existing prose (that is `prose`).
---

# present-your-work

A presentation of autonomous work is a checkpoint, not an ending. Its reader should finish it able
to say what the goal is, how far the work is from it, what was learned on the way and what comes
next. The first draft has to get that shape right; later rounds are for details. Three things make
that likely: the story is fixed on a card before any prose exists, a pass whose only job is to cut
follows the draft, and the checks test whether a stranger can retell the story rather than whether
the facts are on the page.

Paths below are relative to this file's folder.

## Pick the size

The user's word wins. Otherwise read the length of the work from its records: the first and last
dated entries, the commit range, the sessions.

| Size | The work | Output | Main-text words | New terms | Numbers |
|---|---|---|---|---|---|
| small | a task of an hour or two | a few paragraphs in chat | 150 to 300 | 0 to 2 | up to 3 |
| medium | about a day | a one-page memo, Markdown or HTML | 600 to 900 | up to 5 | up to 8 |
| large | a multi-day milestone | an article page with an appendix, and a story file for `studio` | 2,500 to 4,000 | up to 10 | about 25 |

The budgets apply to the main text. The appendix has none; it holds whatever a checker or a
successor needs.

## Inputs

- The raw records: journals, decision logs, result files, diffs and commit messages. When the work
  left no records, the `worklog` plugin reconstructs an activity log from the session transcripts.
- The research-time pages, when the project keeps them (`references/research-pages.md`). `GOAL.md`
  gives the card's goal, distance, obstacles and ranked next steps; `GLOSSARY.md` lists the labels
  the work coined with the plain words that replace them; `EXPLAINER.md` is a plain-words account
  to take the background chain from.
- Never an earlier presentation of the same work. It carries the earlier draft's order, emphasis
  and labels into the new one, and its errors with them. Read it afterwards, if at all, to learn
  what the reader last saw.

## The steps, in order

Each step finishes before the next starts. `references/method.md` has the detail and a worked
example for steps 1 to 6, `references/checks.md` for steps 7 to 9, `references/outputs.md` for
step 10. At the small size the first six steps take minutes together, and the writer may check its
few numbers against their sources itself; steps 7 and 8 run at every size.

### 1. Model the reader in three lines

Who reads it; what they already know; what they care about. The default reader is an intelligent
outsider from a neighbouring field: a statistician for a machine-learning project, a sports
scientist for a football one. When the reader is the person who commissioned the work, add two
lines: the goal they set, in their words, and what they last saw. Every later choice, such as which
terms to define and which comparisons to give, is made for this reader.

### 2. Distill the story card

Before any prose, write the card, at most 150 words:

```
Goal:      the ultimate goal, in the reader's words
Question:  what this stretch of work asked
Answer:    one sentence
Results:   three, chosen by weight across the whole period
Distance:  how far the work is from the goal, measured where possible
Obstacles: what stands in the way
Next:      the next steps, ranked by expected gain and cost
Would change the plan: the result that would reorder the next steps
```

Choose the three results after listing everything done with its date and its weight, which is how
much it moved the answer, the distance or the plan. Then check the list for recency: if the three
come from the last fifth of the period, write down why the weights put them there. The last days
are the most vivid to the writer and seldom the most important to the reader. The card is the
presentation's spine: every section serves one of its lines, and a section that serves none goes
to the appendix.

### 3. Build the background chain

List, in order, what the reader must know to follow the one-sentence answer, and nothing more.
Introduce each idea with a concrete example before its name: show one missed event on one clip
before calling anything a miss. Prefer plain words to terms, and coin no names in the main text.
The budget of new terms (small 0 to 2, medium up to 5, large up to 10) is a test of the answer as
much as of the text: an idea that does not fit is either not needed for the answer or a sign that
the answer is too complicated for this size. Replace every label in `GLOSSARY.md` with its plain
words.

### 4. Set the structure

The main text answers five questions, in this order:

1. What is the goal, and why does it matter?
2. Where does the work stand against it?
3. What did we learn that changes how we think about it?
4. What stands in the way?
5. What should be done next, ranked by expected gain and cost, and what result would change the
   ranking?

One limitations section follows, then the appendix. Approach and method appear only as far as the
results need them: the reader needs to know how a score was measured to trust it, not the order in
which the tools were built. A small presentation answers the five questions in a few paragraphs
without headings; a medium one gives each a short section; a large one may give question 3 a
section per result on the card.

### 5. Draft within the budgets

Write against the budgets for words, new terms and numbers. Each number in the main text comes with
its comparison and its meaning: "it now finishes by 05:40, against 08:50 the week before and a
deadline of 07:00, so the deadline is met with an hour to spare". Write quantities the reader must weigh as
numerals and counts that only structure the text in words ("three results"), so the check sees the
first kind. Open each paragraph with its point. Put what the reader already holds at the start of a
sentence and the new information at its end. Mark each new term where it is defined, with `<dfn>`
or italic or bold, and use italic and bold for nothing else, so the check can find definitions.

### 6. Subtract

A separate pass whose only job is to cut and to move material to the appendix. It adds nothing but
pointers ("five other changes were tried and none helped; Appendix C lists them"). It removes:

- chronology ("first we tried, then"), unless the order is itself the finding;
- everything tried that did not change the answer, beyond one sentence;
- internal detail: run names, file paths, parameters, tool names;
- repeated caveats, since each limitation is stated once, in the limitations section;
- definitions and numbers the answer does not need.

Record the word count before and after. A paragraph that serves no line of the card is cut or
moved whole, not shortened. When the pass finds a structural fault, such as an answer that first
appears in the third section, go back to step 4 instead of patching.

### 7. Run the mechanical checks

```
python3 scripts/check_draft.py DRAFT --size small|medium|large [--glossary GLOSSARY.md] [--known TERM]
```

It reads Markdown or HTML and checks the main text for internal labels (the glossary's, and tokens
that look coined: letters mixed with digits such as dev40 or B8, snake_case, camelCase, file names,
acronyms the draft does not define), for terms used before the draft defines them (a term defined
only in the appendix counts), for new terms and numbers per section against the budget, and for
the word count against the size. It prints a short report and exits non-zero when a rule is broken.
Fix a failure by replacing a label with plain words or moving the passage to the appendix, never by
adding a definition: a defined label is still a label. Pass `--known` for a term the reader model
says the reader already has. `references/checks.md` says what the script counts and what it cannot
see.

### 8. Run the cold-reader teach-back

Give a fresh agent only the draft's text, pasted into its brief, with no tools and no project files.
It must not be a fork, which inherits the writer's context. Ask it for three sentences (the goal, the
finding, the next step) and a list of every term or step it had to guess; the prompt is in
`references/checks.md`. Compare its sentences with the card's Goal, Answer and Next. A mismatch
means the structure is wrong: the answer is buried, the goal is never stated, or the ending lists
options without ranking them. Fix the structure, not the wording, and repeat with a new agent.
Replace each guessed term with plain words or move it out.

Model readers fill gaps from what they already know and do not get lost, so the teach-back checks
the shape of the story, not whether a person can follow it. A human reader new to the work is the
stronger check; when one is available, ask them for the same three sentences after one reading.

### 9. Check every number

A separate agent that did not write the draft checks every number in the main text and the appendix
against its source file or run, and returns disagreements as findings, not fixes. Correct the
number. When the check shows that a claim needs a qualification, the qualification goes into the
limitations section, never into the sentence that carries the number. Run step 7 again after the
fixes, since fixes add words.

### 10. Deliver by size

- Small: the text in chat and nothing else.
- Medium: a one-page Markdown file or HTML page, published as an artifact where the platform
  offers one.
- Large: an article page holding the main text, the limitations section and the appendix, and
  `STORY.md` for `studio`: the card, the background chain and the vocabulary in studio's narrative
  format (`references/outputs.md`). A video of the work starts from that file.

For medium and large, the reply that delivers the page gives the card first, so the reader can judge
the spine in a minute, then the link, then one line each on the checks: the script's result, the
teach-back's three sentences against the card, and the fact check.

## Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| Internal labels (dev40, "the spotter", B8) | The writer has used them for weeks and the reader meets them cold; defining them adds length without removing the need. |
| Chronological narration | It follows the order of the work, not the order of understanding, and the answer arrives last. |
| Listing everything tried | Each attempt costs attention and few change the answer; one sentence and the appendix carry them. |
| A caveat in every sentence | Qualifiers bury the claim and read as doubt about all of it; one limitations section states each once. |
| Numbers without a comparison | A bare number means nothing to an outsider; the comparison is the finding. |
| Recency over importance | The last days are vivid to the writer and crowd out the weeks that decided the answer. |
| Background after its use | A reader who meets a term before its explanation holds a gap open or rereads. |
| Sections that do not lead back to the goal | The reader cannot tell a detour from the argument. |
| Ending on results without the way forward | Without the distance to the goal and the ranked next steps, the reader cannot decide anything. |

## Where the rules come from

`references/sources.md` gives each rule's source: the thesis defense and the Heilmeier catechism for
the five questions, Minto's pyramid principle for the answer first and the card, Gopen and Swan for
the order within a sentence, Mayer's principles of multimedia learning for the background chain and
the cutting, Olah and Carter's "Research Debt" for the research-time pages, and the curse of
knowledge for the labels and the cold reader. `references/case-eventlearn.md` is the failure the
skill was built from, and `DESIGN.md` gives the reasons for its shape.
