# papershop

A small Claude Code plugin marketplace.

| Plugin | What it does |
| --- | --- |
| [`worklog`](./worklog) | Query your Claude Code transcripts as a personal work history — time reports, per-task activity logs and runbooks, friction analysis, resume-context packs, find-and-reopen, and mining recurring corrections into CLAUDE.md rules. The heavy, many-session analyses run as dynamic workflows. |
| [`orchestrate`](./orchestrate) | Turn a rough task into a well-structured dynamic-workflow invocation. A skill that decides whether a workflow is even warranted, scopes it, fills the gaps, and fires it — plus reusable invocation templates. |
| [`prose`](./prose) | Improve writing style without changing content. Two modes: `rewrite` returns clean prose silently; `review` returns a located, attributed critique that teaches. Strips AI/LLM and bad-prose signatures, moves toward careful human writing. Grounded in a curated craft corpus. |

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
