---
name: studio
description: >
  Make, revise and publish narrated, animated videos with an agent-driven studio: an explained
  topic from research or from a repo or knowledge base the user points at, a narrative settled
  with the user, a script checked by fresh-context reviewers when the user can't judge it, real
  evidence, scenes written as code on one timeline (Remotion), cuts reviewed on a local page where
  the user leaves notes, and a published page. Use whenever the user asks for a video, an explainer,
  a video lesson, "teach me X" as a video, or "make a video of this repo"; wants to see or give
  notes on a cut; wants a video revised, re-voiced, re-rendered or republished; or asks about the
  studio's setup. NOT for a plain chat explanation, a slide deck, a single diagram, or a document.
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
| **Drive** | `author`: the user knows the subject (they may want it for others) · `learner`: the user is learning it and has to trust you | Author: the user's notes are the review, so no reviewer rounds by default. Learner: fresh-context research, competing narratives, reviewers, evidence, risk flags. Read `references/propose.md` |
| **Genre** | `explainer` | Only explainers are supported so far: `references/explainer.md`. Motion graphics, launch videos, pixel art and footage editing are designed (`DESIGN.md`) but not built; say so rather than improvising one |
| **Destination** | `private-page` (default) · `share` · `files` | Where it goes: `references/publishing.md` |

Ask one plain question for the drive ("Do you know this well, or are you learning it?").
Economy mode (`"economy": true` in video.json) is for a short budget: one agent, at most two
review rounds, one frame review.

## Modes

| Mode | When | What you do |
|---|---|---|
| **setup** | first use on a machine, or a command fails with an environment error | `bin/studio doctor` (add `--fetch`, and `--extra kokoro` for local narration, `--extra align` for the voice check). It prints the fix for each failure |
| **propose** | a new video | `studio new NAME [--source REPO] [--drive …]`, then `references/propose.md`. Ends with an approved `research/narrative.md`. When the video explains a repo or knowledge base, that folder is the primary source: explore it first (delegate wide reads), and cite files in the Evidence table |
| **build** | the narrative is approved | Author drive: build it yourself, in the open, per `references/explainer.md`, showing stills before animation. Learner drive: spawn one background agent with `prompts/build_agent.md` (the context that shaped the narrative is what the script reviewers must not see), and relay its report |
| **loop** | a cut exists | `references/publishing.md`, "The review loop": serve the cut, wait for a round, answer it with the next cut |
| **publish** | the user locks the video | `studio publish VIDEO`, then the Artifact tool (`references/publishing.md`) |
| **revise** | notes on the published page, or in chat | `references/publishing.md`, "Revising from notes" |
| **revoice** | a voice or timing change | edit `narration.json`, `studio narrate`, `studio voice-check`, `studio cut`, check the stills, republish |
| **status** | "where did it get to" | SCRIPT.md's status line, `research/reviews/`, `cuts/`, `review/notes.jsonl`; report the last completed stage and resume |

## Commands

Everything runs through `bin/studio` (it enters its own pinned environment; no shell setup):

| Command | Does |
|---|---|
| `studio doctor [--fetch] [--extra kokoro\|align\|audio] [--net]` | Checks every layer of the environment and prints fixes |
| `studio new NAME [--dir D] [--title T] [--drive author\|learner] [--source REPO]` | A video folder (default `$STUDIO_HOME/NAME`, STUDIO_HOME defaults to `~/studio`) |
| `studio narrate VIDEO [--estimate] [--plan] [--list] [--fetch-only] [--yes]` | Narration from SCRIPT.md into `audio/` and the timeline (with word timings). `--estimate`: timings from word counts, no audio, so scenes can be built before the voice |
| `studio voice-check VIDEO` | Transcribes every sentence and scores it; the audio review, since you can't listen |
| `studio review VIDEO ROUND [--narrative FILE]` | One round of fresh-context reviewers (expert, student, editor) |
| `studio cut VIDEO [--stills-only] [--changelog FILE] [--quality final]` | The next cut: stills first, then only changed clips, then the composite |
| `studio serve VIDEO` · `studio notes VIDEO` | The review page (http://127.0.0.1:8765/) · the notes on a cut, numbered |
| `studio still VIDEO CLIP T --out PNG` · `studio boxes VIDEO CLIP T` | One frame (about 1.6 s after an edit) · pixel boxes of named elements |
| `studio determinism VIDEO` · `studio align VIDEO` | Same frame twice gives the same hash · word timings by speech recognition |
| `studio publish VIDEO` | Final cut, web encode, poster, and `out/page/` |
| `studio import-tutor LESSON VIDEO` | A timeline from a lesson made with the old tutor plugin |

## The video folder

```
VIDEO/
  video.json        title, version, genre, drive, destination, engine, poster, source, learner, economy
  SCRIPT.md         Argument · Chain · Format · Ledgers · Script · Evidence · Review log
  narration.json    engine, voice, holds, spoken respellings
  research/         research reports, narrative.md, reviews/, frame_review/, annotations_vN.txt
  sims/  data/      every run behind every number on screen
  scenes/           index.ts + s1.tsx … (one component per chapter) + shared files
  timeline.json     written by narrate: scene, narration (with words), captions, audio tracks
  layout.json       canvas, fps, caption band
  audio/            narration.mp3 (+ .wav, not committed), elevenlabs_cache/, voice_check.txt
  cuts/cutN/        video.mp4, stills/, before/, cut.json
  review/           notes.jsonl
  out/              web.mp4, page/
```

## Gates you don't skip

- **The narrative** is approved by the user before any script (author: they approve it; learner: after reviewers, with risk flags).
- **The look**: a stills-only cut, and the user's pick, before scenes are animated.
- **Script lock** (learner drive): expert PASS + editor PASS + the student's retelling answers the opening question. Rules in `references/explainer.md`.
- **Voice check** before the first animated cut: read what was heard for every sentence under 0.8.
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
- `prompts/build_agent.md`, `prompts/frame_review.md`, `prompts/reviewers/`: prompts for fresh contexts.
- `DESIGN.md`: why the studio is shaped this way, and what is designed but not built.
