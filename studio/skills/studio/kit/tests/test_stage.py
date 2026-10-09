import json
import time

from studio_kit import stage


def video(tmp_path, budget=None):
    cfg = {"title": "t"}
    if budget:
        cfg["budget"] = budget
    (tmp_path / "video.json").write_text(json.dumps(cfg))
    return tmp_path


def test_marks_report_the_previous_stage_and_the_budget(tmp_path):
    v = video(tmp_path)
    stage.mark(v, "research", now=0)
    lines = stage.mark(v, "script", now=600)
    assert lines[0] == "research: 10m00s"
    assert "10m00s into the first cut (budget 20m00s)" in lines[1]
    assert not any("OVER BUDGET" in ln for ln in lines)


def test_over_budget_says_so(tmp_path):
    v = video(tmp_path, {"first_cut": 30})
    stage.mark(v, "research", now=0)
    lines = stage.mark(v, "scenes", now=31 * 60)
    assert any(ln.startswith("OVER BUDGET by 1m00s") for ln in lines)


def test_a_revision_round_has_its_own_budget(tmp_path):
    v = video(tmp_path)
    stage.mark(v, "research", now=0)
    stage.mark(v, "round", now=3 * 3600)
    lines = stage.mark(v, "cut", now=3 * 3600 + 6 * 60)
    assert "into this revision round (budget 5m00s)" in lines[1]
    assert any("OVER BUDGET by 1m00s" in ln for ln in lines)


def test_a_deep_dive_has_the_longer_budget(tmp_path):
    (tmp_path / "video.json").write_text(json.dumps({"level": "deep-dive"}))
    stage.mark(tmp_path, "research", now=0)
    assert "(budget 1h00m)" in stage.mark(tmp_path, "script", now=60)[1]


def test_report_shares_add_up(tmp_path):
    v = video(tmp_path)
    for name, t in [("research", 0), ("script", 300), ("scenes", 900)]:
        stage.mark(v, name, now=t)
    rows = stage.report(v, now=1200)
    assert rows[0].startswith("research") and "5m00s" in rows[0]
    assert rows[-2].startswith("total") and "20m00s" in rows[-2]
    assert "active 20m00s" in rows[-1]


def test_status_reads_the_current_stage_and_its_scope_as_data(tmp_path):
    v = video(tmp_path, {"first_cut": 30, "scenes": 10})
    stage.mark(v, "research", now=0)
    stage.mark(v, "scenes", now=15 * 60)
    s = stage.status(v, now=27 * 60)
    assert (s["stage"], s["kind"], s["spent"], s["total"], s["budget"], s["over"]) == ("scenes", "local", 12 * 60, 12 * 60, 600, True)
    assert s["scope"] == {"name": "first_cut", "spent": 27 * 60, "limit": 30 * 60, "ratio": 0.9, "over": False}
    stage.mark(v, "round", now=40 * 60, kind="structural")
    s = stage.status(v, now=50 * 60)
    assert s["budget"] is None and s["scope"]["name"] == "structural_round" and s["scope"]["limit"] == 20 * 60


def test_a_stage_budget_from_video_json_is_reported_when_the_stage_ends(tmp_path):
    v = video(tmp_path, {"script": 10})
    stage.mark(v, "research", now=0)
    assert "now: script (stage: 0m00s of 10m00s)" in stage.mark(v, "script", now=60)[1]
    lines = stage.mark(v, "scenes", now=60 + 12 * 60)
    assert lines[0] == "script: 12m00s (stage: 12m00s of 10m00s, over by 2m00s)"
    assert lines[1].startswith("now: scenes · ")


def test_a_stage_budget_counts_every_run_of_the_stage_since_the_latest_round(tmp_path):
    v = video(tmp_path, {"scenes": 30})
    stage.mark(v, "scenes", now=0)
    stage.mark(v, "waiting", now=25 * 60)
    stage.mark(v, "scenes", now=90 * 60)
    lines = stage.mark(v, "cut", now=115 * 60)
    assert lines[0] == "scenes: 25m00s (stage: 50m00s of 30m00s, over by 20m00s)"
    stage.mark(v, "round", now=120 * 60)
    stage.mark(v, "scenes", now=121 * 60)
    s = stage.status(v, now=131 * 60)
    assert (s["total"], s["over"]) == (10 * 60, False)


def background(tmp_path, budget, mode="background"):
    (tmp_path / "video.json").write_text(json.dumps({"title": "t", "mode": mode, "budget": budget}))
    return tmp_path


def test_a_background_stage_stops_at_twice_its_own_budget(tmp_path):
    v = background(tmp_path, {"polish": 60})
    stage.mark(v, "polish", now=0)
    assert not stage.status(v, now=119 * 60)["stop"] and stage.status(v, now=119 * 60)["over"]
    assert stage.status(v, now=120 * 60)["stop"]
    lines, stopped = stage.check(v, now=125 * 60)
    assert stopped and lines[1].startswith("STOP: polish has run 2h05m against its 1h00m budget")
    assert f"studio handoff {v.resolve()} --notes" in lines[1] and "budget.polish" in lines[1]
    stage.mark(v, "waiting", now=130 * 60)
    lines = stage.mark(v, "polish", now=200 * 60)     # a resumed run counts with the earlier ones
    assert any(ln.startswith("STOP: polish") for ln in lines) and not any("OVER BUDGET" in ln for ln in lines)


def test_aggregates_and_interactive_mode_never_stop(tmp_path):
    v = background(tmp_path, {"first_cut": 10, "round": 1})
    stage.mark(v, "scenes", now=0)
    s = stage.status(v, now=10 * 3600)
    assert s["scope"]["over"] and not s["stop"]
    assert stage.check(v, now=10 * 3600) == ([stage.check(v, now=10 * 3600)[0][0]], False)
    v = background(tmp_path, {"scenes": 10}, mode="interactive")
    assert stage.status(v, now=10 * 3600)["over"] and not stage.status(v, now=10 * 3600)["stop"]
    v = background(tmp_path, {"waiting": 10})
    stage.mark(v, "waiting", now=0)
    assert not stage.status(v, now=10 * 3600)["stop"]


def test_check_exits_3_when_stopped_and_takes_no_lock(tmp_path, monkeypatch, capsys):
    from studio_kit import cli, workspace
    v = background(tmp_path, {"polish": 1})
    assert stage.check(v) == (["no stages marked yet (studio stage VIDEO NAME)"], False)
    stage.mark(v, "polish", now=time.time() - 150)
    assert cli.main(["stage", str(v), "--check"]) == stage.STOPPED
    assert "STOP: polish" in capsys.readouterr().out
    def locked(video):
        raise AssertionError("a check took the operation lock")
    monkeypatch.setattr(workspace, "operation", locked)
    assert cli.main(["stage", str(v), "--check"]) == stage.STOPPED      # while a cut holds the lock
    background(tmp_path, {"polish": 10 ** 6})
    assert cli.main(["stage", str(v), "--check"]) == 0
