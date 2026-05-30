# worklog

Query your Claude Code transcripts as a personal work history. worklog keeps an
incremental DuckDB index of *distilled* transcript events — prose, files edited
vs read, commands, session titles — and exposes it through reports, ranked
search, and per-task dossiers. A companion subagent drives the index and writes
the synthesis.

The index is a lossy retrieval projection; your raw `~/.claude/projects/**/*.jsonl`
transcripts remain the lossless archive. The index stays a ranked skeleton
(what/when/where); the agent reads raw transcripts on demand when it needs detail
the index dropped (for example, the error bodies that friction analysis needs).

## Parts

- `scripts/worklog.py` — the engine. LLM-free, deterministic, incremental
  (full build ~30s, refresh ~0.2s). BM25 ranking via DuckDB's `fts` extension,
  with a keyword fallback when the extension is unavailable.
- `agents/worklog.md` — the `worklog` subagent. Covers five use cases: time
  report, task activity log (→ runbook when there's enough evidence to
  generalize), friction analysis, resume-context pack, and find-and-reopen a
  past session.

## Commands

Every subcommand refreshes the index first, so `index` is rarely needed by hand.
All accept `--json`.

| Command | What it does |
| --- | --- |
| `worklog index` | Build or refresh the index |
| `worklog report --since 7d [--until ISO] [--summarize]` | What you worked on in a window |
| `worklog search "<topic>" [--since ISO]` | Sessions matching a topic, ranked |
| `worklog task "<topic>"` | Full dossier: sessions, timeline, files, commands |

`--since` accepts `7d` / `2w` / `12h` or an ISO date.

## Install

### Nix (NixOS / nix-darwin)

Add the flake as an input and pull the package into your environment:

```nix
inputs.worklog = {
  url = "github:papersson/worklog";
  inputs.nixpkgs.follows = "nixpkgs";
};

# in a home-manager module:
home.packages = [ inputs.worklog.packages.${pkgs.system}.worklog ];
home.file.".claude/agents/worklog.md".source = "${inputs.worklog}/agents/worklog.md";
```

This builds `worklog` from `python3.withPackages [ duckdb ]` — no uv, no runtime
PyPI fetch. The `fts` extension downloads once into `$XDG_CACHE_HOME/worklog/ext`.

### Plugin (non-nix)

```
claude plugin marketplace add papersson/worklog
claude plugin install worklog@patrik-worklog
```

A SessionStart hook runs `bootstrap.sh`, which ensures `uv` is installed and
drops a `worklog` shim into `~/.local/bin`. The shim runs the bundled script via
`uv run --script`; the PEP 723 header pins duckdb.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `WORKLOG_DB` | `~/.claude/worklog.duckdb` | Index location |
| `WORKLOG_DUCKDB_EXTENSION_DIR` | duckdb default | Writable dir for the `fts` extension |

The nix wrapper sets both to a path under `$XDG_CACHE_HOME/worklog`.

## State and schema

The index is disposable — delete it and the next command rebuilds it. The schema
is versioned (`meta.schema_version`); bumping `SCHEMA_VERSION` in the script
forces a clean rebuild. Subagent sidechains (`*/subagents/*.jsonl`) are skipped
so worklog never ingests its own output.
