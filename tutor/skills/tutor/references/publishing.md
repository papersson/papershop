# Publishing, feedback and revision

## The page

`kit/make_page.py LESSON` writes `out/page/`: `index.html`, `video.mp4` (the web encode) and `poster.jpg` (the frame named by `lesson.json`'s `poster`: a sentence id and an offset in seconds, negative to count back from the sentence's end). The page has the video, a chapter strip, a captions toggle, and a "Lost me here" button; nothing else, because a learner found a page with the script and sources on it "too busy". Check the poster frame before publishing: it is the image the learner sees in their gallery, so it should be the lesson's central picture, not a title card.

## Where it goes

**With the Artifact tool (claude.ai sessions).** Publish `out/page/index.html` with `files: {"video.mp4": ..., "poster.jpg": ...}`, `capabilities: {"db": {}}`, `icon: "video"`, and `description` from `lesson.json`. The `db` capability is what makes "Lost me here" work: notes are written to the collection `feedback`. After publishing, confirm the store with `ArtifactData list` on `feedback` (an empty result, not an error). The page is private to the learner until they share it from the page's Share menu; say so when handing over the link. To update a lesson, republish with the same `url`, so the link and the notes survive.

**Without it.** The same `out/page/` folder works as a local page: tell the learner to open `index.html` in a browser (the video plays from the folder). The "Lost me here" button hides itself when no database is available, so ask the learner to note timestamps by hand, or to send the times and what lost them in chat. Say plainly that feedback isn't collected automatically in this mode.

## Reading the notes and revising

Each note names a time, a chapter, the sentence on screen and the one before, an optional comment, and the lesson version. An empty comment still says "here".

1. Read all notes (`ArtifactData list`, collection `feedback`), or the learner's message.
2. For each, find the sentence in `SCRIPT.md` and name what the note shows: a skipped step, a term used before it was defined, two ideas in one sentence, an example that didn't land, pace. Add a row to `learner.md`'s evidence table; if a pattern recurs across lessons, add a standing instruction.
3. Revise only the chapters the notes point at. Keep sentence ids stable where text doesn't change, so the scenes' cues still hold; where a sentence is split or added, renumber that chapter's later ids and update the scene's `at()` calls.
4. Run the three reviewers on the revised script (the student plays the updated learner) until the gate holds again.
5. Re-narrate (`narration.py`; the whole lesson, since timings shift), re-render only the changed chapters (`build.py --only sN,sM`), rebuild the page with the version bumped in `lesson.json`, and republish to the same link.
6. Tell the learner what changed, chapter by chapter, and which note each change answers. Leave the notes in place; a note answered by version 2 stays as evidence.

## Re-voicing

A voice change is mechanical: edit `narration.json`, run `narration.py`, run `voice_check.py`, then a full `build.py` (every chapter's timing changes), `sheets.py` to check the cues still land, `make_page.py`, republish. Line ids do not change, so scenes need no edits, but holds may: a slower voice needs shorter holds. For ElevenLabs, a machine with the key can run `narration.py LESSON --fetch-only --yes` (standard library only) and commit `audio/elevenlabs_cache/`; any other machine then builds from the cache without the key and without paying again.
