# The build: from an approved narrative to a published lesson

This is the procedure the build agent follows. It records what earlier builds got wrong, so keep the reasons when you change a step. The narrative is already approved (see narrative.md) before this starts, and the learner's decisions from that stage are binding.

The script is the product and everything else renders it, so do no visual work until the script is locked. No human reviews the script: you lock it when independent reviewers pass it, so hold it to their standard. Commit after every stage (research, evidence, each review round, narration, scenes, render, page), so a build that is interrupted (a spend limit, a lost container) resumes from the last stage instead of starting over.

## Stage 1: Canonical research in fresh contexts

The narrative stage already ran two research passes and saved them in research/. Read them; run a further pass only for a question they leave open. The rules below still apply to every later fact.

Whatever sits in your context (your own draft, an earlier framing, this prompt's wording) anchors your judgment. The lesson must teach established knowledge the way the standard sources teach it.

- Run two independent research passes in fresh contexts: a subagent with web access, and a headless `claude -p "..." < /dev/null` call. Give both the same neutral prompt, containing the lesson, the audience and the questions below. Never include your ideas, a draft or candidate answers. Start each `claude -p` in an empty temporary folder, so it cannot read the lesson's other files.
- The questions: the canonical worked example and why it is the standard one (and the main competitor); the standard progression, including which simpler version is shown first; the standard model, notation and what exactly is measured, with notation clashes between fields; the key results with exact formulas and their assumptions; the standard numeric examples from textbooks; the misconceptions students bring and how the canonical treatment corrects them; what is essential, a common extra, or out of scope for a short lesson; real systems canonically cited, with the mechanism each uses; claims that are commonly overstated or subtly wrong; which parts are best learned by watching a narrated animation, which by doing (an interactive simulation, running code, an exercise), and which by reading. Ask for citations (book, chapter or section, paper, year) and for uncertain items to be marked.
- Save both reports in research/. Where they agree, treat it as canonical. Where they disagree or flag uncertainty, check a primary source.
- Later, whenever you are about to rely on a fact you have not verified in this session (a tool's default, the exact wording a tool prints, a formula's exact form), check it in a fresh context or against a primary source. Reading local documentation counts: `zcat /usr/share/info/coreutils.info.gz` settled what GNU sort's merge width is for.

## Stage 2: The argument

Write SCRIPT.md, starting with the argument, before any narration:

- **Question.** The specific question the opening raises. The strongest openings show a real, runnable demonstration with a surprising outcome (the same memory, one program crashes, another finishes and leaves twelve temporary files behind).
- **Answer.** How the ending answers that question, using the opening's own evidence.
- **Takeaway.** The rule the viewer should leave with, in one or two sentences.
- **Wrong model.** The intuition the audience brings that the lesson must dislodge. Take it from the canonical misconceptions.
- **Objectives.** Three or four things the viewer can do afterwards.
- **The chain.** One sentence per segment, each joined to the next by "but" or "therefore". Follow the canonical progression, and write down any deviation and the reason for it.
- **Ledgers.** Setups and where each pays off. Vocabulary: every term, where it is first used, its definition, and no synonyms afterwards; use the canonical names. Numbers the viewer should remember: two or three.

Then decide the format of each chapter, and record it in SCRIPT.md as a table: chapter, format, why. Not every idea is best learned from a video. Timing, motion, and things that build up are good in narrated animation; a skill is learned by doing; reference detail is read. When a chapter would be better as a sandbox or an exercise, say so, and offer it separately instead of adding it to the video's page.

## Stage 3: Evidence

- Every number spoken or shown comes from a run in this environment, a simulation written for this video, or a cited source. Typical published values are labelled as typical.
- Measure what the script compares. If the script says two algorithms differ in one quantity and not another, measure both quantities.
- A number that depends on the setup is spoken as the setup's number ("in our simulation, about three I/Os per item"), never as a general law.
- Choose the demonstration's parameters so the arithmetic the narration states is exact, and fix the evidence rather than explaining a mismatch in a footnote. In one build, GNU sort with 100-byte records spent half its buffer on per-line bookkeeping, so a file six buffers long made twelve runs. With 10,000-byte records and a buffer given in bytes, the file was 11.6 buffers long and made twelve runs, and the script no longer needed the aside.
- Use one unit system everywhere. Decimal megabytes and gigabytes are the default; a buffer written as `88M` is 88 MiB, and mixing that with a decimal file size produced an error an expert caught.
- If the script says a real system behaves a certain way, capture the real output and replay it: terminal sessions, query plans, file listings. Scale runs down when needed and say so on screen.
- Step-by-step animations of an algorithm replay an event log from a small instrumented implementation.
- Keep an evidence table in SCRIPT.md: claim, how it was checked, value.

## Stage 4: The script

Narration is written for the ear: short clauses, parameter names spoken as words, formulas described in words rather than read out, and no more than one new number per sentence. When a number has a reason, say the reason ("eighteen doublings take you from one item to a quarter of a million"). Next to every narration line, write what is on screen at that moment; those notes become the scene specifications.

Hold the script to these principles, each of which has a test:

1. **One question, answered with its own evidence.** The last minute refers back to the first, and every part of the opening question is answered.
2. **"But" and "therefore", never "and then".** Join the segment sentences. Any "and then" marks a list or a tangent.
3. **Derive, don't reveal.** Before each new idea there is a visible problem that it fixes, so the viewer could almost have invented it.
4. **Setups pay off, and payoffs are set up.** Check the ledger in both directions.
5. **One vocabulary.** Every term is defined where it is first used, and no concept has two names.
6. **A budget of numbers.** The viewer should retain two or three. The others support those and can live on screen.
7. **Concrete before abstract.** A formula summarizes something the viewer already watched, and a general rule follows a concrete case.
8. **Show the wrong model failing.** Show a result the wrong model cannot explain; it is not enough to argue against it.
9. **Depth over breadth.** One application understood beats five that are only named. Generalizations get one sentence, or their own lesson.
10. **Words and pictures split the work.** The narration explains, the picture shows, and on-screen text only labels. Text on screen that repeats the narration word for word is wasted.
11. **The deletion test.** Delete each line in turn. If nothing later breaks and the takeaway doesn't weaken, the line goes.

There is no length target and no limit. The script is as long as the argument needs after the deletion test. Estimate duration at about 150 words per minute of finished video. Engagement data on lecture videos (Guo, Kim and Rubin, 2014) found that watch time levels off around six minutes, so if the argument answers two separate questions, consider two videos, split where one question ends.

## Stage 5: Review until the script passes

Three reviewers, each a fresh context, run by `kit/review.py LESSON ROUND` (each is a `claude -p` started in an empty folder, so it cannot read earlier rounds), each given only what it needs:

- **Expert:** the script with screen notes, plus the evidence table.
- **Student:** the learner model (background and standing instructions only, not the history of earlier notes) and the script with screen notes. The student plays that learner; with no learner model, it plays the AUDIENCE line.
- **Editor:** the argument (question, answer, takeaway, wrong model, objectives) and the script with screen notes, but not your ledgers, so that it builds its own.

The prompts are in kit/reviewers/ (expert.md, student.md, editor.md); the student prompt takes the learner model's Background and standing instructions.

Rules for the loop:

- After each round, revise and log every finding in SCRIPT.md: what changed, or why it was declined. Decline a finding only for a reason a domain expert would accept, and say what that reason is.
- Apply every revision with a script that checks each replacement matched exactly once, and write nothing if any didn't. Start a round only after the revision is confirmed on disk; review.py refuses a round unless the script's status line names it (two rounds once started on half-applied revisions and had to be killed).
- Run all three reviewers again after every revision. Fixes introduce new errors: in the build this template comes from, one round's revision introduced two blocking errors, and only the next round caught them.
- The gate: the expert and the editor both return PASS, and the student's retelling answers the opening question and covers every objective. The student may still lose some spoken arithmetic, but only where the screen notes show that arithmetic as it is said.
- Stopping rule: once a round passes the gate, apply that round's SHOULD FIX items once and run one final round. Lock the script if the final round also passes the gate. If it does not, fix the blocking items and run another round. Do not keep polishing NITs after a passing final round.
- Build each reviewer's input by cutting named sections out of SCRIPT.md, then check it before every round: the expert's input contains the evidence table, and no input contains the review log, the ledgers or earlier reviews. In the build this template comes from, a section reorder silently dropped the evidence table from the expert's input for nine rounds and showed all three reviewers part of the review log, and those rounds had to be rerun.
- Check for these before the first round. Each one reached a reviewer in an earlier build:
  - a ratio shown in the opening that doesn't match the count the script derives from it;
  - decimal and binary units mixed in one video;
  - an off-by-one in a capacity claim (a k-way merge needs k input blocks plus one for output), repeated in the recap;
  - a simulation-specific number stated as a general fact;
  - "same big-O, so same speed";
  - a tool's behavior described slightly wrong (the Sort Method line appears in EXPLAIN ANALYZE, not EXPLAIN);
  - a claim about the naive approach worded as a claim about a language;
  - one word used at two scales (a "block" of kilobytes in one scene and a megabyte in another);
  - a real tool's default that contradicts the rule just taught, left unexplained;
  - two different examples called by the same words ("our file" for both the real file and the simulated one).

## Stage 6: Production

Only now plan the visuals, from the screen notes, one segment at a time. Every visual serves the beat its line belongs to.

VISUAL LANGUAGE:
- Dark background, IBM Plex Sans and IBM Plex Mono, 1920×1080 at 30 fps.
- One fixed picture of the lesson's main structure (for external sorting, memory on top and disk below) reused in every scene where it applies, with its geography unchanged.
- Colour roles: one accent reserved for cost (amber), one for the current selection (ice blue), grey for idle. Values use a perceptually uniform colormap (seaborn "mako") and are also printed as numbers in close-up scenes, so colour is never the only cue.
- A persistent counter for whatever the lesson counts, ticking only when that thing happens.
- A formula appears only as a label for something already shown, or on the end card for reference.

PIPELINE:
1. narration.py reads the narration straight from the locked SCRIPT.md (the single source of truth, so the audio can never drift from the reviewed text), splits it into sentences with ids like s2_13, renders it with Kokoro (voice af_heart), and writes narration.wav, narration.mp3 and timings.json with each sentence's id, spoken text, caption text, start and end. New lessons set `"kokoro": {"voice": "af_heart", "speed": 1.0, "paragraph": true}` in narration.json: each paragraph is one Kokoro call, so intonation carries across sentences and pauses follow the punctuation, and each sentence's edges come from Kokoro's word timings snapped to silence. (Rendering each sentence separately, the older default at speed 0.92, makes every sentence start at the same pitch after the same gap, which sounds robotic.) Silence: 0.8 s lead-in, the voice's own pauses between sentences of a paragraph, 0.5 s between paragraphs, 1.2 s between segments, holds after sentences whose visuals need time, and a tail long enough to read the end card. A segment's video runs from its first line to the next segment's first line. Keep spoken spellings ("Postgress", years in words) separate from caption spellings. You cannot listen, so `kit/voice_check.py` is the audio review: it transcribes every sentence's clip with a speech recogniser and scores it against the text. Read what was heard for every low score; a mispronounced term gets a `spoken` respelling (acronyms especially: "BM25" as "B M twenty-five"), and a clipped sentence means a timing bug.
2. make_data.py writes every dataset the visuals use (simulation traces, event logs, images) to data/.
3. One Manim Community scene per segment. A shared module holds the palette, fonts, the fixed picture, the counter and a cue helper: each scene loads its segment from timings.json, waits for a line with at(line_id, offset), and ends with finish(), which waits until the segment's exact length. Consecutive scenes either end and start on the same frame or fade through the background colour.
4. Render every scene at 480p15 (`build.py --preview`), cut contact sheets (`kit/sheets.py`), and check them (see VERIFICATION). Re-render only the scenes that changed.
5. build.py renders all scenes at 1920×1080 30 fps in parallel, checks each scene's length against its segment, concatenates them with ffmpeg, muxes the narration as AAC, writes WebVTT captions from timings.json, and encodes a web copy under 15 MB (libx264, CRF about 27, -tune animation).

ENVIRONMENT:
- System packages: ffmpeg, espeak-ng, libcairo2-dev, libpango1.0-dev, pkg-config, fonts-ibm-plex. Python venv: manim, kokoro, torch, numpy, scipy, matplotlib, seaborn, soundfile.
- Kokoro downloads its weights from huggingface.co, and the CPU build of torch comes from download.pytorch.org. If the network policy blocks a host, report the host and keep working on everything that does not need it. Do not work around a policy block.
- There is no LaTeX. Use Text and MarkupText; Pango markup handles subscripts.

MANIM PITFALLS:
- Pango lays out small text with broken kerning (letters spread apart, spaces lost between words). Render every text at 4× its font size and scale it by 1/4.
- Manim renders Text into a canvas as wide as the video and MarkupText into a 600 px canvas with wrapping, so 4× text wraps mid-line. Patch manimpango.text2svg and MarkupUtils.text2svg to use a wide canvas with no wrap width, and clear Manim's text cache after changing either.
- Every animation lasts a whole number of frames. When many short events run back to back, compute each duration from the time left before the next cue instead of using a fixed value, or the sequence overruns the narration.
- Text drops leading spaces. Indent code and terminal lines by measured character width.
- For counters and other text that changes every frame, cache one Text object per value.
- Scene.play takes animations, not mobjects: wrap a new arrow in Create or GrowArrow.
- Animating set_opacity on a Group does not dim the ImageMobjects in it. Fade images out, or cover them with a rectangle in the background colour.
- A counter whose digits are redrawn by an updater cannot be Indicated, because the updater overwrites the effect every frame. Circumscribe it instead.
- A mobject that is reachable only through a group that was removed stops rendering. When items move between containers, remove and add the groups explicitly, and rebuild a scene's end state from scratch instead of fading back in something that was faded out.

VERIFICATION:
- For every segment, cut a contact sheet of frames at its cue times, first from the 480p15 preview and again from the final render.
- Screen text says what the locked narration says, never a stronger version of it (in an earlier build a caption read "the count of I/Os is the cost" where the script said the I/Os "typically dominate"), and it adds no claim the evidence table does not cover. Check every on-screen sentence against the script and the evidence table.
- Show a measurement while the narration sets it up, so the numbers are on screen when they are spoken rather than appearing as the line ends.
- After the first full render, run the frame review (prompts/frame_review.md): a fresh-context reviewer gets the contact sheets, the script, the evidence table and the data, and returns MUST / SHOULD / NIT findings. Before acting on a finding, check it against the full 1080p frame: reviewers read downscaled sheets and have reported a panel missing that was there. In the build this template comes from, it caught these after the script had passed fifteen review rounds: an axis labelled "time" on two panels each scaled to its own run, so equal widths implied equal durations; a gauge forced to the cap when the measured peak was lower; two counters for different amounts of work shown side by side with nothing saying so; one example's pass count shown under the other example's file; and a formula's name reused for a tool's configured limit. Log each finding with what was done, fix, and re-render.
- In each frame, check that nothing overlaps or runs off the frame, every label is legible at 1080p, every number on screen matches the evidence table and the narration, the thing the viewer must watch is visible, and each animation finishes before the line that follows it.
- Every scene's length matches its segment within 0.1 s, and the video's length matches the narration's.

## Stage 7: Delivery

Build the page with `kit/make_page.py`, then publish it (see publishing.md): with the Artifact tool when it is available, otherwise as a local page the learner opens in a browser.

- A minimal page: the video, a chapter strip, a captions toggle, and a "Lost me here" button. Nothing else: the script, sources and review log live in the repository, not on the page (a learner found a page with them "too busy"). Claude artifacts do not serve .vtt files, so embed the caption cues in the page and attach them with video.addTextTrack.
- "Lost me here" pauses the video and shows the sentence on screen and the one before it, with an optional note. Saving writes a document to the artifact's database (declare the db capability; collection "feedback") with the time, chapter, both sentence ids and texts, the note, the lesson version and a timestamp. Show the learner their saved notes under a collapsed "N notes saved", with jump-to and delete. Hide the button when the database isn't available in that view.
- Commit the research reports, the locked script with its review log, the reviews, sources, data, captures, the narration mp3, the web video and captions. Keep the wav, the 1080p master and Manim's media folder out of git.
- Add the lesson's row to learner.md (length, and the places reviewers predicted the learner would be lost), and update its "Last updated" line.
- Finish with the page link, the video length, the number of review rounds, the frame review's findings and what was done, the voice check's result, and anything you could not verify.

## Stage 8: Revise from the learner's notes

When the learner has watched and left notes:
1. Read the notes (ArtifactData, collection "feedback"). Each names a time, a chapter and the sentence on screen; the note may be empty, which still says "here".
2. Update the learner model's evidence table with what each note shows (a skipped step, a term used before it was defined, two new ideas in one sentence, an example that didn't land, a pace problem), and adjust the standing instructions if a pattern appears.
3. Revise only the chapters the notes point at: add the missing step, define the term, split the sentence, swap the example. Keep sentence ids stable where the text doesn't change.
4. Run the three reviewers on the revised script, with the student playing the updated learner, until the lock criteria hold again.
5. Re-narrate, re-render only the changed chapters, rebuild, and republish to the same page with a new version number. Mark each note as addressed (add the version that addressed it) instead of deleting it.
6. Tell the learner what changed, chapter by chapter, and which notes each change answers.

---
