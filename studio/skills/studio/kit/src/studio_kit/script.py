"""SCRIPT.md: the video's narration, its single source of truth.

Every "> " line under a "### N. Title" heading in the "## Script" section is a paragraph of
narration, split here into sentences with ids like s2_13 (chapter 2, sentence 13). Chapter N is
scene clip sN.
"""
import re
from pathlib import Path


def sections(text):
    """{heading: section text including its "## " line} for every level-2 heading."""
    parts = re.split(r"^## ", text, flags=re.M)
    return {p.split("\n", 1)[0].strip(): "## " + p for p in parts[1:]}


def load(video):
    """[(chapter id, title, [(sentence id, caption text, paragraph index)])]."""
    text = (Path(video) / "SCRIPT.md").read_text(encoding="utf-8")
    s = sections(text)
    if "Script" not in s:
        raise SystemExit("SCRIPT.md has no '## Script' section")
    chapters = []
    for block in re.split(r"^### ", s["Script"], flags=re.M)[1:]:
        head, rest = block.split("\n", 1)
        num, title = head.split(". ", 1)
        cid = f"s{int(num)}"
        sentences, n = [], 0
        paras = [line[2:].strip() for line in rest.splitlines() if line.startswith("> ")]
        for pi, para in enumerate(paras):
            for sent in re.split(r'(?<=[.!?])\s+(?=[A-Z"])', para):
                n += 1
                sentences.append((f"{cid}_{n:02d}", sent.strip(), pi))
        chapters.append((cid, title.strip(), sentences))
    if not chapters:
        raise SystemExit("SCRIPT.md's Script section has no '### 1. Title' chapters")
    return chapters
