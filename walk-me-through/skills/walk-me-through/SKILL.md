---
name: walk-me-through
description: >
  Explain one mechanism as a local click-through HTML page: each click changes exactly one thing on
  a stage drawn from the real data (a tree for nested data, a value as a value, code as code), and
  one caption line of at most 12 words says what it means when the picture cannot. Decides first
  whether a sentence would do, writes the whole page as a click list for approval, builds from it,
  then checks it with a script, screenshots and a fresh reader. Use when someone says "show me how
  X works", "walk me through this", "I don't get it", "explain it visually", or asks to turn a deck
  or document into a walkthrough. Not for a one-line answer, a comparison of options or a lookup.
---

# walk-me-through

A page that a colleague who did not get something reads in twenty clicks and can explain back.
Every rule below has its reason in `references/principles.md`; each exists because a page failed
without it. Paths are relative to this file's folder. Run scripts with `python3 -I`; they need only
Python 3 and a Chrome or Chromium (`WALK_CHROME` points at one).

**First, should this be a page?** Answer in text when it fits in a sentence, when the reader is
comparing options, or when they are looking something up. A page is for a mechanism with steps.

## 1. Ground

Write down who reads it, what they already know, and what did not land. Find the raw material:
real data, real code, real output, not a summary. Pick one running example and keep it for the
whole page. Compute every value the page will show with a small script, never from memory.

## 2. Click list

Write the page as chapters and clicks: each click names the one thing that changes, plus a caption
of at most 12 words only where the picture cannot say it. Show the reader the markdown from
`new_page.py clicks.json --markdown` and change it until they approve. Format and what makes a good
list: `references/click-list.md`, which also covers converting a deck (a faithful copy first).

## 3. Build

`new_page.py clicks.json OUT_DIR` writes a page that runs at once, one placeholder per click. Replace
placeholders one at a time with real pieces and states (`references/visuals.md`, and the format in
`engine/walk.js`'s header). `assets/example/` is a finished page, `assets/pieces/` a tour.

## 4. Check

`check.py OUT_DIR` prints nothing. You have looked at every shot from `shoot.py OUT_DIR --mid 3,8
--strip`. A fresh reader, given only the shots and captions, explains it back. Then open the page.
Details: `references/checking.md`.

## The rules in one breath

One change per click. One caption line, one sentence, 12 words, only when needed. One highlight, on
the part that changed, after the motion settles. Labels name data. The data is the picture, boxes
only when containing is the point. Real values only. Plain chapter titles. No controls on the
stage. A deck has a cover. The stage is 1600 by 900, scaled. Plain words, no dashes or semicolons.
Motion carries meaning: no bounces, no gradients, no sound.

## Files

`engine/walk.js`, `walk.css` (copied into every page) · `scripts/new_page.py`, `check.py`,
`shoot.py`, `walklib.py`, `test_walk.py` · `references/principles.md`, `click-list.md`,
`visuals.md`, `checking.md` · `assets/example/` (hash table, with `values.py`) · `assets/pieces/`.
Keys on a page: arrows, space, Page Up and Down, Home, End or a click move. C hides captions, N
shows notes, and `page.html#12` opens click 12 finished.
