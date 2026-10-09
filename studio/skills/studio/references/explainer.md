# Build an explainer

Start from the agreed `research/narrative.md`. Read `pedagogy.md`, `levels.md`, `style.md`, the
learner model and the video's snapshotted `research/house.md`. For code, also read `code.md`.
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
| 7 Boards | boards/boards.json, a boards cut | every sentence has a board or a screen note on screen | builder (user in interactive mode) |
| 8 Animatic | an animatic cut and its pacing report | runtime, unchanged stretches and empty sentences read and addressed | builder (user in interactive mode) |
| 9 The look | a stills-only cut | the user's pick, unless a house style already settles it | user |
| 10 Scenes, cuts, craft | cuts, chapter by chapter | `studio check` passes; craft pass on changed chapters | builder; the user reviews cuts |
| 11 Frame review | frame review receipt | required for deep-dive, shared or `frame_review` videos | fresh reviewer; the main session dispatches |
| 12 Finish | local master, page | `studio publish` gate passes | user |

`mode` in video.json sets how the user takes part. In `background` (the default) an agent builds
unattended: the user approves the narrative, picks the look and reviews cuts; boards and the
animatic are the builder's own checks, and nothing waits on the user. In `interactive` the user
follows on the desk: the main session builds in the foreground, chapter by chapter, opens the desk
before stage 7, says when each chapter is ready there, and takes each note as it arrives
(`desk.md`). Older videos that say `checkpoints: many` load as interactive.

## Ownership

One builder owns the folder: `studio lock VIDEO acquire --owner NAME`, then use the printed
`STUDIO_OWNER` for its commands. Keep ownership across stages and direct file edits. The main
session queues additions with `studio request VIDEO "text"`; read pending requests at stage
boundaries and resolve each incorporated request with `studio request VIDEO --resolve ID`.
Explicit stop/correction applies immediately. Reviewers use snapshots, never edit the folder.
Release the lease when handing ownership back; recover only an abandoned build.

Mark stages with `studio stage VIDEO NAME`; `waiting` excludes user wait from active budgets and
`finished` closes timing. video.json `budget` holds minutes: `first_cut`, `round` and
`structural_round` for the scopes, and a stage's name as it is marked (`"scenes": 30`) for a
budget on that stage alone: every run of it since the latest round mark (the first cut, before
one), resumed runs included; there are no per-stage defaults. Over-budget reports are advisory:
re-estimate changed scope and report where time went, without skipping correctness. Commit at
authorized stages through `studio commit`. Never push a video's repository without authorization.
See `publishing.md` for revision rounds.

One exception is a hard stop. In background mode, a stage with its own budget in video.json stops
at twice that budget: `studio stage` prints a STOP line, and `studio stage VIDEO --check` (which
marks nothing and exits 3 when stopped) says the same between chapters. Run the check between
chapters and fix rounds of a long stage. On STOP, write a handoff, report to the main session and
do not continue. The main session decides whether to raise that stage's budget or stop there. The
`first_cut` and `round` defaults are not calibrated against real builds, so they never stop a build,
and nothing stops in interactive mode, where the user is watching.

In background mode, write `studio handoff VIDEO --notes "…"` at every stage boundary and before
stopping. It writes `research/handoff.md`, a brief a fresh builder can act on without your
transcript: the owner, the stage against its budget, the last cut and its open notes, reviews in
flight, pending requests, the next commands, and your notes on what the files don't show (a
half-finished chapter, a decision and its reason, a helper and what it does). `studio lock VIDEO
acquire --recover` prints the brief and its age to whoever takes over.

Scratch goes in `VIDEO/.studio/work/`, never /tmp: probes, intermediate frames, a helper being
tried out. Inside the video it survives a restart, but Git ignores it and fork leaves it behind. A
helper the build depends on, or one a later builder or a fork should rerun, moves to `sims/`, which
is committed and forked with the sources and holds the video's scripts: evidence extraction and
build helpers alike. Run either with `studio run VIDEO SCRIPT [ARGS…]`. It uses the kit's Python
with the kit importable, runs in the video's folder with stdin closed, and goes through the
allowlisted `bin/studio`, so no path trick is needed to get past a sandbox. `.mjs`/`.js` scripts
run with node, without the engines' packages on their import path.

## Long passes

A fix round or polish pass over a whole video is where builds run long and builders run out of
context.

- **Split by chapter when the main session can run several builders.** The lock is per video, and
  every changing command takes a short operation lock that fails, without waiting, while another
  runs. So the main session holds the lock (`studio lock VIDEO acquire --owner main`) and gives
  each chapter fixer its `STUDIO_OWNER` token and a disjoint set of files: its own
  `scenes/<clip>.js` and its chapter's boards. A fixer edits only those files and checks its frames
  with `studio still` on its own clips, trying again after a few seconds when told another
  operation is running. It never runs `cut`, `check`, `narrate`, `timeline`, `stage` or
  `commit`, and never edits a shared file (SCRIPT.md, `cues.json`, captions, a helper several
  scenes import). A change to a shared file comes back to the main session as a patch with its
  reason. When every fixer has reported, the main session applies the patches, runs `studio
  check` and makes one cut.
- **Keep each builder's context small.** Hand frame inspection to sub-agents. A sub-agent reads
  the stills, sheets or strips and returns findings as text (clip, time, element, what is wrong),
  not images. A builder that reads every frame itself fills its context with pictures and stops
  mid-pass.
- **Write a handoff at every stage boundary** in background mode, and before any stop, so a
  restart costs minutes.

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
Use `[pause 2]`, `[predict 3]` or `[beat]` immediately after a complete sentence. These become
inserted silence after speech, in addition to its natural gap; they are never spoken or captioned.
An explicit marker replaces the default/legacy hold on that sentence. A sentence may have one
marker. Intro defaults on new videos: speed 0.95, chapter-end hold 2s, chapter gap 1.2s, beat 0.5s.
Override in `narration.json.timing` and voice settings. Old videos retain their timing defaults.

Run the pedagogy self-check and `studio check VIDEO --only script` before narration. Fill the
brief, log substantive diagnostics and accepted exceptions. `script_check` in video.json accepts
`products` (name → aliases), `product_budget`, `number_budget`, and scoped accepted findings such
as `"meta:s1_01"`. It counts narration and screen notes, not arbitrary scene code. Scene cues and
per-ID pronunciation overrides remain positional; validate/update them after sentence edits.

## Stage 5: Independent script review

Every teaching explainer gets one student pass before synthesis, including author/intro:
`studio review VIDEO ROUND --only student`. SCRIPT.md's status names the round. The main session
owns dispatch; a child builder reports **ready for script review** with the revision and inputs.
The existing CLI starts fresh processes; use a fresh main-session reviewer only when needed and
record unavailable isolation honestly. An empty directory is not a filesystem sandbox.

Learner drive or deep-dive level also requires expert and editor review. For risky claims in an
author/intro video, record additional roles in `video.json.review_roles`. Inputs are separated: expert
gets script/evidence, student gets audience/script/transfer questions without answers, editor gets
argument/chain/script. None gets the Review log or prior verdicts. Respect the charter; add detail
only if the learning chain needs it. Review receipts are tied to the current teaching material.

Fix blockers and apply relevant smaller fixes once. Default cap is three rounds (third for a
blocking issue), economy two, thorough six, per revision of the script: the kit counts the scripts
reviewed since the latest structural stage mark, whatever ROUND says, and a re-run on an unchanged
script is the same round. A structural revision
(`studio stage VIDEO revision --kind structural --summary …`), marked over a script that changed
since its last review, starts the count again; a mark alone does not. Raising `max_rounds` is the
learner's decision. Repeatedly opposed advice is surfaced to the user, not
endlessly rewritten. Caps leave findings open; they never turn a failed check into a pass.
After a material teaching edit, rerun the affected review. A simulated student is a diagnostic,
not evidence of real learning. If a required review is unavailable, report it; a user-authorized
waiver is recorded with `studio review-status VIDEO student waived --reason "authorization"`.

## Stage 6: Narration

`studio narrate VIDEO --estimate` gives a timeline without synthesis. Actual `studio narrate`
requires a current student pass for new teaching videos. `narration.json` owns engine, voice,
speed, timing and pronunciation. Kokoro in paragraph mode is the voice from the first narration to
the published video, so the timing scenes are built against is the final timing. ElevenLabs is used
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

## Stage 8: The animatic

`studio animatic VIDEO` holds each sentence's picture (scenes where they exist, boards elsewhere;
`--boards` for all) to the real narration, with its audio, and reports the runtime against
`target_minutes`, each chapter's length, the longest stretch where the picture does not change and
sentences with nothing on screen. Watch it, or at least read the report, before animating: a chapter
that runs long or a stage that sits empty while the voice talks is a board or script change now and a
rebuild later. It needs real narration (Kokoro is quick), so narrate before boards.

## Stage 9: The look

Make real static scenes for the main picture and a close-up; `studio cut --stills-only` records
these without displacing playable cuts. Get the user's choice before animation unless already
settled/authorized. Existing house style can supply a direction rather than requiring alternatives.

## Stage 10: Scenes, cuts and craft

One scene per chapter, built in order and cut as each is done: unbuilt chapters show their boards,
so every cut plays the whole video. In interactive mode, show the first finished chapter on the desk
before building the rest. On the live engine (`engines.md`), a chapter is `scenes/<clip>.js` and the
desk shows it the moment it is saved; on Remotion, every frame is a pure function of `useClip().t` (no timers, accumulated
state or unseeded randomness). `at`, `end` and `word` cue sentences; `phrase('03', 'and the whole
state')` cues the spoken words themselves, so a label lands as the voice says it and survives edits
elsewhere in the sentence; `cue('reveal:s1_03')` lands
a reveal after an inline hold, and a cue of your own is named in `cues.json` (never timeline.json). Call `cue('name')` with the name written out: a clip re-renders when a cue its scene names (or one inside its frames) moves, and a computed name (`cue(x)`, reading `cues` directly) makes it re-render on every cue edit. `Beats`, `ramp`, `pulse` and closed-form `spring` drive progress.
Stage coordinates are centered, y up, eight units high, above the reserved caption band.

Use `@studio` primitives and the explainer components documented in `code.md`: CodePanel,
Terminal, JsonTree, RowTable, ColumnStrips, GeoMap, VarCard and Thread. These new components are
Remotion components; the data contracts are portable, but Motion Canvas scenes use its own kit.
Name important text/boxes for checks. Keep shared helpers small; changing one invalidates its users.
Motion must preserve the meaning of identity, copying, references and location (`style.md`).

Check a frame with `studio still`, then `studio cut` for changed clips only. Before sharing:
`studio check`, `studio sheets`, and one craft pass on changed chapters for readability, motion,
composition, synchronization and banned defaults. Inspect full-resolution crops; a reduced
contact sheet does not establish font size. Fix the significant findings; avoid endless polish.
`studio open VIDEO [CUT]` opens and protects an MP4; `studio desk` provides annotation playback.

## Stage 11: Independent frame review

Required before delivering a deep-dive, a shared video, or when video.json `frame_review` is true.
First run `studio sheets VIDEO VIDEO/out/sheets` for the current cut, adding `--strip CLIP T` for
mechanism-sensitive transitions (`--strip` repeats; `--windows FILE` lists many). `studio
review-frames VIDEO` packages that directory together with the current cut's stills, script and
data; sheets saved elsewhere are not included.
The builder reports **ready for frame review**. The main session dispatches a fresh image-capable
reviewer using `prompts/frame_review.md`; the command itself does not start an agent. Include
transition strips for mechanism-sensitive motion. Validate findings against full-resolution frames.
Import the response with `studio review-frames VIDEO --result FILE`; it must include the bundle's
REVISION and FRAMES verdict. A change to what the reviewer saw invalidates the receipt, and a result
for a cut older than the sources is recorded as stale (`publishing.md`). Never label a builder's
own pass independent. Unavailable/authorized waived reviews use `studio review-status`.

## Stage 12: Finish and hand over

Run `studio publish VIDEO` for the local final-quality master, including files-only delivery;
external uploading remains a separate authorized action (`publishing.md`). Default landscape is
1920×1080, but report actual dimensions and fps, quality, final-quality status and user approval
separately. The compressed web copy may have lower resolution. Report the cut/path or page, main
and sidebar lengths, model delta, changes, review/voice findings, late requests, stage times,
open issues and checkpoint. Add useful real viewer evidence to the learner model.
