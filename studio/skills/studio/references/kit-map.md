# Where things live

Paths an agent otherwise guesses. The skill root is the folder holding `SKILL.md`; use absolute
paths from it (`SKILL_ROOT/bin/studio`, `SKILL_ROOT/references/…`).

## The skill

```
SKILL_ROOT/
  SKILL.md, DESIGN.md        the router and the rationale
  bin/studio                 the one entry point (enters the pinned environment, then the kit's CLI)
  references/                procedures: explainer, propose, gates, reviews, ownership, audio, desk,
                             publishing, setup, engines, code, pedagogy, levels, commands, this file;
                             genres/ for motion, launch, pixel, footage; taste/ for the look, text on
                             screen, motion and delight, the narration, and the comic tone
  prompts/                   prompts for fresh contexts: build_agent, frame_review, motion_review,
                             reviewers/ (expert, student, editor and their narrative versions)
  templates/                 what `studio new` copies: SCRIPT.md, narration.json, learner.md, and
                             starter scenes per engine and genre (templates/live/scenes/example-*.js)
  kit/                       the Python kit: kit/src/studio_kit/<module>.py, tests in kit/tests/
  engines/live/              the live engine: cli.mjs, src/player.js (the scene context `c`),
                             src/stage.js (2D), src/stage3d.js (3D), src/kit.js (helpers),
                             src/glossary.json (the motion glossary)
  engines/remotion/          src/kit/ (Frame, explain.tsx: CodePanel, Terminal…; map, look)
  engines/motion-canvas/     src/ (kit.ts, map.ts, …)
  engines/shared/            what every engine imports: timing.js (cues, captions), motion.js,
                             camera.js, camera3d.js, reply.js
```

## A command's code

The CLI table is `kit/src/studio_kit/cli.py` (COMMANDS: each command's arguments and the
`module:function` that runs it). Each command lives in the module of its name, except:

| Commands | Module |
|---|---|
| still, boxes, duration, render, cut, import-tutor | `cli.py` (calls `render.py`, `engine.py`) |
| export | `render.py` |
| desk, serve, notes, wait, status | `page.py` (the desk; its page is `page.html`) |
| review-frames, review-status | `review_state.py` (receipt kinds: `reviews.py`) |
| lock, request | `workspace.py` |
| new, variant, fork | `new.py` |
| preflight, doctor | `doctor.py` |
| capture, asset | `assets.py` |
| sfx, sound-lab | `sfx.py` (the sound kit: `soundkit.py`, `soundkit.json`) |
| commit | `checkpoint.py` |
| open | `cuts.py` (the cut store: every cut record is read and written here) |
| ingest, edit | `footage.py` |
| typing | `typecode.py` |
| init | `pin.py` |
| lexicon | `preferences.py` |

Plates are `plates.py` (the kit's side) and `engines/blender/plate.py` (Blender's), with a starter
scene script in `templates/blender/scene.py`. Typed code is `typecode.py` (the generator) and `engines/remotion/src/kit/editor.tsx` (Editor,
RunTerminal, ProgramWindow); an effect made of many events is `streams.py`. What a clip's frames
depend on (its cache key) is `keys.py`; the timeline's contract, cues and
captions are `timeline.py`; video.json's settings and their defaults are `settings.py`.

## Questions the kit answers in one place

- **Can captions be hidden?** Set layout.json `band.height` to 0: no band, no captions
  (`taste/screen-text.md`).
- **Where does a reviewer's result go?** `VIDEO/.studio/work/review/` (`reviews.md`).
- **Where do helper scripts go?** `.studio/work/` while trying, `sims/` once the build depends on
  them; run with `studio run` (`ownership.md`).
- **Which Python has numpy and Pillow?** The kit's, through `studio run`; never system `python3`.

## The video folder

`SCRIPT.md` owns narration and its learning brief; narrative Decisions own settled direction.
`narration.json` owns effective voice/timing settings. `boards/` holds the boards (boards.json is
written by the builder; notes.json is generated). `sims/` holds the video's scripts (evidence
extraction and helpers the build reruns), `data/` the evidence they produce.
`timeline.json` is built, never edited: each command writes the source it owns and rebuilds it
(`audio/timings.json` narrate, `audio/words.json` align, `audio/sfx.json` sfx, `audio/beats.json`
beats, `footage/edit.json` edit, video.json `duration` or `clips` for a piece without narration).
`cues.json` is the beat sheet: named events, each seconds or an anchor on the narration
(`{"sentence", "at": "start"|"end"|"word"|"phrase", "word", "phrase", "offset"}`, the contract at the
top of `timeline.py`) that follows its words when the narration moves. Time picture and sound from
the same event: a scene's `cue(name)` and an sfx entry naming it land on one frame, and every cut
has a still two frames after each event. Extra audio such as a music bed goes in `audio/tracks.json`
(`[{"file", "start", "gain"}]`; `studio music --bed` writes its own entry), and captions the kit must not re-chunk in `captions.json`
(chunks of `text` or `lines`, fixed at `start`/`end` or anchored to their words; a kit chunk copied
from timeline.json keeps its anchor, so a locked chunk follows its words when the narration moves); after editing any of them, `studio timeline VIDEO` (or the next cut) rebuilds it.
`research/` holds reviews, snapshots, timing, pending requests and the handoff. `.studio/work/` is
the builder's scratch: kept across a restart, ignored by Git and left behind by fork; a helper worth
keeping moves to `sims/`.
`cuts/cutN/` retains a record and MP4; watched/final/noted cuts also retain their review previews.
`out/master.mp4` is the final-quality local master; the web copy may be smaller.

`$STUDIO_HOME` defaults to `~/studio`. Read its learner model for audience knowledge. `studio new`
snapshots its optional `house.md` and `lexicon.json`; existing videos do not silently inherit later
edits. Explicit video choices win over series, house and kit defaults. Natural-language house
preferences are applied by the agent; commands do not interpret arbitrary prose as configuration.

Generated media are ignored by Git; preserve them through cut retention/artifact storage. Old
tracked binaries are not automatically removed from the index or rewritten out of history.
Pinned videos still run their old cleanup code until explicitly updated: protect/back up their
cuts before resuming production, then use the installed `studio init VIDEO --update`.
