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
    assert reviews.KINDS["script"].rounds.resets_on == ("structural", "fork")
    assert reviews.KINDS["frames"].rounds.cap is None and reviews.KINDS["frames"].freshness == "record-stale"


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


def frame_cut(video, n=1):
    """A cut record as make_cut writes one, for the sources as they are now."""
    t = tl.load(video)
    d = video / "cuts" / f"cut{n}"
    (d / "stills").mkdir(parents=True)
    (d / "stills" / "s1_01.jpg").write_bytes(b"fixture")
    keys = review_state.review_keys(video, t)
    (d / "cut.json").write_text(json.dumps({"cut": n, "source_revision": review_state.fingerprint(video, frames=True, keys=keys),
                                            "review_keys": keys}))
    return keys


def test_an_older_cuts_frame_review_is_recorded_stale_and_publish_says_what_changed(tmp_path, capsys):
    from studio_kit import publish
    make_video(tmp_path)
    (tmp_path / "video.json").write_text(json.dumps({"teaching_contract": True, "frame_review": True}))
    (tmp_path / "SCRIPT.md").write_text("## Script\n### 1. A\n> One.\n## Evidence\nActual run.\n")
    frame_cut(tmp_path)
    judged = review_state.fingerprint(tmp_path, frames=True)
    assert review_state.fingerprint(tmp_path, frames=True, keys=review_state.review_keys(tmp_path, tl.load(tmp_path))) == judged
    (tmp_path / "scenes" / "s2.tsx").write_text("// s2, edited after the cut\n")
    current = review_state.fingerprint(tmp_path, frames=True)
    assert current != judged

    args = SimpleNamespace(video=tmp_path, cut=1, result=None)
    review_state.main_frames(args)                        # an older cut may still be packaged
    assert "s2 changed since" in capsys.readouterr().out
    manifest = json.loads(next((tmp_path / "research" / "frame_review").glob("cut1-*/manifest.json")).read_text())
    assert manifest["revision"] == judged
    args.result = tmp_path / "response.md"
    args.result.write_text(f"FRAMES: PASS\nREVISION: {current}\n")
    with pytest.raises(SystemExit, match="exact REVISION"):      # the bundle's revision, not the current one
        review_state.main_frames(args)
    args.result.write_text(f"FRAMES: PASS\nREVISION: {judged}\n")
    assert review_state.main_frames(args) == 1
    rec = review_state.read(tmp_path, "frames")
    assert (rec["status"], rec["revision"], rec["cut"], rec["stale"], rec["changed"]) == ("passed", judged, 1, True, "s2")

    review_state.record(tmp_path, "student", review_state.revision(tmp_path, reviews.KINDS["script"]), "waived", "user said so")
    with pytest.raises(SystemExit, match=r"judged cut 1, and s2 changed since: make a fresh cut .* waiver"):
        publish.gate(tmp_path)
    frame_cut(tmp_path, 2)
    review_state.main_frames(SimpleNamespace(video=tmp_path, cut=2, result=None))
    args.cut, args.result = 2, tmp_path / "fresh.md"
    args.result.write_text(f"FRAMES: PASS\nREVISION: {current}\n")
    assert review_state.main_frames(args) == 0 and review_state.read(tmp_path, "frames")["stale"] is False
    review_state.require(tmp_path, "frames")
    args.result.write_text(f"FRAMES: FIX\nREVISION: {current}\n")
    review_state.main_frames(args)
    with pytest.raises(SystemExit, match="missing, stale or unresolved"):     # current, with findings: nothing changed
        review_state.require(tmp_path, "frames")


def test_a_cut_without_a_revision_cannot_be_frame_reviewed(tmp_path):
    make_video(tmp_path)
    (tmp_path / "cuts" / "cut1").mkdir(parents=True)
    (tmp_path / "cuts" / "cut1" / "cut.json").write_text("{}")
    with pytest.raises(SystemExit, match="predates review fingerprints"):
        review_state.main_frames(SimpleNamespace(video=tmp_path, cut=1, result=None))
