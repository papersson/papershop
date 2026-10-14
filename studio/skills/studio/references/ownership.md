# Ownership, stages and long runs

How a builder holds a video, marks its stages, stops, hands over and keeps its scratch. These rules
hold for every genre.

## One owner

One builder owns the folder: `studio lock VIDEO acquire --owner NAME`, then use the printed
`STUDIO_OWNER` for its commands. Keep ownership across stages and direct file edits. The main
session queues additions with `studio request VIDEO "text"`; read pending requests at stage
boundaries and resolve each incorporated request with `studio request VIDEO --resolve ID`.
Explicit stop/correction applies immediately. Reviewers use snapshots, never edit the folder.
Release the lease when handing ownership back; `acquire --recover` is for an abandoned build, never
a way to displace a live one. Do not launch two writers against the same folder.

## Stages and budgets

Mark stages with `studio stage VIDEO NAME`; `waiting` excludes user wait from active budgets and
`finished` closes timing. video.json `budget` holds minutes: `first_cut`, `round` and
`structural_round` for the scopes, and a stage's name as it is marked (`"scenes": 30`) for a
budget on that stage alone: every run of it since the latest round mark (the first cut, before
one), resumed runs included; there are no per-stage defaults. Over-budget reports are advisory:
re-estimate changed scope and report where time went, without skipping correctness. Commit at
authorized stages through `studio commit`. Never push a video's repository without authorization.

One exception is a hard stop. In background mode, a stage with its own budget in video.json stops
at twice that budget: `studio stage` prints a STOP line, and `studio stage VIDEO --check` (which
marks nothing and exits 3 when stopped) says the same between chapters. Run the check between
chapters and fix rounds of a long stage. On STOP, write a handoff, report to the main session and
do not continue. The main session decides whether to raise that stage's budget or stop there. The
`first_cut` and `round` defaults are not calibrated against real builds, so they never stop a build,
and nothing stops in interactive mode, where the user is watching.

## Handoffs

In background mode, write `studio handoff VIDEO --notes "…"` at every stage boundary and before
stopping. It writes `research/handoff.md`, a brief a fresh builder can act on without your
transcript: the owner, the stage against its budget, the last cut and its open notes, reviews in
flight, pending requests, the next commands, and your notes on what the files don't show (a
half-finished chapter, a decision and its reason, a helper and what it does). `studio lock VIDEO
acquire --recover` prints the brief to whoever takes over, its state read from the files at that
moment (so a stop lifted since is gone) with your notes and when you wrote them. The brief names
paths relative to the video and holds no host, so it is committed with the sources and still reads
right on another machine. A builder can stop without warning (a usage limit stopped two in one
week), so a stale handoff costs the next builder an hour of reading transcripts.

## Scratch and helpers

Scratch goes in `VIDEO/.studio/work/`, never /tmp: probes, intermediate frames, a helper being
tried out, a reviewer's raw result. Inside the video it survives a restart, but Git ignores it and
fork leaves it behind. A helper the build depends on, or one a later builder or a fork should rerun,
moves to `sims/`, which is committed and forked with the sources and holds the video's scripts:
evidence extraction and build helpers alike. `sims/` is rerunnable build code, not a history of
rounds: a one-off patch for round 3 stays in `.studio/work/`, and a helper that would overwrite
files other steps now own says so in its first line. Run either with
`studio run VIDEO SCRIPT [ARGS…]`. It uses the kit's Python with the kit importable (Pillow always,
numpy and soundfile once narration is set up; system `python3` has none of them), runs in the video's folder with stdin closed,
and goes through the allowlisted `bin/studio`, so no path trick is needed to get past a sandbox.
`.mjs`/`.js` scripts run with node, without the engines' packages on their import path. Paths given
to `studio` commands are resolved against the directory you call them from.

## Long passes

A fix round or polish pass over a whole video is where builds run long and builders run out of
context.

- **Split by chapter when the main session can run several builders.** The lock is per video, and
  every changing command takes a short operation lock that fails, without waiting, while another
  runs (`still`, `boxes` and `duration` wait their turn for up to two minutes instead). So the main
  session holds the lock (`studio lock VIDEO acquire --owner main`) and starts each chapter fixer
  with its `STUDIO_OWNER` token, `STUDIO_ROLE=fixer` and a disjoint set of files: its own
  `scenes/<clip>.js` and nothing shared. A fixer edits only those files and checks its frames with
  `studio still` on its own clips. It never runs `cut`, `check`, `narrate`, `timeline`, `stage`,
  `commit` or `handoff` (with `STUDIO_ROLE=fixer`, `handoff` refuses), and never edits a shared
  file: SCRIPT.md, `boards/boards.json` (every chapter's boards are in that one file), `cues.json`,
  `captions.json`, `audio/tracks.json`, `data/` manifests other chapters read, or a helper several
  scenes import. A change to a shared file, and the notes a handoff would hold, come back to the
  main session in the fixer's report, as a patch with its reason. When every fixer has reported,
  the main session applies the patches, runs `studio check`, makes one cut and writes the handoff.
- **Give each sub-agent a brief, not the whole thread.** A fixer or researcher forked with the
  main session's full history carries days of context it does not need; write what it must know.
- **Keep each builder's context small.** Hand frame inspection to sub-agents. A sub-agent reads
  the stills, sheets or strips and returns findings as text (clip, time, element, what is wrong),
  not images. A builder that reads every frame itself fills its context with pictures and stops
  mid-pass.
- **Long renders run in the background, and say how long.** Before a render that takes more than a
  few minutes, say the estimate `studio cut` prints; run it in the background and post one status
  line (`studio status VIDEO "…" --busy`) rather than a message a minute. When the user asks to be
  left alone ("sleep for two hours"), check back once.
