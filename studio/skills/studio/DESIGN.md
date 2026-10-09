# Why the studio is shaped this way

The studio replaces the tutor plugin, which built fourteen narrated lessons with one learner and
two work projects (an engineer explainer and a stakeholder cut of it). Every rule here traces to
something that went wrong or to a choice a user made. This file records them, so a future change
knows what it is trading away.

## The narrative is settled first

Across the tutor's lessons, the learner's reactions were almost entirely about the argument: the
wrong story, too much history, a chapter that did not earn its place. Iterating a narrative costs
minutes; iterating a finished video costs hours. So the narrative is settled with the user before
any script exists.

## Two drives, because expertise changes who can judge

When the user knows the subject (author drive), they are the best reviewer and iteration is cheap,
so their notes guide revisions. A student pass still checks whether the intended audience can follow;
subject-review rounds remain optional when the author can judge correctness. When they don't (learner drive),
correctness has to be established by fresh-context reviewers before they see it, and they get risk
flags rather than a false sense of a finished product. In the work projects, the user was the
expert and repeated three-role reviewer rounds were friction: one lock took 18 rounds, and reviewers asking for
more explanation doubled a six-minute plan. Hence the charter, the caps and the oscillation stop.

## Fresh contexts where content is judged

A context that holds a draft anchors every later judgment to it. Research, competing narratives,
script reviews and the frame review run in fresh contexts, each seeing only what it needs; reviewers
run with selected inputs in empty folders because, in one build, reviewers with file access read earlier reviews and
repeated them. When isolation failed once, the fallback subagents loaded the project's context and
the "newcomer" knew far too much, so a failed reviewer stops the round loudly. An empty folder reduces context leakage, but is not a
filesystem sandbox; the main session owns reviewer dispatch and records capability limits. The in-agent
craft critique is allowed because it judges legibility and motion, not content.

## One timeline, frames as functions of time

Most of the work projects' improvised scripts (captions, a band check, word timings, contact sheets)
existed because nothing owned the frame's layout or the time grid. The timeline is that owner:
narration, words, captions and scene clips, derived from the script. Engines render clips from it,
and every frame is a pure function of time, so any frame renders alone. That is what makes a still
after an edit take about 1.6 s, a changed chapter re-render alone, and checks seek exactly the
frames they need (a Motion Canvas port measured 4× faster iteration than Manim for this reason).
Remotion is the default engine: its frames are already functions of the current frame, its CLI and
renderer give stills and renders directly, and its components double as the look-gate mockups.

## The loop is the product

The user never operates the tools. They see a cut, leave notes against the exact sentence on
screen, and see the next cut. So cuts render stills first, re-render only changed clips (keys hash
what each clip's frames depend on, with relative paths so a moved video keeps its cache), show
before/after stills, and keep final quality for publishing. The review page puts its controls below
the video because an overlay hid the burned-in captions exactly when the video was paused for a note.

## Captions are a layout primitive

The learner asked for burned-in captions that never cover anything. They live in a reserved band
the scenes can't enter, chunked from word timings (two lines of about 42 characters, phrase
boundaries, at least 1.2 s). The page drops its captions toggle so they don't show twice.

## Voice

Kokoro `af_heart` sounded robotic synthesised sentence by sentence: every sentence started at the
same pitch after the same gap. One call per paragraph doubled the sentence-to-sentence pitch
variation at no cost. Kokoro stays the voice through to publishing: a late switch re-times every
word, which changes every chapter's render key and reopens every sync decision. ElevenLabs is the
hosted option when a user asks for it, its responses cached and committed so a
rebuild never pays twice (the port reproduces the tutor kit's ElevenLabs timings exactly). Nobody
can listen, so the voice check transcribes every sentence; it caught a synthesis that silently
dropped two sentences. A one-pass loudness "finish" once raised the room tone in every pause, so the
narration is muxed as rendered.

## Visual style

"The macro view needs to be super clean": a single diagram that accumulated every chapter's detail
became unreadable, so the default is a clean map plus full-screen close-ups. A visual protagonist
and real imagery were the biggest single improvement. The banned-defaults list comes from studying
why "one prompt" motion design looks alike. Two rounds of static mockups each saved a full build,
hence the look gate.

## The environment

`bin/studio` enters the plugin's own flake (Python, uv, Node 22, ffmpeg, sox), caching the
environment per lock file, because entering a Nix shell on every call would add seconds to every
still. Python packages are pinned by `uv.lock`, the engine's by `package-lock.json`, and the heavy
parts (Kokoro and torch, faster-whisper) are optional extras. The browser is the engine's headless
shell: a full Chrome in headless mode rendered at about 18 frames a second, the shell at about 73.
An installed Chrome is the fallback behind a proxy that blocks the download. `studio doctor` checks
every layer and prints the fix.

## Measured

On an 8-core Apple silicon machine, with "Charged Twice" (4:35, seven chapters) rebuilt in Remotion:
a frame after editing a scene, including the rebundle, 1.6 s; one chapter at draft quality after an
edit, 13.5 s; the next cut after editing one chapter, 24.8 s; a full draft cut from nothing, 2:05;
21 of 21 sampled frames identical across two renders. The narration port reproduced the tutor's
ElevenLabs build of "From LLM to Agent" to the millisecond (125 sentences), and its voice check gave
the same result.

## Checks, and what each one caught

`studio check` runs through the engine interface, and each check earned its place on something real:
- **length** found Python's `round()` and the engine's `Math.round` disagreeing on half frames
  (436.5 → 436 against 437), which put a chapter boundary a frame off between kit and engine.
- **band** (named boxes against the band, and the scene alone against the bare background over the
  band's pixels) and **bounds** catch an element entering the caption band or leaving the frame;
  proven by putting one in each on a scratch scene.
- **contrast** reads the brightest pixel under the band against the caption colour (16:1 on the
  opaque band).
- **legible** fails text under 18 px tall; **provenance** fails a scene that uses an asset with no
  source row; **dead** fails a run of identical frames over four seconds; **loop** compares the last
  frame with the first (a template whose return began at the loop point failed it).
- **grid** and **palette** (pixel art), and **filler, cuts, levels, sync, segments** (footage).
- A check that samples sentence times checked nothing for a video with no narration, so clips
  without narration are sampled evenly.

## Genres

One engine and one timeline serve five genres; each genre file (`references/genres/`) holds the
procedure and the checks that fit it. Motion is reference-driven, with a state list and a loop that
must settle before its seam; launch films use captured screens and record where every asset came
from; pixel art is a fixed grid, a palette and whole-number scaling; footage is edited by its words,
with captions from the footage's own transcript. Formats (16:9, 9:16, 1:1) each have their own stage
and caption band, bundle cache and clip keys, so one timeline exports all of them.

## Engines

Remotion is the default; Motion Canvas is the second, for work (Remotion's licence) and for scenes
that are naturally tweens. It was written from the packages against the same four operations: a
Vite dev server serves the video's scenes, a headless browser loads a page that runs Motion Canvas's
own Player and Stage, and the driver seeks to exactly the frames it needs. The kit's checks pass
unchanged on a Motion Canvas video (length, determinism, bounds, band through the `layers` project
variable, contrast, legibility, dead beats and the loop seam), and it exports every format. Its scene
kit has the same components as Remotion's (map and close-up, pixel art, captured assets, footage
edits), driven from a per-frame `c.every`; pixel, launch, footage and motion videos pass their genre
checks on it.

## Evals

`evals/` covers genre/drive routing, a negative case, exhaustive code coverage, and revisions
including mid-flight requests. Run with `claude plugin eval` against a clean checkout (the installed
`node_modules` push a plugin folder past the tool's 20,000-entry limit). The first run cost $4.25
and scored 0.91: the two low runs were the sandbox (with only read tools the agent led with having
no shell, and the judge found no plan), so the prompts now say so up front. The routing cases then
scored 1.0 on all 18 runs ($3.37), and the negative case (a chat question must not start a video)
passed.

## Still open

| What | Done when |
|---|---|
| **Migrating a pinned video**: `studio init --update` replaces a video's kit copy | a real video's stills compared before and after an update |
| **Boards in Motion Canvas**: a Remotion chapter without a scene renders its board; Motion Canvas still requires every scene | the Motion Canvas project falls back to a board scene |


## What the next three productions changed (0.6.0)

A 26-minute line-by-line Rust tour failed even though its facts were correct. A construction story
with four marked ideas, real intermediate runs and optional language sidebars worked. The method
now lives in one pedagogy reference: model delta and transfer questions precede the outline,
abstractions earn their place, and prediction beats leave actual silence. Intro describes
scaffolding rather than an exemption from evidence/review. Runtime follows the cognitive arc;
engagement measurements do not establish a universal learning duration.

An expert author is not a substitute for a beginner's perspective. One student pass applies to
teaching explainers in either drive, with receipts tied to the current script. Builders hand
frame bundles back to the main session so independent review does not require nested delegation.
A review that could not run is unavailable, never an implicit pass. Reaching a cap leaves findings
open rather than certifying correctness. Simulated students remain diagnostics, not learning data.

Cut pruning deleted a video the user had just watched. Cut records and MP4s are now retained by
default; explicit media cleanup excludes watched/final/noted cuts. The local player and page share
the same protection. Git checkpoints track source and evidence rather than rotating binary
renders into history. These are separate forms of preservation. Older pinned kits must be updated
explicitly before their old pruning code is used again.

Inline pauses belong to source sentences, not a hand-maintained map of positional IDs. The parser
serves narration and pre-render diagnostics. Old narration settings keep their old timing; new
intro defaults add breathing room. Prediction reveal cues, like other timeline cues, must remain
relative to a shifted chapter for incremental rendering to remain valid.

Revisions now begin with a merge/trim analysis. Only changed dependencies render, but the editorial
change covers the smallest coherent argument, not necessarily only the annotated sentence. One
folder has one writer, late requests are queued, and structural revisions get different forecasts.
Personal style/lexicon and series evidence are snapshotted so global edits cannot change old cuts.


## Boards, the animatic and checkpoints (0.7.0)

Two explainers made after 0.6.0 found their worst problems only after scenes were built: a
chapter that opened on an empty stage, a close-up that sat empty for two sentences, a runtime
8:42 against a 7:00 target, and a note ("show concretely what a script or a storyboard is") that
was about what the picture shows, not how it moves, yet cost a scene rewrite. Animation studios
settle those questions with storyboards and an animatic before animating, because each stage is
cheaper to change than the next. The studio borrows the two that make videos better.

Boards are layout decisions in data (boards/boards.json: boxes, text, arrows per beat), drawn
rough on purpose; screen notes fill the gaps, so a chapter has a picture from the moment its script
exists. They live outside scenes/ because a change to a shared scene file changes every chapter's
render key; a chapter's key includes the boards only when it renders them. A chapter without a
scene renders its board in every cut, which is what makes progressive cuts possible: finished
chapters animated, the rest as boards.

The animatic holds each sentence's picture to the real narration. It renders its own stills at
half resolution (upscaled page thumbnails made board text unreadable) into its own cache, since a
still cache removes the stills a call no longer wants. It refuses an estimated timeline: a
timeline written by `narrate --estimate` now says so, where before the animatic would have played
silence. Kokoro stays the voice from first narration to publishing, so the animatic's timing is the
final timing; the word-count estimate was recalibrated against two Kokoro narrations (3.55 words
per second at speed 1.0, sentence ends included, within 2% of both; the old 2.8 + 0.3 s overstated
one video by 27%).

`checkpoints: few | many` is how much the user follows along. The boards and animatic checks run
either way; `many` only adds the stops.

Considered and left out: a picture-lock state. In film it protects work that depends on frozen
timing (sound, colour, other people's schedules); here re-rendering after a late timing change
costs seconds, so a lock would only make late fixes harder. Cut records now carry a kind (stills,
boards, animatic, cut, final) so the new kinds never reach publish or frame review, and
`settings.py` lists every video.json key in one place.

## The desk, the live engine and two modes (0.8.0)

Evidence: one 11-minute explainer (TigerBeetle's seven stages of survivability) built in a single
session on a prototype desk, through 16 notes from the user. That closes the "notes from real use"
item: the loop is proven by the user's own notes.

- **What the user wanted was to be in the middle.** Before, a background builder worked for hours
  and the user saw the end; checkpoints asked process questions (review caps, waivers) on a page
  they didn't open. On the prototype, each note was answered in 5 to 15 minutes, in place, and the
  user stayed in the loop for the whole build. But the user also said plainly that sometimes they
  just want a video made without them. So there are two modes: `background` (the default; nothing
  waits on the user) and `interactive` (the desk, chapter by chapter, note by note). `checkpoints`
  is superseded; old videos with `many` load as interactive.
- **The desk replaces the review page, it doesn't add one.** Notes keep their log; they gain a
  status and a reply shown under the note on the cut that answers it; open notes carry to later
  cuts. `studio wait` is the mechanism that makes it interactive: a builder that runs it in the
  background is woken by each note. None of the desk's commands take the operation lock.
- **Most notes were about teaching, not motion.** About 12 of the 16: explain this better, the jump
  is too big, use canonical terms, what is a key, how runs relate to the log, which stages survive.
  The reviews that passed the script had missed most of them, so the student reviewer and the
  pedagogy self-check gained eight checks drawn from those notes.
- **The live engine exists for the loop.** A scene that is plain JS drawn from t needs no build:
  the desk draws the current scenes and redraws the moment a file changes, and the same code renders
  the cut (measured: a 27 s two-chapter draft cut in 28 s; the prototype's 11-minute 1080p video in
  under 6 minutes with six workers). It is the default for explainers; Remotion keeps the code
  components, so code explainers stay there.
- **Determinism is enforced, not hoped for.** The prototype carried a clock reading across frames;
  the engine now gives every node exactly this frame's attributes and stacking order, so a frame
  drawn after any other equals the frame drawn alone (tested, and `studio check` renders samples twice).
- **Cues on what the voice says.** Positional sentence cues broke whenever a note split a sentence
  (several did). `phrase(id, text)` cues the spoken words (word timings, or the caption position where
  a spoken rule rewrote them), in all three engines.
- **One writer for the timeline.** Seven commands edited timeline.json in place, and a re-narration
  rebuilt it keeping only the hand cues, so it dropped the effects track, the beat grid and any music
  bed. Each command now owns one source file (narrate the timings, align the words, sfx its cues, the
  builder `cues.json` and `audio/tracks.json`) and `timeline.build` composes the file from them; words
  aligned against an earlier narration are ignored rather than misplaced.
- **Paragraph synthesis stays.** The prototype re-voiced sentence by sentence; studio keeps paragraph
  synthesis (sentence-by-sentence Kokoro sounded robotic, above). An edit re-voices its paragraph.
- **ElevenLabs refusals say why.** A per-key quota stopped the prototype's final render with a bare
  401. The balance is now checked before a run when the key may read it, and a refusal prints
  ElevenLabs' own reason and that the cache resumes.
- **Words for motion.** The motion glossary (20 terms, each one helper in the live kit, with the
  Remotion equivalent) grew from the user's own words ("blur them together"); a note that uses a
  term says so to the builder.
- **Checks after every change.** A text-on-text `overlap` check joins the incremental per-chapter
  set, and a live scene that throws fails with its clip, time and source line, so a collision or a
  crash is caught before the user sees it.

| Still open | Done when |
|---|---|
| **Live parity for code explainers**: CodePanel, Terminal and the other code components are Remotion-only | a code explainer is built on the live engine |
| **Desk on other machines**: the desk binds to 127.0.0.1 | a phone or second machine can follow a build safely |

