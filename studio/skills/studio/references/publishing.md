# The review loop, publishing, and revising

## The review loop

Each round is a cut the user watches and a batch of notes you answer.

1. **Serve the cut.** `studio cut VIDEO` (a stills-only cut before animation), then
   `studio serve VIDEO` in the background, and give the user http://127.0.0.1:8765/. The server
   keeps running across cuts; the page picks up a new cut by itself.
2. **Wait for the round.** On the page the user pauses, presses A, says whether the note is about
   the narration, the picture or both, and clicks Send round. Every change is a line appended to
   `review/notes.jsonl`; a `"type": "round"` line means the batch is ready. Watch the file (a
   Monitor on it, or ask the user to tell you) rather than polling in a loop.
3. **Read the batch**: `studio notes VIDEO` prints the notes numbered, each with its time, sentence
   id and the sentence on screen. Save them as `research/annotations_cutN.txt`.
4. **Propose before applying.** Map each note to its sentence and chapter, group the notes into
   themes, and say what you'll change. A narration note changes SCRIPT.md (then `studio narrate`:
   only the edited paragraphs re-synthesise, and in learner drive the reviewers re-check the
   changed sentences); a picture note changes a scene. Log each decision under the narrative's
   Decisions ("## After cut N").
5. **Answer fast.** When a frame settles a picture note, show the updated still first (`studio
   still`); then `studio cut VIDEO --changelog FILE`, where FILE is a JSON list of
   `{"note": "3. the labels are too small", "change": "labels 18 → 24 pt in s2"}`. Only the
   chapters a change touches re-render, and the page shows before/after stills for them. Keep the
   round's whole-video steps incremental too: `studio check`, `studio voice-check` (changed
   sentences) and `studio sheets` (changed frames), and hand a frame reviewer only the changed
   chapters. The user is waiting on this round: time from notes to the next cut is the thing to
   keep short, without dropping a check.
6. Repeat until the user locks the video. Final quality is rendered once, by `studio publish`.

A picture note about something reviewers passed is still right: the user spotted an off-centre
label on the first frame of a build that had passed every review.

## Publishing

`studio publish VIDEO` first runs the full `studio check` on every chapter as its gate (a failure
stops it), then renders the final cut (1080p) unless the latest cut is one (only chapters
whose key changed since the last final render re-render), links it as `out/master.mp4`, encodes
`out/web.mp4` to fit the Artifact tool's upload limit for one binary file (15 MiB: 1080p up to
about 16 minutes, 720p up to about 28, 540p beyond; it prints the settings it chose; each chapter is
encoded once and cached, so a re-publish encodes only the chapters that changed), grabs the
poster frame (`video.json` `"poster": ["s5_07", -0.2]`: a sentence id and
an offset, negative to count back from its end; pick the video's central picture, not a title
card), and writes `out/page/`: `index.html`, `video.mp4`, `poster.jpg`.

The page is the video, its chapters and one feedback button. In learner drive it is "Lost me here"
(the moment and an optional note); in author drive it is "Annotate" (the moment, narration or
picture, ±1 s). Notes go to the artifact's database, collection `feedback`. There is no captions
toggle: captions are burned in.

**With the Artifact tool:** publish `out/page/index.html` with
`files: {"video.mp4": "out/page/video.mp4", "poster.jpg": "out/page/poster.jpg"}` (the web encode,
already under the upload limit; `out/master.mp4` is the 1080p master, for the user to open locally),
`capabilities: {"db": {}}`, `icon: "video"`, and `description` from video.json (one sentence: the
question the video answers). After publishing, confirm the store with `ArtifactData list` on
`feedback` (empty, not an error). The page is private until the user shares it from its Share menu;
say so. To update, republish with the same `url`, so the link and the notes survive.

**Without it:** `out/page/` works as a local page opened in a browser; the button hides itself with
no database, so ask the user for notes in chat or on the local review page. Say that notes aren't
collected automatically.

**destination: files:** hand over `out/web.mp4` and the poster.

**destination: social:** `studio export VIDEO --formats 9:16,1:1,16:9 --lufs -14` renders every
format from the same scenes into `out/export/`, each with its own stage and caption band (a
phone-shaped frame gets larger, shorter caption lines). Check each format first
(`studio check VIDEO --format 9:16`): text and images that fit a landscape stage often leave a
portrait one.

## Disk

Each cut folder holds a draft video and its stills (20–40 MB for a long video), so `studio cut` keeps
only the newest 3 (`"keep_cuts": N` in video.json), plus the cut of the latest notes round. After a
video is published, or when space runs short, `studio clean VIDEO --dry-run` lists what can be
regenerated and its size, and `studio clean VIDEO` removes it (old cuts, caches for older versions,
narration chunks the script no longer uses, sheets, the web copy and the loudness pass). It never
touches the script, scenes, data, research, the narration audio, the latest cut, out/master.mp4 or
out/page. On the 25-minute benchmark video it freed 407 MB of 841 MB.

## Versions

video.json's `version` names the page's note set. Keep it across minor revisions and put the minor
version in the description ("v2.1: shorter chapter 3"), so notes on the page survive; bump it for a
major change, which starts a new note set.

## Revising from notes

Notes from the published page: `ArtifactData list` on `feedback`. Each names a time, a chapter,
the sentence on screen and the one before, a note (possibly empty, which still says "here"), and
the version.

1. Save them to `research/annotations_vN.txt`, map each to its sentence, group into themes, and
   propose the changes before applying any.
2. In learner drive, add what each note shows to the learner model's evidence table (a skipped
   step, a term used before it was defined, two ideas in one sentence, pace), and add a standing
   instruction when a pattern recurs across videos.
3. Revise only what the notes point at. Keep sentence ids stable where the text doesn't change; a
   split or added sentence renumbers that chapter's later ids, so update its scene's `at()` calls.
4. Learner drive: re-run the reviewers until the gate holds (the student plays the updated model).
5. `studio narrate`, `studio voice-check`, `studio cut` (changed chapters only), check the stills,
   `studio publish`, republish to the same link.
6. Tell the user what changed, chapter by chapter, and which note each change answers. Leave the
   notes in place.

## Re-voicing

Edit `narration.json`, then `studio narrate` (ElevenLabs: `--plan` shows the characters it will
spend, and `--fetch-only --yes` fills the response cache on a machine with the key; commit
`audio/elevenlabs_cache/` and any machine builds from it without the key), `studio voice-check`,
`studio cut`, check the stills (a faster voice can end a sentence before its animation does), and
republish. Sentence ids don't change, so scenes need no edits, but holds may.

## Videos from the old tutor plugin

A tutor lesson keeps its own copied kit and rebuilds with it. To bring one into the studio,
`studio import-tutor LESSON VIDEO` turns its narration and timings into a timeline; its Manim
scenes are the visual reference for new Remotion scenes (ported chapter by chapter, as
"Charged Twice" was).
