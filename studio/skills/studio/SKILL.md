---
name: studio
description: >
  Create and revise narrated explainer videos. Develop the story with the user, shoot chapters
  in parallel on one timeline, and review versions on a local desk with notes on sentences.
  Use for video creation, narration, rendering, desk feedback, publishing and Studio setup.
---

# Studio

Make the visuals the centerpiece: finished illustrations, continuous transformations and
full explanatory sentences. Get the film onto the desk quickly. The user develops the story with you and judges the video by watching it.

Use the absolute path to this folder as SKILL_ROOT. Run commands through `SKILL_ROOT/bin/studio`.
VIDEO is a folder containing `video.json`; new videos go under `$STUDIO_HOME/films` when that folder exists, else `$STUDIO_HOME`, default `~/studio`.
Run `studio preflight [VIDEO]` once before production. It reads prerequisites without installing
anything. If something is missing, use the setup guidance in `references/kit.md`.

## Develop the story, with the user

Read `references/taste.md` and `references/story.md`. For an origins film, historical journey,
or a request to explain a modern system through its history, also read
[`references/origins.md`](references/origins.md). Its story order and reference selection take
precedence over the lecture defaults below. Ask only what changes the story and cannot
be inferred. Otherwise default to a canonical undergraduate lecture with one small example and few numbers.
Three or four ideas is guidance, not a cap; breadth is welcome when each idea has room. Put the level and tone into ordinary sentences in the brief.

First run `/elicit:elicit` on the request and known context (or the short fallback in `story.md`).
Then show a draft quickly. If the user asked for a draft first, show it in chat before production.
Convert the panel and brief into `research/brief.md`: the viewer, story order (historical route for origins films), ideas, hero moments, the subject-appropriate visual language and any exact metaphor mapping, permitted tactile sounds (none by default), omissions, length and level. Name key points and section ends. Write `SCRIPT.md` with a beat table including breaths,
narration and screen notes. Write and revise the narration to `references/script.md`, and read it aloud before anyone else hears it. Draw rough boards that make the picture and its scale visible.

Run `studio reel VIDEO` for boards held to the real narration and its pacing report. Start
`studio desk VIDEO` and give the user its address within minutes of the first draft. Run
`studio panel VIDEO` once: expert, viewer and editor read the brief and script in parallel.
Bring their findings and uncertainties to the user alongside the reel. Revise the story together.

**Decision 1 is story lock.** Record the user's agreement in the brief. Existing authorization
counts. After lock, render three to five final-quality style frames in the real engine: opening,
chapter heroes and closing. Follow the style-frame step in `story.md`, compare beside a reference
of the same kind: the selected historical-journey reference for origins films, otherwise
3Blue1Brown for abstract subjects, Ciechanowski or Kurzgesagt for physical ones.
Apply the hard 3D admission test in `taste.md` and record the judgment. Then shoot to those frames. This is
preparation within the existing story decision, not another routine approval stop.

## Shoot, in one go

Read `references/shoot.md`; use `references/kit.md` for commands and scene APIs. Run
`studio shoot VIDEO`. It narrates with the configured voice, rebuilds the timeline and writes
one short chapter job in `research/shoot/<clip>.md`.

Use the main session's Agent tool to spawn one agent per chapter in parallel, each with that
job and the taste file. Each agent writes only `scenes/<clip>.js`, `cues/<clip>.json` and
`data/<clip>/`, runs `studio check VIDEO --chapter CLIP`, and inspects its rendered frames.
A needed shared change comes back to you to apply. Live supplies the code editor, terminal and
program-window components as well as diagrams and 3D.

Build the performed hero moments to match the accepted style frames. Sound is absent unless a
listed tactile event earns it; that picture and sound use the same named cue.
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

Take each accepted note, make the smallest coherent change (narration changes follow `references/script.md`), run the relevant checks and put a
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
to inspect expendable caches. After recording or shipping, `studio media push VIDEO`; elsewhere,
`studio media pull VIDEO`. Keep the kit unchanged while making a video. Put reproducible
helpers in `sims/` or the chapter's data folder and run them through `studio run`.

After the video, append lasting lessons from the user's notes to the last section of
`references/taste.md`. Preserve the note and its reason. Read `references/taste/comic.md` only
when the user asks for comedy. For other kinds of video, use `references/by-hand.md`.

The six working references are `taste.md`, `story.md`, `script.md`, `shoot.md`, `desk.md` and `kit.md`.
`DESIGN.md` records the reasons behind the tools.
