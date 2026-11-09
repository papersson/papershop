# The rules, each with its reason

Every rule here exists because a page failed without it. A page that "seems fine" without one is
the case the rule was written for: the failure shows up in a reader who quietly stopped following,
not in the author's own read-through. Keep them all. Where a rule comes from someone's work, the
name is there so a maintainer knows what to read before changing it.

## Before building

**Decide whether a page is right at all.** Answer in text when the answer fits in a sentence, when
the reader is comparing options (a table does that better), or when they are looking something up.
A page is for a mechanism someone did not get: a thing with steps, where each step changes
something you can see. *Why:* a skeptic who asked a one-line question would rather have the line
than twenty clicks. A page that should have been a sentence costs the reader minutes and costs the
skill its credibility.

**One running example, kept for the whole page.** Pick one real case (one key, one request, one
order) and follow it to the end. *Why:* a new example per chapter makes the reader start over each
time. Bret Victor's ladder of abstraction: start concrete, see the concrete thing work, and climb
to the general rule only after.

**Real values only.** Every value on the page comes from data, a run or the code, computed by a
small script and never from memory. A made-up example on a real mechanism is fine when the page
says once that it is an example. *Why:* one wrong number makes the careful reader distrust every
other number, and they are the reader who would have explained it to others.

**Write the click list before building.** The whole page as chapters and clicks in words, shown to
the reader and approved. *Why:* the story reel. Nobody at a studio animates before the reel is
approved, because a drawing is cheap to change and an animated shot is not. A line in a list costs
seconds to change, a built click costs an hour.

## On the stage

**One change per click.** Exactly one object changes on each click. *Why:* if two things move at
once the eye has to choose and misses one. Richard Mayer's segmenting principle: learners
understand more when a mechanism is broken into learner-paced pieces. The reader sets the pace, so
splitting one beat into two costs nothing. A click that changes nothing is also a mistake: if a
click feels like padding, cut it or fold its idea into a neighbour's caption, but never put two
motions back into one click. A custom piece that changes several of its own parts on one class (a
table filling, entries staggered) is still one change: one idea, one gesture.

**Text in one place.** All narration is one caption line at the bottom centre: one sentence, at
most 12 words, replaced on every click and never stacked. No side columns, no paragraphs under the
picture, no captions scattered next to objects. *Why:* hunting for words around the stage is tiring
and pulls the eye off the picture. A caption that needs two sentences means the click is doing two
things.

**A caption only when the change needs words.** A cause, a consequence, what a number means, a rule.
When a value appears with its name, the picture already said it: leave the line empty. The first
click of a chapter usually needs one. A run of similar reveals needs one on the first at most.
*Why:* Mayer's redundancy principle. Captions that repeat the picture train the reader to skip
captions, including the ones that matter.

**One highlight.** The thing the click changed gets the page's single highlight ring, arriving as
the motion settles. Point it at the part that changed (the row, the value), not the whole object.
Skip it when the motion already points, as a glide does. *Why:* Mayer's signalling principle. The
caption says what, the ring says where. A ring on everything, or on a whole card, points at
nothing.

**Labels name data.** Text on objects only names things: a field, a version, an axis. *Why:* a
label that starts to explain is a caption in the wrong place, and it breaks "text in one place".

**The data is the picture.** A tree for nested data, a chip for one value, code as code, a custom
piece for anything else. Use type, space, colour and motion for hierarchy, and a container only when
containing is the point (a bucket holds entries, so it may contain, but a value needs no box).
One colour per meaning, set once per page, plus one highlight colour that means "what changed" and
nothing else. *Why:* Edward Tufte. Ink spent on frames and decoration is ink not spent on data.
Flat rounded boxes with words in them are the failure this skill exists to avoid: they show that
there are parts, not how the parts work.

**Motion carries meaning.** Objects glide between states with eased motion (slow in, slow out), one
thing at a time, and the ring arrives after the motion lands. *Why:* Frank Thomas and Ollie
Johnston, *The Illusion of Life*: staging presents one idea so it is unmistakable, easing makes
motion read as physical, timing carries meaning. The beat of "motion, settle, ring, caption" is the
rhythm of the page. Motion for its own sake (bounces, spins, confetti) is tacky, and so are gradients
competing with the data, and sound.

**The last chapter is often the same thing as code.** Shown last, once the reader already
understands it, with margin numbers that are the clicks which showed each line. *Why:* Grant
Sanderson (3Blue1Brown) and Amit Patel (Red Blob Games) show the formula or code after the
intuition, so the code reads as a summary instead of a wall.

## Page furniture

**Plain chapter titles.** Short plain sentences, no numbers in front. *Why:* numbers are noise at
the top of every screen, and the corner count already says where you are.

**No controls on the stage.** No Back and Next buttons, no progress dots, no "arrow keys work too".
Arrow keys, space, Page Up and Down, Home and End, or a click on the stage move. A quiet "x/N" in a
corner says where you are. *Why:* controls take space and look cheap, and the reader finds the
arrow keys on their first try.

**A deck has a cover.** A page that will be presented opens on a large title or question with no
caption, and the count starts after it. *Why:* a presenter needs a screen to stand in front of
while people settle.

**Presenting live.** Captions are for someone reading alone. C hides them so they do not compete
with a speaker, and N shows the chapter's speaker notes in a side panel.

**The stage scales.** Everything is laid out on a fixed 1600 by 900 stage, scaled to the window and
letterboxed. Check at three sizes. *Why:* a page laid out for one screen breaks on the next one,
and the colleague you send it to has a different screen.

**Every click has an address.** `page.html#12` opens click 12 finished, and Back plays the last
change in reverse. *Why:* the state at click N is computed, not accumulated, so links and Back are
free, and readers who try them are pleased when they just work.

**Plain writing.** Plain words, no em dashes, no semicolons, no rhetorical questions. Say what is
measured and what is an example. The checker enforces the punctuation. *Why:* the caption line has
12 words to spend, and a dash or a semicolon is two sentences pretending to be one.

## Checking

**Nobody trusts the author's claim that it works.** A hostile tester resizes the window, presses
Back, opens click 7 from a link, turns on reduced motion and checks every number against its
source. A fresh reader sees only the screenshots and captions and has to explain the topic back.
*Why:* the author knows what each click means and sees it in the picture whether or not it is
there. See `checking.md`.
