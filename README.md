# papershop

A small Claude Code plugin marketplace.

| Plugin | What it does |
| --- | --- |
| [`worklog`](./worklog) | Query your Claude Code transcripts as a personal work history — time reports, per-task activity logs and runbooks, friction analysis, resume-context packs, find-and-reopen, and mining recurring corrections into CLAUDE.md rules. The heavy, many-session analyses run as dynamic workflows. |
| [`orchestrate`](./orchestrate) | Turn a rough task into a well-structured dynamic-workflow invocation. A skill that decides whether a workflow is even warranted, scopes it, fills the gaps, and fires it. Non-trivial runs end with a self-contained HTML report the human can follow and verify — task-first, with the orchestration machinery subordinate. Plus reusable invocation templates. |
| [`prose`](./prose) | Improve writing style without changing content. Two modes: `rewrite` returns clean prose silently; `review` returns a located, attributed critique that teaches. Strips AI/LLM and bad-prose signatures, moves toward careful human writing. Grounded in a curated craft corpus. |
| [`cartograph`](./cartograph) | Map any real codebase as ONE navigable, self-contained diagram. Extracts a system model from the repo's own structured sources, then renders it with a fixed visual spine: a typed-map home (scan one global layer at a time, drill per-element), column-level data lineage, and sequence/lifecycle siblings. No legends, full-bleed, zero external requests. You produce only the model; the renderer never changes. |
| [`project-triage`](./project-triage) | Classify a project or component on nine validated axes — do failures reproduce, is there real resource pressure, is latency sold, how many writers, who reads your data, what can't you take back, is the problem still moving, can a machine check correctness, what does a defect cost — and get a committal, falsifiable record of which engineering concerns dominate and which recede. Quick pass first, deep passes only where flagged; a grading mode revisits old records against what actually happened. |

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
```

`worklog` also ships a Nix flake (it has a Python engine to build); see
[`worklog/README.md`](./worklog/README.md) for the flake input and home-manager
wiring. `orchestrate` and `prose` are pure Markdown — no build, install via the
plugin command above.
