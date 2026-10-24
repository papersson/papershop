# Review on the desk

Run `studio desk VIDEO`. It starts a standalone process that survives the agent and prints an address on the first free
port from 8765; `--port` chooses one. Give the user that address when the reel or a new version is
ready. The desk is a computer tool. The user watches and gives feedback; you operate the kit.

The default view plays the real narration with boards, then live scenes as chapters land; a saved
reel remains playable before any scene exists. Selecting a saved version keeps its picture and
sentence timings stable. A/B switches versions at the same timecode and shows what changed.
Space and J/K/L control playback, comma/period step frames, A adds a note even while playing,
C toggles captions, and I/O or Shift-drag selects a range. The timeline holds story beats,
picture thumbnails, the measured voice waveform, sound events and notes. `studio open VIDEO [CUT]` opens and protects a
saved playable movie when the user wants the MP4.

A note records its version and playhead, range, story beat, chapter lane or whole-film scope.
Notes save as they are written; there is no round to send. Narration, picture and both are useful kinds. Keep
controls below the picture so paused captions stay visible. The notes are stored in
`review/notes.jsonl`, and `review/status.json` supplies the status line.

Run `studio wait VIDEO --chapter s1` between chapter actions (omit the chapter for the main builder).
It returns queued notes, including those written while a watcher was absent and
review suggestions the user has just accepted. `studio notes VIDEO` lists the current notes.
Reading does not consume a note: `notes --start ID` acknowledges it. Honour Stop control notes,
stop work, resolve the note and emit `agent.stopped`. Stop is cooperative; the desk says requested
until the agent acknowledges it. Keep `studio status VIDEO "Working on the input example" --busy` current.

The build lives in `review/events.jsonl`. Emit real actions, never fake heartbeats:
`studio event VIDEO agent.activity "Typing the gradient" --lane s2`. Record `story.lock` when locked,
`chapter.done` after checks and inspection, and `decision "Reason for this hold" --lane s2 --t 150`
for a decision pin. The file watcher records saved scenes, cues, previews and checks. The lane becomes
quiet after 30 seconds without evidence and stalled after two minutes, retaining its last action.
The raw event and its source are one click away. `--hook` accepts Claude hook JSON on stdin and
retains session, agent and tool metadata only. Scope hooks to the chapter's job; do not guess a lane
from an unrelated transcript. Codex agents use the same event command at meaningful boundaries.
Replay build runs the actual log at 10x. Estimates use completed lock-to-ready intervals and label
small samples as guesses. The arrival tick is off by default.

For finer story anchors, `data/story-beats.json` is a list of `{id, title, clip, t}`; `t` is a real
timeline second or narration anchor. Without it, chapter starts form the story lane.

For each accepted note:

1. Read it against the cut and sentence the user saw. Mark it with `studio notes VIDEO --start ID`.
2. Make the smallest coherent change. A structural complaint needs a change to the story, even
   when it arrived beside one sentence. Take whole-video feedback in chat as well; the user
   should never need to annotate every instance of the same underlying problem.
3. If speech changed, narrate again and check the affected voice. Sentence ids are positional;
   update anchors and pronunciation overrides after edits. If only the picture changed, keep
   the existing narration.
4. Run the relevant deterministic checks and inspect the affected frame or transition. Make
   `studio cut VIDEO` and show the new version. `--changelog FILE` accepts a JSON list of
   `{ "note": "...", "change": "..." }` for the desk's before-and-after account.
5. Resolve with `studio notes VIDEO --resolve ID --reply "The pixel now fills the stage."`
   The reply appears under the note. Aim to return each local revision in minutes.

Reviewers' findings enter through `studio suggest VIDEO FILE`. FILE is JSON:

```json
{"cut": 2, "chapter": "s1", "findings": [
  {"t": 3.2, "kind": "picture", "note": "Enlarge the editor so its active line is readable."}
]}
```

A finding can use `sentence_id` in place of `t`; a time is in seconds from the start of the full
video. The importer uses that cut's saved timeline, validates the whole file before writing and
preserves existing decisions on repeated imports. Notes have author `review` and status
`suggested`. The user presses Accept or Dismiss on the desk. You may also use
`studio notes VIDEO --accept ID` or `--dismiss ID` when relaying the user's explicit decision.
Work begins only on accepted suggestions. Plain review records stay under `research/reviews/`.

When the user says “ship it,” record the decision and publish with
`studio publish VIDEO --by "NAME"`. `SHIP.md` contains one line with who and when. A retry reads
that line. The command checks every chapter, finishes the mix, renders a final cut and writes
`out/master.mp4`, `out/web.mp4`, `out/page/` and `out/colophon.md`. Listen to judge balance and pronunciation.
Report actual resolution, frame rate, duration and file paths.
External uploading follows the user's requested destination.

Mark `studio stage VIDEO waiting` while waiting for feedback and `finished` when done. Use
`studio stage VIDEO --report` for elapsed time. Append lasting preferences from the user's notes
to the final section of `taste.md`; keep individual corrections with the video.
