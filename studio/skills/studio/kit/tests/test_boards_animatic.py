import json

from studio_kit import animatic, boards

SCRIPT = """# T

## Script

### 1. One

> First sentence. Second sentence. Third sentence.

*Screen:* s1_02–s1_03: a box moves.

### 2. Two

> Alone here.
"""


def timeline():
    return {"duration": 10.0, "fps": 30,
            "tracks": {"scene": [{"id": "s1", "title": "One", "start": 0.0, "end": 6.0},
                                 {"id": "s2", "title": "Two", "start": 6.0, "end": 10.0}],
                       "narration": [{"id": "s1_01", "clip": "s1", "start": 0.5, "end": 2.0},
                                     {"id": "s1_02", "clip": "s1", "start": 2.0, "end": 4.0},
                                     {"id": "s1_03", "clip": "s1", "start": 4.0, "end": 5.5},
                                     {"id": "s2_01", "clip": "s2", "start": 6.5, "end": 9.0}]}}


def test_notes_cover_their_range_and_are_written_once(tmp_path):
    (tmp_path / "SCRIPT.md").write_text(SCRIPT)
    assert boards.notes(tmp_path) == {"s1_02": "a box moves.", "s1_03": "a box moves."}
    f = boards.write_notes(tmp_path)
    stamp = f.stat().st_mtime_ns
    boards.write_notes(tmp_path)                      # unchanged content is not rewritten
    assert f.stat().st_mtime_ns == stamp


def test_coverage_holds_frames_and_notes_until_the_next(tmp_path):
    (tmp_path / "SCRIPT.md").write_text(SCRIPT)
    (tmp_path / "boards").mkdir()
    (tmp_path / "boards" / "boards.json").write_text(json.dumps({"s2": [{"from": "s2_01", "elements": []}]}))
    assert boards.coverage(tmp_path, timeline()) == {"s1_01": None, "s1_02": "note", "s1_03": "note", "s2_01": "frame"}


def test_each_still_holds_until_the_next_sentence_and_lead_ins_are_covered():
    stills = [{"id": s, "file": f"stills/{s}.jpg"} for s in ("s1_01", "s1_02", "s1_03", "s2_01")]
    segs = animatic.segments(timeline(), stills)
    # Each chapter's lead-in shows its first still, then each still holds to the next sentence.
    assert [f for f, _ in segs] == ["stills/s1_01.jpg", "stills/s1_01.jpg", "stills/s1_02.jpg", "stills/s1_03.jpg",
                                    "stills/s2_01.jpg", "stills/s2_01.jpg"]
    assert [round(d, 2) for _, d in segs] == [0.5, 1.5, 2.0, 2.0, 0.5, 3.5]
    assert abs(sum(d for _, d in segs) - 10.0) < 1e-9
