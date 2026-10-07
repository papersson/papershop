"""Scoped source checkpoints; media retention is independent of Git history."""
import json
import os
import signal
import subprocess
import tempfile
from pathlib import Path

from . import settings

GITIGNORE = """.cache/
audio/*.wav
cuts/*/*
!cuts/*/cut.json
out/
__pycache__/
"""
PATHS = ("SCRIPT.md", "video.json", "narration.json", "lexicon.json", "layout.json", "timeline.json", ".gitignore",
         "research", "scenes", "sims", "data", "assets", "review", "cuts", "audio", ".studio")


def init(video):
    video = Path(video)
    r = subprocess.run(["git", "-C", str(video), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if r.returncode:
        subprocess.run(["git", "-C", str(video), "init", "-q"], check=True)


def commit(video, message):
    video = Path(video).resolve()
    init(video)
    cfg = settings.raw(video).get("git", {})
    sign = cfg.get("sign")
    if sign is not None and not isinstance(sign, bool):
        raise SystemExit("video.json git.sign must be true, false, or null (inherit)")
    base = ["git", "-C", str(video)]
    # Use a private index so unrelated staged files can never enter this commit.
    with tempfile.TemporaryDirectory(prefix="studio-index-") as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
        head = subprocess.run(base + ["rev-parse", "--verify", "HEAD"], capture_output=True)
        subprocess.run(base + ["read-tree", "HEAD"] if head.returncode == 0 else base + ["read-tree", "--empty"], env=env, check=True)
        tracked = subprocess.run(base + ["ls-files", "-z"], capture_output=True, text=True, check=True).stdout.split("\0")
        paths = [p for p in PATHS if (video / p).exists() or any(x == p or x.startswith(p + "/") for x in tracked)]
        subprocess.run(base + ["add", "-A", "--", *paths], env=env, check=True)
        changed = subprocess.run(base + ["diff", "--cached", "--quiet"], env=env)
        if changed.returncode == 0:
            return "no source changes to commit"
        command = base + ([] if sign is None else ["-c", f"commit.gpgsign={'true' if sign else 'false'}"])
        p = subprocess.Popen(command + ["commit", "-m", message], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, start_new_session=True)
        try:
            out, err = p.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.communicate()
            raise SystemExit("commit timed out (check signer/hooks); set git.sign=false only if unsigned commits are authorized")
        if p.returncode:
            raise SystemExit(f"commit failed: {err.strip()}")
        # Bring just the video's paths in the real index up to the new commit; leave other staged work alone.
        subprocess.run(base + ["reset", "-q", "HEAD", "--", *paths], check=True)
        return out.strip()


def main(args):
    print(commit(args.video, args.message))
