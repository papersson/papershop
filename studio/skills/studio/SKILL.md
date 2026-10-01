---
name: studio
description: >
  Make, revise and publish videos with an agent-driven studio: narrated explainers (from research or
  from a repo or knowledge base the user points at), motion-graphics pieces and showreels, product
  and launch films, pixel art, and edits of the user's own recordings by their transcript. Scenes are
  code on one timeline (Remotion); cuts are reviewed on a local page where the user leaves notes
  against the exact sentence on screen; formats (16:9, 9:16, 1:1) come from the same scenes. For an
  explainer the narrative is settled with the user first, and a script is checked by fresh-context
  reviewers when the user can't judge it. Use whenever the user asks for a video, an explainer, a
  video lesson, "teach me X" as a video, a motion or launch video, pixel art, or to cut or caption a
  recording; wants to see or give notes on a cut; wants a video revised, re-voiced, re-rendered,
  exported or republished; or asks about the studio's setup. NOT for a plain chat explanation, a
  slide deck, a still image, or a document.
---

# studio

You make one video and improve it in rounds. The user never runs the tools. They approve a
narrative, pick a look from stills, then watch cuts on a review page and leave notes, and you
answer each round with the next cut. Two things decide the result:

1. **The narrative is the bottleneck.** A polished video of the wrong argument is worthless, so
   it is settled with the user before any script exists, and the build treats it as fixed.
2. **The loop is the product.** Speed from note to visible change is what makes iteration work:
   render only what changed, answer picture notes with stills first, and keep final quality for
   the end. Every step is incremental and says what it reused: a narration edit re-renders only
   the chapter it is in (later chapters move by whole frames and stay cached), and stills, label
   crops, the voice check, the soundtrack and the audio finish redo only what changed. Run the
   whole-video passes (`voice-check --all`, a full frame review) once, before the first publish.
3. **Wall-clock time is a cost the user feels.** A first cut in about an hour, a revision round in
   about ten minutes (video.json `budget`). The slow builds were loops nobody timed: three
   competing narratives, six script review rounds, polish passes repeated until perfect. So the
   user approves the narrative (minutes of their time beat an hour of reviewers), reviews are
   capped, independent work runs in parallel, a rough cut comes early, and every stage is marked
   with `studio stage` so time over budget is seen and cut, not discovered afterwards.

## Before anything: four choices

Ask, or infer from the request, and record them in `video.json`:

| Choice | Options | What it changes |
|---|---|---|
| **Drive** | `author`: the user knows the subject (they may want it for others) · `learner`: the user is learning it and has to trust you | Author: the user's notes are the review, so no reviewer rounds by default. Learner: fresh-context research, one narrative the user approves with its risk flags, capped script reviews, evidence. Read `references/propose.md`. Only explainers have a learner drive; the other genres are directed by the user |
| **Genre** | `explainer` · `motion` · `launch` · `pixel` · `footage` | The story structure, look defaults, engine and checks: `references/explainer.md` for a narrated explanation; `references/genres/<genre>.md` for the others. Ask which the user means if it isn't clear: "an explainer", "a motion reel", "a launch video for this product", "pixel art", "cut this recording" |
| **Destination** | `private-page` (default) · `share` · `social` · `files` | Where it goes: `references/publishing.md`. `social` exports 9:16, 1:1 and 16:9 at -14 LUFS |
| **Level** | `intro` (default) · `deep-dive` | How deep it goes: `references/levels.md`. Intro: an undergrad explainer, 3–4 big ideas, a toy example, two or three numbers, about five minutes, planned in one pass with a self-check instead of reviewer rounds, a first cut in about 20 minutes. Deep-dive: research, measured evidence on real data, reviewer rounds, a fresh frame review. Default to intro unless the user asks for depth; `studio new --level` |

Ask one plain question for the drive ("Do you know this well, or are you learning it?").
**Pace.** The default is fast: the user approves the narrative, script reviews stop at 3 rounds
(2, plus 1 for an expert's blocking finding), one craft-critique round, one frame review, and its
SHOULD FIX items that take a minute; the rest is logged as open. `"thorough": true` in video.json
restores competing narratives, 6 review rounds and 3 critique rounds, for a video that must be
right more than soon; use it only when the user asks. `"economy": true` is tighter still: one
agent, 2 review rounds. Mark each stage as it starts (`studio stage VIDEO research`, `narrative`,
`evidence`, `script`, `review`, `narration`, `scenes`, `cut`, `frame-review`, `publish`, and
`round` for each revision round); it prints the time against the budget, and over budget you
finish the stage with what is open logged and tell the user where the time went.

## Modes

| Mode | When | What you do |
|---|---|---|
| **setup** | first use on a machine, or a command fails with an environment error | `bin/studio doctor` (add `--fetch`, and `--extra kokoro` for local narration, `--extra align` for the voice check). It prints the fix for each failure |
| **propose** | a new video | `studio new NAME [--genre G] [--source REPO] [--drive …] [--level intro\|deep-dive] [--duration N]`. Explainer at the intro level: the big ideas and the toy example, approved by the user, then one-shot planning (`references/levels.md`). Explainer at the deep-dive level: `references/propose.md`, ending with an approved `research/narrative.md`; when the video explains a repo or knowledge base, that folder is the primary source: explore it first (delegate wide reads), and cite files in the Evidence table. Other genres: the brief in `references/genres/<genre>.md` (a state list, a storyboard, an edit list), shown as stills or a paper edit before building |
| **build** | the narrative or brief is approved | Explainer, author drive: build it yourself, in the open, per `references/explainer.md`, showing stills before animation. Explainer, learner drive: spawn one background agent with `prompts/build_agent.md` (the context that shaped the narrative is what the script reviewers must not see), and relay its report. Either way, once the shared scene helpers exist, write the chapters' scenes in parallel (subagents, a few chapters each, each owning its own `sN.tsx`). Other genres: build it yourself per its genre file |
| **loop** | a cut exists | `references/publishing.md`, "The review loop": serve the cut, wait for a round, answer it with the next cut |
| **publish** | the user locks the video | `studio publish VIDEO`, then the Artifact tool (`references/publishing.md`) |
| **revise** | notes on the published page, or in chat | `references/publishing.md`, "Revising from notes" |
| **revoice** | a voice or timing change | edit `narration.json`, `studio narrate`, `studio voice-check`, `studio cut`, check the stills, republish |
| **status** | "where did it get to" | `studio stage VIDEO --report` (time per stage), SCRIPT.md's status line, `research/reviews/`, `cuts/`, `review/notes.jsonl`; report the last completed stage and resume |

## Commands

Everything runs through `bin/studio` (it enters its own pinned environment; no shell setup):

| Command | Does |
|---|---|
| `studio doctor [--fetch] [--extra audio\|align\|kokoro] [--engine motion-canvas] [--net]` | Checks every layer of the environment and prints fixes |
| `studio new NAME [--genre G] [--engine remotion\|motion-canvas] [--dir D] [--title T] [--drive …] [--source REPO] [--duration N]` | A video folder (default `$STUDIO_HOME/NAME`, STUDIO_HOME defaults to `~/studio`). `--duration` starts a narration-less piece (motion, launch) |
| `studio narrate VIDEO [--estimate] [--plan] [--list] [--fetch-only] [--yes]` | Narration from SCRIPT.md into `audio/` and the timeline (with word timings). `--estimate`: timings from word counts, no audio, so scenes can be built before the voice |
| `studio voice-check VIDEO [--all]` · `studio align VIDEO` | Transcribes the sentences whose audio changed and scores every sentence (the audio review, since you can't listen); `--all` re-transcribes everything · word timings by speech recognition |
| `studio review VIDEO ROUND [--narrative FILE]` | One round of fresh-context reviewers (expert, student, editor) |
| `studio stage VIDEO NAME` · `studio stage VIDEO --report` | Mark a stage's start; prints the last stage's time and the total against video.json's `budget` · the time per stage |
| `studio cut VIDEO [--stills-only] [--changelog FILE] [--quality final]` | The next cut: stills first (unchanged frames reused), then only changed clips (on every core), then the composite; it prints what it rendered and what it reused |
| `studio serve VIDEO` · `studio notes VIDEO` | The review page (http://127.0.0.1:8765/) · the notes on a cut, numbered |
| `studio still VIDEO CLIP T --out PNG [--layers all\|no-captions\|no-band\|background]` · `studio boxes VIDEO CLIP T` | One frame (about 1.6 s after an edit) · pixel boxes of named elements |
| `studio check VIDEO [--all] [--samples N] [--only …] [--format F]` | Only chapters changed since they last passed (`--all`: every chapter; `studio publish` always runs the full check): length, determinism, bounds, band, contrast, legible, and by genre: grid and palette (pixel), dead and loop (motion), filler, cuts, levels, sync and segments (footage), provenance (assets). Run before a cut goes to the user |
| `studio sheets VIDEO OUTDIR [--strip CLIP T]` | Chapter contact sheets, a 360 px phone sheet, fast-action strips, and full-resolution label crops with measured sizes (what the frame review judges from; unchanged frames reuse their crops, a label repeated across a chapter is cropped once) |
| `studio audio VIDEO [--lufs -16] [--peak -1.5]` | The audio finish: 48 kHz, one fixed gain to the target loudness, a limiter for the peaks; run by `publish` |
| `studio export VIDEO [--formats 16:9,9:16,1:1] [--lufs -14]` | The whole video in several formats from one timeline, into `out/export/` |
| `studio publish VIDEO` | Final cut (changed chapters only), `out/master.mp4` (1080p), a web encode that fits the Artifact upload limit, poster, and `out/page/` |
| `studio clean VIDEO [--dry-run]` | Removes what can be regenerated: cuts beyond the newest 3 (`keep_cuts` in video.json; `studio cut` prunes these itself), narration chunks the script no longer uses, stale clip, web, still and crop caches, old bundles and sound mixes, out/sheets, out/web.mp4, audio/final.wav. Never the script, scenes, data, sims, research, narration.json, timeline.json, the narration audio, the ElevenLabs cache, the latest cut, out/master.mp4 or out/page. Prints the bytes freed |
| `studio capture URL VIDEO` · `studio asset add\|list VIDEO [FILE]` | A page screenshot into `assets/` · files added or listed, each with its source in `assets/provenance.json` |
| `studio beats VIDEO TRACK` · `studio sfx VIDEO CUES` · `studio sound-lab VIDEO` | A beat grid from music · synthesised effects on beat or cue names · a page to choose effects by ear |
| `studio ingest FILE VIDEO` · `studio edit VIDEO EDL` | A recording's transcript, shots and paper edit · the timeline from an edit list |
| `studio init VIDEO [--update]` | Pin the kit a video is made with, so a plugin update can't change how it renders |
| `studio import-tutor LESSON VIDEO` | A timeline from a lesson made with the retired tutor plugin |

## The video folder

```
VIDEO/
  video.json        title, version, genre, drive, destination, engine, poster, source, learner, budget, thorough, economy, loop, pixel
  SCRIPT.md         Argument · Chain · Format · Ledgers · Script · Evidence · Review log
  narration.json    engine, voice, holds, spoken respellings, phoneme overrides
  research/         research reports, narrative.md, reviews/, frame_review/, annotations_vN.txt
  sims/  data/      every run behind every number on screen
  scenes/           index.ts + s1.tsx … (one component per chapter) + shared files
  timeline.json     written by narrate: scene, narration (with words), captions, audio tracks
  layout.json       canvas, fps, caption band (formats add their own: 9:16, 1:1)
  assets/           captured, generated and supplied files, and provenance.json; served to scenes
  footage/          footage videos: words, shots and paper edit per recording
  audio/            narration.mp3 (+ .wav, not committed), elevenlabs_cache/, voice_check.txt
  cuts/cutN/        video.mp4, stills/, before/, cut.json
  review/           notes.jsonl
  out/              web.mp4, page/
```

## Gates you don't skip

- **The narrative** (at the intro level: the big ideas and the toy example) is approved by the user before any script, in both drives (learner: shown with its risk flags; it takes them minutes). Only when the user has said to go ahead without them does a narrative review round stand in for their approval.
- **The look**: a stills-only cut, and the user's pick, before scenes are animated.
- **Script lock** (learner drive, deep-dive; at the intro level the one-shot self-check in `references/levels.md` replaces it): expert PASS + editor PASS + the student's retelling answers the opening question, or the round cap (3 by default) with every open finding logged. Rules in `references/explainer.md`.
- **Pronunciation and voice check** before the first animated cut: every finding in
  `audio/pronunciation.txt` resolved (a phoneme, a respelling, or accepted as it is), then read what
  was heard for every sentence under 0.8.
- **Checks**: `studio check` passes before a cut goes to the user, and `studio sheets` and the craft critique (explainer.md Stage 8; motion.md for the scored loop) have been run on what changed.
- **Frame review** before publishing a deep-dive or a video going to other people (`prompts/frame_review.md`, fresh context); at the intro level, look at a handful of the cut's stills yourself instead. Verify each finding against a full-resolution still. The first publish reviews every chapter; a re-publish after a revision round reviews the chapters the round changed (the cut's `changed` list) and their neighbours.
- **Evidence**: a number on screen without a row in the Evidence table is a bug.

## Standing rules

- Commit per stage and per cut, so a stop (a spend limit, a lost session) loses at most one chapter. Never commit `.cache/` or `audio/*.wav`.
- Never put a model identifier string in a video, page, script or commit.
- Never bypass a permission check, and never route a blocked action through a subagent.
- Keep the kit unchanged during a video's work; if it can't do something, do it in the video's own files and report it.

## References

- `references/propose.md`: the narrative stage for both drives, and the narrative document.
- `references/explainer.md`: research, evidence, script, review, narration, look, scenes, cuts, frame review.
- `references/style.md`: what a finished video looks and sounds like, with the reasons.
- `references/publishing.md`: the review loop, the page, publishing, revising from notes, re-voicing.
- `references/engines.md`: Remotion and Motion Canvas (a video picks one in video.json; Remotion is the default).
- `references/genres/motion.md`, `launch.md`, `pixel.md`, `footage.md`: the other genres.
- `prompts/build_agent.md`, `prompts/frame_review.md`, `prompts/reviewers/`: prompts for fresh contexts.
- `DESIGN.md`: why the studio is shaped this way, and what is designed but not built.
