# The review loop, publishing, and revising

## One revision procedure

Desk notes and published/chat notes enter the same loop. Open the desk with `studio desk VIDEO`, or
open the MP4 with `studio open VIDEO [CUT]` to protect it. The desk records playback handoffs too.
Either wait for a submitted batch (or explicit chat instructions) and read `studio notes`, or, when
the user wants to follow along, run `studio wait VIDEO` in the background and take each note as it
arrives: `studio notes VIDEO --start ID`, the change, a new cut, then `--resolve ID --reply "…"`
with one line saying what changed (it shows under the note, on the cut that answers it). Keep
`studio status VIDEO "…" --busy` current while working. Save the original annotations, and map each
note to the sentence/chapter of its cut. An empty note still means “here.”

1. Read the narrative Decisions, current review findings and pending research/requests.md.
2. Start a round: `studio stage VIDEO round --kind local|structural --summary "…"`. The summary
   records repeated ideas, obsolete material, merges/trims, affected chapters and expected change
   in length. Classify a new chapter or a changed arc as structural. Honor already authorized notes;
   present a genuine scope change before applying it, not a new approval ritual for routine fixes.
3. Revise the smallest coherent argument affected. An addition ships with the consolidation it
   makes possible, even when that touches a neighboring chapter. Update the learning brief and
   narrative Decisions together when needed. Record each note's disposition.
4. Recheck the teaching chain if the script changed; rerun the student review and any required
   subject review after material changes. `max_rounds` caps the review rounds of one revision of
   the script: rounds are counted from the reviews since the latest structural round mark, not
   from the ROUND typed, and reviewers run again on an unchanged script are the same round. A
   structural round mark (step 2) made over a script changed since its last review starts the
   count again; a mark over an unchanged script does not. Raising the cap is the learner's
   decision. Keep sentence cues/per-ID pronunciation overrides in sync. Narrate and voice-check
   only changed speech; a timing-only edit should reuse synthesis.
5. Answer picture notes with a still where useful, then `studio cut VIDEO --changelog FILE`.
   FILE is a JSON list of `{note, change}`. Run incremental checks/sheets/craft on the actual
   dependency changes; shared helpers may affect more than one chapter. Required independent
   frame review uses the new bundle and includes affected transitions/neighbors. A frame receipt
   goes stale when what its reviewer saw changes (a chapter's frames, the Script or Evidence
   section, data/), not after a sound-only edit (effects, music, the mix); a new beat grid stales
   the chapters whose scenes read it. `review-frames` packages any cut with that cut's own
   revision, and a result for a cut older than the current sources is recorded as stale, naming
   the chapters changed since; publish refuses a stale receipt and says what changed. Review a
   fresh cut, or record an authorized waiver. A motion review that has ended is not reopened by
   these fixes (below).
6. Report the cut, actual width×height/fps, quality and final-quality status, runtime change,
   note dispositions, late requests and measured stage times. Do not guess per-request minutes.
   Mark waiting/finished boundaries and checkpoint at authorized stages.

New requests are queued by the main session with `studio request VIDEO "text"` and incorporated
at a stage boundary; explicit stop/correction is immediate. One builder owns the folder. Do not
change sources during a render or launch a second writer. Preserve the record of what was deferred.
A changed chapter without a new Review log entry produces a cut warning; a re-encode need not
invent an editorial revision.

## The motion review and its stop rule

An explainer with a teaching contract (what `studio new` makes) publishes only with a settled motion
receipt: `passed`, `known-issues` or `waived`. Other genres don't need one. `studio review-motion`
packages a cut's motion windows and imports the reviewer's findings (`explainer.md`, Stage 11).

The review stops at a round with no must-fix findings, or after video.json `motion_rounds` rounds
(default 2), whichever comes first. Rounds count per cut lineage: each cut motion-reviewed is a
round (a re-cut of unchanged sources too), since the latest structural stage mark (or fork) made over
a picture that changed substantially: a new chapter, or half the chapters or more. A mark over a
small change buys no rounds, as a mark over an unchanged script buys no script rounds. Should-fix findings
plateaued at 25 to 45 a round in one long session, so the loop ran for hours with no natural end;
now the last round's should-fix and nit findings go on the cut record as `known_issues`, later cuts
carry them, and the desk shows them under the cut, so nobody raises them again. The receipt says how
it ended, read from the findings with the verdict line as a cross-check: `passed` (nothing left),
`known-issues` (no must-fix, smaller findings left), or `findings` with `stopped: "cap"` (must-fix
findings still open at the cap). A bundle takes one result, so a reviewer is not re-rolled. That last one is open,
never passed: report it to the user, who either has them fixed and records acceptance with
`studio review-status VIDEO motion waived --reason …`, or asks for more rounds by raising
`motion_rounds`. A third round is refused with that choice spelled out.

An ended review stands for its lineage: later small edits (frame-review fixes, desk notes) are
judged by the frame review and the user, not by another motion round. It stops standing when the
reviewed cut came before a structural mark that started a new count, or when a chapter is new or
half the chapters or more changed since that cut; publish names them and asks for a structural mark,
a fresh cut and a new review. A later review that ends replaces the known issues; a waiver records
how many it accepts. In interactive mode, when the user prefers to judge motion on the desk, record
a waiver whose reason names their notes by id (the receipt keeps the mode and the ids; such a reason
is refused in background mode). A video made before this requirement is told so at publish, with
the waiver to record if the user agrees.

## Publishing

`studio publish VIDEO` first requires the review receipts (script reviews, the frame review where
required, the motion review for an explainer) and runs the full `studio check` on every chapter as
its gate (a failure stops it), then renders the final cut (1080p) unless the latest cut is one (only chapters
whose key changed since the last final render re-render) with its whole mix finished to -16 LUFS
under a -1.5 dBTP ceiling (`studio audio`; a social export takes `--lufs -14`, below), links it as
`out/master.mp4`, encodes
`out/web.mp4` (its sound re-encoded under the same ceiling) to fit the Artifact tool's upload limit for one binary file (15 MiB: 1080p up to
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

**destination: files:** finish with `studio publish VIDEO` locally, then hand over `out/master.mp4`
and the poster (plus the smaller web copy when useful). Report both resolutions; no external upload
is required for a files-only deliverable.

**destination: social:** `studio export VIDEO --formats 9:16,1:1,16:9 --lufs -14` renders every
format from the same scenes into `out/export/`, each with its own stage and caption band (a
phone-shaped frame gets larger, shorter caption lines). Check each format first
(`studio check VIDEO --format 9:16`): text and images that fit a landscape stage often leave a
portrait one.

## Retention and checkpoints

Automatic pruning keeps every cut record and MP4. It removes only expendable previews/intermediates
from unprotected old drafts. `keep_cuts` defaults to ten playable drafts; stills-only previews have
a separate ten-preview allowance and do not evict playable cuts. Watched/opened, final-quality,
pinned and any noted cuts are protected, as are the latest playable cut and latest preview. A
legacy record without enough metadata is retained conservatively. “Watched” records a playback
handoff, not completion of viewing.

`studio clean VIDEO --dry-run` previews cache/preview cleanup. `--videos` additionally permits
removal of eligible old unprotected draft MP4s, never protected cuts or their records. The page
marks removed media unavailable. Do not delete cuts manually to satisfy a budget. Pinned older
kits retain their older pruning behavior until explicitly updated: protect/back up their cuts
before resuming production and run the installed `studio init VIDEO --update`.

`studio new` initializes Git for a standalone folder or reuses its enclosing repository. Generated
media (video, audio, recordings and GIFs, in any letter case), cut previews, caches, out/, package
folders and secrets (`.env*`, keys) are ignored; source/evidence/review records, boards, captures
and paid narration responses remain checkpointable. `studio commit VIDEO "message"` uses a private
index and stages every file in the video's folder that its .gitignore admits, adding the kit's
rules to an older .gitignore first, and preserves unrelated staged work. A new file over 20 MB is
left out with a note, whatever its type; `git add` it once to track it on purpose. `video.json.git.sign` is null/inherit by default, true
for explicit signing, false only when unsigned commits are authorized. It never changes global
Git settings or silently falls back from signed to unsigned. Commit only at authorized stages.
Existing tracked binaries need an explicit index migration; ignoring a formerly tracked MP4 does
not remove it or its history. Cut retention is separate from Git backup.

## Versions

video.json's `version` names the page's note set. Keep it across minor revisions and put the minor
version in the description ("v2.1: shorter chapter 3"), so notes on the page survive; bump it for a
major change, which starts a new note set.

## Published notes

Use `ArtifactData list` on feedback when that connector is available; save its output to
research/annotations_vN.txt and follow the revision procedure above. Each note identifies version,
time, chapter and sentence. In learner drive, add observed gaps to the learner model; simulated
reviewer predictions remain labeled predictions. Republish to the same link for minor revisions
and leave the notes intact. Do not claim notes were collected when no feedback connector exists.

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
