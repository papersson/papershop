"""Observability episode 1's timing, pinned: every cue and every phrase its scene code reads, resolved from
a snapshot of its narration (cut 9, 2026-10-28) and compared with the times that film shipped with.

A shipped film is the best fixture the timeline has: 359 cues anchored every way the contract allows,
and 189 sentences of real ElevenLabs narration with recognised words. A change to how anchors resolve
that moves one of them by a frame fails here. If a move is intended, regenerate expected.json and say
why in the commit; never loosen the comparison.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from studio_kit import timeline as tl
from studio_kit.env import engine_dir

EP1 = Path(__file__).parent / "fixtures" / "ep1-timing"


def load():
    return json.loads((EP1 / "timeline.json").read_text()), json.loads((EP1 / "expected.json").read_text())


def test_every_cue_of_episode_1_resolves_to_the_frame_it_shipped_on():
    t, expected = load()
    cues, _ = tl.cue_sources(EP1, t)
    assert len(cues) == len(expected["cues"]) == 359
    moved = {name: (tl.event_time(t, spec), expected["cues"][name]) for name, spec in cues.items()
             if tl.event_time(t, spec) != expected["cues"][name]}
    assert moved == {}


def test_the_phrases_episode_1_scene_code_reads_keep_their_times():
    t, expected = load()
    said = {s["id"]: s for s in t["tracks"]["narration"]}
    assert expected["scene_phrases"]
    for c in expected["scene_phrases"]:
        assert tl.phrase_start(said[c["sentence"]], c["phrase"]) == c["time"], c


PARITY = """
import { phraseStart } from %s
const { entries, calls } = JSON.parse(process.argv[2])
console.log(JSON.stringify(calls.map(c => phraseStart(entries[c.sentence], c.phrase))))
"""


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_the_engines_resolve_episode_1s_scene_phrases_as_the_kit_does(tmp_path):
    t, expected = load()
    said = {s["id"]: s for s in t["tracks"]["narration"]}
    calls = expected["scene_phrases"]
    script = tmp_path / "parity.mjs"
    script.write_text(PARITY % json.dumps((engine_dir("shared") / "timing.js").as_uri()))
    entries = {c["sentence"]: said[c["sentence"]] for c in calls}
    run = subprocess.run(["node", str(script), json.dumps({"entries": entries, "calls": calls})],
                         capture_output=True, text=True, check=True)
    assert json.loads(run.stdout) == [c["time"] for c in calls]
