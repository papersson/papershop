import copy
import json
import subprocess
from types import SimpleNamespace

import pytest

from studio_kit import cli, review, review_state, reviews
from studio_kit import timeline as tl
from test_render import make_video
from test_review import make as review_video


def test_each_kind_reads_its_own_verdict_line():
    script, frames = reviews.KINDS["script"], reviews.KINDS["frames"]
    assert script.verdict("notes\nVERDICT: REVISE\n...\n  VERDICT: PASS \n") == ("passed", "VERDICT: PASS")
    assert script.verdict("no verdict") == ("findings", None)
    assert frames.verdict("FRAMES: PASS\nlater: FRAMES: FIX\n") == ("passed", "FRAMES: PASS")
    assert frames.verdict("FRAMES: FIX\n")[0] == "findings"


def test_the_script_cap_comes_from_video_json_and_frames_have_none():
    cap = reviews.KINDS["script"].rounds.cap
    assert (cap({}), cap({"economy": True}), cap({"thorough": True}), cap({"max_rounds": 9})) == (3, 2, 6, 9)
    assert reviews.KINDS["frames"].rounds.cap is None and reviews.KINDS["frames"].freshness == "refuse"


def test_review_status_takes_its_roles_from_the_registry_and_frame_as_an_alias(tmp_path, capsys):
    (tmp_path / "video.json").write_text("{}")
    args = cli.build_parser().parse_args(["review-status", str(tmp_path), "frame", "waived", "--reason", "user said so"])
    assert args.role == "frames"
    review_state.main_status(args)
    rec = json.loads((tmp_path / "research" / "reviews" / "frames.json").read_text())
    assert (rec["role"], rec["kind"], rec["status"]) == ("frames", "frames", "waived") and "round" not in rec
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["review-status", str(tmp_path), "director", "waived"])


def test_a_script_receipt_names_its_kind_and_round_and_an_old_receipt_still_counts(tmp_path):
    review_video(tmp_path)
    args = SimpleNamespace(video=tmp_path, round=2, narrative=None, only="student")
    review.main(args, runner=lambda text, cwd: subprocess.CompletedProcess([], 0, "VERDICT: PASS\n", ""))
    p = tmp_path / "research" / "reviews" / "student.json"
    rec = json.loads(p.read_text())
    assert (rec["kind"], rec["round"], rec["status"]) == ("script", 2, "passed")
    p.write_text(json.dumps({k: rec[k] for k in ("role", "revision", "status", "detail", "created")}))
    assert review_state.read(tmp_path, "student")["kind"] == "script"
    review_state.require(tmp_path, "student")


def test_a_sound_edit_keeps_a_frame_review_current_and_a_caption_edit_stales_it(tmp_path):
    t = make_video(tmp_path)
    before = review_state.fingerprint(tmp_path, frames=True)
    sound = copy.deepcopy(t)
    sound["sources"] = ["audio/timings.json", "audio/sfx.json"]
    sound["tracks"]["audio"].append({"file": "audio/sfx.wav", "start": 0.0, "role": "sfx"})
    (tmp_path / "timeline.json").write_text(json.dumps(sound))
    (tmp_path / "narration.json").write_text(json.dumps({"voice": "af_bella"}))
    assert review_state.fingerprint(tmp_path, frames=True) == before
    caption = copy.deepcopy(sound)
    caption["tracks"]["narration"][1]["caption"] = "Two, reworded."
    caption["tracks"]["captions"] = tl.chunk_captions(caption["tracks"]["narration"])
    (tmp_path / "timeline.json").write_text(json.dumps(caption))
    assert review_state.fingerprint(tmp_path, frames=True) != before


def test_a_crlf_script_hashes_its_line_endings_as_before(tmp_path):
    """Receipts written before the registry stay current: the script is hashed as its bytes decode."""
    import hashlib
    review_video(tmp_path)
    p = tmp_path / "SCRIPT.md"
    text = p.read_text().replace("\n", "\r\n")
    p.write_bytes(text.encode())
    from studio_kit.script import sections
    parts = sections(text)
    h = hashlib.sha256()
    h.update(review.learner_brief(tmp_path).encode())
    h.update(review.charter(tmp_path).encode())
    h.update(b"SCRIPT.md")
    h.update("\n".join(parts.get(k, "") for k in ("Argument", "Chain", "Script", "Evidence")).encode())
    assert review_state.fingerprint(tmp_path) == h.hexdigest()
