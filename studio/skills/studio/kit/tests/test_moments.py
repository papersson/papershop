"""The moments sampler gives the frames the three samplers it replaced chose: the legacy code is
kept here verbatim, as the reference, and compared on a timeline with every case they handled."""
from pathlib import Path

import pytest

from studio_kit import moments, render
from studio_kit import timeline as tl


def fixture():
    def sent(sid, clip, start, end):
        return {"id": sid, "clip": clip, "text": sid, "caption": f"Caption {sid}.", "paragraph": 0,
                "start": start, "end": end, "words": []}
    narration = [sent("s1_01", "s1", 0.4, 1.9), sent("s1_02", "s1", 2.0, 2.1),     # shorter than STILL_BEFORE_END
                 sent("s1_03", "s1", 2.3, 4.25), sent("s1_04", "s1", 4.4, 5.9), sent("s1_05", "s1", 6.0, 7.66),
                 sent("s3_01", "s3", 13.1, 14.7)]
    return {"version": 1, "fps": 30, "duration": 16.0, "cues": {},
            "tracks": {"scene": [{"id": "s1", "engine": "live", "title": "A", "start": 0.0, "end": 8.0},
                                 {"id": "s2", "engine": "live", "title": "B", "start": 8.0, "end": 12.7},   # no narration
                                 {"id": "s3", "engine": "live", "title": "C", "start": 12.7, "end": 15.1},
                                 {"id": "s4", "engine": "live", "title": "D", "start": 15.1, "end": 16.0}],  # short, no narration
                       "narration": narration, "captions": tl.chunk_captions(narration), "audio": []}}


# --- the legacy samplers, as they were ----------------------------------------------------------------

def legacy_still_requests(timeline, outdir, clips=None):
    reqs = []
    for s in timeline["tracks"]["narration"]:
        if clips and s["clip"] not in clips:
            continue
        c = tl.clip(timeline, s["clip"])
        t = max(s["start"], s["end"] - 0.15) - c["start"]
        reqs.append({"id": s["id"], "clip": s["clip"], "t": round(t, 3), "out": str(outdir / f"{s['id']}.jpg"),
                     "scale": 0.25, "caption": s["caption"], "at": round(s["start"], 3)})
    narrated = {s["clip"] for s in timeline["tracks"]["narration"]}
    for c in timeline["tracks"]["scene"]:
        if c["id"] in narrated or (clips and c["id"] not in clips):
            continue
        dur = c["end"] - c["start"]
        for i in range(max(3, int(dur / 1.5))):
            local = min(dur - 1 / timeline["fps"], (i + 0.5) * dur / max(3, int(dur / 1.5)))
            sid = f"{c['id']}_t{i + 1:02d}"
            reqs.append({"id": sid, "clip": c["id"], "t": round(local, 3), "out": str(outdir / f"{sid}.jpg"),
                         "scale": 0.25, "caption": f"{c['start'] + local:.1f} s", "at": round(c["start"] + local, 3)})
    return reqs


def legacy_sample_times(t, per_clip, clips=None):
    out = []
    for c in t["tracks"]["scene"]:
        if clips is not None and c["id"] not in clips:
            continue
        sents = [s for s in t["tracks"]["narration"] if s["clip"] == c["id"]]
        if not sents:
            dur = c["end"] - c["start"]
            out += [{"clip": c["id"], "t": round(dur * (i + 1) / (per_clip + 1), 3)} for i in range(per_clip)]
            continue
        picks = sorted({sents[min(len(sents) - 1, round(i * (len(sents) - 1) / max(1, per_clip - 1)))]["id"]
                        for i in range(per_clip)})
        for s in sents:
            if s["id"] in picks:
                out.append({"clip": c["id"], "t": round(max(s["start"], s["end"] - 0.15) - c["start"], 3)})
    return out


def legacy_determinism(t, samples, clips=None):
    reqs = []
    for c in t["tracks"]["scene"]:
        if clips is not None and c["id"] not in clips:
            continue
        dur = c["end"] - c["start"]
        reqs += [{"clip": c["id"], "t": round(dur * (i + 1) / (samples + 1), 3)} for i in range(samples)]
    return reqs


def legacy_strip(t, out, clip, t0, frames=12):
    reqs = [{"clip": clip, "t": round(t0 + (i - frames // 2) / t["fps"], 4)} for i in range(frames)]
    return [r for r in reqs if r["t"] >= 0], out / f"strip_{clip}_{t0}.png"


def legacy_phone(t, n=15):
    sents = t["tracks"]["narration"]
    picks = [sents[round(i * (len(sents) - 1) / max(1, n - 1))] for i in range(min(n, len(sents)))]
    return [(s["id"], s["clip"], round(max(s["start"], s["end"] - 0.15) - tl.clip(t, s["clip"])["start"], 3)) for s in picks]


def legacy_crops(t, ids=None):
    out = []
    for s in t["tracks"]["narration"]:
        if ids and s["id"] not in ids:
            continue
        c = tl.clip(t, s["clip"])
        out.append((s["id"], s["clip"], round(max(s["start"], s["end"] - 0.15) - c["start"], 3)))
    return out


# --- the comparisons -----------------------------------------------------------------------------------

@pytest.mark.parametrize("clips", [None, {"s2"}, {"s1", "s4"}])
def test_the_cut_stills_are_unchanged(clips):
    t, out = fixture(), Path("/stills")
    assert render.still_requests(t, out, clips) == legacy_still_requests(t, out, clips)


@pytest.mark.parametrize("per_clip", [1, 2, 3, 5, 8])
@pytest.mark.parametrize("clips", [None, set(), {"s2", "s3"}])
def test_the_check_samples_are_unchanged(per_clip, clips):
    t = fixture()
    assert moments.requests(moments.check_samples(t, per_clip, clips)) == legacy_sample_times(t, per_clip, clips)
    assert moments.requests(moments.even(t, per_clip, clips)) == legacy_determinism(t, per_clip, clips)


@pytest.mark.parametrize("clip,t0", [("s1", 0.1), ("s1", 3.0), ("s2", 2.2667)])
def test_a_strip_is_unchanged(clip, t0):
    t = fixture()
    m = moments.sequence(t, clip, t0)
    reqs, name = legacy_strip(t, Path("/out"), clip, t0)
    assert moments.requests([m]) == reqs and Path("/out") / f"{m['id']}.png" == name


def test_the_phone_sheet_and_the_crops_pick_the_same_frames():
    t = fixture()
    ends = moments.sentence_ends(t)
    picks = [ends[round(i * (len(ends) - 1) / max(1, 14))] for i in range(min(15, len(ends)))]
    assert [(m["id"], m["clip"], m["t"]) for m in picks] == legacy_phone(t)
    assert [(m["id"], m["clip"], m["t"]) for m in ends] == legacy_crops(t)
    assert [(m["id"], m["clip"], m["t"]) for m in ends if m["id"] in {"s1_02", "s3_01"}] == legacy_crops(t, {"s1_02", "s3_01"})


def test_every_moment_carries_its_absolute_time_and_kind():
    t = fixture()
    kinds = {m["kind"] for m in moments.stills(t) + moments.even(t, 2) + [moments.sequence(t, "s3", 1.0)]}
    assert kinds == {"sentence-end", "spread", "check-sample", "strip"}
    s3 = moments.sentence_ends(t, {"s3"})[0]
    assert s3["time"] == round(12.7 + s3["t"], 3) and s3["sentence"] == "s3_01"


def test_sheets_take_several_strips_and_a_windows_file_in_one_engine_call(tmp_path, monkeypatch):
    import json
    import shutil
    import subprocess
    from studio_kit import cli, sheets
    (tmp_path / "video.json").write_text("{}")
    (tmp_path / "timeline.json").write_text(json.dumps(fixture()))
    frame = tmp_path / "frame.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=blue:s=64x36:d=1", "-frames:v", "1", str(frame)], check=True)

    class Engine:
        calls = []

        def __init__(self, video):
            pass

        def stills(self, reqs):
            Engine.calls.append(reqs)
            for r in reqs:
                shutil.copyfile(frame, r["out"])

    (tmp_path / "windows.json").write_text(json.dumps([{"clip": "s3", "t": 1.0, "frames": 4, "fps": 10}]))
    monkeypatch.setattr(sheets, "Engine", Engine)
    monkeypatch.setattr(sheets.tl, "build", lambda video: None)
    args = cli.build_parser().parse_args(["sheets", str(tmp_path), str(tmp_path / "out"), "--strip", "s1", "3.0",
                                          "--strip", "s2", "0.1", "--windows", str(tmp_path / "windows.json")])
    assert args.strip == [["s1", "3.0"], ["s2", "0.1"]]
    sheets.main(args)
    (reqs,) = Engine.calls
    t = fixture()
    expected = [moments.sequence(t, "s1", 3.0), moments.sequence(t, "s2", 0.1), moments.sequence(t, "s3", 1.0, 4, 10)]
    assert [(r["clip"], r["t"]) for r in reqs] == [(r["clip"], r["t"]) for r in moments.requests(expected)]
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == sorted(f"{m['id']}.png" for m in expected)
    with pytest.raises(SystemExit, match="strip window"):
        sheets.windows([["s1", "soon"]])
