# The narrative stage

At the intro level (the default; `references/levels.md`) most of this page collapses: show the
user the 3–4 big ideas and the toy example, plan in one pass, and self-check; no research passes
for a canonical topic and no narrative reviews. What follows is the deep-dive path, and the parts
that hold at every level (the narrative document, Cut on purpose, Vocabulary, Decisions).

The narrative is the bottleneck. A build with a weak narrative produces a polished video of the
wrong argument, and nothing downstream (reviewers, animation, voice) can fix it; a build with a
strong one mostly renders it. So the narrative is settled, in the open, before any script is
written, and the build starts only on the user's explicit approval.

The drive decides who can judge it. Ask plainly: "Do you know this well, or are you learning it?"

## Before either drive

1. **Create the video**: `studio new NAME --drive author|learner [--source REPO]`.
2. **Pin down the video** as a topic or a question in the user's words, without the answer. "How
   B-trees keep disk lookups fast" is a topic; "how a high branching factor trades comparisons
   for I/Os" is already content and would steer the research. Record the audience and a target
   length. Aim for what the argument needs: past videos ran 4½ to 8 minutes, and the two longest
   (10–11 minutes) were liked least. One question per video.
3. **Read the learner model** (`$STUDIO_HOME/learner.md`, or video.json's `learner`): what they
   know, what earlier videos lost them on, standing instructions. For a video meant for someone
   else (a stakeholder cut), write that audience's model and point video.json's `learner` at it.
4. **Gather sources.**
   - A repo or knowledge base the user points at is the primary source. Explore it before
     drafting (delegate wide reads to a search agent and keep its summary), and record the paths
     that each claim will rest on. `studio new --source` stores the repo's commit.
   - For a general topic, run research in fresh contexts: two passes with the same neutral prompt
     (the topic, the audience and the research questions in `explainer.md` Stage 1), one a
     web-research subagent, one `claude -p` started in an empty folder. Save both under
     `research/`. Where they disagree, check a primary source.
   - Do this before drafting anything: a context that holds a draft anchors every later judgment.

## The narrative document

Whichever drive, the narrative is one file, `research/narrative.md`:

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

## Vocabulary
- term: definition. Banned substitutes: ...

## Evidence plan
- what will be run or measured, and what it must show

## Decisions
- {{date}}: the user said ...; changed ...
```

Show the chain as claims, not chapter titles. "Chapter 3: the loop" says nothing; "Chapter 3 —
Claim: repeating the request→result step until the model stops is what 'agent' means. Why it
follows: one step fixed nothing in chapter 2. Evidence: a real 12-request run" lets the user see
whether the link holds.

**Cut on purpose** and **Vocabulary** are the charter: `studio review` gives them to every
reviewer, and a finding that reopens them is declined. In one build, drift in terms ("rebuild" for
the canonical term, "held" for "quarantined") was the most common correction, and reviewers who
asked for "a little more explanation" doubled a planned six-minute video to twelve.

**Decisions** is versioned: when the user revises after a cut, append a section ("## After cut 3")
rather than editing old ones. Newer sections override older ones where they conflict, and every
agent, including a resumed one, reads this one file for the binding state. Never attribute a
preference to the user that is not written here.

## Author drive (the user knows the subject)

Iterating with an expert is cheap, so optimise for fast, precise rounds.

- Draft one narrative from the sources and show it. Ask at most three questions, only ones whose
  answer changes the narrative.
- Log every correction under Decisions. A decision the user made is not reopened by anyone.
- Offer one stress-test pass: the weakest link in the chain, the claim most likely to be
  overstated, the chapter a newcomer would skip.
- Repeat until they say build. Don't start on "looks good, maybe change X": apply X, show it, ask.

## Learner drive (the user is learning the subject)

The user can't check correctness, so you have to earn their trust; but they can judge, in a few
minutes, whether a story is the one they want to learn. Their approval replaces the hour that
competing drafts and narrative reviews took.

1. **One draft** from the research reports, written after both reports are in (a fresh context if
   your own has a framing to shake off).
2. **One narrative review round** (`studio review VIDEO 1 --narrative research/narrative.md`: the
   narrative expert, student and editor, in parallel). It is cheap, and it catches the errors that
   matter most: a wrong claim, a non-canonical order, a chain the student can't follow. Fix what
   it finds; don't run a second round unless the expert found a blocking error.
3. **Show the user** the narrative, and a short list of **risk flags**: claims a reviewer doubted,
   places the student got lost, anything not verified against a primary source. Ask at most two
   questions. Log their decision, then build.
4. Their questions during the loop get answers in chat; a question that shows a gap in the video
   also becomes a change.

If the user has said to go ahead without them, the review round stands in for their approval:
record that in Decisions and build. Competing drafts (two or three narratives in fresh contexts,
each with a different organising choice, reviewed and then chosen or merged against stated
criteria) are for `"thorough": true` only.

## What the build gets

`research/narrative.md` with an approval line ("Approved by the user on {{date}}"), the sources
or research reports, and the learner model. The build treats the chain, the charter and Decisions
as fixed: it may sharpen wording and fix what the sources show is wrong, and it reports any
deviation in SCRIPT.md's Review log.
