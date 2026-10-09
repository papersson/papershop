Build the approved explainer at VIDEO={{path}} using STUDIO={{path to bin/studio}}.
The main session owns user communication and independent review dispatch. You are the only writer.

Read references/explainer.md, references/pedagogy.md, references/style.md, the video's narrative,
learner model and research/house.md. For code read references/code.md. Keep the existing headings
in SCRIPT.md. Honor the narrative's charter and Decisions, and current user authorization.

Claim ownership with studio lock and use its STUDIO_OWNER token across commands/direct edits.
If `lock acquire --recover` prints a handoff, start from its Next list. Read pending
research/requests.md at each stage; resolve incorporated request IDs and record scope/time
changes. Do not spawn additional writers in this folder. Mark stages, including waiting and
finished. Checkpoint only at authorized stages through studio commit; do not push.

Obey the hard stop. Run `studio stage VIDEO --check` between chapters and fix rounds; when it or
a stage mark prints STOP (exit 3), write the handoff, report to the main session and do not
continue that stage. At every stage boundary, and before you stop for any reason, write
`studio handoff VIDEO --notes "…"` with what the files don't show: a half-finished chapter, a
decision and its reason, a helper and what it does. A chapter fixer (STUDIO_ROLE=fixer) writes no
handoff and edits no shared file (boards/boards.json, cues.json, captions.json, SCRIPT.md); it
reports those notes and patches to the main session.

Put scratch files and helper scripts in VIDEO/.studio/work, never /tmp; move a helper the build
depends on to sims/. Run them with `studio run VIDEO SCRIPT [ARGS…]`, not by path. Keep your
context small: give frame inspection to sub-agents that return findings as text (clip, time,
element, what is wrong), not images.

Follow the stages in the table at the top of references/explainer.md. Where it names a decision
for fresh reviewers or the user (script review, the look, frame review), stop and report ready for
that decision: for frame review, run `studio sheets VIDEO VIDEO/out/sheets` and
`studio review-frames VIDEO` and include the manifest. The main session arranges the reviewers and
the user's choice and returns them. Do not replace an independent review with your own pass or
claim a reviewer ran when it did not; a cap never makes unresolved errors pass. Determinism is
`studio check --only determinism`; there is no separate determinism command.

Report cut/path, actual width×height/fps, quality and final-quality status, duration (main/sidebars),
model delta, evidence, reviews and waivers, voice results, changed chapters, late requests, stage
times, open findings and last checkpoint. Release ownership when handing the folder back, with a
current handoff if the video is not finished.
