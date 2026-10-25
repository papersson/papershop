import json
from pathlib import Path

import pytest

from studio_kit import check, keys, narration, render, script, script_check, timeline
from test_narration import SCRIPT, video


def test_breath_keeps_speech_cache_and_marks_only_its_silent_interval(tmp_path):
    v = video(tmp_path)
    before = script.load(v)
    (v / 'SCRIPT.md').write_text(SCRIPT.replace('Then the network goes quiet.',
                                              'Then the network goes quiet. [breath 2.5]'))
    assert script.load(v) == before  # synthesis and captions see identical words/paragraphs
    S = narration.Settings(v)
    durations = {sid: 1 for _, _, ss in before for sid, _, _ in ss}
    normal = narration.layout(S, before, durations)
    line = normal['segments'][0]['lines'][1]
    assert line['pause'] == {'seconds': 2.5, 'prediction': False, 'breath': True,
                             'start': line['end'], 'end': line['end'] + 2.5}
    assert normal['segments'][0]['lines'][2]['start'] >= line['pause']['end']
    tl = timeline.from_timings(normal)
    assert tl['tracks']['narration'][1]['pause'] == line['pause']
    assert tl['cues']['reveal:s1_02'] == line['pause']['end']
    caption = next(c for c in tl['tracks']['captions'] if c['anchor']['sentence'] == 's1_02')
    assert caption['end'] == line['pause']['end']  # no caption disappearance mid-breath
    assert not any(s.prediction for c in script.read(v) for s in c.sentences)


@pytest.mark.parametrize('marker', ['[breath]', '[breath -1]', '[breath NaN]',
                                  '[breath 2] [pause 1]', '[breath 2'])
def test_invalid_breath_fails_with_source_location(tmp_path, marker):
    (tmp_path / 'SCRIPT.md').write_text(f'## Script\n### 1. A\n> Hello. {marker}\n')
    with pytest.raises(SystemExit, match='SCRIPT.md:3'):
        script.read(tmp_path)


def test_inline_prediction_moves_with_the_sentence_and_never_enters_speech(tmp_path):
    v = video(tmp_path)
    original = SCRIPT.replace("Did the charge go through?", "Did the charge go through? [predict 3]")
    (v / "SCRIPT.md").write_text(original)
    sentences = [s for c in script.read(v) for s in c.sentences]
    question = next(s for s in sentences if s.prediction)
    assert question.id == "s1_03" and question.text == "Did the charge go through?" and question.pause == 3
    S = narration.Settings(v)
    cap = " ".join(t for _, _, sents in script.load(v) for _, t, _ in sents)
    assert "[predict" not in cap
    chunk_key = narration.kokoro_key(S, cap)
    (v / "SCRIPT.md").write_text(original.replace("[predict 3]", "[predict 2]"))
    assert chunk_key == narration.kokoro_key(S, " ".join(t for _, _, ss in script.load(v) for _, t, _ in ss))
    (v / "SCRIPT.md").write_text(original.replace("Did the charge", "We have no reply. Did the charge"))
    question = next(s for c in script.read(v) for s in c.sentences if s.prediction)
    assert question.id == "s1_04" and question.pause == 3


@pytest.mark.parametrize("text", ["[pause 2] Hello.", "Hello [beat] world.", "Hello. [pause -2]",
                                  "Hello. [pause NaN]", "Hello. [beat 2]", "Hello. [predict]",
                                  "Hello. [pause 1] [beat]", "Hello. [pause 2"])
def test_invalid_markers_fail_with_source_location(tmp_path, text):
    (tmp_path / "SCRIPT.md").write_text(f"## Script\n### 1. A\n> {text}\n")
    with pytest.raises(SystemExit, match="SCRIPT.md:3"):
        script.read(tmp_path)


def test_inline_pause_replaces_legacy_hold_and_default_and_produces_reveal(tmp_path):
    v = video(tmp_path, {"holds": {"s1_03": 8}, "timing": {"chapter_hold": 2}})
    (v / "SCRIPT.md").write_text(SCRIPT.replace("Did the charge go through?", "Did the charge go through? [predict 3]"))
    S, chapters = narration.Settings(v), script.load(v)
    t = narration.layout(S, chapters, {sid: 1 for _, _, ss in chapters for sid, _, _ in ss})
    last = t["segments"][0]["lines"][-1]
    assert last["pause"]["seconds"] == 3
    assert last["pause"]["end"] == last["end"] + 3
    tl = timeline.from_timings(t)
    assert tl["cues"]["reveal:s1_03"] == last["end"] + 3
    assert all("predict" not in x["caption"] for x in tl["tracks"]["narration"])


def test_prediction_cues_and_pause_metadata_do_not_invalidate_shifted_chapter(tmp_path):
    v = video(tmp_path)
    (v / "SCRIPT.md").write_text(SCRIPT.replace("Send a key with every attempt.", "Send a key with every attempt. [beat]"))
    (v / "scenes").mkdir()
    for name in ("s1", "s2"):
        (v / "scenes" / f"{name}.tsx").write_text("// scene")
    S, chapters = narration.Settings(v), script.load(v)
    durations = {sid: 1 for _, _, ss in chapters for sid, _, _ in ss}
    a = timeline.from_timings(narration.layout(S, chapters, durations))
    durations["s1_01"] = 2.3
    b = timeline.from_timings(narration.layout(S, chapters, durations))
    assert keys.clip_key(v, a, "s2", "draft") == keys.clip_key(v, b, "s2", "draft")


def test_script_check_runs_without_timeline_engine_or_audio(tmp_path, monkeypatch):
    video(tmp_path)
    monkeypatch.setattr(check, "Engine", lambda *a, **kw: pytest.fail("no browser for text checks"))
    rows = check.run(tmp_path, only=["script"])
    assert rows and not (tmp_path / "timeline.json").exists()
    assert all(r["ok"] for r in rows)  # Brief diagnostics leave the story decision with the user.


def test_runtime_and_meta_diagnostics_and_scoped_acceptance(tmp_path):
    video(tmp_path)
    (tmp_path / "SCRIPT.md").write_text(SCRIPT.replace("A checkout page", "This video shows 32 JSON values. A checkout page"))
    (tmp_path / "video.json").write_text(json.dumps({"target_minutes": 0.01,
        "script_check": {"products": {"JSON": []}, "accept": ["meta:s1_01"]}}))
    rows = script_check.run(tmp_path)
    assert not any(r["rule"] == "meta" for r in rows)
    assert any(r["rule"] == "length" for r in rows)
    assert any("1 (JSON)" in r["detail"] for r in rows)
