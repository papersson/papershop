from studio_kit import script, script_check

SCRIPT = """# T

## Script

### 1. One

> First sentence. Second sentence.
> Third sentence.

*Screen:* s1_01: a box appears. s1_02–s1_03: it moves.

### 2. Two

> Alone here.

*Screen:* a single picture, for the paragraph above.
"""


def test_screen_notes_follow_their_sentence_ids(tmp_path):
    (tmp_path / "SCRIPT.md").write_text(SCRIPT)
    one, two = script.read(tmp_path)
    assert [(n.start, n.end, n.text) for n in one.screen] == [("s1_01", "s1_01", "a box appears."), ("s1_02", "s1_03", "it moves.")]
    assert [(n.start, n.end) for n in two.screen] == [("s2_01", "s2_01")]


def test_stale_screen_cues_are_reported(tmp_path):
    (tmp_path / "SCRIPT.md").write_text(SCRIPT.replace("s1_02–s1_03", "s1_02–s1_07"))
    rows = [r for r in script_check.run(tmp_path) if r["rule"] == "screen"]
    assert len(rows) == 1 and "s1_07" in rows[0]["detail"] and rows[0]["severity"] == "warning"
