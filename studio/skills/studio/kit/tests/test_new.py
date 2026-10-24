import json

import pytest

from studio_kit import new, narration, script


def test_new_video_is_ready_for_a_script_and_an_estimate(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    video, _ = new.create("retry-safety", source=str(tmp_path))
    assert video == tmp_path / "home" / "retry-safety"
    cfg = json.loads((video / "video.json").read_text())
    assert cfg["title"] == "Retry safety" and cfg["source"]["path"] == str(tmp_path.resolve())
    (video / "SCRIPT.md").write_text((video / "SCRIPT.md").read_text().replace(
        "> {{Narration paragraph", "> Retries can charge twice. {{Narration paragraph"))
    assert script.load(video)[0][0] == "s1"
    narration.narrate(video, estimate=True)
    assert (video / "timeline.json").exists() and (video / "scenes" / "example-chapter.js").exists()
    from studio_kit import keys
    assert not keys.has_scene(video, "s1")          # a new explainer starts on boards


def test_new_refuses_an_existing_video(tmp_path):
    new.create("x", directory=str(tmp_path / "v"))
    try:
        new.create("x", directory=str(tmp_path / "v"))
    except SystemExit as e:
        assert "already holds a video" in str(e)
    else:
        raise AssertionError("expected a refusal")


def test_a_path_as_name_titles_the_video_by_its_folder(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    video, _ = new.create(str(tmp_path / "e2e-comic"))
    assert video == (tmp_path / "e2e-comic").resolve()
    assert json.loads((video / "video.json").read_text())["title"] == "E2e comic"


def test_engine_comes_from_video_json_and_scaffolds_its_own_scenes(tmp_path, monkeypatch):
    from studio_kit.engine import Engine, EngineError
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "h"))
    mc, _ = new.create("mc", directory=str(tmp_path / "mc"), engine="live")
    assert Engine(mc).name == "live"
    assert (mc / "scenes" / "example-code.js").exists()
    with pytest.raises(SystemExit, match="renders live scenes"):
        new.create("old", directory=str(tmp_path / "old"), engine="old-engine")
    assert not (tmp_path / "old").exists()
    with pytest.raises(EngineError, match="no engine named"):
        Engine(mc, "aftereffects")._command("still")


