# The explainer: from an approved narrative to a locked video

This is the procedure for an explainer, whoever builds it (you in author drive, a background agent
in learner drive). It records what earlier builds got wrong; keep the reasons when you change a
step. The narrative is approved (`propose.md`) before this starts, and its chain, charter and
Decisions are binding.

The script is the product and everything else renders it, so do no animation until the script is
locked. Commit after every stage and every cut, so an interrupted build resumes.

## Stage 1: Sources and research

The narrative stage gathered sources (a repo, or two fresh-context research reports). Read them;
research further only for a question they leave open.

Whatever sits in your context (a draft, an earlier framing) anchors your judgment, and the video
must teach established knowledge the way the standard sources teach it. The research questions,
for a fresh-context pass with a neutral prompt (never your ideas or a draft): the canonical worked
example and why it is standard (and the main competitor); the standard progression, and which
simpler version comes first; the standard model and notation, with clashes between fields; the key
results with exact formulas and assumptions; standard numeric examples; the misconceptions
students bring and how the canonical treatment corrects them; what is essential, a common extra, or
out of scope; real systems canonically cited, with their mechanism; claims commonly overstated;
which parts are best watched, which done, which read. Ask for citations, and for uncertain items to
be marked.

When the source is a repo, the code and its docs are the canon: read the implementation behind
every claim, run it where you can, and cite the file and commit.

Whenever you are about to rely on a fact you haven't verified in this session (a tool's default,
the exact text a tool prints, a formula's exact form), check it against a primary source or run it.

## Stage 2: The argument

Write SCRIPT.md (the template is already in the video folder), starting with the argument:

- **Question.** The specific question the opening raises. The strongest openings show a real,
  runnable demonstration with a surprising outcome.
- **Answer.** How the ending answers it, using the opening's own evidence.
- **Takeaway.** The rule the viewer leaves with, in one or two sentences.
- **Wrong model.** The intuition the audience brings that the video must dislodge.
- **Objectives.** Three or four things the viewer can do afterwards.
- **The chain.** One sentence per chapter, each joined to the next by "but" or "therefore".
- **Ledgers.** Setups and payoffs; vocabulary (every term, where first used, its definition, no
  synonyms afterwards, the narrative's banned substitutes); two or three numbers to remember.

Then a **Format** table: chapter, format, why. Timing, motion and things that build up suit
narrated animation; a skill is learned by doing; reference detail is read. Offer a chapter that
would be better as an exercise separately instead of adding it to the video.

## Stage 3: Evidence

- Every number spoken or shown comes from a run in this environment, a simulation written for this
  video, or a cited source. Typical published values are labelled as typical.
- Measure what the script compares, both quantities when it contrasts two.
- A number that depends on the setup is spoken as the setup's number, never as a general law.
- Choose the demonstration's parameters so the arithmetic the narration states is exact; fix the
  evidence rather than explaining a mismatch. (GNU sort with 100-byte records spent half its buffer
  on bookkeeping, so the runs didn't match the narration; 10,000-byte records fixed it.)
- One unit system everywhere (decimal MB and GB by default). Mixing `88M` (MiB) with a decimal file
  size produced an error an expert caught.
- If the script says a real system behaves a certain way, capture the real output and replay it:
  terminal sessions, query plans, file listings. Step-by-step animations replay an event log from a
  small instrumented implementation. Real captures and screenshots, when available, beat
  illustrations; record their source and capture parameters.
- Keep an Evidence table in SCRIPT.md: claim, how it was checked, value. Runs go in `sims/`, their
  outputs in `data/`, and scenes read `data/` rather than literals.

## Stage 4: The script

Narration is written for the ear: short clauses, parameter names spoken as words, formulas
described rather than read, at most one new number per sentence, and a reason given with a number
("eighteen doublings take you from one item to a quarter of a million"). Next to every paragraph,
write what is on screen (`*Screen:*`); those notes become the scene specifications.

The principles, each with a test:

1. **One question, answered with its own evidence.** The last minute refers back to the first.
2. **"But" and "therefore", never "and then".** Any "and then" marks a list or a tangent.
3. **Derive, don't reveal.** Before each new idea, a visible problem it fixes.
4. **Setups pay off, and payoffs are set up.** Check the ledger both ways.
5. **One vocabulary.** Defined where first used; no concept has two names.
6. **A budget of numbers.** Two or three to retain; the rest support them on screen.
7. **Concrete before abstract.** A formula summarizes something already watched.
8. **Show the wrong model failing,** don't argue against it.
9. **Depth over breadth.** One application understood beats five named.
10. **Words and pictures split the work.** The narration explains, the picture shows, on-screen
    text only labels.
11. **The deletion test.** Delete each line in turn; if nothing later breaks and the takeaway
    doesn't weaken, it goes.

Estimate about 150 words per minute. Watch time on lecture videos levels off around six minutes
(Guo, Kim and Rubin, 2014): two questions are two videos.

## Stage 5: Review (learner drive; optional in author drive)

`studio review VIDEO ROUND` runs three fresh-context reviewers, each in an empty folder:

- **Expert:** the script with screen notes, and the evidence table.
- **Student:** the learner model (background and standing instructions) and the script.
- **Editor:** the argument and chain, and the script, but not your ledgers.

All three also get the charter (Cut on purpose, vocabulary). Rules for the loop:

- After each round, revise and log every finding in the Review log: what changed, or why it was
  declined. Decline only for a reason a domain expert would accept.
- **A finding that asks for more explanation is declined unless the chain breaks without it**; log
  it as "declined: outside the chain". A finding that reopens the charter is declined the same way.
- Apply revisions with replacements that each match exactly once, and write nothing if any
  doesn't. Start a round only after the revision is on disk: `studio review` refuses a round unless
  SCRIPT.md's status line names it (two rounds once started on half-applied revisions).
- Run all three reviewers after every revision: fixes introduce errors (one round's revision
  introduced two blocking errors that only the next round caught).
- **The gate:** expert PASS, editor PASS, and the student's retelling answers the opening question
  and covers every objective.
- **Stopping:** once a round passes, apply its SHOULD FIX items once and run one final round; lock
  if it passes too. Don't polish NITs after a passing final round.
- **Caps:** rounds stop at video.json's `max_rounds` (6; 2 in economy mode); at the cap, lock with
  every open finding logged. **If two reviewers give opposite verdicts on the same sentence twice,
  stop and ask the user** instead of revising again (the expert and the editor once alternated on
  one sentence for five rounds).
- If `studio review` fails because a reviewer can't run in isolation, don't fall back to
  subagents that can read the project; if you must continue, tell the subagent to read only the
  files it is given, and log "reviewers not isolated from round N".
- Check for these before the first round; each reached a reviewer once: a ratio in the opening
  that doesn't match the count derived from it; mixed units; an off-by-one in a capacity claim; a
  simulation's number stated as a general fact; "same big-O, so same speed"; a tool's behavior
  described slightly wrong; a claim about a naive approach worded as a claim about a language; one
  word at two scales; a real default that contradicts the rule just taught; two examples called
  by the same words.

## Stage 6: Narration

`studio narrate VIDEO` reads the locked Script section (the single source of truth, so the audio
can't drift from the reviewed text), synthesises each paragraph in one call, and writes the audio
and the timeline: every sentence's id (s2_13), spoken and caption text, start and end, and its
words. Settings live in `narration.json`:

- Kokoro `af_heart` in paragraph mode is the default: local, free, deterministic, and its chunks
  are cached, so re-narrating after an edit re-synthesises only the changed paragraphs. Develop
  with it; `studio narrate --estimate` gives timings with no audio at all, so scenes can start
  before the voice exists.
- ElevenLabs (`"engine": "elevenlabs"`) is the hosted voice; switch at the end, once the script and
  scenes are right. A faster voice can shorten a sentence below the animation written for it, so
  re-check the stills after switching. `studio narrate --plan` shows what it would cost.
- Holds give the picture time after a reveal. Spoken respellings keep captions correct while the
  voice says "B M twenty-five"; they match whole words only.
- **Pronunciation.** `studio narrate` (and `--estimate`) first runs the pronunciation lint and
  writes `audio/pronunciation.txt`: every lone capital letter the voice won't say as its name,
  every acronym with the reading it will get, lowercase abbreviations the lexicon knows as words
  ("id" is said like the Freudian id), and words the lexicon lacks. Resolve each one before the
  first animated cut. A letter that names something ("A reads one": Kokoro says the article "uh")
  gets a per-sentence phoneme, `"phonemes_by_id": {"s6_17": {"A": "ˈA"}}`; a word gets `"phonemes"`
  or a `spoken` respelling. Respelled text can backfire ("Ay" is read "eye"), so prefer phonemes
  with Kokoro, and re-run the lint to see what each fix will sound like. Write abbreviations in
  capitals in the script (ID, not id). Accepting a finding as it is is fine; ignoring it isn't.

Then `studio voice-check VIDEO`: read what was heard for every sentence under 0.8. It transcribes
only sentences whose audio changed (the rest come from `audio/voice_check_cache.json`); run it with
`--all` once before the first publish. A mispronounced
term gets a `spoken` respelling or a phoneme; a clipped sentence means a timing bug. The voice check
can't hear a letter read as the article, or an acronym said as a word, since the recogniser writes
both the same way: that is the lint's job.

## Stage 7: The look (a gate)

Before animating, agree on the look from real frames. Write the main picture and one close-up as
scenes (static is fine), and make a stills-only cut (`studio cut VIDEO --stills-only`): two or three
directions if the style is open, one if the user already set it. Serve it and get the user's pick.
Two static rounds like this each saved a full build in earlier work. The approved scenes are also
the start of the build: they are the real components.

## Stage 8: Scenes and cuts

Write one scene per chapter (`scenes/sN.tsx`, registered in `scenes/index.ts`), following
`style.md`. What the Remotion engine expects:

- **Every frame is a pure function of time.** Everything derives from `useClip().t`: no timers, no
  state carried between frames, no `Math.random` (seed any noise). `studio determinism` checks it.
- **Time comes from the narration.** `at('03')` is when sentence 3 of this chapter starts,
  `end('03', 0.5)` half a second after it ends, `word('03', 4)` its fifth word. A picture that a
  sentence describes appears as it is said, and each animation finishes by its key word. `Beats`
  sequences animations like play() calls; `ramp`, `pulse` and `spring` (closed-form) ease.
  Stage camera moves and content changes; don't run them at once.
- **Stage units:** origin at the stage centre, y up, 8 units tall, above the caption band. Nothing
  enters the band; it belongs to the captions track. `Txt` sizes are Manim-style points.
- **Name what matters** (`name=` on Txt and Rect) so `studio boxes` reports it.
- Keep anything two chapters use in a shared file; `Chapter` fades a scene out over its last half
  second so consecutive chapters cut on the background.
- Data comes from `data/` (import the JSON), never from literals typed into the scene.

Then iterate: `studio still` to check a frame (about 1.6 s after an edit), and `studio cut VIDEO`
for a draft cut (only changed chapters re-render; it prints each chapter as rendered or cached, and
how many stills it reused). Keep edits local so the loop stays fast: a change to a shared scene file
re-renders every chapter, a change to one chapter's file re-renders that chapter, and a narration
edit re-renders only the chapter it is in. Before showing a cut to the user, run
`studio check VIDEO` (length, determinism, bounds, the caption band, contrast, legibility, and
provenance when assets are used; fix every failure) and `studio sheets VIDEO out/sheets` (chapter
sheets, a phone-width sheet, and full-resolution crops of small labels), then the craft critique on
the changed chapters:

- look at the cut's stills, and a phone-width look (the stills at 480 px wide are close to it);
- score each chapter 1–10 on phone-width readability, motion, composition, clarity of the beat,
  sound sync and polish; fix the three worst problems; repeat until every score is 8 or more, at
  most three rounds (one in economy mode);
- hunt for the banned defaults in `style.md`, text off centre in its box, sibling boxes of
  different sizes, connectors that miss their targets, and anything in the caption band.

The critique judges craft only. Content is judged by the reviewers and the frame review, in fresh
contexts.

## Stage 9: The frame review (a gate before publishing)

A fresh context (`prompts/frame_review.md`) gets the cut's stills, the script, the evidence table
and the data, and returns MUST / SHOULD / NIT findings. Give it the crops and their measured sizes from
`studio sheets` (`crops/index.json`): four builds of frame reviewers reported "labels are 15–18
px" from downscaled sheets when they measured 26 px. Before acting on a finding, check it against
the full-resolution frame. In earlier builds this review caught, after many passing script rounds:
a code card that did not compile, a narration line that was wrong, an axis labelled "time" on two
panels each scaled to its own run, a gauge forced to the cap, and one example's count shown under
the other example's file. Log each finding with what was done, fix, and re-cut.

Check in every frame: nothing overlaps, runs off the stage or enters the band; every label is
legible; every number matches the evidence and the narration; the thing to watch is visible; each
animation finishes before the line that follows; every chapter's length matches its narration.

## Stage 10: Hand over

Publish (`publishing.md`). Add the video's row to the learner model (length, and where reviewers
predicted the viewer would be lost), and finish with the page link, the length, the review rounds,
the frame review's findings and what was done, the voice check's result, and anything you could
not verify.
