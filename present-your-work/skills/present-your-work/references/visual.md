# Visual mode in detail

Read this when you build a click-through presentation. `assets/example/` is a finished one: an
invented nightly load, made faster by skipping files that haven't changed. Its `clicks.json` is
the approved list, `values.py` computes every number on it, and `page.html` is the page.

## The click list

```json
{
  "title": "The nightly load now finishes before the analysts start",
  "cover": "The nightly load now finishes before the analysts start.",
  "chapters": ["Each night the load read every file", "Most files had not changed"],
  "notes": ["An invented example. values.py computes the numbers."],
  "clicks": [
    {"chapter": 1, "change": "The season's 40 files appear, all outlined as read",
     "caption": "Each night the load read all 40 files of the season.", "object": "files", "state": "read"},
    {"chapter": 2, "change": "The files lose their outline", "predict": true,
     "caption": "How many of these do you think changed since last night?"}
  ]
}
```

- `cover`: the answer, one sentence, what is now true. Required.
- `chapters`: plain short sentences, no numbers in front. A title can state the chapter's finding
  ("It now finishes at 05:49").
- `clicks[].change`: what the reader sees change, in words. If it needs "and", it's two clicks.
- `clicks[].caption`: optional, one sentence of at most 12 words, in the report voice: no colons,
  semicolons or dashes, nothing a person wouldn't say out loud. Leave it out where the picture says
  it.
- `clicks[].predict`: `true` on the one click whose caption asks the reader to guess before the
  next click answers. Asking first makes people take in the answer; asking twice is a quiz.
- `clicks[].object`, `state`, `with`: filled in while building. `with` keeps an object at the
  second brightness on a click whose subject must be read against it.

`new_page.py --markdown` prints the list the way the person will follow it, with one line per
problem. Show them that, not the JSON.

## What makes a good list

- **One real case from start to end.** The same file, request or run on every chapter, so the
  reader never starts over.
- **One idea per chapter.** A chapter title that needs "and" is two chapters.
- **Each click one visible change.** "The fingerprint of round-17 appears" is a click. "The file is
  fingerprinted" is not, because it doesn't say what the reader sees.
- **Before and after together.** The after chapter keeps a trace of the before on screen (a faint
  old marker, the old number beside the new), because a change is easiest to see as a comparison.
- **The catch shown, not told.** Where the catch can be drawn on the example, draw it.
- **The closing chapter in plain sentences.** Where it stands, what's open, and the decision, one
  click each, in the same voice as a quick report.
- **No proof.** No test runs, commands or counts of passing tests on the stage, unless the person
  asked for them.

## Staging for attention

The engine draws the subject of each click (the object it changes) at full brightness, the subject
before it at a second tone, and everything older quietly. It does the pointing for you, so the
work is in choosing what the subject is:

- **The subject is the part that changed.** When the change is inside a bigger picture (three files
  of forty), the piece lights those parts itself and fades the rest. A highlight ring is the last
  resort.
- **Large enough to find at a glance.** A tick mark or a lone digit makes the eye hunt. Give the
  payoff its own chapter and a large picture in the middle of the stage.
- **Near where the eye already is.** Put the next subject close to the last one, or let it travel
  there.
- **A consequence elsewhere is its own click.** When one change causes another somewhere else, the
  second waits for its own click.
- **Nothing on the stage that no click is about.** Mark a true frame of reference `context`; cut
  everything else.
- **Labels name things, in at most four words.** Explanations go in the caption.

`check_page.py` measures what it can: one thing at full ink, the subject's size, jumps across the
stage, text under 20 px, long labels, objects no click is about, captions in the wrong voice. It
can't see whether the picture means what the caption says. The screenshots and the two readers do.

## The pieces

`engine/stage.js`'s header has the full format. In short:

| The data | The piece |
|---|---|
| one value: a key, a time, a count | `chip` (a label naming it, the value large) |
| a record with named fields | `card`, with chips docking into `Stage.slot(card, state, field)` |
| nested data: JSON, a config | `tree` with `data`, lit and walked by path |
| code | `code`, lines lit with `lit:3-5` |
| a sentence on the closing screen | `text`, `size` 34 to 40 |
| anything with its own shape: a set of files, a time line, a queue | a custom piece from `Stage.piece(name, render)` that reacts to its state's classes |

A custom piece stays one object, so lighting part of it or moving its marker is one change per
click. The example's `files` and `clock` pieces are small complete ones.

## The fresh reader

Give a fresh agent (not a fork) only `shots/captions.md`, with the finished shots at one size,
and ask:

1. In three sentences: what changed, why it was done this way, and what the reader has to decide?
2. What is the key idea, in your own words?
3. Which screen confused you, and which caption could you not connect to its picture?

Compare the answers with the card. A wrong answer to the first two means the click list is wrong
(an idea missing, a chapter doing two things, the answer buried), so fix the list, have the person
approve the change, and rebuild those clicks.
