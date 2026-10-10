# papershop

A small Claude Code plugin marketplace.

| Plugin | What it does |
| --- | --- |
| [`worklog`](./worklog) | Query your Claude Code transcripts as a personal work history — time reports, per-task activity logs and runbooks, friction analysis, resume-context packs, find-and-reopen, and mining recurring corrections into CLAUDE.md rules. The heavy, many-session analyses run as dynamic workflows. |
| [`orchestrate`](./orchestrate) | Turn a rough task into a well-structured dynamic-workflow invocation. A skill that decides whether a workflow is even warranted, scopes it, fills the gaps, and fires it. Non-trivial runs end with a self-contained HTML report the human can follow and verify — task-first, with the orchestration machinery subordinate. Plus reusable invocation templates. |
| [`prose`](./prose) | Improve writing style without changing content. Two modes: `rewrite` returns clean prose silently; `review` returns a located, attributed critique that teaches. Strips AI/LLM and bad-prose signatures, moves toward careful human writing. Grounded in a curated craft corpus. |
| [`cartograph`](./cartograph) | Map any real codebase as ONE navigable, self-contained diagram. Extracts a system model from the repo's own structured sources, then renders it with a fixed visual spine: a typed-map home (scan one global layer at a time, drill per-element), column-level data lineage, and sequence/lifecycle siblings. No legends, full-bleed, zero external requests. You produce only the model; the renderer never changes. |
| [`project-triage`](./project-triage) | Classify a project or component on nine validated axes — do failures reproduce, is there real resource pressure, is latency sold, how many writers, who reads your data, what can't you take back, is the problem still moving, can a machine check correctness, what does a defect cost — and get a committal, falsifiable record of which engineering concerns dominate and which recede. Quick pass first, deep passes only where flagged; a grading mode revisits old records against what actually happened. |
| [`studio`](./studio) | Make narrated, animated videos around what the viewer should learn. Builds in the background, or with you on the desk: leave a note on a sentence and the builder answers it in place, with live scenes that redraw as they change. Polished by default: a beat sheet times picture and sound to the frame, motion is reviewed on frame sequences, and a measured mix keeps effects out of the words. Builds code explanations from recorded runs, checks scripts with fresh reviewers, settles each beat on a rough board and the pacing in an animatic before animating, and renders scenes on one timeline. Protects watched cuts and supports shared styles and pronunciation across a series. Replaces `tutor`. |
| [`screenshot-pane`](./screenshot-pane) | A mod that shows every screenshot Claude takes in a pane beside the transcript. Flip to the previous version of the same page, and point Claude at a shot with one key. Needs a terminal with the kitty graphics protocol, such as Ghostty. |

## Install

Add the marketplace once:

```
claude plugin marketplace add papersson/papershop
```

Then install either plugin:

```
claude plugin install worklog@papershop
claude plugin install orchestrate@papershop
claude plugin install prose@papershop
claude plugin install studio@papershop
claude plugin install screenshot-pane@papershop
```

`worklog` also ships a Nix flake (it has a Python engine to build); see
[`worklog/README.md`](./worklog/README.md) for the flake input and home-manager
wiring. `orchestrate` and `prose` are pure Markdown — no build, install via the
plugin command above. `studio` runs through its own `bin/studio`, which loads its own flake (see
[`studio/README.md`](./studio/README.md)). The retired `tutor` plugin's lessons rebuild with the kit
each one copied; `nix develop .#tutor` still provides that kit's system tools (Manim's cairo and
pango, espeak-ng, ffmpeg, the IBM Plex fonts).
