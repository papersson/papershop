"""Pauses and speeds by role, and the delivery report that measures them."""
import json

import numpy as np
import pytest

from studio_kit import animatic, delivery, narration as nr, new, script as sc

SCRIPT = """# T

## Ledgers

- **Vocabulary.** idempotency key (s2), ledger (s2; the table of charges).

## Script

### 1. Opening

> A page asks the server to charge. Then the network goes quiet.
> Did the charge go through? Nobody knows.
> A timeout says nothing about the work. [key]
> One more sentence here. And one more.

### 2. Keys

> [recap] Send an idempotency key. Keep it in the ledger.
> The ledger is a table. An idempotency key names one attempt. [aside]

## Evidence
"""


def video(tmp_path, cfg=None, script=SCRIPT):
    (tmp_path / "SCRIPT.md").write_text(script)
    if cfg is not None:
        (tmp_path / "narration.json").write_text(json.dumps(cfg))
    return tmp_path


def starts(t):
    return {l["id"]: (l["start"], l["end"]) for seg in t["segments"] for l in seg["lines"]}


def test_markers_give_roles_to_a_sentence_or_a_whole_paragraph(tmp_path):
    sents = {s.id: s for c in sc.read(video(tmp_path)) for s in c.sentences}
    assert sents["s1_05"].role == "key" and sents["s1_05"].text == "A timeout says nothing about the work."
    assert [sents[k].role for k in ("s2_01", "s2_02", "s2_03", "s2_04")] == ["recap", "recap", None, "aside"]
    assert sents["s1_01"].role is None
    # one hold and one role on a sentence is fine; two of either is not
    assert sc.paragraph("Think. [predict 2] [key]", 1, 0.5) == [("Think.", 2.0, True, "key")]


@pytest.mark.parametrize("text", ["Hello. [key] [aside]", "Hello. [key 2]", "Hello [key] world.", "Hi. [recap"])
def test_invalid_role_markers_fail_with_source_location(tmp_path, text):
    (tmp_path / "SCRIPT.md").write_text(f"## Script\n### 1. A\n> {text}\n")
    with pytest.raises(SystemExit, match="SCRIPT.md:3"):
        sc.read(tmp_path)


def test_the_vocabulary_ledger_names_terms_in_its_list_or_table(tmp_path):
    assert sc.vocabulary(video(tmp_path)) == ["idempotency key", "ledger"]
    table = SCRIPT.replace("- **Vocabulary.** idempotency key (s2), ledger (s2; the table of charges).",
                           "**Vocabulary.**\n| Term | First use | Meaning |\n|---|---|---|\n| timeout | ch. 1 | x |\n| ledger | ch. 2 | y |")
    assert sc.vocabulary(video(tmp_path, script=table)) == ["timeout", "ledger"]
    assert sc.vocabulary(video(tmp_path, script=SCRIPT.replace("- **Vocabulary.**", "- **Words.**"))) == []


def test_each_sentence_gets_a_pause_role_and_the_first_use_of_a_term_a_speed_role(tmp_path):
    S = nr.Settings(video(tmp_path))
    R = nr.roles(S, sc.load(tmp_path))
    assert {k: r[0] for k, r in R.items()} == {
        "s1_01": "short", "s1_02": "long", "s1_03": "question", "s1_04": "long", "s1_05": "key",
        "s1_06": "short", "s1_07": "chapter", "s2_01": "short", "s2_02": "long", "s2_03": "short", "s2_04": "chapter"}
    # markers win; a term counts on its first use only, and s2_04's own marker beats it
    assert {k: r[1] for k, r in R.items() if r[1]} == {"s1_05": "key", "s2_01": "recap", "s2_02": "recap", "s2_04": "aside"}
    S2 = nr.Settings(video(tmp_path, script=SCRIPT.replace("[recap] ", "")))
    assert {k: r[1] for k, r in nr.roles(S2, sc.load(tmp_path)).items() if r[1]} == {
        "s1_05": "key", "s2_01": "term", "s2_02": "term", "s2_04": "aside"}


def test_a_key_paragraph_pauses_long_once_at_its_end(tmp_path):
    S = nr.Settings(video(tmp_path, script=SCRIPT.replace("[recap] ", "[key] ")))
    R = nr.roles(S, sc.load(tmp_path))
    assert (R["s2_01"], R["s2_02"]) == (("short", "key"), ("key", "key"))


def test_sentence_mode_lays_out_exact_role_pauses_after_any_hold(tmp_path):
    v = video(tmp_path, {"kokoro": {"paragraph": False}, "timing": {"chapter_hold": 2.0},
                         "holds": {"s1_01": 1.0}})
    S, chapters = nr.Settings(v), sc.load(v)
    t = nr.layout(S, chapters, {k: 1.0 for _, _, ss in chapters for k, _, _ in ss})
    st = starts(t)
    gap = lambda a, b: round(st[b][0] - st[a][1], 3)
    P = nr.PAUSES
    assert gap("s1_01", "s1_02") == 1.0 + P["short"]          # the hold, then the role's pause
    assert gap("s1_02", "s1_03") == P["long"]
    assert gap("s1_03", "s1_04") == P["question"]
    assert gap("s1_05", "s1_06") == P["key"]
    assert gap("s1_06", "s1_07") == P["short"]
    assert t["pauses"]["used"] == {"short": 4, "long": 3, "question": 1, "key": 1}
    # a chapter keeps its hold and gap, on the grid
    assert st["s2_01"][0] >= st["s1_07"][1] + 2.0 + nr.SEGMENT_GAP


def test_paragraph_mode_keeps_a_quicker_voice_gap_and_floors_the_long_ones(tmp_path):
    S, chapters = nr.Settings(video(tmp_path, {"timing": {"pause": {"short": 0.4, "long": 1.2}}})), sc.load(tmp_path)
    durs = {k: 1.0 for _, _, ss in chapters for k, _, _ in ss}
    st = starts(nr.layout(S, chapters, durs, gaps={"s1_01": 0.3, "s1_03": 0.5, "s1_06": 0.0, "s2_03": 0.7}))
    gap = lambda a, b: round(st[b][0] - st[a][1], 3)
    assert gap("s1_01", "s1_02") == 0.3                      # the voice's own, inside the short band
    assert gap("s1_06", "s1_07") == 0.0                      # a run-on stays run-on: no silence forced in
    assert gap("s2_03", "s2_04") == 0.4                      # a slow gap capped at short
    assert gap("s1_03", "s1_04") == nr.PAUSES["question"]    # at least the role's
    assert gap("s1_02", "s1_03") == 1.2                      # a tuned value, no voice gap across paragraphs


def test_timing_pause_is_validated(tmp_path):
    for bad in ({"pause": {"shrt": 0.3}}, {"pause": {"long": -1}}, {"pause": 2}, {"pause": {"key": True}}):
        with pytest.raises(SystemExit, match="timing.pause"):
            nr.Settings(video(tmp_path, {"timing": bad}))
    with pytest.raises(SystemExit, match="role_speed"):
        nr.Settings(video(tmp_path, {"kokoro": {"role_speed": {"key": 0.5}}}))


def test_role_speeds_apply_per_sentence_or_to_whole_chunks_only(tmp_path):
    v = video(tmp_path, {"kokoro": {"speed": 1.0}})
    S, chapters = nr.Settings(v), sc.load(v)
    R = nr.roles(S, chapters)
    # paragraph mode: s1_05 is a one-sentence paragraph; the recap paragraph is uniform; s2_04's
    # aside shares its paragraph with an unmarked sentence, so it keeps the paragraph's speed
    assert nr.assign_speeds(S, chapters, R) == {"s1_05": 0.9, "s2_01": 1.05, "s2_02": 1.05}
    S.paragraph = False
    assert nr.assign_speeds(S, chapters, R) == {"s1_05": 0.9, "s2_01": 1.05, "s2_02": 1.05, "s2_04": 1.05}
    S.engine = "elevenlabs"
    assert nr.assign_speeds(S, chapters, R) == {}


def test_the_kokoro_cache_key_includes_speed_and_keeps_old_keys(tmp_path):
    S = nr.Settings(video(tmp_path, {"kokoro": {"speed": 0.95}}))
    assert nr.kokoro_key(S, "Hi.") == nr.kokoro_key(S, "Hi.", 0.95) != nr.kokoro_key(S, "Hi.", 0.855)


def test_a_chunk_with_a_role_speed_is_synthesised_at_it(tmp_path):
    S, chapters = nr.Settings(video(tmp_path, {"kokoro": {"speed": 1.0}})), sc.load(tmp_path)
    nr.assign_speeds(S, chapters, nr.roles(S, chapters))
    calls = []

    def synth(full, prev, nxt, marked=None, speed=None):
        calls.append((full, speed))
        n = int(0.5 * nr.RATE)
        return (0.5 * np.sin(np.arange(n) * 0.3)).astype(np.float32), [(0, 0.0, 0.5)]

    chunks = [c for c in nr.all_chunks(S, chapters) if c[0][0][0] in ("s1_04", "s1_05")]
    nr.paragraph_clips(S, synth, chunks)
    assert calls == [("A timeout says nothing about the work.", 0.9)]
    # and plan() looks for it under that speed's key
    _, _, todo = nr.plan(tmp_path)
    assert any(c[0][0] == "s1_05" for c, _ in todo)


def test_sentence_mode_reads_its_cache_under_the_sentence_speed(tmp_path):
    S, chapters = nr.Settings(video(tmp_path, {"kokoro": {"paragraph": False, "speed": 1.0}})), sc.load(tmp_path)
    nr.assign_speeds(S, chapters, nr.roles(S, chapters))
    cache = tmp_path / ".cache" / "narration"
    cache.mkdir(parents=True)
    key = nr.kokoro_key(S, "sentence:A timeout says nothing about the work.", 0.9)
    np.save(cache / f"{key}.npy", np.ones(10, dtype=np.float32))
    (cache / f"{key}.json").write_text(json.dumps("ə tˈIməwt"))
    clips, phonemes = nr.sentence_clips(S, [("s1_05", "A timeout says nothing about the work.")])
    assert len(clips["s1_05"]) == 10 and phonemes["s1_05"] == "ə tˈIməwt"


def test_an_estimate_lays_out_role_pauses_and_role_speeds(tmp_path, capsys):
    v = video(tmp_path, {"kokoro": {"paragraph": False, "speed": 1.0}})
    t = nr.narrate(v, estimate=True)
    st = starts(t)
    assert round(st["s1_04"][0] - st["s1_03"][1], 3) == nr.PAUSES["question"]
    wps = nr.PACE["kokoro"][0]
    assert abs((st["s1_05"][1] - st["s1_05"][0]) - 7 / (wps * 0.9)) < 0.01
    assert t["speeds"]["s1_05"] == 0.9
    out = capsys.readouterr().out
    assert "pauses by role: 4 short" in out and "estimated total" in out


def test_renarrating_over_a_flat_narration_says_the_timings_moved(tmp_path, capsys):
    v = video(tmp_path, {"timing": {"pause": False}})
    flat = nr.narrate(v, estimate=True)
    assert flat["pauses"] == "flat"
    (v / "narration.json").write_text("{}")
    capsys.readouterr()
    roles = nr.narrate(v, estimate=True)
    out = capsys.readouterr().out
    assert f"was {flat['total']:.1f}s" in out and "previous narration had flat pauses" in out
    assert roles["total"] > flat["total"]


def test_new_explainers_write_the_pause_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    v, _ = new.create("x", directory=tmp_path / "x")
    timing = json.loads((v / "narration.json").read_text())["timing"]
    assert timing["pause"] == nr.PAUSES and timing["chapter_hold"] == 2.0


# --- the delivery report ---------------------------------------------------------------------------

def narration(pauses, words_per_sentence=12, word=0.3):
    """Timings with one sentence between each pause in `pauses`, words back to back."""
    lines, t = [], 0.8
    for i, p in enumerate([*pauses, None]):
        ws = [{"w": "w", "start": round(t + k * word, 3), "end": round(t + (k + 1) * word, 3)} for k in range(words_per_sentence)]
        lines.append({"id": f"s1_{i + 1:02d}", "caption": "w " * words_per_sentence, "start": t, "end": ws[-1]["end"], "words": ws})
        t = ws[-1]["end"] + (p or 0)
    return {"segments": [{"lines": lines}]}


def test_a_fixed_beat_reads_flat_and_role_pauses_do_not():
    flat = delivery.measure(narration([0.5] * 60))
    assert flat["pause_median"] == 0.5 and flat["pauses_over_1_5"] == 0
    why = delivery.warnings(flat)
    assert any("pauses over 1.5s" in w for w in why) and any("one length" in w for w in why)
    roles = delivery.measure(narration([0.4, 0.4, 0.9, 0.4, 1.6, 0.4, 0.9, 2.0, 0.4, 0.9] * 6))
    assert roles["pauses_over_1_5"] == 12 and roles["pause_evenness"] > delivery.EVEN
    assert not [w for w in delivery.warnings(roles) if "pause" in w]


def test_the_rate_measures_match_their_definitions():
    m = delivery.measure(narration([1.0] * 4, words_per_sentence=10, word=0.25))
    # 50 words over 5 × 2.5 s of speech and 4 s of pauses
    assert m["words"] == 50 and m["seconds"] == 16.5
    assert m["speaking_wpm"] == 240.0 and m["overall_wpm"] == round(50 / 16.5 * 60, 1)
    assert m["pauses"] == 4 and m["pause_p90"] == 1.0 and m["per_minute"] == []


def test_a_long_stretch_without_a_long_pause_warns_even_when_the_rate_is_met():
    pauses = [1.6] * 40 + [0.4, 0.9] * 70
    m = delivery.measure(narration(pauses, words_per_sentence=8))
    assert m["long_pauses_per_min"] >= delivery.LONG_RATE
    assert m["longest_without_long_pause"]["seconds"] > delivery.STRETCH
    assert any(w.startswith("no pause over 1.5s") for w in delivery.warnings(m))


def test_an_even_rate_minute_to_minute_warns_only_past_three_minutes():
    steady = delivery.measure(narration([0.4, 1.6] * 50))
    assert steady["seconds"] > delivery.SPREAD_AFTER and steady["per_minute_spread"] < delivery.SPREAD_MIN
    assert any("minute to minute" in w for w in delivery.warnings(steady))
    short = delivery.measure(narration([0.4, 1.6] * 10))
    assert not any("minute to minute" in w for w in delivery.warnings(short))


def test_the_references_pass_the_thresholds():
    """Calibration: each reference explainer's own numbers clear every warning."""
    R = delivery.REFERENCE
    assert R["per_minute_spread"][0] > delivery.SPREAD_MIN
    assert R["pause_evenness"][0] > delivery.EVEN
    assert R["long_pauses_per_min"][0] >= delivery.LONG_RATE


def test_an_estimate_is_measured_from_its_sentences():
    t = {"segments": [{"lines": [{"caption": "one two three four", "start": 0.0, "end": 2.0},
                                  {"caption": "five six", "start": 3.0, "end": 4.0}]}]}
    m = delivery.measure(t)
    assert m["words"] == 6 and m["pauses"] == 1 and m["pause_median"] == 1.0


def test_the_animatic_report_carries_the_delivery_lines():
    m = delivery.measure(narration([0.5] * 60))
    report = {"seconds": 300, "chapters": [], "longest_unchanged": {"at": 0, "seconds": 3}, "unchanged_runs": [],
              "no_picture": [], "delivery": m}
    lines = animatic.describe(report)
    assert any(l.startswith("delivery: speaking") for l in lines) and any(l.startswith("warn delivery:") for l in lines)


# --- regressions from review -----------------------------------------------------------------------

def test_pause_false_is_the_old_behaviour_including_speed(tmp_path):
    """timing.pause false once kept role speeds, so a term's first use was slowed with no markup."""
    S, chapters = nr.Settings(video(tmp_path, {"timing": {"pause": False}})), sc.load(tmp_path)
    S.paragraph = False
    assert nr.assign_speeds(S, chapters, nr.roles(S, chapters)) == {}
    durs = nr.estimate_durations(S, chapters)
    wps = nr.PACE["kokoro"][0]
    assert all(abs(durs[k] - len(c.split()) / wps) < 1e-9 for _, _, ss in chapters for k, c, _ in ss)
    # a speed named in narration.json still applies
    S2 = nr.Settings(video(tmp_path, {"timing": {"pause": False}, "kokoro": {"paragraph": False, "role_speed": {"key": 0.9}}}))
    assert nr.assign_speeds(S2, chapters, nr.roles(S2, chapters)) == {"s1_05": 0.9}


def test_common_abbreviations_end_no_sentence():
    """"Dr. Smith" and "Rust vs. Go" were split, and the gap raised to a forced pause mid-phrase."""
    split = lambda t: [x[0] for x in sc.paragraph(t, 1, 0.5)]
    assert split("Ask Dr. Smith about it. Then go.") == ["Ask Dr. Smith about it.", "Then go."]
    assert split("Rust vs. Go is old. Mr. Lee, e.g. Ann, and i.e. This.") == ["Rust vs. Go is old.", "Mr. Lee, e.g. Ann, and i.e. This."]
    assert split("It ends. Next one.") == ["It ends.", "Next one."]


def test_the_reference_band_is_reachable_and_the_short_pause_counts_as_speech(tmp_path):
    """The pause median sat at 0.9 s against the references' 0.67-0.75: it is the paragraph end's."""
    lo, hi = delivery.REFERENCE["pause_median"]
    assert nr.PAUSES["short"] < delivery.PAUSE <= lo - 0.03 <= nr.PAUSES["long"] <= hi
    pauses = [nr.PAUSES[k] for k in ["short", "short", "long", "short", "long", "question", "short", "long"] * 8]
    m = delivery.measure(narration(pauses))
    assert lo <= m["pause_median"] <= hi


def test_the_evenness_warning_needs_a_long_video_and_hints_by_layout():
    short_flat = delivery.measure(narration([0.5] * 20))            # about 80 s
    assert short_flat["seconds"] < delivery.SPREAD_AFTER
    assert not any("one length" in w for w in delivery.warnings(short_flat))
    t = narration([0.7] * 60)
    flat = delivery.warnings(delivery.measure(t))
    roles = delivery.warnings(delivery.measure({**t, "pauses": {"short": 0.4, "used": {}}}))
    assert any("re-narrate" in w for w in flat if "one length" in w)
    assert [w for w in roles if "one length" in w] and not any("re-narrate" in w for w in roles)


def test_a_key_sentence_that_ends_a_chapter_gets_the_key_pause(tmp_path):
    """The chapter gap (1.2 s) won over [key]'s 2 s when chapter_hold was 0."""
    S, chapters = nr.Settings(video(tmp_path, script=SCRIPT.replace("And one more.", "And one more. [key]"))), sc.load(tmp_path)
    st = starts(nr.layout(S, chapters, {k: 1.0 for _, _, ss in chapters for k, _, _ in ss}))
    assert st["s2_01"][0] - st["s1_07"][1] >= nr.PAUSES["key"] - 1e-9
    plain = starts(nr.layout(nr.Settings(video(tmp_path)), sc.load(tmp_path), {k: 1.0 for _, _, ss in chapters for k, _, _ in ss}))
    assert plain["s2_01"][0] - plain["s1_07"][1] < nr.PAUSES["key"]


def test_narrate_prints_the_laid_out_pause_and_plurals(tmp_path, capsys):
    v = video(tmp_path, {"kokoro": {"paragraph": False, "speed": 1.0}})
    t = nr.narrate(v, estimate=True)
    out = capsys.readouterr().out
    st = starts(t)
    assert f"s1_03:" in out and f"then {st['s1_04'][0] - st['s1_03'][1]:.2f}s" in out
    assert "1 sentence slower" in out
