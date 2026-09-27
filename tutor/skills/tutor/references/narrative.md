# The narrative stage

The narrative is the bottleneck. A build with a weak narrative produces a polished video of the wrong argument, and nothing downstream (reviewers, animation, voice) can fix it; a build with a strong one mostly renders it. So the narrative is settled, in the open, before any script is written, and the build only starts on the learner's explicit approval.

The stage has two tracks, chosen by one question: **how well does the learner know this topic?** Ask it first, plainly ("Are you fairly expert here, or is this new to you?"). Their answer decides who is qualified to judge the narrative.

## Before either track

1. **Pin down the lesson** as a topic or a question in the learner's words, without the answer. "How B-trees keep disk lookups fast" is a lesson; "how a high branching factor trades comparisons for I/Os" is already content and would steer the research. Record the audience (default: the learner model's Background) and the target length.
2. **Read the learner model** (`learner.md`): what they know, what earlier lessons lost them on, standing instructions. A narrative that repeats what they know, or re-explains what they've already been taught, wastes the video.
3. **Research in fresh contexts.** Two passes with the same neutral prompt (the lesson, the audience, and the research questions in build.md Stage 1), one a web-research subagent, one `claude -p` started in an empty folder. Save both under `research/`. Do this before drafting anything, because a context that holds a draft anchors every later judgment to it. Where the passes disagree, check a primary source.

## The narrative document

Whichever track, the narrative is one file, `research/narrative.md`, in this shape:

```
# {{Working title}}
Audience: ...   Length: about N minutes
Question: the specific question the opening raises
Answer: how the ending answers it
Takeaway: one or two sentences

## Chain
1. **{{Chapter}}** ({{duration}}) — Claim: ... Why it follows: ... Evidence: ... Terms: ...
2. ...

## Cut on purpose
- ... (and why)

## Evidence plan
- what will be run or measured, and what it must show

## Decisions
- {{date}}: the learner said ...; changed ...   (co-author track: every correction, so later rounds can't undo it)
```

Show the chain as claims, not chapter titles. "Chapter 3: the loop" tells the learner nothing; "Chapter 3 — Claim: repeating the request→result step until the model stops is what 'agent' means. Why it follows: one step fixed nothing in chapter 2. Evidence: a real 12-request run" lets them see whether the link holds.

## Co-author track (the learner knows the topic)

Iterating with an expert is cheap, so optimise for fast, precise rounds.

- Draft one narrative from the research and show it. Ask at most three questions, only ones whose answer changes the narrative.
- Log every correction under `## Decisions`. Reviewers and the build agent read this file; a decision the learner made is not reopened by a reviewer's SHOULD FIX.
- Offer one "grill me" pass if they want it: stress-test the chain for the weakest link, the claim most likely to be overstated, and the chapter a newcomer would skip.
- Repeat until they say build. Don't start the build on "looks good, maybe change X": apply X, show it, then ask.

## Trust track (the learner is new to the topic)

The learner cannot check correctness, so the agents have to earn trust, and the narrative has to be judged by reviewers before the learner sees it.

1. **Competing drafts.** Draft two or three narratives, each in its own fresh context (`claude -p` in an empty folder, given only the research reports, the audience and the learner model), so one framing does not anchor the others. Ask each for a different organising choice (e.g. history-first vs mechanism-first; one worked example vs a survey).
2. **Review the narratives**, not the scripts: `kit/review.py LESSON 1 --narrative research/narrative_A.md` runs the narrative expert, student and editor (prompts in `kit/reviewers/narrative_*.md`). This is far cheaper than reviewing a full script, and it catches the errors that matter most: a wrong claim, a non-canonical order, a chain the student can't follow.
3. **Choose or merge** against stated criteria: the expert's blocking findings (none allowed), the student's verdict (FOLLOWABLE), the editor's chain test, and the learner model. Write the reasons down.
4. **Show the learner** the chosen narrative, why it won, what was rejected, and a short list of **risk flags**: claims a reviewer doubted, places the student got lost, anything that could not be verified against a primary source. The learner doesn't need expertise to judge whether this is what they want to learn, and they can veto or redirect.
5. Log their decision, then build.

## What both tracks hand to the build

`research/narrative.md` with an approval line at the end ("Approved by the learner on {{date}}"), the research reports, and the learner model. The build agent treats the chain and the Decisions section as fixed: it may sharpen wording and fix what research shows is wrong, and it must report any deviation in the Review log.
