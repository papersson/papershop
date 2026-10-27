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


def test_lecture_does_not_need_prediction_pauses(tmp_path):
    (tmp_path / "SCRIPT.md").write_text(SCRIPT)
    rows = script_check.run(tmp_path)
    assert not [r for r in rows if r["severity"] == "warning"]


def test_delivery_tags_open_a_sentence_and_never_reach_its_caption(tmp_path):
    (tmp_path / "SCRIPT.md").write_text(SCRIPT.replace("> First sentence. Second sentence.",
                                                       "> [curious] First sentence. [breath 1] [sighs] Second sentence."))
    first, second, third = script.read(tmp_path)[0].sentences
    assert (first.text, first.tag, first.breath) == ("First sentence.", "[curious]", True)
    assert (second.text, second.tag) == ("Second sentence.", "[sighs]")
    assert third.tag is None


def test_a_delivery_tag_inside_a_sentence_is_refused(tmp_path):
    import pytest
    (tmp_path / "SCRIPT.md").write_text(SCRIPT.replace("First sentence.", "First [quietly] sentence."))
    with pytest.raises(SystemExit, match="start of a sentence"):
        script.read(tmp_path)
