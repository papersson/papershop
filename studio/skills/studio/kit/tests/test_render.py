import copy
import json
import re
from pathlib import Path

from studio_kit import cuts, render
from studio_kit import keys as clip_keys
from studio_kit import timeline as tl


def make_video(tmp_path):
    (tmp_path / "scenes").mkdir()
    for name in ("s1.js", "s2.js", "kit.js", "index.js"):
        (tmp_path / "scenes" / name).write_text(f"// {name}\n")
    narration = [{"id": "s1_01", "clip": "s1", "text": "One.", "caption": "One.", "paragraph": 0,
                  "start": 0.5, "end": 1.5, "words": []},
                 {"id": "s2_01", "clip": "s2", "text": "Two.", "caption": "Two.", "paragraph": 0,
                  "start": 2.5, "end": 3.5, "words": []}]
    t = {"version": 1, "fps": 30, "duration": 4.0, "cues": {},
         "tracks": {"scene": [{"id": "s1", "engine": "live", "title": "A", "start": 0.0, "end": 2.0},
                              {"id": "s2", "engine": "live", "title": "B", "start": 2.0, "end": 4.0}],
                    "narration": narration, "captions": tl.chunk_captions(narration),
                    "audio": [{"file": "audio/narration.mp3", "start": 0.0}]}}
    (tmp_path / "timeline.json").write_text(json.dumps(t))          # a built timeline, as the engines read it
    return t


def keys(video, t, quality="draft"):
    return {c["id"]: clip_keys.clip_key(video, t, c["id"], quality) for c in t["tracks"]["scene"]}


def test_editing_a_chapter_scene_changes_only_that_chapter(tmp_path):
    t = make_video(tmp_path)
    before = keys(tmp_path, t)
    (tmp_path / "scenes" / "s2.js").write_text("// s2, edited\n")
    after = keys(tmp_path, t)
    assert after["s1"] == before["s1"] and after["s2"] != before["s2"]


def test_editing_a_shared_scene_file_changes_every_chapter(tmp_path):
    t = make_video(tmp_path)
    before = keys(tmp_path, t)
    (tmp_path / "scenes" / "kit.js").write_text("// kit, edited\n")
    after = keys(tmp_path, t)
    assert all(after[c] != before[c] for c in before)


def test_a_caption_change_touches_only_the_clip_it_falls_in(tmp_path):
    t = make_video(tmp_path)
    before = keys(tmp_path, t)
    t2 = copy.deepcopy(t)
    t2["tracks"]["narration"][1]["caption"] = "Two, reworded."
    t2["tracks"]["captions"] = tl.chunk_captions(t2["tracks"]["narration"])
    after = keys(tmp_path, t2)
    assert after["s1"] == before["s1"] and after["s2"] != before["s2"]


def test_quality_is_part_of_the_key(tmp_path):
    t = make_video(tmp_path)
    assert keys(tmp_path, t, "draft")["s1"] != keys(tmp_path, t, "final")["s1"]


def test_latest_cut_ignores_folders_without_a_record(tmp_path):
    for n in (1, 2):
        d = tmp_path / "cuts" / f"cut{n}"
        d.mkdir(parents=True)
        (d / "cut.json").write_text(json.dumps({"cut": n}))
    (tmp_path / "cuts" / "cut3").mkdir()
    assert cuts.last(tmp_path) == 2


def test_keys_survive_moving_the_video(tmp_path):
    a = tmp_path / "a"
    a.mkdir()
    t = make_video(a)
    before = keys(a, t)
    b = tmp_path / "b"
    a.rename(b)
    assert keys(b, t) == before


def test_changing_data_rerenders_the_clips_that_read_it(tmp_path):
    """A chapter's frames depend on the data its scene imports; rewriting data/typing.json used to
    re-render every chapter, those without code too. A path built at run time reads anything."""
    t = make_video(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "runs.json").write_text('{"n": 1}')
    (tmp_path / "data" / "other.json").write_text('{"n": 1}')
    (tmp_path / "scenes" / "s1.js").write_text("import runs from '../data/runs.json';\nexport default runs;\n")
    before = keys(tmp_path, t)
    (tmp_path / "data" / "runs.json").write_text('{"n": 2}')
    after = keys(tmp_path, t)
    assert after["s1"] != before["s1"] and after["s2"] == before["s2"]
    (tmp_path / "data" / "other.json").write_text('{"n": 2}')
    assert keys(tmp_path, t) == after                                # nobody reads it
    (tmp_path / "scenes" / "s2.js").write_text("const f = (n) => import(`../data/${n}.json`);\nexport default f;\n")
    computed = keys(tmp_path, t)
    (tmp_path / "data" / "other.json").write_text('{"n": 3}')
    assert keys(tmp_path, t)["s2"] != computed["s2"]


def test_literal_browser_data_fetch_does_not_depend_on_agent_activity(tmp_path):
    t = make_video(tmp_path)
    (tmp_path / "data").mkdir()
    data = tmp_path / "data" / "runs.json"
    data.write_text('{"n": 1}')
    scene = tmp_path / "scenes" / "s1.js"
    scene.write_text("const runs = await fetch(new URL('../data/runs.json', import.meta.url)).then(r => r.json());")
    before = keys(tmp_path, t)
    (tmp_path / "data" / "activity.jsonl").write_text('{"message": "inspected frames"}\n')
    assert keys(tmp_path, t) == before
    data.write_text('{"n": 2}')
    assert keys(tmp_path, t)["s1"] != before["s1"]
    scene.write_text("const runs = await fetch('data/' + name);")
    before = keys(tmp_path, t)
    data.write_text('{"n": 3}')
    assert keys(tmp_path, t)["s1"] != before["s1"]


def test_clips_without_narration_get_stills_at_even_intervals(tmp_path):
    t = make_video(tmp_path)
    t["tracks"]["narration"] = [s for s in t["tracks"]["narration"] if s["clip"] == "s1"]
    reqs = render.still_requests(t, tmp_path)
    s2 = [r for r in reqs if r["clip"] == "s2"]
    assert [r["id"] for r in s2] == ["s2_t01", "s2_t02", "s2_t03"]
    assert all(0 <= r["t"] < 2.0 for r in s2) and [r["id"] for r in reqs if r["clip"] == "s1"] == ["s1_01"]


def test_a_chapter_moved_by_whole_frames_keeps_its_key(tmp_path):
    """A narration edit earlier in the video moves later chapters by whole frames (narration
    CHAPTER_GRID); their frames are the same, so their clips stay cached."""
    t = make_video(tmp_path)
    before = keys(tmp_path, t)
    t2 = copy.deepcopy(t)
    shift = 0.3                                   # 9 frames, 300 ms
    t2["tracks"]["scene"][0]["end"] += shift
    t2["tracks"]["scene"][1]["start"] += shift
    t2["tracks"]["scene"][1]["end"] += shift
    for s in t2["tracks"]["narration"][1:]:
        s["start"] += shift
        s["end"] += shift
    t2["tracks"]["captions"] = tl.chunk_captions(t2["tracks"]["narration"])
    after = keys(tmp_path, t2)
    assert after["s2"] == before["s2"] and after["s1"] != before["s1"]


class StillEngine:
    """Writes a tiny file per requested still and counts them."""
    def __init__(self):
        self.calls = []

    def stills(self, requests):
        self.calls.append(len(requests))
        for r in requests:
            Path(r["out"]).write_bytes(f"{r['clip']} {r['t']}".encode())


def test_stills_are_reused_unless_their_frame_changed(tmp_path):
    t = make_video(tmp_path)
    eng = StillEngine()
    reqs = lambda d: render.still_requests(t, d)
    (tmp_path / "a").mkdir()
    assert render.cached_stills(tmp_path, t, eng, reqs(tmp_path / "a")) == (2, 0)
    (tmp_path / "b").mkdir()
    assert render.cached_stills(tmp_path, t, eng, reqs(tmp_path / "b")) == (0, 2)
    assert (tmp_path / "b" / "s1_01.jpg").read_bytes() == (tmp_path / "a" / "s1_01.jpg").read_bytes()
    (tmp_path / "scenes" / "s2.js").write_text("// s2, edited\n")
    (tmp_path / "c").mkdir()
    assert render.cached_stills(tmp_path, t, eng, reqs(tmp_path / "c")) == (1, 1)


def cue_keys(tmp_path, t, cues):
    return keys(tmp_path, {**t, "cues": cues})


def test_moving_a_cue_no_scene_names_keeps_the_other_clips(tmp_path):
    t = make_video(tmp_path)
    (tmp_path / "scenes" / "s1.js").write_text("const { at, cue } = useClip();\n// waits on cue('late') below\n"
                                               "const x = spring(t - cue('chart_up', 0.2));\n")
    before = cue_keys(tmp_path, t, {"chart_up": 1.0, "other": 3.0})
    after = cue_keys(tmp_path, t, {"chart_up": 1.0, "other": 3.2})
    assert after["s1"] == before["s1"] and after["s2"] != before["s2"]      # s2's window holds `other`
    assert cue_keys(tmp_path, t, {"chart_up": 1.1, "other": 3.0})["s1"] != before["s1"]


def test_a_named_cue_outside_the_clip_changes_its_key(tmp_path):
    """An animation started before the clip is still running in it."""
    t = make_video(tmp_path)
    (tmp_path / "scenes" / "s2.js").write_text("export default c => c.P(c.cue(\"early\"), 3)\n")
    before = cue_keys(tmp_path, t, {"early": 0.5})
    after = cue_keys(tmp_path, t, {"early": 0.8})
    assert after["s2"] != before["s2"] and after["s1"] != before["s1"]       # s1 holds it in its window
    assert cue_keys(tmp_path, t, {"early": 0.5, "unused": 0.6})["s2"] == before["s2"]


def test_a_computed_cue_name_reads_every_cue(tmp_path):
    t = make_video(tmp_path)
    for code in ("names.map(n => cue(n))", "cue(`step_${i}`)", "timeline.cues[name]", "const { cue: when } = useClip()"):
        (tmp_path / "scenes" / "kit.js").write_text(code + "\n")       # a shared module: every clip
        before = cue_keys(tmp_path, t, {"far": 3.5})
        assert cue_keys(tmp_path, t, {"far": 3.6})["s1"] != before["s1"], code


def test_the_engine_kits_read_cues_only_through_cue():
    """scene_cues scans scene code only; a kit that read timeline cues itself, or called cue() with a
    name a scene passed it, would go unseen."""
    engines = Path(render.__file__).parents[3] / "engines"
    for f in [*engines.glob("*/src/**/*"), *engines.glob("shared/**/*")]:
        if f.suffix not in clip_keys.SCENE_CODE:
            continue
        code = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), f.read_text(), flags=re.S)
        code = re.sub(r"(^|\s)//.*", r"\1", code, flags=re.M)        # the kits' own comments, not a parser
        lines = code.splitlines()
        for i, line in enumerate(lines):
            if re.search(r"\.cues\b|\[['\"]cues['\"]\]|\bcue\s*\(", line):
                # the typed code editor reads the cues data/typing.json names; scene_cues counts them
                assert any("cue: (name" in x for x in lines[max(0, i - 2):i + 1]) or f.name == "code.js", f"{f}:{i + 1}: {line.strip()}"


def test_a_formats_key_holds_that_formats_caption_lines(tmp_path):
    t = make_video(tmp_path)
    t["tracks"]["captions"][1]["wrapped"] = {"9:16": ["Two."], "1:1": ["Two."]}
    before = {f: keys_in(tmp_path, t, f) for f in ("9:16", "1:1")}
    t["tracks"]["captions"][1]["wrapped"]["9:16"] = ["Two", "lines."]
    assert keys_in(tmp_path, t, "9:16")["s2"] != before["9:16"]["s2"]
    assert keys_in(tmp_path, t, "9:16")["s1"] == before["9:16"]["s1"] and keys_in(tmp_path, t, "1:1") == before["1:1"]


def keys_in(video, t, fmt):
    return {c["id"]: clip_keys.clip_key(video, t, c["id"], "draft", fmt=fmt) for c in t["tracks"]["scene"]}


def test_editing_the_engines_shared_modules_changes_every_chapter(tmp_path, monkeypatch):
    engines = tmp_path / "engines"
    for f in ("live/src/kit.js", "shared/motion.js"):
        (engines / f).parent.mkdir(parents=True, exist_ok=True)
        (engines / f).write_text(f"// {f}\n")
    monkeypatch.setattr(clip_keys, "engine_dir", lambda name: engines / name)
    (tmp_path / "v").mkdir()
    t = make_video(tmp_path / "v")
    before = keys(tmp_path / "v", t)
    (engines / "shared" / "motion.js").write_text("// motion, edited\n")
    after = keys(tmp_path / "v", t)
    assert all(after[c] != before[c] for c in before)


def test_jsx_text_that_looks_like_a_comment_hides_no_cue(tmp_path):
    """`src/*.tsx` in JSX text or a URL once started a "comment" that blanked the cue calls after it."""
    t = make_video(tmp_path)
    for code in ("const p = ramp(t, cue('boom'));\nconst el = <Code>rm -rf build/*</Code>;\n/** a */\n",
                 "const el = <><Code>glob: src/*</Code><Dot o={ramp(t, cue('boom'))}/></>;\n/** helper */\n",
                 "const el = <p>see https://x.dev <b style={{opacity: ramp(t, cue('boom'))}}/></p>;\n"):
        (tmp_path / "scenes" / "s1.js").write_text("const { t, cue } = useClip();\n" + code)
        assert cue_keys(tmp_path, t, {"boom": 3.5})["s1"] != cue_keys(tmp_path, t, {"boom": 3.6})["s1"], code
    (tmp_path / "scenes" / "s1.js").write_text("const {t, cue} = useClip();\nconst el = <p>see https://x.dev {names.map(n => cue(n))}</p>;\n")
    assert clip_keys.scene_cues(tmp_path, "s1", {"s1", "s2"}) is None


def test_a_helper_imported_from_another_clips_file_is_read(tmp_path):
    t = make_video(tmp_path)
    (tmp_path / "scenes" / "index.js").write_text("import {S1} from './s1';\nimport {S2} from './s2';\nexport default {s1: S1, s2: S2};\n")
    (tmp_path / "scenes" / "s2.js").write_text("export const S2 = () => { const {t, cue} = useClip(); return ramp(t, cue('own')); };\n")
    assert clip_keys.scene_cues(tmp_path, "s1", {"s1", "s2"}) == set()            # the clip list imports both
    for helper in ("s2.js", "s2/parts.tsx"):
        (tmp_path / "scenes" / helper).parent.mkdir(exist_ok=True)
        (tmp_path / "scenes" / helper).write_text("export const Boom = () => { const {t, cue} = useClip(); return ramp(t, cue('boom')); };\n")
        (tmp_path / "scenes" / "s1.js").write_text(f"import {{Boom}} from './{Path(helper).with_suffix('')}';\n")
        before = cue_keys(tmp_path, t, {"boom": 3.5})["s1"]
        assert cue_keys(tmp_path, t, {"boom": 3.6})["s1"] != before, helper     # outside s1's frames
        (tmp_path / "scenes" / helper).write_text((tmp_path / "scenes" / helper).read_text().replace("ramp", "spring"))
        assert cue_keys(tmp_path, t, {"boom": 3.5})["s1"] != before, helper     # the helper's code is in the key


def test_a_computed_name_reads_other_clips_reveal_cues(tmp_path):
    t = make_video(tmp_path)
    (tmp_path / "scenes" / "s1.js").write_text("const {cue} = useClip(); cue(`reveal:s2_${n}`);\n")
    assert cue_keys(tmp_path, t, {"reveal:s2_01": 3.5})["s1"] != cue_keys(tmp_path, t, {"reveal:s2_01": 3.6})["s1"]


def test_an_asset_replaced_at_the_same_size_and_time_changes_every_key(tmp_path):
    """cp -p, rsync -a and unzip keep a file's size and time; its content is what a frame shows."""
    import os
    t = make_video(tmp_path)
    (tmp_path / "assets").mkdir()
    a = tmp_path / "assets" / "logo.png"
    a.write_bytes(b"A" * 100)
    os.utime(a, (1000, 1000))
    before = keys(tmp_path, t)
    a.write_bytes(b"B" * 100)
    os.utime(a, (1000, 1000))
    after = keys(tmp_path, t)
    assert all(after[c] != before[c] for c in before)


def test_a_new_beat_grid_re_renders_only_the_chapters_that_read_it(tmp_path):
    t = make_video(tmp_path)
    (tmp_path / "scenes" / "s2.js").write_text("const {beat} = useClip(); const x = ramp(t, beat(4));\n")
    before = keys(tmp_path, t)
    t2 = copy.deepcopy(t)
    t2["beats"] = {"bpm": 120, "beats": [0.5, 1.0, 1.5, 2.0], "downbeats": [0.5], "hits": []}
    after = keys(tmp_path, t2)
    assert after["s1"] == before["s1"] and after["s2"] != before["s2"]


def test_a_live_clip_is_keyed_on_its_webgl_backend_and_the_engines_page(tmp_path, monkeypatch):
    """A clip rendered on the GPU differs from one rendered on the CPU (2D frames too), so a backend
    switch must not reuse the other's clips; nor may an edit to the live page or its CLI (launch flags,
    the import map)."""
    t = make_video(tmp_path)
    (tmp_path / "video.json").write_text(json.dumps({"engine": "live"}))
    cpu = clip_keys.clip_key(tmp_path, t, "s1", "draft")
    (tmp_path / "video.json").write_text(json.dumps({"engine": "live", "gl": "gpu"}))
    assert clip_keys.clip_key(tmp_path, t, "s1", "draft") != cpu
    hashed = []
    real = clip_keys._hash_tree
    monkeypatch.setattr(clip_keys, "_hash_tree", lambda h, p, root=None: (hashed.append(Path(p).name), real(h, p, root)))
    clip_keys.clip_key(tmp_path, t, "s1", "draft")
    assert {"cli.mjs", "render.html", "package-lock.json"} <= set(hashed)


def test_a_render_is_estimated_from_the_cuts_before_it(tmp_path):
    # A final render took 4h54m against a guess of about two hours, and nobody knew before it began.
    # The cut says up front how long the clips it is about to render took a frame last time.
    t = make_video(tmp_path)
    assert render.estimate(tmp_path, t, "draft", ["s1"]) is None          # nothing to go on yet
    rec = {"cut": 1, "kind": "cut", "quality": "draft", "clips": [
        {"id": "s1", "key": "a", "rendered": True, "seconds": 30.0, "frames": 60},
        {"id": "s2", "key": "b", "rendered": False, "seconds": 0.0, "frames": 45}]}
    cuts.allocate(tmp_path)
    cuts.write(tmp_path, 1, rec)
    est = render.estimate(tmp_path, t, "draft", ["s1", "s2"])
    frames = sum(tl.frames(t, c)[1] for c in ("s1", "s2"))
    assert est["frames"] == frames and est["per_frame"] == 0.5 and est["seconds"] == frames * 0.5 and est["from"] == [1]
    assert render.estimate(tmp_path, t, "final", ["s1"]) is None            # another quality is another cost
