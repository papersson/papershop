# cc-plugins

A small Claude Code plugin marketplace.

| Plugin | What it does |
| --- | --- |
| [`worklog`](./worklog) | Query your Claude Code transcripts as a personal work history — time reports, per-task activity logs and runbooks, friction analysis, resume-context packs, find-and-reopen, and mining recurring corrections into CLAUDE.md rules. The heavy, many-session analyses run as dynamic workflows. |
| [`orchestrate`](./orchestrate) | Turn a rough task into a well-structured dynamic-workflow invocation. A skill that decides whether a workflow is even warranted, scopes it, fills the gaps, and fires it — plus reusable invocation templates. |

## Install

Add the marketplace once:

```
claude plugin marketplace add papersson/cc-plugins
```

Then install either plugin:

```
claude plugin install worklog@patrik-plugins
claude plugin install orchestrate@patrik-plugins
```

`worklog` also ships a Nix flake (it has a Python engine to build); see
[`worklog/README.md`](./worklog/README.md) for the flake input and home-manager
wiring. `orchestrate` is pure Markdown — no build, install via the plugin
command above.
