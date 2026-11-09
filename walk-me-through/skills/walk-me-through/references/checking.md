# Checking

A page is done when all three checks pass, in this order. Each catches what the one before cannot.

## 1. The checker prints nothing

```
python3 -I scripts/check.py OUT_DIR
```

It loads the page with `?check` in headless Chrome at 2000x1150, 1440x900 and 1280x720 and prints
one line per problem, exiting 1 on any:

- a click that changes no object, or more than one (a `clear` may hide many and change nothing else)
- a click whose named object is not the one that changed
- a caption over 12 words, with two sentences, a question, a dash or a semicolon, or too wide for
  one line
- text that overlaps other text, runs off the stage, or sits in the caption band
- a highlight selector that matches nothing, or points at something hidden
- a stage that does not fit the window, letterboxed
- a page error: an unknown object or state, a bad tree path, a script error
- drift from the approved `clicks.json`: a different number of clicks, chapter titles, a caption,
  an object or a state
- prose anywhere on the stage (titles, captions, labels, notes) with a dash or a semicolon

A note about placeholders left does not fail the check, but a page with placeholders is not done.

The checker sees text boxes, not meaning. It cannot see a ring framing empty space, a crowded
picture, or a caption that does not match its picture. That is check 2.

## 2. You have looked at every screenshot

```
python3 -I scripts/shoot.py OUT_DIR --out shots --mid 3,8 --strip
```

This writes every click finished at the three sizes, the chosen clicks frozen mid-motion,
`strip.png` (every click as a small multiple, with its caption) and `captions.md`. Open every image
yourself (the strip first, for the whole argument at a glance) and look for what a script cannot
see:

- more than one thing moving in a mid shot
- a ring framing empty space, missing the change, or covering a neighbour
- a crowded or boxy picture: containers where nothing is contained, words in boxes instead of data
- a label that explains (it belongs in the caption)
- a caption that does not match its picture, or repeats it
- a number that differs from the script that computed it

Then be the hostile tester for a minute in a real browser: resize the window, press Back after a
glide, open `page.html#7` fresh, turn on reduced motion, press C and N.

## 3. A fresh reader can explain it back

Give a reader who has not seen the page or the conversation only the finished screenshots at one
size with their captions (`shots/captions.md`, or `shots/strip.png`). A subagent works. Ask:

1. In three sentences: what does it explain, how does it work, and what is the one thing to
   remember?
2. Which screen confused you?
3. Which caption could you not connect to its picture?

Compare their three sentences with what the page was meant to land, written down at the grounding
stage. If they miss the point, fix the click list (order, a missing click, a chapter doing two
things), not the wording. Re-approve the changed list with the reader, rebuild those clicks, and
run all three checks again.

## Then open it

Open the page for the reader (`page.html`, from disk, no server) and tell them the keys in one
line: arrows or a click to move, C hides captions, N shows notes, `#N` links to a click.
