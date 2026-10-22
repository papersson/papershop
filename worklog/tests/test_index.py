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
