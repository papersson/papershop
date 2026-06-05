#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["duckdb>=1.0"]
# ///
"""
worklog.py — query Claude Code transcripts as a work history.

A persistent, incrementally-built DuckDB index of *distilled* transcript events
feeds three retrieval shapes. The script is LLM-free and deterministic; synthesis
is done by the caller (the `worklog` agent) or, headless, by `report --summarize`
shelling out to `claude -p`.

Subcommands (all auto-refresh the index first; all accept --json):
  index                                build/refresh the index
  report  --since --until [--summarize]   what you worked on in a window
  search  QUERY [--since]                 sessions matching a topic, ranked (BM25)
  task    QUERY                           full dossier for a task across all history

Index: ~/.claude/worklog.duckdb   Transcripts: ~/.claude/projects/**/*.jsonl
Ranking uses DuckDB's FTS (BM25) when available, falling back to keyword counts offline.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import duckdb

PROJECTS = Path.home() / ".claude" / "projects"
# DB location is overridable so the nix wrapper can point it at the XDG cache
# while the uv/non-nix path keeps the default under ~/.claude.
DB_PATH = Path(os.environ.get("WORKLOG_DB", Path.home() / ".claude" / "worklog.duckdb"))
SCHEMA_VERSION = 3          # bump to force a full rebuild on distillation changes
MAX_LINE_BYTES = 2 * 1024 * 1024
TEXT_CAP = 4000
HAY_CAP = 8000

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
READ_TOOLS = {"Read", "NotebookRead"}

# Slash-command plumbing and harness-injected blocks that the transcript records
# as "user" turns but which carry no work-log signal.
_NOISE_BLOCK = re.compile(
    r"<(command-[\w-]+|local-command-[\w-]+)>.*?</\1>", re.S | re.I)
_NOISE_TAG = re.compile(
    r"</?(?:command-[\w-]+|local-command-[\w-]+|system-reminder)[^>]*>", re.I)
_SYS_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S | re.I)

SCHEMA = """
CREATE SEQUENCE IF NOT EXISTS events_id_seq;
CREATE TABLE IF NOT EXISTS events (
    id BIGINT DEFAULT nextval('events_id_seq'),
    path VARCHAR, session VARCHAR, project VARCHAR, branch VARCHAR,
    ts VARCHAR, role VARCHAR, is_sidechain BOOLEAN,
    text VARCHAR, edits VARCHAR, reads VARCHAR, commands VARCHAR, hay VARCHAR
);
CREATE TABLE IF NOT EXISTS titles   (session VARCHAR PRIMARY KEY, title VARCHAR);
CREATE TABLE IF NOT EXISTS ingested (path VARCHAR PRIMARY KEY, mtime DOUBLE, size BIGINT);
CREATE TABLE IF NOT EXISTS meta     (k VARCHAR PRIMARY KEY, v VARCHAR);
"""
INSERT_COLS = "path,session,project,branch,ts,role,is_sidechain,text,edits,reads,commands,hay"

FTS_OK = False


# ----------------------------------------------------------------------------- time
def parse_since(s: str) -> datetime:
    now = datetime.now(timezone.utc)
    if m := re.fullmatch(r"(\d+)\s*([hdw])", s.strip(), re.I):
        n, u = int(m.group(1)), m.group(2).lower()
        return now - {"h": timedelta(hours=n), "d": timedelta(days=n), "w": timedelta(weeks=n)}[u]
    return parse_iso(s)


def parse_iso(s: str) -> datetime:
    try:
        dt = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
    except ValueError:
        sys.exit(f"error: cannot parse date {s!r} (use ISO, or 7d/2w/12h)")
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def short_path(cwd: str) -> str:
    home = str(Path.home())
    return cwd.replace(home, "~") if cwd else "(unknown)"


# ----------------------------------------------------------------------------- distill
def strip_noise(text: str) -> str:
    text = _SYS_REMINDER.sub(" ", text)
    text = _NOISE_BLOCK.sub(" ", text)
    text = _NOISE_TAG.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def unpack(content) -> tuple[str, list[str], list[str], list[str]]:
    if isinstance(content, str):
        return content.strip(), [], [], []
    if not isinstance(content, list):
        return "", [], [], []
    prose, edits, reads, cmds = [], [], [], []
    for b in content:
        if not isinstance(b, dict):
            continue
        if b.get("type") == "text":
            prose.append(b.get("text", ""))
        elif b.get("type") == "tool_use":
            name, inp = b.get("name"), (b.get("input") or {})
            fp = inp.get("file_path")
            if name in EDIT_TOOLS and fp:
                edits.append(fp)
            elif name in READ_TOOLS and fp:
                reads.append(fp)
            elif name == "Bash" and inp.get("command"):
                cmds.append(inp["command"])
    return " ".join(p for p in prose if p).strip(), edits, reads, cmds


def distill_file(path: Path) -> tuple[list[tuple], tuple[str, str] | None]:
    rows: list[tuple] = []
    title = None
    stem = path.stem
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if len(line) > MAX_LINE_BYTES:
                continue
            try:
                e = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            typ = e.get("type")
            if typ == "ai-title":
                title = (e.get("sessionId", stem), e.get("aiTitle", ""))
                continue
            if typ not in ("user", "assistant"):
                continue
            ts = e.get("timestamp")
            if not ts:
                continue
            msg = e.get("message")
            content = msg.get("content") if isinstance(msg, dict) else msg
            prose, edits, reads, cmds = unpack(content)
            prose = strip_noise(prose)
            if not (prose or edits or reads or cmds):
                continue  # pure slash-command / system-reminder turn -> drop
            project = short_path(e.get("cwd", ""))
            hay = " ".join(filter(None, [
                prose, project, " ".join(edits), " ".join(reads), " ".join(cmds)]))[:HAY_CAP]
            rows.append((
                str(path), e.get("sessionId", stem), project, e.get("gitBranch", ""),
                ts, typ, bool(e.get("isSidechain", False)), prose[:TEXT_CAP],
                json.dumps(edits), json.dumps(reads), json.dumps(cmds), hay,
            ))
    return rows, title


def ensure_index(con) -> int:
    global FTS_OK
    con.execute("CREATE TABLE IF NOT EXISTS meta (k VARCHAR PRIMARY KEY, v VARCHAR)")
    cur = con.execute("SELECT v FROM meta WHERE k = 'schema_version'").fetchone()
    if cur is None or int(cur[0]) != SCHEMA_VERSION:
        for stmt in ("DROP TABLE IF EXISTS events", "DROP SEQUENCE IF EXISTS events_id_seq",
                     "DROP TABLE IF EXISTS titles", "DROP TABLE IF EXISTS ingested"):
            con.execute(stmt)
    con.execute(SCHEMA)
    con.execute("INSERT INTO meta VALUES ('schema_version', ?) "
                "ON CONFLICT(k) DO UPDATE SET v = excluded.v", [str(SCHEMA_VERSION)])

    prior = {r[0]: (r[1], r[2]) for r in con.execute("SELECT path, mtime, size FROM ingested").fetchall()}
    changed = 0
    for p in PROJECTS.rglob("*.jsonl"):
        # Skip subagent sidechains: they hold agent-generated output (incl. worklog's
        # own runbooks/reports), which would otherwise re-enter and pollute searches.
        if "subagents" in p.parts:
            continue
        st = p.stat()
        if prior.get(str(p)) == (st.st_mtime, st.st_size):
            continue
        rows, title = distill_file(p)
        con.execute("DELETE FROM events WHERE path = ?", [str(p)])
        if rows:
            con.executemany(f"INSERT INTO events ({INSERT_COLS}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        if title and title[1]:
            con.execute("INSERT INTO titles VALUES (?,?) ON CONFLICT(session) "
                        "DO UPDATE SET title = excluded.title", list(title))
        con.execute("INSERT INTO ingested VALUES (?,?,?) ON CONFLICT(path) "
                    "DO UPDATE SET mtime = excluded.mtime, size = excluded.size",
                    [str(p), st.st_mtime, st.st_size])
        changed += 1

    _ensure_fts(con, rebuild=changed > 0)
    return changed


def _ensure_fts(con, rebuild: bool) -> None:
    """Build/refresh the BM25 full-text index. Degrades to keyword fallback offline."""
    global FTS_OK
    # On nix, the store-resident duckdb can't write extensions next to itself;
    # point its extension cache at a writable dir before INSTALL/LOAD.
    if ext_dir := os.environ.get("WORKLOG_DUCKDB_EXTENSION_DIR"):
        con.execute(f"SET extension_directory = '{ext_dir}'")
    try:
        con.execute("INSTALL fts; LOAD fts;")
    except duckdb.Error:
        FTS_OK = False
        return
    FTS_OK = True
    if not rebuild:
        try:  # probe: does the index already exist?
            con.execute("SELECT fts_main_events.match_bm25(id, 'probe') FROM events LIMIT 1")
            return
        except duckdb.Error:
            pass
    con.execute("PRAGMA create_fts_index('events', 'id', 'hay', "
                "overwrite=1, stemmer='porter', stopwords='english', lower=1, strip_accents=1)")


# ----------------------------------------------------------------------------- helpers
def jl(s: str) -> list[str]:
    try:
        return json.loads(s) if s else []
    except (json.JSONDecodeError, ValueError):
        return []


def fetch_window(con, start: str, end: str) -> list[dict]:
    rows = con.execute(
        """SELECT e.session, e.project, e.branch, e.ts, e.role, e.is_sidechain,
                  e.text, e.edits, e.reads, e.commands, t.title
           FROM events e LEFT JOIN titles t USING(session)
           WHERE e.ts >= ? AND e.ts <= ? ORDER BY e.ts""",
        [start, end],
    ).fetchall()
    return [{"session": r[0], "project": r[1], "branch": r[2], "ts": r[3], "role": r[4],
             "sidechain": r[5], "text": r[6], "edits": jl(r[7]), "reads": jl(r[8]),
             "commands": jl(r[9]), "title": r[10]} for r in rows]


def group_sessions(events: list[dict]) -> list[dict]:
    sess: dict[str, dict] = {}
    for e in events:
        s = sess.setdefault(e["session"], {
            "session": e["session"], "title": e["title"] or "(untitled)",
            "project": e["project"], "branch": e["branch"], "sidechain": e["sidechain"],
            "t0": e["ts"], "t1": e["ts"], "asks": [], "edits": [], "reads": [], "commands": [],
        })
        s["t0"], s["t1"] = min(s["t0"], e["ts"]), max(s["t1"], e["ts"])
        s["edits"] += e["edits"]; s["reads"] += e["reads"]; s["commands"] += e["commands"]
        if e["title"]:
            s["title"] = e["title"]
        if e["role"] == "user" and e["text"]:
            s["asks"].append(e["text"])
    for s in sess.values():
        s["edits"] = sorted(set(s["edits"])); s["reads"] = sorted(set(s["reads"]))
    return sorted(sess.values(), key=lambda s: s["t0"])


# ----------------------------------------------------------------------------- report
def render_report(sessions: list[dict]) -> str:
    if not sessions:
        return "_No transcript activity in this window._"
    out = [f"# Work log — {len(sessions)} session(s)\n"]
    for s in sessions:
        span = f"{s['t0'][:16].replace('T', ' ')} → {s['t1'][11:16]}"
        tag = " · sidechain" if s["sidechain"] else ""
        out.append(f"## {s['title']}\n`{s['project']}` · `{s['branch']}` · {span}{tag}\n")
        for a in s["asks"][:12]:
            out.append(f"- {a[:160]}")
        if (more := len(s["asks"]) - 12) > 0:
            out.append(f"- _…+{more} more_")
        if s["edits"]:
            shown = ", ".join(f"`{Path(f).name}`" for f in s["edits"][:10])
            out.append(f"\n  **Edited:** {shown}{' +' + str(len(s['edits']) - 10) if len(s['edits']) > 10 else ''}")
        gits = [c for c in s["commands"] if c.strip().startswith("git ")][:6]
        if gits:
            out.append("  **Git:** " + "; ".join(g[:60] for g in gits))
        out.append("")
    return "\n".join(out)


def claude_summarize(text: str, instruction: str) -> str:
    prompt = f"{instruction}\n\n--- ACTIVITY LOG ---\n{text}"
    try:
        p = subprocess.run(["claude", "-p", prompt], capture_output=True, text=True, timeout=300)
    except FileNotFoundError:
        sys.exit("error: `claude` CLI not found on PATH for --summarize")
    except subprocess.TimeoutExpired:
        sys.exit("error: `claude -p` timed out")
    if p.returncode != 0:
        sys.exit(f"error: claude -p failed: {p.stderr.strip()[:300]}")
    return p.stdout.strip()


# ----------------------------------------------------------------------------- search / task
def score_sessions(con, query: str, since: str | None) -> dict[str, dict]:
    return _score_bm25(con, query, since) if FTS_OK else _score_like(con, query, since)


def _accumulate(sessions: dict, ev: dict, sc: float) -> None:
    s = sessions.setdefault(ev["session"], {
        "session": ev["session"], "title": ev["title"] or "(untitled)",
        "project": ev["project"], "branch": ev["branch"], "score": 0.0,
        "t0": ev["ts"], "t1": ev["ts"], "events": [],
    })
    s["score"] += sc
    s["t0"], s["t1"] = min(s["t0"], ev["ts"]), max(s["t1"], ev["ts"])
    s["events"].append(ev)


def _ev(r) -> dict:
    return {"session": r[0], "project": r[1], "branch": r[2], "ts": r[3], "role": r[4],
            "sidechain": r[5], "text": r[6], "edits": jl(r[7]), "reads": jl(r[8]),
            "commands": jl(r[9]), "title": r[10]}


def _score_bm25(con, query: str, since: str | None) -> dict[str, dict]:
    extra = "AND ts >= ?" if since else ""
    params = [query] + ([since] if since else [])
    rows = con.execute(
        f"""WITH scored AS (
              SELECT e.session, e.project, e.branch, e.ts, e.role, e.is_sidechain,
                     e.text, e.edits, e.reads, e.commands, t.title,
                     fts_main_events.match_bm25(e.id, ?) AS score
              FROM events e LEFT JOIN titles t USING(session))
            SELECT * FROM scored WHERE score IS NOT NULL {extra}
            ORDER BY score DESC LIMIT 4000""",
        params,
    ).fetchall()
    sessions: dict[str, dict] = {}
    for r in rows:
        _accumulate(sessions, _ev(r), r[11])
    return sessions


def _score_like(con, query: str, since: str | None) -> dict[str, dict]:
    terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 1]
    if not terms:
        sys.exit("error: empty query")
    extra = "AND e.ts >= ?" if since else ""
    params = terms + ([since] if since else [])
    rows = con.execute(
        f"""SELECT e.session, e.project, e.branch, e.ts, e.role, e.is_sidechain,
                   e.text, e.edits, e.reads, e.commands, t.title, lower(e.hay) AS hay
            FROM events e LEFT JOIN titles t USING(session)
            WHERE ({" OR ".join("hay LIKE '%'||?||'%'" for _ in terms)}) {extra}
            ORDER BY e.ts""",
        params,
    ).fetchall()
    sessions: dict[str, dict] = {}
    for r in rows:
        _accumulate(sessions, _ev(r), float(sum(1 for t in terms if t in r[11])))
    return sessions


def cmd_search(con, query: str, since: str | None, as_json: bool) -> None:
    ranked = sorted(score_sessions(con, query, since).values(), key=lambda s: -s["score"])[:15]
    if as_json:
        for s in ranked:
            s["score"] = round(s["score"], 2)
            s["snippets"] = [e["text"][:200] for e in s["events"] if e["text"]][:4]
            del s["events"]
        print(json.dumps(ranked, indent=2)); return
    if not ranked:
        print(f"_No sessions matching {query!r}._"); return
    print(f"# Sessions matching {query!r} — {len(ranked)} hit(s)\n")
    for s in ranked:
        print(f"## {s['title']}  (score {s['score']:.1f})")
        print(f"`{s['project']}` · `{s['branch']}` · {s['t0'][:16].replace('T',' ')} → {s['t1'][:10]}\n")
        for e in s["events"][:3]:
            if e["text"]:
                print(f"- {e['text'][:160]}")
        print()


def cmd_task(con, query: str, as_json: bool) -> None:
    sessions = sorted(score_sessions(con, query, None).values(), key=lambda s: -s["score"])
    sessions = [s for s in sessions if s["score"] > 0][:20]
    timeline, edits, reads, cmds = [], {}, {}, []
    for s in sorted(sessions, key=lambda s: s["t0"]):
        for e in s["events"]:
            if e["text"]:
                timeline.append({"ts": e["ts"][:16], "project": e["project"],
                                 "role": e["role"], "text": e["text"][:220]})
            for f in e["edits"]:
                edits[f] = edits.get(f, 0) + 1
            for f in e["reads"]:
                reads[f] = reads.get(f, 0) + 1
            cmds += list(e["commands"])
    dossier = {
        "query": query,
        "sessions": [{"title": s["title"], "project": s["project"], "branch": s["branch"],
                      "from": s["t0"][:16], "to": s["t1"][:16], "score": round(s["score"], 2)}
                     for s in sessions],
        "timeline": timeline[:120],
        "files_edited": sorted(edits.items(), key=lambda kv: -kv[1])[:30],
        "files_read": sorted(reads.items(), key=lambda kv: -kv[1])[:40],
        "commands": cmds[:60],
    }
    if as_json:
        print(json.dumps(dossier, indent=2)); return
    print(f"# Task dossier — {query!r}\n")
    print(f"**{len(sessions)} relevant session(s)** across "
          f"{len({s['project'] for s in sessions})} project(s)\n")
    for s in dossier["sessions"]:
        print(f"- {s['title']} · `{s['project']}` · {s['from']} (score {s['score']})")
    print("\n## Files edited"); [print(f"- {f} ×{n}") for f, n in dossier["files_edited"][:15]]
    print("\n## Files read");   [print(f"- {f} ×{n}") for f, n in dossier["files_read"][:15]]
    print(f"\n## Timeline ({len(dossier['timeline'])} events)")
    for t in dossier["timeline"]:
        print(f"- {t['ts']} [{t['role']}] {t['text'][:140]}")


# ----------------------------------------------------------------------------- main
def main() -> None:
    """Parse args, refresh the index, and dispatch to the requested subcommand.

    Connects to the DuckDB index (creating/migrating it as needed via
    `ensure_index`), then routes to one of `index`, `report`, `search`, or
    `task`. Every path auto-refreshes the index first, so the data is current
    regardless of which subcommand runs.
    """
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("index", help="build/refresh the index")
    rp = sub.add_parser("report", help="what you worked on in a time window")
    rp.add_argument("--since", default="7d"); rp.add_argument("--until", default=None)
    rp.add_argument("--summarize", action="store_true"); rp.add_argument("--json", action="store_true")
    se = sub.add_parser("search", help="sessions matching a topic")
    se.add_argument("query"); se.add_argument("--since", default=None); se.add_argument("--json", action="store_true")
    tk = sub.add_parser("task", help="full dossier for a task")
    tk.add_argument("query"); tk.add_argument("--json", action="store_true")

    args = ap.parse_args()
    con = duckdb.connect(str(DB_PATH))
    changed = ensure_index(con)

    if args.cmd == "index":
        n = con.execute("SELECT count(*) FROM events").fetchone()[0]
        rank = "BM25" if FTS_OK else "keyword-fallback"
        print(f"indexed: {changed} file(s) refreshed · {n} events · ranking={rank} · {DB_PATH}")
    elif args.cmd == "report":
        since = parse_since(args.since)
        until = parse_iso(args.until) if args.until else datetime.now(timezone.utc)
        sessions = group_sessions(fetch_window(con, iso_z(since), iso_z(until)))
        if args.json:
            print(json.dumps(sessions, indent=2))
        elif args.summarize:
            print(claude_summarize(render_report(sessions),
                  "Turn this developer activity log into a crisp standup report grouped by "
                  "project/theme. Lead with accomplishments, past tense, no filler."))
        else:
            print(render_report(sessions))
    elif args.cmd == "search":
        since = iso_z(parse_since(args.since)) if args.since else None
        cmd_search(con, args.query, since, args.json)
    elif args.cmd == "task":
        cmd_task(con, args.query, args.json)


if __name__ == "__main__":
    main()
