import json

from studio_kit import cuts, proc, review_pack, timeline as tl
from studio_kit.workspace import atomic_json


def test_pack_combines_saved_frames_motion_and_sound_for_only_one_chapter(tmp_path):
    atomic_json(tmp_path / 'video.json', {'engine': 'live', 'clips': [{'id': 's1', 'seconds': 2}, {'id': 's2', 'seconds': 2}]})
    t = tl.build(tmp_path)
    t['cues'] = {'s1-hit': 1, 's2-hit': 3}
    n, saved = cuts.allocate(tmp_path)
    proc.ffmpeg('-f', 'lavfi', '-i', 'testsrc2=size=320x180:rate=30:duration=4',
                '-f', 'lavfi', '-i', 'sine=frequency=440:duration=4', '-c:v', 'libx264', '-preset', 'ultrafast',
                '-pix_fmt', 'yuv420p', '-c:a', 'aac', saved / 'video.mp4')
    atomic_json(saved / 'timeline.json', t)
    atomic_json(saved / 'layout.json', tl.layout(tmp_path))
    atomic_json(saved / 'cues.json', t['cues'])
    atomic_json(saved / 'sfx.json', [{'t': 's2-hit', 'time': 3, 'type': 'click', 'visual': 'land'}])
    (saved / 'SCRIPT.md').write_text('This is the saved script.')
    cuts.write(tmp_path, n, {'cut': n, 'kind': 'cut', 'quality': 'draft', 'video': 'video.mp4', 'clips': []})
    (tmp_path / 'SCRIPT.md').write_text('Later narration.')
    (tmp_path / 'cues.json').write_text('{"later":0.5}')
    out = review_pack.make(tmp_path, 's2')
    manifest = json.loads((out / 'manifest.json').read_text())
    assert manifest['frames'] and manifest['windows']
    assert all(f['clip'] == 's2' and (out / f['file']).exists() for f in manifest['frames'])
    assert all(w['clip'] == 's2' and (out / w['sheet']).exists() for w in manifest['windows'])
    hit = next(w for w in manifest['windows'] if w['name'] == 's2-hit')
    assert hit['contact_frame'] == 90 and hit['sfx'][0]['time'] == 3
    assert (out / hit['sound_sheet']).exists()
    assert (out / 'SCRIPT.md').read_text() == 'This is the saved script.'
    assert 'findings.json' in (out / 'PROMPT.md').read_text()
