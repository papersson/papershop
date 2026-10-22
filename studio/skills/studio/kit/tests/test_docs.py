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
GONE = {"style.md"}                  # moved into references/taste/ and audio.md
PREFIXES = ("references/", "prompts/", "taste/", "genres/", "../")


def mentioned_docs(text):
    return re.findall(r"`([\w./-]+\.md)`", text) + re.findall(r"(?<![\w/.])((?:references|prompts)/[\w./-]+\.md)", text)


def test_every_skill_file_the_instructions_name_exists():
    missing = []
    for doc in DOCS:
        for name in mentioned_docs(doc.read_text()):
            if not (name.startswith(PREFIXES) or Path(name).name in SKILL_DOCS | GONE):
                continue          # a video's own file (SCRIPT.md, research/narrative.md, house.md)
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


def test_each_rule_has_one_home():
    # A phrase only the rule's home states; elsewhere the rule is a pointer.
    homes = {"plateaued at 25 to 45": "references/reviews.md",
             "at twice that budget": "references/ownership.md",
             "Package first, then dispatch": "references/reviews.md",
             "Go ahead\" covers the next gate": "references/gates.md",
             "Introduce, settle, explain, move on": "references/session.md"}
    for phrase, home in homes.items():
        found = [str(d.relative_to(ROOT)) for d in DOCS if phrase in d.read_text()]
        assert found == [home], (phrase, found)


def test_skill_md_stays_a_router():
    lines = (ROOT / "SKILL.md").read_text().splitlines()
    assert len(lines) <= 110, f"SKILL.md has {len(lines)} lines: move detail to the reference that owns it"
