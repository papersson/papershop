import json

import pytest

from studio_kit import new, narration, script


def test_new_video_is_ready_for_a_script_and_an_estimate(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    video, learner = new.create("retry-safety", source=str(tmp_path))
    assert video == tmp_path / "home" / "retry-safety" and learner.exists()
    cfg = json.loads((video / "video.json").read_text())
    assert cfg["title"] == "Retry safety" and cfg["source"]["path"] == str(tmp_path.resolve())
    assert cfg["level"] == "intro" and cfg["budget"] == {"first_cut": 20, "round": 5}
    assert cfg["checkpoints"] == "few"
    (video / "SCRIPT.md").write_text((video / "SCRIPT.md").read_text().replace(
        "> {{Narration paragraph", "> Retries can charge twice. {{Narration paragraph"))
    assert script.load(video)[0][0] == "s1"
    narration.narrate(video, estimate=True)
    assert (video / "timeline.json").exists() and (video / "scenes" / "index.ts").exists()
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
    rm, _ = new.create("rm", directory=str(tmp_path / "rm"))
    assert Engine(mc).name == "live" and Engine(rm).name == "remotion"
    assert (mc / "scenes" / "example-chapter.js").exists() and not (rm / "scenes" / "project.ts").exists()
    assert Engine(mc, "remotion").name == "remotion"
    with pytest.raises(EngineError, match="no engine named"):
        Engine(mc, "aftereffects")._command("still")




def test_new_video_records_how_often_to_stop_for_the_user(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    video, _ = new.create("busy", checkpoints="many")
    assert json.loads((video / "video.json").read_text())["checkpoints"] == "many"


def test_new_records_the_tone_and_a_series_episode_keeps_it(tmp_path, monkeypatch):
    from studio_kit import cli
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    tone = lambda name: json.loads((tmp_path / "home" / name / "video.json").read_text())["tone"]
    assert cli.main(["new", "dry"]) == 0 and tone("dry") == "plain"
    assert cli.main(["new", "silly", "--tone", "comic"]) == 0 and tone("silly") == "comic"
    assert cli.main(["new", "episode-2", "--from", str(tmp_path / "home" / "silly")]) == 0 and tone("episode-2") == "comic"
    with pytest.raises(SystemExit):
        cli.main(["new", "loud", "--tone", "zany"])










def test_new_records_the_delivery_and_a_series_episode_keeps_it(tmp_path, monkeypatch):
    from studio_kit import cli
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    delivery = lambda name: json.loads((tmp_path / "home" / name / "video.json").read_text())["delivery"]
    assert cli.main(["new", "full"]) == 0 and delivery("full") == "polished"
    assert cli.main(["new", "quick", "--delivery", "session"]) == 0 and delivery("quick") == "session"
    assert cli.main(["new", "quick-2", "--from", str(tmp_path / "home" / "quick")]) == 0 and delivery("quick-2") == "session"
    with pytest.raises(SystemExit):
        cli.main(["new", "slow", "--delivery", "instant"])
