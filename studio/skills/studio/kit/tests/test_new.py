import json

from studio_kit import new, narration, script


def test_new_video_is_ready_for_a_script_and_an_estimate(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    video, learner = new.create("retry-safety", source=str(tmp_path))
    assert video == tmp_path / "home" / "retry-safety" and learner.exists()
    cfg = json.loads((video / "video.json").read_text())
    assert cfg["title"] == "Retry safety" and cfg["source"]["path"] == str(tmp_path.resolve())
    (video / "SCRIPT.md").write_text((video / "SCRIPT.md").read_text().replace(
        "> {{Narration paragraph", "> Retries can charge twice. {{Narration paragraph"))
    assert script.load(video)[0][0] == "s1"
    narration.narrate(video, estimate=True)
    assert (video / "timeline.json").exists() and (video / "scenes" / "s1.tsx").exists()


def test_new_refuses_an_existing_video(tmp_path):
    new.create("x", directory=str(tmp_path / "v"))
    try:
        new.create("x", directory=str(tmp_path / "v"))
    except SystemExit as e:
        assert "already holds a video" in str(e)
    else:
        raise AssertionError("expected a refusal")
