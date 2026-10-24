from studio_kit import stage


def test_stage_timing_keeps_waiting_visible_and_finishes_at_the_last_mark(tmp_path):
    stage.mark(tmp_path, "story", now=0)
    assert stage.mark(tmp_path, "waiting", now=60)[0] == "story: 1m00s"
    stage.mark(tmp_path, "shoot", now=120)
    stage.mark(tmp_path, "finished", now=180)
    assert stage.durations(stage.read(tmp_path), now=9000) == [("story", 60), ("waiting", 60), ("shoot", 60), ("finished", 0)]
    assert "active 2m00s · waiting 1m00s" in stage.report(tmp_path, now=9000)
