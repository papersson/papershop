# Motion: a piece where the motion is the point

A showreel, a UI morph, a story told in shapes, a launch teaser without a product. There is
usually no narration and often music. `studio new NAME --genre motion --duration 15` starts one:
a single clip of that length, and a starter scene (one shape that never cuts, and loops).

## What separates a good one from the "mid" ones

Everyone has the same model; what differs is the context you give it and whether it looks at its
own frames. A one-line prompt ("make a dynamic 15-second motion graphics video that shows what an
incredible motion designer you are") tests the engine and never the idea, because it contains no
idea, and hundreds of them produced reels that rhyme. So:

1. **A reference, not a description.** Naming a style beats describing one. With a frame, a video
   or a folder of the user's own work, extract stills (`ffmpeg -vf fps=2`), write
   `docs/style_guide.md` (palette in hex, type family, weight and tracking, shot lengths, transition
   types, camera moves, texture, how text enters and leaves) and `docs/shotlist.md`. Take the
   grammar of the reference, never its content, logos or characters. Show both files and wait for
   an OK before any code. Without a reference the default is centred text on a gradient with
   everything fading in.
2. **A state list, not a vibe.** The best pieces come from a beat-by-beat list of states: what
   exists at each moment, what changes. "One shape, never cut" is the strongest: a single element
   morphs size, radius and colour from state to state (button, loader, player, slider, chart,
   command palette); a cursor drives each change; the last state equals the first, so it loops.
   Write the list on the beat grid and show it before writing scenes.
3. **Stills before motion** (`studio cut --stills-only`): three directions if the look is open. A
   still takes seconds to change, a render takes a minute.
4. **Look at your own frames** (below). This is the habit that separates the viral clips from the
   rest; the honest ones report 160 model calls and hours, not one shot.

## Building it

- Every frame a pure function of time. Motion is closed-form: `spring(t)`, and `track(t, keys)` for
  a value that changes target several times (one spring per change, so any frame renders alone).
  Tab indicators and knobs stretch by putting the leading and trailing edge on different springs.
  Text inside a morphing container enters after the morph starts and leaves before the next
  (`swapAlpha`). Tiny overshoot on UI, none on type. Never `Math.random` (use `rng(seed)`), timers
  or CSS transitions.
- **The return must settle before the loop point.** A change that starts at the last frame leaves a
  seam. Set `"loop": true` in video.json (the motion scaffold does) and `studio check` compares the
  last frame with the first.
- **Something new every 2 to 4 seconds.** `studio check` flags a run of identical frames longer
  than four seconds as a dead beat.
- **Sound.** A supplied track: `studio beats VIDEO track.wav` writes bpm, beats, downbeats and hits
  into the timeline; scenes cue with `useClip().beat(i)`, `downbeat(i)`, `hits`. Start on a
  downbeat; state changes on beats, big moments on downbeats. No track: synthesise effects,
  `studio sfx VIDEO cues.json` (click, pop, thump, whoosh, placed on beat or cue names), and choose
  candidates by ear with `studio sound-lab`. Add the track to `audio/tracks.json`
  (`[{"file": "assets/track.wav", "start": 0}]`) and run `studio timeline VIDEO`. Finish with
  `studio audio` (-14 LUFS for social: `--lufs -14`).
- Motion needs less structure than an explainer: no SCRIPT.md, no reviewers. It has a brief (the
  state list) and the user's notes.

## The critique loop, in the agent

Before showing a cut, render the stills, `studio sheets VIDEO out/sheets` (a contact sheet, a
360 px phone sheet), and, around anything fast, `studio sheets VIDEO out --strip CLIP T` (12
consecutive frames, to catch pops and overlaps). Be a harsh motion director, not a proud author.
Score 1–10 on: hook in the first two seconds, readability at phone size, motion quality (springs,
no dead frames), variety, composition, sound sync. List the three worst problems with timestamps and
fix them; repeat until every score is 8 or more, at most three rounds. Hunt specifically for: text
overlapping during swaps, anything sliding instead of easing, corner labels and frame borders,
centred-on-gradient shots, blurry scaled text (never `will-change` on anything the camera scales),
a dead beat, a stutter at the loop seam.

## Formats

`studio export VIDEO --formats 16:9,9:16,1:1` renders every format from one timeline. Lay out
against the stage's size (`useStage()`): reframe type and UI per format, don't crop a landscape
render to vertical. `studio check --format 9:16` verifies a format.

## A long, ambitious piece (a music video, a five-minute film)

Write a director's brief, and treat it as hiring a crew: the film in one line (what the viewer
feels at the end, and the joke), references and what to keep, tools and keys and a budget, a
character bible if there is one, a beat sheet with timestamps and a visual payoff every three to
five seconds and a hook in the first two, where text goes big and where it sits like subtitles,
workflow gates (plan, stills, animatic at low resolution, full pass, polish, audio, render), the
critique loop above, and deliverables (final, loop check, poster, contact sheet). Work in
chapters: one scene file each (`scenes/sN.tsx`), a shared `docs/ANIMATION_GUIDE.md` written first
so parallel agents code in one style.
