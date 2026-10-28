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


def test_a_new_run_of_checks_clears_failures_from_older_runs(tmp_path):
    chapters = [{'id': 's4'}]
    old = events.emit(tmp_path, 'checks.ran', lane='s4', ts=1)['id']
    events.emit(tmp_path, 'check.failed', 'Code too small', lane='s4', t=580, check='legible', run=old, ts=2)
    assert events.view(tmp_path, chapters, 3)['lanes'][0]['state'] == 'failing'
    # Re-timed: the same check now passes at another second, and a run with nothing to report is clean too.
    new = events.emit(tmp_path, 'checks.ran', lane='s4', ts=4)['id']
    events.emit(tmp_path, 'check.passed', 'Clear', lane='s4', t=596, check='legible', run=new, ts=5)
    lane = events.view(tmp_path, chapters, 6)['lanes'][0]
    assert lane['state'] != 'failing' and [c['t'] for c in lane['checks']] == [596]
    events.emit(tmp_path, 'checks.ran', lane='s4', ts=7)
    assert events.view(tmp_path, chapters, 8)['lanes'][0]['checks'] == []


def test_rollout_adapter_is_idempotent_and_keeps_only_activity_metadata(tmp_path):
    import json
    f = tmp_path / 'rollout.jsonl'
    f.write_text(json.dumps({'timestamp': '2026-10-24T17:25:00Z', 'type': 'response_item',
                            'payload': {'type': 'function_call', 'name': 'exec', 'arguments': 'private text'}}) + '\n')
    assert events.import_rollout(tmp_path, f, 's2') == 1
    assert events.import_rollout(tmp_path, f, 's2') == 0
    rows = events.read(tmp_path)
    assert rows[0]['lane'] == 's2' and rows[0]['tool'] == 'exec'
    assert 'private text' not in events.path(tmp_path).read_text()


def test_new_file_after_observer_start_is_a_save_not_a_snapshot(tmp_path):
    from test_render import make_video
    make_video(tmp_path)
    observer = events.Observer(tmp_path)
    observer.poll()
    (tmp_path / 'scenes/s1.js').write_text('export default function(c) {}')
    observer.poll()
    row = [e for e in events.read(tmp_path) if e.get('path') == 'scenes/s1.js'][-1]
    assert row['kind'] == 'file.saved' and row['lane'] == 's1'
    count = len(events.read(tmp_path))
    observer.poll()
    assert len(events.read(tmp_path)) == count
