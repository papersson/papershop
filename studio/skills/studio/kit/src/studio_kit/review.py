"""Run a reviewer with only the supplied material in an empty working directory."""
import os
import shlex
import shutil
import tempfile

from . import proc


def run_reviewer(text, runner=None):
    command = shlex.split(os.environ.get("STUDIO_REVIEW_COMMAND") or "claude -p")
    if runner is None and (not command or not shutil.which(command[0])):
        raise RuntimeError("No reviewer command is available. Set STUDIO_REVIEW_COMMAND or install claude.")
    runner = runner or (lambda prompt, cwd: proc.run(command, input=prompt, capture_output=True,
                                                    text=True, timeout=1800, cwd=cwd))
    with tempfile.TemporaryDirectory(prefix="studio-review-") as empty:
        result = runner(text, empty)
    if result.returncode or not result.stdout.strip():
        detail = (result.stderr or "").strip()[-500:] or f"exit {result.returncode}, no output"
        raise RuntimeError(f"Reviewer unavailable: {detail}")
    return result.stdout
