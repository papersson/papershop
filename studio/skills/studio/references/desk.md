# Review on the desk

Run `studio desk VIDEO` and keep the process alive. It prints a local address on the first free
port from 8765; `--port` chooses one. Give the user that address when the reel or a new version is
ready. The desk is a computer tool. The user watches and gives feedback; you operate the kit.

The default view plays a story reel until scene cuts exist, then shows live scenes and the whole
mix as files change. Selecting a saved cut keeps its picture and sentence timings stable. The
version list lets the user compare earlier cuts. `studio open VIDEO [CUT]` opens and protects a
saved playable movie when the user wants the MP4.

A note records the cut, time, chapter and current sentence, with the preceding sentence for
context. Narration, picture and both are useful note kinds. Empty notes still mean “here.” Keep
controls below the picture so paused captions stay visible. The notes are stored in
`review/notes.jsonl`, and `review/status.json` supplies the status line.

Run `studio wait VIDEO` in the background while working. It returns newly queued notes, including
review suggestions the user has just accepted. `studio notes VIDEO` lists the current notes.
Keep `studio status VIDEO "Working on the input example" --busy` current; clear it when idle.

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
`out/master.mp4`, `out/web.mp4`, `out/page/` and `out/colophon.md`. It may remind you to listen;
there is no listening receipt. Report actual resolution, frame rate, duration and file paths.
External uploading follows the user's requested destination.

Mark `studio stage VIDEO waiting` while waiting for feedback and `finished` when done. Use
`studio stage VIDEO --report` for elapsed time. Append lasting preferences from the user's notes
to the final section of `taste.md`; keep individual corrections with the video.
