import json

import pytest

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
    (tmp_path / 'research/style-frames').mkdir()
    (tmp_path / 'research/style-frames/manifest.json').write_text(json.dumps({
        'accepted_by': 'Delegated maker', 'judgment': 'Materials and scale accepted', 'reference': 'research/reference.png',
        'frames': [{'clip': 's1', 't': 2, 'role': 'opening', 'file': 'research/style-frames/open.png'},
                   {'clip': 's2', 't': 1, 'role': 'closing', 'file': 'research/style-frames/close.png'}]}))
    (tmp_path / 'research/sound.json').write_text(json.dumps({'s1': [{'cue': 's1-press', 'event': 'finger presses a switch'}]}))
    (tmp_path / 'research/elicit.md').write_text('The long raw brief is not a chapter job.')
    (tmp_path / 'research/reviews').mkdir()
    (tmp_path / 'research/reviews/panel-1.md').write_text('# Story fact panel')
    (tmp_path / 'SCRIPT.md').write_text(SCRIPT.replace('Then the network goes quiet.', 'Then the network goes quiet. [breath 2]'))
    calls = []
    original = narration.narrate
    monkeypatch.setattr(shoot.narration, 'narrate', lambda v: (calls.append(v), original(v, estimate=True)))
    jobs = shoot.prepare(tmp_path)
    assert calls == [tmp_path.resolve()]
    assert [j['chapter'] for j in jobs] == ['s1', 's2']
    first = (tmp_path / 'research/shoot/s1.md').read_text()
    assert 's1_01' in first and '| s2_01 |' not in first
    assert '0.800' in first and 'avoid charging twice' in first
    assert '| Breath |' in first and 's: still and silent' in first
    assert '[breath' not in first
    assert 'references/taste.md' in first and '--chapter s1' in first
    assert 'Murch: leave silence' in first and 'Hold the blocked payment' in first
    assert 'style-frames/open.png' in first and 'style-frames/close.png' not in first
    assert 'finger presses a switch' in first and 's1-press' in first
    second = (tmp_path / 'research/shoot/s2.md').read_text()
    assert 'finger presses a switch' not in second and '\n[]\n' in second
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


def test_shoot_refuses_a_story_the_panel_has_not_read(tmp_path):
    (tmp_path / 'research').mkdir()
    (tmp_path / 'research/brief.md').write_text('A collector receives, stores and searches.')
    with pytest.raises(SystemExit, match='studio panel'):
        shoot.prepare(tmp_path)


def test_a_kodawari_film_needs_its_bible_and_every_chapter_job_carries_it(tmp_path, monkeypatch):
    monkeypatch.setenv('STUDIO_HOME', str(tmp_path / 'home'))
    (tmp_path / 'video.json').write_text('{"engine":"live","kodawari":true}')
    (tmp_path / 'research/reviews').mkdir(parents=True)
    (tmp_path / 'research/brief.md').write_text('Story locked by the user.')
    (tmp_path / 'research/reviews/panel-1.md').write_text('# Story fact panel')
    (tmp_path / 'SCRIPT.md').write_text(SCRIPT)
    with pytest.raises(SystemExit, match='research/kodawari/bible.md'):
        shoot.prepare(tmp_path)
    (tmp_path / 'research/kodawari').mkdir()
    (tmp_path / 'research/kodawari/bible.md').write_text('Spine: a small, kind city of workers moving real traffic.\nNever: winking mascots.')
    original = narration.narrate
    monkeypatch.setattr(shoot.narration, 'narrate', lambda v: original(v, estimate=True))
    jobs = shoot.prepare(tmp_path)
    for job in jobs:
        text = (tmp_path / f"research/shoot/{job['chapter']}.md").read_text()
        assert '## Kodawari bible' in text and 'city of workers' in text and 'winking mascots' in text


def test_a_film_without_kodawari_shoots_exactly_as_before(tmp_path, monkeypatch):
    monkeypatch.setenv('STUDIO_HOME', str(tmp_path / 'home'))
    (tmp_path / 'video.json').write_text('{"engine":"live"}')
    (tmp_path / 'research/reviews').mkdir(parents=True)
    (tmp_path / 'research/brief.md').write_text('Story locked by the user.')
    (tmp_path / 'research/reviews/panel-1.md').write_text('# Story fact panel')
    (tmp_path / 'research/kodawari').mkdir()
    (tmp_path / 'research/kodawari/bible.md').write_text('A stray bible is ignored without the flag.')
    (tmp_path / 'SCRIPT.md').write_text(SCRIPT)
    original = narration.narrate
    monkeypatch.setattr(shoot.narration, 'narrate', lambda v: original(v, estimate=True))
    jobs = shoot.prepare(tmp_path)
    assert all('Kodawari' not in (tmp_path / f"research/shoot/{j['chapter']}.md").read_text() for j in jobs)
