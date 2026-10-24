"""Review findings enter the desk as proposals that the user can accept or dismiss."""
import hashlib
import json
import math
from pathlib import Path

from . import cuts, page
from .workspace import locked


def import_file(video, file):
    video = Path(video)
    try:
        data = json.loads(Path(file).read_text())
        n = data['cut']
        if type(n) is not int or n < 1:
            raise ValueError('cut must be a positive integer')
        rec = cuts.read(video, n)
        if not rec:
            raise ValueError(f'no cut {n}')
        timeline = json.loads((cuts.cut_dir(video, n) / 'timeline.json').read_text())
        chapter = data.get('chapter')
        chapters = timeline['tracks']['scene']
        if chapter and chapter not in {c['id'] for c in chapters}:
            raise ValueError(f'no chapter {chapter} in cut {n}')
        findings = data['findings']
        if not isinstance(findings, list):
            raise ValueError('findings must be a list')
        entries = []
        for f in findings:
            if not isinstance(f.get('note'), str) or not f['note'].strip():
                raise ValueError('each finding needs a nonempty note')
            kind = f.get('kind', 'picture')
            if kind not in ('picture', 'narration', 'both'):
                raise ValueError(f'unknown note kind {kind}')
            said = timeline['tracks']['narration']
            named = next((s for s in said if s['id'] == f.get('sentence_id')), None)
            if f.get('sentence_id') and named is None:
                raise ValueError(f'no sentence {f["sentence_id"]} in cut {n}')
            at = f.get('t', named['start'] if named else None)
            if isinstance(at, bool) or not isinstance(at, (int, float)) or not math.isfinite(at) or not 0 <= at < timeline['duration']:
                raise ValueError('each finding needs t in absolute video seconds or a sentence_id')
            clip = next((c['id'] for c in chapters if c['start'] <= at < c['end']), None)
            if not clip or (chapter and clip != chapter) or (named and named['clip'] != clip):
                raise ValueError('finding time and sentence must belong to the reviewed chapter')
            local = [s for s in said if s['clip'] == clip]
            before = [s for s in local if s['start'] <= at]
            sentence = named or (before[-1] if before else local[0] if local else None)
            previous = next((local[i - 1] for i, s in enumerate(local) if i and s is sentence), None)
            identity = json.dumps([n, clip, at, kind, f['note'].strip()], ensure_ascii=False)
            entries.append({'type': 'note', 'id': 'review_' + hashlib.sha256(identity.encode()).hexdigest()[:16],
                            'cut': n, 'clip': clip, 't': at, 'kind': kind, 'note': f['note'].strip(),
                            'sentence_id': sentence['id'] if sentence else None,
                            'sentence': sentence.get('caption', sentence['text']) if sentence else None,
                            'previous_id': previous['id'] if previous else None,
                            'previous': previous.get('caption', previous['text']) if previous else None,
                            'author': 'review', 'status': 'suggested', 'source': str(Path(file).resolve())})
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        raise SystemExit(f'Cannot import review findings: {e}')
    added = []
    # A repeated import preserves the user's acceptance or dismissal of the original suggestion.
    with locked(video, 'suggest'):
        known = {e['id'] for e in page.read_log(video) if e['type'] == 'note'}
        for entry in entries:
            if entry['id'] not in known:
                added.append(page.append(video, entry))
                known.add(entry['id'])
    return added


def main(args):
    notes = import_file(args.video, args.file)
    print(f'{len(notes)} suggested notes added to the desk. The user can accept or dismiss each one.')
    return 0
