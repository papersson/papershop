---
name: studio
description: >
  Make or revise a video with an agent-driven studio: scenes written as code on one timeline,
  rendered by an engine (Remotion first), shown to the user as a cut on a local review page where
  they leave notes, then revised and re-cut until they lock it. Use when the user wants a video
  made, rebuilt, re-cut or revised from notes, wants to see the current cut, or asks about the
  studio's environment. NOT for a still image, a slide deck, or a document.
---

# studio

You make one video and improve it in rounds. The user never runs the tools; they watch a cut on
the review page, leave notes, and you answer with the next cut. How fast a note turns into a
visible change is the measure of the whole setup, so render only what changed and show stills
before video.

This is phase 0 of the redesign (the timeline, the Remotion engine and the review loop). The
router that picks a genre, a driving mode and a destination comes later; until then every video
is an explainer driven by the user as author.

## Commands

Run everything through `bin/studio` (it enters the flake's pinned environment itself):

| Command | Does |
|---|---|
| `studio doctor [--fetch] [--extra align] [--net]` | Checks tools, the engine's packages and the browser, and prints the fix for each failure. `--fetch` installs the engine's packages and its headless shell. Run it first whenever a command fails with an environment error |
| `studio import-tutor LESSON VIDEO` | A video folder from a tutor lesson: its narration and sentence timings become the timeline |
| `studio align VIDEO` | Word timings (faster-whisper) and captions re-chunked from them |
| `studio still VIDEO CLIP T --out PNG [--layers all\|no-captions\|background]` | One frame, rendered alone (about 1.6 s after an edit) |
| `studio render VIDEO CLIP --out MP4 [--quality draft\|final]` | One clip as a silent video |
| `studio cut VIDEO [--stills-only] [--changelog FILE]` | The next cut: stills first, then only the clips whose key changed, then the composite with narration |
| `studio serve VIDEO` | The review page for the latest cut, at http://127.0.0.1:8765/ |
| `studio notes VIDEO [--cut N]` | The notes on a cut, numbered |
| `studio boxes VIDEO CLIP T` · `studio duration VIDEO CLIP` | Element boxes and a clip's length, from the engine |
| `studio determinism VIDEO` | Renders sample frames twice and compares hashes |
| `studio narrate VIDEO --plan` | Which paragraphs a re-narration would synthesise |

## The video folder

```
VIDEO/
  video.json      title, genre, drive, destination, engine, voice
  timeline.json   tracks: scene (one clip per chapter), narration (sentences, words), captions, audio
  layout.json     canvas, fps, the caption band
  scenes/         index.ts (clip id → component), <clip>.tsx per chapter, shared files
  audio/          narration
  cuts/cutN/      video.mp4, stills/, before/, cut.json
  review/         notes.jsonl, the review page's log
  .cache/         bundles, rendered clips, narration (never committed)
```

## The loop

1. `studio cut VIDEO`, then `studio serve VIDEO` in the background, and give the user the URL.
   A cut before any animation is `--stills-only`: agree on the look from stills first.
2. Watch `review/notes.jsonl` for a `"type": "round"` line: the user pressed Send round. Read the
   batch with `studio notes VIDEO`.
3. Map each note to its sentence and clip, group notes into themes, and say what you will change
   before changing it.
4. Answer picture notes with `studio still` first when a frame settles the question, then cut.
   Pass `--changelog` with one `{note, change}` per note, so the page shows what answered what.
5. Repeat until the user locks the video. Final quality (`--quality final`) is rendered once, at lock.

## Writing scenes (Remotion engine)

- A scene is a React component for one clip. Everything it draws derives from `useClip().t`:
  no timers, no state carried between frames, no unseeded randomness. `studio determinism` checks it.
- Time comes from the narration: `at('03')` is sentence 3 of this clip, `end('03', 0.5)` half a
  second after it ends, `word('03', 2)` its third word (after `studio align`). `Beats` sequences
  animations like a list of play() calls; `ramp`, `pulse` and `spring` are pure easing functions.
- Place things in stage units: origin at the centre, y up, 8 units tall, above the caption band.
  The band belongs to the captions track; nothing a scene draws may enter it.
- Name what matters (`name=` on `Txt` and `Rect`), so `studio boxes` can report it.

## Standing rules

- Commit per cut. Never commit `.cache/`.
- Never put a model identifier string in a video, page or commit.
- Keep the kit unchanged inside a video's work; if it can't do something, do it in the video's
  own files and report it.
