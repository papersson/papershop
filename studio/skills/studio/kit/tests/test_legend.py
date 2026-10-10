"""The colour legend check: one colour, one meaning, read from the engines' boxes against video.json's legend."""
import json

from studio_kit import check, legend
from test_render import make_video

HOT, COLD, WARM, GOOD, BAD, DIM, INK = "#F2A93B", "#8FD3FF", "#F5CF7A", "#8FD19E", "#E4715F", "#8C97A4", "#E6EBF0"
LAYOUT = {"width": 1920, "height": 1080, "band": {"height": 160}}


def rgb(h):
    return f"rgb({int(h[1:3], 16)}, {int(h[3:5], 16)}, {int(h[5:7], 16)})"


def box(name, stroke=None, fill=None, means=None, **kw):
    """A box as the engines report it: colours as the browser resolves them."""
    return {"name": name, "x": 0, "y": 0, "w": 10, "h": 10, "fill": rgb(fill) if fill else "none",
            "stroke": rgb(stroke) if stroke else "none", **({"means": means} if means else {}), **kw}


def video(tmp_path, declared=None, engine="live"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    make_video(tmp_path)
    (tmp_path / "video.json").write_text(json.dumps({"title": "t", "engine": engine, **({"legend": declared} if declared is not None else {})}))
    return tmp_path


def frames(*per_clip):
    return LAYOUT, [{"clip": clip, "t": 1.0, "boxes": boxes} for clip, boxes in per_clip]


def warnings(rows):
    return [r["detail"] for r in rows if r.get("severity") == "warning"]


class FakeEngine:
    def __init__(self, by_clip):
        self.by_clip, self.asked = by_clip, []

    def layout(self):
        return LAYOUT

    def boxes_at(self, requests):
        self.asked += [r["clip"] for r in requests]
        return [{**r, "boxes": self.by_clip.get(r["clip"], [])} for r in requests]


def test_colours_are_read_as_the_browser_reports_them():
    assert legend.hex_of("rgb(143, 211, 255)") == COLD and legend.hex_of("#8fd3ff") == COLD
    assert legend.hex_of("rgba(143, 211, 255, 0.9)") == COLD
    for none in ("none", "rgba(0, 0, 0, 0)", "rgba(143, 211, 255, 0.1)", "url(#g)", None):     # nothing, a tint, a gradient
        assert legend.hex_of(none) is None


def test_the_legend_names_the_engines_theme_colours(tmp_path):
    assert legend.declared(video(tmp_path / "a", {"request": "warm", "x": "#e4715f"}))[0] == {"request": WARM, "x": BAD}
    assert legend.declared(video(tmp_path / "b", {"focus": "ice", "box": "TRAY_FILL"}, "remotion"))[0] == {"focus": COLD, "box": "#17202A"}
    v = video(tmp_path / "c", {"request": "wram"})
    rows = legend.check(v, boxes=frames(("s1", [])))
    assert not rows[0]["ok"] and "'wram' is not a live theme colour" in rows[0]["detail"]


def test_a_video_without_a_legend_is_not_checked_but_a_tag_without_one_is_named(tmp_path):
    v = video(tmp_path)
    assert legend.check(v, boxes=frames(("s1", [box("box", HOT)]))) == []
    (row,) = legend.check(v, boxes=frames(("s1", [box("box", HOT, means="request")])))
    assert row["ok"] and "declares no legend" in row["detail"]


def test_a_video_that_keeps_its_legend_passes(tmp_path):
    """Tagged, named and neutral elements, a tint and a blend mid-transition: none is a misuse."""
    v = video(tmp_path, {"step": "hot", "failure": "bad"})
    rows = legend.check(v, boxes=frames(("s1", [
        box("box one", HOT, "#151B22", means="step"), box("box failure", BAD),          # tagged; named after its meaning
        box("title", fill=INK), box("arrow", DIM), box("halo", fill=None, stroke=None) | {"fill": "rgba(242, 169, 59, 0.1)"},
        box("box two", "#C9A97B")]), ("s2", [box("box three", HOT, means="step"), box("caption", fill=HOT)])))
    assert warnings(rows) == [] and rows[-1]["ok"] and rows[-1]["detail"].startswith("2 meanings; 3 tagged elements in 2 chapters")


def test_one_colour_for_two_meanings(tmp_path):
    v = video(tmp_path, {"cost": "hot", "request": "hot"})
    assert warnings(legend.check(v, boxes=frames(("s1", [])))) == ["hot stands for cost (legend) and request (legend)"]
    v = video(tmp_path / "b", {"cost": "hot"})
    rows = legend.check(v, boxes=frames(("s1", [box("a", WARM, means="request")]), ("s2", [box("b", WARM, means="reply")])))
    assert warnings(rows) == ["warm stands for request ('a' (means request) at s1 t=1.0) and reply ('b' (means reply) at s2 t=1.0)"]
    assert rows[0]["clip"] == "s1"


def test_one_meaning_in_two_colours(tmp_path):
    v = video(tmp_path, {"step": "hot"})
    rows = legend.check(v, boxes=frames(("s1", [box("box one", HOT, means="step")]), ("s2", [box("box two", WARM, means="step")])))
    assert warnings(rows) == ["step is drawn in hot (legend) and warm ('box two' (means step) at s2 t=1.0)"]
    assert rows[0]["clip"] == "s2"
    rows = legend.check(v, boxes=frames(("s1", [box("a", WARM, means="reply")]), ("s2", [box("b", GOOD, means="reply")])))
    assert warnings(rows) == ["reply is drawn in warm ('a' (means reply) at s1 t=1.0) and good ('b' (means reply) at s2 t=1.0)"]


def test_a_reserved_colour_on_another_element(tmp_path):
    v = video(tmp_path, {"focus": "cold", "context": "dim"})
    rows = legend.check(v, boxes=frames(("s1", [box("title", fill=COLD), box("cost", COLD, means="cost"), box("guide", DIM)])))
    (w,) = warnings(rows)
    assert w.startswith("cold, which the legend keeps for focus, is on 'title' at s1 t=1.0, 'cost' (means cost) at s1 t=1.0")
    assert "tag it means: 'focus'" in w and "guide" not in w            # a neutral colour is never reserved


def test_the_whole_video_is_compared_when_only_changed_chapters_are_sampled(tmp_path):
    v = video(tmp_path, {"step": "hot"})
    keys = {"s1": "k1", "s2": "k2"}
    s1, s2 = [box("a", WARM, means="reply")], [box("b", GOOD, means="reply")]
    assert len(warnings(legend.check(v, boxes=frames(("s1", s1), ("s2", s2)), keys=keys))) == 1
    # s1 changed and alone was sampled: s2's elements come from the cache
    rows = legend.check(v, boxes=frames(("s1", s1)), clips={"s1"}, keys=keys)
    assert warnings(rows) == ["reply is drawn in warm ('a' (means reply) at s1 t=1.0) and good ('b' (means reply) at s2 t=1.0)"]
    # s2 changed and was not sampled by the other checks: the legend check samples it
    e = FakeEngine({"s2": [box("b", WARM, means="reply")]})
    rows = legend.check(v, engine=e, boxes=frames(("s1", s1)), clips={"s1"}, keys={"s1": "k1", "s2": "k3"})
    assert set(e.asked) == {"s2"} and warnings(rows) == []


def test_the_check_runs_from_studio_check(tmp_path):
    v = video(tmp_path, {"focus": "cold"})
    e = FakeEngine({"s1": [box("title", fill=COLD)], "s2": [box("title", fill=COLD, means="focus")]})
    rows = check.run(v, only=["legend"], engine=e)
    (w,) = warnings(rows)
    assert "'title' at s1" in w and "s2" not in w
    assert "legend" in check.MORE


def test_a_legend_edit_changes_a_live_clips_key_and_the_legend_check_samples_it_again(tmp_path):
    """Live scenes draw with c.legend, so a cached clip or a cached check from the old legend was stale:
    `step: hot` to `step: cold` kept the clip key and the check still read the old colour."""
    from studio_kit import render
    v = video(tmp_path, {"step": "hot"})
    t = json.loads((v / "timeline.json").read_text())
    keys = lambda: {c["id"]: render.clip_key(v, t, c["id"], "check", engine="live") for c in t["tracks"]["scene"]}
    before = keys()
    e = FakeEngine({"s1": [box("card", HOT, means="step")]})
    assert warnings(legend.check(v, engine=e, keys=before)) == [] and set(e.asked) == {"s1", "s2"}
    (v / "video.json").write_text(json.dumps({"title": "t", "engine": "live", "legend": {"step": "cold"}}))
    after = keys()
    assert all(after[c] != before[c] for c in after)
    e = FakeEngine({"s1": [box("card", COLD, means="step")]})          # the clip as the new legend draws it
    assert warnings(legend.check(v, engine=e, keys=after)) == [] and set(e.asked) == {"s1", "s2"}
    # Remotion scenes don't read the legend, and a video without one keeps its keys
    assert render.clip_key(v, t, "s1", "check", engine="remotion") == render.clip_key(video(tmp_path / "b"), t, "s1", "check", engine="remotion")


def test_the_kits_own_accent_states_unnamed_shapes_and_dimmed_elements_are_left_alone(tmp_path):
    """A lit layer, a selected cell, a minimap tagged "kit" by the kit; a Remotion Rect with no name;
    and an accent element dimmed under half opacity (a guide) were all flagged."""
    v = video(tmp_path, {"selection": "cold"})
    rows = legend.check(v, boxes=frames(("s1", [
        box("layer app", COLD, means="kit"), box("minimap", COLD, COLD, means="kit"),
        box("rect", fill=COLD, named=False), box("guide", COLD, opacity=0.3)])))
    assert warnings(rows) == [] and rows[-1]["detail"].startswith("1 meaning; 0 tagged elements")
    # the scene's own tag on a kit component is checked as any other
    rows = legend.check(v, boxes=frames(("s1", [box("layer app", COLD, means="cost")])))
    assert "is on 'layer app' (means cost)" in warnings(rows)[0]
    assert legend.check(video(tmp_path / "b"), boxes=frames(("s1", [box("layer app", COLD, means="kit")]))) == []
