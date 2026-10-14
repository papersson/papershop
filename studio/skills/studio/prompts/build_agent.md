Build the approved explainer at VIDEO={{path}} using STUDIO={{path to bin/studio}}.
The skill's files are under SKILL_ROOT={{the folder holding SKILL.md}}; use absolute paths from it
(SKILL_ROOT/references/…, SKILL_ROOT/kit/src/studio_kit/…), never paths relative to your cwd.
The main session owns user communication and independent review dispatch. You are the only writer.

Read SKILL_ROOT/references/explainer.md and the files its first paragraph names (pedagogy, levels,
gates, ownership, reviews, the taste files), the video's narrative, learner model and
research/house.md. For code read references/code.md; for sound, references/audio.md. If video.json
tone is comic, read references/taste/comic.md too. Where a command or a file lives is in
references/kit-map.md; read it before reading kit code to answer a question. Keep the existing
headings in SCRIPT.md. Honor the narrative's charter and Decisions, and current user authorization.

Ownership, budgets, the hard stop, handoffs, scratch and long passes are in references/ownership.md:
claim the lock and use its STUDIO_OWNER token; if `lock acquire --recover` prints a handoff, start
from its Next list; read pending requests at each stage; obey a STOP (exit 3) by writing the handoff
and reporting; write `studio handoff VIDEO --notes "…"` at every stage boundary and before you stop
for any reason. Scratch goes in VIDEO/.studio/work, never /tmp; run helpers with `studio run`.
Do not spawn additional writers in this folder. Checkpoint only at authorized stages through
studio commit; do not push.

The user sees the video on the desk (references/gates.md): start `studio desk VIDEO` early, and
report its address with each boards cut, animatic and cut, so the main session can pass it on.
Never render a final cut or publish without the user's recorded approval of a cut; previews go on
until they give it.

Follow the stages in the table at the top of references/explainer.md. Where it names a decision
for fresh reviewers or the user (script review, the look, motion review, frame review), stop and
report ready for that decision: for motion review, run `studio review-motion VIDEO` and include the
manifest; for frame review, run `studio sheets VIDEO VIDEO/out/sheets` and
`studio review-frames VIDEO` and include the manifest. The reviewer contract and each review's stop
rule are in references/reviews.md: never replace an independent review with your own pass or claim
a reviewer ran when it did not, never ask for a round past the cap, and a cap never makes unresolved
errors pass. Keep your context small: give frame inspection to sub-agents that return findings as
text (clip, time, element, what is wrong), not images.

Report the desk's address and the cut, actual width×height/fps, quality, duration (main/sidebars),
model delta, evidence, reviews and waivers, voice results, changed chapters, late requests, stage
times, open findings and last checkpoint. Release ownership when handing the folder back, with a
current handoff if the video is not finished.
