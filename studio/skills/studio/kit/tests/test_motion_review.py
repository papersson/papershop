import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from studio_kit import cli, handoff, moments, motion_review, page, review_state, reviews, stage
from studio_kit import timeline as tl
from test_render import make_video


def test_the_motion_kind_reads_a_drifting_verdict_and_stops_at_two_rounds():
    kind = reviews.KINDS["motion"]
    assert kind.verdict("x\n**Motion: pass**\n") == ("passed", "MOTION: PASS")
    assert kind.verdict("## MOTION: FIX\n") == ("findings", "MOTION: FIX")
    assert kind.verdict("no verdict") == ("findings", None)
    assert (kind.rounds.cap({}), kind.rounds.cap({"motion_rounds": 4})) == (2, 4)
    assert kind.rounds.resets_on == ("structural", "fork") and kind.freshness == "record-stale"
    assert "known-issues" in kind.settled and kind.stands == "lineage" and kind.scope == "frames"


def test_review_status_accepts_the_motion_role(tmp_path):
    (tmp_path / "video.json").write_text("{}")
    args = cli.build_parser().parse_args(["review-status", str(tmp_path), "motion", "waived", "--reason", "desk notes n1-n4"])
    review_state.main_status(args)
    assert review_state.read(tmp_path, "motion")["kind"] == "motion"
    review_state.require(tmp_path, "motion")


def test_a_sequence_can_put_its_time_fourth():
    t = {"fps": 30, "tracks": {"scene": [{"id": "s1", "start": 0.0, "end": 4.0}]}}
    m = moments.sequence(t, "s1", 1.0, 12, 15, "motion", before=3)
    assert m["frames"][3] == 1.0 and m["frames"][0] == 0.8 and len(m["frames"]) == 12
    assert m["id"] == "motion_s1_1.0_15fps_3b" and moments.sequence(t, "s1", 1.0)["id"] == "strip_s1_1.0"


def test_findings_are_parsed_through_format_drift():
    text = """Window by window.
1. **MUST FIX** | drop | 1.0 s | frame 30 | the token pops in. Fix: ease it in over 4 frames
- should-fix — move_s2_0.5 — 2.6s — frame 78 — a jerk mid-move. Fix: even the spacing
- Nit: drop, 1.07 s: the shadow lags
**drop_2** — the card swells late. Severity: SHOULD FIX
GAG | drop | 2/5 | the take is too short
MUST FIX 1 · SHOULD FIX 2 · NIT 1
MOTION: FIX"""
    found, gags = motion_review.parse(text, ["drop", "drop_2", "move_s2_0.5"])
    assert [(f["severity"], f["window"], f["t"], f["frame"]) for f in found] == [
        ("must-fix", "drop", 1.0, 30), ("should-fix", "move_s2_0.5", 2.6, 78), ("nit", "drop", 1.07, None),
        ("should-fix", "drop_2", None, None)]
    assert found[0]["text"] == "the token pops in. Fix: ease it in over 4 frames"
    assert gags == [{"window": "drop", "score": 2, "text": "the take is too short"}]


def box(x, at):
    return f"drawbox=x={x}:y=50:w=200:h=150:color=white:t=fill:enable='gte(t,{at})'"


def cut_video(path, landings):
    """A 960×540, 30 fps, 4 s video in which a box lands at each time."""
    graph = "color=c=black:s=960x540:r=30:d=4," + ",".join(box(60 + 220 * i, at) for i, at in enumerate(landings))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", graph, "-pix_fmt", "yuv420p", str(path)], check=True)


def motion_video(v, cfg=None):
    t = make_video(v)
    t["cues"] = {"drop": 1.0}
    (v / "timeline.json").write_text(json.dumps(t))
    (v / "cues.json").write_text(json.dumps({"drop": 1.0}))
    (v / "audio").mkdir()
    (v / "audio" / "sfx.json").write_text(json.dumps([{"t": "drop", "type": "click"}, {"t": 3.9, "type": "pop"}]))
    (v / "video.json").write_text(json.dumps({"teaching_contract": True, **(cfg or {})}))
    (v / "SCRIPT.md").write_text("## Script\n### 1. A\n> One.\n## Evidence\nActual run.\n## Review log\nprivate\n")
    return t


def make_cut(v, n, landings=(1.0, 2.5, 3.2)):
    """Cut N as make_cut records one, for the sources as they are now, with its own video."""
    t = tl.load(v)
    d = v / "cuts" / f"cut{n}"
    d.mkdir(parents=True)
    keys = review_state.review_keys(v, t)
    (d / "timeline.json").write_text(json.dumps(t))
    (d / "SCRIPT.md").write_text((v / "SCRIPT.md").read_text())
    cut_video(d / "video.mp4", landings)
    (d / "cut.json").write_text(json.dumps({
        "cut": n, "kind": "cut", "quality": "draft", "created": f"2026-10-10 10:0{n}:00",
        "source_revision": review_state.fingerprint(v, frames=True, keys=keys), "review_keys": keys,
        "clips": [{"id": c, "key": "k" + c} for c in keys], "stills": [], "changelog": []}))
    return d


def bundle_of(v, n):
    return next((v / "research" / "motion_review").glob(f"cut{n}-*"))


def respond(v, n, body, tmp):
    judged = json.loads((bundle_of(v, n) / "manifest.json").read_text())["revision"]
    f = tmp / f"response{n}.md"
    f.write_text(f"{body}\n**REVISION: {judged}**\n")
    return motion_review.main(SimpleNamespace(video=v, cut=n, result=f))


def edit(v, what):
    (v / "scenes" / "s2.tsx").write_text(f"// s2, {what}\n")


@pytest.fixture
def video(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    v = tmp_path / "v"
    v.mkdir()
    motion_video(v)
    return v


def test_the_bundle_holds_a_window_per_event_and_per_uncovered_move_from_the_cuts_frames(video, capsys):
    make_cut(video, 1)
    edit(video, "edited after the cut")                       # the bundle still shows cut 1's frames
    assert motion_review.main(SimpleNamespace(video=video, cut=None, result=None)) == 0
    out = capsys.readouterr().out
    assert "s2 changed since" in out and "3 motion windows (1 events, 2 moves); round 1 of at most 2" in out
    b = bundle_of(video, 1)
    manifest = json.loads((b / "manifest.json").read_text())
    assert (manifest["cut"], manifest["round"], manifest["cap"], manifest["previous"]) == (1, 1, 2, None)
    found = json.loads((b / "windows.json").read_text())
    drop = found[0]
    assert (drop["name"], drop["kind"], drop["clip"], drop["contact_frame"], drop["fps"]) == ("drop", "event", "s1", 30, 15)
    assert drop["frames"] == list(range(24, 48, 2)) and drop["frames"][3] == 30           # the contact is the fourth
    assert drop["narration"] == {"sentence": "s1_01", "said": "One."}
    assert drop["sfx"] == [{"type": "click", "cue": "drop", "time": 1.0, "frame": 30}]
    moves = [w for w in found if w["kind"] == "move"]
    assert [w["clip"] for w in moves] == ["s2", "s2"]
    assert [w["narration"] for w in moves] == [{"sentence": "s1_01", "said": "One.", "pause": True},     # 2.4 s
                                               {"sentence": "s2_01", "said": "Two."}]
    assert all(0 <= f - w["contact_frame"] <= 3 for w, f in zip(moves, (75, 96)))     # landings at 2.5 and 3.2 s
    assert moves[1]["sfx"] == [] and moves[0]["frames"][3] == moves[0]["contact_frame"]
    for w in found:
        assert (b / w["sheet"]).stat().st_size > 0
    assert (b / "SCRIPT.md").read_text().startswith("## Script") and "Evidence" not in (b / "SCRIPT.md").read_text()
    prompt = (b / "prompt.md").read_text()
    assert "MOTION: PASS" in prompt and f"REVISION: {manifest['revision']}" in prompt and "Is it funny" not in prompt


def test_the_sheet_frames_come_from_the_cut_not_the_sources(video):
    d = make_cut(video, 1, landings=(1.0,))
    rec = json.loads((d / "cut.json").read_text())
    t = tl.load(video)
    assert motion_review.source(video, 1, rec, t, "s2") == (d / "video.mp4", 60)
    clip = video / ".cache" / "clips" / "s2-draft-ks2.mp4"
    clip.parent.mkdir(parents=True)
    clip.write_bytes(b"")
    assert motion_review.source(video, 1, rec, t, "s2") == (clip, 0)          # the clip render the cut recorded


def test_the_stop_rule_ends_at_a_round_without_must_fix_and_leaves_known_issues(video, tmp_path, capsys):
    make_cut(video, 1)
    motion_review.main(SimpleNamespace(video=video, cut=1, result=None))
    f = tmp_path / "bare.md"
    f.write_text("MUST FIX | drop | 1.0 s | frame 30 | pop\n")
    with pytest.raises(SystemExit, match="exact REVISION"):
        motion_review.main(SimpleNamespace(video=video, cut=1, result=f))
    with pytest.raises(SystemExit, match="no verdict line"):
        respond(video, 1, "MUST FIX | drop | 1.0 s | frame 30 | pop", tmp_path)
    assert respond(video, 1, "**Must fix** | drop | 1.0 s | frame 30 | the token pops in. Fix: ease it\n"
                             "- SHOULD FIX — drop — 1.2 s — frame 36 — late settle\n**MOTION: FIX**", tmp_path) == 1
    rec = review_state.read(video, "motion")
    assert (rec["status"], rec["round"], rec["cut"], rec["must_fix"]) == ("findings", 1, 1, 1) and "stopped" not in rec
    findings = json.loads((bundle_of(video, 1) / "findings.json").read_text())
    assert findings["findings"][0] == {"severity": "must-fix", "window": "drop", "t": 1.0, "frame": 30,
                                       "text": "the token pops in. Fix: ease it"}
    assert "known_issues" not in json.loads((video / "cuts" / "cut1" / "cut.json").read_text())
    with pytest.raises(SystemExit, match="missing, stale or unresolved"):
        review_state.require(video, "motion")
    with pytest.raises(SystemExit, match="has had its motion review"):        # its result is kept
        motion_review.main(SimpleNamespace(video=video, cut=1, result=None))

    edit(video, "the pop fixed")
    make_cut(video, 2)
    motion_review.main(SimpleNamespace(video=video, cut=2, result=None))
    b2 = bundle_of(video, 2)
    assert json.loads((b2 / "manifest.json").read_text())["round"] == 2
    assert "Findings from the last round (round 1, cut 1)" in (b2 / "prompt.md").read_text()
    assert json.loads((b2 / "previous.json").read_text())["findings"][0]["text"].startswith("the token pops in")
    assert respond(video, 2, "SHOULD FIX | drop | 1.2 s | frame 36 | late settle. Fix: shorten it\nNIT | drop | 1.0 s | "
                             "frame 30 | shadow\nMOTION: PASS", tmp_path) == 0
    assert "known issue(s) recorded on cut 2" in capsys.readouterr().out
    rec = review_state.read(video, "motion")
    assert (rec["status"], rec["round"], rec["stopped"], rec["left"]) == ("known-issues", 2, "clean", 2)
    issues = json.loads((video / "cuts" / "cut2" / "cut.json").read_text())["known_issues"]
    assert [(i["severity"], i["cut"]) for i in issues] == [("should-fix", 2), ("nit", 2)]
    assert page.state(video, 2)["cut"]["known_issues"] == issues                 # the desk shows them under the cut
    review_state.require(video, "motion")

    edit(video, "a frame-review fix")                       # a later edit doesn't reopen a review that ended
    review_state.require(video, "motion")
    make_cut(video, 3)
    with pytest.raises(SystemExit, match=r"round 3 would pass motion_rounds \(2\).*known issues.*waived.*explicitly asks"):
        motion_review.main(SimpleNamespace(video=video, cut=3, result=None))
    (video / "video.json").write_text(json.dumps({"teaching_contract": True, "motion_rounds": 3}))
    motion_review.main(SimpleNamespace(video=video, cut=3, result=None))

    stage.mark(video, "revision", kind="structural", summary="a new chapter")
    with pytest.raises(SystemExit, match="before a structural revision that started a new count"):
        review_state.require(video, "motion")


def test_must_fix_at_the_cap_is_reported_open_never_passed(video, tmp_path, capsys):
    for n in (1, 2):
        if n == 2:
            edit(video, "round two")
        make_cut(video, n)
        motion_review.main(SimpleNamespace(video=video, cut=n, result=None))
        code = respond(video, n, "MUST FIX | drop | 1.0 s | frame 30 | pop\nSHOULD FIX | drop | 1.1 s | frame 33 | lag\n"
                                 "MOTION: PASS", tmp_path)          # a PASS with a must-fix is findings
    assert code == 1
    out = capsys.readouterr().out
    assert "verdict says PASS but 1 finding(s) are MUST FIX" in out and "motion: OPEN at the cap (round 2 of 2)" in out
    rec = review_state.read(video, "motion")
    assert (rec["status"], rec["stopped"]) == ("findings", "cap")
    assert [i["text"] for i in json.loads((video / "cuts" / "cut2" / "cut.json").read_text())["known_issues"]] == ["lag"]
    with pytest.raises(SystemExit, match="stopped at its cap with must-fix findings open"):
        review_state.require(video, "motion")
    text = handoff.assemble(video)
    assert "motion: findings, OPEN at the round cap" in text and "motion review stopped at its cap" in text


def test_a_comic_bundle_reads_the_comic_questions_from_the_style_file(video, tmp_path):
    (video / "video.json").write_text(json.dumps({"teaching_contract": True, "tone": "comic"}))
    make_cut(video, 1)
    motion_review.main(SimpleNamespace(video=video, cut=1, result=None))
    prompt = (bundle_of(video, 1) / "prompt.md").read_text()
    assert "This video's tone is comic." in prompt and "**Is it funny?**" in prompt and "GAG | window name | n/5" in prompt
    assert "## Motion review" not in prompt
    respond(video, 1, "GAG | drop | 4/5 | the pause sells it\nMOTION: PASS", tmp_path)
    assert json.loads((bundle_of(video, 1) / "findings.json").read_text())["gags"] == [
        {"window": "drop", "score": 4, "text": "the pause sells it"}]
    assert review_state.read(video, "motion")["status"] == "passed"


def test_handoff_picks_up_a_motion_bundle_waiting_for_its_result(video):
    make_cut(video, 1)
    motion_review.main(SimpleNamespace(video=video, cut=1, result=None))
    text = handoff.assemble(video)
    assert "motion review of cut 1 prepared, not imported: research/motion_review/cut1-" in text
    assert 'studio review-motion "$VIDEO" --cut 1 --result FILE' in text


def test_publish_asks_an_explainer_for_its_motion_review(video, monkeypatch):
    from studio_kit import check, publish
    monkeypatch.setattr(check, "run", lambda video, everything: [])
    review_state.record(video, "student", review_state.revision(video, reviews.KINDS["script"]), "waived", "user said so")
    with pytest.raises(SystemExit, match="current motion review missing"):
        publish.gate(video)
    review_state.record(video, "motion", review_state.revision(video, reviews.KINDS["motion"]), "waived",
                        "interactive: the user's desk notes on cut 4 stand in for the motion review")
    publish.gate(video)
    (video / "video.json").write_text(json.dumps({"teaching_contract": True, "genre": "motion"}))
    (video / "research" / "reviews" / "motion.json").unlink()
    publish.gate(video)


def test_a_new_cut_carries_the_known_issues_forward(tmp_path):
    from studio_kit import render
    from test_build import StillEngine
    (tmp_path / "video.json").write_text(json.dumps({"title": "Reel", "duration": 3}))
    tl.build(tmp_path)
    rec = render.make_cut(tmp_path, stills_only=True, engine=StillEngine())
    issues = [{"severity": "should-fix", "window": "logo", "t": 2.0, "frame": 60, "text": "late settle", "cut": 1}]
    motion_review.write_known_issues(tmp_path, rec["cut"], issues)
    assert render.make_cut(tmp_path, stills_only=True, engine=StillEngine())["known_issues"] == issues
    assert json.loads((Path(tmp_path) / "cuts" / "cut2" / "cut.json").read_text())["known_issues"] == issues
