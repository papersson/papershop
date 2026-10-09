from types import SimpleNamespace

import pytest

from studio_kit import cli, doctor, preferences, workspace


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    for name in ("myvideo", "my-video-2", "unrelated"):
        (home / name).mkdir(parents=True)
        (home / name / "video.json").write_text("{}\n")
    monkeypatch.setenv("STUDIO_HOME", str(home))
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    return home


@pytest.mark.parametrize("argv", [["stage", "myvideo", "draft"], ["notes", "myvideo"], ["variant", "myvideo", "copy"]])
def test_a_name_from_the_wrong_folder_stops_and_suggests_the_home_video(home, argv):
    with pytest.raises(SystemExit) as e:
        cli.main(argv)
    assert "myvideo is not a video: no folder at" in str(e.value)
    assert f"  {home / 'myvideo'}\n" in str(e.value)
    assert not any((home.parent / "elsewhere").iterdir()), "nothing is created in the wrong folder"
    assert not (home / "copy").exists() and not (home / "myvideo" / ".cache").exists()


def test_suggestions_are_ranked_by_name(home):
    with pytest.raises(SystemExit) as e:
        cli.main(["notes", "myvidoe"])
    listed = [line.strip() for line in str(e.value).splitlines() if line.startswith("  ")]
    assert listed[0] == str(home / "myvideo") and str(home / "unrelated") not in listed


def test_a_folder_without_video_json_is_refused(home):
    (home.parent / "elsewhere" / "repo").mkdir()
    with pytest.raises(SystemExit, match="has no video.json") as e:
        cli.main(["stage", "repo", "draft"])
    assert "no video in" in str(e.value)
    assert not (home.parent / "elsewhere" / "repo" / ".cache").exists()


def test_a_real_video_runs_under_its_lock(home):
    cli.main(["stage", str(home / "myvideo"), "draft"])
    assert (home / "myvideo" / ".cache" / "studio" / "operation.lock").exists()
    cli.main(["request", str(home / "myvideo"), "a sidebar"])
    assert "a sidebar" in (home / "myvideo" / "research" / "requests.md").read_text()


def test_new_still_creates_its_folder(home):
    assert cli.main(["new", "fresh", "--genre", "motion", "--duration", "4"]) == 0
    assert (home / "fresh" / "video.json").exists()
    with pytest.raises(SystemExit, match="nowhere is not a video"):
        cli.main(["new", "other", "--from", "nowhere"])
    assert not (home / "other").exists()


def test_import_tutor_may_name_a_new_folder():
    assert cli.build_parser().parse_args(["import-tutor", "lesson", "not-yet"]).video == "not-yet"


def test_import_tutor_makes_a_video_the_other_commands_accept(tmp_path):
    import json
    lesson = tmp_path / "lesson"
    (lesson / "audio").mkdir(parents=True)
    (lesson / "audio" / "narration.mp3").write_bytes(b"mp3")
    line = {"id": "s1_01", "text": "Hello.", "caption": "Hello.", "paragraph": 0, "start": 0.8, "end": 1.6}
    (lesson / "audio" / "timings.json").write_text(json.dumps(
        {"total": 3.0, "segments": [{"id": "s1", "title": "Hi", "start": 0.0, "end": 3.0, "lines": [line]}]}))
    video = tmp_path / "hello-world"
    assert cli.main(["import-tutor", str(lesson), str(video)]) == 0
    cfg = json.loads((video / "video.json").read_text())
    assert cfg["genre"] == "explainer" and cfg["engine"] == "remotion" and cfg["title"] == "Hello world"
    timings = json.loads((video / "audio" / "timings.json").read_text())
    assert timings["timing"] == "narrated" and timings["segments"][0]["lines"] == [line]
    assert cli.main(["timeline", str(video)]) == 0
    t = json.loads((video / "timeline.json").read_text())
    assert t["timing"] == "narrated" and t["tracks"]["narration"][0]["caption"] == "Hello."


def test_doctor_runs_without_a_video(home, monkeypatch):
    seen = []
    monkeypatch.setattr(doctor, "main", lambda args: seen.append(args.video) or 0)
    assert cli.main(["doctor"]) == 0 and seen == [None]
    with pytest.raises(SystemExit, match="is not a video"):
        cli.main(["doctor", "nowhere"])


def test_a_lock_never_creates_the_folder_it_names(tmp_path):
    with pytest.raises(SystemExit, match="no folder at"):
        with workspace.locked(tmp_path / "missing"):
            pass
    assert not (tmp_path / "missing").exists()


def test_lexicon_makes_studio_home_on_a_fresh_machine(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "fresh-home"))
    preferences.main_lexicon(SimpleNamespace(word="JSON", spoken="J S O N", phonemes=None))
    assert (tmp_path / "fresh-home" / "lexicon.json").exists()


def test_engine_reads_wait_their_turn_for_the_operation_lock(home, monkeypatch):
    import threading
    import time
    v = home / "myvideo"
    calls = []
    monkeypatch.setattr(cli, "_engine_call", lambda args: calls.append((args.cmd, time.monotonic())) or 0)
    monkeypatch.setitem(cli.COMMANDS, "still", (*cli.COMMANDS["still"][:2], cli._engine_call))
    monkeypatch.setitem(cli.COMMANDS, "boxes", (*cli.COMMANDS["boxes"][:2], cli._engine_call))
    held = threading.Event()
    def hold():
        with workspace.locked(v, "operation", blocking=False):
            held.set()
            time.sleep(0.6)
    t = threading.Thread(target=hold)
    t.start()
    held.wait()
    start = time.monotonic()
    assert cli.main(["still", str(v), "s1", "1", "--out", "x.png"]) == 0      # queued, not refused
    assert cli.main(["boxes", str(v), "s1", "1"]) == 0
    t.join()
    assert calls[0][1] - start > 0.4
    with workspace.locked(v, "operation", blocking=False):
        with pytest.raises(SystemExit, match="held it for 0.3 s"):
            with workspace.operation(v, wait=0.3):
                pass
        with pytest.raises(SystemExit, match="operation is running for"):
            cli.main(["stage", str(v), "draft"])                              # a change still refuses at once


def test_boxes_waits_but_needs_no_owner(home, monkeypatch):
    v = home / "myvideo"
    workspace.main_lock(SimpleNamespace(video=v, action="acquire", owner="b", recover=False))
    monkeypatch.delenv("STUDIO_OWNER", raising=False)
    seen = []
    monkeypatch.setitem(cli.COMMANDS, "boxes", (*cli.COMMANDS["boxes"][:2], lambda args: seen.append(args.cmd) or 0))
    monkeypatch.setitem(cli.COMMANDS, "still", (*cli.COMMANDS["still"][:2], lambda args: seen.append(args.cmd) or 0))
    assert cli.main(["boxes", str(v), "s1", "1"]) == 0 and seen == ["boxes"]
    with pytest.raises(SystemExit, match="video owned by b"):
        cli.main(["still", str(v), "s1", "1", "--out", "x.png"])
