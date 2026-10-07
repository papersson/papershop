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
    from studio_kit import render
    assert not render.has_scene(video, "s1")          # a new explainer starts on boards


def test_new_refuses_an_existing_video(tmp_path):
    new.create("x", directory=str(tmp_path / "v"))
    try:
        new.create("x", directory=str(tmp_path / "v"))
    except SystemExit as e:
        assert "already holds a video" in str(e)
    else:
        raise AssertionError("expected a refusal")


def test_a_variant_keeps_evidence_and_look_and_drops_the_words(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    src, _ = new.create("engineer", directory=str(tmp_path / "engineer"))
    (src / "data").mkdir()
    (src / "data" / "runs.json").write_text('{"n": 3}')
    (src / "scenes" / "s1.tsx").write_text("export const S1 = () => null;\n")
    (src / "SCRIPT.md").write_text("# T\n\nStatus: locked\n\n## Script\n\n### 1. A\n\n> Words for engineers.\n\n## Review log\n\n- round 1: PASS\n")
    (src / "cuts" / "cut1").mkdir(parents=True)
    (src / "audio").mkdir()
    (src / "audio" / "narration.mp3").write_bytes(b"x")
    glossary = tmp_path / "plain.md"
    glossary.write_text("held: quarantined\n")
    v = new.variant(src, "stakeholder", learner=tmp_path / "exec.md", vocabulary=glossary)
    assert (v / "data" / "runs.json").read_text() == '{"n": 3}' and (v / "scenes" / "s1.tsx").exists()
    assert not (v / "cuts").exists() and not (v / "audio").exists() and not (v / "timeline.json").exists()
    text = (v / "SCRIPT.md").read_text()
    assert "Status: draft variant" in text and "round 1: PASS" not in text and "Variant of engineer" in text
    cfg = json.loads((v / "video.json").read_text())
    assert cfg["variant_of"] == str(src) and cfg["vocabulary"] == str(glossary) and cfg["version"] == "v1"


def test_engine_comes_from_video_json_and_scaffolds_its_own_scenes(tmp_path, monkeypatch):
    from studio_kit.engine import Engine, EngineError
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "h"))
    mc, _ = new.create("mc", directory=str(tmp_path / "mc"), engine="motion-canvas")
    rm, _ = new.create("rm", directory=str(tmp_path / "rm"))
    assert Engine(mc).name == "motion-canvas" and Engine(rm).name == "remotion"
    assert (mc / "scenes" / "project.ts").exists() and not (rm / "scenes" / "project.ts").exists()
    assert Engine(mc, "remotion").name == "remotion"
    with pytest.raises(EngineError, match="no engine named"):
        Engine(mc, "aftereffects")._command("still")


def test_motion_canvas_genres_get_their_own_starters(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "h"))
    for genre, needle in (("motion", "loopT"), ("pixel", "pixelCanvas"), ("launch", "shot("), ("footage", "footage(")):
        v, _ = new.create(genre, directory=str(tmp_path / genre), genre=genre, engine="motion-canvas", duration=6 if genre != "footage" else None)
        assert needle in (v / "scenes" / "s1.ts").read_text() and (v / "scenes" / "project.ts").exists()
    plain, _ = new.create("plain", directory=str(tmp_path / "plain"), engine="motion-canvas")
    assert "studioScene" in (plain / "scenes" / "s1.ts").read_text()


def test_new_video_records_how_often_to_stop_for_the_user(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    video, _ = new.create("busy", checkpoints="many")
    assert json.loads((video / "video.json").read_text())["checkpoints"] == "many"
