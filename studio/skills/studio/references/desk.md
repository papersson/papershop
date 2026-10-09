# The desk: interactive mode

Interactive mode is for when the user wants to follow along and steer: they watch the video take
shape on the desk, a local page beside the terminal, and leave notes on single sentences; the
builder takes each note as it arrives and answers under it. It is opt-in (`"mode": "interactive"` in
video.json, or the user asks to follow along). In background mode nothing here waits on the user.

## Setting up

1. Run `studio desk VIDEO` in the background and give the user its address. On the live engine the
   desk plays the current scenes with the narration and redraws the moment a scene, the timeline or
   the boards change; on Remotion or Motion Canvas it plays the latest cut and swaps in each new cut
   at the same moment.
2. Run `studio wait VIDEO` in the background. It returns when a note arrives, printing the note, its
   sentence, its kind (narration, picture or both), its id and any glossary words it uses; then
   handle it and start `studio wait` again.
3. Keep `studio status VIDEO "what you are doing" --busy` current; it is the line in the desk's
   header, and the user's answer to "is it stuck?". Clear it (`studio status VIDEO`) when idle.

## Building

Settle the narrative and pass the script review first (`explainer.md`); the desk is for the build.
Build in the foreground, one chapter at a time. Unbuilt chapters show their boards, so the desk
always plays the whole video. After each chapter: `studio check VIDEO` (incremental: only changed
chapters), then tell the user **chapter N is ready on the desk**, and keep building while notes
arrive. Make a cut (`studio cut VIDEO`) when a chapter or a round of notes is done; on the live
engine a cut is for the record and the publish gate, not for the user to see the change.

## Each note

1. `studio notes VIDEO --start ID`: the desk shows it as working.
2. Classify it with the per-note procedure in `publishing.md`: local (one sentence or picture) or
   structural (a new chapter, a reordered argument, a changed claim). For a structural note, first
   propose the change and its runtime cost (in the session and on the status line), and apply it
   once the user agrees.
3. Make the smallest coherent change:
   - narration: edit SCRIPT.md, re-run `studio narrate VIDEO` (only the changed paragraphs and their
     neighbours re-voice), then fix cues the edit moved;
   - picture: edit `scenes/<clip>.js` (live) or the clip's scene; cue labels on what the voice says
     with `c.phrase(id, text)` so they land on the words;
   - a glossary word in the note ("stagger", "blur them together") names the move: use its helper
     (`studio glossary --term …`). The terms for weight and life map to the shared motion helpers:
     "keyframe" (`keyed`, a path with stops and an ease per leg), "heavy", "float" and "snap" (eases),
     "overshoot" (`ease.back`), "follow-through" (`follow`), "settle" (`settle`) and "wobble"
     (`wobble`). A move the glossary lacks: make it, and add the term to
     `engines/live/src/glossary.json` with a demo in `glossary.js`;
   - a note on timing at a contact ("the thud is early"): move the event in `cues.json`, which moves
     its picture, its effect and its still together (`studio timeline VIDEO --events` lists them).
4. Check before answering: `studio check VIDEO` (determinism, bounds, band, legible, overlap, pacing
   once a cut has rendered the chapter and, on the live engine, any scene error, for the changed
   chapter) and look at a still of the changed
   moment (`studio still VIDEO CLIP T --out …`). Never resolve a note whose change fails a check.
5. `studio notes VIDEO --resolve ID --reply "one line saying what changed"`. The reply shows under
   the note, on the cut or live view that answers it.

Several notes that arrive together come back together from `studio wait`; handle them in sentence
order and resolve each. A note that asks a question ("is this the same log?") is answered in the
video when the video should have answered it, and in the reply when it shouldn't.

## Background runs and the desk

A background builder never waits on the user. If the user opens the desk on a background video and
leaves notes, `studio stage` lists them as open notes at each stage boundary; take them then, with
the same per-note procedure, and resolve each.
