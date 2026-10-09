import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from studio_kit import checkpoint, cuts, new, preferences, review, review_state, stage, workspace
from test_review import make as review_video
from test_render import make_video


def git(video, *args, env=None):
    return subprocess.run(["git", "-C", str(video), *args], env=env, capture_output=True, text=True, check=True).stdout.strip()


def test_owner_excludes_second_builder_but_metadata_remains_available(tmp_path, monkeypatch):
    args = SimpleNamespace(video=tmp_path, action="acquire", recover=False, owner="first")
    workspace.main_lock(args)
    rec = workspace.owner(tmp_path)
    with pytest.raises(SystemExit, match="already owned"):
        workspace.main_lock(args)
    with pytest.raises(SystemExit, match="owned by first"):
        with workspace.operation(tmp_path):
            pytest.fail("second writer entered")
    monkeypatch.setenv("STUDIO_OWNER", rec["token"])
    with workspace.operation(tmp_path):
        with workspace.locked(tmp_path):
            pass
        with pytest.raises(SystemExit, match="another studio"):
            with workspace.operation(tmp_path):
                pass
    args.action = "release"
    workspace.main_lock(args)
    assert workspace.owner(tmp_path) is None and not (tmp_path / ".studio").exists()


def test_requests_are_resolved_once_and_reported_at_stage_boundaries(tmp_path):
    args = SimpleNamespace(video=tmp_path, text="Add the borrow sidebar", resolve=None)
    workspace.main_request(args)
    pending = (tmp_path / "research/requests.md").read_text()
    rid = pending.split("- [ ] ")[1].split()[0]
    assert any("borrow sidebar" in line for line in stage.mark(tmp_path, "scenes", now=0))
    args.text, args.resolve = None, rid
    workspace.main_request(args)
    assert not any("pending:" in line for line in stage.mark(tmp_path, "cut", now=2))
    with pytest.raises(SystemExit, match="no pending"):
        workspace.main_request(args)


def test_waiting_is_not_active_budget_and_structural_round_has_separate_estimate(tmp_path):
    stage.mark(tmp_path, "research", now=0)
    stage.mark(tmp_path, "waiting", now=10)
    lines = stage.mark(tmp_path, "script", now=1000)
    assert "0m10s into" in lines[1]
    lines = stage.mark(tmp_path, "round", now=1010, kind="structural")
    assert "0m00s into this structural revision round (budget 20m00s)" in lines[1]
    stage.mark(tmp_path, "finished", now=1020)
    assert stage.durations(stage.read(tmp_path), now=9999)[-1][1] == 0


def test_private_checkpoint_preserves_unrelated_staged_changes_and_excludes_media(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    git_env = {**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
               "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com"}
    for k, v in git_env.items():
        if k.startswith("GIT_AUTHOR") or k.startswith("GIT_COMMITTER"):
            monkeypatch.setenv(k, v)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    git(tmp_path, "config", "commit.gpgsign", "false")
    (tmp_path / "unrelated.txt").write_text("original\n")
    git(tmp_path, "add", "unrelated.txt")
    git(tmp_path, "commit", "-m", "initial")
    (tmp_path / "unrelated.txt").write_text("staged elsewhere\n")
    git(tmp_path, "add", "unrelated.txt")
    v, _ = new.create("v", directory=tmp_path / "video")
    cfg = json.loads((v / "video.json").read_text())
    cfg["git"]["sign"] = False
    (v / "video.json").write_text(json.dumps(cfg))
    (v / "cuts/cut1").mkdir(parents=True)
    (v / "cuts/cut1/cut.json").write_text("{}")
    (v / "cuts/cut1/video.mp4").write_bytes(b"video")
    checkpoint.commit(v, "video source checkpoint")
    assert git(tmp_path, "show", "HEAD:unrelated.txt") == "original"
    assert git(tmp_path, "diff", "--cached", "--name-only") == "unrelated.txt"
    assert "video/cuts/cut1/video.mp4" not in git(tmp_path, "ls-tree", "-r", "--name-only", "HEAD")
    assert "video/cuts/cut1/cut.json" in git(tmp_path, "ls-tree", "-r", "--name-only", "HEAD")


OLD_GITIGNORE = ".cache/\naudio/*.wav\ncuts/*/*\n!cuts/*/cut.json\nout/\n__pycache__/\n"


def unsigned(monkeypatch, v):
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "Test")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "test@example.com")
    cfg = json.loads((v / "video.json").read_text())
    cfg["git"] = {"sign": False}
    (v / "video.json").write_text(json.dumps(cfg))


def test_a_checkpoint_takes_every_source_and_leaves_media_and_caches_out(tmp_path, monkeypatch):
    """boards/ and captures/ were missing from the allowlist, so boards were never checkpointed."""
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    v, _ = new.create("v", directory=tmp_path / "video")
    unsigned(monkeypatch, v)
    files = {"boards/boards.json": "[]", "captures/home.png": "png", "notes.txt": "mine", "captions.json": "[]",
             "audio/narration.mp3": "mp3", "audio/sfx.wav": "wav", "assets/talk.mov": "rec", "assets/bed.m4a": "m4a",
             ".cache/clips/s1.mp4": "c", "out/page/index.html": "o", "node_modules/x/index.js": "n",
             ".studio/work/scratch.txt": "w", ".studio/kit/.venv/bin/python": "p", "cuts/cut1/cut.json": "{}",
             "cuts/cut1/stills/s1_01.jpg": "jpg", "cuts/cut1/video.mp4": "mp4"}
    for rel, text in files.items():
        (v / rel).parent.mkdir(parents=True, exist_ok=True)
        (v / rel).write_text(text)
    checkpoint.commit(v, "sources")
    tracked = set(git(v, "ls-tree", "-r", "--name-only", "HEAD").splitlines())
    assert {"boards/boards.json", "captures/home.png", "notes.txt", "captions.json", "cuts/cut1/cut.json",
            "SCRIPT.md", "video.json", ".gitignore"} <= tracked
    assert not tracked & {rel for rel in files if rel not in ("boards/boards.json", "captures/home.png", "notes.txt",
                                                              "captions.json", "cuts/cut1/cut.json")}
    (v / "boards/boards.json").unlink()
    checkpoint.commit(v, "a board removed")
    assert "boards/boards.json" not in git(v, "ls-tree", "-r", "--name-only", "HEAD")


def test_a_video_made_under_the_old_ignore_rules_keeps_working(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    v, _ = new.create("v", directory=tmp_path / "video")
    unsigned(monkeypatch, v)
    (v / ".gitignore").write_text(OLD_GITIGNORE + "my-notes/")          # no final newline, a line of the builder's
    (v / "audio").mkdir()
    (v / "audio/narration.mp3").write_text("mp3")                       # the allowlist took audio/
    git(v, "add", "-A")
    git(v, "commit", "-q", "-m", "made by an older kit")
    (v / "audio/narration.mp3").write_text("mp3, narrated again")
    (v / "assets").mkdir()
    (v / "assets/talk.mp4").write_text("recording")
    (v / "boards").mkdir()
    (v / "boards/boards.json").write_text("[]")
    checkpoint.commit(v, "sources")
    tracked = git(v, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
    assert "boards/boards.json" in tracked and "assets/talk.mp4" not in tracked
    assert git(v, "show", "HEAD:audio/narration.mp3") == "mp3, narrated again"     # tracked stays tracked
    lines = (v / ".gitignore").read_text().splitlines()
    assert lines[:7] == (OLD_GITIGNORE + "my-notes/").splitlines() and "*.[mM][pP]4" in lines
    checkpoint.commit(v, "again")
    assert (v / ".gitignore").read_text().splitlines() == lines


def test_a_checkpoint_leaves_out_secrets_media_in_any_case_and_large_new_files(tmp_path, monkeypatch, capsys):
    """A commit took a top-level .env (an API key) and, where Git compares case, IMG_0001.MOV."""
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    v, _ = new.create("v", directory=tmp_path / "video")
    unsigned(monkeypatch, v)
    git(v, "config", "core.ignorecase", "false")
    files = {".env": "KEY=x", ".env.local": "KEY=y", "footage/IMG_0001.MOV": "rec", "assets/room.AIFF": "a",
             "assets/loop.gif": "g", "assets/bed.Flac": "f", "keys/deploy.pem": "k", "notes.txt": "mine"}
    for rel, text in files.items():
        (v / rel).parent.mkdir(parents=True, exist_ok=True)
        (v / rel).write_text(text)
    with (v / "assets" / "big.zip").open("wb") as f:
        f.truncate(checkpoint.LARGE + 1)
    checkpoint.commit(v, "sources")
    tracked = set(git(v, "ls-tree", "-r", "--name-only", "HEAD").splitlines())
    assert "notes.txt" in tracked and not tracked & (set(files) - {"notes.txt"} | {"assets/big.zip"})
    assert "not committed: assets/big.zip (20 MB)" in capsys.readouterr().out
    git(v, "add", "assets/big.zip")                       # tracked by choice: later commits keep it
    git(v, "commit", "-q", "-m", "the archive, on purpose")
    with (v / "assets" / "big.zip").open("ab") as f:
        f.write(b"more")
    checkpoint.commit(v, "again")
    assert git(v, "diff", "HEAD~1", "HEAD", "--name-only") == "assets/big.zip"
    assert "not committed" not in capsys.readouterr().out


def test_house_lexicon_and_series_are_portable_snapshots(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("STUDIO_HOME", str(home))
    (home / "house.md").write_text("Use quiet diagrams.")
    (home / "lexicon.json").write_text('{"spoken":[["JSON","J S O N"]]}')
    src, _ = new.create("first")
    (src / "data").mkdir()
    (src / "data/rows.json").write_text('[{"id":1}]')
    (src / "scenes/shared.ts").write_text('import rows from "../data/rows.json"; export {rows};')
    nr = json.loads((src / "narration.json").read_text())
    nr["holds"], nr["spoken_by_id"] = {"s1_01": 9}, {"s1_01": [["A", "ay"]]}
    (src / "narration.json").write_text(json.dumps(nr))
    (home / "lexicon.json").write_text('{"spoken":[["JSON","changed"]]}')
    dst, _ = new.create("second")
    files = preferences.inherit(dst, src, ["scenes/shared.ts"])
    assert "data/rows.json" in files
    assert json.loads((dst / "lexicon.json").read_text())["spoken"] == [["JSON", "J S O N"]]
    assert "holds" not in json.loads((dst / "narration.json").read_text())
    (src / "data/rows.json").unlink()
    assert (dst / "data/rows.json").exists()
    assert (dst / "research/house.md").read_text() == "Use quiet diagrams."


def test_student_receipt_is_revision_bound_but_review_log_does_not_stale_it(tmp_path):
    review_video(tmp_path)
    args = SimpleNamespace(video=tmp_path, round=2, narrative=None, only="student")
    review.main(args, runner=lambda text, cwd: subprocess.CompletedProcess([], 0, "VERDICT: PASS\n", ""))
    review_state.require(tmp_path, "student")
    from studio_kit.script import append_review
    append_review(tmp_path, "student passed")
    review_state.require(tmp_path, "student")
    p = tmp_path / "SCRIPT.md"
    p.write_text(p.read_text().replace("A retry can charge twice.", "A retry cannot charge twice."))
    with pytest.raises(SystemExit, match="stale"):
        review_state.require(tmp_path, "student")


def test_student_gets_transfer_cases_not_expected_answers(tmp_path):
    review_video(tmp_path)
    p = tmp_path / "SCRIPT.md"
    p.write_text(p.read_text().replace("## Chain", "- **Transfer questions.** What if an acknowledgement is lost?\n\n## Chain") +
                 "\n## Transfer answers\n\nSecret solution.\n")
    student = review.script_inputs(tmp_path, 2)["student"]
    assert "acknowledgement is lost" in student and "Secret solution" not in student


def test_frame_bundle_requires_matching_cut_and_revision_tagged_response(tmp_path):
    make_video(tmp_path)
    (tmp_path / "SCRIPT.md").write_text("## Script\n### 1. A\n> One.\n## Evidence\nActual run.\n## Review log\nsecret\n")
    cut = tmp_path / "cuts/cut1"
    (cut / "stills").mkdir(parents=True)
    (cut / "stills/s1.jpg").write_bytes(b"fixture")
    revision = review_state.fingerprint(tmp_path, frames=True)
    (cut / "cut.json").write_text(json.dumps({"source_revision": revision}))
    args = SimpleNamespace(video=tmp_path, cut=1, result=None)
    review_state.main_frames(args)
    bundle = next((tmp_path / "research/frame_review").iterdir())
    assert "secret" not in (bundle / "SCRIPT.md").read_text()
    response = tmp_path / "response.md"
    response.write_text("FRAMES: PASS\nREVISION: wrong\n")
    args.result = response
    with pytest.raises(SystemExit, match="exact REVISION"):
        review_state.main_frames(args)
    response.write_text(f"FRAMES: PASS\nREVISION: {revision}\n")
    review_state.main_frames(args)
    review_state.require(tmp_path, "frames")


def test_failed_opener_still_protects_cut(tmp_path, monkeypatch):
    d = tmp_path / "cuts/cut1"
    d.mkdir(parents=True)
    (d / "cut.json").write_text('{"quality":"draft"}')
    (d / "video.mp4").write_bytes(b"movie")
    def fail(*args, **kwargs):
        raise OSError("no player")
    monkeypatch.setattr(cuts.proc, "run", fail)
    with pytest.raises(SystemExit, match="protected, but"):
        cuts.main_open(SimpleNamespace(video=tmp_path, cut=None))
    assert json.loads((d / "cut.json").read_text())["watched"]


def test_review_requirements_separate_drive_depth_and_claim_risk():
    assert not review_state.required_roles({"drive": "learner"})  # legacy projects opt in
    cfg = {"teaching_contract": True, "drive": "author", "level": "intro"}
    assert review_state.required_roles(cfg) == ("student",)
    for override in ({"drive": "learner"}, {"level": "deep-dive"}):
        assert review_state.required_roles({**cfg, **override}) == ("student", "expert", "editor")
    assert review_state.required_roles({**cfg, "review_roles": ["expert"]}) == ("student", "expert")
