import json
import os
import shlex
import subprocess
import threading
from pathlib import Path

import pytest

from studio_kit import agent_hook as hook, events
from studio_kit.env import ROOT


@pytest.fixture
def shoot(tmp_path, monkeypatch):
    home, video = tmp_path / 'home', tmp_path / 'a video'
    video.mkdir()
    (video / 'video.json').write_text('{}')
    monkeypatch.setenv('STUDIO_HOME', str(home))
    r = hook.activate(video, [{'id': 's1', 'start': 0}, {'id': 's2', 'start': 42}], now=1000)
    return video, Path(hook.record_path()), r


def payload(event, agent=None, tool=None, data=None, session='parent', **extra):
    return {'hook_event_name': event, 'session_id': session, 'agent_id': agent,
            'tool_name': tool, 'tool_input': data or {}, 'cwd': '/',
            'transcript_path': '/never/open/private.jsonl', **extra}


def launch(r, cid, agent, now=1001):
    hook.handle(payload('PreToolUse', tool='Agent', data={
        'description': r['lanes'][cid]['tag'] + ' Build chapter', 'prompt': 'SECRET prompt'}), now=now)
    hook.handle(payload('SubagentStart', agent=agent, agent_type='general-purpose'), now=now)
    hook.handle(payload('PostToolUse', agent, 'Read', {'file_path': r['lanes'][cid]['job']},
                        tool_response='SECRET contents'), now=now)


def test_parallel_agents_join_only_by_tagged_session_and_unique_job(shoot):
    video, path, r = shoot
    for cid in ['s1', 's2']:
        hook.handle(payload('PreToolUse', tool='Agent', data={'description': r['lanes'][cid]['tag']}), now=1001)
    # Starts arrive in reverse order and carry no lane information. Never guess from order/type.
    for aid in ['b', 'unrelated', 'a']:
        hook.handle(payload('SubagentStart', aid, agent_type='general-purpose'), now=1001)
    assert events.read(video) == []
    for cid, aid in [('s2', 'b'), ('s1', 'a')]:
        hook.handle(payload('PostToolUse', aid, 'Read', {'file_path': r['lanes'][cid]['job']}), now=1002)
    saved = json.loads(path.read_text())
    assert saved['lanes']['s1']['agent'] == 'a'
    assert saved['lanes']['s2']['agent'] == 'b'
    before = path.read_bytes(), events.path(video).read_bytes()
    for aid, sid in [('unrelated', 'parent'), ('a', 'other'), (None, 'parent')]:
        hook.handle(payload('PostToolUse', aid, 'Write', {'file_path': str(video / 'scenes/s1.js')}, session=sid), now=1006)
    # Bound s1 agent cannot steal s2, even knowing the correct file path.
    hook.handle(payload('PostToolUse', 'a', 'Read', {'file_path': r['lanes']['s2']['job']}, session='other'), now=1006)
    assert (path.read_bytes(), events.path(video).read_bytes()) == before
    assert [(e['lane'], e['agent']) for e in events.read(video)] == [('s2', 'b'), ('s1', 'a')]


def test_activity_is_readable_private_and_coalesced_with_a_final_flush(shoot):
    video, path, r = shoot
    launch(r, 's2', 'b')
    hook.handle(payload('PostToolUse', 'b', 'Write', {'file_path': str(video / 'scenes/s2.js'), 'content': 'SECRET file'}, tool_use_id='write1', tool_response='SECRET result'), now=1003)
    hook.handle(payload('PostToolUse', 'b', 'Bash', {'command': 'echo SECRET'}, tool_use_id='bash1'), now=1003.1)
    cmd = f'studio check {shlex.quote(str(video))} --chapter s2'
    hook.handle(payload('PostToolUse', 'b', 'Bash', {'command': cmd}, tool_use_id='check1'), now=1003.2)
    hook.handle(payload('PostToolUse', 'b', 'Bash', {'command': cmd}, tool_use_id='check1'), now=1003.3)
    assert len(events.read(video)) == 2
    hook.handle(payload('SubagentStop', 'b', last_assistant_message='SECRET reasoning'), now=1003.4)
    rows = events.read(video)
    assert [e['message'] for e in rows] == ['reading chapter s2 brief', 'editing scenes/s2.js', 'checking chapter s2', 'Chapter agent finished']
    assert rows[2]['coalesced'] == 2 and rows[2]['ts'] == 1003.2
    assert rows[-1]['kind'] == 'chapter.done'
    assert 'SECRET' not in path.read_text() + events.path(video).read_text()
    assert '/never/open' not in path.read_text() + events.path(video).read_text()


def test_still_uses_absolute_video_time_and_external_paths_are_not_kept(shoot):
    video, path, r = shoot
    launch(r, 's2', 'b')
    hook.handle(payload('PostToolUse', 'b', 'Bash', {'command': f'/kit/bin/studio still {shlex.quote(str(video))} s2 30 --out /private/x.png'}), now=1003)
    row = events.read(video)[-1]
    assert row['message'] == 'rendering a still at 1:12' and row['t'] == 72
    hook.handle(payload('PostToolUse', 'b', 'Read', {'file_path': '/private/SECRET'}), now=1005)
    assert events.read(video)[-1]['message'] == 'reading project files'
    assert 'SECRET' not in events.path(video).read_text()


def test_interrupted_stop_archives_bindings_and_removes_gate(shoot):
    video, path, r = shoot
    for cid, aid in [('s1', 'a'), ('s2', 'b')]:
        launch(r, cid, aid)
    hook.handle(payload('SubagentStop', 'a'), now=1002)
    assert path.exists()
    hook.handle(payload('PostToolUseFailure', 'b', 'Bash', is_interrupt=True, error='SECRET error'), now=1003)
    hook.handle(payload('SubagentStop', 'b', last_assistant_message='SECRET stop'), now=1004)
    assert not path.exists()
    archived = video / 'research/shoot' / r['run'] / 'agents.json'
    assert json.loads(archived.read_text())['lanes']['s2']['agent'] == 'b'
    assert events.read(video)[-1]['kind'] == 'agent.stopped'
    view = events.view(video, [{'id': 's1'}, {'id': 's2'}], at=1100)
    assert [l['state'] for l in view['lanes']] == ['built', 'stopped']
    assert 'SECRET' not in archived.read_text() + events.path(video).read_text()


def test_old_launches_cannot_attach_to_a_new_shoot(shoot):
    video, path, old = shoot
    launch(old, 's1', 'old-agent')
    fresh = hook.activate(video, [{'id': 's1', 'start': 0}], now=1002)
    before = path.read_bytes(), events.path(video).read_bytes()
    launch(old, 's1', 'stale-agent', now=1003)
    assert (path.read_bytes(), events.path(video).read_bytes()) == before
    assert fresh['run'] != old['run']


def test_concurrent_lane_updates_do_not_lose_bindings(shoot):
    video, path, r = shoot
    threads = [threading.Thread(target=launch, args=(r, cid, aid)) for cid, aid in [('s1', 'a'), ('s2', 'b')]]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert {lane.get('agent') for lane in json.loads(path.read_text())['lanes'].values()} == {'a', 'b'}
    assert len(events.read(video)) == 2


@pytest.mark.parametrize('record', [None, '{}', '{bad', '{"version":1,"lanes":{},"expires":1}'])
def test_noop_exits_without_reading_stdin_or_starting_the_kit(tmp_path, record):
    if record is not None:
        (tmp_path / '.active-shoot.json').write_text(record)
    command = ROOT.parents[1] / 'hooks/activity.sh'
    env = {**os.environ, 'STUDIO_HOME': str(tmp_path), 'HF_HUB_OFFLINE': '1'}
    # Leave stdin open. An inactive hook must not wait for a payload at all.
    p = subprocess.Popen([str(command)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    try:
        assert p.wait(timeout=3) == 0
        assert p.stdout.read() == p.stderr.read() == b''
        assert not (tmp_path / '.active-shoot.json.lock').exists()
    finally:
        p.stdin.close()
        if p.poll() is None:
            p.kill()
            p.wait()


def test_plugin_declares_completion_and_tool_hooks():
    manifest = json.loads((ROOT.parents[1] / 'hooks/hooks.json').read_text())['hooks']
    assert {'PreToolUse', 'PostToolUse', 'PostToolUseFailure', 'SubagentStop'} <= manifest.keys()
    assert manifest['PreToolUse'][0]['matcher'] == 'Agent|Task'
    assert all('${CLAUDE_PLUGIN_ROOT}' in entry['hooks'][0]['command'] for entries in manifest.values() for entry in entries)


def test_recorded_legacy_payloads_fill_the_lane_without_inventing_a_caller(shoot):
    video, path, _ = shoot
    r = hook.activate(video, [{'id': 's1', 'start': 0}], now=1000)
    fixture = json.loads((Path(__file__).parent / 'fixtures/claude-hooks-recorded.json').read_text())
    for i, row in enumerate(fixture['payloads']):
        raw = json.dumps(row).replace('VIDEO/JOB', r['lanes']['s1']['job']).replace('VIDEO', str(video)).replace('TAG', r['lanes']['s1']['tag'])
        b = json.loads(raw)
        b['last_assistant_message'] = 'SECRET answer'
        b.setdefault('tool_input', {})['content'] = 'SECRET file contents'
        hook.handle(b, now=1001 + i * 3)
    rows = events.read(video)
    assert rows[0]['association'] == 'launch-result' and rows[0]['agent'] == 'agent-probe'
    edits = [e for e in rows if e['message'] == 'editing data/s1/probe.txt']
    assert len(edits) == 1 and edits[0]['association'] == 'chapter-path' and 'agent' not in edits[0]
    assert not any(e.get('tool') == 'Bash' for e in rows)  # generic sleep has no lane evidence
    assert rows[-1]['kind'] == 'chapter.done' and rows[-1]['agent'] == 'agent-probe'
    assert not path.exists()
    assert 'SECRET' not in events.path(video).read_text()


def test_legacy_path_scope_still_rejects_other_sessions_shared_files_and_symlinks(shoot):
    video, path, r = shoot
    b = payload('PreToolUse', tool='Task', data={'description': r['lanes']['s1']['tag']}, tool_use_id='launch1')
    hook.handle(b, now=1001)
    # A response for a different tool call cannot claim this lane.
    post = {**b, 'hook_event_name': 'PostToolUse', 'tool_response': {'agentId': 'a', 'status': 'async_launched'}}
    hook.handle({**post, 'tool_use_id': 'wrong'}, now=1002)
    assert events.read(video) == []
    hook.handle(post, now=1002)
    (video / 'data/s1').mkdir(parents=True)
    (video / 'data/s1/private').symlink_to(video.parent / 'outside')
    before = path.read_bytes(), events.path(video).read_bytes()
    for file, session in [('data/s1/file.txt', 'unrelated'), ('SCRIPT.md', 'parent'), ('data/s1/private', 'parent'), ('data/s2/file.txt', 'parent')]:
        hook.handle(payload('PostToolUse', tool='Read', data={'file_path': str(video / file)}, session=session), now=1005)
    assert (path.read_bytes(), events.path(video).read_bytes()) == before
    hook.handle(payload('PostToolUse', tool='Bash', data={'command': f'studio check {shlex.quote(str(video))} --chapter s1 --only bounds,band'}), now=1006)
    assert events.read(video)[-1]['message'] == 'checking chapter s1'
    assert 'agent' not in events.read(video)[-1]
