"""Checks that run through the engine interface. Phase 0 has determinism; the band, contrast and
alignment checks join it later.
"""
import hashlib
import tempfile
from pathlib import Path

from . import timeline as tl
from .engine import Engine


def determinism(video, samples=3, engine=None):
    """Render `samples` frames per clip twice, in separate engine calls, and compare their hashes.
    A frame that differs means some state leaks between frames (a timer, unseeded randomness)."""
    engine = engine or Engine(video)
    t = tl.load(video)
    reqs = []
    for c in t["tracks"]["scene"]:
        dur = c["end"] - c["start"]
        reqs += [{"clip": c["id"], "t": round(dur * (i + 1) / (samples + 1), 3)} for i in range(samples)]
    with tempfile.TemporaryDirectory() as tmp:
        runs = []
        for run in ("a", "b"):
            batch = [{**r, "out": str(Path(tmp) / f"{run}-{r['clip']}-{r['t']}.png")} for r in reqs]
            engine.stills(batch)
            runs.append([hashlib.sha256(Path(r["out"]).read_bytes()).hexdigest() for r in batch])
    return [{**r, "a": a[:12], "b": b[:12], "same": a == b} for r, a, b in zip(reqs, *runs)]


def main(args):
    rows = determinism(args.video, args.samples)
    for r in rows:
        print(f"{'ok  ' if r['same'] else 'DIFF'}  {r['clip']} t={r['t']:<8} {r['a']} {r['b']}")
    bad = [r for r in rows if not r["same"]]
    print(f"determinism: {len(rows) - len(bad)} of {len(rows)} frames identical")
    return 1 if bad else 0
