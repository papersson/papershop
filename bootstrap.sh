#!/usr/bin/env bash
# Non-nix bootstrap. Run by the plugin's SessionStart hook. Ensures `uv` is
# available and drops a `worklog` shim on PATH that runs the bundled script via
# `uv run --script` (the PEP 723 header pins duckdb). On NixOS this file is
# never used — there `worklog` comes from home.packages instead.
set -euo pipefail

[ "${1:-}" = "ensure" ] || { echo "usage: bootstrap.sh ensure" >&2; exit 2; }

root="${CLAUDE_PLUGIN_ROOT:?CLAUDE_PLUGIN_ROOT not set (run me from the plugin hook)}"

# 1. uv — install via the official script if it isn't already on PATH.
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# 2. worklog shim — bake the absolute script path so it works outside plugin
#    context (the shim runs wherever the user's PATH picks it up).
bindir="$HOME/.local/bin"
shim="$bindir/worklog"
mkdir -p "$bindir"
cat > "$shim" <<EOF
#!/usr/bin/env bash
exec uv run --script "$root/scripts/worklog.py" "\$@"
EOF
chmod +x "$shim"
