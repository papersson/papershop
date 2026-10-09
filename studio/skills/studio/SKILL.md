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
| Build explainer | `references/explainer.md`; code also reads `references/code.md`; visual language is in `references/style.md` |
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
script review**, **ready for look choice**, or **ready for frame review** and receive results back.
It need not spawn children. In interactive mode the main session is the builder: it builds in the
foreground, says **chapter N ready on the desk**, and takes notes as `studio wait` delivers them.
Do not substitute a self-review for an unavailable independent review.

The stages and what must hold before each next one are listed once: the table at the top of
`references/explainer.md` for explainers, and each genre file for the other genres. These rules
hold at every stage:

- Agree on the learning brief and chain before scripting, unless already authorized to proceed.
- Frame review judges full-resolution crops and mechanism-sensitive transition frames, not just
  thumbnails; import the revision-tagged result.
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
| `doctor [VIDEO] [--fetch] [--extra kokoro|align|audio] [--net]` | Environment, package/model and network diagnostics |
| `new NAME [--source REPO] [--drive …] [--level …] [--mode background\|interactive] [--genre …] [--engine live\|remotion\|motion-canvas]` | New folder, source repository and snapshotted defaults (explainers default to the live engine) |
| `new NAME --from VIDEO [--include RELATIVE_FILE]` | New series episode with look/lexicon and selected source/evidence dependencies |
| `variant SOURCE NAME` | Adapt a source video's evidence and scenes for a different audience |
| `fork SOURCE NAME [--title T]` | The same video taken elsewhere (another version or direction): its sources copied with a history of its own, no cuts, notes, requests or caches. `variant` is for another audience and a new script |
| `lock VIDEO acquire|release|status` · `request VIDEO [TEXT] [--resolve ID]` | One writer and a pending-request queue; `acquire --recover` prints the handoff |
| `handoff VIDEO [--notes TEXT \| --notes-file FILE]` | `research/handoff.md`: a brief a fresh builder resumes from (state, reviews in flight, requests, next commands, builder notes) |
| `stage VIDEO NAME [--kind local|structural] [--summary TEXT]` · `stage VIDEO --report` · `stage VIDEO --check` | Timing and revision refactoring log; `--check` reads the current stage without marking and exits 3 at a background hard stop |
| `run [--allow-outside] VIDEO SCRIPT [ARGS…]` | A builder's `.py` (kit Python, kit importable) or `.mjs`/`.js` (node) inside the video, run in its folder with `STUDIO_VIDEO` and `STUDIO_WORK` set and stdin closed; exit status passes through |
| `check VIDEO --only script|code-source` | Source/text checks before a browser or timeline exists |
| `steps VIDEO STEPS.json` | Execute full-file program versions and record source/output evidence |
| `review VIDEO ROUND [--only student|expert|editor] [--narrative FILE]` | Isolated, revision-bound script/narrative review; `max_rounds` counts the rounds since the latest structural stage mark |
| `review-frames VIDEO [--cut N] [--result FILE]` | Package a cut's frames for the main session, or import the reviewer's result (one for a cut older than the sources is recorded as stale, and publish refuses it) |
| `review-status VIDEO ROLE unavailable|waived [--reason TEXT]` | Explicit review limitation/authorization; ROLE is a script reviewer or `frames` (alias `frame`) |
| `narrate VIDEO [--estimate|--plan|--list|--fetch-only] [--yes]` | Script → speech, captions, word timings and pause cues |
| `voice-check VIDEO [--all]` · `align VIDEO` | Recognition check and word alignment |
| `timeline VIDEO` | Rebuild timeline.json from its sources, after editing `cues.json`, `captions.json` or `audio/tracks.json` |
| `lexicon add WORD --spoken TEXT [--phonemes IPA]` | Promote a pronunciation for future videos |
| `cut VIDEO [--stills-only] [--quality final] [--changelog FILE]` | Stills, changed clips and composite; reports actual output dimensions. Chapters without a scene show their boards |
| `boards VIDEO` | A stills cut of every chapter's board (`boards/boards.json`, notes from the screen notes); reports sentences with nothing on screen |
| `animatic VIDEO [--boards]` | Pictures held to the real narration with its audio, and a pacing report (runtime, chapter lengths, unchanged stretches, empty sentences) |
| `open VIDEO [CUT]` · `desk VIDEO` · `notes VIDEO [--start ID \| --resolve ID --reply TEXT]` | Protected system playback; the desk (latest cut, sentence notes, live status and replies; `serve` is an alias); numbered notes and their marks |
| `wait VIDEO [--timeout S]` · `status VIDEO [TEXT] [--busy]` | Block until a new desk note arrives (run in the background to be woken by each note); the builder's status line on the desk |
| `glossary [--term T]` | The motion glossary: the words a note can use for motion and the helper behind each (`references/desk.md`) |
| `still VIDEO CLIP T --out PNG` · `boxes VIDEO CLIP T` | Inspect a frame or named-element bounds |
| `check VIDEO [--only …] [--all] [--format F]` · `sheets VIDEO OUTDIR [--strip CLIP T]… [--windows FILE]` | Incremental render checks, contact sheets and label crops; strips of consecutive frames around each `--strip` time (repeatable) or each `{clip, t, frames?, fps?}` of a JSON windows file |
| `audio VIDEO [--lufs -14]` · `export VIDEO --formats 16:9,9:16,1:1` | Finish the whole mix to its loudness and true-peak ceiling (publish and export do it too); multiple formats |
| `publish VIDEO` | Local final master, compressed web copy, poster and page; upload separately |
| `clean VIDEO [--dry-run] [--videos]` | Stale caches/previews; MP4 deletion is explicit and never overrides protection |
| `commit VIDEO MESSAGE` | Scoped source checkpoint; video.json `git.sign` is true, false or null/inherit |
| `capture URL VIDEO` · `asset add|list VIDEO` | Assets with provenance |
| `beats VIDEO TRACK` · `sfx VIDEO CUES` · `sound-lab VIDEO` | Music timing, and optional effects on cue or beat names (each mix places them on the current timeline) |
| `ingest FILE VIDEO` · `edit VIDEO EDL` | Transcript-based footage editing |
| `init VIDEO [--update]` · `import-tutor LESSON VIDEO` | Pin/update a kit or migrate a retired tutor timeline |

## Durable files and personal defaults

`SCRIPT.md` owns narration and its learning brief; narrative Decisions own settled direction.
`narration.json` owns effective voice/timing settings. `boards/` holds the boards (boards.json is
written by the builder; notes.json is generated). `sims/` holds the video's scripts (evidence
extraction and helpers the build reruns), `data/` the evidence they produce.
`timeline.json` is built, never edited: each command writes the source it owns and rebuilds it
(`audio/timings.json` narrate, `audio/words.json` align, `audio/sfx.json` sfx, `audio/beats.json`
beats, `footage/edit.json` edit, video.json `duration` or `clips` for a piece without narration). Named cues
go in `cues.json` (`{"name": seconds}`), extra audio such as a music bed in `audio/tracks.json`
(`[{"file", "start", "gain"}]`), and captions the kit must not re-chunk in `captions.json`
(`[{"start", "end", "text"}]` or `lines`; a whole track, or kit chunks copied from timeline.json to
lock them); after editing any of them, `studio timeline VIDEO` (or the next cut) rebuilds it.
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
