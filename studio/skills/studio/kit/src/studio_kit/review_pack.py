"""One chapter bundle combines motion, frames and sound from the same saved cut."""
import json
import re
import shutil
from pathlib import Path

from . import cuts, moments, motion_review as motion, proc
from . import timeline as tl
from .env import ROOT
from .workspace import atomic_json


def make(video, chapter, cut=None):
    video = Path(video).resolve()
    n, rec = cuts.resolve(video, cut)
    if not rec or cuts.kind(rec) not in cuts.RENDERED:
        raise SystemExit('Make a scene cut before preparing a chapter review.')
    saved = cuts.cut_dir(video, n)
    t = json.loads((saved / 'timeline.json').read_text())
    if not re.fullmatch(r'[A-Za-z0-9_-]+', chapter) or chapter not in {c['id'] for c in t['tracks']['scene']}:
        raise SystemExit(f'No chapter {chapter!r} in cut {n}.')
    out = video / 'research' / 'reviews' / f'cut{n}' / chapter
    (out / 'sheets').mkdir(parents=True, exist_ok=True)
    (out / 'frames').mkdir(exist_ok=True)
    lay = json.loads((saved / 'layout.json').read_text())
    fx, sound_source = motion.effects(video, saved, t)
    windows, dropped = motion.windows(video, n, rec, t, fx, lay, spans=(saved / "video.mp4").exists(), chapter=chapter, event_video=saved)
    for w in windows:
        movie, offset = motion.source(video, n, rec, t, chapter)
        offset -= tl.frames(t, chapter)[0]
        motion.sheet(movie, w['frames'], offset, w['contact_frame'], t['fps'], out / w['sheet'])
    motion.sound_sheets(video, n, windows, t, out, saved / 'video.mp4', rec)
    frames = []
    source = motion.source(video, n, rec, t, chapter)
    if source is None:
        raise SystemExit(f'Cut {n} has no saved picture. Make a fresh cut.')
    movie, first = source
    for i, m in enumerate(moments.stills(t, {chapter})):
        name = f'frames/{i:03}.png'
        at = (first + tl.half_up(m['t'] * t['fps'])) / t['fps']
        proc.ffmpeg('-ss', f'{at:.6f}', '-i', movie, '-frames:v', '1', out / name)
        frames.append({**m, 'file': name})
    for name in ('SCRIPT.md', 'layout.json', 'timeline.json'):
        if (saved / name).exists():
            shutil.copyfile(saved / name, out / name)
    manifest = {'cut': n, 'chapter': chapter, 'movie': str(saved / 'video.mp4'), 'frames': frames,
                'windows': windows, 'dropped': dropped, 'sound_source': sound_source}
    atomic_json(out / 'manifest.json', manifest)
    prompt = (f'Review chapter {chapter} of cut {n} once. Read manifest.json, the saved script, and {ROOT / "references/taste.md"}. '
              'Inspect the frame images and motion sheets together. Play the chapter and listen at its hero moments when a player is available. '
              'Check frame occupancy, readable labels, one meaning per colour, introduce then settle then explain, event contact and sound, '
              'pacing and continuity. State any evidence you could not inspect. Return concrete findings for the user to accept or dismiss. '
              'Do not edit the video. Write findings.json using absolute video seconds and this shape:\n\n'
              + json.dumps({'cut': n, 'chapter': chapter, 'findings': [{'t': tl.clip(t, chapter)['start'],
                  'kind': 'picture', 'note': 'Describe the observed issue and a specific proposed change.'}]}, indent=2)
              + '\n\nUse an empty findings list when you found no issues. Each finding becomes a suggested desk note.\n')
    (out / 'PROMPT.md').write_text(prompt)
    return out


def main(args):
    out = make(args.video, args.chapter, args.cut)
    print(f'Chapter review bundle: {out}\nGive its PROMPT.md to one reviewer in parallel with the other chapters.')
    return 0
