# Build an explainer

Start from the agreed `research/narrative.md`. Read `pedagogy.md`, `levels.md`, `gates.md`,
`ownership.md`, the taste files (`taste/look.md`, `taste/screen-text.md`, `taste/delight.md`,
`taste/narration.md`), the learner model and the video's snapshotted `research/house.md`. For code,
also read `code.md`; for sound, `audio.md`; for the reviews each stage waits on, `reviews.md`.
When video.json `tone` is `comic`, also read `taste/comic.md`, and apply it from the script on:
gags in the screen notes with their meaning, `[beat]` before each punch, comic sound on anchored
cues, and its questions in the motion review. A plain video never reads it.
The same stages apply at either level; depth and claim risk determine additional review effort.

## Stages at a glance

This table is the one list of the explainer's stages; SKILL.md and the build prompt point here.

| Stage | Produces | Before the next stage | Decided by |
|---|---|---|---|
| 1 Sources | research notes, source hashes | claims to verify are listed | builder |
| 2 Argument and chain | SCRIPT.md Argument and Chain | matches the approved narrative | user (at the narrative) |
| 3 Evidence | sims/, data/, Evidence rows | every asserted number has a row | builder |
| 4 Script | narration with screen notes | pedagogy self-check, `studio check --only script` | builder |
| 5 Script review | review receipts | current student pass (plus expert and editor for learner drive or deep-dive) | fresh reviewers; the main session dispatches |
| 6 Narration | audio, timeline with word times | voice-check scores under 0.8 inspected | builder |
| 7 Boards | boards/boards.json, a boards cut on the desk, the hero moments named | every sentence has a board or a screen note on screen | builder; the user sees it on the desk |
| 8 Animatic | an animatic cut on the desk and its pacing report | runtime, unchanged stretches and empty sentences read and addressed | builder; the user sees it on the desk |
| 9 The look | the look sheet (`studio look-sheet`) and a stills-only cut | the user's pick, unless a house style already settles it | user |
| 10 Scenes and cuts | cuts, chapter by chapter: the blocking (layout, moves timed on events) | `studio check` passes, pacing included; craft pass on changed chapters | builder; the user reviews cuts |
| 11 Polish | secondary motion, anticipation, effects on events; a motion review receipt | the motion review stops by its rule: a round with no must-fix findings, or `motion_rounds` rounds (2) | fresh reviewer, the main session dispatching; in interactive mode the user's desk notes instead, if the user prefers |
| 12 Frame review | frame review receipt | required for deep-dive, shared or `frame_review` videos | fresh reviewer; the main session dispatches |
| 13 Finish | local master, page | the user's approval of a cut (`reviews.md`), then the `studio publish` gate | user |

`mode` in video.json sets how the user takes part. In `background` (the default) an agent builds
unattended: the user approves the narrative, picks the look and reviews cuts. Boards and the animatic
are the builder's checks, but they go on the desk as soon as they exist, with a link to the user, so
the user can watch the video take shape; nothing waits on them. In `interactive` the user follows on
the desk: the main session builds in the foreground, chapter by chapter, opens the desk before
stage 7, says when each chapter is ready there, and takes each note as it arrives (`desk.md`).
Older videos that say `checkpoints: many` load as interactive. Every user decision, and how to ask
for it, is in `gates.md`; ownership, budgets, handoffs, scratch and long passes in `ownership.md`.

## Stage 1: Sources

Use sources gathered during proposal. Research further only for unresolved claims. Read the code
behind repository claims; cite files, commit and any uncommitted content hashes. Verify exact
outputs, defaults and formulas against a primary source or a recorded run. Avoid claiming a
simulation proves behavior outside its assumptions.

## Stage 2: Argument and chain

Populate the template's Argument with the agreed learning brief and the Chain with chapter
questions, motivated ideas, predictions and closure. Apply `pedagogy.md`. Reference detail can
be a sidebar/document; it need not inflate the main story. Keep a vocabulary and number ledger.

## Stage 3: Evidence

Every asserted number or behavior has an Evidence row. Keep extraction/measurement scripts in
`sims/`, their outputs in `data/`, and import those outputs into scenes. Show the actual small
record and transformations for a data system; an explicitly synthetic worked example is allowed.
Measure both sides of comparisons, use consistent units, and state setup-dependent results as
such. Real terminal output, query plans and event logs beat an invented reconstruction. Choose
parameters that make a worked example's arithmetic match what is actually shown.

## Stage 4: Script

Write short spoken clauses with `*Screen:*` notes specifying the visual change and its sentence:
`*Screen:* s2_01: … s2_03–s2_05: …`; text without an id belongs to the paragraph above. Sentence ids
are positional, so `studio check --only script` reports notes that name a sentence that no longer exists.
Keep one voice and speed throughout. Paragraph synthesis preserves its natural punctuation;
spacing is 0.5s between paragraphs (0.3s between sentences in sentence mode). Use explicit
`[pause 2]`, `[predict 3]` or `[beat]` after a complete sentence for a deliberate hold. Markers are
never spoken or captioned; a prediction's end is the `reveal:` cue. An explicit hold replaces the
default/legacy hold on that sentence. Intro defaults: speed 0.95, chapter-end hold 2s, chapter gap
1.2s, beat 0.5s. `narration.json` owns these settings. Legacy `[key]`, `[aside]` and `[recap]`
markers still parse but do not affect delivery; `timing.pause` and `kokoro.role_speed` are ignored.
Old videos keep their timings until they are narrated again. A full stop after Dr., Mr., Mrs., Ms.,
Prof., St., vs., e.g., i.e., etc. or cf. ends no sentence, so a capital after it stays in the same
sentence (and keeps its sentence id); end a sentence on "etc." with care.

Run the pedagogy self-check and `studio check VIDEO --only script` before narration. Fill the
brief, log substantive diagnostics and accepted exceptions. `script_check` in video.json accepts
`products` (name → aliases), `product_budget`, `number_budget`, and scoped accepted findings such
as `"meta:s1_01"`. It counts narration and screen notes, not arbitrary scene code. Scene cues and
per-ID pronunciation overrides remain positional; validate/update them after sentence edits.

## Stage 5: Independent script review

Every teaching explainer gets a student pass before narration (`studio review VIDEO ROUND --only
student`), and learner drive or deep-dive level adds expert and editor review. The builder reports
**ready for script review** with the revision and inputs; the main session dispatches. Inputs,
round caps and what reviewers check are in `reviews.md`. If the user asked for the script to be
written or restyled by another writer (Claude Opus with the prose skill, say), do that before the
review and review its result (`taste/narration.md`).

## Stage 6: Narration

`studio narrate VIDEO --estimate` gives an approximate timeline without synthesis. Actual
`studio narrate` requires a current student pass for new teaching videos. Both print the laid-out
timings and the change in total length since the previous narration. `narration.json`
owns engine, voice, speed, timing and pronunciation. Keep its configured voice and speed constant;
do not add role-based changes or treat consistent delivery as a defect. Kokoro in paragraph mode
is the voice from the first narration to the published video, so the timing scenes are built
against is the final timing. ElevenLabs is used
only when the user asks for it, and is chosen before scenes are timed: `--plan` reports
cached/costed work, `--fetch-only --yes` fills its paid response cache; retain that cache. A voice
change moves every word, so recheck visual timing after one.

The per-video `lexicon.json` snapshot supplies shared pronunciations; narration.json overrides it,
then per-sentence overrides win. `studio lexicon add WORD --spoken "…" [--phonemes "…"]` promotes
a deliberate fix for future videos. Resolve or accept pronunciation lint findings (narration.json
`accepted`: words or `sentence:word`). Do not suppress a genuine variable A as an article.
Run `studio voice-check`; inspect every score under 0.8. It cannot reliably distinguish an acronym
read as letters from the same acronym read as a word. Run `--all` once before first delivery.
Missing extras/models print the precise doctor command; models are installed during setup.

## Stage 7: Boards

Before any scene code, settle what each beat shows and where. Write `boards/boards.json`: for each
chapter, frames that start at a sentence (`"from": "s2_04"`) and hold until the next, each a few
rough elements: `{"box": label, "at": [x, y], "w", "h"}`, `{"text", "at", "size"}`,
`{"arrow": [[x, y], [x, y]]}`, `{"line": …}`, `{"dot": [x, y]}`, in stage units (centred, y up,
eight high). A board is a layout decision, not a drawing: boxes and labels where the real elements
will go, enough to see an empty stage, a crowded one or a picture that never changes. Screen notes
fill in where no frame is drawn, so a chapter can start from its notes alone.

`studio boards VIDEO` makes a boards cut: one still per sentence with its screen note, and before and
after stills on the review page when boards change. It reports sentences with neither a board nor
a note. A chapter without a scene file renders its board in every cut, so boards stay useful as
scenes replace them one chapter at a time.

Post the boards cut on the desk and give the user the link (`gates.md`).

While boarding, hunt for the hero moments (`taste/delight.md`): the few events the picture can
perform with a sound, such as code typed and run, or a contact. Name each in its sentence's screen
note with what is shown, what is heard and what answers it, so the blocking leaves room for it and
the polish starts from it. A video with code being written has at least one.

## Stage 8: The animatic

`studio animatic VIDEO` holds each sentence's picture (scenes where they exist, boards elsewhere;
`--boards` for all) to the real narration, with its audio, and reports the runtime against
`target_minutes`, each chapter's length, the longest stretch where the picture does not change and
sentences with nothing on screen. Watch it, or at least read the report, before animating: a chapter
that runs long or a stage that sits empty while the voice talks is a board or script change now and a
rebuild later. It needs real narration (Kokoro is quick), so narrate before boards. It goes on the
desk too: the user can watch it while the scenes are built.

## Stage 9: The look

Run `studio look-sheet VIDEO` first: the model sheet, in the video's engine, theme and layout. Add
this video's own elements (its protagonist and each of its states) to `scenes/look.js` or
`scenes/look.tsx` from the template, exporting each drawing so scenes import it, and re-run. Scenes
draw what is on the sheet; the motion review checks drawings are on sheet. A live video with a 3D
chapter (only when the admission test in `taste/look.md` holds) puts its model on the sheet too, each
item in its own view, flat and oblique, in each state.

Make real static scenes for the main picture and a close-up; `studio cut --stills-only` records
these without displacing playable cuts. Get the user's choice before animation unless already
settled/authorized. Existing house style can supply a direction rather than requiring alternatives.

## Stage 10: Scenes and cuts

This stage is the blocking: what is where, and when each move happens. Polish (secondary motion,
anticipation, effects) is the next stage, planned from the start rather than added at the end, so
build the moves plainly here and leave room for it. Move the camera with keys (`c.camAt` in live,
`<Camera keys>` in Remotion; `engines.md`), staged apart from content changes; a layout `header` is
kept clear the way the band is. `studio check` warns (inframe) when an element the sentence names is
cut by the frame, header or band. A 3D chapter (live, `engines.md`) opens from its flat diagram with
`c.flatShot()` and returns to it, and `studio check` also warns (occluded) when a part the sentence
names is hidden behind the model.

One scene per chapter, built in order and cut as each is done: unbuilt chapters show their boards,
so every cut plays the whole video. In interactive mode, show the first finished chapter on the desk
before building the rest. On the live engine (`engines.md`), a chapter is `scenes/<clip>.js` and the
desk shows it the moment it is saved; on Remotion, every frame is a pure function of `useClip().t` (no timers, accumulated
state or unseeded randomness). `at`, `end` and `word` cue sentences; `phrase('03', 'and the whole
state')` cues the spoken words themselves, so a label lands as the voice says it and survives edits
elsewhere in the sentence; `cue('reveal:s1_03')` lands
a reveal after an inline hold, and an event of your own goes in `cues.json`, the beat sheet (never timeline.json): seconds, or an anchor such as `{"sentence": "s2_03", "phrase": "hits the floor", "offset": 0.05}` that follows its words when the narration moves. Name every contact there and time both the scene's move (`cue('name')`) and its effect (`studio sfx` on the name) from it, so they share a frame; every cut has a still two frames after each event, and `studio timeline VIDEO --events` lists them. Call `cue('name')` with the name written out: a clip re-renders when a cue its scene names (or one inside its frames) moves, and a computed name (`cue(x)`, reading `cues` directly) makes it re-render on every cue edit. `Beats`, `ramp`, `pulse` and closed-form `spring` drive progress.
Stage coordinates are centered, y up, eight units high, above the reserved caption band.

Use `@studio` primitives and the explainer components documented in `code.md`: CodePanel,
Terminal, JsonTree, RowTable, ColumnStrips, GeoMap, VarCard and Thread. These new components are
Remotion components; the data contracts are portable, but Motion Canvas scenes use its own kit.
Name important text/boxes for checks. Keep shared helpers small; changing one invalidates its users.
Motion must preserve the meaning of identity, copying, references and location (`taste/delight.md`).

Check a frame with `studio still`, then `studio cut` for changed clips only. Before sharing:
`studio check`, `studio sheets`, and one craft pass on changed chapters for readability, motion,
composition, synchronization and banned defaults. `studio check` warns at a hold under 0.5 s
between significant moves (pacing); space the moves or merge them into one. Inspect full-resolution crops; a reduced
contact sheet does not establish font size. Fix the significant findings; polish is the next stage.
`studio open VIDEO [CUT]` opens and protects an MP4; `studio desk` provides annotation playback.

## Stage 11: Polish

Polish is a stage of every explainer, with its own gate. Start from the hero moments named at the
boards and give them the most time: performed, timed to the words, with their sound
(`taste/delight.md`). Then, on the blocked chapters, add what makes
motion read as physical (`taste/delight.md`, and for a comic `taste/comic.md`): secondary motion (`follow`
for a label riding a moving token, `settle` for a heavy thing landing, `wobble` for a held picture
that should feel alive), anticipation before a significant move (a small wind-up, or the camera
easing before a zoom), and effects on the events of the beat sheet (`studio sfx` on the cue the
move waits on, so picture and sound share a frame). Cut, and keep `studio check` passing.

Then the motion review: `studio review-motion VIDEO`, reported as **ready for motion review**,
judged by a fresh reviewer the main session dispatches, and stopped by its rule (a round with no
must-fix findings, or `motion_rounds` rounds). The bundle, the import and the stop rule are in
`reviews.md`. Fix must-fix findings and leave the rest as the known issues it records; don't chase
should-fix findings round after round. In interactive mode the user watches every cut on the desk,
so it runs only when they ask.

## Stage 12: Independent frame review

Required before delivering a deep-dive, a shared video, or when video.json `frame_review` is true:
`studio sheets VIDEO VIDEO/out/sheets` (with `--strip CLIP T` for mechanism-sensitive transitions),
then `studio review-frames VIDEO`, reported as **ready for frame review**. The bundle, the import
and freshness are in `reviews.md`.

## Stage 13: Finish and hand over

Previews go on until the user says a cut is ready; record their words with `studio review-status
VIDEO approval passed --cut N --reason "…"` (`reviews.md`). Then run `studio publish VIDEO` for the
local final-quality master, including files-only delivery; external uploading remains a separate
authorized action (`publishing.md`). Default landscape is 1920×1080, but report actual dimensions
and fps, quality and final-quality status. The compressed web copy may have lower resolution. Report the cut/path or page, main
and sidebar lengths, model delta, changes, review/voice findings, late requests, stage times,
open issues and checkpoint. Add useful real viewer evidence to the learner model.
