# Commands

Every command runs through the skill's `bin/studio`, by its absolute path; only `preflight` skips
environment bootstrapping. `studio COMMAND --help` lists full arguments. VIDEO is a path to a folder
holding `video.json`; anything else is refused, with the nearest videos in `$STUDIO_HOME` suggested.
Every file or folder argument is resolved against the directory you call `studio` from. Where each
command's code lives is in `kit-map.md`.

All commands run through `bin/studio`; only `preflight` skips environment bootstrapping.
`--help` lists full arguments.
VIDEO is a path to a folder holding `video.json`, relative to the current directory; anything else
is refused, with the nearest videos in `$STUDIO_HOME` suggested, so pass the full path.

| Command | Purpose |
|---|---|
| `preflight [VIDEO] [--engine live\|remotion\|motion-canvas] [--extra kokoro\|align\|audio] [--silent]` | Read-only prerequisite check before setup; defaults to live with Kokoro and alignment, or the video's requirements; no downloads, syncs or browser/model launches |
| `doctor [VIDEO] [--fetch] [--extra kokoro|align|audio] [--sounds] [--net] [--speech]` | `--speech` tests local synthesis and recognition (may download weights; setup approval first). Environment, package/model and network diagnostics, the WebGL renderer the live engine's 3D stage gets; `--fetch --sounds` fetches the sound kit alone (CC0 recordings, pinned by sha256, into `$STUDIO_HOME/cache/`; engines only with `--engine`/`--extra` or when Remotion is missing); packs stay zipped, and a row says whether it is there and verified (with VIDEO: whether its library sounds are present) |
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
| `typing VIDEO PLAN.json` | Code typed from a plan of edits between recorded versions: `data/typing.json` for the Remotion `Editor`, `type-*` cues, and per burst a key stream and accents in `audio/sfx.json` (`code.md`) |
| `review VIDEO ROUND [--only student|expert|editor] [--narrative FILE]` | Isolated, revision-bound script/narrative review; `max_rounds` counts the rounds since the latest structural stage mark |
| `review-frames VIDEO [--cut N] [--result FILE]` | Package a cut's frames for the main session, or import the reviewer's result (one for a cut older than the sources is recorded as stale, and publish refuses it) |
| `review-motion VIDEO [--cut N] [--result FILE]` | Package a cut's motion windows (frame strips around every event and uncovered move, from the cut's own frames) for the main session, or import the result as findings; stops at a round with no must-fix findings or after `motion_rounds` (2), recording the rest on the cut as known issues |
| `review-status VIDEO ROLE unavailable|waived [--reason TEXT]` · `review-status VIDEO listen passed|waived --reason TEXT [--at m:ss.s,…]` · `review-status VIDEO approval passed --cut N --reason TEXT` | Explicit review limitation/authorization; ROLE is a script reviewer, `frames` (alias `frame`) or `motion`. `listen` records the user's one listening to a mix with effects or music (publish warns without one), with the timecodes listened at: `--at`, else the ones audio-check chose for this mix. `approval` records the user's words approving cut N for its final render; `cut --quality final` and `publish` require it (`reviews.md`) |
| `narrate VIDEO [--estimate|--plan|--list|--fetch-only] [--yes]` | Script → speech, captions, word timings and explicit pause cues; one voice and speed throughout |
| `voice-check VIDEO [--all]` · `align VIDEO` | Recognition check and word alignment |
| `timeline VIDEO [--events]` | Rebuild timeline.json from its sources, after editing `cues.json`, `captions.json` or `audio/tracks.json`; `--events` lists the beat sheet: every cue's time, frame, clip and anchor |
| `lexicon add WORD --spoken TEXT [--phonemes IPA]` | Promote a pronunciation for future videos |
| `cut VIDEO [--stills-only] [--quality final] [--changelog FILE]` | Stills, changed clips and composite; says how long the clips it renders should take (from earlier cuts at that quality) before rendering, and reports actual output dimensions. Chapters without a scene show their boards. `--quality final` needs the user's approval of a cut |
| `boards VIDEO` | A stills cut of every chapter's board (`boards/boards.json`, notes from the screen notes); reports sentences with nothing on screen |
| `animatic VIDEO [--boards]` | Pictures held to the real narration with its audio, and a pacing report (runtime, chapter lengths, unchanged stretches, empty sentences) |
| `open VIDEO [CUT]` · `desk VIDEO` · `notes VIDEO [--start ID \| --resolve ID --reply TEXT]` | Protected system playback; the desk (latest cut, sentence notes, live status and replies; `serve` is an alias); numbered notes and their marks |
| `wait VIDEO [--timeout S]` · `status VIDEO [TEXT] [--busy]` | Block until a new desk note arrives (run in the background to be woken by each note); the builder's status line on the desk |
| `glossary [--term T]` | The motion glossary: the words a note can use for motion and the helper behind each (`references/desk.md`) |
| `still VIDEO CLIP T --out PNG` · `boxes VIDEO CLIP T` | Inspect a frame or named-element bounds |
| `check VIDEO [--only …] [--all] [--format F]` · `sheets VIDEO OUTDIR [--strip CLIP T]… [--windows FILE]` | Incremental render checks (pacing, a 0.5 s hold after each move, warns from the cut's clips; `--only pacing` samples stills where no clip is rendered; occluded warns when a narrated 3D part is hidden), contact sheets and label crops; strips of consecutive frames around each `--strip` time (repeatable) or each `{clip, t, frames?, fps?}` of a JSON windows file; `legend` (with video.json `legend`) warns on a colour used for two meanings, a meaning in two colours, or a reserved colour on an untagged element; tag elements with `means` |
| `look-sheet VIDEO [--format F]` | The model sheet: every element in each state (theme colours and roles, type sizes, the band, boxes, arrows, tokens, cards, close-up), drawn by the video's engine (live or Remotion) into `out/look/`, plus the video's own from `scenes/look.js`/`look.tsx`; `review-motion` includes its pages and flags a missing or stale sheet; a colour legend page when video.json declares `legend` |
| `audio VIDEO [--lufs -14]` · `export VIDEO --formats 16:9,9:16,1:1` | Finish the whole mix to its loudness and true-peak ceiling (publish and export do it too); multiple formats |
| `publish VIDEO` | Local final master, compressed web copy, poster and page, once the user has approved a cut; upload separately |
| `clean VIDEO [--dry-run] [--videos]` | Stale caches/previews; MP4 deletion is explicit and never overrides protection |
| `commit VIDEO MESSAGE` | Scoped source checkpoint; video.json `git.sign` is true, false or null/inherit |
| `capture URL VIDEO` · `asset add|list VIDEO` · `asset library VIDEO SOUND [--name ID]` · `asset restore VIDEO` · `asset list VIDEO --credits` | Assets with provenance; `library` copies a sound kit sound (an id, or `PACK:MEMBER`) into `assets/sounds/ID.ogg` with its pack, licence, creator and sha256, `restore` copies back the ones a clone lacks (Git leaves sound out), `--credits` prints the CREDITS block for the description (`references/publishing.md`) |
| `beats VIDEO TRACK` · `sfx VIDEO CUES` · `sound-lab VIDEO` | Music timing, and optional effects on cue or beat names or anchors (each mix places them on the current timeline): a cue's `type` plays its synth voice (24, `sfx.py`); `"sound": "kit"` or `"kit:ID"` plays a recording from the sound kit, landing on its transient peak and copied into `assets/sounds/` (needs `doctor --fetch --sounds` once); the lab plays each type's synth candidates and kit recordings; a kit sound plays at its trim (its synth voice's level), and `"visual"` (`cut`, `move`, `land`, `appear`) says what the picture does on the effect's frame, while the time stays the cue's. `"sound"` may also be `"asset:PATH"` (the video's own recording) or a pool (a list), and an effect with `"events"` is a stream (`audio.md`); effects with a `"source"` (made by `studio typing`) are kept |
| `music VIDEO --bed [--key Am] [--bpm 72] [--seconds S]` · `music VIDEO --remove` | An optional generated bed (slow chords, a soft pulse) as a music track the mix ducks, with its beat grid; only when the user asks for music |
| `audio-check VIDEO [--cut N]` | The soundtrack measured: sync (a kit recording by its peak; a tagged effect's picture judged in frames), audible, loud (over 13.5 dB above the voice's loudness; against the music without a narration), ducking, masking per word, the pauses guard (fails) and loudness, into `out/audio-check.json`; draws `out/audio-sheet.png` and close-ups of the hero effects, and prints about five timecodes to listen at (`references/publishing.md`) |
| `ingest FILE VIDEO` · `edit VIDEO EDL` | Transcript-based footage editing |
| `init VIDEO [--update]` · `import-tutor LESSON VIDEO` | Pin/update a kit or migrate a retired tutor timeline |
