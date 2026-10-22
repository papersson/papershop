# worklog

Query your Claude Code transcripts as a personal work history. worklog keeps an
incremental DuckDB index of *distilled* transcript events — prose, files edited
vs read, commands, tool names (incl. MCP), session titles — and exposes it through reports, ranked
search, and per-task dossiers. A companion skill drives the index and writes the
synthesis.

The index is a lossy retrieval projection; your raw `~/.claude/projects/**/*.jsonl`
transcripts remain the lossless archive. The index stays a ranked skeleton
(what/when/where); the skill reads raw transcripts on demand when it needs detail
the index dropped (for example, the error bodies that friction analysis needs).

## Parts

- `scripts/worklog.py` — the engine. LLM-free, deterministic, incremental
  (build and refresh time depend on transcript volume). BM25 ranking via DuckDB's `fts` extension,
  with a keyword fallback when the extension is unavailable.
- `skills/worklog/SKILL.md` — the `worklog` skill. Covers six use cases: time
  report, task activity log (→ runbook when there's enough evidence to
  generalize), friction analysis, resume-context pack, find-and-reopen a past
  session, and mining recurring corrections into CLAUDE.md rules. It gates each
  request: cheap one-context queries run inline against the engine; the heavy
  many-session analyses (friction analysis, rule-mining) fan out as a dynamic
  workflow — one agent per session reading raw transcripts — to avoid the
  agentic laziness and self-preferential bias of doing it all in one context.

## Commands

Every subcommand refreshes the index first, so `index` is rarely needed by hand.
The query subcommands (`report`, `search`, `task`) accept `--json`.

| Command | What it does |
| --- | --- |
| `worklog index` | Build or refresh the index |
| `worklog report --since 7d [--until ISO] [--summarize] [--json]` | What you worked on in a window |
| `worklog search "<topic>" [--since ISO] [--json]` | Sessions matching a topic, ranked |
| `worklog task "<topic>" [--json]` | Full dossier: sessions, timeline, files, commands |

`--since` accepts `7d` / `2w` / `12h` or an ISO date.

## Install

### Nix (NixOS / nix-darwin)

Add the flake as an input and pull the package into your environment:

```nix
inputs.worklog = {
  url = "github:papersson/papershop";
  inputs.nixpkgs.follows = "nixpkgs";
};

# in a home-manager module:
home.packages = [ inputs.worklog.packages.${pkgs.system}.worklog ];
home.file.".claude/skills/worklog/SKILL.md".source = "${inputs.worklog}/worklog/skills/worklog/SKILL.md";
```

This builds `worklog` from `python3.withPackages [ duckdb ]` — no uv, no runtime
PyPI fetch. The `fts` extension downloads once into `$XDG_CACHE_HOME/worklog/ext`.

### Plugin (non-nix)

```
claude plugin marketplace add papersson/papershop
claude plugin install worklog@papershop
```

A SessionStart hook runs `bootstrap.sh`, which ensures `uv` is installed and
drops a `worklog` shim into `~/.local/bin`. The shim runs the bundled script via
`uv run --script`; the PEP 723 header pins duckdb.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `WORKLOG_DB` | `~/.claude/worklog.duckdb` | Index location |
| `WORKLOG_DUCKDB_EXTENSION_DIR` | duckdb default | Writable dir for the `fts` extension |

The nix wrapper points both at `$XDG_CACHE_HOME/worklog` — `WORKLOG_DUCKDB_EXTENSION_DIR`
unconditionally, `WORKLOG_DB` as a default that an already-set value overrides.

## State and schema

The transcript projection is rebuildable. The schema is versioned
(`meta.schema_version`); bumping `SCHEMA_VERSION` forces a clean rebuild of that
projection. Schema 5 also records event UUIDs, human/SDK/system/tool-result
provenance, tool IDs, explicit path arguments, and subagent sidechains. Tool
result bodies are still omitted, but their timestamps are retained. Reports and
search exclude sidechains and injected messages, preventing generated worklog
reports from re-entering retrieval results.

`session_runs` holds explicit host/task/fallback annotations, and `repositories`
holds checkout roots discovered from event working directories on the current
filesystem. These tables survive schema rebuilds. Back up `session_runs` before
deleting the database; its annotations cannot be reconstructed from transcripts.

## Workspace audit

`queries/workspace-audit.sql` computes one row per retained session in a rolling
three-month window. It deduplicates event UUIDs and tool IDs, counts human
messages separately from SDK jobs, includes subagent tool activity, and records
elapsed span, longest inter-human-message gap, and inter-event time capped at
five and fifteen minutes. Neither capped time nor elapsed span measures human
attention. Overlapping sessions also overlap in the summed totals.

Run DuckDB directly through Nushell; the helper only executes the saved SQL:

```nu
with-env {WORKLOG_DB: ($env.HOME | path join .claude worklog.duckdb)} {
    uv run worklog/scripts/worklog.py index
}
nu worklog/queries/workspace-audit.nu ~/drafts/workspace-audit
# Fixed windows without changing the SQL:
nu worklog/queries/workspace-audit.nu ~/drafts/workspace-pilot \
    --since 2026-10-23T00:00:00Z --until 2026-11-06T00:00:00Z
```

The helper writes `sessions.json` (including sorted path inventories and
dependency evidence) and `summary.json`. Outputs contain private local paths
and command excerpts; keep them outside the repository. The helper always reads
`~/.claude/worklog.duckdb`, independent of the Nix wrapper's cache default.

The five groups are behavioral proxies: no human messages; conversation only;
at most three instructions with tools; more instructions with at least ten main
tool calls per instruction and a gap of at least thirty minutes; remaining
interactive/mixed work. Dependency flags are independent of the groups. A
browser command is a portability question, not automatically a laptop lock-in.

Native file tool arguments are read/write evidence. Search roots and generic
MCP path arguments are references. Shell path regex matches are **candidates**:
they may occur in source strings, use an ambiguous cwd, or refer to nonexistent
files. They cannot establish all actual subprocess I/O, expand shell variables,
or see paths generated by programs. The five-way path classification gives
`~/.claude` and `~/drafts` precedence over checkout roots, then other home and
elsewhere. Deleted or moved repositories may no longer be recognized.

Host and fallback metrics require explicit annotations, for example:

```sql
INSERT INTO session_runs VALUES
  ('SESSION-UUID', 'z840', 'pilot-01', NULL)
ON CONFLICT (session) DO UPDATE SET
  execution_host=excluded.execution_host, task_id=excluded.task_id,
  fallback_reason=excluded.fallback_reason;
-- If this task later needs the laptop, mark the original remote session:
UPDATE session_runs SET fallback_reason='macOS browser login'
WHERE session='SESSION-UUID';
```

Use `local` for local sessions; unannotated sessions remain `unknown`, never
inferred remote from an SSH command. Import remote Claude transcripts under a
distinct subtree of `~/.claude/projects`, preserving session IDs and sidechain
directories, then reindex and rerun the same SQL. Amp/Codex histories require an
explicit format adapter before this index can measure them. The pilot query
counts human sessions, keeping SDK child jobs out of its denominator.

Validation: `uv run --with duckdb python -m unittest discover -s worklog/tests`.
