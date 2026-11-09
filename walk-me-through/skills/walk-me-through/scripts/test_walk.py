#!/usr/bin/env python3
"""Tests for walk-me-through: the click list lint, the starter page, and the checker on good and
deliberately broken pages. The browser tests need a headless Chrome and are skipped, with the fix
named, on a machine without one.

    python3 -I scripts/test_walk.py
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walklib  # noqa: E402

SKILL = HERE.parent
CHROME = walklib.find_chrome()
needs_chrome = unittest.skipUnless(CHROME, walklib.NO_BROWSER)

THREE = {
    "title": "How a cache hit works",
    "chapters": ["A request arrives", "The cache answers", "The same thing as code"],
    "clicks": [
        {"chapter": 1, "change": "The request chip appears at the left", "caption": "One real request, kept for the whole page."},
        {"chapter": 1, "change": "The key is computed from the path"},
        {"chapter": 2, "change": "The key glides into the cache card", "caption": "The cache is keyed by path."},
        {"chapter": 2, "change": "The matching row lights"},
        {"chapter": 3, "change": "The code appears with margin numbers", "caption": "The margin numbers are the clicks above."},
    ],
}


def script(name, *args):
    return subprocess.run([sys.executable, "-I", str(HERE / name), *map(str, args)], capture_output=True, text=True)


class Lint(unittest.TestCase):
    def problems(self, **click):
        spec = json.loads(json.dumps(THREE))
        spec["clicks"][0].update(click)
        return walklib.lint(spec)[0]

    def test_clean_list(self):
        self.assertEqual(walklib.lint(THREE)[0], [])

    def test_fourteen_word_caption(self):
        caption = "This caption runs on for fourteen words, which is two more than we allow."
        self.assertEqual(len(walklib.words(caption)), 14)
        self.assertIn("click 1 caption has 14 words, the limit is 12", self.problems(caption=caption))

    def test_semicolon(self):
        self.assertTrue(any("semicolon" in p for p in self.problems(caption="The key is hashed; then it is stored.")))

    def test_em_dash_and_two_sentences(self):
        self.assertTrue(any("dash" in p for p in self.problems(caption="The key — hashed once")))
        self.assertTrue(any("one sentence" in p for p in self.problems(caption="It hashes. It stores.")))

    def test_code_spans_are_not_prose(self):
        self.assertEqual(self.problems(caption="Then `a; b` runs and `x.y` is set."), [])

    def test_chapter_out_of_range_and_missing_change(self):
        self.assertTrue(any("chapter 4" in p for p in self.problems(chapter=4)))
        self.assertIn("click 1 does not say what changes (give it a 'change')", self.problems(change=""))

    def test_numbered_chapter_title(self):
        spec = dict(THREE, chapters=["1. A request arrives", *THREE["chapters"][1:]])
        self.assertTrue(any("starts with a number" in p for p in walklib.lint(spec)[0]))

    def test_markdown_rejects_and_accepts(self):
        with tempfile.TemporaryDirectory() as tmp:
            good, bad = Path(tmp, "good.json"), Path(tmp, "bad.json")
            good.write_text(json.dumps(THREE))
            spec = json.loads(json.dumps(THREE))
            spec["clicks"][2]["caption"] = "The cache is keyed by path; nothing else matters here."
            bad.write_text(json.dumps(spec))
            ok = script("new_page.py", good, "--markdown")
            self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
            self.assertIn("## The cache answers", ok.stdout)
            self.assertIn("   > The cache is keyed by path.", ok.stdout)
            no = script("new_page.py", bad, "--markdown")
            self.assertEqual(no.returncode, 1)
            self.assertIn("click 3 caption has a semicolon", no.stdout)
            refused = script("new_page.py", bad, Path(tmp, "out"))
            self.assertEqual(refused.returncode, 1)
            self.assertFalse(Path(tmp, "out", "page.html").exists())


class Copies(unittest.TestCase):
    def test_shipped_pages_carry_the_current_engine(self):
        for page in ("example", "pieces"):
            for name in ("walk.js", "walk.css"):
                self.assertEqual((SKILL / "assets" / page / name).read_bytes(), (SKILL / "engine" / name).read_bytes(),
                                 f"assets/{page}/{name} is stale: copy engine/{name} over it")

    def test_values(self):
        run = subprocess.run([sys.executable, "-I", str(SKILL / "assets/example/values.py")], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("fig", run.stdout)


def broken_page(tmp, objects, clicks, chapters=("One",), **extra):
    """A page directory with the engine and the given definition."""
    out = Path(tmp)
    for name in ("walk.js", "walk.css"):
        shutil.copyfile(SKILL / "engine" / name, out / name)
    definition = dict({"title": "Broken", "chapters": list(chapters), "objects": objects, "clicks": clicks}, **extra)
    (out / "page.html").write_text('<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="walk.css">'
                                   f'<body><script src="walk.js"></script><script>Walk.page({json.dumps(definition)})</script>')
    return out


def text(t, x, y, ch=None, **kw):
    o = {"piece": "text", "text": t, "states": {"a": {"x": x, "y": y}, "b": {"x": x + 300, "y": y}}, **kw}
    if ch:
        o["ch"] = ch
    return o


@needs_chrome
class Checker(unittest.TestCase):
    def check(self, out):
        run = script("check.py", out, "--sizes", "1440x900")
        return run.returncode, run.stdout

    def test_shipped_pages_pass_at_three_sizes(self):
        for page in ("example", "pieces"):
            run = script("check.py", SKILL / "assets" / page)
            self.assertEqual((run.returncode, run.stdout), (0, ""), page)

    def test_starter_page_runs_and_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "clicks.json").write_text(json.dumps(THREE))
            built = script("new_page.py", Path(tmp, "clicks.json"), Path(tmp, "out"))
            self.assertEqual(built.returncode, 0, built.stderr)
            run = script("check.py", Path(tmp, "out"))
            self.assertEqual((run.returncode, run.stdout), (0, ""))
            self.assertIn("5 placeholders left", run.stderr)

    def test_catches_broken_pages(self):
        cases = {
            "click 2 changes nothing": (
                {"a": text("alpha", 100, 200)},
                [{"chapter": 1, "object": "a", "state": "a"}, {"chapter": 1, "object": "a", "state": "a"}]),
            "click 3 changes 2 objects (a, b)": (  # b re-enters chapter 1 with its start state as a moves
                {"a": text("alpha", 100, 200), "b": text("beta", 100, 400, ch=[1, 3], start="a")},
                [{"chapter": 1, "object": "a", "state": "a"}, {"chapter": 2, "object": "a", "state": "b"},
                 {"chapter": 3, "object": "a", "state": "a"}]),
            "text overlaps: a \"alpha\" and b \"alpha\"": (
                {"a": text("alpha", 100, 200), "b": text("alpha", 110, 205)},
                [{"chapter": 1, "object": "a", "state": "a"}, {"chapter": 1, "object": "b", "state": "a"}]),
            "text runs outside the stage": (
                {"a": text("alpha", 1550, 200)}, [{"chapter": 1, "object": "a", "state": "a"}]),
            "more than one line (1400px)": (
                {"a": text("alpha", 100, 200)},
                [{"chapter": 1, "object": "a", "state": "a",
                  "caption": "Pneumonoultramicroscopic supercalifragilistic antidisestablishmentarianism floccinaucinihilipilification."}]),
            "highlight '.nope' matches nothing": (
                {"a": text("alpha", 100, 200)}, [{"chapter": 1, "object": "a", "state": "a", "highlight": ".nope"}]),
            "is a clear that hides nothing": (
                {"a": text("alpha", 100, 200)},
                [{"chapter": 1, "object": "a", "state": "a"}, {"chapter": 1, "clear": True, "keep": ["a"]}]),
            "object text sits in the caption band": (
                {"a": text("alpha", 100, 780)}, [{"chapter": 1, "object": "a", "state": "a"}]),
            "page error: click 1 names unknown object 'nope'": (
                {"a": text("alpha", 100, 200)}, [{"chapter": 1, "object": "nope", "state": "a"}]),
            "page error: tree: no row at 'x.y'": (
                {"t": {"piece": "tree", "data": {"x": 1}, "states": {"a": {"x": 100, "y": 200, "cls": ["lit:x.y"]}}}},
                [{"chapter": 1, "object": "t", "state": "a"}]),
        }
        for expected, (objects, clicks) in cases.items():
            chapters = sorted({c["chapter"] for c in clicks})
            with self.subTest(expected), tempfile.TemporaryDirectory() as tmp:
                out = broken_page(tmp, objects, clicks, chapters=[f"Part {'abc'[i - 1]}" for i in chapters])
                code, stdout = self.check(out)
                self.assertEqual(code, 1, stdout)
                self.assertIn(expected, stdout)

    def test_drift_from_the_approved_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = broken_page(tmp, {"a": text("alpha", 100, 200)},
                              [{"chapter": 1, "object": "a", "state": "a", "caption": "Alpha arrives."}])
            Path(out, "clicks.json").write_text(json.dumps(
                {"title": "Broken", "chapters": ["One"], "clicks": [{"chapter": 1, "change": "alpha shows", "caption": "Alpha appears."}]}))
            code, stdout = self.check(out)
            self.assertEqual(code, 1)
            self.assertIn("click 1 caption differs from the approved list", stdout)

    def test_hash_opens_finished_and_mid_freezes(self):
        """#7 opens click 7 finished; ?mid freezes part way. Read from the DOM, not a screenshot."""
        page = walklib.page_url(SKILL / "assets/example", "", "7")
        dom = walklib.run_chrome(CHROME, (1440, 900), page, ["--dump-dom"]).stdout
        self.assertIn('class="w-count">7/22<', dom)
        mid = walklib.page_url(SKILL / "assets/example", "mid=7&at=450")
        dom = walklib.run_chrome(CHROME, (1440, 900), mid, ["--dump-dom"]).stdout
        self.assertIn('class="w-count">7/22<', dom)


if __name__ == "__main__":
    unittest.main(verbosity=1)
