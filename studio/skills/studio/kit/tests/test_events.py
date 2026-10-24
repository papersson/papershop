from studio_kit import events


def test_liveness_and_replay_are_from_events_not_percentages(tmp_path):
    chapters = [{'id': 's1', 'start': 0, 'end': 30, 'title': 'One'}]
    events.emit(tmp_path, 'story.lock', ts=100)
    action = events.emit(tmp_path, 'agent.activity', 'Typing the line', lane='s1', ts=105)
    assert events.view(tmp_path, chapters, 134)['lanes'][0]['state'] == 'building'
    assert events.view(tmp_path, chapters, 135)['lanes'][0]['state'] == 'quiet'
    stalled = events.view(tmp_path, chapters, 225)['lanes'][0]
    assert stalled['state'] == 'stalled' and stalled['last']['id'] == action['id']
    saved = events.emit(tmp_path, 'file.saved', lane='s1', path='scenes/s1.js', ts=230)
    assert events.view(tmp_path, chapters, 229)['lanes'][0]['landed'] is False
    assert events.view(tmp_path, chapters, 230)['lanes'][0]['scene']['id'] == saved['id']
    events.emit(tmp_path, 'version.ready', version=1, ts=743)
    before = events.view(tmp_path, chapters, 200)
    assert before['eta'] == 543 and before['guess'] is True
    assert events.view(tmp_path, chapters, 800)['lanes'][0]['state'] == 'built'


def test_failed_check_keeps_its_second_and_resolves_in_place(tmp_path):
    chapters = [{'id': 's1'}]
    events.emit(tmp_path, 'check.failed', 'Caption collision', lane='s1', t=132, check='band', ts=1)
    assert events.view(tmp_path, chapters, 2)['lanes'][0]['state'] == 'failing'
    events.emit(tmp_path, 'check.passed', 'Clear', lane='s1', t=132, check='band', ts=3)
    lane = events.view(tmp_path, chapters, 4)['lanes'][0]
    assert len(lane['checks']) == 1 and lane['checks'][0]['t'] == 132
    assert lane['checks'][0]['kind'] == 'check.passed'
