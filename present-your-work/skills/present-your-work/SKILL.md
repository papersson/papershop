---
name: present-your-work
description: >
  Present finished work to the person who asked for it, in the chat, in under a minute, the way a
  colleague would tell them: a few short paragraphs that open on the goal and what is now true,
  say why it was done this way and what the key idea is, put the one thing that could change their
  mind beside the answer, and end on what they now have to decide or do. A one-second script flags
  private labels, budgets, superlatives, log-like telling and the marks of machine-written prose.
  A visual mode tells the same story as a click-through page with one change per click, for when
  the person asks to be shown. Use at the end of a task, or when asked "present your work", "what
  did you do", "write it up", "report back", "summarize what you did" or "show me what you did".
  Not for a changelog, a commit message, or a style edit of existing prose (that is `prose`).
---

# present-your-work

Doing the work and making it understood are different jobs. A finished task usually ends with an
activity log ("updated the middleware, refactored validation, added tests, all pass") that is
accurate and leaves the reader no wiser. They can't tell what is now true, why it was done this
way, or what they have to do next.

This skill is about the second job, the exposition. The reader should come away knowing what
changed, why it was done this way, the idea that made it work, and what is theirs to decide. It
is not an audit. Don't argue for the work or prove it: say what's true and why. If the reader
wants proof, they'll ask, and then you give it.

Paths below are relative to this file's folder.

## Quick mode: in the chat, in under a minute

The reader is in the conversation and knows the request. Write from what is already in context:
the request, the session, the diff, the commands that ran and their output. Do no new research
and start no subagents. Budget: 15 to 60 seconds.

### 1. Fill the card in your head

| Line | What goes in it |
|---|---|
| Goal | the request, in the reader's words |
| Answer | what is now true, as a plain statement, with its main comparison |
| Why | what the diff cannot show: the problem behind the request, the alternative rejected, the tradeoff accepted |
| Key idea | what a colleague would need to know to have done it themselves; "routine" when there is none |
| The catch | the one limitation, gap or departure from the request that changes what the reader should do |
| Opaque | anything that works but is not understood, if there is any |
| Next | what the reader has to decide or do, ranked, and what would change the order |

Leave a line empty rather than inflate it: most tasks have no key idea and nothing opaque.
`references/quick.md` has each line's rule and a worked example.

### 2. Write it the way you'd say it

Write the text to a scratch file as if you were telling the person across a desk what you did. It
has this shape, in 60 to 300 words and no headings, but the shape is never spelled out in the text:

1. **The goal and the answer, then the catch.** One clause of goal, then what is now true with its
   comparison ("by 05:40, against 08:50 the week before"), then the catch in the next sentence.
2. **Why, and the key idea.** Why this and not what the reader would have expected. When there is a
   key idea, state it plainly with one concrete case. Anything opaque goes here too.
3. **What the reader decides or does next,** ranked, with an if-then where a result would reorder it.

While writing:

- Explain, don't prove. Leave out test runs, commands and how you made sure, unless the reader
  asked or the catch is that something didn't work.
- Names from the code go in code spans: files, commands, functions. A name the session coined
  ("the v2 approach", "the fp trick") is replaced with plain words, never defined.
- Order by the argument, not by the session: no "first I, then I". What was tried and did not
  change the answer gets one sentence at most.
- Each number comes with its comparison and what it means for the goal.
- Neutral words: say what changed, not "robust", "comprehensive" or "seamless".
- Mark a new term once, where it is defined, in bold or italic, and use bold and italic for
  nothing else. At most two new terms.

The voice matters as much as the content: a report that reads like a model wrote it gets skimmed.
How the drafting goes decides most of it, because a later edit removes only a third of the tells,
so get it right in the first draft.

- Talk, don't announce. First person, contractions, plain words, full sentences.
- One idea per sentence, most under 25 words, with the length varied.
- No labels in front of sentences ("The catch:", "Next:", "Bottom line:"). Say it: "There's one
  catch." "What I need from you is…"
- No colon reveals ("The answer: it works"), no "not X, but Y", no em dashes, no groups of three
  for rhythm, no trailing "-ing" clause that comments on the sentence ("…, ensuring that…").
- Watch the words models overuse today: *specifically*, *essential*, *though*, *furthermore*,
  *vital*, *alongside*, *crucial*, *additionally*. One is fine; a cluster is a tell.
- No "checked", "verified", "validated" or "confirmed". They're the vocabulary of an audit, and
  this is an explanation.
- No sign-off, no summary of the summary, no offer of more help.

`references/voice.md` has three short reports in this voice, each beside the version a model writes
by default. Read one before your first report in a session.

### 3. Reread it as them, then run the script once

Read the draft once as the person hearing it. Edit only what you wouldn't say out loud to them and
what reads as written by a model; keep the meaning, the facts and the order. Then run:

```
python3 scripts/check_draft.py DRAFT [--glossary GLOSSARY.md] [--known TERM]
```

It runs in under a second and flags words, new terms, numbers, private labels, terms used before
their definition, superlatives, log-like telling and the voice tells above (`references/checks.md`).
Fix what it reports by replacing or cutting, never by adding a definition or a caveat, and run it
once more. Then paste the text into the reply as the reply's whole content: no preamble, no offer
of more.

## Visual mode: a click-through page

Use it when the person asks for it ("show me", "walk me through what you did", "make it visual"),
or offer it in one line at the end of a quick report when the work changed how something behaves
and a picture would show it better than prose. It is the same story as quick mode, told on a
stage: one change per click, a caption of at most 12 words, the eye always on one thing. It takes
longer, from a quarter of an hour to an hour, so it is never the default.

### 1. Fill the card, then pick the running example

Fill the same card as in quick mode. Then pick one real case that shows the change: one request, one
file, one night's run. Follow it from the first click to the last. Compute every value the page
will show with a small script (`values.py` beside the page), never from memory. If the case is
invented, the page's notes say so once.

### 2. Write the click list and get it approved

The story has a fixed order, one chapter each. Chapter titles name the parts of the click list and
never appear on the stage: the caption is the only line of words beside the picture, so the first
click of each chapter has a caption that says the chapter's point.

1. **The cover states the answer**, as one sentence: what is now true.
2. **Before.** The running example as it was, and why that was a problem.
3. **Why it was like that.** The cause, shown on the example. This is the place for the one
   prediction click (`"predict": true`), whose caption asks the reader to guess before the answer.
4. **The key idea**, shown on the example, concrete before any name.
5. **After.** The same example now, with before and after on screen together.
6. **The catch**, no later than here, shown on the example where it can be.
7. **What I need from you.** Two or three plain sentences, one per click: where it stands, what is
   open or opaque, and the decision.

Fold chapters together when the work is small, and leave the key idea out when there is none. Aim
for 8 to 20 clicks. Write the list as `clicks.json`, show the person
`python3 -I scripts/new_page.py clicks.json --markdown`, and change it until they approve it.
`references/visual.md` has the format and what makes a good list.

### 3. Build it

`python3 -I scripts/new_page.py clicks.json OUT_DIR` writes a page that runs at once, one
placeholder per click, with its own copy of `engine/stage.js` and `engine/stage.css`. Replace the
placeholders with real pieces one at a time; the format is in `engine/stage.js`'s header, and
`assets/example/` is a finished presentation with its `values.py`. Stage it for attention: the
engine draws each click's subject at full brightness and steps everything older down, so draw the
part that changed as the subject, large and near where the eye already is, and put nothing on the
stage that no click is about.

### 4. Look at it, then hand it over

- `python3 -I scripts/check_page.py OUT_DIR` prints nothing.
- You've looked at every shot from `python3 -I scripts/shoot_page.py OUT_DIR --mid 3,8 --strip`,
  the strip first.
- A fresh agent given `shots/attention.md` finds one place to look on every click. Fix what it
  points to.
- A fresh agent given only `shots/captions.md` and the shots says in three sentences what changed,
  why, and what the reader has to decide, and names the key idea. If they miss the point, fix the
  click list, not the wording.

Then open `page.html` for the person and tell them the keys in one line: arrows or a click to move,
C hides captions, `#N` opens click N.

## Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| An activity log | It follows the order of the work, and the answer arrives last or not at all. |
| Reciting the diff | The reader can read the diff; what they cannot read is why, and what it means. |
| Proof nobody asked for | Test counts, commands and "I made sure that" turn an explanation into an audit and push the point down. |
| The catch at the end, or not at all | The limitation that changes what the reader should do is the first thing they need after the answer. |
| A caveat in every sentence | Hedges bury the claim and train the reader to skip them; one catch, said once, beside the answer. |
| Labels from the session | The writer has used them for an hour; the reader meets them cold. |
| Superlatives | They praise the work instead of saying what it does. |
| Length | A longer report is skimmed, and it sounds surer than it is. |
| Labelled sentences and colon reveals | They read as a form being filled in, and they are the first thing a reader recognizes as machine-written. |

`references/sources.md` gives the sources behind each rule, and `DESIGN.md` the reasons for the
skill's shape.
