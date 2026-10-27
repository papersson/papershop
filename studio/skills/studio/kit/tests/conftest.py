"""Stop before the first test when the machine lacks the studio's tools, with the fix in one line: under
an older Node, the engine tests fail deep inside a subprocess, with nothing pointing at the cause."""
import re
import shutil
import subprocess

import pytest

NODE_MAJOR = 22


def pytest_sessionstart(session):
    problems = [f"{tool} is not on PATH" for tool in ("ffmpeg", "ffprobe", "sox") if not shutil.which(tool)]
    node = shutil.which("node")
    version = subprocess.run([node, "--version"], capture_output=True, text=True).stdout if node else ""
    major = int(re.match(r"v(\d+)", version).group(1)) if version else 0
    if major < NODE_MAJOR:
        problems.append(f"Node {NODE_MAJOR}+ is needed, found {version.strip() or 'none'}")
    if problems:
        pytest.exit("studio's tests can't run here: " + "; ".join(problems) +
                    ". Run them with script/test, which takes the flake's tools, or install them.", returncode=4)
