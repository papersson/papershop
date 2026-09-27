#!/usr/bin/env bash
# Set up a project for the tutor skill: copy the kit and templates in (so a lesson always rebuilds
# with the kit it was made with, whatever the plugin later becomes), and create the Python venv.
#
#   scripts/setup.sh PROJECT_DIR            # creates PROJECT_DIR/tutor/{kit,templates,learner.md,.venv}
#   scripts/setup.sh PROJECT_DIR --no-venv  # files only (e.g. inside `nix develop`, which has the deps)
#
# System dependencies (apt names): ffmpeg espeak-ng libcairo2-dev libpango1.0-dev pkg-config
# fonts-ibm-plex. With Nix: `nix develop github:papersson/papershop#tutor` provides them all.
set -euo pipefail
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${1:?usage: setup.sh PROJECT_DIR [--no-venv]}"
T="$PROJECT/tutor"

mkdir -p "$T/lessons"
if [ -d "$T/kit" ]; then
  echo "kit already present at $T/kit (leaving it; delete it to take the plugin's current kit)"
else
  cp -r "$SKILL/kit" "$T/kit"
  rm -rf "$T/kit/__pycache__"
  echo "copied kit to $T/kit"
fi
[ -d "$T/templates" ] || { cp -r "$SKILL/templates" "$T/templates"; echo "copied templates"; }
[ -f "$T/learner.md" ] || { cp "$SKILL/templates/learner.md" "$T/learner.md"; echo "created $T/learner.md: fill in Background before the first lesson"; }
cat > "$T/.gitignore" <<'EOF'
__pycache__/
.venv/
lessons/*/audio/*.wav
lessons/*/out/video.mp4
lessons/*/out/preview.mp4
lessons/*/out/parts.txt
lessons/*/out/page/video.mp4
lessons/*/scenes/media/
EOF

if [ "${2:-}" != "--no-venv" ]; then
  for dep in ffmpeg espeak-ng pkg-config; do
    command -v "$dep" >/dev/null || echo "warning: $dep not found on PATH"
  done
  if [ ! -x "$T/.venv/bin/python" ]; then
    if command -v uv >/dev/null; then
      uv venv -q --python 3.11 "$T/.venv" && uv pip install -q --python "$T/.venv/bin/python" -r "$T/kit/requirements.txt"
    else
      python3 -m venv "$T/.venv" && "$T/.venv/bin/pip" install -q -r "$T/kit/requirements.txt"
    fi
    echo "created $T/.venv"
  fi
  "$T/.venv/bin/python" - <<'EOF'
import importlib
for m in ("manim", "kokoro", "soundfile", "faster_whisper", "PIL"):
    importlib.import_module(m)
print("python deps ok")
EOF
fi
echo "done. Activate with: source $T/.venv/bin/activate"
