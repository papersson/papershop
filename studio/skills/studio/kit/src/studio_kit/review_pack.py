"""One chapter bundle combines motion, frames and sound from the same saved cut.

It carries two briefs. PROMPT.md is the combined review. ATTENTION.md is for a second reader who
looks at one thing only: where the viewer's eye is at each moment, and what the order of the
picture would teach that is not true."""
import json
import re
import shutil
from pathlib import Path

from . import cuts, moments, motion_review as motion, proc
from . import timeline as tl
from .env import ROOT
from .workspace import atomic_json


def shape(n, chapter, start, note):
    """The findings file both reviewers write, which `studio suggest` imports."""
    return json.dumps({'cut': n, 'chapter': chapter, 'findings': [{'t': start, 'kind': 'picture', 'note': note}]}, indent=2)


def attention(n, chapter, start):
    """The attention reviewer's brief. The combined reviewer has ten things to check; on the TCP film
    nobody was looking only at where the eye goes, and the director caught every such fault himself."""
    return (
        f'Review chapter {chapter} of cut {n} once, for the viewer\'s attention only. Another reviewer covers beauty, terms, sound '
        f'and pacing, so leave those. Read manifest.json, the saved script, and the paragraph on one place to look in {ROOT / "references/taste.md"}. '
        'Go through the motion sheets in time order, with the frame stills between them. A sheet shows a few frames of a move: '
        'when they are too far apart to tell whether two changes overlap, take more frames from the movie named in the manifest, '
        'or say that you could not tell.\n\n'
        'For each motion window, answer these in order.\n\n'
        '1. The place. Where on the frame should the viewer be looking, and what sends the eye there: the only thing moving, the brightest mark, '
        'a label arriving, the word being said?\n'
        '2. The rivals. What else changes during the window, and where? A change in a second place while the first is being read is a finding, '
        'unless both are one idea in one place: a group leaving together, one shape becoming another, the camera following its subject.\n'
        '3. The consequence. When a change causes another somewhere else (a counter, a buffer, a label, a second panel), does the second wait '
        'until the first has finished, is the eye led across, and does the first place stay still while the second changes?\n'
        '4. The absence. When the point is something that did not happen (a reply that never came, a slot left empty), is the absence drawn '
        'and given its own beat, or does it only fail to appear?\n'
        '5. The wrong conclusion. What would a viewer who knows nothing of the subject conclude from the order, grouping and spacing of what '
        'was shown that is not true of it? Showing events one at a time can teach that they take turns. Name the conclusion, the picture '
        'that suggests it, and whether the narration or a later replay at true pace corrects it.\n'
        '6. The hold. Where the picture is still, is there one thing left to read? Stillness after a point has landed is a rest; '
        'stillness with nothing to read is dead time.\n\n'
        'Report only what you saw in the frames, with the frame or second it is on. Propose one specific change for each finding: '
        'what should wait, dim, hold still or get its own beat. Do not ask for a hold after every small change; the rule is about '
        'where the eye is, and the voice may carry on across a second beat. State any evidence you could not inspect. '
        'Do not edit the video. Write attention.json using absolute video seconds, and begin every note with "Attention:" '
        'so the user can tell these notes from the combined review on the desk. Use this shape:\n\n'
        + shape(n, chapter, start, 'Attention: describe what competes or misleads, and the specific change proposed.')
        + '\n\nUse an empty findings list when the eye always had one place to go and nothing misled. Each finding becomes a suggested desk note.\n')


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
              'pacing and continuity. Check that each technical term is used the way the field\'s real tools use it, or that the narration names the simplification, '
              'and that the system\'s whole path is stated plainly somewhere. A second reviewer reads ATTENTION.md and reports where the eye goes '
              'and what the order of the picture would wrongly teach, so leave those to them. '
              'State any evidence you could not inspect. Return concrete findings for the user to accept or dismiss. '
              'Do not edit the video. Write findings.json using absolute video seconds and this shape:\n\n'
              + shape(n, chapter, tl.clip(t, chapter)['start'], 'Describe the observed issue and a specific proposed change.')
              + '\n\nUse an empty findings list when you found no issues. Each finding becomes a suggested desk note.\n')
    (out / 'PROMPT.md').write_text(prompt)
    (out / 'ATTENTION.md').write_text(attention(n, chapter, tl.clip(t, chapter)['start']))
    return out


def main(args):
    out = make(args.video, args.chapter, args.cut)
    print(f'Chapter review bundle: {out}\nGive its PROMPT.md to one reviewer and its ATTENTION.md to a second, in parallel with the other chapters.')
    return 0
