# papershop

A small Claude Code plugin marketplace.

| Plugin | What it does |
| --- | --- |
| [`worklog`](./worklog) | Query your Claude Code transcripts as a personal work history — time reports, per-task activity logs and runbooks, friction analysis, resume-context packs, find-and-reopen, and mining recurring corrections into CLAUDE.md rules. The heavy, many-session analyses run as dynamic workflows. |
| [`prose`](./prose) | Improve writing style without changing content. Two modes: `rewrite` returns clean prose silently; `review` returns a located, attributed critique that teaches. Strips AI/LLM and bad-prose signatures, moves toward careful human writing. Grounded in a curated craft corpus. |
| [`cartograph`](./cartograph) | Map any real codebase as ONE navigable, self-contained diagram. Extracts a system model from the repo's own structured sources, then renders it with a fixed visual spine: a typed-map home (scan one global layer at a time, drill per-element), column-level data lineage, and sequence/lifecycle siblings. No legends, full-bleed, zero external requests. You produce only the model; the renderer never changes. |
| [`project-triage`](./project-triage) | Classify a project or component on nine validated axes — do failures reproduce, is there real resource pressure, is latency sold, how many writers, who reads your data, what can't you take back, is the problem still moving, can a machine check correctness, what does a defect cost — and get a committal, falsifiable record of which engineering concerns dominate and which recede. Quick pass first, deep passes only where flagged; a grading mode revisits old records against what actually happened. |
| [`studio`](./studio) | Make narrated explainers with a shared story, a parallel chapter shoot and a local desk for sentence notes. Uses the user’s taste, Kokoro narration, recorded sound, one timeline and incremental live scenes. The user locks the story and says when to ship. |
| [`present-your-work`](./present-your-work) | Present a stretch of autonomous work to a reader who was not there, at the size the work earned: a few paragraphs in chat, a one-page memo, or an article with an appendix and a story for a `studio` video. The story is fixed on a short card before any prose, the text answers a defense's five questions and ends on the distance to the goal and the ranked next steps, a separate pass only cuts, a script checks internal labels and budgets, and a cold reader checks that the story can be retold. |
| [`elicit`](./elicit) | Rewrite a prompt into the brief a leading practitioner would write for themselves before starting, from what the model already knows. It convenes a panel of masters (the fields the result depends on, the fields best at each quality of the effect in any medium, someone who questions the premise, someone who tries to break it), shows the roster, then writes the brief in full sentences with reasons: what to start from, what is uncertain, and above all the moments and taste that would make it exceptional, ending with checks someone else could make. No research, no review agents; it never carries the prompt out. |
| [`screenshot-pane`](./screenshot-pane) | A mod that shows every screenshot Claude takes in a pane beside the transcript. Flip to the previous version of the same page, and point Claude at a shot with one key. Needs a terminal with the kitty graphics protocol, such as Ghostty. |

## Install

Add the marketplace once:

```
claude plugin marketplace add papersson/papershop
```

Then install either plugin:

```
claude plugin install worklog@papershop
claude plugin install prose@papershop
claude plugin install studio@papershop
claude plugin install screenshot-pane@papershop
claude plugin install present-your-work@papershop
claude plugin install elicit@papershop
```

`worklog` also ships a Nix flake (it has a Python engine to build); see
[`worklog/README.md`](./worklog/README.md) for the flake input and home-manager
wiring. `prose` is pure Markdown — no build, install via the
plugin command above. `present-your-work` is Markdown and one standard-library Python script, with
nothing to build. `elicit` is pure Markdown. `studio` runs through its own `bin/studio`, which loads its own flake (see
[`studio/README.md`](./studio/README.md)). The retired `tutor` plugin's lessons rebuild with the kit
each one copied; `nix develop .#tutor` still provides that kit's system tools (Manim's cairo and
pango, espeak-ng, ffmpeg, the IBM Plex fonts).
