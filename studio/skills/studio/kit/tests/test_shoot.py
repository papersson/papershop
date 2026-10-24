import json

from studio_kit import narration, shoot
from test_narration import SCRIPT


def test_shoot_briefs_follow_real_timings_and_preserve_chapter_work(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv('STUDIO_HOME', str(tmp_path / 'home'))
    (tmp_path / 'video.json').write_text('{"engine":"live"}')
    (tmp_path / 'research').mkdir()
    (tmp_path / 'research/brief.md').write_text('We follow a retry that needs to avoid charging twice.\nStory locked by the user.')
    (tmp_path / 'research/story').mkdir()
    (tmp_path / 'research/story/s1.md').write_text('Hold the blocked payment in close-up; the click resolves it.\nMurch: leave silence before the contact so it matters.')
    (tmp_path / 'research/story/s2.md').write_text('The second chapter has a different hero moment.')
    (tmp_path / 'research/elicit.md').write_text('The long raw brief is not a chapter job.')
    (tmp_path / 'SCRIPT.md').write_text(SCRIPT)
    calls = []
    original = narration.narrate
    monkeypatch.setattr(shoot.narration, 'narrate', lambda v: (calls.append(v), original(v, estimate=True)))
    jobs = shoot.prepare(tmp_path)
    assert calls == [tmp_path.resolve()]
    assert [j['chapter'] for j in jobs] == ['s1', 's2']
    first = (tmp_path / 'research/shoot/s1.md').read_text()
    assert 's1_01' in first and '| s2_01 |' not in first
    assert '0.800' in first and 'avoid charging twice' in first
    assert 'references/taste.md' in first and '--chapter s1' in first
    assert 'Murch: leave silence' in first and 'Hold the blocked payment' in first
    assert 'different hero moment' not in first and 'long raw brief' not in first
    active = json.loads((tmp_path / 'home/.active-shoot.json').read_text())
    assert active['video'] == str(tmp_path.resolve())
    assert active['lanes']['s1']['job'] == jobs[0]['brief']
    assert jobs[0]['description'].startswith(active['lanes']['s1']['tag'])
    assert 'first tool call must be Read' in jobs[0]['prompt']
    assert active['expires'] > 0 and len(active['lanes']) == 2
    cue = tmp_path / 'cues/s1.json'
    cue.write_text('{"s1-hit": 1}')
    (tmp_path / 'data/s1/value.json').write_text('[42]')
    again = shoot.prepare(tmp_path)
    assert again[0]['brief'] != jobs[0]['brief']  # old launches cannot claim the new shoot
    assert json.loads(cue.read_text()) == {'s1-hit': 1}
    assert (tmp_path / 'data/s1/value.json').read_text() == '[42]'
