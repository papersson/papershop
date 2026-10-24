import json
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from studio_kit import moments, motion_review
from studio_kit import timeline as tl
from test_render import make_video


def test_a_sequence_can_put_its_time_fourth():
    t = {"fps": 30, "tracks": {"scene": [{"id": "s1", "start": 0.0, "end": 4.0}]}}
    m = moments.sequence(t, "s1", 1.0, 12, 15, "motion", before=3)
    assert m["frames"][3] == 1.0 and m["frames"][0] == 0.8 and len(m["frames"]) == 12
    assert m["id"] == "motion_s1_1.0_15fps_3b" and moments.sequence(t, "s1", 1.0)["id"] == "strip_s1_1.0"


NAMES = ["drop", "drop_2", "flip_2", "move_s2_0.5"]


def rows(text):
    found, _, _ = motion_review.parse(text, NAMES)
    return [(f["severity"], f["window"], f["t"], f["frame"], f["text"]) for f in found]


def test_findings_are_parsed_through_format_drift():
    text = """Window by window.
1. **MUST FIX** | drop | 1.0 s | frame 30 | the token pops in. Fix: ease it in over 4 frames
- should-fix — move_s2_0.5 — 2.6s — frame 78 — a jerk mid-move. Fix: even the spacing
- Nit: drop, 1.07 s: the shadow lags
**drop_2** — the card swells late. Severity: SHOULD FIX
GAG | drop | 2/5 | the take is too short
MUST FIX 1 · SHOULD FIX 2 · NIT 1
MOTION: FIX"""
    found, _, gags = motion_review.parse(text, NAMES)
    assert [(f["severity"], f["window"], f["t"], f["frame"]) for f in found] == [
        ("must-fix", "drop", 1.0, 30), ("should-fix", "move_s2_0.5", 2.6, 78), ("nit", "drop", 1.07, None),
        ("should-fix", "drop_2", None, None)]
    assert found[0]["text"] == "the token pops in. Fix: ease it in over 4 frames"
    assert gags == [{"window": "drop", "score": 2, "text": "the take is too short"}]


def test_counts_lines_and_the_regression_check_are_never_findings():
    """The reviewer's probes: each of these made a false must-fix that blocked publish."""
    assert rows("SHOULD FIX | drop | 1.0 s | frame 30 | lag\nMUST FIX: 0 · SHOULD FIX: 1 · NIT: 0") == \
        rows("SHOULD FIX | drop | 1.0 s | frame 30 | lag\nMUST FIX 0 | SHOULD FIX 1 | NIT 0") == \
        [("should-fix", "drop", 1.0, 30, "lag")]
    assert rows("MUST FIX 0 • SHOULD FIX 1 • NIT 0") == rows("Must fix: 0") == []
    assert rows("Regressions:\n- MUST FIX | drop | 1.0 s | frame 30 | pop — fixed.\n\nSHOULD FIX | flip_2 | 2 s | frame 60 | lag") \
        == [("should-fix", "flip_2", 2.0, 60, "lag")]
    assert rows("## Previous round\n- MUST FIX | drop | 1.0 s | frame 30 | pop\n## This round\nNIT | drop | 1 s | f30 | x") == \
        [("nit", "drop", 1.0, 30, "x")]
    assert rows("Should fix rounds be needed, ping me.\nMust fix nothing else.") == []


def test_tables_headings_checkboxes_and_unicode_hyphens_are_findings():
    table = "| Severity | Window | t | Frame | Issue |\n|---|---|---|---|---|\n| MUST FIX | drop | 1.0 s | 30 | pop |\n" \
            "| SHOULD FIX | flip_2 | 2.0 s | 60 | lag |"
    assert rows(table) == [("must-fix", "drop", 1.0, 30, "pop"), ("should-fix", "flip_2", 2.0, 60, "lag")]
    assert rows("## Must fix\n- drop, 1.0 s, frame 30: pop\n## Should fix\n- flip_2 2.0 s: lag") == \
        [("must-fix", "drop", 1.0, 30, "pop"), ("should-fix", "flip_2", 2.0, None, "lag")]
    assert rows("- [ ] MUST FIX | drop | 1.0 s | frame 30 | pop") == [("must-fix", "drop", 1.0, 30, "pop")]
    assert [r[0] for r in rows("Must‑fix | drop | 1.0 s | frame 30 | pop\nShould–fix | flip_2 | 2 s | lag")] == \
        ["must-fix", "should-fix"]
    assert rows("MUST FIX | drop | 1.0 s | frame 30 |\n  the token pops in. Fix: ease") == \
        [("must-fix", "drop", 1.0, 30, "the token pops in. Fix: ease")]
    assert rows("MUST FIX | drop | frame 30 | moves 0.5 s too late") == [("must-fix", "drop", None, 30, "moves 0.5 s too late")]


def test_a_findings_block_is_all_that_is_read_and_regressions_have_their_own():
    text = ("Notes: MUST FIX | drop | 1 s | frame 30 | discussed, not a finding\n```findings\n"
            "SHOULD FIX | drop | 1.2 s | frame 36 | late settle. Fix: shorten it\n```\n"
            "```regressions\nFIXED | drop | the pop is gone\nSTILL | flip_2 | lag\n```\nMOTION: PASS")
    found, regressions, _ = motion_review.parse(text, NAMES)
    assert [(f["severity"], f["text"]) for f in found] == [("should-fix", "late settle. Fix: shorten it")]
    assert regressions == [{"status": "fixed", "window": "drop", "text": "the pop is gone"},
                           {"status": "still", "window": "flip_2", "text": "lag"}]


# --- a video with four chapters and a cut of its own ---------------------------------------------------


@pytest.mark.skipif(not any(f.is_file() for f in motion_review.LABEL_FONTS), reason="none of the label fonts is here")
def test_frame_labels_name_their_font_so_fontconfig_says_nothing(tmp_path, monkeypatch, capfd):
    """drawtext asked fontconfig for a font, which printed "Fontconfig error: Cannot load default
    config file" about a dozen times a review where it had no config."""
    import subprocess
    clip = tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=s=320x180:r=30:d=1", "-pix_fmt", "yuv420p", str(clip)], check=True)
    monkeypatch.setenv("FONTCONFIG_FILE", str(tmp_path / "no-fonts.conf"))
    assert motion_review.sheet(clip, [3, 4, 5, 6], 0, 4, 30, tmp_path / "sheet.png") is True
    assert "Fontconfig" not in capfd.readouterr().err and (tmp_path / "sheet.png").exists()


