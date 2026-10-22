-- Run after workspace-audit.sql in the same DuckDB CLI connection.
CREATE OR REPLACE TEMP VIEW audit_groups AS
SELECT mode, count(*) AS sessions, sum(human_messages) AS human_messages,
  sum(tool_calls) AS tool_calls, sum(main_tool_calls) AS main_tool_calls,
  round(sum(wall_minutes)/60, 2) AS summed_wall_hours,
  round(sum(active_minutes_5m)/60, 2) AS activity_hours_5m,
  round(sum(active_minutes_15m)/60, 2) AS activity_hours_15m,
  count(*) FILTER (WHERE laptop_signal) AS laptop_signal_sessions,
  count(*) FILTER (WHERE browser_signal) AS agent_browser_sessions,
  count(*) FILTER (WHERE personal_state) AS personal_state_sessions,
  count(*) FILTER (WHERE working_tree_probe) AS working_tree_probe_sessions,
  count(*) FILTER (WHERE execution_host NOT IN ('unknown','local','laptop')) AS remote_sessions,
  count(*) FILTER (WHERE nullif(fallback_reason,'') IS NOT NULL) AS fallback_sessions
FROM audit_session_metrics GROUP BY mode ORDER BY mode;

CREATE OR REPLACE TEMP VIEW audit_dependency_summary AS
SELECT dependency, count(*) AS sessions, sum(hits) AS hits
FROM audit_dependencies d JOIN audit_session_metrics s USING (session)
WHERE s.human_messages > 0 GROUP BY dependency ORDER BY sessions DESC;

CREATE OR REPLACE TEMP VIEW audit_path_summary AS
SELECT category, access, count(DISTINCT p.session) AS sessions,
  count(DISTINCT path) AS unique_paths
FROM audit_paths p JOIN audit_session_metrics s USING (session)
WHERE s.human_messages > 0 GROUP BY category, access ORDER BY category, access;

CREATE OR REPLACE TEMP VIEW audit_months AS
SELECT strftime(started_at, '%Y-%m') AS month, count(*) AS sessions,
  count(*) FILTER (WHERE human_messages > 0) AS human_sessions,
  sum(human_messages) AS human_messages
FROM audit_session_metrics GROUP BY month ORDER BY month;

-- Denominator stays human sessions; unattended SDK critiques are separate.
CREATE OR REPLACE TEMP VIEW audit_pilot AS
SELECT count(*) AS human_sessions,
  count(*) FILTER (WHERE execution_host = 'unknown') AS unknown_host_sessions,
  count(*) FILTER (WHERE execution_host NOT IN ('unknown','local','laptop')) AS remote_sessions,
  round(100.0 * count(*) FILTER (WHERE execution_host != 'unknown')
    / nullif(count(*),0),2) AS host_label_coverage_pct,
  CASE WHEN count(*) FILTER (WHERE execution_host = 'unknown') = 0 THEN
    round(100.0 * count(*) FILTER (WHERE execution_host NOT IN ('unknown','local','laptop'))
      / nullif(count(*),0),2) END AS remote_share_pct,
  count(*) FILTER (WHERE nullif(fallback_reason,'') IS NOT NULL) AS fallback_sessions,
  round(100.0 * count(*) FILTER (WHERE nullif(fallback_reason,'') IS NOT NULL)
    / nullif(count(*) FILTER (WHERE execution_host NOT IN ('unknown','local','laptop')),0),2) AS fallback_per_remote_pct
FROM audit_session_metrics WHERE human_messages > 0;

CREATE OR REPLACE TEMP VIEW audit_group_shares AS
SELECT *, round(100.0 * sessions / sum(sessions) OVER (), 2) AS all_session_share_pct,
  CASE WHEN mode != 'G0' THEN round(100.0 * sessions /
    sum(sessions) FILTER (WHERE mode != 'G0') OVER (), 2) END AS human_session_share_pct,
  CASE WHEN mode != 'G0' THEN round(100.0 * activity_hours_5m /
    sum(activity_hours_5m) FILTER (WHERE mode != 'G0') OVER (), 2) END AS human_activity_share_pct
FROM audit_groups;

SELECT (SELECT list(g) FROM audit_group_shares g) AS groups,
       (SELECT list(d) FROM audit_dependency_summary d) AS dependencies,
       (SELECT list(p) FROM audit_path_summary p) AS paths,
       (SELECT list(m) FROM audit_months m) AS months,
       (SELECT list(p) FROM audit_pilot p) AS pilot;
