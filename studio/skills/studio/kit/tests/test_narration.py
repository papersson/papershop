import pytest
import json
import math

import numpy as np

from studio_kit import narration as nr
from studio_kit import script as sc

SCRIPT = """# T

## Script

### 1. Opening

> A checkout page asks the server to charge. Then the network goes quiet.
> Did the charge go through?

*Screen:* two boxes.

### 2. Keys

> Send a key with every attempt.

## Evidence
"""


def video(tmp_path, cfg=None):
    (tmp_path / "SCRIPT.md").write_text(SCRIPT)
    if cfg:
        (tmp_path / "narration.json").write_text(json.dumps(cfg))
    return tmp_path


def test_script_splits_chapters_paragraphs_and_sentences(tmp_path):
    chapters = sc.load(video(tmp_path))
    assert [(c, t) for c, t, _ in chapters] == [("s1", "Opening"), ("s2", "Keys")]
    assert chapters[0][2] == [("s1_01", "A checkout page asks the server to charge.", 0),
                              ("s1_02", "Then the network goes quiet.", 0),
                              ("s1_03", "Did the charge go through?", 1)]


def test_layout_places_gaps_holds_and_chapter_edges(tmp_path):
    S = nr.Settings(video(tmp_path, {"holds": {"s1_02": 1.0}, "tail": 2.0}))
    chapters = sc.load(tmp_path)
    t = nr.layout(S, chapters, {k: 1.0 for _, _, ss in chapters for k, _, _ in ss}, gaps={"s1_01": 0.25})
    s1, s2 = t["segments"]
    starts = [l["start"] for l in s1["lines"]]
    assert starts == [nr.LEAD_IN, nr.LEAD_IN + 1.25, nr.LEAD_IN + 1.25 + 1.0 + 1.0 + nr.PARAGRAPH_GAP]
    # the next chapter starts on the 0.1 s grid, and its clip PRE_ROLL_FRAMES before that, on the frame grid
    grid = math.ceil(round((starts[-1] + 1.0 + nr.SEGMENT_GAP) / nr.CHAPTER_GRID, 6)) * nr.CHAPTER_GRID
    assert s2["lines"][0]["start"] == round(grid, 3)
    assert s1["end"] == s2["start"] == (round(grid * 30) - nr.PRE_ROLL_FRAMES) / 30
    assert t["total"] == round(s2["lines"][0]["end"] + 2.0, 3)


def test_spoken_respellings_apply_globally_and_per_sentence(tmp_path):
    S = nr.Settings(video(tmp_path, {"spoken": [["UUID", "U U I D"]], "spoken_by_id": {"s2_01": [["key", "kee"]]}}))
    assert S.spoken("a UUID key", "s1_01") == "a U U I D key"
    assert S.spoken("a UUID key", "s2_01") == "a U U I D kee"


def tone_and_silence(pieces):
    """Audio of (seconds, loud) pieces at the engine rate."""
    return np.concatenate([(0.5 * np.sin(np.arange(int(d * nr.RATE)) * 0.3) if loud else np.zeros(int(d * nr.RATE)))
                           .astype(np.float32) for d, loud in pieces])


def test_paragraph_clips_cut_at_the_pause_and_keep_words_relative(tmp_path):
    S = nr.Settings(video(tmp_path))
    texts = ["One two.", "Three four."]
    full = " ".join(texts)
    audio = tone_and_silence([(0.2, False), (1.0, True), (0.5, False), (1.0, True), (0.2, False)])
    words = [(0, 0.2, 0.6), (4, 0.6, 1.2), (9, 1.7, 2.1), (15, 2.1, 2.7)]
    chunk = [("s1_01", texts[0], 0), ("s1_02", texts[1], 0)]
    clips, gaps, said, words_by = nr.paragraph_clips(S, lambda f, p, n: (audio, words), [(chunk, "", "")])
    assert abs(len(clips["s1_01"]) / nr.RATE - 1.0) < 0.05
    assert abs(gaps["s1_01"] - 0.5) < 0.05
    assert [w for w, _, _ in words_by["s1_02"]] == ["Three", "four"]
    assert words_by["s1_02"][0][1] < 0.05


def test_kokoro_chunks_come_from_the_cache_without_kokoro(tmp_path):
    S = nr.Settings(video(tmp_path))
    full = "Send a key with every attempt."
    cache = tmp_path / ".cache" / "narration"
    cache.mkdir(parents=True)
    key = nr.kokoro_key(S, full)
    np.save(cache / f"{key}.npy", np.ones(10, dtype=np.float32))
    (cache / f"{key}.json").write_text(json.dumps([[0, 0.0, 0.1]]))
    audio, words = nr.kokoro_engine(S)(full, "", "")
    assert len(audio) == 10 and words == [(0, 0.0, 0.1)]
    _, chunks, todo = nr.plan(tmp_path)
    assert len(chunks) == 3 and [c[0][0] for c, _ in todo] == ["s1_01", "s1_03"]


def test_estimate_writes_a_timeline_scenes_can_be_timed_against(tmp_path):
    nr.narrate(video(tmp_path), estimate=True)
    t = json.loads((tmp_path / "timeline.json").read_text())
    assert [c["id"] for c in t["tracks"]["scene"]] == ["s1", "s2"]
    assert len(t["tracks"]["narration"]) == 4 and t["tracks"]["captions"]


def test_a_refused_narration_refuses_before_the_pronunciation_pass(tmp_path, monkeypatch):
    """A narrate the review gate refused loaded torch and ran the pronunciation pass first."""
    from studio_kit import pronounce
    (video(tmp_path) / "video.json").write_text(json.dumps({"teaching_contract": True}))
    monkeypatch.setattr("studio_kit.script_check.run", lambda video: [])
    monkeypatch.setattr(pronounce, "report", lambda S, chapters: pytest.fail("the pronunciation pass ran before the gates"))
    with pytest.raises(SystemExit, match="^no student review is recorded"):
        nr.narrate(tmp_path)


def test_voice_check_spells_numbers_before_comparing():
    from studio_kit.voice_check import score
    assert score("It took 18 doublings in 2023.", "it took eighteen doublings in twenty twenty-three") > 0.95
    assert score("It took 18 doublings.", "it took doublings") < 0.8      # a dropped word is flagged


def test_spoken_respellings_match_whole_words_only(tmp_path):
    S = nr.Settings(video(tmp_path, {"spoken": [["A", "Ay"], ["rr", "R R"]]}))
    assert S.spoken("All of A, and rr's error", "s1_01") == "All of Ay, and R R's error"


def test_phoneme_overrides_mark_kokoro_input_only(tmp_path):
    S = nr.Settings(video(tmp_path, {"phonemes": {"JSON": "ʤˈAsᵊn"}, "phonemes_by_id": {"s1_02": {"A": "ˈA"}}}))
    assert S.marked("A JSON reply", "s1_01") == "A [JSON](/ʤˈAsᵊn/) reply"
    assert S.marked("A reads All", "s1_02") == "[A](/ˈA/) reads All"
    S.phonemes_by_id["s1_03"] = {"A": "ˈA", "A's": "ˈAz"}
    assert S.marked("A's turn, then A", "s1_03") == "[A's](/ˈAz/) turn, then [A](/ˈA/)"
    seen = []

    def synth(full, prev, nxt, marked=None):
        seen.append((full, marked))
        return tone_and_silence([(0.2, False), (1.0, True), (0.2, False)]), [(0, 0.2, 0.6), (2, 0.6, 1.2)]

    nr.paragraph_clips(S, synth, [([("s1_02", "A reads.", 0)], "", "")])
    assert seen == [("A reads.", "[A](/ˈA/) reads.")]


def test_pronunciation_lint_flags_a_lone_letter_read_as_the_article(tmp_path):
    pytest.importorskip("misaki")
    from studio_kit import pronounce

    (tmp_path / "SCRIPT.md").write_text("# T\n\n## Script\n\n### 1. One\n\n> A reads one. Then B writes. A unit test passes.\n"
                                        "> Encode it as JSON with rr, keyed by id.\n\n## Evidence\n")
    S = nr.Settings(tmp_path)
    found = pronounce.find(S, sc.load(tmp_path))
    kinds = {(k, lid, w) for k, lid, w, _, _ in found}
    assert ("letter", "s1_01", "A") in kinds and ("letter", "s1_03", "A") not in kinds   # obvious article; preserve the variable warning
    assert not any(w == "B" for _, _, w in kinds)                                     # B is read as its name
    assert ("acronym", "s1_04", "JSON") in kinds and ("unknown", "s1_04", "rr") in kinds
    assert ("word", "s1_04", "id") in kinds                                             # read as the Freudian id
    S = nr.Settings(tmp_path)
    S.phonemes_by_id = {"s1_01": {"A": "ˈA"}}
    assert ("letter", "s1_01", "A") not in {(k, lid, w) for k, lid, w, _, _ in pronounce.find(S, sc.load(tmp_path))}


def test_a_longer_chapter_shifts_later_chapters_by_whole_frames_and_milliseconds(tmp_path):
    """So later chapters' clips, keyed on times relative to their first frame, stay cached."""
    S = nr.Settings(video(tmp_path))
    chapters = sc.load(tmp_path)
    durs = {k: 1.0 for _, _, ss in chapters for k, _, _ in ss}
    a = nr.layout(S, chapters, durs)
    durs["s1_02"] = 1.37
    b = nr.layout(S, chapters, durs)
    shift = b["segments"][1]["start"] - a["segments"][1]["start"]
    assert shift > 0 and abs(shift * 30 - round(shift * 30)) < 1e-9 and abs(shift * 1000 - round(shift * 1000)) < 1e-6
    rel = lambda t: [round(l["start"] - t["segments"][1]["start"], 6) for l in t["segments"][1]["lines"]]
    assert rel(a) == rel(b)


def test_moved_chapters_keep_identical_relative_times_and_clip_keys(tmp_path):
    """Float drift in absolute times once changed a later chapter's key by 1 ms; offsets are exact."""
    from studio_kit import render, timeline as tl
    v = video(tmp_path)
    (v / "scenes").mkdir()
    (v / "scenes" / "s1.tsx").write_text("//")
    (v / "scenes" / "s2.tsx").write_text("//")
    S = nr.Settings(v)
    chapters = sc.load(v)
    durs = {"s1_01": 2.217, "s1_02": 1.873, "s1_03": 3.331, "s2_01": 2.0}
    keys = []
    for extra in (0.0, 0.456, 1.2345):
        d = {**durs, "s1_02": durs["s1_02"] + extra}
        t = tl.from_timings(nr.layout(S, chapters, d))
        keys.append(render.clip_key(v, t, "s2", "draft"))
    assert keys[0] == keys[1] == keys[2]


def test_estimated_timelines_say_so(tmp_path):
    from studio_kit import narration, timeline as tl
    (tmp_path / "SCRIPT.md").write_text(SCRIPT)
    narration.narrate(tmp_path, estimate=True)
    t = tl.load(tmp_path)
    assert t["timing"] == "estimate" and tl.timing(tmp_path) == "estimate"
    del t["timing"]                                   # an older timeline: no record, no audio
    t["tracks"]["audio"] = [{"file": "audio/narration.mp3", "start": 0.0}]
    assert tl.timing(tmp_path, t) == "estimate"
    (tmp_path / "audio" / "narration.mp3").write_bytes(b"mp3")
    assert tl.timing(tmp_path, t) == "narrated"


def test_eleven_fetch_stops_before_spending_more_than_the_account_has(tmp_path, monkeypatch):
    """A run that needs more characters than the account has left fails before any synthesis."""
    from types import SimpleNamespace
    from studio_kit import narration
    calls = []

    def fake_call(key, method, path, body=None):
        calls.append(path)
        if path == "/user/subscription":
            return {"character_limit": 10000, "character_count": 9990}
        raise AssertionError("no synthesis call may happen")

    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-key")
    monkeypatch.setattr(narration, "eleven_call", fake_call)
    monkeypatch.setattr(narration, "eleven_request", lambda S, full, p, n: ({"text": full}, tmp_path / "missing.json"))
    S = SimpleNamespace(eleven={"model": "eleven_multilingual_v2", "voice_id": "v", "voice": "Alice"}, audio=tmp_path)
    chunks = [([("s1_01", "A sentence long enough to cost more than ten characters.", None)], None, None)]
    with pytest.raises(SystemExit, match="nothing was spent"):
        narration.eleven_fetch(S, chunks, yes=True)
    assert calls == ["/user/subscription"]


def test_eleven_call_reports_the_refusal_not_the_key(monkeypatch):
    import io
    import urllib.error
    from studio_kit import narration
    body = b'{"detail": {"status": "quota_exceeded", "message": "This request exceeds your API key quota"}}'

    def refuse(req, timeout=0):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO(body))

    monkeypatch.setattr(narration.urllib.request, "urlopen", refuse)
    with pytest.raises(SystemExit) as e:
        narration.eleven_call("secret-key", "POST", "/text-to-speech/v/with-timestamps?x=1", {"text": "hi"})
    assert "exceeds your API key quota" in str(e.value) and "resumes" in str(e.value)
    assert "secret-key" not in str(e.value)
