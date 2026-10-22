---
name: studio
description: >
  Make, revise and publish narrated explainers, code lessons, motion graphics, launch films,
  pixel art and transcript-based edits of recordings. Settle the narrative, build scenes on a
  shared timeline, review cuts on the desk and revise incrementally. Use for video creation,
  watching or annotating a cut, re-voicing, rendering, publishing, or studio setup. Not for a
  plain chat explanation, slide deck, still image or document.
---

# studio

Make one video and improve it in rounds. The user approves the direction, chooses a look, watches
cuts on the desk and says when one is ready; you do the rest. The narrative decides what the viewer
learns; the timeline and recorded evidence keep narration, scenes and revisions consistent; the
subject's events are performed, with their sound, not just shown. Re-render only what changed.

Paths below are relative to this file's folder (SKILL_ROOT); use them as absolute paths. Every
command runs through `SKILL_ROOT/bin/studio`.

## Check setup first

At every invocation, before `new`, narration or rendering, run `bin/studio preflight [VIDEO]`. It
only inspects prerequisites: no installs, downloads or browser launches. Infer the engine and speech
needs from the request or the video (`--engine`, `--extra`, `--silent`); new explainers default to
live, Kokoro and alignment. Run it once per invocation. If anything is missing, this is a first run,
or the user asks for setup, follow `references/setup.md`: say what is missing and what it costs,
ask once, install what was agreed, and verify a render and a speech sample. Never silently switch to
paid narration or waive reviews to finish setup.

## Route the work

Infer these choices, or ask only what changes the result; record them in video.json:

| Choice | Meaning |
|---|---|
| Drive | `author`: the user can judge the subject; `learner`: independent subject verification is needed |
| Genre | `explainer`, `motion`, `launch`, `pixel`, `footage`; code construction is an explainer format |
| Level | `intro` (default): scaffold a few key ideas; `deep-dive`: more mechanisms, assumptions and evidence |
| Tone | `plain` (default): the polish in `references/taste/`. `comic` only when the user asks for a comic, cartoon, silly or slapstick video; "fun", "delightful" or "engaging" mean plain done well. When comic, read `references/taste/comic.md` before the narrative; otherwise never read it |
| Delivery | `polished` (default): the full stages. `session`: a modest cut of the user's own learning or work session, one review cycle, 540p, visual-first staging (`references/session.md`) |
| Destination | `private-page` (default), `share`, `social`, `files` |
| Mode | `background` (default): a builder works unattended and posts each boards cut, animatic and cut on the desk. `interactive`: the user follows on the desk while the builder works in the foreground, chapter by chapter (`references/desk.md`); only when the user asks to follow or steer |
| Engine | `live` (default for explainers): plain JS scenes drawn from t, hot-reloaded on the desk, with an optional 3D stage. `remotion`: code explainers (CodePanel, Terminal…), motion, launch and footage. `motion-canvas`: generator scenes (`references/engines.md`) |

## Read for the job

Read the files for the job at hand, not all of them. Each rule has one home; when two files seem to
disagree, the one named here for the job wins.

| Job | Read |
|---|---|
| Any job with the user | `references/gates.md`: every decision that is theirs, and how to ask |
| Setup | `references/setup.md` |
| A new explainer | `references/propose.md`, `pedagogy.md`, `levels.md`; a present-your-work `STORY.md` when the video presents finished work (`propose.md`, step 4) |
| A session video | `references/session.md`, then the explainer files |
| Build an explainer | `references/explainer.md` and the files its first paragraph names; code: `code.md` |
| Build another genre | `references/genres/<genre>.md` |
| Background build | spawn one builder with `prompts/build_agent.md` (fill VIDEO, STUDIO and SKILL_ROOT); relay its reports and the desk's address |
| Taste: look, text, motion, voice | `references/taste/look.md`, `references/taste/screen-text.md`, `references/taste/delight.md`, `references/taste/narration.md` |
| Sound | `references/audio.md` |
| Reviews, the listening, the approval | `references/reviews.md` |
| Locks, budgets, handoffs, scratch | `references/ownership.md` |
| The desk and notes | `references/desk.md`, `references/publishing.md` (the revision procedure) |
| Publish, re-voice, versions | `references/publishing.md` |
| A command's arguments | `references/commands.md` |
| Where a file or module is | `references/kit-map.md` |
| Status or resume | `research/handoff.md` (`studio handoff` writes it; `lock acquire --recover` prints it), the narrative's Decisions, SCRIPT.md, receipts, pending requests, cuts, `studio stage VIDEO --report` |
| Why something is the way it is | `DESIGN.md` |

## Rules that hold everywhere

- **The user decides** the draft, the narrative, the look and when a cut is ready for its final;
  "go ahead" covers the next gate only (`gates.md`). A final cut and publish need their recorded
  approval of a cut.
- **The desk is how the user sees the video.** Start it early and give them its address; never
  send a raw MP4 or a viewer of your own. Where no server may run, `studio review-export` writes the
  sanctioned static page (`desk.md`).
- **Evidence:** every asserted number or behavior has an Evidence row; recorded code and data
  drive the scenes.
- **Independent review:** content is judged by fresh reviewers the main session dispatches, never
  by the builder's own pass (`reviews.md`). Caps leave findings open; they never make them pass.
- **One writer per video folder**, holding the lock (`ownership.md`).
- **Scratch in `VIDEO/.studio/work/`, never /tmp**; helpers the build depends on in `sims/`, run
  with `studio run`.
- **Commit only at authorized stages** through `studio commit`; never push or upload without
  authorization.
- **Keep the kit unchanged during a video's work**: work around a missing capability in the video
  and report it.
- **Keep production out of the narration**: no tools, briefs or sessions; the subject's own code
  and product names are fine.
- **A feature ships when it makes a real video better** (`DESIGN.md`): try a change to what the
  viewer sees or hears on one real video before making it a default.

`$STUDIO_HOME` defaults to `~/studio`; videos, the sound kit cache, the learner model, `house.md`
and `lexicon.json` live there (`kit-map.md`). Explicit video choices win over series, house and kit
defaults.
