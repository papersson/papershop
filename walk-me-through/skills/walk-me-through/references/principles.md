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

## Attention

One change per click says what moves. These rules say where the eye goes, which is a different
question: a page where only one thing moves at a time can still look like a dashboard, every value
ever shown at full brightness, the new one a small square among them. The reader should never have
to search. Their eyes go to the thing they need to attend to, and everything around it is blank or
quiet.

**One subject per click, and brightness points at it.** The subject is the object the click
changes, and the engine draws it at full ink. The subject of the click before steps down to the
second tone, and everything older is quiet. At most one thing is at full ink and two at the second
tone. *Why:* contrast is what the eye goes to first, before it reads anything (Treisman's
pop-out; Mayer's signalling principle). A tone that falls with age also tells the reader what is
new without a word.

**The subject is the part that changed.** When the change is inside a large object (one bucket of
a table, one row of a tree), the piece lights that part itself and fades the rest, so the bright
thing is exactly where the change is. A highlight ring is the last resort, for a part the piece
cannot light. Never glow, pulse, a second accent colour or an arrow that is not the motion itself.
*Why:* a ring on a dim stage is a second pointer competing with brightness, and a ring around a
whole object points at nothing.

**Size is importance.** The subject is large enough to find at a glance, never a tick mark or a
digit on its own: give a small result its context (the mark goes on the row it judges). *Why:*
Hitchcock's rule that the size of a thing in the frame should match its importance to the story at
that moment. A small bright thing still makes the eye hunt.

**The next subject appears where the eye already is.** Put it near the last one, or carry the eye
there with one visible motion: the thing itself travels, or a line draws. A chapter's first click
may start anywhere. *Why:* Walter Murch's eye trace. A cut that sends the eye across the frame
with nothing to follow costs the viewer the first moment of the new shot.

**A consequence elsewhere is its own click.** When one change causes another somewhere else (a
count, a second panel), the second waits for its own click. Where real events overlap, show them
one at a time, then once together, so the order of telling is not taken for the order of the
mechanism. *Why:* the eye can follow one place at a time, and a sequence teaches a sequence.

**Draw an absence.** When the point is that something did not happen (no reply, an empty slot, a
list that ends), draw it and give it its click. *Why:* the reader cannot see a thing failing to
appear.

**Nothing on the stage that no click is about.** Every object is the subject of some click, or is
marked `context` (an axis, a frame of reference) and stays quiet. No legends, counters or
reminders the clicks do not need. *Why:* Doumont's signal-to-noise law. Everything on the stage
competes for the eye, so anything that is not the signal is noise.

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
thing at a time, and the brightness steps settle with it. *Why:* Frank Thomas and Ollie
Johnston, *The Illusion of Life*: staging presents one idea so it is unmistakable, easing makes
motion read as physical, timing carries meaning. The beat of "motion, settle, step down, caption" is the
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
