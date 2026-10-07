"""Cheap script diagnostics, usable before a timeline or browser exists."""
import json
import re
from pathlib import Path

from . import settings
from . import script

META = re.compile(r"\b(?:this video|the [\w-]+ video|this repo|this session|we decided|you're learning this|"
                  r"SCRIPT\.md|CLAUDE\.md|AGENTS\.md)\b", re.I)
NUMBER = re.compile(r"(?<!\w)\d+(?:[.,]\d+)*(?:%|\b)")


def run(video):
    video = Path(video)
    text = (video / "SCRIPT.md").read_text()
    cfg = settings.load(video)
    chapters = script.read(video)
    sections = script.sections(text)
    policy = cfg.get("script_check", {})
    rows = []

    def add(where, detail, severity="warning", rule="style"):
        if f"{rule}:{where}" not in policy.get("accept", []):
            rows.append({"check": "script", "clip": where, "ok": severity != "error", "severity": severity,
                         "rule": rule, "detail": detail})

    if cfg.get("genre", "explainer") == "explainer":
        arg = sections.get("Argument", "")
        for field in ("Audience", "Model delta", "Key ideas", "Recurring example", "Transfer questions"):
            match = re.search(rf"^\s*- \*\*{field}[.:]?\*\*\s*(.+)$", arg, re.M | re.I)
            if not match or "{{" in match[1]:
                add("Argument", f"fill in {field}", "error" if cfg.get("teaching_contract") else "warning", "brief")
        predictions = [s for c in chapters for s in c.sentences if s.prediction and (s.pause or 0) >= 2]
        if len(predictions) < 2:
            add("Script", f"{len(predictions)} prediction pauses of at least 2s; review whether the viewer gets real attempts", rule="prediction")
        chain = sections.get("Chain", "")
        if re.search(r"lines?\s+\d+\s*[-–:]|line.by.line|^\d+\.\s+(?:imports|initialization|cleanup)\b", chain, re.I | re.M):
            add("Chain", "possible source tour: organize around needs and key ideas, with reference coverage separately", rule="tour")
    names = policy.get("products", {})
    if isinstance(names, list):
        names = {n: [] for n in names}
    for chapter in chapters:
        found_names = set()
        for s in chapter.sentences:
            for hit in META.finditer(s.text):
                add(s.id, f"production self-reference {hit.group()!r} at SCRIPT.md:{s.line}", rule="meta")
            for name, aliases in names.items():
                if any(re.search(rf"(?<!\w){re.escape(n)}(?!\w)", s.text, re.I) for n in [name, *aliases]):
                    found_names.add(name)
            nums = NUMBER.findall(s.text)
            if nums:
                add(s.id, f"narration numerals: {', '.join(nums)}", "info", "numbers")
        add(chapter.id, f"distinct declared product names: {len(found_names)} ({', '.join(sorted(found_names)) or 'none'})",
            "warning" if len(found_names) > policy.get("product_budget", 3) else "info", "products")
    labels = re.findall(r"^\*Screen:\*\s*(.*)$", sections.get("Script", ""), re.M)
    add("Screen", f"{len(NUMBER.findall(' '.join(labels)))} numerals in screen notes; arbitrary scene text is not counted", "info", "numbers")
    ledger = sections.get("Ledgers", "")
    remember = re.search(r"\*\*Numbers to remember\.\*\*\s*(.*)", ledger)
    if remember:
        n = len(NUMBER.findall(remember[1]))
        add("Ledgers", f"{n} quantities to remember (budget {policy.get('number_budget', 3)}); data/identifiers are separate",
            "warning" if n > policy.get("number_budget", 3) else "info", "budget")
    if cfg.get("target_minutes"):
        from .narration import Settings, estimate_durations, layout
        S = Settings(video)
        tuples = script.load(video)
        seconds = layout(S, tuples, estimate_durations(S, tuples))["total"]
        if seconds > float(cfg["target_minutes"]) * 120:
            add("Runtime", f"estimated {seconds / 60:.1f} min exceeds twice target {cfg['target_minutes']} min; justify scope before building", rule="length")
    return rows
