# Only orchestration: all measurement and grouping remains in the saved SQL.
# Run from any directory. Output includes private paths; keep it local.
def main [out: path, --since: string, --until: string] {
    mkdir $out
    const here = path self | path dirname
    let audit = open ($here | path join workspace-audit.sql) --raw
    let summary = open ($here | path join workspace-summary.sql) --raw
    # Cast user-supplied strings through safe SQL literals (single-quote doubling).
    let since_value = $since | default '' | str replace --all "'" "''"
    let until_value = $until | default '' | str replace --all "'" "''"
    let bounds = ([
        (if $since != null { $"SET VARIABLE audit_since = '($since_value)';" } else { '' })
        (if $until != null { $"SET VARIABLE audit_until = '($until_value)';" } else { '' })
    ] | str join "\n")
    let db = '~/.claude/worklog.duckdb' | path expand
    duckdb -readonly -json $db ($bounds + "\n" + $audit)
        | from json | save -f ($out | path join sessions.json)
    let setup = $audit | split row '-- AUDIT RESULT' | first
    duckdb -readonly -json $db ($bounds + "\n" + $setup + "\n" + $summary)
        | from json | first | save -f ($out | path join summary.json)
    open ($out | path join summary.json) | get groups
}
