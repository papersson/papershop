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
| Publish | Local final master through `studio publish`; external upload per `references/publishing.md` and existing authorization |
| Revoice | Edit narration.json, narrate, voice-check, inspect affected stills and create a new cut |
| Status/resume | Read narrative Decisions, SCRIPT.md, review receipts, pending requests, cuts and `studio stage --report` |

## Ownership, review and gates

One builder owns a folder across stages: `studio lock VIDEO acquire --owner NAME` prints an
`STUDIO_OWNER` token for its commands. The main session queues mid-flight additions with
`studio request`; the owner reads them at stage boundaries and resolves incorporated IDs.
Do not launch multiple writers against the same folder. Reviewers use immutable input bundles.
Release ownership at handoff; `--recover` is for an abandoned build, never a way to displace a live one.

The main session owns independent review dispatch. A background builder can report **ready for
script review**, **ready for look choice**, or **ready for frame review** and receive results back.
It need not spawn children. Do not substitute a self-review for an unavailable independent review.

- Agree on the learning brief and chain before scripting, unless already authorized to proceed.
  The brief includes audience, model delta, key ideas, example and transfer questions.
- Run the pedagogy self-check and script diagnostics before narration. `studio review --only
  student` uses a fresh process; new teaching videos require its current pass before synthesis.
- Settle the look from stills before animation, unless already selected/authorized.
- Resolve or accept pronunciation findings and inspect low voice-check scores before an animated cut.
- Run mechanical checks and the craft pass on changed chapters before showing a cut.
- Before delivering a deep-dive/shared video, prepare `studio review-frames` and have the main
  session dispatch a fresh image-capable reviewer. Import the revision-tagged result. Frame
  review judges full-resolution crops and mechanism-sensitive transition frames, not just thumbnails.
- Every asserted number or behavior has an Evidence row. Recorded code/data drive the scenes.
- Review caps leave open findings; they do not make them pass. Record unavailable or explicitly
  user-waived checks with `studio review-status`, including the reason. A material edit invalidates
  an earlier review receipt.

Mark stages with `studio stage` (including `waiting` and `finished`). Budgets are advisory; report
scope changes and stage time. Commit only at authorized stages through `studio commit`. Never
push or upload without authorization. Keep kit changes out of individual video work; implement a
workaround in the video and report a missing kit capability. Keep production tools and process
out of the narration; subject-specific code/product names remain legitimate.

## Commands

All commands run through `bin/studio` in its pinned environment. `--help` lists full arguments.

| Command | Purpose |
|---|---|
| `doctor [VIDEO] [--fetch] [--extra kokoro|align|audio] [--net]` | Environment, package/model and network diagnostics |
| `new NAME [--source REPO] [--drive …] [--level …] [--genre …] [--engine …]` | New folder, source repository and snapshotted defaults |
| `new NAME --from VIDEO [--include RELATIVE_FILE]` | New series episode with look/lexicon and selected source/evidence dependencies |
| `variant SOURCE NAME` | Adapt a source video's evidence and scenes for a different audience |
| `lock VIDEO acquire|release|status` · `request VIDEO [TEXT] [--resolve ID]` | One writer and a pending-request queue |
| `stage VIDEO NAME [--kind local|structural] [--summary TEXT]` · `stage VIDEO --report` | Timing and revision refactoring log |
| `check VIDEO --only script|code-source` | Source/text checks before a browser or timeline exists |
| `steps VIDEO STEPS.json` | Execute full-file program versions and record source/output evidence |
| `review VIDEO ROUND [--only student|expert|editor] [--narrative FILE]` | Isolated, revision-bound script/narrative review |
| `review-frames VIDEO [--cut N] [--result FILE]` | Package frames for the main session, or import a fresh reviewer result |
| `review-status VIDEO ROLE unavailable|waived [--reason TEXT]` | Explicit review limitation/authorization |
| `narrate VIDEO [--estimate|--plan|--list|--fetch-only] [--yes]` | Script → speech, captions, word timings and pause cues |
| `voice-check VIDEO [--all]` · `align VIDEO` | Recognition check and word alignment |
| `lexicon add WORD --spoken TEXT [--phonemes IPA]` | Promote a pronunciation for future videos |
| `cut VIDEO [--stills-only] [--quality final] [--changelog FILE]` | Stills, changed clips and composite; reports actual output dimensions |
| `open VIDEO [CUT]` · `serve VIDEO` · `notes VIDEO` | Protected system playback, review page, numbered feedback |
| `still VIDEO CLIP T --out PNG` · `boxes VIDEO CLIP T` | Inspect a frame or named-element bounds |
| `check VIDEO [--only …] [--all] [--format F]` · `sheets VIDEO OUTDIR` | Incremental render checks, contact sheets and label crops |
| `audio VIDEO` · `export VIDEO --formats 16:9,9:16,1:1` | Audio finish and multiple formats |
| `publish VIDEO` | Local final master, compressed web copy, poster and page; upload separately |
| `clean VIDEO [--dry-run] [--videos]` | Stale caches/previews; MP4 deletion is explicit and never overrides protection |
| `commit VIDEO MESSAGE` | Scoped source checkpoint; video.json `git.sign` is true, false or null/inherit |
| `capture URL VIDEO` · `asset add|list VIDEO` | Assets with provenance |
| `beats VIDEO TRACK` · `sfx VIDEO CUES` · `sound-lab VIDEO` | Music timing and optional effects |
| `ingest FILE VIDEO` · `edit VIDEO EDL` | Transcript-based footage editing |
| `init VIDEO [--update]` · `import-tutor LESSON VIDEO` | Pin/update a kit or migrate a retired tutor timeline |

## Durable files and personal defaults

`SCRIPT.md` owns narration and its learning brief; narrative Decisions own settled direction.
`narration.json` owns effective voice/timing settings. `sims/` and `data/` hold evidence.
`timeline.json` is generated. `research/` holds reviews, snapshots, timing and pending requests.
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
