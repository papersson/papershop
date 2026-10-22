"""The feel helpers in the scenes templates (templates/live/scenes/example-feel.js), and video.json motion:
a hitstop holds and catches up without moving later cues, a shake stays inside its limits, and
"reduced" takes both out, as part of what a live clip is keyed on."""
import json
import shutil
import subprocess

import pytest

from studio_kit.env import ROOT, engine_dir
from studio_kit.keys import clip_key
from test_render import make_video

node = pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")

SCRIPT = """
import * as f from %s
import * as kit from %s
const { ts } = JSON.parse(process.argv[2])
console.log(JSON.stringify({
  hit: ts.map(t => f.hitstop(t, 1, 3, 30)),
  hitReduced: ts.map(t => f.hitstop(t, 1, 3, 30, { reduced: true })),
  shake: ts.map(t => f.shake(kit, t, 1, 1)),
  again: ts.map(t => f.shake(kit, t, 1, 1)),
  big: ts.map(t => f.shake(kit, t, 1, 5)),
  shakeReduced: ts.map(t => f.shake(kit, t, 1, 1, { reduced: true })),
}))
"""


def run(tmp_path, ts):
    script = tmp_path / "feel.mjs"
    script.write_text(SCRIPT % (json.dumps((ROOT / "templates" / "live" / "scenes" / "example-feel.js").as_uri()),
                                json.dumps((engine_dir("shared") / "motion.js").as_uri())))
    done = subprocess.run(["node", str(script), json.dumps({"ts": ts})], capture_output=True, text=True, check=True)
    return json.loads(done.stdout)


@node
def test_a_hitstop_holds_its_frames_then_catches_up_to_real_time(tmp_path):
    ts = [round(0.5 + i / 300, 5) for i in range(301)]          # 0.5 to 1.5 s
    got = run(tmp_path, ts)
    hit = dict(zip(ts, got["hit"]))
    assert all(hit[t] == t for t in ts if t < 1)                 # real time before the contact
    assert all(hit[t] == 1 for t in ts if 1 <= t < 1.1)          # held for 3 frames at 30 fps
    assert all(hit[t] == pytest.approx(t) for t in ts if t >= 1.35)    # back on real time
    assert all(b >= a - 1e-9 for a, b in zip(got["hit"], got["hit"][1:]))   # never runs backwards
    assert got["hitReduced"] == ts


@node
def test_a_shake_is_pure_capped_and_gone_after_half_a_second(tmp_path):
    ts = [round(0.9 + i / 100, 3) for i in range(80)]
    got = run(tmp_path, ts)
    assert got["shake"] == got["again"]
    by = dict(zip(ts, got["shake"]))
    assert all(v == {"x": 0, "y": 0, "deg": 0} for t, v in by.items() if t < 1 or t >= 1.5)
    assert any(abs(v["x"]) > 1 for t, v in by.items() if 1 <= t < 1.2)
    for v in got["big"]:                                          # trauma clamps to 1
        assert abs(v["x"]) <= 12 and abs(v["y"]) <= 12 and abs(v["deg"]) <= 1
    assert all(v == {"x": 0, "y": 0, "deg": 0} for v in got["shakeReduced"])


def test_motion_reduced_is_part_of_a_live_clips_key_and_unset_keeps_it(tmp_path):
    make_video(tmp_path)
    t = json.loads((tmp_path / "timeline.json").read_text())
    keys = lambda: [clip_key(tmp_path, t, c["id"], "check", engine="live") for c in t["tracks"]["scene"]]
    (tmp_path / "video.json").write_text(json.dumps({"title": "t", "engine": "live"}))
    plain = keys()
    (tmp_path / "video.json").write_text(json.dumps({"title": "t", "engine": "live", "motion": "reduced"}))
    assert all(a != b for a, b in zip(plain, keys()))
    (tmp_path / "video.json").write_text(json.dumps({"title": "t", "engine": "live", "motion": "sideways"}))
    from studio_kit import settings
    with pytest.raises(SystemExit, match="motion must be one of full, reduced"):
        settings.load(tmp_path)
