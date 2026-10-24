"""Chapter work must not mutate the coordinator's timeline or another chapter's files."""
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from studio_kit import chapter, timeline as tl


def video(tmp_path):
    (tmp_path / "video.json").write_text(json.dumps({"engine": "live", "clips": [
        {"id": "s1", "seconds": 3}, {"id": "s2", "seconds": 4}]}))
    (tmp_path / "cues").mkdir()
    tl.build(tmp_path)
    return tmp_path


def test_chapter_cues_merge_with_legacy_and_keep_the_frame_grid(tmp_path):
    v = video(tmp_path)
    (v / "cues.json").write_text('{"old": 0.1}')
    (v / "cues/s1.json").write_text('{"s1-hit": 1.25}')
    (v / "cues/s2.json").write_text('{"s2-hit": 4.1}')
    t = tl.build(v)
    assert t["cues"] == {"old": 0.1, "s1-hit": round(38 / 30, 6), "s2-hit": 4.1}
    assert [e["clip"] for e in tl.events(v)] == ["s1", "s1", "s2"]
    assert t["sources"][-2:] == ["cues/s1.json", "cues/s2.json"]
    (v / "cues/s2.json").write_text('{"s1-hit": 4}')
    with pytest.raises(SystemExit, match="duplicate cue"):
        tl.build(v)
    (v / "cues/s2.json").write_text('{"s2-hit": 1}')
    with pytest.raises(SystemExit, match="outside chapter"):
        tl.build(v)


def test_chapter_workspaces_build_independently_and_leave_sources_untouched(tmp_path):
    v = video(tmp_path)
    (v / "cues/s1.json").write_text('{"one": 1}')
    (v / "cues/s2.json").write_text('{"two": 4}')
    before = {p: p.read_bytes() for p in v.rglob('*') if p.is_file()}
    def work(clip):
        with chapter.working_copy(v, clip) as (path, t):
            assert set(t['cues']) == ({'one'} if clip == 's1' else {'two'})
            (path / 'video.json').write_text('{}')
            return str(path)
    with ThreadPoolExecutor(2) as pool:
        paths = list(pool.map(work, ['s1', 's2']))
    assert paths[0] != paths[1]
    assert all(p.read_bytes() == data for p, data in before.items())
    with pytest.raises(SystemExit, match='invalid chapter'):
        chapter.validate(v, '../s1')


def test_check_limits_engine_requests_to_one_chapter(tmp_path, monkeypatch):
    from studio_kit import check
    v = video(tmp_path)
    seen = []
    class Engine:
        def durations(self, clips):
            seen.extend(clips)
            return {c: tl.frames(tl.load(v), c)[1] for c in clips}
    rows = check.run(v, only=['length'], engine=Engine(), chapter='s2')
    assert seen == ['s2']
    assert all(r['clip'] == 's2' and r['ok'] for r in rows)
