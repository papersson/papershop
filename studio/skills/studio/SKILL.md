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
   the end.

## Before anything: three choices

Ask, or infer from the request, and record them in `video.json`:

| Choice | Options | What it changes |
|---|---|---|
| **Drive** | `author`: the user knows the subject (they may want it for others) · `learner`: the user is learning it and has to trust you | Author: the user's notes are the review, so no reviewer rounds by default. Learner: fresh-context research, competing narratives, reviewers, evidence, risk flags. Read `references/propose.md`. Only explainers have a learner drive; the other genres are directed by the user |
| **Genre** | `explainer` · `motion` · `launch` · `pixel` · `footage` | The story structure, look defaults, engine and checks: `references/explainer.md` for a narrated explanation; `references/genres/<genre>.md` for the others. Ask which the user means if it isn't clear: "an explainer", "a motion reel", "a launch video for this product", "pixel art", "cut this recording" |
| **Destination** | `private-page` (default) · `share` · `social` · `files` | Where it goes: `references/publishing.md`. `social` exports 9:16, 1:1 and 16:9 at -14 LUFS |

Ask one plain question for the drive ("Do you know this well, or are you learning it?").
Economy mode (`"economy": true` in video.json) is for a short budget: one agent, at most two
review rounds, one frame review.

## Modes

| Mode | When | What you do |
|---|---|---|
| **setup** | first use on a machine, or a command fails with an environment error | `bin/studio doctor` (add `--fetch`, and `--extra kokoro` for local narration, `--extra align` for the voice check). It prints the fix for each failure |
| **propose** | a new video | `studio new NAME [--genre G] [--source REPO] [--drive …] [--duration N]`. Explainer: `references/propose.md`, ending with an approved `research/narrative.md`; when the video explains a repo or knowledge base, that folder is the primary source: explore it first (delegate wide reads), and cite files in the Evidence table. Other genres: the brief in `references/genres/<genre>.md` (a state list, a storyboard, an edit list), shown as stills or a paper edit before building |
| **build** | the narrative or brief is approved | Explainer, author drive: build it yourself, in the open, per `references/explainer.md`, showing stills before animation. Explainer, learner drive: spawn one background agent with `prompts/build_agent.md` (the context that shaped the narrative is what the script reviewers must not see), and relay its report. Other genres: build it yourself per its genre file |
| **loop** | a cut exists | `references/publishing.md`, "The review loop": serve the cut, wait for a round, answer it with the next cut |
| **publish** | the user locks the video | `studio publish VIDEO`, then the Artifact tool (`references/publishing.md`) |
| **revise** | notes on the published page, or in chat | `references/publishing.md`, "Revising from notes" |
| **revoice** | a voice or timing change | edit `narration.json`, `studio narrate`, `studio voice-check`, `studio cut`, check the stills, republish |
| **status** | "where did it get to" | SCRIPT.md's status line, `research/reviews/`, `cuts/`, `review/notes.jsonl`; report the last completed stage and resume |

## Commands

Everything runs through `bin/studio` (it enters its own pinned environment; no shell setup):

| Command | Does |
|---|---|
| `studio doctor [--fetch] [--extra audio\|align\|kokoro] [--engine motion-canvas] [--net]` | Checks every layer of the environment and prints fixes |
| `studio new NAME [--genre G] [--engine remotion\|motion-canvas] [--dir D] [--title T] [--drive …] [--source REPO] [--duration N]` | A video folder (default `$STUDIO_HOME/NAME`, STUDIO_HOME defaults to `~/studio`). `--duration` starts a narration-less piece (motion, launch) |
| `studio narrate VIDEO [--estimate] [--plan] [--list] [--fetch-only] [--yes]` | Narration from SCRIPT.md into `audio/` and the timeline (with word timings). `--estimate`: timings from word counts, no audio, so scenes can be built before the voice |
| `studio voice-check VIDEO` · `studio align VIDEO` | Transcribes every sentence and scores it (the audio review, since you can't listen) · word timings by speech recognition |
| `studio review VIDEO ROUND [--narrative FILE]` | One round of fresh-context reviewers (expert, student, editor) |
| `studio cut VIDEO [--stills-only] [--changelog FILE] [--quality final]` | The next cut: stills first, then only changed clips, then the composite |
| `studio serve VIDEO` · `studio notes VIDEO` | The review page (http://127.0.0.1:8765/) · the notes on a cut, numbered |
| `studio still VIDEO CLIP T --out PNG [--layers all\|no-captions\|no-band\|background]` · `studio boxes VIDEO CLIP T` | One frame (about 1.6 s after an edit) · pixel boxes of named elements |
| `studio check VIDEO [--samples N] [--only …] [--format F]` | length, determinism, bounds, band, contrast, legible, and by genre: grid and palette (pixel), dead and loop (motion), filler, cuts, levels, sync and segments (footage), provenance (assets). Run before a cut goes to the user |
| `studio sheets VIDEO OUTDIR [--strip CLIP T]` | Chapter contact sheets, a 360 px phone sheet, fast-action strips, and full-resolution label crops with measured sizes (what the frame review judges from) |
| `studio audio VIDEO [--lufs -16] [--peak -1.5]` | The audio finish: 48 kHz, one fixed gain to the target loudness, a limiter for the peaks; run by `publish` |
| `studio export VIDEO [--formats 16:9,9:16,1:1] [--lufs -14]` | The whole video in several formats from one timeline, into `out/export/` |
| `studio publish VIDEO` | Final cut, web encode, poster, and `out/page/` |
| `studio capture URL VIDEO` · `studio asset add\|list VIDEO [FILE]` | A page screenshot into `assets/` · files added or listed, each with its source in `assets/provenance.json` |
| `studio beats VIDEO TRACK` · `studio sfx VIDEO CUES` · `studio sound-lab VIDEO` | A beat grid from music · synthesised effects on beat or cue names · a page to choose effects by ear |
| `studio ingest FILE VIDEO` · `studio edit VIDEO EDL` | A recording's transcript, shots and paper edit · the timeline from an edit list |
| `studio init VIDEO [--update]` | Pin the kit a video is made with, so a plugin update can't change how it renders |
| `studio import-tutor LESSON VIDEO` | A timeline from a lesson made with the retired tutor plugin |

## The video folder

```
VIDEO/
  video.json        title, version, genre, drive, destination, engine, poster, source, learner, economy, loop, pixel
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

- **The narrative** is approved by the user before any script (author: they approve it; learner: after reviewers, with risk flags).
- **The look**: a stills-only cut, and the user's pick, before scenes are animated.
- **Script lock** (learner drive): expert PASS + editor PASS + the student's retelling answers the opening question. Rules in `references/explainer.md`.
- **Pronunciation and voice check** before the first animated cut: every finding in
  `audio/pronunciation.txt` resolved (a phoneme, a respelling, or accepted as it is), then read what
  was heard for every sentence under 0.8.
- **Checks**: `studio check` passes before a cut goes to the user, and `studio sheets` and the craft critique (explainer.md Stage 8; motion.md for the scored loop) have been run on what changed.
- **Frame review** before publishing (`prompts/frame_review.md`, fresh context). Verify each finding against a full-resolution still.
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
