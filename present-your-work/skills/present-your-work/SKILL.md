---
name: present-your-work
description: >
  Present finished work to the person who asked for it, in the chat, in under a minute: a few
  short paragraphs that open on the goal and the answer, say why it was done this way and what the
  key idea is, put the one limitation that matters beside the answer, tie every claimed check to
  its evidence, and end on what the reader now has to decide or do. A one-second script checks
  labels, budgets, superlatives, unbacked claims, unnamed test changes and log-like telling. Use at
  the end of a task, or when asked "present your work", "what did you do", "write it up", "report
  back" or "summarize what you did". Not for a changelog, a commit message, or a style edit of
  existing prose (that is `prose`).
---

# present-your-work

Doing the work and making it understood are different jobs. A finished task usually ends with an
activity log ("updated the middleware, refactored validation, added tests, all pass") that is
accurate and leaves the reader no wiser: they cannot tell what is now true, why it was done this
way, how sure to be of it, or what they have to do next.

A presentation of finished work has two jobs. It lets the reader **check** it: what is true, how
each claim is known, what is not known. And it lets the reader **learn** from it: the idea that
made the work go, which they could reuse. Fluent prose makes readers trust whether or not the work
is right, and length makes them trust more without making them more accurate, so the presentation
is built to make checking cheaper than trusting, and it stays short.

Paths below are relative to this file's folder.

## Quick mode: in the chat, in under a minute

The reader is in the conversation and knows the request. Write from what is already in context:
the request, the session, the diff, the commands that ran and their output. Do no new research
and start no subagents. Budget: 15 to 60 seconds.

### 1. Fill the card in your head

| Line | What goes in it |
|---|---|
| Goal | the request, in the reader's words |
| Answer | what is now true, as a claim that could be false, with its main comparison |
| Why | what the diff cannot show: the problem behind the request, the alternative rejected, the tradeoff accepted |
| Key idea | what a colleague would need to know to have done it themselves; "routine" when there is none |
| The catch | the one limitation, unverified point or departure from the request that changes what the reader should do |
| Opaque | anything that works but is not understood, if there is any |
| Next | what the reader has to decide or do, ranked, and the result that would change the order |

Leave a line empty rather than inflate it: most tasks have no key idea and nothing opaque.
`references/quick.md` has each line's rule and a worked example.

### 2. Write it

Write the text to a scratch file in this shape, 60 to 300 words before the evidence list, no
headings:

1. **The goal and the answer, then the catch.** One clause of goal, then the answer with its
   comparison ("by 05:40, against 08:50 the week before"), then the catch in the next sentence.
2. **Why, and the key idea.** Why this and not what the reader would have expected. When there is a
   key idea, state it plainly with one concrete case.
3. **What is not verified or not understood**, in a sentence or two, when there is any.
4. **What the reader decides or does next,** ranked, with an if-then where a result would reorder it.
5. **`Evidence:`** on its own line, then a short list: each command with its result, each file
   changed, in code spans. The reader checks the claims against this list.

While writing:

- Every claim that something passes, works or was verified carries its evidence in the same
  sentence: the command in a code span or the result as a number ("passes, `script/test`: 16
  tests"). Say "ran", "inferred" or "not run" where it matters.
- Names from the code go in code spans: files, commands, functions. A name the session coined
  ("the v2 approach", "the fp trick") is replaced with plain words, never defined.
- Order by the argument, not by the session: no "first I, then I". What was tried and did not
  change the answer gets one sentence at most.
- Each number comes with its comparison and what it means for the goal.
- Neutral words: say what was measured, not "robust", "comprehensive" or "seamless".
- Mark a new term once, where it is defined, in bold or italic, and use bold and italic for
  nothing else. At most two new terms.

### 3. Check it once

```
python3 scripts/check_draft.py DRAFT [--changed-from -] [--glossary GLOSSARY.md] [--known TERM]
```

Pipe the changed files in so the script can see changed tests:
`git diff --name-only BASE | python3 scripts/check_draft.py DRAFT --changed-from -`, with BASE the
commit the work started from. The script runs in under a second and checks words, new terms,
numbers, private labels, terms before their definition, superlatives, checks claimed without
evidence, changed test files not named, and log-like telling (`references/checks.md`). Fix what it
reports by replacing or cutting, never by adding a definition or a caveat, and run it once more.
Then paste the text into the reply as the reply's whole content: no preamble, no offer of more.

## Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| An activity log | It follows the order of the work, and the answer arrives last or not at all. |
| Reciting the diff | The reader can read the diff; what they cannot read is why, and what it means. |
| "All tests pass" with nothing beside it | A claimed check without its evidence costs the reader trust or a rerun; readers accept fluent claims whether or not they hold. |
| The catch at the end, or not at all | The limitation that changes what the reader should do is the first thing they need after the answer. |
| A caveat in every sentence | Hedges bury the claim and train the reader to skip them; one catch, said once, beside the answer. |
| Labels from the session | The writer has used them for an hour; the reader meets them cold. |
| Superlatives | They make the work sound checked without checking it. |
| Length | A longer report raises trust without raising accuracy. |

`references/sources.md` gives the sources behind each rule, and `DESIGN.md` the reasons for the
skill's shape.
