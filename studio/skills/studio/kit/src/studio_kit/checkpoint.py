"""Scoped source checkpoints; media retention is independent of Git history.

A commit takes every file in the video's folder that its .gitignore lets through, so a source
folder a new command writes (boards/, captures/) is never left out the way an allowlist left it.
The ignore rules keep out what is media or regenerable: renders, recordings and sound, caches,
outputs, package folders, and every file of a cut but its record (clean and cut retention manage
those files, not Git).
"""
import json
import os
import signal
import tempfile
from pathlib import Path

from . import proc
from . import settings

GITIGNORE = """.cache/
out/
cuts/*/*
!cuts/*/cut.json
*.mp4
*.mov
*.m4v
*.mkv
*.webm
*.wav
*.mp3
*.m4a
node_modules/
.venv/
.studio/work/
__pycache__/
.DS_Store
"""


def ignore(video):
    """Append the GITIGNORE lines the video's .gitignore lacks, so a video made under older rules
    keeps its media out too; the builder's own lines stay. A file Git already tracks stays tracked."""
    p = Path(video) / ".gitignore"
    text = p.read_text() if p.exists() else ""
    missing = [line for line in GITIGNORE.splitlines() if line not in text.splitlines()]
    if missing:
        p.write_text(text + ("\n" if text and not text.endswith("\n") else "") + "\n".join(missing) + "\n")


def init(video):
    video = Path(video)
    git = proc.tool("git")
    r = proc.run([git, "-C", str(video), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if r.returncode:
        proc.run([git, "-C", str(video), "init", "-q"], check=True)


def commit(video, message):
    video = Path(video).resolve()
    init(video)
    cfg = settings.raw(video).get("git", {})
    sign = cfg.get("sign")
    if sign is not None and not isinstance(sign, bool):
        raise SystemExit("video.json git.sign must be true, false, or null (inherit)")
    base = [proc.tool("git"), "-C", str(video)]
    # Use a private index so unrelated staged files can never enter this commit.
    with tempfile.TemporaryDirectory(prefix="studio-index-") as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
        head = proc.run(base + ["rev-parse", "--verify", "HEAD"], capture_output=True)
        proc.run(base + ["read-tree", "HEAD"] if head.returncode == 0 else base + ["read-tree", "--empty"], env=env, check=True)
        ignore(video)
        proc.run(base + ["add", "-A", "--", "."], env=env, check=True)      # the video's folder, in a larger repo too
        changed = proc.run(base + ["diff", "--cached", "--quiet"], env=env)
        if changed.returncode == 0:
            return "no source changes to commit"
        command = base + ([] if sign is None else ["-c", f"commit.gpgsign={'true' if sign else 'false'}"])
        p = proc.popen(command + ["commit", "-m", message], env=env, stdout=proc.PIPE, stderr=proc.PIPE,
                       text=True, start_new_session=True)
        try:
            out, err = p.communicate(timeout=30)
        except proc.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.communicate()
            raise SystemExit("commit timed out (check signer/hooks); set git.sign=false only if unsigned commits are authorized")
        if p.returncode:
            raise SystemExit(f"commit failed: {err.strip()}")
        # Bring just the video's paths in the real index up to the new commit; leave other staged work alone.
        proc.run(base + ["reset", "-q", "HEAD", "--", "."], check=True)
        return out.strip()


def main(args):
    print(commit(args.video, args.message))
