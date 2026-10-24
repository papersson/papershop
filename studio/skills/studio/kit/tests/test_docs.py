"""The skill's instructions point at real files and real commands, and each rule has one home.

Agents guessed paths that did not exist and re-read rules copied into six files, so these checks
keep the references and the commands honest as the docs move."""
import re
from pathlib import Path

from studio_kit import cli
from studio_kit.env import ROOT

DOCS = [ROOT / "SKILL.md", ROOT / "DESIGN.md", *sorted((ROOT / "references").rglob("*.md")),
        *sorted((ROOT / "prompts").rglob("*.md"))]
SKILL_DOCS = {p.name for p in (ROOT / "references").rglob("*.md")}
GONE = set()
PREFIXES = ("references/", "taste/", "../")


def mentioned_docs(text):
    return re.findall(r"`([\w./-]+\.md)`", text) + re.findall(r"(?<![\w/.])((?:references|prompts)/[\w./-]+\.md)", text)


def test_every_skill_file_the_instructions_name_exists():
    missing = []
    for doc in DOCS:
        for name in mentioned_docs(doc.read_text()):
            if not (name.startswith(PREFIXES) or Path(name).name in SKILL_DOCS | GONE):
                continue          # a video's own file (SCRIPT.md, research/brief.md)
            bases = (doc.parent, ROOT, ROOT / "references")
            if not any((b / name).resolve().is_file() for b in bases):
                missing.append(f"{doc.relative_to(ROOT)}: {name}")
    assert not missing, "\n".join(missing)


def test_every_command_the_instructions_name_is_a_command():
    unknown = []
    for doc in DOCS:
        for cmd in re.findall(r"`studio ([a-z][a-z-]*)", doc.read_text()):
            if cmd not in cli.COMMANDS:
                unknown.append(f"{doc.relative_to(ROOT)}: studio {cmd}")
    assert not unknown, "\n".join(unknown)


def test_core_reading_stays_small():
    names = ("taste", "story", "shoot", "desk", "kit")
    docs = [ROOT / "SKILL.md", *(ROOT / "references" / f"{n}.md" for n in names)]
    words = sum(len(p.read_text().split()) for p in docs)
    assert words < 12000, f"Core instructions contain {words} words"


def test_skill_md_stays_a_router():
    lines = (ROOT / "SKILL.md").read_text().splitlines()
    assert len(lines) <= 120, f"SKILL.md has {len(lines)} lines: move detail to the reference that owns it"
