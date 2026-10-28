# Studio release history

What each release changed and why, moved out of the skill's DESIGN.md so agents reading the skill
see current rules, not their history. DESIGN.md keeps the standing rationale.

## A video's media on any machine (0.20.0)

With the studio journey in Git and its media backed up to a Cloudflare R2 bucket, a clone on another
machine or in a cloud session had every script and narration response but none of the media Git leaves
out: a recording, a downloaded sound, the shipped master. Patrik asked for the reproducible way to work
on a video anywhere.

- `studio media push VIDEO` uploads each such file to the media bucket under its SHA-256 and lists it,
  with its size, in the video's `media.json`, which Git keeps. The default set is the ignored media
  outside `.cache/`, `cuts/` and `research/`, which studio makes again; a file named on the command line
  is listed too, and a listed file stays listed on a machine that never pulled it. Content addressing
  means an unchanged file or a sound two videos share is stored once.
- `studio media pull VIDEO` fetches each listed file a folder lacks and checks it against its hash
  before it replaces anything; a local copy that differs is kept unless `--force`. `--dry-run` says
  what is present and what would come.
- The bucket speaks S3; requests are signed in the kit with AWS Signature V4 (checked against Amazon's
  published example), so nothing new is installed. The credentials are papershop's
  `RCLONE_CONFIG_R2_*` secrets, from the environment or decrypted for the transfer, the way the
  ElevenLabs key is; `script/doctor` and the receipt say whether they decrypt, and in a cloud session
  whether the bucket's host is allowed.

Review stills stay out of Git too. Episode 1 of the observability series added 287 MB to the studio
journey repo, 248 MB of it the stills and motion sheets of its chapter reviews. Those images are copies
of a cut's frames that a new review makes again, and the checkpoint meant to leave them out, but its
rule named the older bundle folders (`research/*_review/`) while chapter reviews write to
`research/reviews/cutN/CHAPTER/`.

- `studio commit` now leaves out PNG, JPEG and WebP files under `research/reviews/` too; a review's
  manifest, prompt, findings and the panel notes are still committed. A film made earlier gets the
  rule on its next commit; images it already tracks stay tracked until removed with `git rm --cached`.

## A quieter desk once a cut is ready (0.19.1)

Watching episode 1's fifth cut, Patrik found the desk mostly noise: 114 notes already acted on filled
the Notes panel, eleven "Chapter finished" rows filled the timeline, and the header said "s10
failing · 10/11 chapters finished" for one accepted legibility check in a finished film.

- The Notes panel lists open notes; closed ones fold behind "Show N closed", and their marks leave
  the timeline until shown.
- The chapter-agent rows are the shoot's build log. Once a version is ready (and no build is being
  replayed) only the chapters that need attention keep a row: failing, stalled or unbuilt ones.
- The desk broke mid-review when a sentence was re-narrated: the live mix came out at the old length,
  the soundtrack raised, and the whole page state failed. The live desk now falls back to the
  narration alone, as it already did when an effect's cue was gone.
- With a version ready, the header names it and the chapter with a failed check ("v5 ready · s10
  has a failed check") instead of counting chapters as if the build were still running.
- On cut 7 the header still said "s4 failing · s9 failing" for checks that had since passed. Results
  were keyed by check and second, and re-timing a chapter moves its checks to new seconds, so an old
  failure was never replaced. Each run of a chapter's checks now records a `checks.ran` event, and a
  lane shows only its latest run's results.

## Films in a home kept in Git (0.19.0)

~/studio is becoming one Git repository for the whole practice, with films under `films/` next to
notes, verdicts and plans. Two things stood in the way.

- `studio new` puts a film in `$STUDIO_HOME/films/NAME` when `films/` exists, and in
  `$STUDIO_HOME/NAME` as before when it doesn't. The nearest-video suggestion searches both.
- A film inside a home repository that ignores its folder (the home's `.gitignore` opts folders in
  with `/*`) got no repository of its own, so every checkpoint quietly committed nothing. A film now
  gets its own repository unless the enclosing one actually tracks its folder.

## ElevenLabs narration from a cloud session (0.18.2)

A fresh cloud session should be able to make new ElevenLabs narration, not only rebuild cached audio.
No package can carry a secret, so the key is committed encrypted (sops, one age recipient per machine,
`script/secrets` in papershop) and each machine holds only its age key. Builds and tests still never
need it, and each response is still cached in `audio/elevenlabs_cache/` and committed.

- `narration.eleven_key()` reads `ELEVENLABS_API_KEY`, else decrypts it from papershop's
  `secrets/secrets.json` (or `PAPERSHOP_SECRETS`) only when text must be fetched.
- A missing key or a blocked `api.elevenlabs.io` stops with the setting that fixes it, before any
  spending, instead of a bare error or a traceback.
- The studio shell carries sops and age; its tests need them.

## Extras survive a rebuilt environment (0.18.1)

Pinning the managed Python (3.12.13) made uv rebuild the kit's `.venv`, which keeps only what the
next sync asks for. `script/bootstrap` asked for audio and Kokoro, so the voice check's recogniser
(the align extra) silently disappeared and `studio voice-check` and `studio align` failed.

- `studio doctor --fetch` records the extras it installs in `kit/.extras`, outside the environment,
  and `bin/studio` restores them on every run with its usual non-destructive sync.
- `script/bootstrap` installs align with audio (Kokoro stays opt-in) and records them too.

## Delivery tags for ElevenLabs (0.18.0)

The ElevenLabs v4 guide directs delivery with bracketed tags such as `[curious]`, but SCRIPT.md
already uses square brackets for breaths and pauses, and any other bracket stayed in the caption
and was read aloud by Kokoro.

- Any bracket that is not a studio marker is a delivery tag. It goes at the start of a sentence
  (a tag inside one is refused), is sent to ElevenLabs in front of that sentence, and is removed
  from captions, Kokoro's text and the voice check.
- Word timing skips the tag's characters, which ElevenLabs' alignment includes. A script without
  tags sends the same text as before, so cached takes stay valid.
- `script.md` asks for a few tags per film, where the words alone can't carry the delivery.

## Narration written for the ear (0.17.0)

The user named the narration as the videos' primary weakness: “The script is not that great, I
think it has to be much more engaging and natural. Use full sentences, use "we", etc.” Measured
against 3Blue1Brown, Sebastian Lague, the Mollick AI-origins film and a corpus of popular
explainers' captions, our eleven October scripts never said “I”, almost never said “you”, used no
contractions, kept nearly every sentence at twelve to fifteen words and rarely asked a question.

- New working reference `references/script.md`: talk to one person, keep a question open, give
  2 + 2, people and things before abstractions, chain cause to cause, write for the ear, beat the
  misconception, point rather than narrate the camera, keep caveats in the Evidence table, and end
  on the opening changed. It names the four moments a viewer remembers, the tics to cut and five
  before/after pairs from our own films, and ends with Saunders's read-aloud revision method.
- `references/script-example.md` rewrites the TCP origins film's narration end to end, with
  the reason for each change.
- The skill, story step, desk revisions and SCRIPT template point to it. The taste file's
  narration section shrinks to a summary and a link. The story panel's editor now reads the
  narration against it.
- Voice remains Kokoro; moving to ElevenLabs is a separate change.

## Reproducible narration and checks (0.16.2)

The papershop repo now has to bootstrap and pass its tests on any machine (the Mac, Claude's cloud,
CI), and to make the same output from the same input. Three studio fixes came out of checking that.

- Kokoro loads its model and voices from one pinned commit of its Hugging Face repo instead of
  following `main`, and each synthesis call is seeded: the vocoder adds random noise, so the same
  sentence used to come out different on every run. Paragraphs synthesised from now on can sound
  slightly different from earlier ones; cached audio is untouched.
- The sound kit's manifest cache is keyed on the file's bytes, not its mtime, which on Linux ticks
  too coarsely to see a quick rewrite.
- `studio doctor` probes the browser with `--no-sandbox` when it runs as root (a container, the
  cloud), as Playwright does when it renders, so the check no longer fails where rendering works.
- The tests stop at once, with the fix, when Node 22, ffmpeg or sox is missing.

## Visuals at the center (0.16.0)

The user found the 0.15 hash-table film visually lame, its sound effects cheap, its governing
question forced and some pauses too long. The earlier taste revision had over-corrected toward
calm and minimal. The loved shader sphere, Blender hard drive, tunnel game-feel pass and real
keyboard performance establish spatial and tactile craft where those subjects call for it.
Part E establishes a separate flat drawing standard for abstract subjects. Part F places still,
silent rests after key points and at section endings, with flowing motion inside each idea.

- Standard lectures now follow canonical textbook order. A protagonist and governing question
  are optional tools; three or four ideas is guidance, not a cap. The old two-prediction quota
  is removed. One thing at a time, full
  sentences, canonical level and few numbers remain.
- One new preparation step after story lock renders three to five finished style frames in the
  real engine and compares references of the same kind: 3Blue1Brown for abstract subjects,
  Ciechanowski or Kurzgesagt for physical ones. Shoot jobs carry the matching images and
  drawing/composition judgment. Existing chapter reviews compare the
  finished film with them; there is no new review stage or engine.
- Abstract subjects use 2D craft at the 3Blue1Brown standard: meaningful colour, confident vector
  marks, moving type, a large mechanism, continuous transformations and varied shots. A physical
  metaphor must map exactly and stay flat. Physical subjects may use the lit look and Blender
  after the restored hard test: “the viewer needs to see ___, and the flat diagram hides it.”
  Abstract subjects almost never pass. The banned generated-design defaults remain.
- Effects default to an empty list. Shoot jobs list exact permitted tactile touches; abstract
  bucket arrivals, labels and reveals stay silent. The recorded kit, shared event frames and
  no-music default remain.
- Rhythm now follows meaning: 1.5–3 seconds of stillness and silence after named key points and
  hero payoffs, and 3–4 seconds between sections including a stage reset. Related motion can
  flow under narration; there is no hold after every small change. One genuinely new mechanism
  at a time and the dead-time warning remain. The reason is the user's part F response: the
  attractive 2D film still felt too busy and never took a real breath.
- The brief and beat table name breaths. `[breath N]` reuses narration's silence layout and
  records its exact interval in the timeline and chapter jobs. The final generated caption
  phrase stays through the rest. Pacing exempts only marked breaths/predictions from dead-time
  warnings, reports significant motion inside breaths, and treats short gaps as diagnostics
  rather than prescriptions for more holds. No new renderer or workflow stage is introduced.
- The scaffold’s eight-second tail becomes 0.8 seconds. Narration adds why, cost and failure
  while the picture shows the mechanism.

Part D's hash-table cabinet followed the wrong visual brief. The user rejected the 3D result;
the model's preference for richer objects did not predict the user's taste. Part E corrects the
brief and remakes the prompt in flat 2D, following Elicit, story, like-for-like style comparisons
and parallel chapter production. Evidence and honest limitations are in
~/drafts/studio-phase2/STEP-E.md; the rejected cabinet evidence remains in STEP-D.md. References
remain in research only. This correction stays in 0.16.0.

The fresh 2:56 hash-table remake uses original flat vector scenes, three style-frame rounds beside
four official 3Blue1Brown lesson stills, and one combined review per chapter. Nine accepted picture
findings and a saved-final label-overlap correction improve the actual mechanism and readability.
The film varies association, arithmetic, table, chain, resize and cost views; effects and music
remain absent. First playable was 15m35s after story lock, missing the target by 35 seconds.
The full suite passes 663 tests. The report includes matched-time cabinet/2D/reference contact
sheets, delegated decision reasons and saved-film diagnostics. The result fits an abstraction
better, but still falls short of 3Blue1Brown in composition and choreography. Native playback was
blocked by computer permissions; human listening and the user's taste verdict were unverified
at that stage. The user subsequently called the 2D result “really nice” and asked for breaths
after important points and sections, while allowing motion elsewhere.

Part F preserves the 2:56 film and re-times an independent scratch copy to **3:13.10**. Eleven
still, silent breaths follow the named ideas and hero payoffs, including both section endings;
the stage clears before the next section. Related moves absorb small per-change holds, while
Bea/Leo insertion and resize records act sequentially and unnecessary camera excursions go.
All 459 words and all 36 speech segments remain sample-identical. A production-found caption
interruption was fixed by retaining the final phrase through a breath. A saved-film sampling
edge incorrectly counted the next section's clear as breath motion; the check now measures
interior samples and retains detection of actual motion inside the pause.

The final full suite passes **670 tests**. The saved master verifies all eleven rests, including
captions, across 687 decoded interior frames and silent audio. Publication has 172 checks with
no failures; audio has 16 rows with no failures or warnings, and each chapter has zero general
flashes. Eight short-gap groups and three small-trace pacing diagnostics remain explained rather
than hidden with decorative movement. ~/drafts/studio-phase2/STEP-F.md records the exact rule,
every breath and removed hold, both film lengths, a saved-film motion/stillness timeline, delegated reasons and an honest
judgement. All 1,488 inventoried original-film files are unchanged. This remains version 0.16.0.

## Story, shoot and desk (0.15.0)

Phase 1 compared the same five-minute shaders request. A bare agent produced its video in
21 minutes; Studio 0.14 took 2 hours 10 minutes. The Studio timing included 18 minutes writing
scenes, 57 minutes polishing, 23 minutes waiting for serial reviews and 8 minutes publishing.
Applying review notes invalidated the review record, so one builder ran another review and left
its notes unapplied to preserve approval. The user liked the bare video's result and preferred
Studio's recorded keyboard clicks. Across 27 videos, all were explainers: 17 used live and 10
used Remotion. The unused engines, genre workflows and generated music had no production use.

- The workflow is now three verbs and two user decisions. Develop the brief and narrated story
  reel together, lock the story, shoot chapters in parallel, then iterate on the desk until the
  user says ship it. The first playable cut targets 10–15 minutes after story lock. The delegated
  shaders shoot met that target: 10m43s from story lock to a playable desk version.
- Consolidated the user's taste into one reference, with reasons and a place for lasting notes.
  The router and five working references replace the large process reading stack. Level and tone
  are sentences in the brief. Comedy remains an optional reference read only on request.
- Removed the motion, launch, pixel and recording-edit genres from the core, their templates and
  checks, the unused Motion Canvas and cairo engines, and the 14 routing evals. A short by-hand
  reference explains how to approach those videos using the remaining kit.
- Removed review receipts, revision counters, caps, waivers and stale-review refusals; work
  budgets, hard stops, owner tokens, the request queue and chapter-fixer roles; learner and house
  snapshots; and the drive, level, tone, delivery, mode and checkpoints switches. Plain findings,
  waiting file locks and elapsed stage timing remain.
- Removed imported-cut and portable-note workflows, the generated music-bed command, variant,
  fork, restructure, kit-copy updates, tutor import, recorded-step orchestration and archive.
  Publish now writes the colophon beside the master. Existing videos retain their pinned 0.14 kit.
- Added `reel`, `panel`, `shoot`, `review-pack`, `suggest` and `ablation`. The panel reads the brief
  once through three parallel perspectives. Chapter cues, scenes and data are isolated, chapter
  checks use private workspaces, and shoot prints one job per chapter for the main Agent session.
  A combined motion/frame pass per chapter becomes suggested desk notes the user accepts or
  dismisses. Ablation prepares separate bare-agent and Studio starts for a later comparison.
- Publishing records the user's shipping decision as one line with a name and time. It keeps
  full deterministic checks and the measured mix. Listening supplies judgment without a receipt.
  The live engine, 3D, lit look, plates, sound kit, exact typed-key streams, narration, captions,
  timeline, incremental cuts, desk, exports and provenance remain.

- Proved a 4:56 shaders explainer with three parallel chapter agents, private checks, one parallel
  review pass and a published final. Prompt to story lock took 7m43s; first playable took 10m43s
  after lock. Matched-time contact sheets compare it with both phase 1 videos. The proof exposed
  and fixed board text sizing, punctuation typos, literal JSON dependency handling and per-key sync checks.
- Rebuilt the desktop desk around a viewer, story/picture/voice/sound/note lanes and an inspector.
  Notes autosave immediately at moments, ranges, beats, whole videos or chapter lanes. Added keyboard
  transport, speed, captions, same-time A/B, change lists and automatic new-cut arrival. Fixed the
  pre-play duration, A during playback, dropped watcher notes, theme paint and process lifetime.
- Added `event`, append-only production events, real chapter activity, live chapter arrivals,
  exact-time check marks, decision pins, cooperative lane/whole-build Stop and measured ETA.
  Quiet/stalled transitions were measured at 30.13s/120.13s; a real save appeared in 0.578s.
  Browser evidence includes dark/light at 1440×900 and 1920×1080 and a real build replayed at 10x.
- Ported CodePanel, Terminal, Editor, RunTerminal, ProgramWindow and HelperCard to live, including
  collapse, folds, highlights and payoff. Compared twelve paired frames and all 1,800 replay states;
  the final minute-long code proof measured all 26 key attacks within 0.15 frames. Removed Remotion,
  its templates, setup dependency and active references after the proof. Browser setup uses the
  pinned Playwright package and an independent cache; existing videos were left untouched.
- Story now starts with Elicit's panel and brief, with an under-15-line local fallback when the
  skill is absent. User words override taste, which overrides Elicit. The one-page conversion
  cuts scope, never craft; chapter jobs receive only their hero moments and relevant principles.
  Proved a 3:02 hash-table film through lock, parallel shoot, review and publication; first playable
  took 7m11s after lock. The fallback brief retained essentially the same story, so this sequential
  comparison does not establish Elicit's superiority.
- Installed metadata-only Claude hooks for background launches, tool completion/failure and subagent
  stop. A small expiring active-shoot record and explicit tags/job reads prevent cross-session lane
  guesses. Legacy Task payloads use returned agent ids for lifecycle and exact chapter paths/commands
  for tool activity when caller ids are absent. Bursts coalesce; Codex retains explicit events.
  The absent-record path measured 4.54ms median / 5.23ms p95 under suite load. A real Haiku subagent's
  events appeared on the desk; its parent CLI required compatibility resumes and later termination.
- Fixed the intermittent suggestion-button browser test: visible notes did not imply that the
  live iframe had finished starting. A deliberately delayed player now establishes that precondition
  before the test checks whether note refreshes preserve it. Five focused repeats passed.
- The complete Studio suite passes 659 tests, including recorded hook payloads and cold-player
  suggestion-button coverage. Saved-frame comparisons, browser interactions and
  real liveness/steering evidence accompany the production proofs; human listening and user taste
  judgments remain explicitly unverified.

Earlier entries below describe the versions they shipped, including interfaces retired here.

## Session videos (0.14.0)

Three videos of the user's own game-programming sessions, the last rebuilt as a visual-first
"two clocks", showed what a modest learning video needs and what the studio's defaults got in the
way of: voice talking over a mechanism the first time it appeared, a perpetual loop behind the next
idea, a polish stage and several review rounds for a cut nobody would publish, a fallback pipeline
written beside the kit when no browser could start, and a hand-made typed-code editor with keys
that did not land on their frames. The user's corrections were about pacing and staging far more
than about animation.

- **Session delivery.** `delivery: session` (`studio new --delivery session`; `references/session.md`
  is its one home): one review cycle (`max_rounds` and `motion_rounds` default to 1), a 540p desk
  cut, one beat preview in place of boards and animatic, polish and hero embellishments on request,
  a beat table before the prose, full "we" narration over a settled picture. Delight and the motion
  review now ask for introduce, settle, explain for a session video; an unconditional "motion starts
  with its sentence" stays for polished work. The final viewing and listening is the user's, and the
  receipt records who (`review-status … --by`).
- **Timeline repairs.** Narrated and silent-clip timelines keep `layout.json`'s frame rate (they
  restored 30 fps). The encoded soundtrack is written aside, checked against the video's length and
  then promoted; a truncated file left by an interrupted run is no longer reused.
- **Keys on their frames.** A typed key's sound time comes from its displayed frame, typing streams
  are `"exact"` (pitch and level vary, timing does not), and each grain's attack is measured instead
  of assumed.
- **Staging checks.** `staging.json` declares introductions, replays, typing, questions and loops
  with cues.json times; `studio check` names each conflict with the narration (intro under voice,
  unsettled, question not held, loop runs on). The hundreds of pacing warnings become one per
  stretch of crowded moves.
- **The code view.** `data/codeview.json`: the Remotion `Editor` collapses between uses, shows folds
  in source order, lights lines before the words that name them, draws helper cards (`HelperCard`)
  and ends on the whole program. The `code-view` check holds ranges, highlight lead, the payoff
  and the closure of every name.
- **A cairo engine.** `"engine": "cairo"` draws still, render, boxes and duration natively (Python
  scenes, pycairo, ffmpeg), with no browser and no local port, and declares what it does not do.
  Engines list their capabilities; preflight checks pycairo and cached Kokoro weights without the
  network (`STUDIO_OFFLINE=1`); reviewers can come from `STUDIO_REVIEW_COMMAND` and are recorded as
  unavailable when there is none.
- **Imported cuts.** `studio import-cut` takes an MP4 and timeline from elsewhere, checked to agree,
  with an identity of media and timeline hashes. `review-export` writes a static review page, and
  `notes-export`/`notes-import` carry notes only onto a cut with the same media. Approvals and
  listenings of an imported cut lapse when its media is replaced.

Not yet tried on a real video: the cairo scene API is minimal (rectangles, text, lines), the staging
numbers (1 s settle, 2 s question, 0.6 s lead) are starting values, and the code view's Remotion
changes are type-checked but unrendered.

## Feel spent on meaning (0.13.0)

An analysis of studio against game feel, film editing, sound design and multimedia learning found
that studio already performed each event: set up, landing on its sound, settling, with one cue
for both. What it lacked was a rule for how much feel an event gets and what the feel may claim,
and the layers around an event. A 20-second film made outside studio, plain until a stake,
consequences, proximity and materials were added, was the worked case. Two independent reviews of
the analysis cut it back: a boolean hero flag became a graded weight beside the `visual` tag,
hitstop and shake moved out of the engine into scenes templates and behind a test of what they
encode, and safety came before the effects that need it.

- **Stakes.** The learning brief names the protagonist's want, what blocks it and the frame the
  payoff gives it, shown on its glyph (`references/pedagogy.md`, self-check item 14).
- **Weights.** A `cues.json` anchor takes `weight` 1 to 3 and `hitstop` frames. audio-check features
  weight-3 effects first; the motion review checks each event's layers against its weight and that
  every layer encodes something true (`references/taste/delight.md`, "Spend feel on meaning").
- **Rules around the event.** Consequence (the world reacts, as the mechanism causes), close to feel
  and wide to explain, cut when the viewer can close the gap, silence before a reveal, sound that
  leads the picture into a chapter, and a material per landing element in the look file. The motion
  review gains items for each.
- **Hitstop and trauma shake** as `example-feel.js` and `example-feel.ts` scenes templates, capped at
  12 px and 1 degree, and `"motion": "reduced"` in video.json, which turns both off and keys live
  clips. The glossary's shake is the trauma kick; hitstop is a term. Pacing reads a hitstop's hold
  as meant.
- **Checks.** `studio check` fails more than three general flashes in any second (WCAG 2.3.1,
  approximately). audio-check measures the dip before each reveal and lists effects near chapter
  cuts.

Not yet tried on a real video; DESIGN.md's Still open says what would show they help.

## A narrative from a present-your-work story (0.12.1)

An article and a video about three weeks of autonomous research passed every check and lost their
reader: the video's narrative was drafted from the article, which had been built bottom-up from a
journal and a ledger of claims. When the `present-your-work` plugin has written a `STORY.md` for the
work (the story card, the background chain and the vocabulary), the narrative stage now starts from
it instead of drafting its own, and the narrative is approved the same way (`references/propose.md`,
steps 4 and 5).

## Performed events, plates, and instructions by job (0.12.0)

Two videos made by another agent, a hard-drive film and an introduction to game development,
showed where the studio stopped being used. The hard-drive film moved to Blender and about fifty
scripts of its own replaced the desk, cut records, reviews and publish; the game-dev video worked
around three kit bugs and built its own typed-code editor and key sounds. The user's corrections
were mostly gates: a final rendered before they were done with previews, a draft not shown first,
"go ahead" read as more than it said, a desk they had to ask about, an animatic nobody showed them.

- **Gates.** A final cut and publish need the user's recorded approval of a cut, which lapses when
  the picture changes. The desk shows a background build's boards, animatic and cuts with the whole
  mix, and says when the builder read a round of notes. `references/gates.md` lists every decision.
- **Performed events.** `studio typing` types code from a plan of edits between recorded versions,
  for a Remotion `Editor`, `RunTerminal` and `ProgramWindow`, with one key stream for the sound. An
  effect can be a stream of many events (grains of real typing, thinning when dense, stepping back
  under a word), a pool of variants, or the video's own recording; the sound kit has keyboard
  recordings. `taste/delight.md` says what to aim for: hero moments, cause and effect in one shot.
- **Realism.** `G.lit()` gives the 3D stage light, soft shadows and materials. Plates let Blender
  render the picture behind a live chapter, with labels on the points it projects, so the checks,
  desk and publish still work; frames render on demand, resume, and can be probed for an estimate.
- **Reliability.** Engines reply through a file (a pipe cut replies at 64 KiB); paths are made
  absolute when parsed; 3D boxes are clipped to their view; a band of height 0 means no captions;
  Pillow ships with the kit; cuts say how long their render should take; clean reaches plate frames
  and old review images; a clip's key hashes only the data its scenes read; `studio steps` keeps a
  program's captures and checks they replay the same; `studio restructure` reshapes a video in
  place; `studio archive` keeps a master with its colophon.
- **Instructions by job.** SKILL.md is a router with a reading list per job. Each rule has one home:
  gates, reviews, ownership, audio, commands, a kit map, and `taste/` for the look, text on screen,
  motion and delight, and the narration. The editor reviewer looks for narration that repeats the
  picture and for lines that sound written by a model. This file took DESIGN.md's release history.

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


## Polish by default and long runs (0.9.0)

One long session (six builder runs, about 14 hours) made a video the user judged very polished, but
the kit did not make the polish: the builders invented a beat sheet, a motion rig, staged passes,
motion reviews on frame sequences and a measured mix, and hit about twenty kit gaps on the way. Two
failures cost hours: a polish loop with no end and a builder that ran out of context with no
handoff. 0.9.0 makes that method the default for every explainer, in a neutral style, with comic
technique kept in one reference read only on request, and adds stopping rules and handoffs so long
passes end on time and survive a restart.

- **One writer for the timeline.** Seven commands edited timeline.json in place, and a re-narration
  rebuilt it keeping only the hand cues, so it dropped the effects track, the beat grid and any music
  bed. Each command now owns one source file (narrate the timings, align the words, sfx its cues, the
  builder `cues.json` and `audio/tracks.json`) and `timeline.build` composes the file from them; words
  aligned against an earlier narration are ignored rather than misplaced.
- **The finish is on the master.** It ran on the narration file alone, so an effect or a music hit
  over the voice could take the published sound past the -1.5 dBTP ceiling, and the effects, rendered
  once, stayed at their old times after a re-narration. The mix is now staged (sources, a chain per
  role, the bus, the master): effects render at mix time against the current timeline, and the fixed
  gain and the limiter run on the whole mix. AAC then overshoots the finished peak (0.1 dB at 160
  kbps, up to 1.5 dB for the web copy's low-bitrate mono), so every encode is measured and made
  quieter until it is under the ceiling too.
- **One frame sampler.** The cut's stills, the checks' samples and the sheets' strips each chose
  their frames in their own code, with the 0.15 s before a sentence's end written three times.
  `moments.py` now chooses them all, as moments with a clip time, a video time and a kind, so
  stills at beat events or in a pause, or a frame sequence for a beat window, is one function that
  every consumer can use. The change was proved against the old samplers on a fixture timeline.
- **A frame review goes stale on what its reviewer saw.** Its revision hashed timeline.json's
  bytes, and since the timeline became a build product it also changes for sources, the audio track
  and effects, so a sound edit staled a frame review. The revision now hashes the bundle's Script
  and Evidence, data/ and each chapter's clip key, which already covers the narration, captions,
  cues, scene code and layout a frame shows. Review kinds (script, frames, and later motion) declare their roles,
  revision scope, verdict line, round cap and freshness rule in one registry, `reviews.py`.
  Upgrading changes every frame revision once: existing frame receipts (waived and unavailable
  ones included) and every cut's `source_revision` stop matching, so a video that requires a frame
  review needs a fresh cut and a new review or waiver.
- **Captions wrap balanced, at every format's width.** The greedy wrap filled a line and left a word
  or two alone below it, and a chunk sized for 16:9 wrapped to three lines in 9:16. `wrap` now takes
  the fewest lines that hold the text and the most even of those, and ends a line on an article,
  short preposition or conjunction, or leaves a word alone, only when nothing else fits. Every
  format shares the chunks, so `split_phrases` sizes them to two lines at the narrowest width; 16:9
  chunks are shorter for it, and every caption, so every clip key, changes once on upgrade.
- **A stale frame review is recorded, not refused.** `review-frames` refused a cut older than the
  sources, so a review that came back after a small edit was lost. The frames kind's freshness is
  now "record-stale": a bundle carries its cut's revision, a result is checked against its
  manifest, and the receipt records the cut, that it is stale and which chapters changed since
  (cuts keep their review keys). Publish still needs the current revision, and says what changed.
- **Review rounds count per revision of the script.** The cap compared the typed round number with
  `max_rounds` across the whole video, so a structural rewrite began near the cap, and one build
  raised it from 3 to 17. A round is now a script revision reviewed since the latest structural
  stage mark (logged in research/reviews/rounds.jsonl); ROUND only names the files.
- **A background stage stops at twice its own budget.** One long session (six builder runs, about
  14 hours) had a polish stage alone run over five hours unattended, because every budget was
  advisory and nobody was watching. In background mode, a stage with its own budget in video.json
  now stops at twice it: the mark prints STOP, and `studio stage VIDEO --check`, run between
  chapters, exits 3. The builder writes a handoff and reports, and the main session decides
  whether to raise the budget. The scopes' defaults (20 and 5 minutes) were never calibrated
  against real builds, so they stay advisory, and so does everything in interactive mode, where
  the user is watching.
- **A restart reads a handoff, not a transcript.** In the same session, a builder that ran out of
  context was resumed from notes it happened to write. `studio handoff` assembles
  research/handoff.md from the files (owner, stage against budget, last cut and open notes,
  reviews in flight, requests, the next commands they imply) and adds the builder's own notes.
  `lock acquire --recover` rebuilds the state from the files and keeps only the stored notes: a
  stored brief once told the next builder to obey a stop the main session had already lifted.
  Background builders write one at every stage boundary; chapter fixers report to the owner
  instead, since they share its token and would overwrite each other's. The brief is committed,
  so it names paths relative to the video and no host.
- **Scratch lives in the video, and scripts run through the kit.** That session's key helper
  scripts lived in /tmp, outside the video and its history, and builders put "claude" in a
  script's path to get it past the macOS sandbox. Scratch now goes in `.studio/work/`, which
  survives a restart but stays out of Git and forks; a helper the build depends on moves to
  `sims/`. `studio run` runs either through the allowlisted `bin/studio`, with the kit's Python
  and that kit's own `studio` first on PATH, so a pinned video's script calls the pinned kit.
- **Stills wait their turn.** Parallel chapter fixers rendering stills hit the operation lock,
  which refuses at once. Stills can't skip it: Remotion bundles into `.cache/bundle` and deletes
  other bundles there, and Motion Canvas transcodes footage into `.cache/mc-footage`. So `still`,
  `boxes` and `duration` wait up to two minutes for it instead.
- **doctor starts the browser the way a cut does.** It launched Chrome with `--dump-dom`, which a
  sandbox can allow while refusing the engine's own launch. It now renders a one-frame still
  through the live engine in a throwaway video.
- **cues.json is a beat sheet.** One builder session wrote its own: named events anchored to a
  sentence's start or end or to a word, with picture and sound both timed from them. That put all
  93 sound contacts within a frame of their visual contact, the largest single quality gain of the
  session, and it hand-added 74 stills, because the kit's fell only near sentence ends. A cue may now
  be an anchor (`sentence`, `at`, `word`, `phrase`, `offset`) that a phrase finds again after a
  renumbering and that stops the build, naming the cue, when its words are gone. Every cue lands on
  the frame grid by the engines' half-up rule, so a scene's `cue()` and an effect on it start on the
  same frame, and every cut has a still two frames after each event and one in each long pause.
- **A hold after every move, measured on the pixels.** Moves that follow each other with no rest
  read as one blur, and nothing checked for it. `pacing` samples each chapter's stage at 10 frames a
  second from the cut's own rendered clips (0.2 s a chapter; rendering stills instead costs about
  0.7 s a second of video, so that is opt-in), finds the significant moves, and warns at a hold
  under 0.5 s. Its thresholds were set so the kit's live and Remotion templates pass; it warns
  rather than fails until real builds calibrate it.
- **Motion is reviewed on frame sequences.** In a long session, motion reviews on frame sequences
  were the builders' main polish tool, and stills near a sentence's end could not see a contact or
  a pop. `studio review-motion` packages a strip of consecutive frames (about 15 a second) around
  every event of the cut's beat sheet, the contact fourth so anticipation and settle show, and over
  every significant move no event covers, each with the narration and the effects cued in it. The
  frames are cut from the cut's own renders, so the bundle carries that cut's revision, and a
  result for an older cut is recorded as stale, as a frame review's is. Polish became a planned
  stage of the explainer (Stage 11), after the blocking and before the frame review, with the
  motion review as its gate; publish requires it for explainers built in background mode; in
  interactive mode the user watches every cut on the desk, so a gate would only repeat them.
- **A motion review stops by a rule.** The same session's review loop ran for hours with no natural
  end: should-fix findings plateaued at 25 to 45 a review. A motion review now ends at a round with
  no must-fix findings or after `motion_rounds` (default 2) rounds, whichever comes first, and the
  rest is recorded on the cut as known issues that later cuts carry and the desk shows. Rounds count
  per cut lineage: each cut reviewed is a round (counting revisions let a re-cut of unchanged
  sources roll the reviewer again), and the count starts again only at a structural mark over a
  substantially changed picture (a new chapter, or half the chapters or more), as a script mark
  needs a changed script; per script revision, a one-word fix would buy two more rounds. An ended
  review stands while its lineage does, so frame-review fixes don't reopen it, and stops standing
  when its cut predates such a mark or the picture changed that much since (the first version
  compared the import time with the mark, so a result for the old picture could stand for the new).
  A round with must-fix findings at the cap is reported as open, never passed.
- **A reviewer's findings are read from a block, and the status from the findings.** An independent
  review of the first version found that common formats made false findings: a counts line such as
  `MUST FIX: 0 · SHOULD FIX: 1`, or last round's list echoed with "fixed", became a must-fix that
  stopped publish, while a table or heading-grouped list read as nothing, so known issues were lost.
  The prompt now asks for a fenced `findings` block and a separate `regressions` block; without
  them the parser skips counts lines and the regression check and reads tables, headings,
  checkboxes and unicode hyphens. The status follows the findings, a FIX with none readable is
  refused, and a bundle takes one result. Each window's sheet labels its frames, outlines the
  contact and runs across a cut between chapters, and the cut keeps its effect times and layout, so
  an older cut is not judged against newer sound.
- **The mix is one room with the voice in front.** In one long session the builders wrote their own
  mixer: every track in one shared room (a send reverb), the presence band of effects and music cut
  under speech, the bed ducked under speech, the whole mix finished to a loudness target under a
  true-peak limiter. The kit's bus now does the same, in per-role sub-buses so the narration can key
  the processing: effects and music get a few early reflections (aecho, delays off any common
  multiple so they don't comb on one pitch), a 1-4 kHz dip of about 3 dB while the narration speaks,
  and music ducks 8 to 9 dB (`sidechaincompress`, 2:1, 20 ms attack, 500 ms release), with the key
  brought to a fixed loudness so the thresholds hold at any voice level. The dip is the band
  subtracted and its compressed copy added back, so a pause keeps the dry signal: a static EQ dip
  would thin every effect in its pause, where effects belong, and ffmpeg's crossover filter hung
  in front of a sidechain. Every sub-bus, the key among them, is padded to the video's length: a
  sidechain stops where its key does, and after a narration shorter than the video the ducked music
  went silent and the effects lost their whole presence band (found by an end-to-end test). A
  narration alone, or with footage, is the plain sum it always was.
- **Sound is measured, and the user listens once.** The same builders wrote an audio checker: sync
  against the beat sheet, ducking, per-word masking in 1-4 kHz, loudness, and a guard that failed a
  loud effect over a spoken word. `studio audio-check` measures these on stems the kit renders
  itself (one role's sub-bus as in the mix, at the master's level), so nothing is unmixed; the
  pauses guard runs in `studio check`, so publish stops on it. Taste stays the user's: a listening
  receipt in the reviews registry, bound to the soundtrack's stamp, that publish asks for (a
  warning) when there are effects or music.
- **More voices, and a bed only on request.** Four effect voices sent builders to their own synths;
  the kit has 24 neutral ones now, each a deterministic numpy synth with a line on what it is for,
  and a build (riser, swell) ends on its cue. `studio music --bed` generates a quiet pad and pulse
  that registers as music, so it ducks, and writes its beat grid. The plain default stays no music.

| Still open | Done when |
|---|---|
| **Live parity for code explainers**: CodePanel, Terminal and the other code components are Remotion-only | a code explainer is built on the live engine |
| **Desk on other machines**: the desk binds to 127.0.0.1 | a phone or second machine can follow a build safely |
- **Comic is a tone, asked for, not a default.** The same session's video was comic, and much of its
  craft (gags acting out the sentence, double takes, impact frames, layered sound) would be wrong in
  a calm explainer. `tone: comic` in video.json is set only when the user asks for a comic, cartoon
  or silly video, and only then is `references/styles/comic.md` read; "fun", "delightful" or
  "engaging" ask for the plain polish done well. Two evals hold that line.

## Sound, delivery and colour (0.10.0)

One long session's builders and a public "sound layer" both found the synthesised beeps the weakest
part of the soundtrack, so studio gains recorded CC0 sounds, each placed on its cue by its transient.
Measurements of three reference explainers (3Blue1Brown, Kurzgesagt, Sebastian Lague) then showed a
flat voice and an unchecked colour legend as the next gaps.

- **One resolver, one placement.** An effect's sound was a synth's name, read straight from the
  voice table, and the render, the cut's snapshot, the motion review and audio-check's sync each
  worked out its time. Now `sfx.resolve` makes any cue's sound (its optional `sound` id, else its
  type) into one record: samples, rate, the contact sample where the cue lands, where that is (start,
  end for a build, peak for a recording) and a digest; the synths are its first provider. `sfx.place`
  puts every cue on a timeline once, and all four read it. The track's cache key is the placements'
  digests, times and gains, so an edit elsewhere in the kit no longer re-renders every video's
  effects.
- **Recordings are pinned, verified and copied in.** A public tool we studied fetched hundreds of
  unpinned URLs with no checksums. The sound kit's manifest (`soundkit.json`, beside the kit's
  modules, so `studio init` pins it) names each pack's URL, sha256, size, licence (CC0 only) and
  creator. `studio doctor --fetch --sounds` downloads each once into `$STUDIO_HOME/cache/sounds/`:
  one cache for every video and pinned kit, outside the plugin folder an update replaces, and named
  by digest, so two kits' manifests coexist. A mismatch deletes the download and names both
  digests; only whitelisted members are unpacked, and an archive with an absolute path, a `..` or
  a link is refused whole. A video never reads the cache: `studio asset library` copies a sound
  from the verified zip into `assets/sounds/` with a provenance row (pack, member, licence,
  creator, sha256), so it renders without the cache and its page credits the packs. Git leaves the
  sound out, and `studio asset restore` copies it back by its recorded digest.
- **Picture motion is measured once.** The pacing check and the motion review sampled a rendered
  stage ten times a second, and audio-check's sync decoded the cut's frames with its own ffmpeg
  pipeline, threshold and edge logic. The sound tags coming next (`cut`, `move`, `land`, `appear`)
  are judged against the picture frame by frame, so `motion.frame_signal` reads a window of a
  rendered file at its own frame rate, from frame `first` exactly (a seek half a frame early),
  through the same decoder and change measure as the sampled signal, and adds the share of the stage
  that changed. Its helpers are the tags' vocabulary: where motion starts and ends, the frame of peak
  speed, and cuts. A cut is a one-frame spike: at least 60% of the stage changes into a frame and less
  into the frames either side. The kit's own fades and wipes change at most 48% of the stage a frame
  on 109 rendered clips, but a flat full-stage fade, a flash or a fast pan changes all of it frame
  after frame, and read as runs of cuts until the spike became the rule; a run of full-frame change
  is motion, and so is a cut between two scenes on one background. Where motion starts and ends also
  counts a frame where a small element visibly changes (0.05% of the stage over the window's
  median), so a 40 px label fading in has a start.
  The sampled signal keeps ffmpeg's fps filter, which picks a frame from within each tenth of a
  second (at 30 fps the second of three, not the first), so the pacing check and the motion review
  report what they did.
- **A recording lands on its peak.** A recorded effect has a lead-in, so starting its file on the
  cue puts the sound late by its attack (up to 180 ms in the kit's whooshes). `sound: "kit:ID"`
  resolves to a Sound that lands at its transient peak: the first local peak of a 2 ms RMS
  envelope within 6 dB of the loudest, so an attack wins over a louder ring unless the ring is
  much louder, and a build lands on its loudest moment. It is measured once, from the audio decoded
  to 48 kHz mono, and kept in the manifest's facts with the length, so placing needs neither the
  file nor numpy and the digest holds the file's sha256. audio-check's sync times a recording the
  same way; on a Kokoro-narrated test video a whoosh read 3 frames early by its onset and 0.2 by its
  peak. `studio sfx` copies each named recording into `assets/sounds/`, and a render reads only
  that copy. Recordings are opt-in per cue: a type alone keeps its synth voice, `"sound": "kit"`
  plays the type's default, and there is no video.json switch, because audio/sfx.json then says on
  its own what each effect plays, and one setting does not silently move every effect's file and
  timing.
- **Curated by measurement, not by ear.** No one could listen, so 174 of the five packs' 386 sounds
  were mapped to types by their file names and measured (length, peak, lead-in, attack, tail,
  centroid, floor, events); 22 were rejected (10 clipped, 12 with several events, 4 with long
  silence, some for two reasons) and 152 kept across 28 types, adding question, page-turn, stack,
  dice and toggle; swell has none and stays a synth. Each type's default has a crisp attack and is
  nearest its synth voice in brightness and length. A test re-measures every sound from a fetched
  kit against the committed facts.
- **Every effect heard.** The "sound layer" we studied checked each effect's audibility but passed
  one at -60 dBFS in a silent pause. audio-check's `audible` row measures each effect in a window
  around its contact: masked when it lifts the narration and music by under 6 dB, wideband and an
  octave either side of its centroid, and too quiet when its loudest 10 ms is more than 30 dB under
  the voice's level. On fixtures a pop in a pause passes (over silence, 1 dB under the voice), the
  same pop under an unducked pink-noise bed warns (a 0.8 dB lift), and one at -60 dBFS in silence
  warns (45 dB under the voice).
- **Tags say what the picture does, never when.** A cue's `visual` (`cut`, `move`, `land`, `appear`)
  is judged on the cut's frame signal and reported in frames, as a warning only: the beat sheet stays
  the one source of timing. On the test video a whoosh tagged `move` but placed on a slide's first
  frame read 10 frames early, which is the kind of thing an ear catches and a frame count can too. A
  cut between two scenes on one background changes too little to read as a cut, so `cut` also
  accepts a change exactly at a clip seam. Reading the cut frame by frame exposed a decoder bug: with
  an audio track, two seeks in three returned the frame before (fixed with `-fps_mode passthrough`).
  A miss reports where the mark really is, up to a second away, and the picture is read at the frame
  the cut's own timeline put the event on, saying so when the sources have moved it since.
- **Recordings at their synth's level.** Kenney's sounds are mastered near -1 dBFS, so a kit confirm
  at gain 0 came out 12.9 dB over the voice. Each kit sound's `trim_db` (from -15.9 to +8.7 dB) brings
  its K-weighted loudest 10 ms to its synth voice's, and it is in the digest. The mix set effects at a
  fixed -8 dB and the finish raised everything to its target, so a voice synthesised 8 dB quieter made
  every effect 8 dB louder against it; the effects track now follows the narration's integrated
  loudness against Kokoro's -25.6 LUFS, and the `loud` row compares an effect's K-weighted loudest
  10 ms with the voice's integrated loudness. Against that fixed relation the synth voices at gain 0
  sit from -3.5 dB (key-tick) to +12.2 dB (thump), so the line is 13.5 dB: every default passes at any
  narration level, and +10 dB warns from confirm (+5) up. A first version compared with the voice's
  99th-percentile 10 ms level, which moved with the voice's dynamics and left the thump 1.2 dB from
  the line. With no narration the effects are measured against the music.
- **A sheet to look at, timecodes to listen at.** The kit cannot hear, so audio-check draws the
  soundtrack (waveform, spectrogram, sentence bands, one marker per effect, red where a row flagged
  it; close-ups of the hero effects with the frame grid) with ffmpeg alone, and each motion-review
  window with effects gets its own. It then picks about five moments for the user's one listen, each
  with its reason, kept with the soundtrack's stamp so publish, the handoff and the listen receipt
  name them only for that mix.
- **Consistent narration (revised after 0.11.0).** The 0.10.0 experiment varied pauses and
  Kokoro speed by sentence role and first vocabulary use, calibrated against reference explainers.
  Listening to actual videos found it unnatural. It is removed, together with the warnings that
  encouraged varied delivery. One configured voice and speed now runs throughout; paragraph
  punctuation, explicit holds and chapter spacing remain. Old role markers and variation settings
  are accepted without changing speech, so existing scripts remain usable. Re-narration can move
  timing, while existing audio and pinned kits are untouched. The sentence-splitter fixes for
  common abbreviations and the sentence audio cache remain.
- **One colour, one meaning, checked.** All three references keep one colour legend for the whole
  video, and a colour used for two things was the most common frame-review finding. The check needed
  a machine-readable record of what a colour means, so a video declares `legend` in video.json,
  elements carry `means` (or the meaning's words in their name), and the engines' boxes report each
  element's resolved fill and stroke. It warns rather than fails, because tags and names are
  heuristic; neutrals, blends mid-transition and tints never count, so a fade or a guide dimmed
  below half opacity is not a misuse. The kit tags its own accent states, so a legend that follows
  style.md passes the kit's components; editing the legend re-keys live clips, and elements below
  half opacity are not counted.

## 3D inside the live engine (0.11.0)

The user asked for 3D that sits coherently next to the 2D explainers rather than as a gimmick. A spike
(a 20 s narrated chapter: a hard-disk platter drawn flat, tilted into a stack of four, the arm landing
on one cue, the cylinder lighting, back to flat) settled the shape before anything was built.

- **3D earns its place by a sentence.** "The viewer needs to see ___, and the flat diagram hides it."
  The spike's subject passed: "cylinder" means nothing until the stack is seen. Most of what studio
  explains (code, flows, maps, tables) fails it, and stays 2D. The test is in style.md.
- **One engine, one timeline: a stage under the SVG, not a second engine.** A separate 3D engine
  would rebuild the lifecycle, boxes, look sheet, desk and cache, and one engine per video would
  stop a chapter moving between flat and 3D, which is the point. The live engine gained `c.G`, an
  immediate-mode three.js stage built like the SVG one (keyed nodes, all state from `t`, undrawn
  nodes hidden), on a canvas under the SVG made the first time a scene asks for it; a 2D video
  never makes a WebGL context. To make room for it the page now paints the background, which the
  SVG stage drew as a full-frame rect; every 2D frame is the same as before.
- **The flat diagram is the model seen from above.** Camera maths live in `shared/camera3d.js`
  (shots `{target, az, el, span, fov}`, keyed as the 2D camera is), and the 3D stage loads its
  matrices as they are, so SVG projected through the same numbers lands on WebGL's pixels.
  `c.flatShot()` makes world `(x, 0, z)` the stage's pixel `(x, z)`: the hand-over between an SVG
  diagram and its model measured 0.23 grey levels of mean difference, all antialiasing, once faces
  sat a little behind their own outlines (a face had been winning the depth test against the line on
  its edge, halving the rim). A diorama with the diagram painted onto a surface was considered and
  left out: an SVG texture is asynchronous to make, blurs up close, and hides its text from the checks.
- **No lights.** Faces take three tones of their palette colour from one fixed house light, so a lit
  face shows the legend colour exactly (11,056 pixels of exactly `#8FD3FF` in a 3D frame) and a
  washed-out grade can't happen. Shadows, bloom and depth of field cost 214, 292 and 667 ms a frame on
  the CPU renderer against 156 for the house look, and none of them explains anything.
- **CPU WebGL by default, the GPU on request, and the backend in the keys.** Studio's renderer runs
  Chrome with `--disable-gpu`, which gives WebGL 2 on SwiftShader: 599 of 599 frames identical across
  runs and render orders, at 156 ms a 3D frame against 45 for 2D. On Metal a 3D frame costs what a 2D
  one does and is just as repeatable, but no frame matched the CPU's, 2D ones included (the GPU
  rasterises SVG differently too). The spike reused a GPU-rendered clip for a CPU cut because the
  backend wasn't in the key; now `render.engine_inputs` hashes the live engine's page and CLI, the
  video's `gl` and the browser for both the clip keys and the look sheet's key (which hadn't hashed
  the lock file either).
- **The checks see 3D.** Named 3D nodes are reported like SVG ones, with projected bounds, colours,
  meaning and `camera` while the shot moves, so `bounds`, `band`, `inframe` and `legend` work unchanged.
  They also report `visible`, from object masks made only for boxes. The spike's first layout had seven
  of eight heads invisible under "every head lands": a frame review might miss that, a measurement
  doesn't. `occluded` warns at a sentence's samples and at each event; the name match learned that "head
  2" is one of the heads a sentence names.
- **Labels stay SVG**, on points projected from the model: upright, legible and read by every text
  check. SDF text in 3D was left out.
- **The desk reloads a fresh page when a module changes.** It re-imported chapter files in place, but a
  browser keeps an imported module by URL, so an edited helper (or the engine) showed stale. It now
  watches two groups and reloads the page for the second; it also serves video.json, so the legend on
  the desk is the render's. Scenes import the engine as `@studio/`: an absolute `/engine/` import, as
  `kit.js` once suggested, worked in the renderer and failed on the desk.
- **Sound needs no new clock.** audio-check judged the landing's `land` tag on the 3D picture and was
  right twice: once when an in-out ease crept into the stop (3 frames early), once when the tap sat on
  the word it illustrated.

| Still open | Done when |
|---|---|
| **A second 3D subject** of another shape (a molecule, an orbit) | built and checked without kit changes |
| **SwiftShader on another CPU** | a frame compared between Apple silicon and x86 |
| **Pacing reads a settle as a new move**, and motion-review strips are too small for small 3D parts | pacing treats a settle from the contact frame as part of the landing; a window crops to the named element |
