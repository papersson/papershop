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


def test_long_sentence_splits_at_punctuation_near_the_middle():
    text = ("If a payment was charged and the reply was lost on its way back to the client, "
            "a retry without a key charges the customer a second time for the same order.")
    pieces = tl.split_phrases(text)
    assert len(pieces) == 2 and pieces[0].endswith("client,")
    assert all(len(p) <= tl.LINE_CHARS * tl.MAX_LINES for p in pieces)


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
    phrases = ["is longer", "Longer than", "MTBF", "naive", "naïve or", "caf", "café", "co-op's", "3.5 nodes", "the", "quorum.", "here", "absent", ""]
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


def test_captions_are_wrapped_for_every_format_and_lines_stay_the_16_9_ones():
    text = "After a few seconds with no reply the client gives up and marks it as a timeout"
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
