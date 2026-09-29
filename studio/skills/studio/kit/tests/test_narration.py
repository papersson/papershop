from studio_kit import narration
from studio_kit import timeline as tl
from test_render import make_video


def fake_synth(calls):
    def synth(sentences, voice):
        calls.append(list(sentences))
        return b"RIFF" + " ".join(sentences).encode(), [(i, i + 1.0) for i in range(len(sentences))]
    return synth


def test_second_pass_is_all_cache_hits(tmp_path):
    t = make_video(tmp_path)
    calls = []
    _, made = narration.synthesize(tmp_path, fake_synth(calls), t)
    assert made == 2 and len(calls) == 2
    out, made = narration.synthesize(tmp_path, fake_synth(calls), t)
    assert made == 0 and len(calls) == 2
    assert out[0][2] == [(0, 1.0)]


def test_editing_a_sentence_resynthesises_only_its_paragraph(tmp_path):
    t = make_video(tmp_path)
    narration.synthesize(tmp_path, fake_synth([]), t)
    t["tracks"]["narration"][1]["text"] = "Two, said differently."
    calls = []
    _, made = narration.synthesize(tmp_path, fake_synth(calls), t)
    assert made == 1 and calls == [["Two, said differently."]]


def test_a_voice_change_misses_every_paragraph(tmp_path):
    t = make_video(tmp_path)
    narration.synthesize(tmp_path, fake_synth([]), t)
    (tmp_path / "video.json").write_text('{"voice": {"engine": "kokoro", "voice": "af_heart", "speed": 0.9}}')
    assert all(not cached for _, _, cached in narration.plan(tmp_path, t))


def test_paragraphs_group_by_clip_and_paragraph_number():
    s = lambda i, clip, par: {"id": i, "clip": clip, "paragraph": par, "text": i}
    t = {"tracks": {"narration": [s("a", "s1", 0), s("b", "s1", 0), s("c", "s1", 1), s("d", "s2", 1)]}}
    assert [p["ids"] for p in narration.paragraphs(t)] == [["a", "b"], ["c"], ["d"]]
