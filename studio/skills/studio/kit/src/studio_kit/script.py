"""SCRIPT.md: the video's narration, its single source of truth.

Every "> " line under a "### N. Title" heading in the "## Script" section is a paragraph of
narration, split here into sentences with ids like s2_13 (chapter 2, sentence 13). Chapter N is
scene clip sN.
"""
import re
import math
from dataclasses import dataclass, field
from pathlib import Path


def sections(text):
    """{heading: section text including its "## " line} for every level-2 heading."""
    parts = re.split(r"^## ", text, flags=re.M)
    return {p.split("\n", 1)[0].strip(): "## " + p for p in parts[1:]}


@dataclass
class Sentence:
    id: str
    text: str
    paragraph: int
    line: int
    pause: float | None = None
    prediction: bool = False


@dataclass
class Chapter:
    id: str
    title: str
    sentences: list[Sentence] = field(default_factory=list)


def paragraph(text, line, beat):
    """Remove only timing directives, preserving the old splitter for marker-free scripts."""
    clean, events, cursor = "", [], 0
    for m in re.finditer(r"\[(?:pause|predict|beat)[^\]\n]*(?:\]|$)", text):
        clean += text[cursor:m.start()]
        token = re.fullmatch(r"\[(beat|pause|predict)(?: ([0-9]+(?:\.[0-9]+)?))?\]", m.group())
        if not token or (token[1] != "beat" and token[2] is None) or (token[1] == "beat" and token[2]):
            raise SystemExit(f"SCRIPT.md:{line}: invalid pause marker {m.group()!r}")
        seconds = beat if token[1] == "beat" else float(token[2])
        if not math.isfinite(seconds) or seconds < 0:
            raise SystemExit(f"SCRIPT.md:{line}: pause must be a finite nonnegative number")
        if not clean.rstrip().endswith((".", "?", "!", '."', '?"', '!"')):
            raise SystemExit(f"SCRIPT.md:{line}: a pause must follow a complete sentence")
        events.append((len(clean), seconds, token[1] == "predict"))
        cursor = m.end()
    clean += text[cursor:]
    boundaries = list(re.finditer(r'(?<=[.!?])\s+(?=[A-Z"])', clean))
    starts = [0] + [m.end() for m in boundaries]
    ends = [m.start() for m in boundaries] + [len(clean)]
    out = []
    for i, (start, end) in enumerate(zip(starts, ends)):
        end_event = starts[i + 1] if i + 1 < len(starts) else len(clean) + 1
        found = [(seconds, prediction) for pos, seconds, prediction in events if start < pos < end_event]
        if len(found) > 1:
            raise SystemExit(f"SCRIPT.md:{line}: more than one pause on a sentence")
        sentence = clean[start:end].strip()
        if sentence:
            out.append((sentence, *(found[0] if found else (None, False))))
    # A marker is a sentence boundary even before a lowercase continuation; make ambiguity explicit.
    if any(clean[pos:].strip() and not re.match(r'^[A-Z"]', clean[pos:].strip()) for pos, _, _ in events):
        raise SystemExit(f"SCRIPT.md:{line}: start a new sentence or paragraph after a pause")
    return out


def read(video, beat=0.5):
    text = (Path(video) / "SCRIPT.md").read_text(encoding="utf-8")
    chapters, active, chapter, pi = [], False, None, 0
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            active = line.strip() == "## Script"
        if not active:
            continue
        if line.startswith("### "):
            m = re.fullmatch(r"### (\d+)\. (.+)", line)
            if not m:
                raise SystemExit(f"SCRIPT.md:{lineno}: expected '### 1. Title'")
            chapter = Chapter(f"s{int(m[1])}", m[2].strip())
            if any(c.id == chapter.id for c in chapters):
                raise SystemExit(f"SCRIPT.md:{lineno}: duplicate chapter {chapter.id}")
            chapters.append(chapter)
            pi = 0
        elif line.startswith("> ") and chapter:
            for cap, pause, prediction in paragraph(line[2:].strip(), lineno, beat):
                chapter.sentences.append(Sentence(f"{chapter.id}_{len(chapter.sentences)+1:02d}", cap, pi,
                                                  lineno, pause, prediction))
            pi += 1
    if not chapters or any(not c.sentences for c in chapters):
        raise SystemExit("SCRIPT.md needs a '## Script' section with narrated '### 1. Title' chapters")
    return chapters


def load(video):
    """Compatibility view: [(chapter id, title, [(sentence id, caption text, paragraph index)])]."""
    return [(c.id, c.title, [(s.id, s.text, s.paragraph) for s in c.sentences]) for c in read(video)]


def append_review(video, entry):
    p = Path(video) / "SCRIPT.md"
    text = p.read_text()
    match = re.search(r"^## Review log\s*$", text, re.M)
    if not match:
        text += "\n## Review log\n\n- " + entry + "\n"
    else:
        end = re.search(r"^## ", text[match.end():], re.M)
        at = match.end() + end.start() if end else len(text)
        text = text[:at].rstrip() + "\n\n- " + entry + "\n\n" + text[at:]
    p.write_text(text)
