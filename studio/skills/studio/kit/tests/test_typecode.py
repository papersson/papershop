import json
from types import SimpleNamespace

import pytest

from studio_kit import cli, narration, sfx, soundkit, typecode
from studio_kit import timeline as tl
from test_narration import SCRIPT

pytest.importorskip("numpy")
pytestmark = pytest.mark.skipif(soundkit.check()[0] != "ok", reason="the sound kit is not fetched (doctor --fetch --sounds)")

V1 = "int main(void) {\n    return 0;\n}\n"
V2 = "int main(void) {\n    int x = 100;\n    draw(x);\n    return 0;\n}\n"
V3 = "int main(void) {\n    int x = 300;\n    draw(x);\n    return 0;\n}\n"


def video(tmp_path):
    (tmp_path / "SCRIPT.md").write_text(SCRIPT)
    (tmp_path / "video.json").write_text(json.dumps({"title": "T", "engine": "live"}))
    narration.narrate(tmp_path, estimate=True)
    src = tmp_path / "data" / "versions"
    src.mkdir(parents=True)
    for name, text in (("v1.c", V1), ("v2.c", V2), ("v3.c", V3)):
        (src / name).write_text(text)
    (tmp_path / "data" / "run.txt").write_text("INFO: window opened\nINFO: 960 x 600\nINFO: running\n")
    return tmp_path


PLAN = {
    "sources": {"v1": "data/versions/v1.c", "v2": "data/versions/v2.c", "v3": "data/versions/v3.c"},
    "file": "main.c",
    "run": {"command": "$ cc main.c -o game && ./game", "log": "data/run.txt", "lines_before_window": 2},
    "bursts": [
        {"id": "draw", "clip": "s1", "file": "v2", "before": "v1", "ops": [
            {"op": "open", "below": "main(", "segments": [{"text": "    int x = 100;", "typo": 2}],
             "due": {"sentence": "s1_02", "at": "end"}},
            {"op": "open", "below": "int x", "text": "    draw(x);"},
            {"op": "save"}, {"op": "run"}]},
        {"id": "move", "clip": "s2", "file": "v3", "before": "v2", "ops": [
            {"op": "change", "line": "int x", "from": "100", "to": "300", "think": 0.3}, {"op": "save"}]},
    ],
}


def test_typed_code_ends_as_the_recorded_file_and_its_keys_are_one_stream(tmp_path):
    """Code is typed, not revealed: the edits replay into the recorded version exactly, a typo is
    typed and put right, every key gets a frame, and the same keys are one stream of sound on the
    burst's cue, with accents on the save and the window opening."""
    v = video(tmp_path)
    report = []
    data = typecode.build(v, PLAN, report)
    draw = data["draw"]
    assert draw["after"] == V2.rstrip("\n").split("\n") and draw["cue"] == "type-draw"
    kinds = [s[1] for s in draw["steps"]]
    assert kinds.count("back") == 2 and "enter" in kinds                  # the typo, put right; the save's Enter
    first_back = kinds.index("back")
    before_correction = [fx for _, _, effects in draw["steps"][:first_back] for fx in effects
                         if fx[0] == "set" and fx[1] == 1][-1][2]
    assert before_correction != "    int x = 100;"                       # digits and punctuation must really be wrong
    frames = [s[0] for s in draw["steps"]]
    assert frames[0] == 0 and all(b > a for a, b in zip(frames, frames[1:]))
    assert draw["run"]["pop"] > draw["run"]["enter"] > draw["run"]["up"] and len(draw["run"]["log"]) == 3
    cues = json.loads((v / "cues.json").read_text())
    assert {"type-draw", "type-draw-save", "type-draw-run", "type-draw-pop", "type-move", "type-move-save"} <= set(cues)
    t = tl.load(v)
    due = tl.event_time(t, {"sentence": "s1_02", "at": "end"})
    first_line_done = t["cues"]["type-draw"] + next(f for f, _, fx in draw["steps"] if ["set", 1, "    int x = 100;"] in
                                                     [x for x in fx if x[0] == "set"]) / t["fps"]
    assert first_line_done <= due + 1 / t["fps"]                        # finished by the words that discuss it
    effects = json.loads((v / "audio" / "sfx.json").read_text())
    streams = [e for e in effects if "events" in e]
    assert [e["stream"] for e in streams] == ["typing:draw", "typing:move"] and all(e["source"] == "typing" for e in effects)
    assert sum(k == "tick" for _, k in streams[0]["events"]) == 3
    assert any(e["t"] == "type-draw-pop" and e["type"] == "thump" for e in effects)


def test_a_plan_that_does_not_end_at_the_recorded_file_stops_with_a_diff(tmp_path):
    v = video(tmp_path)
    plan = json.loads(json.dumps(PLAN))
    plan["bursts"][0]["ops"][1]["text"] = "    draw(y);"
    with pytest.raises(SystemExit, match=r"differs from v2[\s\S]*-    draw\(x\);[\s\S]*\+    draw\(y\);"):
        typecode.build(v, plan)


def test_studio_sfx_keeps_the_generated_effects(tmp_path):
    """The builder's own cue list doesn't erase the typing: generated effects carry their source, and
    `studio sfx` keeps them unless the new list has effects from that source."""
    v = video(tmp_path)
    plan = {**PLAN, "bursts": [PLAN["bursts"][1]]}
    plan["bursts"][0] = {**plan["bursts"][0], "before": "v2"}
    typecode.build(v, plan)
    (tmp_path / "fx.json").write_text(json.dumps([{"t": 1.0, "type": "click"}]))
    sfx.main(SimpleNamespace(video=v, cues=tmp_path / "fx.json"))
    effects = json.loads((v / "audio" / "sfx.json").read_text())
    assert any(e.get("source") == "typing" for e in effects) and any(e["t"] == 1.0 for e in effects)


def test_typing_is_a_command():
    assert cli.COMMANDS["typing"][2] == "typecode:main"
