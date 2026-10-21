# Delivering by size: step 10

## Small: in chat

Two to four paragraphs, no headings, about 150 to 300 words. The first sentence holds the goal and
the second the answer with its comparison. The last paragraph gives the next steps in rank order and
the result that would change them. Nothing else goes into the reply: no list of files touched, no
log of commands, no offer of further help. A user who wants the detail asks, and the records hold
it. `scripts/samples/pass-small.md` is an example.

## Medium: a one-page memo

A Markdown file, or an HTML page published as an artifact where the platform offers one, of about
600 to 900 words in the main text:

- A title that states the answer, not the topic.
- A summary paragraph: the Goal, the Answer, the Distance and the first of the Next steps.
- Five short sections in the order of the five questions; headings may state each section's
  finding.
- A limitations section of a few sentences.
- Optionally a short appendix, or links to the records, for the run names, files and detail.

## Large: an article and a story

An HTML article page, published as an artifact where the platform offers one:

- A title and a summary paragraph that tells the card in prose.
- The main text in the order of the five questions, about 2,500 to 4,000 words, with question 3
  split into a section per result where the results need room.
- One limitations section.
- The appendix, introduced by a heading that begins "Appendix" or an id that begins `app-`, in the
  order a checker uses it: the glossary from labels to plain words, the runs, methods in full,
  everything tried, full tables, the chronology, reproduction.
- New terms marked with `<dfn>` where they are defined.

Beside the article goes `STORY.md`, which `studio` reads when a video is made of the work. It holds
the card, the background chain and the vocabulary in studio's narrative format
(`research/narrative.md` in a studio video). Studio takes it as the draft of its narrative, fills in
what only a video needs (what is on screen, the hero moments, the timing), and still puts the
narrative to the user for approval. The story file never adds facts the article lacks, so the video
and the article tell one story.

| present-your-work | studio's narrative |
|---|---|
| The reader model | Audience |
| Question and Answer | Learning brief: Opening question and payoff |
| Goal, Distance and Next (the takeaway) | Learning brief: Model delta, as its "After" |
| The three results | Learning brief: Key ideas |
| The chain's first concrete example | Learning brief: Recurring example |
| The background chain, then the five questions | Chain, one chapter per link or section |
| The article's numbers with their sources | The Chain's Evidence column |
| What went to the appendix | Cut on purpose |
| The terms kept, and the glossary's labels | Vocabulary, the labels listed as substitutes to avoid |

The template:

```
# [Working title: the answer in a few words]
Audience: [the reader model's lines]
Target: [minutes for the main story, settled at studio's narrative approval]
Source: present-your-work story of [date], from [the article's path or link]

## Learning brief
- Model delta: Before, [what the viewer lacks or believes]. After, they can say what the goal is,
  how far the work is from it, and what comes next: [the takeaway in one sentence].
- Opening question and payoff: [the Question]; [the Answer].
- Key ideas: [result 1]; [result 2]; [result 3]
- Recurring example: [the chain's first concrete example]
- Wrong model or missing link: [the intuition the chain corrects, if there is one]
- Transfer questions: left to studio

## Chain
| Chapter | Question/limitation | New idea | On screen (picture, camera, sound) | New prediction | Local closure | Evidence | Time |
|---|---|---|---|---|---|---|---|
| 1 The goal | [why it matters] | [the goal] | left to studio | | | [source] | |
| 2 [chain link] | [what the viewer cannot yet follow] | [the idea, example first] | left to studio | | | | |
| ... | | | | | | | |
| n Where it stands | [the question] | [the Answer and the Distance] | left to studio | | | [run or file] | |
| n+1 What stands in the way | | [the obstacles] | left to studio | | | | |
| n+2 What to do next | | [the ranked next steps] | left to studio | [the result that would change them] | | | |

## Cut on purpose
- [what the article's appendix holds, in a line each, and why the video leaves it out]

## Vocabulary
- [term]: [the definition the article gives]
- Avoid [label]; say [its plain words]

## Decisions
- [date]: drafted by present-your-work from the story card; awaits the narrative approval
```

## The delivering reply

For medium and large, in this order, in a few lines:

1. The card, as written in step 2.
2. The link or path to the page, and to `STORY.md` for large.
3. The checks, one line each: the script's result with its counts; the teach-back's three sentences
   against the card, and how many terms it guessed; the fact check's findings and their fixes.
4. The word count before and after the subtraction pass.
