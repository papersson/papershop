-- Worklog schema 5. Run against ~/.claude/worklog.duckdb, never the cache copy.
-- Optional SET VARIABLE audit_since/audit_until overrides; default is 3 months.
-- Everything after the temporary views is one JSON-serializable row/session.
-- Time is elapsed span and a capped inter-event proxy, NOT human attention.
-- session_runs is explicit pilot metadata; absent metadata means unknown host.
CREATE OR REPLACE TEMP VIEW audit_window AS
SELECT coalesce(try_cast(getvariable('audit_until') AS TIMESTAMPTZ), current_timestamp) AS until_ts,
       coalesce(try_cast(getvariable('audit_since') AS TIMESTAMPTZ),
                current_timestamp - INTERVAL '3 months') AS since_ts;

CREATE OR REPLACE TEMP VIEW audit_events AS
SELECT * EXCLUDE (ranked) FROM (
  SELECT e.*, try_cast(ts AS TIMESTAMPTZ) AS at_ts,
    row_number() OVER (
      PARTITION BY session, coalesce(nullif(event_uuid, ''), 'row:' || id)
      ORDER BY is_sidechain, id) AS ranked
  FROM events e, audit_window w
  WHERE try_cast(ts AS TIMESTAMPTZ) >= w.since_ts
    AND try_cast(ts AS TIMESTAMPTZ) < w.until_ts
) WHERE ranked = 1;

CREATE OR REPLACE TEMP VIEW audit_tools AS
SELECT * EXCLUDE (ranked) FROM (
  SELECT e.session, e.id, e.at_ts, e.is_sidechain,
    json_extract_string(j.value, '$') AS tool,
    coalesce(nullif(json_extract_string(e.tool_ids, '$[' || j.key || ']'), ''),
             'row:' || e.id || ':' || j.key) AS tool_id,
    row_number() OVER (PARTITION BY e.session, tool_id ORDER BY e.id) AS ranked
  FROM audit_events e, json_each(e.tools) j
) WHERE ranked = 1;

CREATE OR REPLACE TEMP VIEW audit_commands AS
SELECT e.session, e.id, e.project, e.at_ts, e.is_sidechain,
       json_extract_string(j.value, '$') AS command
FROM audit_events e, json_each(e.commands) j;

-- Keep explicit file accesses and search roots separate from shell references.
-- Shell regex cannot expand variables, execute scripts, see subprocess I/O, or
-- establish that an argument was read/written. Do not count it as proven I/O.
CREATE OR REPLACE TEMP VIEW audit_paths AS
WITH raw AS (
  SELECT e.session, e.project, e.is_sidechain, e.id,
    json_extract_string(j.value, '$.path') AS raw_path,
    json_extract_string(j.value, '$.access') AS access,
    json_extract_string(j.value, '$.tool') AS tool
  FROM audit_events e, json_each(e.path_refs) j
  UNION ALL
  SELECT session, project, is_sidechain, id,
    unnest(regexp_extract_all(command,
      '(?:~\/|\$HOME\/|\/(?:Users|home|tmp|private|var|etc|opt|usr|run|nix|workspace|workspaces|tank)\/)[^\s"''`<>;|)\]}]+|(?:\.?\.?\/)?(?:[A-Za-z0-9_.-]+\/)*[A-Za-z0-9_.-]+\.(?:py|rs|js|ts|tsx|json|toml|yaml|yml|md|sql|nix|csv|parquet|ipynb)\b')),
    'shell_reference', 'shell'
  FROM audit_commands
), normalized AS (
  SELECT *, CASE
    WHEN starts_with(raw_path, '$HOME/') THEN '~/' || substr(raw_path, 7)
    WHEN starts_with(raw_path, (SELECT v || '/' FROM meta WHERE k = 'home'))
      THEN '~' || substr(raw_path, (SELECT length(v) + 1 FROM meta WHERE k = 'home'))
    WHEN starts_with(raw_path, '/') OR starts_with(raw_path, '~') THEN raw_path
    ELSE rtrim(project, '/') || '/' || regexp_replace(raw_path, '^\./', '') END AS normalized_path
  FROM raw WHERE raw_path IS NOT NULL AND raw_path != ''
    AND NOT contains(raw_path, '://')
), categorized AS (
  SELECT *, CASE
    WHEN normalized_path = '~/.claude' OR starts_with(normalized_path, '~/.claude/') THEN '~/.claude'
    WHEN normalized_path = '~/drafts' OR starts_with(normalized_path, '~/drafts/') THEN '~/drafts'
    WHEN EXISTS (SELECT 1 FROM repositories r
      WHERE normalized_path = r.root OR starts_with(normalized_path, r.root || '/')) THEN 'repo'
    WHEN starts_with(normalized_path, '~/') OR normalized_path = '~' THEN 'other_home'
    ELSE 'elsewhere' END AS category
  FROM normalized
)
SELECT session, normalized_path AS path, category, access, tool,
       bool_or(is_sidechain) AS seen_in_subagent, count(*) AS references
FROM categorized GROUP BY session, normalized_path, category, access, tool;

CREATE OR REPLACE TEMP VIEW audit_dependencies AS
WITH tool_hits AS (
  SELECT session, 'browser_or_computer_mcp' AS dependency, tool AS evidence
  FROM audit_tools WHERE regexp_matches(lower(tool), 'mcp.*(browser|chrome|playwright|computer|desktop)|computer.?use')
), command_hits AS (
  SELECT session, rule.dependency, command AS evidence
  FROM audit_commands c, (VALUES
    ('mac_open', '(^|[;|&\n]\s*|\s)(/usr/bin/)?open\s+(-[a-zA-Z]+\s+|["''~/])'),
    ('osascript', '\bosascript\b'),
    ('agent_browser', '\bagent-browser\b'),
    ('arc_cookies', '(?i)(Arc[^\n]*(Cookies|cookie)|browser_cookie3[^\n]*arc|Arc/User Data)'),
    ('keychain', '(?i)(security\s+(find|add|delete|set)-[a-z-]*password|keychain|keyring)'),
    ('gui_app', '(?i)(/Applications/|tell application|screencapture|terminal-notifier|herdr|screenshot-pane)'),
    ('local_browser_profile', '(?i)(agent-browser[^\n]*(--auto-connect|--cdp|--profile)|remote-debugging-port|localhost:9222|127\.0\.0\.1:9222)'),
    ('local_service', '(?i)(localhost|127\.0\.0\.1|/tmp/cc-socks|HERDR_SOCKET)'),
    ('credential_or_data', '(?i)(\.env(\b|\.)|\.aws/|\.ssh/|\.config/|/Downloads/|/Library/|data/artifacts|data/raw)'),
    ('ssh_remote_command', '\bssh\s'),
    ('working_tree_probe', '\bgit\s+([^;\n]*\s)?(status|diff|stash)\b')
  ) AS rule(dependency, pattern)
  WHERE regexp_matches(command, rule.pattern)
)
SELECT session, dependency, count(*) AS hits, list(DISTINCT left(evidence, 500)) AS evidence
FROM (SELECT * FROM tool_hits UNION ALL SELECT * FROM command_hits)
GROUP BY session, dependency;

CREATE OR REPLACE TEMP VIEW audit_session_metrics AS
WITH ordered AS (
  SELECT *, epoch(at_ts - lag(at_ts) OVER (PARTITION BY session ORDER BY at_ts, id)) AS gap_s
  FROM audit_events
), gaps AS (
  SELECT session, epoch(at_ts - lag(at_ts) OVER (PARTITION BY session ORDER BY at_ts, id)) AS gap_s
  FROM audit_events WHERE user_kind = 'human' AND NOT is_sidechain
), metrics AS (
  SELECT session,
    min(at_ts) AS started_at, max(at_ts) AS ended_at,
    arg_min(project, at_ts) FILTER (WHERE NOT is_sidechain) AS project,
    count(*) FILTER (WHERE NOT is_sidechain) AS main_events,
    count(*) FILTER (WHERE user_kind = 'human' AND NOT is_sidechain) AS human_messages,
    count(*) FILTER (WHERE user_kind = 'sdk' AND NOT is_sidechain) AS sdk_messages,
    epoch(max(at_ts) - min(at_ts)) / 60.0 AS wall_minutes,
    sum(least(coalesce(gap_s, 0), 300)) / 60.0 AS active_minutes_5m,
    sum(least(coalesce(gap_s, 0), 900)) / 60.0 AS active_minutes_15m,
    bool_or(NOT is_sidechain) AS has_main
  FROM ordered GROUP BY session
), tools AS (
  SELECT session, count(*) AS tool_calls,
    count(*) FILTER (WHERE NOT is_sidechain) AS main_tool_calls,
    count(*) FILTER (WHERE is_sidechain) AS subagent_tool_calls,
    list(DISTINCT tool ORDER BY tool) AS tool_names
  FROM audit_tools GROUP BY session
), dependencies AS (
  SELECT session,
    list(struct_pack(kind := dependency, hits := hits, evidence := evidence) ORDER BY dependency) AS dependencies,
    bool_or(dependency IN ('mac_open','osascript','arc_cookies','keychain','gui_app','browser_or_computer_mcp','local_browser_profile')) AS laptop_signal,
    bool_or(dependency = 'agent_browser') AS browser_signal,
    bool_or(dependency = 'working_tree_probe') AS working_tree_probe
  FROM audit_dependencies GROUP BY session
), paths AS (
  SELECT session,
    list(struct_pack(path := path, category := category, access := access, tool := tool,
                     subagent := seen_in_subagent) ORDER BY category, path, access, tool) AS paths,
    count(DISTINCT path) AS path_count,
    count(DISTINCT path) FILTER (WHERE access IN ('read','write')) AS explicit_io_paths,
    bool_or(category IN ('~/.claude','~/drafts','other_home')) AS personal_state
  FROM audit_paths GROUP BY session
), human_gaps AS (
  SELECT session, max(gap_s) / 60.0 AS longest_human_gap_minutes,
    median(gap_s) / 60.0 AS median_human_gap_minutes
  FROM gaps GROUP BY session
)
SELECT m.*, coalesce(t.title, '(untitled)') AS title,
  coalesce(tool_calls, 0) AS tool_calls, coalesce(main_tool_calls, 0) AS main_tool_calls,
  coalesce(subagent_tool_calls, 0) AS subagent_tool_calls, coalesce(tool_names, []) AS tool_names,
  longest_human_gap_minutes, median_human_gap_minutes,
  coalesce(laptop_signal, false) AS laptop_signal, coalesce(browser_signal, false) AS browser_signal,
  coalesce(working_tree_probe, false) AS working_tree_probe,
  coalesce(personal_state, false) AS personal_state,
  coalesce(path_count, 0) AS path_count, coalesce(explicit_io_paths, 0) AS explicit_io_paths,
  coalesce(paths, []) AS paths, coalesce(dependencies, []) AS dependencies,
  coalesce(nullif(r.execution_host, ''), 'unknown') AS execution_host,
  r.task_id, r.fallback_reason,
  CASE
    WHEN human_messages = 0 THEN 'G0'
    WHEN coalesce(tool_calls, 0) = 0 THEN 'G1'
    WHEN human_messages <= 3 THEN 'G2'
    WHEN coalesce(main_tool_calls, 0) / human_messages >= 10
      AND coalesce(longest_human_gap_minutes, 0) >= 30 THEN 'G3'
    ELSE 'G4' END AS mode
FROM metrics m LEFT JOIN tools USING (session) LEFT JOIN dependencies USING (session)
LEFT JOIN paths USING (session) LEFT JOIN human_gaps USING (session)
LEFT JOIN titles t USING (session) LEFT JOIN session_runs r USING (session)
WHERE has_main;

-- AUDIT RESULT
SELECT * FROM audit_session_metrics ORDER BY started_at, session;
