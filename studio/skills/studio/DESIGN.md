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
so their notes are the review and reviewer rounds are optional. When they don't (learner drive),
correctness has to be established by fresh-context reviewers before they see it, and they get risk
flags rather than a false sense of a finished product. In the work projects, the user was the
expert and the reviewer machinery was friction: one lock took 18 rounds, and reviewers asking for
more explanation doubled a six-minute plan. Hence the charter, the caps and the oscillation stop.

## Fresh contexts where content is judged

A context that holds a draft anchors every later judgment to it. Research, competing narratives,
script reviews and the frame review run in fresh contexts, each seeing only what it needs; reviewers
run in empty folders because, in one build, reviewers with file access read earlier reviews and
repeated them. When isolation failed once, the fallback subagents loaded the project's context and
the "newcomer" knew far too much, so a failed reviewer now stops the round loudly. The in-agent
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
variation at no cost. ElevenLabs is the hosted option, its responses cached and committed so a
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
kit is smaller than Remotion's; `references/engines.md` says what is missing.

## Evals

`evals/` holds eight cases in the plugin eval format (routing for each genre and drive, a negative
case, revising from notes). The first run cost $4.25 and scored 0.91 overall; the two low runs were
the sandbox (the agent led with having no shell, and the judge found no plan), which the prompt now
addresses.

## Still open

| What | Done when |
|---|---|
| **Motion Canvas kit parity**: the map and close-up components, `PixelCanvas`, `Shot` and `Footage` for Motion Canvas | a pixel, launch or footage video renders on Motion Canvas and passes its checks |
| **Notes from real use**: the loop is proven with scripted notes and by the user's use of the review page | a video goes through several rounds of the user's own notes |
| **Migrating a pinned video**: `studio init --update` replaces a video's kit copy | a real video's stills compared before and after an update |
