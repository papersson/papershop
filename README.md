# papershop

A small Claude Code plugin marketplace.

| Plugin | What it does |
| --- | --- |
| [`worklog`](./worklog) | Query your Claude Code transcripts as a personal work history — time reports, per-task activity logs and runbooks, friction analysis, resume-context packs, find-and-reopen, and mining recurring corrections into CLAUDE.md rules. The heavy, many-session analyses run as dynamic workflows. |
| [`prose`](./prose) | Improve writing style without changing content. Two modes: `rewrite` returns clean prose silently; `review` returns a located, attributed critique that teaches. Strips AI/LLM and bad-prose signatures, moves toward careful human writing. Grounded in a curated craft corpus. |
| [`cartograph`](./cartograph) | Map any real codebase as ONE navigable, self-contained diagram. Extracts a system model from the repo's own structured sources, then renders it with a fixed visual spine: a typed-map home (scan one global layer at a time, drill per-element), column-level data lineage, and sequence/lifecycle siblings. No legends, full-bleed, zero external requests. You produce only the model; the renderer never changes. |
| [`project-triage`](./project-triage) | Classify a project or component on nine validated axes — do failures reproduce, is there real resource pressure, is latency sold, how many writers, who reads your data, what can't you take back, is the problem still moving, can a machine check correctness, what does a defect cost — and get a committal, falsifiable record of which engineering concerns dominate and which recede. Quick pass first, deep passes only where flagged; a grading mode revisits old records against what actually happened. |
| [`studio`](./studio) | Make narrated explainers with a shared story, a parallel chapter shoot and a local desk for sentence notes. Uses the user’s taste, Kokoro narration, recorded sound, one timeline and incremental live scenes. The user locks the story and says when to ship. |
| [`present-your-work`](./present-your-work) | Present finished work to the person who asked for it, in the chat, in under a minute, the way a colleague would tell them. The text opens on the goal and what is now true, says why the work was done this way and what its key idea is, puts the one thing that could change their mind beside the answer, and ends on what they now have to decide. It explains the work rather than proving it. A one-second script flags private labels, budgets, superlatives, log-like telling and the marks of machine-written prose. |
| [`elicit`](./elicit) | Rewrite a prompt into the brief a leading practitioner would write for themselves before starting, from what the model already knows. It convenes a panel of masters (the fields the result depends on, the fields best at each quality of the effect in any medium, someone who questions the premise, someone who tries to break it), shows the roster, then writes the brief in full sentences with reasons: what to start from, what is uncertain, and above all the moments and taste that would make it exceptional, ending with checks someone else could make. No research, no review agents; it never carries the prompt out. |
| [`screenshot-pane`](./screenshot-pane) | A mod that shows every screenshot Claude takes in a pane beside the transcript. Flip to the previous version of the same page, and point Claude at a shot with one key. Needs a terminal with the kitty graphics protocol, such as Ghostty. |
| [`polish-ui`](./polish-ui) | Autonomously hill climb a UI you already like within a scope-sized budget of minutes, hours or days. Preserve its character, evaluate focused candidates with measured checks and independent visual review, and continue until the budget or an evidenced plateau. Returns before/after evidence and a reviewable diff. |
| [`walk-me-through`](./walk-me-through) | Explain one mechanism as a local click-through page. Each click changes exactly one thing on a stage drawn from the real data, the eye has one place to look (the subject bright, the rest quiet), and one caption line of at most 12 words says what it means. It decides first whether a sentence would do, writes the page as a click list for approval, builds it with a small engine (no dependencies, opens from disk), and checks it with a script that enforces the rules at three window sizes, screenshots, an attention reviewer and a fresh reader. |
| [`correctness`](./correctness) | Find the bugs example tests cannot reach in stateful, concurrent or message-driven code. Research a system under test into a catalog of testable properties and assumptions with evidence, fake the dependencies that cannot be run and verify the fakes, build a workload that explores it with faults (a Hegel state machine, or Bombadil for web and terminal UIs), review how well its inputs explore, check the properties with mutation testing, and audit stored data against them. Follows the terminology and strategies of Antithesis's public agent skills, without needing the product. |

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
claude plugin install polish-ui@papershop
claude plugin install walk-me-through@papershop
claude plugin install correctness@papershop
```

`worklog` also ships a Nix flake (it has a Python engine to build); see
[`worklog/README.md`](./worklog/README.md) for the flake input and home-manager
wiring. `prose` is pure Markdown — no build, install via the
plugin command above. `present-your-work` is Markdown and one standard-library Python script, with
nothing to build. `elicit` and `correctness` are pure Markdown. `polish-ui` is Markdown and JSON, with no build step; it uses the target project's preview tools. `walk-me-through` is Markdown, one JavaScript and one CSS file, and standard-library Python scripts that drive an installed Chrome or Chromium. `studio` runs through its own `bin/studio`, which loads its own flake (see
[`studio/README.md`](./studio/README.md)). The retired `tutor` plugin's lessons rebuild with the kit
each one copied; `nix develop .#tutor` still provides that kit's system tools (Manim's cairo and
pango, espeak-ng, ffmpeg, the IBM Plex fonts).
