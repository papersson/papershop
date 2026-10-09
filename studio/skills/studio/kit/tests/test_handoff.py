import json
import os
import sys
from types import SimpleNamespace

import pytest

from studio_kit import cli, handoff, page, stage, workspace


@pytest.fixture
def video(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("STUDIO_OWNER", raising=False)
    v = tmp_path / "v"
    v.mkdir()
    (v / "video.json").write_text(json.dumps({"title": "Keys", "mode": "background", "budget": {"polish": 60}}))
    return v


def build_state(v):
    """A build caught mid-stage: a cut with an open note, a frame review out, a stale script review, a request."""
    workspace.main_lock(SimpleNamespace(video=v, action="acquire", owner="builder-3", recover=False))
    stage.mark(v, "scenes", now=0)
    stage.mark(v, "polish", now=600)
    cut = v / "cuts" / "cut2"
    cut.mkdir(parents=True)
    (cut / "cut.json").write_text(json.dumps({"cut": 2, "kind": "cut", "quality": "draft", "created": "2026-10-09 10:00:00",
                                              "source_revision": "older"}))
    page.append(v, {"type": "note", "id": "n1", "cut": 2, "t": 12.0, "clip": "s1", "sentence_id": "s1_02",
                    "sentence": "Keys sort.", "kind": "picture", "note": "too fast"})
    bundle = v / "research" / "frame_review" / "cut2-abc"
    bundle.mkdir(parents=True)
    (bundle / "manifest.json").write_text(json.dumps({"cut": 2, "revision": "abc"}))
    workspace.atomic_json(v / "research" / "reviews" / "student.json",
                          {"role": "student", "revision": "old", "status": "passed", "detail": "r1_student.md"})
    workspace.main_request(SimpleNamespace(video=v, text="add a sidebar", resolve=None))
    workspace.scratch(v).joinpath("probe.py").write_text("print('hi')\n")


def test_the_brief_is_assembled_from_the_files(video):
    build_state(video)
    text = handoff.assemble(video, notes="s3's arrow is drawn by hand; keep it", now=600 + 30 * 60)
    v = '"$VIDEO"'
    assert f"    export VIDEO={video.resolve()}" in text
    assert "- Owner: builder-3 since " in text and "- Mode background, level intro, engine remotion" in text
    assert "- Stage: polish (local), 30m00s since its mark; stage total 30m00s of 1h00m;" in text
    assert "- Last cut: 2 (cut, draft, 2026-10-09 10:00:00)" in text
    assert "n1 (queued, cut 2, s1_02): too fast" in text
    assert "frame review of cut 2 prepared, not imported" in text and "student: stale" in text
    (request,) = workspace.pending(video)
    rid = request.split()[0]
    assert f"  - {request}" in text
    nxt = text.split("## Next")[1].split("## Scratch")[0]
    for step in (f"studio review-frames {v} --cut 2 --result FILE", f"studio review {v} ROUND --only student",
                 f"studio request {v} --resolve {rid}", f"studio notes {v} --resolve n1 --reply TEXT",
                 f"changed after cut 2: `studio cut {v}`", f"studio stage {v} NAME"):
        assert step in nxt, step
    assert ".studio/work: 1 file: probe.py" in text
    assert text.rstrip().endswith("s3's arrow is drawn by hand; keep it")


def test_a_stopped_stage_says_so_first(video):
    stage.mark(video, "polish", now=0)
    text = handoff.assemble(video, now=2 * 3600)
    assert "(STOPPED: past the hard stop)" in text
    assert "1. Stage polish is past its hard stop" in text and "(none given)" in text


def test_recover_prints_the_handoff_and_when_it_was_written(video, capsys):
    build_state(video)
    handoff.write(video, "chapter 3 half done")
    os.utime(handoff.path(video), (1000, 1000))
    stage.mark(video, "cut", now=2000)
    workspace.main_lock(SimpleNamespace(video=video, action="acquire", owner="builder-4", recover=True))
    out = capsys.readouterr().out
    assert "owner: builder-4" in out and "handoff written 1970-01-01T" in out
    assert "1 stage mark since (latest cut at" in out and "chapter 3 half done" in out


def test_recover_without_a_handoff_says_how_to_make_one(video, capsys):
    workspace.main_lock(SimpleNamespace(video=video, action="acquire", owner="b", recover=True))
    assert f"no handoff at {handoff.path(video)}" in capsys.readouterr().out


def test_releasing_an_unfinished_background_build_asks_for_a_handoff(video, capsys):
    release = SimpleNamespace(video=video, action="release", owner="b", recover=True)
    stage.mark(video, "scenes")
    workspace.main_lock(release)
    assert "has no handoff: write one" in capsys.readouterr().out
    handoff.write(video)
    workspace.main_lock(release)
    assert "handoff" not in capsys.readouterr().out
    stage.mark(video, "finished")
    os.utime(handoff.path(video), (0, 0))
    workspace.main_lock(release)
    assert "handoff" not in capsys.readouterr().out
    (video / "video.json").write_text(json.dumps({"mode": "interactive"}))
    stage.mark(video, "scenes")
    workspace.main_lock(release)
    assert "handoff" not in capsys.readouterr().out


def test_handoff_is_written_by_the_owner(video, monkeypatch):
    workspace.main_lock(SimpleNamespace(video=video, action="acquire", owner="b", recover=False))
    with pytest.raises(SystemExit, match="video owned by b"):
        cli.main(["handoff", str(video)])
    notes = video / "notes.txt"
    notes.write_text("from a file")
    monkeypatch.setenv("STUDIO_OWNER", workspace.owner(video)["token"])
    assert cli.main(["handoff", str(video), "--notes-file", str(notes)]) == 0
    assert handoff.path(video).read_text().rstrip().endswith("from a file")


def test_scratch_does_not_block_pinning(video):
    from studio_kit import pin
    workspace.scratch(video)
    assert pin.init(video) == video.resolve() / ".studio"
    with pytest.raises(SystemExit, match="exists: pinned"):
        pin.init(video)
