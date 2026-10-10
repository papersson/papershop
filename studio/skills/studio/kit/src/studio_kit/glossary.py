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


# Words a note may put between a term's words: an object ("blur them together", "ease it out").
BETWEEN = {"it", "them", "this", "these", "those", "that", "everything", "all", "each"}


def _forms(word):
    """A term word and its simple inflections: pan, pans, panned, panning; settle, settles, settled, settling."""
    stem = word[:-1] if word.endswith("e") else word
    return {word, word + "s", word + "es", word + "d", word + "ed", stem + "ing", stem + "ed",
            word + word[-1] + "ed", word + word[-1] + "ing"}


def mentions(term, text):
    """Whether text uses the term: its words adjacent and in order, each in a simple inflection, with at
    most one object word between two of them (BETWEEN: "blur them together" names "blur together"; a
    hyphen counts as a space). "this frame is empty on the right" does not name "frame on"."""
    want, got = [_forms(w) for w in _words(term)], _words(text)
    for start in (i for i, w in enumerate(got) if w in want[0]):
        at = start
        for forms in want[1:]:
            if at + 1 < len(got) and got[at + 1] in forms:
                at += 1
            elif at + 2 < len(got) and got[at + 1] in BETWEEN and got[at + 2] in forms:
                at += 2
            else:
                break
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
