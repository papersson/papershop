import json

import pytest

from studio_kit import new, narration, script


def test_new_video_is_ready_for_a_script_and_an_estimate(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    video, _ = new.create("retry-safety", source=str(tmp_path))
    assert video == tmp_path / "home" / "retry-safety"
    assert json.loads((video / "audio/sfx.json").read_text()) == []
    assert json.loads((video / "narration.json").read_text())["tail"] < 3
    cfg = json.loads((video / "video.json").read_text())
    assert cfg["title"] == "Retry safety" and cfg["source"]["path"] == str(tmp_path.resolve())
    (video / "SCRIPT.md").write_text((video / "SCRIPT.md").read_text().replace(
        "> {{Narration paragraph", "> Retries can charge twice. {{Narration paragraph"))
    assert script.load(video)[0][0] == "s1"
    narration.narrate(video, estimate=True)
    assert (video / "timeline.json").exists() and (video / "scenes" / "example-chapter.js").exists()
    from studio_kit import keys
    assert not keys.has_scene(video, "s1")          # a new explainer starts on boards


def test_a_home_with_a_films_folder_gets_new_videos_there(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    (tmp_path / "home" / "films").mkdir(parents=True)
    video, _ = new.create("retry-safety")
    assert video == tmp_path / "home" / "films" / "retry-safety"
    with pytest.raises(SystemExit, match="holds the videos"):
        new.create("films", directory=str(tmp_path / "home" / "films"))


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




def test_a_series_episode_records_its_paths_relative_to_the_repo(tmp_path, monkeypatch):
    import subprocess
    from types import SimpleNamespace
    repo = tmp_path / "journey"
    monkeypatch.setenv("STUDIO_HOME", str(repo))
    (repo / "films").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    ep1, _ = new.create("ep-1")
    (tmp_path / "ep-2-brief.md").write_text("# Episode 2\n\nThe story.\n")
    args = SimpleNamespace(name="ep-2", dir=None, title=None, source=None, duration=None, engine=None,
                           from_video=str(ep1), include=[], brief=str(tmp_path / "ep-2-brief.md"))
    assert new.main(args) == 0
    ep2 = repo / "films" / "ep-2"
    assert json.loads((ep2 / "video.json").read_text())["series_of"] == "films/ep-1"
    assert json.loads((ep2 / "research/series.json").read_text())["source"] == "films/ep-1"
    assert "The story." in (ep2 / "research/brief.md").read_text()
    with pytest.raises(SystemExit, match="no such file"):
        new.main(SimpleNamespace(**{**vars(args), "name": "ep-3", "brief": str(tmp_path / "nope.md")}))
    assert not (repo / "films" / "ep-3").exists()


def test_kodawari_is_opt_in_and_a_series_carries_its_bible_and_ledger(tmp_path, monkeypatch):
    """A film opts in with --kodawari; an episode made --from it inherits the flag, bible and ledger,
    and a film that never opted in gets none of it."""
    from types import SimpleNamespace
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    base = dict(dir=None, title=None, source=None, duration=None, engine=None, include=[], brief=None)
    assert new.main(SimpleNamespace(name="plain", from_video=None, kodawari=False, **base)) == 0
    plain = tmp_path / "home" / "plain"
    assert "kodawari" not in json.loads((plain / "video.json").read_text())
    assert new.main(SimpleNamespace(name="ep-1", from_video=None, kodawari=True, **base)) == 0
    ep1 = tmp_path / "home" / "ep-1"
    assert json.loads((ep1 / "video.json").read_text())["kodawari"] is True
    (ep1 / "research/kodawari").mkdir()
    (ep1 / "research/kodawari/bible.md").write_text("Spine: a small, kind city of workers.\n")
    (ep1 / "research/kodawari/ledger.md").write_text("2026-11-05: loved the workers, because they are the processes.\n")
    (ep1 / "research/kodawari/routes.png").write_bytes(b"not carried")
    assert new.main(SimpleNamespace(name="ep-2", from_video=str(ep1), kodawari=False, **base)) == 0
    ep2 = tmp_path / "home" / "ep-2"
    assert json.loads((ep2 / "video.json").read_text())["kodawari"] is True
    assert "city of workers" in (ep2 / "research/kodawari/bible.md").read_text()
    assert "they are the processes" in (ep2 / "research/kodawari/ledger.md").read_text()
    assert not (ep2 / "research/kodawari/routes.png").exists()
    files = json.loads((ep2 / "research/series.json").read_text())["files"]
    assert set(files) == {"research/kodawari/bible.md", "research/kodawari/ledger.md"}
    assert new.main(SimpleNamespace(name="ep-plain", from_video=str(plain), kodawari=False, **base)) == 0
    assert "kodawari" not in json.loads((tmp_path / "home/ep-plain/video.json").read_text())
