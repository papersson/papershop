"""The recorded engine: a film narrated from takes someone read, matched to the script."""
import json
import subprocess

import pytest

from studio_kit import align, recorded
from studio_kit import narration as nr

np = pytest.importorskip("numpy")
sf = pytest.importorskip("soundfile")
pytest.importorskip("num2words")

from test_narration import video  # noqa: E402


def words(text, start=0.0, step=0.4):
    return [{"w": w, "start": start + i * step, "end": start + i * step + 0.3} for i, w in enumerate(text.split())]


def test_digits_and_spelled_numbers_meet():
    heard = words("charging the card takes two thousand seven hundred")
    pairs = recorded.match(["Charging", "the", "card", "takes", "2,700"], [w["w"] for w in heard])
    assert pairs[0] == 0 and pairs[3] == 3
    assert pairs[4] in (4, 5, 6, 7)


def test_a_restart_is_left_out_and_the_last_full_reading_wins():
    heard = words("a checkout page asks") + words("a checkout page asks the server to charge", start=4.0)
    script = "A checkout page asks the server to charge.".replace(".", "").split()
    pairs = recorded.drop_restarts(recorded.match(script, [w["w"] for w in heard]))
    assert pairs[0] == 4, "the first word comes from the second reading"
    assert sorted(pairs.values()) == list(range(4, 12))


def test_a_long_pause_between_sentences_is_not_a_restart():
    heard = words("it takes two hundred milliseconds") + words("charging the card takes longer", start=6.0)
    script = "It takes two hundred milliseconds charging the card takes longer".split()
    pairs = recorded.drop_restarts(recorded.match(script, [w["w"] for w in heard]))
    assert len(pairs) == len(script)


def test_words_not_heard_get_times_between_their_neighbours():
    heard = words("one two four")
    full = "One two three four."
    times = recorded.word_times(full, {0: 0, 1: 1, 3: 2}, heard)
    assert [c for c, _, _ in times] == [0, 4, 8, 14]
    assert heard[1]["end"] <= times[2][1] < times[2][2] <= heard[2]["start"]


def burst_take(path, spoken):
    """A take stand-in: a 0.3 s tone burst per word, 0.1 s apart, a 0.6 s pause after each sentence,
    with silence at both ends. Returns the words in order."""
    rate, pieces, said = 48_000, [np.zeros(int(0.8 * 48_000))], []
    for sentence in spoken:
        for w in sentence.split():
            t = np.arange(int(0.3 * rate)) / rate
            pieces += [(0.3 * np.sin(2 * np.pi * 300 * t)).astype(np.float32), np.zeros(int(0.1 * rate))]
            said.append(w)
        pieces.append(np.zeros(int(0.6 * rate)))
    pieces.append(np.zeros(int(0.8 * rate)))
    sf.write(path, np.concatenate(pieces).astype(np.float32), rate)
    return said


def fake_recogniser(said_by_take):
    """align.recognise for burst takes: each loud run of the cleaned take is the next word."""
    def recognise(path, model=None):
        audio, rate = sf.read(path, dtype="float32")
        hop = int(0.01 * rate)
        loud = [float(np.sqrt((audio[i:i + hop] ** 2).mean())) > 0.02 for i in range(0, len(audio) - hop, hop)]
        runs, start = [], None
        for i, on in enumerate(loud + [False]):
            if on and start is None:
                start = i
            elif not on and start is not None:
                if i - start >= 10:
                    runs.append((start * 0.01, i * 0.01))
                start = None
        said = next(s for s in said_by_take if len(s) == len(runs))
        return [{"w": w, "start": a, "end": b} for w, (a, b) in zip(said, runs)]
    return recognise


def test_a_film_narrates_from_one_take_per_chapter(tmp_path, monkeypatch):
    v = video(tmp_path, {"engine": "recorded"})
    (v / "audio" / "takes").mkdir(parents=True)
    s1 = burst_take(v / "audio" / "takes" / "s1.wav", ["A checkout page asks the server to charge",
                                                       "Then the network goes quiet", "Did the charge go through"])
    s2 = burst_take(v / "audio" / "takes" / "s2.wav", ["Send a key with every attempt"])
    monkeypatch.setattr(align, "recognise", fake_recogniser([s1, s2]))
    S = nr.Settings(v)
    chapters = nr.sc.load(v)
    chunks = nr.all_chunks(S, chapters)
    clips, gaps, _, words_by = nr.paragraph_clips(S, recorded.engine(S, chapters, chunks), chunks)
    assert S.rate == 48_000
    assert set(clips) == {"s1_01", "s1_02", "s1_03", "s2_01"}
    # s1_01 is 8 words of 0.4 s, less the last word's 0.1 s gap
    assert abs(len(clips["s1_01"]) / S.rate - 3.1) < 0.15, len(clips["s1_01"]) / S.rate
    assert 0.4 < gaps["s1_01"] < 0.8, "the reader's own pause between sentences"
    assert [w for w, _, _ in words_by["s2_01"]] == "Send a key with every attempt".split()


def test_a_missing_take_names_the_chapter_and_the_file(tmp_path):
    v = video(tmp_path, {"engine": "recorded"})
    S = nr.Settings(v)
    chapters = nr.sc.load(v)
    with pytest.raises(SystemExit, match=r"no take for chapters s1, s2: record each as audio/takes/<chapter id>\.wav"):
        recorded.engine(S, chapters, nr.all_chunks(S, chapters))
