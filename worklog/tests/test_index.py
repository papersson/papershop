"""Regression checks for audit coverage and retrieval isolation.

Run: uv run --with duckdb python -m unittest discover -s worklog/tests
"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import duckdb

spec = importlib.util.spec_from_file_location("worklog", Path(__file__).parents[1] / "scripts/worklog.py")
worklog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worklog)


class IndexTest(unittest.TestCase):
    def setUp(self):
        # Hermetic: never read the atuin of the machine running the tests.
        env = patch.dict("os.environ", {"WORKLOG_ATUIN": "0"})
        env.start()
        self.addCleanup(env.stop)

    def test_all_tools_and_notebook_paths(self):
        names = ["mcp__browser__click", "Glob", "Grep", "WebFetch", "Agent", "Workflow"]
        content = [{"type": "tool_use", "name": n, "id": n, "input": {}} for n in names]
        content.append({"type": "tool_use", "name": "NotebookEdit", "input": {"notebook_path": "a.ipynb"}})
        _, edits, _, _, tools = worklog.unpack(content)
        self.assertEqual(tools, names + ["NotebookEdit"])
        self.assertEqual(edits, ["a.ipynb"])
        ids, refs = worklog.tool_provenance(content, "/repo")
        self.assertEqual(ids[:6], names)
        self.assertEqual([r["access"] for r in refs], ["search", "search", "write"])

    def test_humans_are_not_notifications_or_sdk_jobs(self):
        for extra, expected in [({"origin": {"kind": "human"}}, "human"),
                                ({"promptSource": "sdk"}, "sdk"),
                                ({"promptSource": "system"}, "system"),
                                ({"isCompactSummary": True}, "system"),
                                ({"isSidechain": True}, "agent")]:
            self.assertEqual(worklog.user_kind({"type": "user", **extra}, "hello", "hello"), expected)
        self.assertEqual(worklog.user_kind({"type": "user"}, [{"type": "tool_result"}], ""), "tool_result")
        self.assertEqual(worklog.user_kind({"type": "user"}, "", "[Request interrupted by user]"), "system")

    def test_schema_rebuild_sidechains_and_incremental_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "session.jsonl"
            child = root / "session/subagents/agent-a.jsonl"
            child.parent.mkdir(parents=True)
            def event(role, content, **extra):
                return dict(type=role, message={"content": content}, uuid=role,
                            timestamp="2026-10-01T10:00:00Z", cwd="/repo", sessionId="session", **extra)
            parent.write_text("\n".join(json.dumps(e) for e in [
                event("user", "human request", origin={"kind": "human"}),
                event("assistant", [{"type": "tool_use", "name": "mcp__browser__click", "id": "tool-1", "input": {}}]),
                event("user", [{"type": "tool_result", "tool_use_id": "tool-1", "content": "done"}]),
            ]))
            child.write_text(json.dumps(event("assistant", "sidechain poison", isSidechain=True)))
            con = duckdb.connect()
            con.execute("CREATE TABLE meta(k VARCHAR PRIMARY KEY, v VARCHAR); INSERT INTO meta VALUES ('schema_version','3'); CREATE TABLE events(old INTEGER)")
            with patch.object(worklog, "PROJECTS", root), patch.object(worklog, "_ensure_fts"):
                self.assertEqual(worklog.ensure_index(con), 2)
                self.assertEqual(worklog.ensure_index(con), 0)
            self.assertEqual(con.execute("SELECT count(*) FROM events").fetchone()[0], 4)
            self.assertEqual(con.execute("SELECT count(*) FROM events WHERE user_kind='tool_result'").fetchone()[0], 1)
            self.assertEqual(len(worklog.fetch_window(con, "2026", "2027")), 2)
            self.assertFalse(worklog._score_like(con, "poison", None))

    def test_without_atuin_nothing_runs(self):
        """A machine without atuin (or with WORKLOG_ATUIN=0) indexes transcripts only."""
        with patch.object(worklog.subprocess, "run") as run:
            self.assertIsNone(worklog.atuin_bin())
            self.assertEqual(worklog._ingest_atuin(duckdb.connect(), {}, set()), 0)
            run.assert_not_called()
        with patch.dict("os.environ", {"WORKLOG_ATUIN": ""}), \
                patch.object(worklog.shutil, "which", return_value=None):
            self.assertIsNone(worklog.atuin_bin())

    def test_atuin_threads_fill_what_transcripts_miss(self):
        threads = [
            # This machine has the transcript, so atuin's copy is skipped.
            {"harness": "claude-code", "session_id": "local", "atuin_id": "a-local",
             "updated_at": "2026-10-01T10:00:00+00:00", "message_count": 2},
            {"harness": "codex", "session_id": "cx", "atuin_id": "a-codex",
             "updated_at": "2026-10-01T11:00:00+00:00", "message_count": 4},
            {"harness": "claude-code", "session_id": "agent-x", "atuin_id": "a-sub",
             "updated_at": "2026-10-01T12:00:00+00:00", "message_count": 1,
             "preview": "look around the repo"},
        ]
        code_cell = ('text(await tools.exec_command({cmd:"rg -n foo src"}))\n'
                     'await tools.apply_patch("*** Begin Patch\\n*** Update File: src/app.py\\n")')
        shows = {
            "a-codex": [
                {"kind": "session", "session_id": "cx", "cwd": "/repo", "title": "Codex fix"},
                {"kind": "message", "role": "user", "timestamp": "2026-10-01T11:00:00.5+00:00",
                 "content": [{"type": "text", "text": "fix the parser"}]},
                {"kind": "message", "role": "assistant", "timestamp": "2026-10-01T11:01:00+00:00",
                 "content": [{"type": "tool_call", "id": "c1", "name": "exec", "input": code_cell}]},
                {"kind": "message", "role": "tool", "timestamp": "2026-10-01T11:02:00+00:00",
                 "content": [{"type": "tool_result", "tool_use_id": "c1", "content": "ok"}]},
                {"kind": "message", "role": "token_usage_record", "timestamp": "2026-10-01T11:02:00+00:00"},
            ],
            "a-sub": [
                {"kind": "session", "session_id": "agent-x", "parent_kind": "subagent", "cwd": "/repo"},
                {"kind": "message", "role": "assistant", "timestamp": "2026-10-01T12:00:00+00:00",
                 "content": [{"type": "tool_call", "id": "b1", "name": "Bash",
                              "input": "{\"command\": \"git status\"}"}]},
            ],
        }
        calls = []
        def fake_atuin(*args):
            calls.append(args)
            if args[:2] == ("threads", "list"):
                return json.dumps(threads)
            return "\n".join(json.dumps(l) for l in shows[args[2]])
        con = duckdb.connect()
        con.execute(worklog.SCHEMA)
        with patch.object(worklog, "_atuin", fake_atuin):
            self.assertEqual(worklog._ingest_atuin(con, {}, {"local"}), 2)
            prior = {r[0]: (r[1], r[2]) for r in con.execute("SELECT path, mtime, size FROM ingested").fetchall()}
            self.assertEqual(worklog._ingest_atuin(con, prior, {"local"}), 0)
        self.assertNotIn(("threads", "show", "a-local", "--style", "ndjson"), calls)
        rows = con.execute("SELECT session, role, user_kind, is_sidechain, commands, edits, ts "
                           "FROM events WHERE path = 'atuin:a-codex' ORDER BY ts").fetchall()
        self.assertEqual([r[2] for r in rows], ["human", "", "tool_result"])
        self.assertEqual(rows[0][6], "2026-10-01T11:00:00.500Z")
        self.assertEqual(json.loads(rows[1][4]), ["rg -n foo src"])
        self.assertEqual(json.loads(rows[1][5]), ["src/app.py"])
        sub = con.execute("SELECT is_sidechain, commands FROM events WHERE path = 'atuin:a-sub'").fetchone()
        self.assertEqual(sub, (True, '["git status"]'))
        window = worklog.fetch_window(con, "2026", "2027")
        self.assertEqual({e["session"] for e in window}, {"cx"})
        sessions = worklog.add_transcripts(con, worklog.group_sessions(window))
        self.assertEqual((sessions[0]["title"], sessions[0]["transcript"]), ("Codex fix", "atuin:a-codex"))
        # No AI title: the thread's first prompt stands in.
        self.assertEqual(con.execute("SELECT title FROM titles WHERE session = 'agent-x'").fetchone(),
                         ("look around the repo",))

    def test_audit_deduplicates_calls_and_counts_human_gaps(self):
        con = duckdb.connect()
        con.execute(worklog.SCHEMA)
        con.execute("INSERT INTO repositories VALUES ('~/repo')")
        con.execute("SET VARIABLE audit_since = '2026-10-01T00:00:00Z'; SET VARIABLE audit_until = '2026-10-02T00:00:00Z'")
        def insert(uuid, time, role, kind, tools='[]', ids='[]', refs='[]'):
            con.execute("INSERT INTO events (session,project,ts,role,is_sidechain,text,edits,reads,commands,tools,hay,event_uuid,user_kind,tool_ids,path_refs) VALUES ('s','~/repo',?,?,false,'','[]','[]','[]',?,'',?,?,?,?)",
                        [f"2026-10-01T10:{time}:00Z", role, tools, uuid, kind, ids, refs])
        insert('u1', '00', 'user', 'human')
        insert('a1', '05', 'assistant', '', '["Read"]', '["call1"]',
               '[{"path":"~/repo/a.py","access":"read","tool":"Read"}]')
        insert('a2', '06', 'assistant', '', '["Read"]', '["call1"]')
        insert('u2', '10', 'user', 'human')
        insert('r1', '20', 'user', 'tool_result')
        sql = (Path(__file__).parents[1] / 'queries/workspace-audit.sql').read_text()
        con.execute(sql)
        row = con.execute("SELECT human_messages, tool_calls, wall_minutes, longest_human_gap_minutes, mode FROM audit_session_metrics").fetchone()
        self.assertEqual(row, (2, 1, 20.0, 10.0, 'G2'))
        self.assertEqual(con.execute("SELECT category FROM audit_paths").fetchone()[0], 'repo')


if __name__ == "__main__":
    unittest.main()
