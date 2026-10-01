# Levels: how deep a video goes

video.json's `level` decides what a video is for. Pick it with the drive, before anything else.

## intro (the default)

An undergrad explainer: what a good lecturer's first lecture on a topic, or a 3Blue1Brown-style
piece, would teach. The viewer leaves able to explain three or four big ideas to a friend, and
nothing else is required of them.

Why it is the default: a search video built the deep way (a real 47,000-document dataset, six
review rounds, every measured number on screen) was "a barrage of details" to its learner: "the
details are probably correct, but it's just way too much!" It explained the evidence instead of
the ideas, a lab report where a lecture was wanted. Every rule below answers part of that.

1. **Ideas first, then mechanism, then numbers.** Write the 3–4 big ideas before anything else,
   one sentence each, at the top of `research/narrative.md` and SCRIPT.md's Argument. The user
   approves these (or the build proceeds on them when the user said to go ahead). Every later
   line is tested against them: a line that serves none of them is deleted.
2. **One idea per chapter**, plus a short opening (one relatable failure) and a close that answers
   it. Four to six chapters.
3. **A toy example you can see.** A handful of items that fit on screen (five short documents,
   two customers, one request), used from the first chapter to the last. Real data appears at most
   once, as "and it holds at scale", and only if it is quick to get right.
4. **A number budget: two or three on screen in the whole video,** none required. A number that
   doesn't make an idea land stays in the Evidence table.
5. **Intuition before formulas.** Show what a mechanism does; a formula, if it appears at all,
   comes last as a summary of what was watched.
6. **True, without the caveats a beginner doesn't need.** Never say anything false; one "real
   systems add more" line beats ten exceptions.
7. **About five minutes** (roughly 700–800 words of narration). Longer only when an idea needs it.

How it is built (fast is part of the level; budget: first cut 20 minutes, a revision round 5):

- **No research passes** for a canonical topic you know; verify the few specific claims you state
  (a default value, an attribution) or leave them out. Research passes are for an unfamiliar
  topic, a repo, or a deep-dive.
- **One-shot planning.** Write the big ideas, the toy example, the chapter list, and SCRIPT.md
  (narration with *Screen:* notes) in one pass, then one written self-check, logged in the Review
  log: every big idea has its chapter and its picture; the deletion test against the big ideas;
  the number count; every factual claim sure or cut; the opening's question answered at the end.
  No reviewer rounds and no competing narratives; the user's notes on the cut are the review.
- **Scenes from the kit's blocks** (`Box`, `Card`, `Link`, `Panel`, `Term`, `Stack`, `span`, `lin`
  from `@studio`): one strong diagram per chapter that builds up, rather than many elements.
- **Checks**: `studio check`, and a look at a handful of stills from the cut (overlaps, empty
  frames, a picture a sentence early). Sheets and a fresh frame review are for a deep-dive, or a
  video going to other people.

## deep-dive

The evidence-heavy build: research passes, measured runs on real data, reviewer rounds to the
gate in explainer.md Stage 5, sheets, the craft critique and a fresh frame review. For a viewer who
asked for depth, a video for an expert audience, or a subject where being exactly right matters
more than being quick. Budget: first cut 60 minutes, a revision round 10. `"thorough": true` adds
competing narratives and six review rounds on top.
