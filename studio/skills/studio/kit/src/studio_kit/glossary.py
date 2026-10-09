"""The motion glossary: the words a note can use for motion, each one move the scenes can make.

The terms live in engines/live/src/glossary.json ({term, what, ask, live, remotion}); the live
engine's glossary.html shows each one looping, and the desk links to it from the note box. When a
note names a move the glossary lacks, add the term (with its helper) and a demo in glossary.js, so
the next note can use the word.
"""
import json
import re

from .env import engine_dir


def terms():
    return json.loads((engine_dir("live") / "src" / "glossary.json").read_text())


def _words(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def mentions(term, text):
    """Whether text uses the term: its words in order, at most two other words between them, so
    "blur them together" names "blur together" (a hyphen counts as a space)."""
    want, got = _words(term), _words(text)
    for start in (i for i, w in enumerate(got) if w == want[0]):
        at = start
        for w in want[1:]:
            nxt = next((j for j in range(at + 1, min(len(got), at + 4)) if got[j] == w), None)
            if nxt is None:
                break
            at = nxt
        else:
            return True
    return False


def find(text):
    """The glossary terms a note's text mentions."""
    return [g for g in terms() if mentions(g["term"], text)]


def main(args):
    rows = terms()
    if args.term:
        rows = [g for g in rows if g["term"] == args.term] or find(args.term)
        if not rows:
            raise SystemExit(f"no glossary term {args.term!r}")
    for g in rows:
        print(f"{g['term']}: {g['what']}\n  ask: \"{g['ask']}\"\n  live: {g['live']}\n  remotion: {g['remotion']}")
    return 0
