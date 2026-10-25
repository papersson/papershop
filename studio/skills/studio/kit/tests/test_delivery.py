"""Consistent narration, including compatibility with old role annotations."""
import json

import numpy as np
import pytest

from studio_kit import narration as nr, new, script as sc
from types import SimpleNamespace

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


@pytest.mark.parametrize("paragraph", [True, False])
def test_one_voice_and_speed_even_with_legacy_variation_settings(tmp_path, monkeypatch, paragraph):
    cfg = {"kokoro": {"voice": "af_heart", "speed": 0.95, "paragraph": paragraph,
                      "role_speed": {"key": 0.9, "term": 0.9, "recap": 1.05, "aside": 1.05}},
           "timing": {"pause": {"short": 0.4, "long": 0.7, "question": 1.6, "key": 2.0}}}
    S = nr.Settings(video(tmp_path, cfg))
    calls = []
    def pipeline(text, **kw):
        calls.append(kw)
        return [SimpleNamespace(graphemes=text, phonemes="test", tokens=[
            SimpleNamespace(text=text, whitespace="", start_ts=0.0, end_ts=0.5)],
            audio=SimpleNamespace(numpy=lambda: np.ones(nr.RATE // 2, dtype=np.float32)))]
    monkeypatch.setattr(nr, "kokoro_pipeline", lambda: pipeline)
    chapters = sc.load(tmp_path)
    if paragraph:
        chunks = nr.all_chunks(S, chapters)
        nr.paragraph_clips(S, nr.kokoro_engine(S), [c for c in chunks if len(c[0]) == 1])
    else:
        nr.sentence_clips(S, [(sid, text) for _, _, ss in chapters for sid, text, _ in ss])
    assert calls and all(c["voice"] == "af_heart" and c["speed"] == 0.95 for c in calls)


def test_legacy_settings_and_markers_do_not_change_estimates_or_pauses(tmp_path, capsys):
    cfg = {"kokoro": {"speed": 0.95, "role_speed": {"key": 0.8}},
           "timing": {"pause": {"key": 2.0, "question": 1.6}}}
    v = video(tmp_path, cfg, SCRIPT.replace("Nobody knows.", "Nobody knows. [predict 3]"))
    legacy = nr.narrate(v, estimate=True)
    plain_script = (v / "SCRIPT.md").read_text()
    for marker in ("[key]", "[aside]", "[recap]"):
        plain_script = plain_script.replace(marker, "")
    video(tmp_path, {"kokoro": {"speed": 0.95}}, plain_script)
    plain = nr.narrate(v, estimate=True)
    assert legacy == plain and "speeds" not in plain and "pauses" not in plain
    st = starts(plain)
    assert st["s1_04"][0] - st["s1_03"][1] == pytest.approx(nr.SENTENCE_GAP)
    assert st["s1_05"][0] - st["s1_04"][1] == pytest.approx(3 + nr.PARAGRAPH_GAP)
    assert "warn delivery" not in capsys.readouterr().out


def test_natural_paragraph_gaps_are_preserved(tmp_path):
    S = nr.Settings(video(tmp_path))
    chapters = sc.load(tmp_path)
    t = nr.layout(S, chapters, {k: 1.0 for _, _, ss in chapters for k, _, _ in ss},
                  gaps={"s1_01": 0.12, "s1_03": 0.8})
    st = starts(t)
    assert st["s1_02"][0] - st["s1_01"][1] == pytest.approx(0.12)
    assert st["s1_04"][0] - st["s1_03"][1] == pytest.approx(0.8)
    assert st["s1_06"][0] - st["s1_05"][1] == pytest.approx(nr.PARAGRAPH_GAP)


def test_sentence_cache_reuses_the_constant_speed(tmp_path, monkeypatch):
    S = nr.Settings(video(tmp_path, {"kokoro": {"role_speed": {"key": 0.9}}}))
    cache = tmp_path / ".cache/narration"
    cache.mkdir(parents=True)
    key = nr.kokoro_key(S, "sentence:A timeout says nothing about the work.")
    np.save(cache / f"{key}.npy", np.ones(10, dtype=np.float32))
    (cache / f"{key}.json").write_text(json.dumps("cached phonemes"))
    monkeypatch.setattr(nr, "kokoro_pipeline", lambda: pytest.fail("cache hit must not load the model"))
    clips, phonemes = nr.sentence_clips(S, [("s1_05", "A timeout says nothing about the work.")])
    assert len(clips["s1_05"]) == 10 and phonemes["s1_05"] == "cached phonemes"


def test_new_explainers_keep_chapter_holds_without_variation(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    v, _ = new.create("x", directory=tmp_path / "x")
    cfg = json.loads((v / "narration.json").read_text())
    assert cfg["timing"]["chapter_hold"] == 2.0 and cfg["kokoro"]["speed"] == 0.95
    assert "pause" not in cfg["timing"] and "role_speed" not in cfg["kokoro"]


def test_markers_give_roles_to_a_sentence_or_a_whole_paragraph(tmp_path):
    sents = {s.id: s for c in sc.read(video(tmp_path)) for s in c.sentences}
    assert sents["s1_05"].role == "key" and sents["s1_05"].text == "A timeout says nothing about the work."
    assert [sents[k].role for k in ("s2_01", "s2_02", "s2_03", "s2_04")] == ["recap", "recap", None, "aside"]
    assert sents["s1_01"].role is None
    # one hold and one role on a sentence is fine; two of either is not
    assert sc.paragraph("Think. [predict 2] [key]", 1, 0.5) == [("Think.", 2.0, True, "key", False)]


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


def test_common_abbreviations_end_no_sentence():
    """"Dr. Smith" and "Rust vs. Go" were split, and the gap raised to a forced pause mid-phrase."""
    split = lambda t: [x[0] for x in sc.paragraph(t, 1, 0.5)]
    assert split("Ask Dr. Smith about it. Then go.") == ["Ask Dr. Smith about it.", "Then go."]
    assert split("Rust vs. Go is old. Mr. Lee, e.g. Ann, and i.e. This.") == ["Rust vs. Go is old.", "Mr. Lee, e.g. Ann, and i.e. This."]
    assert split("It ends. Next one.") == ["It ends.", "Next one."]
