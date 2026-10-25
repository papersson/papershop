# Shoot in parallel

Start after story lock and the style frames in `story.md`. The main session owns `research/brief.md`, `SCRIPT.md`,
`narration.json`, the boards, layout, legend, shared scene helpers and the sound mix. Keep the desk
running and mark `studio stage VIDEO shoot` so the first playable time can be measured.

Run `studio shoot VIDEO`. Kokoro is the default voice; an explicitly chosen ElevenLabs voice
remains the configured voice. The command reuses cached synthesis, rebuilds the timeline and writes
`research/shoot/<clip>.md` for every chapter. Each job contains the locked brief, its narration with
sentence ids and absolute times, beats and screen notes, the taste path and allowed commands.
It includes the chapter’s accepted `research/style-frames/manifest.json` images and the exact
permitted events from `research/sound.json` (none if absent). Inspect the images and match their
materials, light, framing and scale. Sound may accompany only a listed tactile touch.
It also includes `research/story/<clip>.md`: that chapter's hero moment as described in the elicit
material and the relevant panel principles with reasons, selected during story conversion. Keep
the full panel and rich brief in `research/elicit.md`; do not send them wholesale to every agent.

Before dispatch, settle shared visual choices from the reel: the shared object and its metaphor, legend, layout,
common helpers and any sound or typing data the chapter needs to read. A prepared typed-code plan
can already be applied by the main session. Otherwise the chapter proposes its plan in its own
data folder and reports it back. Shared work should be small enough to keep the chapter jobs
independent. The live kit supplies CodePanel, Editor, RunTerminal, ProgramWindow, Terminal and
HelperCard; all read the same typing and code-view data.

## Dispatch the chapter agents

Use the main session's agent capability. Send all chapter calls together in one message so they
start in parallel. Use one agent per chapter, each with a fresh, short context. If the tool has a
concurrency limit, fill the available slots and start the next job as a slot frees. The command
prints the jobs; it does not spawn them itself.

For Claude, use Agent (called Task in some runtimes) with `run_in_background: true`. Copy each
printed `Agent description` exactly, including its `[studio:RUN:CLIP]` tag, and require the chapter's
first tool call to be **Read on its printed unique job path**. Do not paste the job in place of that
read. The tagged background result joins session and subagent id to the lane; newer payloads can
also bind on that first Read. Later tools and SubagentStop report automatically. Start events alone
lack the description, so arrival order and working directory are never lane evidence. Use TaskOutput
or the tool's completion notification to collect each result. On runtimes without tool-event agent
ids, only exact chapter-owned paths and Studio commands naming VIDEO and CLIP are attributed;
generic commands and shared-file reads are dropped. Explicit events can supply those missing actions.
`shoot` writes `$STUDIO_HOME/.active-shoot.json` with the video, lane identities and a six-hour
expiry. One shoot is active per home; rerunning shoot replaces its tags. Completion archives the
bindings under `research/shoot/RUN/agents.json` and removes the active record. An abandoned shoot
expires; rerun shoot to renew it. Use the same STUDIO_HOME in the main Claude session and commands.
For Codex, keep explicit `studio event` calls at meaningful actions, decisions and completion.

Use this prompt, replacing the paths and clip id:

```text
Build chapter CLIP of VIDEO. First use Read on the unique job path printed by studio shoot.
Read that job, SKILL_ROOT/references/taste.md and SKILL_ROOT/references/kit.md.
The story and voice are settled. Build the chapter in one pass, including its performed hero
moment, matching the accepted style frames. Size pauses to new content; do not hold an unchanged
picture. Make the subject large enough to inspect. Use only the listed tactile sounds.

Write only VIDEO/scenes/CLIP.js, VIDEO/cues/CLIP.json and VIDEO/data/CLIP/.
Treat shared files as read-only, including the script, narration, layout, boards, timeline,
audio files and shared scene helpers. Report any needed shared change with its reason.
Place sound or typing proposals in data/CLIP/ for the main session to apply.

Run STUDIO check VIDEO --chapter CLIP and inspect the frames under
VIDEO/.cache/chapters/CLIP/. Correct deterministic errors in your own files.
Return the paths you changed, the check result, which frames you inspected, and any shared
changes needed. Do not make a cut, narrate, publish, or edit another chapter.
```

STUDIO is the absolute path to `bin/studio`.

`cues/<clip>.json` uses the same schema as `cues.json`: names mapped to absolute seconds or
narration anchors. Prefix names with the clip id, such as `s2-enter`. The timeline build merges
the chapter files and continues to read an existing `cues.json`. Duplicate names and cues placed
outside their owning chapter produce an error instead of silently overwriting another event.
The main session applies global typing cues and sound changes after chapter jobs return.

`studio check VIDEO --chapter CLIP` copies source inputs into a private work folder, rebuilds
that chapter's cues and checks its frames. It leaves the shared timeline and other chapters'
check records alone. Its report and frame samples live in `.cache/chapters/CLIP/`. A chapter can
run its own helper with `studio run VIDEO data/CLIP/build.py`; that helper must respect the same
file boundary. Do not run a shared cut or audio command from a chapter job.

## Assemble once

As each chapter lands, read its result and address a failed deterministic check in that chapter.
Apply reported changes to shared files deliberately. Reject effects not in the tactile allowlist.
Combine the permitted effects into one
file, run `studio sfx VIDEO FILE`, and apply typing plans through `studio typing` in the main
session. Rebuild the timeline after changing timing or cues.

Run `studio voice-check VIDEO`; investigate missing speech and bad pronunciation. Use
`studio align VIDEO` when recognized word timing is needed. Keep the voice and speed unchanged.
Once every chapter has landed, run `studio timeline VIDEO --events`, `studio check VIDEO`,
`studio cut VIDEO`, and `studio audio-check VIDEO`. Post the playable cut on the desk immediately.
A first version 10–15 minutes after story lock is the target; stage timing records what happened.
Keep final resolution for the user's shipping decision.

## One combined review per chapter

After the first cut, run `studio review-pack VIDEO --chapter CLIP` for each chapter. These commands
can run concurrently because each writes its own folder under `research/reviews/cutN/CLIP/`.
Wait for the bundle paths, then dispatch one reviewer per chapter together using the Agent tool:

```text
Read BUNDLE/PROMPT.md and review the saved chapter once. Inspect its frame stills beside the accepted style frames and reference, and motion
windows together, and listen at hero moments when a player is available. Use the taste file.
Write BUNDLE/findings.json in the documented shape. State any evidence you could not inspect.
Do not edit video sources. Return the findings file path and a short account of what you saw.
```

The bundle holds frame images, motion strips, sound sheets, the saved script and timeline, and a
manifest. Findings use absolute video seconds or a sentence id from that cut. Import each file
with `studio suggest VIDEO BUNDLE/findings.json`. The desk labels the resulting notes `review`
and `suggested`. The user accepts or dismisses them. Continue with `desk.md`; there is one pass,
with no automatic repeat grading or verdict that gates a cut.
