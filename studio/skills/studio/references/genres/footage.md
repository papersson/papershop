# Footage: editing recordings by their words

Cut a talk, a screen recording, an interview or a demo. The transcript is the edit: you choose
sentences, the kit builds the timeline, and captions come from the recording's own words.
`studio new NAME --genre footage`.

## The steps

1. **Ingest**: `studio ingest recording.mp4 VIDEO --name talk`. The recording is copied into
   `assets/` (recorded as supplied), and the kit writes `footage/talk.words.json` (every word with
   its start and end, from faster-whisper), `talk.shots.json` (scene changes), and
   `talk.paper.md`: the transcript as numbered sentences with timestamps, a `~` on sentences with a
   filler word (um, uh, er, hmm) and a `…` where a pause over 0.7 s precedes.
2. **Fix the transcript.** The recogniser mishears names and terms ("Claude" came out as "CLOD").
   The words become captions, so correct `footage/talk.words.json` (and the paper edit) before the
   edit is built.
3. **Paper edit**: read the paper edit, decide what to keep, drop the tangents and the fillers, and
   write an edit list: `[{"src": "talk", "in": 4.64, "out": 7.10}, {"src": "talk", "in": 15.66,
   "out": 22.76, "gain": -2}]`. Segments play back to back; a jump cut is two segments. Cut between
   words: start a segment a fraction before its first word (0.05 s), end it a fraction after its last.
4. **Build**: `studio edit VIDEO edl.json` writes the timeline: the footage track (segments), the
   audio track (each segment's sound, with an 8 ms fade at each cut so a cut never clicks, and its
   `gain`), the narration track (the words spoken inside each segment, mapped onto the new timeline)
   and captions chunked from them.
5. **Overlays**: `scenes/s1.tsx` draws over the `Footage` component (callouts, lower thirds, titles,
   zooms), cued on the words: `at('03')` is sentence 3 of the edit, `word('03', 2)` its third word.
   The footage plays muted; its sound is mixed from the edit list. `fit="cover"` fills the frame,
   `"contain"` letterboxes.
6. **Cut and review** as usual: `studio cut`, the review page, notes by timestamp against the sentence
   on screen.

## What `studio check` adds

- **filler**: a filler word left in a segment (it reads the source words that overlap each segment).
- **cuts**: a cut through the middle of a word.
- **levels**: a segment more than 3 LU from the median loudness, with the gain that would fix it
  (put it in the segment's `gain`).
- **sync**: a recording whose audio and video lengths differ by more than 40 ms.
- **segments**: a segment under 0.4 s, which flickers.

## Limits

Cuts only: no cross-dissolves, no multi-camera, no colour grading, no speed ramps. The `Footage`
component is where those would go. The finished loudness of the mix is not normalised: `studio audio`
finishes a narration track, not a mixed edit.
