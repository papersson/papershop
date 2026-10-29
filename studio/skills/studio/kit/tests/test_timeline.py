import json
import shutil
import subprocess

import pytest
from studio_kit import timeline as tl
from studio_kit.env import engine_dir


def sentence(caption, start, end, clip="s1"):
    return {"id": "x", "clip": clip, "text": caption, "caption": caption, "paragraph": 0,
            "start": start, "end": end, "words": []}


def test_wrap_keeps_lines_short_and_never_ends_on_an_article():
    text = "After a few seconds with no reply the client gives up and marks the payment as a timeout"
    lines = tl.wrap(text)
    assert all(len(l) <= tl.LINE_CHARS for l in lines)
    assert all(l.split()[-1].lower() not in tl.NO_BREAK_AFTER for l in lines)
    assert " ".join(lines) == text


LONG = ("If a payment was charged and the reply was lost on its way back to the client, "
        "a retry without a key charges the customer a second time for the same order.")


def test_long_sentence_splits_at_punctuation_near_the_middle():
    pieces = tl.split_phrases(LONG, [42])
    assert len(pieces) == 2 and pieces[0].endswith("client,")
    assert all(len(p) <= tl.LINE_CHARS * tl.MAX_LINES for p in pieces)


def test_wrapped_lines_are_balanced_not_greedy():
    """A greedy fill left "for a while." alone under a full line."""
    text = "Then the network goes quiet and nobody knows for a while."
    assert tl.wrap(text, 42) == ["Then the network goes quiet", "and nobody knows for a while."]
    assert tl.wrap("Did it go?", 26) == ["Did it go?"]


def test_a_line_never_ends_on_a_short_word_or_stands_alone_when_it_can_be_helped():
    assert tl.wrap("Send one key with every attempt to the server", 26) == ["Send one key with every", "attempt to the server"]
    assert tl.wrap("Then a retry", 8) == ["Then", "a retry"]          # one word alone, or "a" at a line's end
    assert tl.wrap("Charge it", 4) == ["Charge", "it"]                # unavoidable


def test_a_word_longer_than_the_line_gets_a_line_of_its_own():
    word = "idempotency-key-with-a-long-name"
    assert tl.wrap(word, 26) == [word] and tl.split_phrases(word, [26]) == [word]
    assert tl.wrap(f"Send the {word} again", 26) == ["Send the", word, "again"]


@pytest.mark.parametrize("fmt,width", [("16:9", 42), ("9:16", 26), ("1:1", 34)])
@pytest.mark.parametrize("text", [LONG, "Did it go?", "A retry can charge twice.",
                                  "After a few seconds with no reply the client gives up and marks the payment as a timeout",
                                  "So the client waits, and waits, and then it sends the very same request again with a fresh connection."])
def test_every_chunk_fits_two_balanced_lines_in_every_format(fmt, text, width):
    chunks = tl.chunk_captions([sentence(text, 0.0, 8.0)])
    assert " ".join(" ".join(c["lines"]) for c in chunks) == text
    for c in chunks:
        lines = tl.caption_lines(c, fmt)
        assert 1 <= len(lines) <= tl.MAX_LINES and all(len(l) <= width for l in lines)
        assert all(l.split()[-1].lower() not in tl.NO_BREAK_AFTER for l in lines)       # the chunk's last line too
        if len(lines) == 2:
            assert len(lines[0].split()) > 1 and len(lines[1].split()) > 1
            assert abs(len(lines[0]) - len(lines[1])) <= width // 2


def test_phrases_map_onto_word_timings_in_order():
    words = [{"w": w, "start": i * 0.3, "end": i * 0.3 + 0.25} for i, w in enumerate(LONG.split())]
    s = {**sentence(LONG, 0.0, len(words) * 0.3), "words": words}
    chunks = tl.chunk_captions([s])
    assert len(chunks) > 2
    at = 0
    for c in chunks:
        assert c["start"] == round(words[at]["start"], 3)
        at += len(" ".join(c["lines"]).split())
    assert at == len(words)


def test_captions_hold_at_least_min_show_and_leave_a_two_frame_gap():
    narr = [sentence("Did it go?", 1.0, 1.5), sentence("Nobody knows.", 1.9, 3.0)]
    c = tl.chunk_captions(narr, fps=30)
    assert c[0]["end"] == round(1.9 - 2 / 30, 3)      # would be 1.0 + MIN_SHOW, capped by the gap
    assert c[1]["end"] - c[1]["start"] >= tl.MIN_SHOW


def test_frames_round_absolute_times_so_clips_tile_the_video():
    t = {"fps": 30, "tracks": {"scene": [{"id": "a", "start": 0.0, "end": 26.184},
                                         {"id": "b", "start": 26.184, "end": 74.475}]}}
    a0, an = tl.frames(t, "a")
    b0, bn = tl.frames(t, "b")
    assert a0 + an == b0 and b0 + bn == round(74.475 * 30)


def test_attach_words_matches_and_interpolates_missed_words():
    t = {"tracks": {"narration": [sentence("Then the network goes quiet.", 5.0, 7.0)]}}
    heard = [{"w": "Then", "start": 5.0, "end": 5.2}, {"w": "the", "start": 5.2, "end": 5.3},
             {"w": "goes", "start": 5.9, "end": 6.2}, {"w": "quiet.", "start": 6.2, "end": 6.8}]
    matched, total = tl.attach_words(t, heard)
    words = t["tracks"]["narration"][0]["words"]
    assert (matched, total) == (4, 5)
    assert words[2]["w"] == "network" and 5.3 <= words[2]["start"] < words[2]["end"] <= 5.9


def test_captions_use_word_times_when_present():
    s = sentence("Then the network goes quiet.", 5.0, 7.0)
    s["words"] = [{"w": w, "start": 5.1 + i * 0.3, "end": 5.3 + i * 0.3}
                  for i, w in enumerate(s["caption"].split())]
    (c,) = tl.chunk_captions([s])
    assert c["start"] == 5.1 and c["end"] == round(5.3 + 4 * 0.3 + tl.TAIL, 3)


def test_word_times_are_bounded_by_their_sentence():
    t = {"tracks": {"narration": [sentence("A checkout page.", 0.8, 2.0)]}}
    heard = [{"w": "A", "start": 0.0, "end": 0.9}, {"w": "checkout", "start": 0.9, "end": 1.4},
             {"w": "page.", "start": 1.4, "end": 3.5}]
    tl.attach_words(t, heard)
    words = t["tracks"]["narration"][0]["words"]
    assert words[0]["start"] == 0.6 and words[-1]["end"] == 2.2


def test_frames_round_halves_up_like_the_engine():
    t = {"fps": 30, "tracks": {"scene": [{"id": "a", "start": 0.0, "end": 14.55},
                                         {"id": "b", "start": 14.55, "end": 23.557}]}}
    assert tl.half_up(436.5) == 437 and tl.half_up(2.5) == 3 and tl.half_up(2.4) == 2
    assert tl.frames(t, "a") == (0, 437) and tl.frames(t, "b") == (437, 270)


def test_phrase_start_finds_spoken_words_and_falls_back_to_the_caption():
    from studio_kit.timeline import phrase_start
    entry = {"id": "s1_02", "start": 10.0, "end": 14.0,
             "caption": "The MTTR is longer than the MTBF.",
             "text": "The M T T R is longer than the M T B F.",
             "words": [{"w": w, "start": 10.0 + 0.3 * i, "end": 10.2 + 0.3 * i}
                       for i, w in enumerate("The M T T R is longer than the M T B F.".split())]}
    # matched in the spoken words, punctuation and case ignored
    assert phrase_start(entry, "is longer") == pytest.approx(10.0 + 0.3 * 5)
    assert phrase_start(entry, "Longer than") == pytest.approx(10.0 + 0.3 * 6)
    # a spoken rule rewrote "MTBF": its place in the caption, proportionally
    k = entry["caption"].find("MTBF")
    assert phrase_start(entry, "MTBF") == pytest.approx(10.0 + k / len(entry["caption"]) * 4.0)
    with pytest.raises(KeyError):
        phrase_start(entry, "quorum")


PARITY = """
import { frameOf, phraseStart } from %s
const { entries, phrases, times } = JSON.parse(process.argv[2])
const tryStart = (e, p) => { try { return phraseStart(e, p) } catch { return null } }
console.log(JSON.stringify({ starts: entries.map(e => phrases.map(p => tryStart(e, p))), frames: times.map(([t, fps]) => frameOf(t, fps)) }))
"""


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_the_engines_shared_phrase_start_and_frame_rounding_agree_with_the_kits(tmp_path):
    """engines/shared/timing.js is what every engine runs; the kit's twins must give the same times."""
    spoken = "The M T T R is longer than the M T B F, naïve or not, at the café."
    words = [{"w": w, "start": round(10.0 + 0.3 * i, 3), "end": round(10.2 + 0.3 * i, 3)} for i, w in enumerate(spoken.split())]
    entries = [{"id": "s1_02", "start": 10.0, "end": 14.0, "caption": "The MTTR is longer than the MTBF, naïve or not, at the café.",
                "text": spoken, "words": words},
               {"id": "s1_03", "start": 3.25, "end": 7.9, "caption": "A co-op's 3.5 nodes: the café, the quorum.", "words": []},
               {"id": "s1_04", "start": 1.0, "end": 2.0, "text": "No caption, no words here."}]
    phrases = ["is longer", "Longer than", "MTBF", "naive", "naïve or", "caf", "café", "co-op's", "3.5 nodes", "the", "quorum.", "here", "absent", "",
               "THE CAFÉ", "the  quorum", "Nodes", "mttr Is"]       # case and spacing, with and without spoken words
    times = [[14.55, 30], [23.557, 30], [0.0, 30], [1 / 60, 30], [74.475, 30], [2.5, 1], [12.345, 25], [436.5 / 30, 30]]
    script = tmp_path / "parity.mjs"
    script.write_text(PARITY % json.dumps((engine_dir("shared") / "timing.js").as_uri()))
    run = subprocess.run(["node", str(script), json.dumps({"entries": entries, "phrases": phrases, "times": times})],
                         capture_output=True, text=True, check=True)
    js = json.loads(run.stdout)

    def start(e, p):
        try:
            return tl.phrase_start(e, p)
        except KeyError:
            return None
    assert js["starts"] == [[start(e, p) for p in phrases] for e in entries]
    assert js["frames"] == [tl.half_up(t * fps) for t, fps in times]
    assert any(x is None for row in js["starts"] for x in row) and any(x is not None for x in js["starts"][1])


WORD_PARITY = """
import { wordStart } from %s
const { entries, n } = JSON.parse(process.argv[2])
const tryStart = (e, i) => { try { return wordStart(e, i) } catch (err) { return String(err.message) } }
console.log(JSON.stringify(entries.map(e => [...Array(n).keys()].map(i => tryStart(e, i)))))
"""


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_word_i_means_the_same_caption_word_in_a_scene_and_in_a_cue(tmp_path):
    """A scene's c.word(id, i) and a cue's {"word": i} once counted different words: the scene the
    recognised ones, the cue the caption's. Both now take caption word i (_word_times)."""
    aligned = "Every checkout logs how long it took."
    rewritten = "The HTTP call failed."           # a spoken rule read HTTP as four letters: words don't match
    entries = [
        {"id": "s3_02", "start": 2.0, "end": 5.0, "caption": aligned,
         "words": [{"w": w.strip("."), "start": round(2.0 + 0.4 * i, 3), "end": round(2.3 + 0.4 * i, 3)} for i, w in enumerate(aligned.split())]},
        {"id": "s3_03", "start": 6.0, "end": 8.0, "caption": rewritten,
         "words": [{"w": w, "start": round(6.0 + 0.25 * i, 3), "end": round(6.2 + 0.25 * i, 3)} for i, w in enumerate("The H T T P call failed.".split())]},
        {"id": "s3_04", "start": 9.0, "end": 10.0, "caption": "Except it didn't.", "words": []}]
    n = 8
    script = tmp_path / "words.mjs"
    script.write_text(WORD_PARITY % json.dumps((engine_dir("shared") / "timing.js").as_uri()))
    run = subprocess.run(["node", str(script), json.dumps({"entries": entries, "n": n})], capture_output=True, text=True, check=True)
    t = {"fps": 1000, "tracks": {"narration": entries}}

    def kit(e, i):
        times = tl._word_times(e, e["caption"].split())
        return times[i][0] if i < len(times) else f"{e['id']} has {len(times)} words, no word {i}"
    assert json.loads(run.stdout) == [[kit(e, i) for i in range(n)] for e in entries]
    assert json.loads(run.stdout)[1][3] == pytest.approx(6.0 + 2.0 * len("The HTTP call ") / len(rewritten))   # "failed", not "T"
    assert tl.event_time(t, {"sentence": "s3_02", "word": 3}) == pytest.approx(3.2)


def test_captions_are_wrapped_for_every_format_and_lines_stay_the_16_9_ones():
    text = "After a few seconds the client gives up on it"
    (c,) = tl.chunk_captions([sentence(text, 0.0, 4.0)])
    assert c["lines"] == tl.wrap(text, 42)
    assert set(c["wrapped"]) == {"9:16", "1:1"}
    assert c["wrapped"]["9:16"] == tl.wrap(text, 26) and c["wrapped"]["1:1"] == tl.wrap(text, 34)
    assert tl.caption_lines(c, "9:16") == c["wrapped"]["9:16"] and tl.caption_lines(c) == c["lines"]
    with pytest.raises(SystemExit, match="4:5"):
        tl.caption_lines(c, "4:5")


def test_line_widths_come_from_the_layout_each_format_renders(tmp_path):
    (tmp_path / "layout.json").write_text(json.dumps({**tl.DEFAULT_LAYOUT, "band": {"height": 160, "style": "opaque", "chars": 50},
                                                      "formats": {"4:5": {"width": 1080, "height": 1350, "band": {"height": 260, "chars": 30}}}}))
    assert tl.caption_widths(tmp_path) == {"16:9": 50, "9:16": 26, "1:1": 34, "4:5": 30}


def test_event_time_reads_aligned_words_and_parts_of_words():
    words = [{"w": w, "start": round(2.0 + 0.4 * i, 3), "end": round(2.3 + 0.4 * i, 3)} for i, w in enumerate("The crown drops to the floor.".split())]
    t = {"fps": 30, "tracks": {"narration": [
        {"id": "s1_01", "start": 2.0, "end": 4.4, "caption": "The crown drops to the floor.", "words": words},
        {"id": "s1_02", "start": 5.0, "end": 7.0, "caption": "A co-op's café, at 3.5 nodes.", "words": []}]}}
    on_grid = lambda x: round(tl.half_up(x * 30) / 30, 6)
    assert tl.event_time(t, {"sentence": "s1_01", "word": 2}) == on_grid(2.8)
    assert tl.event_time(t, {"phrase": "the floor", "word": 1, "offset": -0.05}) == on_grid(4.0 - 0.05)
    assert tl.event_time(t, {"phrase": "drops"}) == on_grid(2.8) == tl.event_time(t, {"sentence": "s1_01", "at": "phrase", "phrase": "drops"})
    assert tl.event_time(t, {"sentence": "s1_01", "at": "end", "offset": 0.017}) == on_grid(4.417) == round(133 / 30, 6)
    cap = t["tracks"]["narration"][1]["caption"]                 # no word timings: the caption's share of the time
    assert tl.event_time(t, {"phrase": "caf", "word": 1}) == on_grid(5.0 + 2.0 * cap.index("at") / len(cap))
    assert tl.event_time(t, 1.25) == round(38 / 30, 6)
    with pytest.raises(ValueError, match="no sentence says 'crowns'"):
        tl.event_time(t, {"sentence": "s1_01", "phrase": "crowns"})


def test_the_timeline_command_lists_the_events(tmp_path, capsys):
    from types import SimpleNamespace
    narration = [{"id": "s1_01", "clip": "s1", "text": "Go.", "caption": "Go.", "paragraph": 0, "start": 0.5, "end": 1.5}]
    (tmp_path / "video.json").write_text(json.dumps({"title": "T", "engine": "live"}))
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "timings.json").write_text(json.dumps({"total": 3.0, "timing": "estimate", "segments": [
        {"id": "s1", "title": "One", "start": 0.0, "end": 3.0,
         "lines": [{**narration[0], "pause": {"seconds": 1.0, "start": 1.5, "end": 2.5}}]}]}))
    (tmp_path / "cues.json").write_text(json.dumps({"go": {"sentence": "s1_01", "offset": 0.04}, "late": 2.71}))
    tl.main(SimpleNamespace(video=tmp_path, events=True))
    out = capsys.readouterr().out.splitlines()
    assert "3 events" in out[1]
    assert out[2].split() == ["0.533", "s", "frame", "16", "s1", "0.533", "s", "go", "s1_01", "start", "+0.04", "s"]
    assert out[3].split()[-3:] == ["reveal:s1_01", "hold", "end"] and out[4].split()[:4] == ["2.700", "s", "frame", "81"]


def test_a_phrase_in_another_case_or_spacing_resolves_on_an_estimate():
    """An estimate has no spoken words; the caption's words, compared as the spoken ones are, give the
    time (a phrase in another case once fell through to an exact search and crashed the build)."""
    cap = "The ball hits the floor, then hits the floor again."
    t = {"fps": 30, "tracks": {"narration": [{"id": "s1_01", "start": 1.0, "end": 4.0, "caption": cap, "words": []}]}}
    on_grid = lambda x: round(tl.half_up(x * 30) / 30, 6)
    ball = on_grid(1.0 + 3.0 * cap.index("ball") / len(cap))
    assert tl.event_time(t, {"sentence": "s1_01", "phrase": "Ball hits the floor"}) == ball == tl.event_time(t, {"sentence": "s1_01", "phrase": "ball  HITS the floor"})
    with pytest.raises(ValueError, match="said 2 times"):           # which "hits the floor"? (it once took the first)
        tl.event_time(t, {"sentence": "s1_01", "phrase": "Hits the floor"})
    assert tl.event_time(t, {"sentence": "s1_01", "phrase": "Floor again"}) == on_grid(1.0 + 3.0 * cap.index("floor again") / len(cap))
    assert tl.phrase_start(t["tracks"]["narration"][0], "HITS") == 1.0 + 3.0 * cap.index("hits") / len(cap)


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_a_switch_at_a_cue_happens_on_the_cues_own_frame(tmp_path):
    """Every engine's t is its clip frame / fps and its clip start the first frame / fps; cue() must give
    the cue's clip frame / fps exactly, or `t >= cue('x')` comes a frame late (it did 354 times in 897)."""
    script = tmp_path / "cue.mjs"
    script.write_text(f"import {{ clipTimes, frameOf }} from {json.dumps((engine_dir('shared') / 'timing.js').as_uri())}\n" """
const fps = 30, cues = JSON.parse(process.argv[2]), late = []
for (const clipStart of [0, 3.217, 10.5, 61.0333]) {
  const first = frameOf(clipStart, fps)
  for (const [f, cue] of cues) {
    if (f <= first) continue
    const c = clipTimes({ fps, tracks: { narration: [] }, cues: { x: cue } }, 'c', first / fps)
    const lf = f - first
    if (!(lf / fps >= c.cue('x')) || (lf - 1) / fps >= c.cue('x')) late.push([clipStart, f])
  }
}
console.log(JSON.stringify(late))
""")
    cues = [[f, tl.frame_time(f / 30, 30)] for f in range(1, 2400)]
    late = json.loads(subprocess.run(["node", str(script), json.dumps(cues)], capture_output=True, text=True, check=True).stdout)
    assert late == []


def test_a_phrase_said_twice_in_its_sentence_stops_the_build_instead_of_taking_the_first():
    words = [{"w": w.strip(","), "start": round(1.0 + 0.3 * i, 3), "end": round(1.2 + 0.3 * i, 3)}
             for i, w in enumerate("The floor, then the floor again.".split())]
    t = {"fps": 30, "timing": "narrated", "tracks": {"narration": [
        {"id": "s1_01", "start": 1.0, "end": 3.0, "caption": "The floor, then the floor again.", "words": words}]}}
    with pytest.raises(ValueError, match="'the floor' is said 2 times in s1_01: lengthen the phrase"):
        tl.event_time(t, {"sentence": "s1_01", "phrase": "the floor"})
    assert tl.event_time(t, {"sentence": "s1_01", "phrase": "the floor again"}) == round(tl.half_up(1.9 * 30) / 30, 6)


def test_an_anchor_the_recogniser_did_not_hear_is_marked_as_an_estimate(tmp_path, capsys):
    """Whisper hears "VeryBadRoll" as "very bad roll": the phrase falls back to the caption's share of
    the sentence, a guess the build now names instead of using silently."""
    caption = "We will throw a VeryBadRoll error."
    heard = [{"w": w, "start": round(2.0 + 0.3 * i, 3), "end": round(2.2 + 0.3 * i, 3)}
             for i, w in enumerate("We will throw a very bad roll error.".split())]
    t = {"fps": 30, "timing": "narrated", "tracks": {"narration": [
        {"id": "s1_01", "start": 2.0, "end": 4.7, "caption": caption, "words": heard}]}}
    assert tl.estimated(t, {"sentence": "s1_01", "phrase": "VeryBadRoll"})
    assert not tl.estimated(t, {"sentence": "s1_01", "phrase": "throw a"})
    assert tl.estimated(t, {"sentence": "s1_01", "word": 2})              # recognised words don't match the caption's
    assert not tl.estimated(t, {"sentence": "s1_01", "at": "end"}) and not tl.estimated(t, 3.0)
    assert not tl.estimated({**t, "timing": "estimate"}, {"sentence": "s1_01", "phrase": "VeryBadRoll"})

    from types import SimpleNamespace
    (tmp_path / "video.json").write_text(json.dumps({"title": "T", "engine": "live"}))
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "timings.json").write_text(json.dumps({"total": 6.0, "timing": "narrated", "segments": [
        {"id": "s1", "title": "One", "start": 0.0, "end": 6.0,
         "lines": [{"id": "s1_01", "text": caption, "caption": caption, "paragraph": 0, "start": 2.0, "end": 4.7, "words": heard}]}]}))
    (tmp_path / "cues.json").write_text(json.dumps({"roll": {"sentence": "s1_01", "phrase": "VeryBadRoll"},
                                                     "throw": {"sentence": "s1_01", "phrase": "throw a"}}))
    tl.main(SimpleNamespace(video=tmp_path, events=True))
    out = capsys.readouterr().out
    assert "warn: 'roll' is timed by estimate" in out
    rows = {line.split()[7]: line for line in out.splitlines() if line.startswith("  ")}
    assert rows["roll"].endswith(" ~") and not rows["throw"].endswith(" ~")


def test_the_moments_scene_code_reads_from_the_narration_are_listed_beside_the_cues(tmp_path, capsys):
    from types import SimpleNamespace
    caption = "Our worst checkout took eight point eight seconds."
    heard = [{"w": w.strip("."), "start": round(1.0 + 0.3 * i, 3), "end": round(1.2 + 0.3 * i, 3)} for i, w in enumerate(caption.split())]
    (tmp_path / "video.json").write_text(json.dumps({"title": "T", "engine": "live"}))
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "timings.json").write_text(json.dumps({"total": 6.0, "timing": "narrated", "segments": [
        {"id": "s3", "title": "Three", "start": 0.0, "end": 6.0,
         "lines": [{"id": "s3_03", "text": caption, "caption": caption, "paragraph": 0, "start": 1.0, "end": 3.7, "words": heard}]}]}))
    (tmp_path / "scenes").mkdir()
    (tmp_path / "scenes" / "s3.js").write_text(
        "export default function draw(c) {\n"
        "  const a = c.P(c.phrase('03', 'eight point eight'), .35)\n"
        "  const b = c.word(\"s3_03\", 2) + c.phrase('03', 'nine')\n}\n")
    rows = tl.scene_anchors(tmp_path, tl.build(tmp_path, quiet=True))
    assert [(r["kind"], r.get("phrase", r.get("word")), r["time"], r["problem"]) for r in rows] == [
        ("word", 2, 1.6, None), ("phrase", "eight point eight", 2.2, None), ("phrase", "nine", None, "s3_03: no phrase 'nine'")]
    tl.main(SimpleNamespace(video=tmp_path, events=True))
    out = capsys.readouterr().out
    assert "3 more in scene code" in out and "s3_03 at 'eight point eight'" in out and "(s3_03: no phrase 'nine')" in out
