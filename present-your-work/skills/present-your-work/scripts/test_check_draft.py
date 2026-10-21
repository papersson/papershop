"""Tests for check_draft.py. Run: python3 test_check_draft.py (standard library only)."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_draft as cd  # noqa: E402

SAMPLES = HERE / "samples"

HTML = """<!doctype html><html><head><title>Ignored title</title></head><body>
<header><h1>A draft</h1><p>The agent logs 12 touches per clip.</p></header>
<nav><h2>Contents</h2><ol><li>dev40 in the contents is not text</li></ol></nav>
<h2 id="goal">The goal</h2>
<p>A <dfn>touch</dfn> is any action on the ball.<a class="fnref" href="#fn1">1</a>
On 2026-10-21 the score rose from 0.69 to 0.83 (Section 4), measured in 2026.</p>
<p><span class="sn"><span class="snhead">Reading a clip</span>Each clip is short.</span></p>
<p hidden>Hidden text with B8 and 0.123 is not read.</p>
<figure><svg><text>test40</text><text>0.5</text></svg><figcaption>A chart.</figcaption></figure>
<table><tr><td>pass</td><td>0.91</td></tr></table>
<h2 id="notes">Notes</h2><p id="fn1">A note mentioning q13.</p>
<h2 id="app-glossary"><span class="letter">A</span>Glossary</h2>
<dl><dt>Clip, frame</dt><dd>35 seconds of a broadcast half.</dd></dl>
</body></html>"""


def run(path, *args):
    return subprocess.run([sys.executable, str(HERE / "check_draft.py"), str(path), *args],
                          capture_output=True, text=True)


class Samples(unittest.TestCase):
    def test_passing_sample_breaks_no_rule(self):
        r = cd.analyse(cd.load(SAMPLES / "pass-small.md"), "small")
        self.assertEqual(r.failures, [])
        self.assertEqual(set(r.terms), {"fingerprint"})
        self.assertEqual(r.numbers, {"07:00", "05:40", "08:50"})

    def test_failing_sample_breaks_each_rule_once(self):
        glossary = cd.read_list(SAMPLES / "GLOSSARY.md")
        self.assertEqual(glossary, ["spotter", "B8", "B4"])
        r = cd.analyse(cd.load(SAMPLES / "fail-small.md"), "small", glossary)
        self.assertEqual(r.failures, ["words", "terms", "numbers", "labels", "order"])
        self.assertGreater(r.words, 330)
        self.assertEqual(set(r.terms), {"crowded miss", "receipt", "duplicate"})
        self.assertEqual(r.numbers, {"0.692", "0.838", "0.827", "0.91"})
        kinds = {label: info["kind"] for label, info in r.labels.items()}
        self.assertEqual(kinds, {"spotter": "glossary", "B8": "glossary", "dev40": "letters and digits",
                                 "run_queue": "snake_case", "TCN": "acronym"})
        self.assertEqual([o[0] for o in r.order], ["crowded miss"])

    def test_exit_codes(self):
        self.assertEqual(run(SAMPLES / "pass-small.md", "--size", "small").returncode, 0)
        failing = run(SAMPLES / "fail-small.md", "--size", "small", "--glossary", SAMPLES / "GLOSSARY.md")
        self.assertEqual(failing.returncode, 1)
        self.assertIn("5 of 5 rules broken", failing.stdout)
        self.assertEqual(run(SAMPLES / "missing.md", "--size", "small").returncode, 2)

    def test_known_terms_are_not_labels(self):
        r = cd.analyse(cd.load(SAMPLES / "fail-small.md"), "small", known=["TCN", "dev40"])
        self.assertNotIn("TCN", r.labels)
        self.assertNotIn("dev40", r.labels)


class Html(unittest.TestCase):
    def setUp(self):
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
            f.write(HTML)
        self.path = Path(f.name)
        self.r = cd.analyse(cd.load(self.path), "small")

    def tearDown(self):
        self.path.unlink()

    def test_zones(self):
        zones = {s.title: s.zone for s in self.r.sections}
        self.assertEqual(zones, {"(opening)": "main", "The goal": "main", "Notes": "back",
                                 "A Glossary": "appendix"})

    def test_what_is_read(self):
        words = " ".join(b.text for b in cd.load(self.path))
        for unseen in ("Ignored title", "contents is not text", "Hidden text", "0.123"):
            self.assertNotIn(unseen, words)
        self.assertIn("Reading a clip Each clip", words)
        self.assertNotIn("ball.1", words)

    def test_numbers_terms_labels_order(self):
        # Dates, years and section references are not numbers; table cells are; figures are not.
        self.assertEqual(self.r.numbers, {"12", "0.69", "0.83", "0.91"})
        self.assertEqual(set(self.r.terms), {"touch"})
        self.assertEqual(set(self.r.labels), {"test40"})
        self.assertTrue(self.r.labels["test40"]["figure"])
        self.assertNotIn("q13", self.r.labels)  # the notes are back matter
        # "touches" in the header comes before the definition; "clip" is defined only in the appendix.
        self.assertEqual({(o[0], o[3]) for o in self.r.order}, {("touch", "main"), ("Clip", "appendix")})


class Parts(unittest.TestCase):
    def test_numbers(self):
        text = ("In 2026 the score rose from 0.69 to 0.83 (Section 4.1), 95% of 1,200 clips; see [12]. "
                "The test40 run took 35s, the 3rd took 7:45, and a 35-second clip 2 percent longer.")
        self.assertEqual(cd.find_numbers(text), ["0.69", "0.83", "95%", "1200", "35s", "7:45", "35", "2%"])

    def test_term_keys_and_plurals(self):
        self.assertEqual(cd.term_key("The crowded misses"), "crowded miss")
        self.assertEqual(cd.term_key("categories"), "category")
        self.assertTrue(cd.term_pattern("category", False).search("two categories"))
        self.assertTrue(cd.term_pattern("touch", False).search("Touches"))
        self.assertFalse(cd.term_pattern("dev", False).search("dev40"))

    def test_glossary_list_form(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write("# Glossary\n\n- **dev40**: the forty development clips\n- the sheet — every frame of a second\n")
        try:
            self.assertEqual(cd.read_list(Path(f.name)), ["dev40", "the sheet"])
        finally:
            Path(f.name).unlink()

    def test_markdown_appendix_marker_and_run_in_heads(self):
        md = ("# Title\n\n## Result\n\n*Scope.* The work covered **one league**.\n\n"
              "<!-- appendix -->\n\n## Runs\n\nThe run_queue driver ran B8.\n")
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(md)
        try:
            r = cd.analyse(cd.load(Path(f.name)), "small")
        finally:
            Path(f.name).unlink()
        self.assertEqual(set(r.terms), {"one league"})
        self.assertEqual(r.labels, {})  # labels in the appendix are allowed
        self.assertEqual([s.zone for s in r.sections if s.title == "Runs"], ["appendix"])


if __name__ == "__main__":
    unittest.main()
