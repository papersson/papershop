"""Code tours: `studio source` pins real files at one commit, and the source check holds every
citation in a tour to them (studio_kit/source.py, engines/live/src/source.js)."""
import json
import shutil
import subprocess

import pytest

from studio_kit import source
from studio_kit.env import engine_dir

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")

FILE = "const std = @import(\"std\");\n\npub fn main() void {\n    assert(1 + 1 == 2);\n}\n"


def repo(tmp_path):
    r = tmp_path / "repo"
    (r / "src").mkdir(parents=True)
    (r / "src" / "main.zig").write_text(FILE)
    git = lambda *a: subprocess.run(["git", "-C", str(r), *a], check=True, capture_output=True)  # noqa: E731
    git("init", "-q")
    git("-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
    git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "one")
    return r


def video(tmp_path):
    v = tmp_path / "film"
    (v / "data").mkdir(parents=True)
    (v / "video.json").write_text("{}")
    return v


def tour(v, stops, name="data/tour.json"):
    (v / name).parent.mkdir(parents=True, exist_ok=True)
    (v / name).write_text(json.dumps({"views": {"main": {"file": "src/main.zig", "cols": 40, "stops": stops}}}))


def bad(rows):
    return [r["detail"] for r in rows if not r["ok"]]


def test_source_pins_the_commit_and_the_check_passes(tmp_path):
    r, v = repo(tmp_path), video(tmp_path)
    data = source.add(v, r, ["src/main.zig"], url="https://example.com/repo")
    assert len(data["commit"]) == 40
    assert (v / "data" / "source" / "src" / "main.zig").read_text() == FILE
    assert data["files"]["src/main.zig"]["lines"] == 5
    tour(v, [{"at": 1, "show": [[3, 5]], "focus": [[4, 4]], "point": {"line": 4, "text": "1 + 1"}}])
    rows = source.check(v)
    assert not bad(rows) and "1 files" in rows[-1]["detail"]
    assert source.link(data, "src/main.zig", 3, 5).endswith(f"/blob/{data['commit']}/src/main.zig#L3-L5")


def test_the_check_catches_wrong_citations_and_changed_files(tmp_path):
    r, v = repo(tmp_path), video(tmp_path)
    source.add(v, r, ["src/main.zig"])
    tour(v, [
        {"at": 1, "show": [[3, 9]]},                                         # past the end
        {"at": 2, "show": [[3, 4]], "focus": [[5, 5]]},                       # focus not shown
        {"at": 3, "show": [[3, 4]], "point": {"line": 4, "text": "2 + 2"}},   # token not on the line
        {"at": 4, "file": "src/other.zig", "show": [[1, 1]]},                 # not pinned
    ])
    got = bad(source.check(v))
    assert len(got) == 4
    assert any("outside src/main.zig (1–5)" in d for d in got)
    assert any("focus 5–5 is not all shown" in d for d in got)
    assert any("'2 + 2' is not on src/main.zig:4" in d for d in got)
    assert any("src/other.zig is not in data/source.json" in d for d in got)
    (v / "data" / "source" / "src" / "main.zig").write_text(FILE + "// edited\n")
    tour(v, [{"at": 1, "show": [[1, 2]]}])
    assert any("changed since" in d for d in bad(source.check(v)))


def test_chapter_tours_are_checked_too(tmp_path):
    r, v = repo(tmp_path), video(tmp_path)
    source.add(v, r, ["src/main.zig"])
    tour(v, [{"at": 1, "show": [[3, 4]], "point": {"line": 3, "text": "nope"}}], "data/s2/tour.json")
    got = bad(source.check(v))
    assert got and got[0].startswith("view s2/main")


def test_a_wide_line_warns(tmp_path):
    r, v = repo(tmp_path), video(tmp_path)
    source.add(v, r, ["src/main.zig"])
    (v / "data" / "tour.json").write_text(json.dumps({"views": {"main": {"file": "src/main.zig", "cols": 10, "stops": [{"at": 1, "show": [[1, 1]]}]}}}))
    rows = source.check(v)
    assert not bad(rows) and any(r.get("severity") == "warning" and "wider than" in r["detail"] for r in rows)


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_syntax_colours_zig_and_leaves_prose_alone():
    js = (engine_dir("live") / "src" / "source.js").as_uri()
    out = subprocess.run(["node", "--input-type=module", "-e",
                          f"import {{syntax}} from '{js}';"
                          "console.log(JSON.stringify([syntax('    assert(@sizeOf(T) == 128); // size', 'zig'), syntax('safety and performance', 'text')]))"],
                         capture_output=True, text=True, check=True).stdout
    zig, prose = json.loads(out)
    kinds = {p["text"]: p["kind"] for p in zig}
    assert kinds["@sizeOf"] == "builtin" and kinds["128"] == "number" and kinds["// size"] == "comment"
    assert "".join(p["text"] for p in zig) == "    assert(@sizeOf(T) == 128); // size"
    assert prose == [{"text": "safety and performance", "kind": "plain"}]


def test_a_tour_scene_keys_on_its_stops_cues_and_the_pinned_files(tmp_path):
    """A stop's cue moving, or a pinned file changing, must re-render the chapter that tours it."""
    from studio_kit import keys
    r, v = repo(tmp_path), video(tmp_path)
    source.add(v, r, ["src/main.zig"])
    tour(v, [{"at": "s2-open", "show": [[1, 2]]}, {"at": ["s2-main", 0.5], "show": [[3, 5]]}], "data/s2/tour.json")
    (v / "scenes").mkdir()
    (v / "scenes" / "s2.js").write_text("import { loadTour, SourceView } from '@studio/kit.js'\n"
                                        "const tour = await loadTour(import.meta.url, { tour: 'data/s2/tour.json' })\n"
                                        "export default function draw(c) { SourceView(c, tour, 'main', { box: [0, 0, 100, 100] }) }\n")
    assert keys.scene_cues(v, "s2", {"s2"}) >= {"s2-open", "s2-main"}
    assert keys.scene_data(v, "s2", {"s2"}) >= {"data/s2/tour.json", "data/source.json", "data/source"}


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_a_stop_takes_over_only_as_early_as_its_change_needs():
    """A pointed token 0.7 s before a stop that only points elsewhere stays on screen; a scroll leads by a second."""
    js = (engine_dir("live") / "src" / "source.js").as_uri()
    stops = [{"t": 10, "file": "a", "show": [[1, 5]], "point": {"line": 2, "text": "x"}},
             {"t": 10.7, "file": "a", "show": [[1, 5]], "point": {"line": 3, "text": "y"}},
             {"t": 12, "file": "a", "show": [[1, 5]], "focus": [[2, 2]]},
             {"t": 14, "file": "a", "show": [[6, 9]]}]
    out = subprocess.run(["node", "--input-type=module", "-e",
                          f"import {{stopAt}} from '{js}'; const s = {json.dumps(stops)};"
                          "console.log(JSON.stringify([10.2, 10.5, 11.6, 13.05, 12.9].map(t => stopAt(s, t))))"],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == [0, 1, 2, 3, 2]
