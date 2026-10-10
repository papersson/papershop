---
name: studio
description: >
  Make, revise and publish narrated explainers, code lessons, motion graphics, launch films,
  pixel art and transcript-based edits of recordings. Settle the narrative, build scenes on a
  shared timeline, review cuts and revise incrementally. Use for video creation, watching or
  annotating a cut, re-voicing, rendering, publishing, or studio setup. Not for a plain chat
  explanation, slide deck, still image or document.
---

# studio

Make one video and improve it in rounds. The user approves the direction, chooses a look and
reviews cuts. The narrative determines what the viewer learns; the timeline and recorded evidence
keep narration, scenes and revisions consistent. Re-render only changed dependencies. Respect
existing authorization rather than adding repeated permission gates.

## Route the work

Infer these choices or ask only what affects the result; record them in video.json:

| Choice | Meaning |
|---|---|
| Drive | `author`: the user can judge the subject; `learner`: independent subject verification is needed |
| Genre | `explainer`, `motion`, `launch`, `pixel`, `footage`; code construction is an explainer format |
| Level | `intro` (default): scaffold a few key ideas; `deep-dive`: more mechanisms, assumptions and evidence |
| Tone | `plain` (default): the polish in `references/style.md`. `comic` only when the user asks for a comic, cartoon, silly or slapstick video; "fun", "delightful" or "engaging" mean plain. When tone is comic, read `references/styles/comic.md` before the narrative (it changes script, boards, sound, review and budget); otherwise never read it |
| Destination | `private-page` (default), `share`, `social`, `files` |
| Mode | `background` (default): an agent builds the video unattended; the user approves the narrative, picks the look and reviews cuts. `interactive`: the user follows on the desk and the builder works in the foreground, chapter by chapter, taking each note as it arrives (`references/desk.md`). Use interactive only when the user asks to follow, steer or be involved; never make a background run wait on them |
| Engine | `live` (default for explainers): plain JS scenes drawn from t, played and hot-reloaded on the desk, rendered by the same code. `remotion`: code explainers (CodePanel, Terminal and the other code components), motion, launch and footage. `motion-canvas`: generator scenes (`references/engines.md`) |

Depth, runtime and production effort are separate. Read `references/levels.md` for depth and
`references/pedagogy.md` for explainers. Every teaching explainer gets a student script pass,
including author/intro. Learner drive or deep-dive level also requires expert/editor review;
specific claim risks can add these through `video.json.review_roles`. `thorough`
allows additional investigation and capped review; `economy` reduces optional effort. Neither
setting waives a known correctness failure.

| Mode | Procedure |
|---|---|
| Setup | `studio doctor [VIDEO]`; install missing extras with its exact `--fetch` repair command |
| Propose | `studio new NAME …`; explainers use `references/propose.md`, others use `references/genres/<genre>.md` |
| Build explainer | `references/explainer.md`; code also reads `references/code.md`; visual language is in `references/style.md`; tone comic also reads `references/styles/comic.md` |
| Build other genre | `references/genres/motion.md`, `launch.md`, `pixel.md` or `footage.md` |
| Review/revise | `references/publishing.md`; merge/trim obsolete material as part of each change |
| Interactive | `references/desk.md`: the desk, `studio wait` in the background, note → scoped change → checks → reply |
| Publish | Local final master through `studio publish`; external upload per `references/publishing.md` and existing authorization |
| Revoice | Edit narration.json, narrate, voice-check, inspect affected stills and create a new cut |
| Status/resume | Read `research/handoff.md` (`studio handoff` writes it; `lock acquire --recover` prints it), narrative Decisions, SCRIPT.md, review receipts, pending requests, cuts and `studio stage --report` |

## Ownership, review and gates

One builder owns a folder across stages: `studio lock VIDEO acquire --owner NAME` prints an
`STUDIO_OWNER` token for its commands. The main session queues mid-flight additions with
`studio request`; the owner reads them at stage boundaries and resolves incorporated IDs.
Do not launch multiple writers against the same folder; chapter fixers working under the main
session's lock follow `references/explainer.md` (Long passes). Reviewers use immutable input
bundles. Release ownership at handoff, with `studio handoff` written first when the video is not
finished; `--recover` is for an abandoned build, never a way to displace a live one.

The main session owns independent review dispatch. A background builder can report **ready for
script review**, **ready for look choice**, **ready for motion review** or **ready for frame review**
and receive results back.
It need not spawn children. In interactive mode the main session is the builder: it builds in the
foreground, says **chapter N ready on the desk**, and takes notes as `studio wait` delivers them.
Do not substitute a self-review for an unavailable independent review.

The stages and what must hold before each next one are listed once: the table at the top of
`references/explainer.md` for explainers, and each genre file for the other genres. These rules
hold at every stage:

- Agree on the learning brief and chain before scripting, unless already authorized to proceed.
- Frame review judges full-resolution crops and mechanism-sensitive transition frames, not just
  thumbnails; import the revision-tagged result.
- Polish is a planned stage of every explainer, and its gate is the motion review: frame sequences
  around every event and significant move, judged by a fresh reviewer. It stops at a round with no
  must-fix findings or at `motion_rounds` (default 2), and leaves the should-fix findings on the cut
  as known issues. Each cut reviewed is a round; only a structural mark over a substantially changed
  picture starts a new count. In background mode publish needs it settled (passed, known issues,
  or a user waiver); in interactive mode the user watches every cut, so it runs only when they ask, and it stops
  standing when a chapter is added or half of them change.
- Every asserted number or behavior has an Evidence row. Recorded code/data drive the scenes.
- Review caps leave open findings; they do not make them pass. Record unavailable or explicitly
  user-waived checks with `studio review-status`, including the reason. A material edit invalidates
  an earlier review receipt.

Mark stages with `studio stage` (including `waiting` and `finished`). Budgets are advisory; report
scope changes and stage time. The exception: in background mode a stage with its own budget in
video.json stops at twice it (STOP, and `studio stage VIDEO --check` exits 3); write a handoff and
report rather than continue. Scratch and helper scripts go in `VIDEO/.studio/work/`, never /tmp;
run them with `studio run`. Commit only at authorized stages through `studio commit`. Never
push or upload without authorization. Keep kit changes out of individual video work; implement a
workaround in the video and report a missing kit capability. Keep production tools and process
out of the narration; subject-specific code/product names remain legitimate.

## Commands

All commands run through `bin/studio` in its pinned environment. `--help` lists full arguments.
VIDEO is a path to a folder holding `video.json`, relative to the current directory; anything else
is refused, with the nearest videos in `$STUDIO_HOME` suggested, so pass the full path.

| Command | Purpose |
|---|---|
| `doctor [VIDEO] [--fetch] [--extra kokoro|align|audio] [--sounds] [--net]` | Environment, package/model and network diagnostics; `--fetch --sounds` fetches the sound kit alone (CC0 recordings, pinned by sha256, into `$STUDIO_HOME/cache/`; engines only with `--engine`/`--extra` or when Remotion is missing); packs stay zipped, and a row says whether it is there and verified (with VIDEO: whether its library sounds are present) |
| `new NAME [--source REPO] [--drive …] [--level …] [--tone plain\|comic] [--mode background\|interactive] [--genre …] [--engine live\|remotion\|motion-canvas]` | New folder, source repository and snapshotted defaults (explainers default to the live engine) |
| `new NAME --from VIDEO [--include RELATIVE_FILE]` | New series episode with look/lexicon and selected source/evidence dependencies |
| `variant SOURCE NAME` | Adapt a source video's evidence and scenes for a different audience |
| `fork SOURCE NAME [--title T]` | The same video taken elsewhere (another version or direction): its sources copied with a history of its own, no cuts, notes, requests, caches or the frame and motion receipts that judged those cuts. `variant` is for another audience and a new script |
| `lock VIDEO acquire|release|status` · `request VIDEO [TEXT] [--resolve ID]` | One writer and a pending-request queue; `acquire --recover` prints the handoff |
| `handoff VIDEO [--notes TEXT \| --notes-file FILE]` | `research/handoff.md`: a brief a fresh builder resumes from (state, reviews in flight, requests, next commands, builder notes) |
| `stage VIDEO NAME [--kind local|structural] [--summary TEXT]` · `stage VIDEO --report` · `stage VIDEO --check` | Timing and revision refactoring log; `--check` reads the current stage without marking and exits 3 at a background hard stop |
| `run [--allow-outside] VIDEO SCRIPT [ARGS…]` | A builder's `.py` (kit Python, kit importable) or `.mjs`/`.js` (node) inside the video, run in its folder with `STUDIO_VIDEO` and `STUDIO_WORK` set, `studio` on PATH as the video's own kit, and stdin closed; arguments pass verbatim, SIGTERM reaches the script, exit status passes through |
| `check VIDEO --only script|code-source` | Source/text checks before a browser or timeline exists |
| `steps VIDEO STEPS.json` | Execute full-file program versions and record source/output evidence |
| `review VIDEO ROUND [--only student|expert|editor] [--narrative FILE]` | Isolated, revision-bound script/narrative review; `max_rounds` counts the rounds since the latest structural stage mark |
| `review-frames VIDEO [--cut N] [--result FILE]` | Package a cut's frames for the main session, or import the reviewer's result (one for a cut older than the sources is recorded as stale, and publish refuses it) |
| `review-motion VIDEO [--cut N] [--result FILE]` | Package a cut's motion windows (frame strips around every event and uncovered move, from the cut's own frames) for the main session, or import the result as findings; stops at a round with no must-fix findings or after `motion_rounds` (2), recording the rest on the cut as known issues |
| `review-status VIDEO ROLE unavailable|waived [--reason TEXT]` · `review-status VIDEO listen passed|waived --reason TEXT [--at m:ss.s,…]` | Explicit review limitation/authorization; ROLE is a script reviewer, `frames` (alias `frame`) or `motion`. `listen` records the user's one listening to a mix with effects or music (publish warns without one), with the timecodes listened at: `--at`, else the ones audio-check chose for this mix |
| `narrate VIDEO [--estimate|--plan|--list|--fetch-only] [--yes]` | Script → speech, captions, word timings and pause cues; pauses by role (paragraph ends, questions, `[key]`), a delivery report against three references and a `delivery` warning when flat |
| `voice-check VIDEO [--all]` · `align VIDEO` | Recognition check and word alignment |
| `timeline VIDEO [--events]` | Rebuild timeline.json from its sources, after editing `cues.json`, `captions.json` or `audio/tracks.json`; `--events` lists the beat sheet: every cue's time, frame, clip and anchor |
| `lexicon add WORD --spoken TEXT [--phonemes IPA]` | Promote a pronunciation for future videos |
| `cut VIDEO [--stills-only] [--quality final] [--changelog FILE]` | Stills, changed clips and composite; reports actual output dimensions. Chapters without a scene show their boards |
| `boards VIDEO` | A stills cut of every chapter's board (`boards/boards.json`, notes from the screen notes); reports sentences with nothing on screen |
| `animatic VIDEO [--boards]` | Pictures held to the real narration with its audio, and a pacing report (runtime, chapter lengths, unchanged stretches, empty sentences), and the narration's delivery (rates, pauses, per-minute swing) |
| `open VIDEO [CUT]` · `desk VIDEO` · `notes VIDEO [--start ID \| --resolve ID --reply TEXT]` | Protected system playback; the desk (latest cut, sentence notes, live status and replies; `serve` is an alias); numbered notes and their marks |
| `wait VIDEO [--timeout S]` · `status VIDEO [TEXT] [--busy]` | Block until a new desk note arrives (run in the background to be woken by each note); the builder's status line on the desk |
| `glossary [--term T]` | The motion glossary: the words a note can use for motion and the helper behind each (`references/desk.md`) |
| `still VIDEO CLIP T --out PNG` · `boxes VIDEO CLIP T` | Inspect a frame or named-element bounds |
| `check VIDEO [--only …] [--all] [--format F]` · `sheets VIDEO OUTDIR [--strip CLIP T]… [--windows FILE]` | Incremental render checks (pacing, a 0.5 s hold after each move, warns from the cut's clips; `--only pacing` samples stills where no clip is rendered), contact sheets and label crops; strips of consecutive frames around each `--strip` time (repeatable) or each `{clip, t, frames?, fps?}` of a JSON windows file; `legend` (with video.json `legend`) warns on a colour used for two meanings, a meaning in two colours, or a reserved colour on an untagged element; tag elements with `means` |
| `look-sheet VIDEO [--format F]` | The model sheet: every element in each state (theme colours and roles, type sizes, the band, boxes, arrows, tokens, cards, close-up), drawn by the video's engine (live or Remotion) into `out/look/`, plus the video's own from `scenes/look.js`/`look.tsx`; `review-motion` includes its pages and flags a missing or stale sheet; a colour legend page when video.json declares `legend` |
| `audio VIDEO [--lufs -14]` · `export VIDEO --formats 16:9,9:16,1:1` | Finish the whole mix to its loudness and true-peak ceiling (publish and export do it too); multiple formats |
| `publish VIDEO` | Local final master, compressed web copy, poster and page; upload separately |
| `clean VIDEO [--dry-run] [--videos]` | Stale caches/previews; MP4 deletion is explicit and never overrides protection |
| `commit VIDEO MESSAGE` | Scoped source checkpoint; video.json `git.sign` is true, false or null/inherit |
| `capture URL VIDEO` · `asset add|list VIDEO` · `asset library VIDEO SOUND [--name ID]` · `asset restore VIDEO` · `asset list VIDEO --credits` | Assets with provenance; `library` copies a sound kit sound (an id, or `PACK:MEMBER`) into `assets/sounds/ID.ogg` with its pack, licence, creator and sha256, `restore` copies back the ones a clone lacks (Git leaves sound out), `--credits` prints the CREDITS block for the description (`references/publishing.md`) |
| `beats VIDEO TRACK` · `sfx VIDEO CUES` · `sound-lab VIDEO` | Music timing, and optional effects on cue or beat names or anchors (each mix places them on the current timeline): a cue's `type` plays its synth voice (24, `sfx.py`); `"sound": "kit"` or `"kit:ID"` plays a recording from the sound kit, landing on its transient peak and copied into `assets/sounds/` (needs `doctor --fetch --sounds` once); the lab plays each type's synth candidates and kit recordings; a kit sound plays at its trim (its synth voice's level), and `"visual"` (`cut`, `move`, `land`, `appear`) says what the picture does on the effect's frame, while the time stays the cue's |
| `music VIDEO --bed [--key Am] [--bpm 72] [--seconds S]` · `music VIDEO --remove` | An optional generated bed (slow chords, a soft pulse) as a music track the mix ducks, with its beat grid; only when the user asks for music |
| `audio-check VIDEO [--cut N]` | The soundtrack measured: sync (a kit recording by its peak; a tagged effect's picture judged in frames), audible, loud (over 13.5 dB above the voice's loudness; against the music without a narration), ducking, masking per word, the pauses guard (fails) and loudness, into `out/audio-check.json`; draws `out/audio-sheet.png` and close-ups of the hero effects, and prints about five timecodes to listen at (`references/publishing.md`) |
| `ingest FILE VIDEO` · `edit VIDEO EDL` | Transcript-based footage editing |
| `init VIDEO [--update]` · `import-tutor LESSON VIDEO` | Pin/update a kit or migrate a retired tutor timeline |

## Durable files and personal defaults

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

See `DESIGN.md` for rationale, `references/engines.md` for engine setup and diagnostics, and each
mode's reference for the detailed procedure.
