---
name: studio
description: >
  Create and revise narrated explainer videos. Develop the story with the user, shoot chapters
  in parallel on one timeline, and review versions on a local desk with notes on sentences.
  Use for video creation, narration, rendering, desk feedback, publishing and Studio setup.
---

# Studio

Make the explanation clear, perform its important events with sound, and get it onto the desk
quickly. The user develops the story with you and judges the video by watching it.

Use the absolute path to this folder as SKILL_ROOT. Run commands through `SKILL_ROOT/bin/studio`.
VIDEO is a folder containing `video.json`; new videos go under `$STUDIO_HOME`, default `~/studio`.
Run `studio preflight [VIDEO]` once before production. It reads prerequisites without installing
anything. If something is missing, use the setup guidance in `references/kit.md`.

## Develop the story, with the user

Read `references/taste.md` and `references/story.md`. Ask only what changes the story and cannot
be inferred. Default to an undergraduate explanation with three or four ideas, one small example
and few numbers. Put the level and tone into ordinary sentences in the brief.

Show a draft quickly. If the user asked for a draft first, show it in chat before production.
First run `/elicit:elicit` on the request and known context (or the short fallback in `story.md`), then convert its panel and brief into `research/brief.md`: the viewer, one question, ideas, protagonist and stake, hero moments
with picture and sound, omissions, length and level. Write `SCRIPT.md` with a beat table,
narration and screen notes. Draw rough boards that make the picture and its scale visible.

Run `studio reel VIDEO` for boards held to the real narration and its pacing report. Start
`studio desk VIDEO` and give the user its address within minutes of the first draft. Run
`studio panel VIDEO` once: expert, viewer and editor read the brief and script in parallel.
Bring their findings and uncertainties to the user alongside the reel. Revise the story together.

**Decision 1 is story lock.** Record the user's agreement in the brief. Existing authorization
counts. Once the story is locked, shoot it without further routine approval stops.

## Shoot, in one go

Read `references/shoot.md`; use `references/kit.md` for commands and scene APIs. Run
`studio shoot VIDEO`. It narrates with the configured voice, rebuilds the timeline and writes
one short chapter job in `research/shoot/<clip>.md`.

Use the main session's Agent tool to spawn one agent per chapter in parallel, each with that
job and the taste file. Each agent writes only `scenes/<clip>.js`, `cues/<clip>.json` and
`data/<clip>/`, runs `studio check VIDEO --chapter CLIP`, and inspects its rendered frames.
A needed shared change comes back to you to apply. Live supplies the code editor, terminal and
program-window components as well as diagrams and 3D.

Build the performed hero moments during the shoot. Picture and sound use the same named cue.
Keep one voice and speed, readable subjects that fill the frame, and time for each idea to settle.

As chapters land, apply their reported shared changes and sound plans. Run the voice check,
build the timeline and make one `studio cut VIDEO`. Aim for a first playable version on the desk
10–15 minutes after story lock. Measure with `studio stage`; report actual elapsed time.

Make `studio review-pack VIDEO --chapter CLIP` for every chapter. Dispatch one reviewer per
chapter in parallel to inspect motion and frames together, once. Import their findings with
`studio suggest VIDEO FILE`. They appear as suggested notes that the user accepts or dismisses.
Review findings are plain files under `research/reviews/`; they never authorize production.

## Review on the desk

Read `references/desk.md`. Keep the desk open on the computer. The user watches, leaves notes
on sentences and sees your replies. Keep `studio wait VIDEO` running in the background while
working so new notes reach you. A whole-story comment in chat deserves a whole-story response.

Take each accepted note, make the smallest coherent change, run the relevant checks and put a
new version on the desk in minutes. Use cached narration and incremental cuts. Keep your status
current and answer the note with what changed. Continue through the requested work.

**Decision 2 is ship it.** After the user says it, run `studio publish VIDEO --by "NAME"`.
This records who decided and when in `SHIP.md`, renders the final, finishes the mix and writes
the local master, web page, poster and colophon. Upload only to a destination the user requested.

## Keep the work understandable

Keep `timeline.json` generated. Its sources are narration, chapter cues, captions and audio
tracks. Keep source evidence and asset provenance in the video, and keep production details out
of the spoken explanation. Frames are pure functions of time, so stills, cuts and checks agree.

The main session owns shared files. Chapter agents own disjoint files. Commands that change
shared products wait on a file lock. Timing records measure story, shoot, desk, waiting and
finished; they impose no work limit.

Use `studio commit VIDEO "message"` for source checkpoints and `studio clean VIDEO --dry-run`
to inspect expendable caches. Keep the kit unchanged while making a video. Put reproducible
helpers in `sims/` or the chapter's data folder and run them through `studio run`.

After the video, append lasting lessons from the user's notes to the last section of
`references/taste.md`. Preserve the note and its reason. Read `references/taste/comic.md` only
when the user asks for comedy. For other kinds of video, use `references/by-hand.md`.

The five working references are `taste.md`, `story.md`, `shoot.md`, `desk.md` and `kit.md`.
`DESIGN.md` records the reasons behind the tools.
