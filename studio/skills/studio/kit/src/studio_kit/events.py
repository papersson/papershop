"""Small, append-only production facts. No inferred progress or private transcript text.

Agents and hooks can append events; the desk observes actual saved files. Each displayed
mark retains its event id and source. Replay uses the original wall clock at a chosen speed.
"""
import hashlib
import json
import time
import uuid
from pathlib import Path

from .workspace import locked


def path(video):
    return Path(video) / 'review' / 'events.jsonl'


def read(video):
    f = path(video)
    rows = []
    for i, line in enumerate(f.read_text().splitlines() if f.exists() else []):
        try:
            e = json.loads(line)
            e.setdefault('id', f'recorded-{i}')
            e.setdefault('source', 'agent')
            rows.append(e)
        except ValueError:  # an interrupted final append is not a lost whole log
            continue
    return sorted(rows, key=lambda e: e.get('ts', 0))


def emit(video, kind, message='', **fields):
    e = {'id': uuid.uuid4().hex[:12], 'ts': time.time(), 'kind': kind,
         'message': message, 'source': 'studio', **{k: v for k, v in fields.items() if v is not None}}
    f = path(video)
    f.parent.mkdir(parents=True, exist_ok=True)
    with locked(video, 'events'), f.open('a') as out:
        out.write(json.dumps(e, ensure_ascii=False) + '\n')
    return e


def import_rollout(video, source, lane):
    """Explicitly scoped Codex activity adapter. Never retain prompts, reasoning, arguments,
    output, account metadata or unrelated sessions. Stable ids make repeated reads safe."""
    from datetime import datetime
    source = Path(source).resolve()
    known = {e['id'] for e in read(video)}
    count = 0
    for i, line in enumerate(source.read_text().splitlines()):
        try:
            row = json.loads(line)
            p = row.get('payload', {})
            kind, message = None, None
            if row.get('type') == 'session_meta':
                kind, message = 'agent.started', 'Starting the chapter'
            elif row.get('type') == 'response_item' and p.get('type') in ('function_call', 'custom_tool_call'):
                kind, message = 'agent.tool', 'Working on the chapter'
            elif row.get('type') == 'event_msg' and p.get('type') == 'task_complete':
                kind, message = 'chapter.done', 'Chapter agent finished'
            if not kind:
                continue
            ident = hashlib.sha256(f'{source}:{i}'.encode()).hexdigest()[:12]
            if ident in known:
                continue
            emit(video, kind, message, id=ident, ts=datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00')).timestamp(),
                 lane=lane, source=f'{source}:{i+1}', tool=p.get('name') if kind == 'agent.tool' else None)
            count += 1
        except (ValueError, KeyError):
            continue
    return count


class Observer:
    """Watch project evidence, never the agent's unrelated sessions. Initial files are observations,
    not fabricated save times. Subsequent saves arrive within one desk polling interval."""
    patterns = ('scenes/*.js', 'cues/*.json', 'data/*/activity.jsonl',
                '.cache/chapters/*/check.json', '.cache/chapters/*/frame-*.png',
                'cuts/*/cut.json', 'research/timing.jsonl', 'audio/timings.json')

    def __init__(self, video):
        self.video, self.seen, self.started = Path(video), {}, False

    def poll(self):
        from . import timeline
        try:
            chapters = {c['id']: c for c in timeline.load(self.video)['tracks']['scene']}
        except (OSError, ValueError, KeyError, SystemExit):
            chapters = {}
        for pattern in self.patterns:
            for f in sorted(self.video.glob(pattern)):
                try:
                    st = f.stat()
                    stamp = (st.st_mtime_ns, st.st_size)
                    if self.seen.get(f) == stamp:
                        continue
                    initial = not self.started
                    self.seen[f] = stamp
                    rel = str(f.relative_to(self.video))
                    lane = f.stem if f.parent.name in ('scenes', 'cues') else f.parent.name
                    lane = lane if lane in chapters else None
                    kind = 'file.observed' if initial else 'file.saved'
                    label = ('Picture saved' if f.parent.name == 'scenes' else 'Chapter cues saved' if f.parent.name == 'cues'
                             else 'Preview updated' if f.suffix == '.png' else 'Checks saved' if f.name == 'check.json'
                             else 'Version saved' if f.name == 'cut.json' else 'Timing saved' if f.name == 'timing.jsonl'
                             else 'Chapter activity updated')
                    e = emit(self.video, kind, label if not initial else 'Existing ' + label.lower(),
                             lane=lane, path=rel, sha256=hashlib.sha256(f.read_bytes()).hexdigest(), source='file-watch')
                    if f.name == 'check.json' and not initial:
                        for row in json.loads(f.read_text()):
                            if row.get('t') is not None:
                                emit(self.video, 'check.passed' if row.get('ok') else 'check.failed', row.get('detail', ''),
                                     lane=lane, t=chapters.get(lane, {}).get('start', 0) + row['t'],
                                     check=row.get('check'), source=rel, evidence=e['id'], run=e['id'])
                except (OSError, ValueError):
                    continue
        self.started = True


def view(video, chapters, at=None):
    rows = read(video)
    now = time.time() if at is None else at
    events = [e for e in rows if e.get('ts', 0) <= now]
    locks = [e for e in events if e['kind'] == 'story.lock']
    start = locks[-1]['ts'] if locks else None
    active = [e for e in events if start is None or e['ts'] >= start]
    ready = next((e for e in reversed(active) if e['kind'] == 'version.ready'), None)
    rendering = next((e for e in reversed(active) if e['kind'] == 'render.started'), None)
    if rendering and ready and rendering['ts'] > ready['ts']:
        ready = None
    lanes = []
    for c in chapters:
        own = [e for e in active if e.get('lane') == c['id']]
        actions = [e for e in own if e['kind'] != 'file.observed']
        last = actions[-1] if actions else None
        scene = next((e for e in reversed(own) if e.get('path') == f'scenes/{c["id"]}.js'), None)
        done = next((e for e in reversed(own) if e['kind'] == 'chapter.done'), None)
        age = max(0, now - (last['ts'] if last else start or now))
        # A run of the chapter's checks replaces every earlier result: a re-timed chapter moves its
        # checks to new seconds, so a failure from an older run would otherwise never clear.
        ran = [e for e in own if e['kind'] in ('checks.ran', 'check.failed', 'check.passed')]
        run = ran[-1].get('run', ran[-1]['id'] if ran[-1]['kind'] == 'checks.ran' else None) if ran else None
        checks = {}
        for e in own:
            if e['kind'] in ('check.failed', 'check.passed') and (run is None or e.get('run') == run):
                checks[(e.get('check'), e.get('t'))] = e
        failing = any(e['kind'] == 'check.failed' for e in checks.values())
        lifecycle = [e for e in own if e['kind'] in ('agent.activity', 'agent.started', 'agent.stopped')]
        stopped = lifecycle and lifecycle[-1]['kind'] == 'agent.stopped'
        state = ('stopped' if stopped else 'failing' if failing else 'built' if ready or done else
                 'stalled' if age >= 120 else 'quiet' if age >= 30 else 'building' if own or start else 'board')
        lanes.append({**c, 'state': state, 'age': age, 'last': last, 'scene': scene,
                      'events': own, 'checks': list(checks.values()), 'landed': bool(scene)})
    # Only completed lock -> first-ready intervals are a timing basis. Later final versions
    # are not additional samples. A single run remains explicitly a guess.
    samples, opened = [], None
    for e in rows:
        if e['kind'] == 'story.lock':
            opened = e['ts']
        elif e['kind'] == 'version.ready' and opened is not None:
            samples.append(e['ts'] - opened)
            opened = None
    estimate = sum(samples) / len(samples) if samples else None
    return {'now': now, 'start': start, 'ready': ready, 'lanes': lanes,
            'eta': max(0, start + estimate - now) if start and estimate and not ready else None,
            'estimate': estimate, 'samples': len(samples), 'guess': len(samples) < 3,
            'pins': [e for e in active if e['kind'] == 'decision'],
            'events': events, 'range': [rows[0]['ts'], rows[-1]['ts']] if rows else None}


def main(args):
    if getattr(args, 'rollout', None):
        if not args.lane:
            raise SystemExit('--rollout needs an explicit --lane; never infer it from private text')
        while True:
            count = import_rollout(args.video, args.rollout, args.lane)
            if count:
                print(f'{count} activity records imported', flush=True)
            if not args.follow:
                return 0
            time.sleep(0.5)
    fields = {k: getattr(args, k, None) for k in ('lane', 't', 'source', 'check')}
    message = ' '.join(args.message)
    if args.hook:
        import sys
        body = json.load(sys.stdin)
        fields.update(source='claude-hook', hook=body.get('hook_event_name'),
                      session=body.get('session_id'), tool=body.get('tool_name'),
                      agent=body.get('agent_id'), agent_type=body.get('agent_type'))
        message = message or 'Agent activity'
    print(json.dumps(emit(args.video, args.kind, message, **fields)))
