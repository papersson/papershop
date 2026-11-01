"""Film grammar in the live engine: focus on what is named, shots (wide, close, back) with labels that
keep their size, chapter joins drawn in the outgoing chapter's quiet tail and rendered as their own
piece, and callbacks that draw an earlier chapter's own frame."""
import json

from studio_kit import keys
from studio_kit import timeline as tl
from studio_kit.engine import Engine

from test_live_engine import needs_engine, rgba


def two_chapters(tmp_path, s1, s2):
    (tmp_path / "scenes").mkdir(exist_ok=True)
    (tmp_path / "scenes" / "s1.js").write_text(s1)
    (tmp_path / "scenes" / "s2.js").write_text(s2)
    narration = [{"id": "s1_01", "clip": "s1", "text": "Checkout calls payment.", "caption": "Checkout calls payment.", "paragraph": 0,
                  "start": 0.2, "end": 1.4, "words": [{"w": "Checkout", "start": 0.2, "end": 0.6}, {"w": "calls", "start": 0.6, "end": 0.9},
                                                       {"w": "payment.", "start": 0.9, "end": 1.4}]},
                 {"id": "s2_01", "clip": "s2", "text": "Inside payment.", "caption": "Inside payment.", "paragraph": 0,
                  "start": 2.3, "end": 3.0, "words": [{"w": "Inside", "start": 2.3, "end": 2.6}, {"w": "payment.", "start": 2.6, "end": 3.0}]}]
    t = {"version": 1, "fps": 30, "duration": 3.5, "cues": {},
         "tracks": {"scene": [{"id": "s1", "engine": "live", "title": "One", "start": 0.0, "end": 2.0},
                              {"id": "s2", "engine": "live", "title": "Two", "start": 2.0, "end": 3.5}],
                    "narration": narration, "captions": tl.chunk_captions(narration), "audio": []}}
    (tmp_path / "timeline.json").write_text(json.dumps(t))
    (tmp_path / "video.json").write_text(json.dumps({"title": "t", "engine": "live"}))
    return t


ROAD = """
export default function draw(c) {
  const { S } = c
  S.rect('checkout', 300, 300, 300, 200, { fill: '#1C242E', stroke: '#C9D3DD', box: 'checkout' })
  S.rect('payment', 1200, 300, 300, 200, { fill: '#1C242E', stroke: '#C9D3DD', box: 'payment' })
  S.text('name-payment', 1350, 260, 'payment', { size: 40, anchor: 'middle', keep: true })
  SHOTS
}
"""
INSIDE = "export default function draw(c) { c.S.rect('frame', 200, 100, 1520, 700, { fill: '#8FD3FF', box: 'payment' }) }\n"


def test_a_join_is_its_own_piece_so_editing_the_next_chapter_re_renders_only_the_join(tmp_path):
    t = two_chapters(tmp_path, ROAD.replace("SHOTS", ""), INSIDE)
    p = keys.parts(tmp_path, t, "s1", "draft")
    assert [x["id"] for x in p] == ["s1", "s1~join"] and sum(x["frames"] for x in p) == 60
    assert p[1]["range"][0] * 30 == p[0]["frames"] and p[1]["frames"] >= 6       # at least 0.2 s of quiet
    (tmp_path / "scenes" / "s2.js").write_text(INSIDE + "// edited\n")
    q = keys.parts(tmp_path, t, "s1", "draft")
    assert q[0]["key"] == p[0]["key"] and q[1]["key"] != p[1]["key"]
    (tmp_path / "scenes" / "s2.js").write_text(INSIDE + "export const join = 'hard'\n")
    assert [x["id"] for x in keys.parts(tmp_path, t, "s1", "draft")] == ["s1"]


def test_a_recalled_chapter_is_part_of_the_recalling_chapters_key(tmp_path):
    t = two_chapters(tmp_path, ROAD.replace("SHOTS", ""), "export default function draw(c) { c.recall('s1') }\nexport const join = 'hard'\n")
    before = keys.clip_key(tmp_path, t, "s2", "draft")
    (tmp_path / "scenes" / "s1.js").write_text(ROAD.replace("SHOTS", "// edited"))
    assert keys.clip_key(tmp_path, t, "s2", "draft") != before


@needs_engine
def test_focus_dims_what_is_not_named_and_lifts_when_it_ends(tmp_path):
    two_chapters(tmp_path, ROAD.replace("SHOTS", "c.focus('payment', c.phrase('01', 'payment'), { until: 1.0 })"), INSIDE)
    frames = Engine(tmp_path).boxes_at([{"clip": "s1", "t": 0.5}, {"clip": "s1", "t": 0.95}, {"clip": "s1", "t": 1.5}])
    op = lambda f, name: next(b["opacity"] for b in f["boxes"] if b["name"] == name)
    assert op(frames[0], "checkout") == 1
    assert op(frames[1], "checkout") < 0.5 and op(frames[1], "payment") == 1 and op(frames[1], "name-payment") == 1
    assert op(frames[2], "checkout") > 0.9


@needs_engine
def test_shots_go_close_on_a_name_and_back_and_kept_labels_keep_their_size(tmp_path):
    shots = "c.shots([[0, 'wide'], [0.3, ['close', 'payment']], [1.0, 'back']], { move: 0.4 })"
    two_chapters(tmp_path, ROAD.replace("SHOTS", shots), INSIDE)
    frames = Engine(tmp_path).boxes_at([{"clip": "s1", "t": 0.1}, {"clip": "s1", "t": 0.8}, {"clip": "s1", "t": 1.5}])
    box = lambda f, name: next(b for b in f["boxes"] if b["name"] == name)
    assert abs(box(frames[0], "payment")["w"] - 300) < 2
    assert box(frames[1], "payment")["w"] > 600                                  # framed close, with its label
    assert abs(box(frames[1], "name-payment")["h"] - box(frames[0], "name-payment")["h"]) < 2
    assert abs(box(frames[2], "payment")["w"] - 300) < 2                         # back to the wide


@needs_engine
def test_a_dissolve_ends_on_the_next_chapters_first_frame(tmp_path):
    two_chapters(tmp_path, ROAD.replace("SHOTS", ""), INSIDE)
    e = Engine(tmp_path)
    e.stills([{"clip": "s1", "t": 59 / 30, "out": str(tmp_path / "last.png")}, {"clip": "s2", "t": 0, "out": str(tmp_path / "first.png")},
              {"clip": "s1", "t": 1.0, "out": str(tmp_path / "before.png")}])
    a, b, c = rgba(tmp_path / "last.png"), rgba(tmp_path / "first.png"), rgba(tmp_path / "before.png")
    diff = lambda x, y: sum(abs(p - q) for p, q in zip(x[::997], y[::997])) / len(x[::997])
    assert diff(a, b) < 2 and diff(c, b) > 20


@needs_engine
def test_a_match_cut_carries_the_named_thing_to_where_the_next_chapter_draws_it(tmp_path):
    two_chapters(tmp_path, ROAD.replace("SHOTS", ""), INSIDE + "export const join = { match: 'payment' }\n")
    f = Engine(tmp_path).boxes_at([{"clip": "s1", "t": 58 / 30}])[0]       # the last frame but one: still faintly visible
    pay = next(b for b in f["boxes"] if b["name"] == "payment")
    assert abs(pay["x"] - 200) < 40 and abs(pay["w"] - 1520) < 80


@needs_engine
def test_a_callback_draws_the_earlier_chapters_own_frame(tmp_path):
    two_chapters(tmp_path, ROAD.replace("SHOTS", "c.S.rect('mark', 100, 100, 200, 200, { fill: '#ff0000' })"),
                 "export default function draw(c) { c.recall('s1', 'end', { into: [960, 0, 960, 460] }) }\nexport const join = 'hard'\n")
    e = Engine(tmp_path)
    e.stills([{"clip": "s2", "t": 0.5, "out": str(tmp_path / "s2.png")}])
    px = rgba(tmp_path / "s2.png")
    w = 1920
    at = lambda x, y: tuple(px[(y * w + x) * 3:(y * w + x) * 3 + 3])
    assert at(960 + 100, 100) == (255, 0, 0)          # the mark, at half scale in the inset
    assert at(150, 150) != (255, 0, 0)


@needs_engine
def test_the_template_grammar_chapter_draws_through_its_cues(tmp_path):
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    (tmp_path / "scenes").mkdir()
    (tmp_path / "scenes" / "s1.js").write_text((root / "templates" / "live" / "scenes" / "example-grammar.js").read_text())
    said = [("01", "Every order goes from checkout, to payment, to the bank.", 0.2, 3.0),
            ("02", "When the bank is slow, payment waits.", 3.4, 5.6),
            ("03", "The setting that decides how long sits inside payment. Step back, and checkout waits too.", 6.0, 11.0)]
    narration = []
    for i, text, a, b in said:
        ws = text.split()
        narration.append({"id": f"s1_{i}", "clip": "s1", "text": text, "caption": text, "paragraph": 0, "start": a, "end": b,
                          "words": [{"w": w, "start": a + k * (b - a) / len(ws), "end": a + (k + 1) * (b - a) / len(ws)} for k, w in enumerate(ws)]})
    t = {"version": 1, "fps": 30, "duration": 12.0, "cues": {},
         "tracks": {"scene": [{"id": "s1", "engine": "live", "title": "One", "start": 0.0, "end": 12.0}],
                    "narration": narration, "captions": tl.chunk_captions(narration), "audio": []}}
    (tmp_path / "timeline.json").write_text(json.dumps(t))
    (tmp_path / "video.json").write_text(json.dumps({"title": "t", "engine": "live"}))
    frames = Engine(tmp_path).boxes_at([{"clip": "s1", "t": x} for x in (1.0, 4.0, 8.0, 11.5)])
    box = lambda f, n: next(b for b in f["boxes"] if b["name"] == n)
    assert box(frames[1], "checkout")["opacity"] < 0.5                     # focus on the bank
    assert box(frames[2], "payment")["w"] > 2 * box(frames[0], "payment")["w"]
    assert abs(box(frames[2], "name-payment")["h"] - box(frames[0], "name-payment")["h"]) < 2
    assert abs(box(frames[3], "payment")["w"] - box(frames[0], "payment")["w"]) < 2
