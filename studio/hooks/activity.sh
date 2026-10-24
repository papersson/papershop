#!/bin/sh
# Outside a shoot: one small-file check, no stdin parsing, interpreter, Nix or uv.
[ -s "${STUDIO_HOME:-$HOME/studio}/.active-shoot.json" ] || exit 0
root=$(CDPATH= cd -- "$(dirname -- "$0")/../skills/studio" && pwd) || exit 0
[ -x "$root/kit/.venv/bin/python" ] || exit 0
exec "$root/kit/.venv/bin/python" -I -B -m studio_kit.agent_hook
