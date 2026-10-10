import json
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from studio_kit import cli, handoff, moments, motion_review, page, review_state, reviews, stage
from studio_kit import timeline as tl
from test_render import make_video


def test_the_motion_kind_reads_a_verdict_line_through_drift_but_not_a_sentence():
    v = reviews.KINDS["motion"].verdict
    assert v("x\n**Motion: pass**\n") == ("passed", "MOTION: PASS")
    assert v("## MOTION: FIX\n") == ("findings", "MOTION: FIX")
    assert v("MOTION — PASS") == v("MOTION:PASS.") == v("Verdict: MOTION: PASS") == ("passed", "MOTION: PASS")
    assert v("MOTION: PASS would be my call if not for drop.\nMOTION: FIX") == ("findings", "MOTION: FIX")
    assert v("Motion: fix the ease first, then it reads.") == ("findings", None)
    assert v("no verdict") == ("findings", None)
    kind = reviews.KINDS["motion"]
    assert (kind.rounds.cap({}), kind.rounds.cap({"motion_rounds": 4})) == (2, 4)
    assert kind.rounds.resets_on == ("structural", "fork") and kind.freshness == "record-stale"
    assert "known-issues" in kind.settled and kind.stands == "lineage" and kind.scope == "frames"


def test_a_sequence_can_put_its_time_fourth():
    t = {"fps": 30, "tracks": {"scene": [{"id": "s1", "start": 0.0, "end": 4.0}]}}
    m = moments.sequence(t, "s1", 1.0, 12, 15, "motion", before=3)
    assert m["frames"][3] == 1.0 and m["frames"][0] == 0.8 and len(m["frames"]) == 12
    assert m["id"] == "motion_s1_1.0_15fps_3b" and moments.sequence(t, "s1", 1.0)["id"] == "strip_s1_1.0"


NAMES = ["drop", "drop_2", "flip_2", "move_s2_0.5"]


def rows(text):
    found, _, _ = motion_review.parse(text, NAMES)
    return [(f["severity"], f["window"], f["t"], f["frame"], f["text"]) for f in found]


def test_findings_are_parsed_through_format_drift():
    text = """Window by window.
1. **MUST FIX** | drop | 1.0 s | frame 30 | the token pops in. Fix: ease it in over 4 frames
- should-fix — move_s2_0.5 — 2.6s — frame 78 — a jerk mid-move. Fix: even the spacing
- Nit: drop, 1.07 s: the shadow lags
**drop_2** — the card swells late. Severity: SHOULD FIX
GAG | drop | 2/5 | the take is too short
MUST FIX 1 · SHOULD FIX 2 · NIT 1
MOTION: FIX"""
    found, _, gags = motion_review.parse(text, NAMES)
    assert [(f["severity"], f["window"], f["t"], f["frame"]) for f in found] == [
        ("must-fix", "drop", 1.0, 30), ("should-fix", "move_s2_0.5", 2.6, 78), ("nit", "drop", 1.07, None),
        ("should-fix", "drop_2", None, None)]
    assert found[0]["text"] == "the token pops in. Fix: ease it in over 4 frames"
    assert gags == [{"window": "drop", "score": 2, "text": "the take is too short"}]


def test_counts_lines_and_the_regression_check_are_never_findings():
    """The reviewer's probes: each of these made a false must-fix that blocked publish."""
    assert rows("SHOULD FIX | drop | 1.0 s | frame 30 | lag\nMUST FIX: 0 · SHOULD FIX: 1 · NIT: 0") == \
        rows("SHOULD FIX | drop | 1.0 s | frame 30 | lag\nMUST FIX 0 | SHOULD FIX 1 | NIT 0") == \
        [("should-fix", "drop", 1.0, 30, "lag")]
    assert rows("MUST FIX 0 • SHOULD FIX 1 • NIT 0") == rows("Must fix: 0") == []
    assert rows("Regressions:\n- MUST FIX | drop | 1.0 s | frame 30 | pop — fixed.\n\nSHOULD FIX | flip_2 | 2 s | frame 60 | lag") \
        == [("should-fix", "flip_2", 2.0, 60, "lag")]
    assert rows("## Previous round\n- MUST FIX | drop | 1.0 s | frame 30 | pop\n## This round\nNIT | drop | 1 s | f30 | x") == \
        [("nit", "drop", 1.0, 30, "x")]
    assert rows("Should fix rounds be needed, ping me.\nMust fix nothing else.") == []


def test_tables_headings_checkboxes_and_unicode_hyphens_are_findings():
    table = "| Severity | Window | t | Frame | Issue |\n|---|---|---|---|---|\n| MUST FIX | drop | 1.0 s | 30 | pop |\n" \
            "| SHOULD FIX | flip_2 | 2.0 s | 60 | lag |"
    assert rows(table) == [("must-fix", "drop", 1.0, 30, "pop"), ("should-fix", "flip_2", 2.0, 60, "lag")]
    assert rows("## Must fix\n- drop, 1.0 s, frame 30: pop\n## Should fix\n- flip_2 2.0 s: lag") == \
        [("must-fix", "drop", 1.0, 30, "pop"), ("should-fix", "flip_2", 2.0, None, "lag")]
    assert rows("- [ ] MUST FIX | drop | 1.0 s | frame 30 | pop") == [("must-fix", "drop", 1.0, 30, "pop")]
    assert [r[0] for r in rows("Must‑fix | drop | 1.0 s | frame 30 | pop\nShould–fix | flip_2 | 2 s | lag")] == \
        ["must-fix", "should-fix"]
    assert rows("MUST FIX | drop | 1.0 s | frame 30 |\n  the token pops in. Fix: ease") == \
        [("must-fix", "drop", 1.0, 30, "the token pops in. Fix: ease")]
    assert rows("MUST FIX | drop | frame 30 | moves 0.5 s too late") == [("must-fix", "drop", None, 30, "moves 0.5 s too late")]


def test_a_findings_block_is_all_that_is_read_and_regressions_have_their_own():
    text = ("Notes: MUST FIX | drop | 1 s | frame 30 | discussed, not a finding\n```findings\n"
            "SHOULD FIX | drop | 1.2 s | frame 36 | late settle. Fix: shorten it\n```\n"
            "```regressions\nFIXED | drop | the pop is gone\nSTILL | flip_2 | lag\n```\nMOTION: PASS")
    found, regressions, _ = motion_review.parse(text, NAMES)
    assert [(f["severity"], f["text"]) for f in found] == [("should-fix", "late settle. Fix: shorten it")]
    assert regressions == [{"status": "fixed", "window": "drop", "text": "the pop is gone"},
                           {"status": "still", "window": "flip_2", "text": "lag"}]


# --- a video with four chapters and a cut of its own ---------------------------------------------------

def box(x, at):
    return f"drawbox=x={x}:y=50:w=180:h=150:color=white:t=fill:enable='gte(t,{at})'"


def cut_video(path, landings):
    """A 960×540, 30 fps, 6 s video in which a box lands at each time."""
    graph = "color=c=black:s=960x540:r=30:d=6," + ",".join(box(40 + 220 * i, at) for i, at in enumerate(landings))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", graph, "-pix_fmt", "yuv420p", str(path)], check=True)


def motion_video(v, cfg=None, cues=None):
    t = make_video(v)
    t["tracks"]["scene"] += [{"id": "s3", "engine": "remotion", "title": "C", "start": 4.0, "end": 5.0},
                             {"id": "s4", "engine": "remotion", "title": "D", "start": 5.0, "end": 6.0}]
    t["duration"] = 6.0
    for c in ("s3", "s4"):
        (v / "scenes" / f"{c}.tsx").write_text(f"// {c}\n")
    t["cues"] = cues or {"drop": 1.0, "enter": 2.0}
    (v / "timeline.json").write_text(json.dumps(t))
    (v / "cues.json").write_text(json.dumps(t["cues"]))
    (v / "audio").mkdir()
    (v / "audio" / "sfx.json").write_text(json.dumps([{"t": "drop", "type": "click"}, {"t": 5.9, "type": "pop"}]))
    (v / "video.json").write_text(json.dumps({"teaching_contract": True, **(cfg or {})}))
    (v / "SCRIPT.md").write_text("## Script\n### 1. A\n> One.\n## Evidence\nActual run.\n## Review log\nprivate\n")
    return t


def make_cut(v, n, landings=(1.0, 2.0, 3.2, 4.6), video=True):
    """Cut N as make_cut records one, for the sources as they are now, with its own video and snapshots."""
    t = tl.load(v)
    d = v / "cuts" / f"cut{n}"
    d.mkdir(parents=True)
    keys = review_state.review_keys(v, t)
    (d / "timeline.json").write_text(json.dumps(t))
    (d / "SCRIPT.md").write_text((v / "SCRIPT.md").read_text())
    (d / "sfx.json").write_text(json.dumps([{**c, "time": t["cues"].get(c["t"]) if isinstance(c["t"], str) else c["t"]}
                                            for c in json.loads((v / "audio" / "sfx.json").read_text())]))
    if video:
        cut_video(d / "video.mp4", landings)
    (d / "cut.json").write_text(json.dumps({
        "cut": n, "kind": "cut", "quality": "draft", "created": time.strftime("%Y-%m-%d %H:%M:%S"), "t": time.time(),
        "source_revision": review_state.fingerprint(v, frames=True, keys=keys), "review_keys": keys,
        "clips": [{"id": c, "key": "k" + c} for c in keys], "stills": [], "changelog": []}))
    return d


def bundle_of(v, n):
    return next((v / "research" / "motion_review").glob(f"cut{n}-*"))


def prepare(v, n):
    return motion_review.main(SimpleNamespace(video=v, cut=n, result=None))


def respond(v, n, body, tmp):
    judged = json.loads((bundle_of(v, n) / "manifest.json").read_text())["revision"]
    f = tmp / f"response{n}.md"
    f.write_text(f"{body}\n**REVISION: {judged}**\n")
    return motion_review.main(SimpleNamespace(video=v, cut=n, result=f))


def edit(v, *clips, what="edited"):
    for c in clips or ("s2",):
        (v / "scenes" / f"{c}.tsx").write_text(f"// {c}, {what}\n")


@pytest.fixture
def video(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    v = tmp_path / "v"
    v.mkdir()
    motion_video(v)
    return v


def test_the_bundle_holds_a_window_per_event_and_per_uncovered_move_from_the_cuts_frames(video, capsys):
    make_cut(video, 1)
    edit(video, what="edited after the cut")                    # the bundle still shows cut 1's frames
    (video / "audio" / "sfx.json").write_text(json.dumps([{"t": 1.5, "type": "click"}]))   # and its effects
    assert prepare(video, None) == 0
    out = capsys.readouterr().out
    assert "s2 changed since" in out and "4 motion windows (2 events, 2 moves); round 1 of at most 2" in out
    b = bundle_of(video, 1)
    manifest = json.loads((b / "manifest.json").read_text())
    assert (manifest["cut"], manifest["round"], manifest["cap"], manifest["previous"]) == (1, 1, 2, None)
    assert (manifest["labelled"], manifest["sfx_from"], manifest["dropped"]) == (True, "the cut", [])
    found = {w["name"]: w for w in json.loads((b / "windows.json").read_text())}
    drop = found["drop"]
    assert (drop["kind"], drop["clip"], drop["contact_frame"], drop["contact_index"], drop["fps"]) == ("event", "s1", 30, 3, 15)
    assert drop["frames"] == list(range(24, 48, 2))
    assert drop["narration"] == {"sentence": "s1_01", "said": "One."}
    assert drop["sfx"] == [{"type": "click", "cue": "drop", "time": 1.0, "frame": 30}]
    enter = found["enter"]                                          # at s2's first frame, its lead-in from s1
    assert (enter["clip"], enter["clips"], enter["contact_index"], enter["frames"][0]) == ("s2", ["s1", "s2"], 3, 54)
    moves = [w for w in found.values() if w["kind"] == "move"]
    assert [w["clip"] for w in moves] == ["s2", "s3"] and all(w["contact_index"] == 3 for w in moves)
    assert all(0 <= f - w["contact_frame"] <= 3 for w, f in zip(moves, (96, 138)))     # landings at 3.2 and 4.6 s
    assert moves[0]["narration"] == {"sentence": "s2_01", "said": "Two."}
    for w in found.values():
        assert (b / w["sheet"]).stat().st_size > 0
    assert (b / "SCRIPT.md").read_text().startswith("## Script") and "Evidence" not in (b / "SCRIPT.md").read_text()
    prompt = (b / "prompt.md").read_text()
    assert "```findings" in prompt and f"REVISION: {manifest['revision']}" in prompt and "Is it funny" not in prompt


def test_windows_at_the_videos_ends_say_where_the_contact_is_and_dropped_events_are_listed(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    v = tmp_path / "v"
    v.mkdir()
    motion_video(v, cues={"start": 0.0, "late": 5.95, "neg": -0.5, "after": 6.5})
    make_cut(v, 1, landings=(3.0,))
    prepare(v, 1)
    out = capsys.readouterr().out
    assert "no window for event neg at -0.5 s: before the video's start" in out and "after at 6.5 s: after the video's end" in out
    found = {w["name"]: w for w in json.loads((bundle_of(v, 1) / "windows.json").read_text())}
    assert (found["start"]["contact_index"], found["start"]["frames"][0]) == (0, 0)
    assert (found["late"]["contact_frame"], found["late"]["frames"], found["late"]["contact_index"]) == (179, [173, 175, 177, 179], 3)
    manifest = json.loads((bundle_of(v, 1) / "manifest.json").read_text())
    assert [d["name"] for d in manifest["dropped"]] == ["neg", "after"]
    assert "- neg at -0.5 s: before the video's start" in (bundle_of(v, 1) / "prompt.md").read_text()


def test_the_sheet_frames_come_from_the_cut_and_a_cut_without_its_video_keeps_windows_in_their_clip(video):
    d = make_cut(video, 1, video=False)
    rec = json.loads((d / "cut.json").read_text())
    t = tl.load(video)
    assert motion_review.source(video, 1, rec, t, "s2") is None
    clips = video / ".cache" / "clips"
    clips.mkdir(parents=True)
    for c, (a, b) in {"s1": (0, 2), "s2": (2, 4), "s3": (4, 5), "s4": (5, 6)}.items():
        graph = f"color=c=black:s=960x540:r=30:d={b - a}," + box(40, 0.5)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", graph, "-pix_fmt", "yuv420p",
                        str(clips / f"{c}-draft-k{c}.mp4")], check=True)
    assert motion_review.source(video, 1, rec, t, "s2") == (clips / "s2-draft-ks2.mp4", 0)    # the render the cut recorded
    prepare(video, 1)
    enter = next(w for w in json.loads((bundle_of(video, 1) / "windows.json").read_text()) if w["name"] == "enter")
    assert enter["clips"] == ["s2"] and enter["contact_index"] == 0
    (d / "video.mp4").write_bytes(b"")
    assert motion_review.source(video, 1, rec, t, "s2") == (d / "video.mp4", 60)          # the cut's own video first


def test_the_stop_rule_ends_at_a_round_without_must_fix_and_leaves_known_issues(video, tmp_path, capsys):
    make_cut(video, 1)
    prepare(video, 1)
    f = tmp_path / "bare.md"
    f.write_text("MUST FIX | drop | 1.0 s | frame 30 | pop\n")
    with pytest.raises(SystemExit, match="exact REVISION"):
        motion_review.main(SimpleNamespace(video=video, cut=1, result=f))
    with pytest.raises(SystemExit, match="no verdict line"):
        respond(video, 1, "MUST FIX | drop | 1.0 s | frame 30 | pop", tmp_path)
    with pytest.raises(SystemExit, match="MOTION: FIX but no finding could be read"):
        respond(video, 1, "It pops somewhere.\nMOTION: FIX", tmp_path)
    assert respond(video, 1, "**Must fix** | drop | 1.0 s | frame 30 | the token pops in. Fix: ease it\n"
                             "- SHOULD FIX — drop — 1.2 s — frame 36 — late settle\n**MOTION: FIX**", tmp_path) == 1
    rec = review_state.read(video, "motion")
    assert (rec["status"], rec["round"], rec["cut"], rec["must_fix"]) == ("findings", 1, 1, 1) and "stopped" not in rec
    findings = json.loads((bundle_of(video, 1) / "findings.json").read_text())
    assert findings["findings"][0] == {"severity": "must-fix", "window": "drop", "t": 1.0, "frame": 30,
                                       "text": "the token pops in. Fix: ease it"}
    assert "known_issues" not in json.loads((video / "cuts" / "cut1" / "cut.json").read_text())
    with pytest.raises(SystemExit, match="the motion review of cut 1 is unresolved: its status is findings"):
        review_state.require(video, "motion")
    with pytest.raises(SystemExit, match="has had its motion review"):        # its result is kept
        prepare(video, 1)
    with pytest.raises(SystemExit, match="imported already"):                  # and the reviewer is not re-rolled
        respond(video, 1, "MOTION: PASS", tmp_path)
    assert review_state.read(video, "motion")["status"] == "findings"

    edit(video, what="the pop fixed")
    make_cut(video, 2)
    prepare(video, 2)
    b2 = bundle_of(video, 2)
    assert json.loads((b2 / "manifest.json").read_text())["round"] == 2
    assert "Findings from the last round (round 1, cut 1)" in (b2 / "prompt.md").read_text()
    assert json.loads((b2 / "previous.json").read_text())["findings"][0]["text"].startswith("the token pops in")
    assert respond(video, 2, "```findings\nSHOULD FIX | drop | 1.2 s | frame 36 | late settle. Fix: shorten it\nNIT | drop | "
                             "1.0 s | frame 30 | shadow\n```\n```regressions\nFIXED | drop | the pop\n```\n"
                             "MUST FIX: 0 · SHOULD FIX: 1 · NIT: 1\nMOTION: PASS", tmp_path) == 0
    assert "known issue(s) recorded on cut 2" in capsys.readouterr().out
    rec = review_state.read(video, "motion")
    assert (rec["status"], rec["round"], rec["stopped"], rec["left"]) == ("known-issues", 2, "clean", 2)
    assert json.loads((b2 / "findings.json").read_text())["regressions"][0]["status"] == "fixed"
    issues = json.loads((video / "cuts" / "cut2" / "cut.json").read_text())["known_issues"]
    assert [(i["severity"], i["cut"]) for i in issues] == [("should-fix", 2), ("nit", 2)]
    assert page.state(video, 2)["cut"]["known_issues"] == issues                 # the desk shows them under the cut
    review_state.require(video, "motion")

    edit(video, "s3", what="a frame-review fix")            # a small later edit doesn't reopen a review that ended
    review_state.require(video, "motion")
    make_cut(video, 3)
    with pytest.raises(SystemExit) as refused:     # it read as if something were still open
        prepare(video, 3)
    said = str(refused.value)
    assert said.startswith("the motion review is settled and nothing more is needed: it ended by its rule with 2 "
                           "should-fix or nit finding(s) left, recorded on cut 2 as known issues")
    assert "motion_rounds (2) allows no round 3" in said and "raise" not in said and "waived" not in said
    (video / "video.json").write_text(json.dumps({"teaching_contract": True, "motion_rounds": 3}))
    prepare(video, 3)


def test_an_only_should_fix_round_is_known_issues_whatever_the_verdict_says(video, tmp_path, capsys):
    make_cut(video, 1)
    prepare(video, 1)
    assert respond(video, 1, "SHOULD FIX | drop | 1.0 s | frame 30 | lag\nMOTION: FIX", tmp_path) == 0
    assert "the status follows the findings" in capsys.readouterr().out
    rec = review_state.read(video, "motion")
    assert (rec["status"], rec["stopped"], rec["must_fix"]) == ("known-issues", "clean", 0)
    review_state.require(video, "motion")


def test_must_fix_at_the_cap_is_reported_open_never_passed(video, tmp_path, capsys):
    for n in (1, 2):
        if n == 2:
            edit(video, what="round two")
        make_cut(video, n)
        prepare(video, n)
        code = respond(video, n, "MUST FIX | drop | 1.0 s | frame 30 | pop\nSHOULD FIX | drop | 1.1 s | frame 33 | lag\n"
                                 "MOTION: PASS", tmp_path)          # a PASS with a must-fix is findings
    assert code == 1
    out = capsys.readouterr().out
    assert "verdict line says PASS but 1 finding(s) are MUST FIX" in out and "motion: OPEN at the cap (round 2 of 2)" in out
    rec = review_state.read(video, "motion")
    assert (rec["status"], rec["stopped"]) == ("findings", "cap")
    assert [i["text"] for i in json.loads((video / "cuts" / "cut2" / "cut.json").read_text())["known_issues"]] == ["lag"]
    with pytest.raises(SystemExit, match="stopped at its cap with must-fix findings open"):
        review_state.require(video, "motion")
    text = handoff.assemble(video)
    assert "motion: findings, OPEN at the round cap" in text and "motion review stopped at its cap" in text


def test_a_recut_of_an_unchanged_revision_spends_a_round(video, tmp_path):
    for n in (1, 2):
        make_cut(video, n)
        prepare(video, n)
        assert json.loads((bundle_of(video, n) / "manifest.json").read_text())["round"] == n
        respond(video, n, "MUST FIX | drop | 1.0 s | frame 30 | pop\nMOTION: FIX", tmp_path)
    make_cut(video, 3)
    with pytest.raises(SystemExit, match=r"would pass motion_rounds.*cut 2\) stopped at the cap with 1 must-fix finding\(s\) "
                                         r"open.*raise video.json motion_rounds") as refused:
        prepare(video, 3)
    assert f"studio review-status {video.resolve()} motion waived" in str(refused.value)     # not a VIDEO placeholder


def test_only_a_structural_mark_over_a_changed_picture_starts_a_new_count(video, tmp_path):
    for n in (1, 2):
        edit(video, what=f"round {n}")
        make_cut(video, n)
        prepare(video, n)
        respond(video, n, "MUST FIX | drop | 1.0 s | frame 30 | pop\nMOTION: FIX", tmp_path)
    edit(video, what="a one-pixel nudge")
    stage.mark(video, "revision", kind="structural", summary="(not really)")
    make_cut(video, 3)
    with pytest.raises(SystemExit, match="would pass motion_rounds"):
        prepare(video, 3)
    edit(video, "s1", "s3", what="rebuilt")
    stage.mark(video, "revision", kind="structural", summary="a new arc")
    make_cut(video, 4)
    prepare(video, 4)
    assert json.loads((bundle_of(video, 4) / "manifest.json").read_text())["round"] == 1


def test_a_review_of_the_old_picture_does_not_stand_for_the_new_one(video, tmp_path):
    make_cut(video, 1)
    prepare(video, 1)
    edit(video, "s1", "s2", what="rewritten")
    stage.mark(video, "revision", kind="structural", summary="a new arc")
    assert respond(video, 1, "MOTION: PASS", tmp_path) == 0          # imported after the mark, recorded stale
    with pytest.raises(SystemExit, match=r"no longer stands: cut 1 came before the revision mark"):
        review_state.require(video, "motion")


def test_a_passed_review_goes_stale_when_much_of_the_picture_changes(video, tmp_path):
    make_cut(video, 1)
    prepare(video, 1)
    respond(video, 1, "MOTION: PASS", tmp_path)
    edit(video, "s4", what="one chapter touched")
    review_state.require(video, "motion")
    edit(video, "s1", what="and another")
    with pytest.raises(SystemExit, match=r"since cut 1, s1, s4 changed \(2 of 4 clips\)\. Mark a structural revision"):
        review_state.require(video, "motion")
    (video / "scenes" / "s1.tsx").write_text("// s1.tsx\n")       # both back as they were
    (video / "scenes" / "s4.tsx").write_text("// s4\n")
    review_state.require(video, "motion")
    t = tl.load(video)
    t["tracks"]["scene"].append({"id": "s5", "engine": "remotion", "title": "E", "start": 6.0, "end": 7.0})
    (video / "timeline.json").write_text(json.dumps(t))
    with pytest.raises(SystemExit, match="s5 new"):
        review_state.require(video, "motion")


def test_a_comic_bundle_reads_the_comic_questions_from_the_style_file(video, tmp_path):
    (video / "video.json").write_text(json.dumps({"teaching_contract": True, "tone": "comic"}))
    make_cut(video, 1)
    prepare(video, 1)
    prompt = (bundle_of(video, 1) / "prompt.md").read_text()
    assert "This video's tone is comic." in prompt and "**Is it funny?**" in prompt and "GAG | window name | n/5" in prompt
    assert "## Motion review" not in prompt
    assert "This video's tone is comic. Answer these for the cut under review:\n\n1. **Is it funny?**" in prompt
    assert "written to be included" not in prompt          # comic.md's note to builders stays in comic.md
    respond(video, 1, "```findings\nGAG | drop | 4/5 | the pause sells it\n```\nMOTION: PASS", tmp_path)
    assert json.loads((bundle_of(video, 1) / "findings.json").read_text())["gags"] == [
        {"window": "drop", "score": 4, "text": "the pause sells it"}]
    assert review_state.read(video, "motion")["status"] == "passed"


def test_handoff_picks_up_a_motion_bundle_waiting_for_its_result(video):
    make_cut(video, 1)
    prepare(video, 1)
    text = handoff.assemble(video)
    assert "motion review of cut 1 prepared, not imported: research/motion_review/cut1-" in text
    assert 'studio review-motion "$VIDEO" --cut 1 --result FILE' in text


def test_a_frames_receipt_with_findings_is_addressed_not_must_fixed(video):
    make_cut(video, 1)
    review_state.record(video, "frames", review_state.revision(video, reviews.KINDS["frames"]), "findings", str(video / "r.md"))
    nxt = handoff.assemble(video).split("## Next")[1]
    assert "Address the findings in r.md, then make a fresh cut" in nxt and "must-fix" not in nxt


def test_publish_asks_an_explainer_for_its_motion_review(video, monkeypatch):
    from studio_kit import check, publish
    monkeypatch.setattr(check, "run", lambda video, everything: [])
    review_state.record(video, "student", review_state.revision(video, reviews.KINDS["script"]), "waived", "user said so")
    with pytest.raises(SystemExit, match=r"publish now needs a motion review.*new in this kit.*with the user's agreement"):
        publish.gate(video)
    review_state.record(video, "motion", review_state.revision(video, reviews.KINDS["motion"]), "waived",
                        "the user accepts the motion as it is")
    publish.gate(video)
    (video / "video.json").write_text(json.dumps({"teaching_contract": True, "genre": "motion"}))
    (video / "research" / "reviews" / "motion.json").unlink()
    publish.gate(video)


def test_a_motion_waiver_records_the_mode_and_the_desk_notes_it_cites(video, capsys):
    d = make_cut(video, 1)
    motion_review.write_known_issues(video, 1, [{"severity": "nit", "window": "drop", "t": 1.0, "frame": 30, "text": "x", "cut": 1}])
    page.append(video, {"type": "note", "id": "ab12cd34", "cut": 1, "t": 1.0, "note": "the drop lands late"})
    status = lambda reason: review_state.main_status(cli.build_parser().parse_args(
        ["review-status", str(video), "motion", "waived", "--reason", reason]))
    with pytest.raises(SystemExit, match="only in interactive mode"):
        status("the user's desk notes ab12cd34 stand in")
    (video / "video.json").write_text(json.dumps({"teaching_contract": True, "mode": "interactive"}))
    with pytest.raises(SystemExit, match="by their ids"):
        status("the user's desk notes stand in")
    status("the user's desk notes ab12cd34 stand in")
    assert "(cut 1, its 1 known issue(s) accepted)" in capsys.readouterr().out
    rec = review_state.read(video, "motion")
    assert (rec["mode"], rec["notes"], rec["cut"], rec["accepted"]) == ("interactive", ["ab12cd34"], 1, 1)
    assert rec["cut_t"] == json.loads((d / "cut.json").read_text())["t"]
    review_state.require(video, "motion")


def test_a_new_cut_snapshots_its_effects_and_layout_and_carries_the_known_issues(tmp_path):
    from studio_kit import render
    from test_build import StillEngine
    (tmp_path / "video.json").write_text(json.dumps({"title": "Reel", "duration": 3}))
    (tmp_path / "cues.json").write_text(json.dumps({"logo": 2.0}))
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "sfx.json").write_text(json.dumps([{"t": "logo", "type": "click"}]))
    tl.build(tmp_path)
    rec = render.make_cut(tmp_path, stills_only=True, engine=StillEngine())
    d = Path(tmp_path) / "cuts" / f"cut{rec['cut']}"
    assert json.loads((d / "sfx.json").read_text()) == [{"t": "logo", "type": "click", "time": 2.0}]
    assert json.loads((d / "layout.json").read_text())["band"] == tl.layout(tmp_path)["band"] and "t" in rec
    issues = [{"severity": "should-fix", "window": "logo", "t": 2.0, "frame": 60, "text": "late settle", "cut": 1}]
    motion_review.write_known_issues(tmp_path, rec["cut"], issues)
    assert render.make_cut(tmp_path, stills_only=True, engine=StillEngine())["known_issues"] == issues


def test_the_bundle_carries_the_look_sheet_and_says_when_it_is_missing_or_stale(video, tmp_path, capsys):
    """"On sheet" is judged against the look sheet: its pages are copied into the bundle, and a video
    with none, or with one older than its sources, is flagged in the manifest and the prompt."""
    from studio_kit import look, settings
    from test_look import FakeEngine
    make_cut(video, 1)
    prepare(video, 1)
    b = bundle_of(video, 1)
    assert json.loads((b / "manifest.json").read_text())["look"] == {"status": "missing", "pages": [], "titles": []}
    assert "no look sheet" in (b / "prompt.md").read_text() and "the look sheet is missing" in capsys.readouterr().out
    look.make(video, engine=FakeEngine(video, settings.load(video)["engine"]))
    make_cut(video, 2)
    prepare(video, 2)
    b = bundle_of(video, 2)
    sheet = json.loads((b / "manifest.json").read_text())["look"]
    assert sheet == {"status": "current", "pages": ["look/look-1.png", "look/look-2.png"], "titles": ["colour and type", "elements and states"]}
    assert (b / "look" / "look-1.png").read_bytes() == b"png"
    prompt = (b / "prompt.md").read_text()
    assert "drawn as the look sheet (look/) draws them" in prompt and "stale" not in prompt
    (video / "layout.json").write_text(json.dumps({"width": 1920, "height": 1080, "fps": 30, "band": {"height": 200}}))
    respond(video, 2, "```findings\n```\nMOTION: PASS", tmp_path)
    make_cut(video, 3)
    prepare(video, 3)
    b = bundle_of(video, 3)
    assert json.loads((b / "manifest.json").read_text())["look"]["status"] == "stale"
    assert "the look sheet is stale" in (b / "prompt.md").read_text()


@pytest.mark.skipif(not any(f.is_file() for f in motion_review.LABEL_FONTS), reason="none of the label fonts is here")
def test_frame_labels_name_their_font_so_fontconfig_says_nothing(tmp_path, monkeypatch, capfd):
    """drawtext asked fontconfig for a font, which printed "Fontconfig error: Cannot load default
    config file" about a dozen times a review where it had no config."""
    import subprocess
    clip = tmp_path / "clip.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=s=320x180:r=30:d=1", "-pix_fmt", "yuv420p", str(clip)], check=True)
    monkeypatch.setenv("FONTCONFIG_FILE", str(tmp_path / "no-fonts.conf"))
    assert motion_review.sheet(clip, [3, 4, 5, 6], 0, 4, 30, tmp_path / "sheet.png") is True
    assert "Fontconfig" not in capfd.readouterr().err and (tmp_path / "sheet.png").exists()
