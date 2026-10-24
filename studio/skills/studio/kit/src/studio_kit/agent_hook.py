"""Claude activity, explicitly joined to a shoot lane. No transcript reads or raw payload storage.

A tagged background Agent/Task result supplies the session and agent_id; on newer Claude the
child's first Read can also supply its agent_id. SubagentStart alone cannot join them: it has
no description/tool_use_id. Older tool payloads without agent_id require an exact chapter-owned
path or Studio VIDEO + CLIP command in the registered session; generic activity is dropped.
Never infer a caller from cwd, arrival order or a last-active lane.
Only this stdlib module starts on an active hook; do not import the CLI, narration or models.
"""
import json
import os
import time

MAX_RECORD = 64 * 1024
MAX_INPUT = 4 * 1024 * 1024
CALM_SECONDS = 2
TTL_SECONDS = 6 * 60 * 60


def record_path():
    return os.path.join(os.path.expanduser(os.environ.get('STUDIO_HOME', '~/studio')), '.active-shoot.json')


def read_record(path, now):
    try:
        with open(path) as f:
            raw = f.read(MAX_RECORD + 1)
        r = json.loads(raw) if len(raw) <= MAX_RECORD else None
        if (isinstance(r, dict) and r.get('version') == 1 and isinstance(r.get('lanes'), dict) and r['lanes']
                and isinstance(r.get('video'), str) and os.path.isabs(r['video'])
                and isinstance(r.get('run'), str)
                and all(isinstance(l, dict) and isinstance(l.get('tag'), str) and isinstance(l.get('job'), str)
                        for l in r['lanes'].values())
                and isinstance(r.get('expires'), (int, float)) and r['expires'] > now):
            return r
    except (OSError, ValueError):
        pass
    return None


def activate(video, chapters, now=None):
    """One active shoot per STUDIO_HOME. A fresh run invalidates previous launch tags."""
    import fcntl
    import uuid
    from pathlib import Path
    from .workspace import atomic_json
    video = Path(video).resolve()
    run = uuid.uuid4().hex[:12]
    r = {'version': 1, 'run': run, 'video': str(video),
         'expires': (time.time() if now is None else now) + TTL_SECONDS,
         'lanes': {c['id']: {'start': c['start'],
                           'tag': f'[studio:{run}:{c["id"]}]',
                           'job': str(video / 'research' / 'shoot' / run / f'{c["id"]}.md')}
                   for c in chapters}}
    path = Path(record_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path) + '.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        atomic_json(path, r)
    return r


def ident(value):
    import re
    return value if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_:.\-]{1,160}', value) else None


def input_path(body, value):
    if not isinstance(value, str) or not value or len(value) > 4096:
        return None
    return os.path.realpath(os.path.join(body.get('cwd') or '/', value))


def candidate(r, b):
    session, agent = ident(b.get('session_id')), ident(b.get('agent_id'))
    if not session:
        return None
    hook, tool = b.get('hook_event_name'), b.get('tool_name')
    inp = b.get('tool_input') if isinstance(b.get('tool_input'), dict) else {}
    if hook in ('PreToolUse', 'PostToolUse') and tool in ('Agent', 'Task'):
        desc = inp.get('description')
        tag = desc.split()[0] if isinstance(desc, str) and 0 < len(desc) <= 256 and desc.split() else None
        for cid, lane in r['lanes'].items():
            if lane['tag'] != tag or lane.get('agent') or lane.get('session') not in (None, session):
                continue
            if hook == 'PreToolUse':
                return cid
            response = b.get('tool_response')
            if (isinstance(response, dict) and response.get('status') == 'async_launched'
                    and ident(response.get('agentId')) and lane.get('session') == session
                    and lane.get('launch_tool_id') and lane['launch_tool_id'] == b.get('tool_use_id')):
                return cid
        return None
    if not agent:
        # Recorded older Task payloads omit agent_id on tools. Only an explicitly launched
        # lane's owned path or a Studio command with VIDEO + CLIP can identify that work.
        # Attribute it to the lane, not to an invented calling agent. Shared/generic tools drop.
        if hook not in ('PostToolUse', 'PostToolUseFailure'):
            return None
        matches = [cid for cid, lane in r['lanes'].items()
                   if lane.get('launch_result') and lane.get('session') == session
                   and not lane.get('done') and scoped(r, cid, b)]
        return matches[0] if len(matches) == 1 else None
    for cid, lane in r['lanes'].items():
        if lane.get('session') != session or lane.get('done'):
            continue
        if lane.get('agent') == agent:
            return cid
        if (not lane.get('agent') and hook == 'PostToolUse' and tool == 'Read'
                and input_path(b, inp.get('file_path')) == lane['job']):
            # One agent cannot claim another lane by reading its job.
            if not any(x.get('agent') == agent and x.get('session') == session for x in r['lanes'].values()):
                return cid
    return None


def scoped(r, cid, b):
    inp = b.get('tool_input') if isinstance(b.get('tool_input'), dict) else {}
    if b.get('tool_name') in ('Read', 'Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
        p = input_path(b, inp.get('file_path') or inp.get('notebook_path'))
        if p == r['lanes'][cid]['job']:
            return True
        if p:
            rel = os.path.relpath(p, r['video'])
            return (rel in (f'scenes/{cid}.js', f'cues/{cid}.json')
                    or rel.startswith(f'data/{cid}/') or rel.startswith(f'.cache/chapters/{cid}/'))
    if b.get('tool_name') == 'Bash':
        message, _ = describe(r, cid, {**b, 'hook_event_name': 'PostToolUse'})
        return message != 'running a command'
    return False


def describe(r, cid, b):
    """Extract a small allowlist of action metadata. Never store command/description/result text."""
    import math
    import shlex
    tool = b.get('tool_name')
    inp = b.get('tool_input') if isinstance(b.get('tool_input'), dict) else {}
    if b.get('hook_event_name') == 'PostToolUseFailure':
        return ('tool interrupted' if b.get('is_interrupt') else 'tool failed'), {}
    if tool in ('Read', 'Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
        p = input_path(b, inp.get('file_path') or inp.get('notebook_path'))
        if p and os.path.commonpath([p, r['video']]) == r['video']:
            rel = os.path.relpath(p, r['video'])
            if len(rel) <= 240 and all(ord(c) >= 32 for c in rel):
                if p == r['lanes'][cid]['job']:
                    return f'reading chapter {cid} brief', {'path': rel}
                return ('reading ' if tool == 'Read' else 'editing ') + rel, {'path': rel}
        return ('reading project files' if tool == 'Read' else 'editing project files'), {}
    if tool == 'Bash':
        command = inp.get('command')
        try:
            args = shlex.split(command) if isinstance(command, str) and len(command) <= 16384 else []
        except ValueError:
            args = []
        for i, word in enumerate(args[:-2]):
            if os.path.basename(word) != 'studio' or input_path(b, args[i + 2]) != r['video']:
                continue
            op, rest = args[i + 1], args[i + 3:]
            if op == 'check' and '--chapter' in rest and rest[rest.index('--chapter') + 1:][:1] == [cid]:
                return f'checking chapter {cid}', {}
            if op == 'render' and rest[:1] == [cid]:
                return f'rendering chapter {cid}', {}
            if op == 'still' and len(rest) >= 2 and rest[0] == cid:
                try:
                    t = float(rest[1]) + r['lanes'][cid]['start']
                    if math.isfinite(t) and 0 <= t < 86400:
                        return f'rendering a still at {int(t)//60}:{int(t)%60:02}', {'t': t}
                except (ValueError, TypeError):
                    pass
        return 'running a command', {}
    return {'Glob': 'finding project files', 'Grep': 'searching project files'}.get(tool, 'using a tool'), {}


def handle(body, path=None, now=None):
    import fcntl
    from pathlib import Path
    from . import events
    from .workspace import atomic_json
    path, now = path or record_path(), time.time() if now is None else now
    r = read_record(path, now)
    if not r or not isinstance(body, dict) or candidate(r, body) is None:
        return
    # All lane bindings, coalescing and appends serialize; concurrent chapters cannot lose a join.
    with open(str(path) + '.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        r = read_record(path, now)
        cid = candidate(r, body) if r else None
        if cid is None:
            return
        lane, hook = r['lanes'][cid], body.get('hook_event_name')
        if hook == 'PreToolUse':
            lane['session'] = ident(body.get('session_id'))
            lane['launch_tool_id'] = ident(body.get('tool_use_id'))
        else:
            meta = {'lane': cid, 'source': 'claude-hook', 'hook': hook,
                    'session': lane['session'], 'agent': ident(body.get('agent_id')),
                    'tool': ident(body.get('tool_name')), 'tool_use_id': ident(body.get('tool_use_id'))}
            if hook == 'PostToolUse' and body.get('tool_name') in ('Agent', 'Task'):
                lane['agent'] = ident(body['tool_response']['agentId'])
                lane['launch_result'] = True
                lane['last_activity'] = now
                events.emit(r['video'], 'agent.started', f'Chapter {cid} agent launched',
                            ts=now, **{**meta, 'agent': lane['agent'], 'association': 'launch-result'})
            elif not lane.get('agent'):
                lane['agent'] = meta['agent']
                lane['last_activity'] = now
                events.emit(r['video'], 'agent.started', f'reading chapter {cid} brief', ts=now, **meta)
            elif hook == 'SubagentStop':
                if lane.get('pending'):
                    pending = lane.pop('pending')
                    events.emit(r['video'], 'agent.activity', coalesced=lane.pop('suppressed', 0), **pending)
                stopped = lane.get('interrupted', False)
                events.emit(r['video'], 'agent.stopped' if stopped else 'chapter.done',
                            'Chapter agent stopped' if stopped else 'Chapter agent finished', ts=now, **meta)
                lane['done'] = True
            elif hook in ('PostToolUse', 'PostToolUseFailure'):
                if not meta['agent']:
                    meta['association'] = 'chapter-path'
                tool_id = meta['tool_use_id']
                if tool_id and tool_id in lane.get('seen', []):
                    return
                if tool_id:
                    lane['seen'] = (lane.get('seen', []) + [tool_id])[-32:]
                lane['interrupted'] = hook == 'PostToolUseFailure' and bool(body.get('is_interrupt'))
                message, fields = describe(r, cid, body)
                event = {'message': message, 'ts': now, **meta, **fields}
                if now - lane.get('last_activity', 0) >= CALM_SECONDS:
                    events.emit(r['video'], 'agent.activity', coalesced=lane.pop('suppressed', 0), **event)
                    lane.pop('pending', None)
                    lane['last_activity'] = now
                else:
                    lane['pending'] = event
                    lane['suppressed'] = lane.get('suppressed', 0) + 1
            else:
                return
        if all(l.get('done') for l in r['lanes'].values()):
            atomic_json(Path(r['video']) / 'research' / 'shoot' / r['run'] / 'agents.json', r)
            Path(path).unlink(missing_ok=True)
        else:
            atomic_json(path, r)


def main():
    import sys
    try:
        path, now = record_path(), time.time()
        # Expired/malformed records exit before reading even the hook payload.
        r = read_record(path, now)
        if not r:
            return
        raw = sys.stdin.buffer.read(MAX_INPUT + 1)
        body = json.loads(raw) if len(raw) <= MAX_INPUT else None
        if isinstance(body, dict) and candidate(r, body) is not None:
            handle(body, path, now)
    except (OSError, ValueError, TypeError, KeyError):
        pass  # observability is fail-open; never block a tool or print private input


if __name__ == '__main__':
    main()
