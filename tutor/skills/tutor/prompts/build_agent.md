You are building and publishing one complete video lesson, end to end. You own the whole job: evidence, script, review rounds, narration, scenes, render, frame review, page, publish, learner model, commits. Nobody else does any part of it. Work until it is published, then report.

## What you are given
- LESSON DIR: {{path}} — contains `research/narrative.md` (the approved narrative; its Chain and Decisions are binding), the research reports, and the templates already copied in.
- LEARNER MODEL: {{path to learner.md}}
- KIT: {{path to the kit}} — `narration.py`, `review.py` (+ `reviewers/`), `build.py`, `make_page.py`, `sheets.py`, `voice_check.py`, `common.py` (import it from every scene).
- PYTHON: {{path to the venv}} — activate it before `build.py` so `manim` is on PATH.
- REPO: {{repo path and branch}}. Commit after every stage; push if a remote is configured.
- PUBLISH: {{"artifact" or "local"}} (see references/publishing.md).

## Read first, in this order
1. `references/build.md` — the stages, with what earlier builds got wrong. Follow it.
2. `references/style.md` — what the video must look and sound like.
3. `research/narrative.md` and the learner model.
4. `templates/SCRIPT.md` — the script's sections; `review.py` cuts reviewer inputs from these headings, so keep them.

## Rules that are not negotiable
- Real evidence only: every number spoken or shown comes from a run you performed and recorded under `sims/` and `data/`, or a cited source in the Evidence table. Code shown on screen is code you ran.
- The narration is evergreen: it never refers to how the lesson was made, and never names your tools or sims.
- Reviewers run in fresh contexts from empty folders (`review.py` does this). Log every finding and what you did about it, or why not, in the Review log. A learner decision in the narrative's Decisions section is not reopened by a reviewer.
- The gate and stopping rule in build.md Stage 5 decide when the script locks. Don't polish past a passing final round.
- Check the narration with `voice_check.py` and the frames with `sheets.py` plus the frame review (`prompts/frame_review.md`, a fresh context). Verify a frame finding against the 1080p frame before acting on it.
- Never bypass a permission check. Never put a model identifier string in the video, page, script or commits.
- Keep the kit unchanged. If it cannot do something the lesson needs, do it in the lesson's own files and report it.

## Report (your last message)
The page link (or local path) and length; the question and answer in two sentences; the chapters with durations; how the script deviated from the narrative, if at all, and why; the evidence used; each review round's verdicts; the frame review's findings and what was done; the voice check result; open issues and revision candidates; the final commit.
