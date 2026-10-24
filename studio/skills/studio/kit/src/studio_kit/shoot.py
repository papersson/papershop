"""Prepare independent chapter jobs from the story the user has locked."""
import shlex
from pathlib import Path

from . import chapter, narration, script, timeline as tl
from .env import ROOT


def prepare(video):
    video = Path(video).resolve()
    brief = video / 'research' / 'brief.md'
    if not brief.is_file():
        raise SystemExit(f'Write the agreed story to {brief} before preparing the shoot.')
    narration.narrate(video)
    timeline = tl.build(video)
    chapters = {c.id: c for c in script.read(video)}
    sections = script.sections((video / 'SCRIPT.md').read_text())
    beats = sections.get('Beats', 'The screen notes below describe this chapter’s beats.')
    out = video / 'research' / 'shoot'
    out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for c in timeline['tracks']['scene']:
        cid = chapter.validate(video, c['id'])
        (video / 'data' / cid).mkdir(parents=True, exist_ok=True)
        (video / 'cues').mkdir(exist_ok=True)
        cues = video / 'cues' / f'{cid}.json'
        if not cues.exists():
            cues.write_text('{}\n')
        commands = [f'studio check {shlex.quote(str(video))} --chapter {cid}',
                    f'studio run {shlex.quote(str(video))} data/{cid}/build.py']
        lines = [f'# Shoot {cid}: {c["title"]}', '',
                 f'This chapter occupies {c["start"]:.3f}–{c["end"]:.3f} seconds on the shared timeline.', '',
                 '## Locked story', '', brief.read_text().strip(), '',
                 '## Chapter narration', '', '| Sentence | Start | End | Words |', '|---|---:|---:|---|']
        for s in timeline['tracks']['narration']:
            if s['clip'] == cid:
                words = s.get('caption', s['text']).replace('|', '\\|')
                lines.append(f'| {s["id"]} | {s["start"]:.3f} | {s["end"]:.3f} | {words} |')
        lines += ['', '## Beats and hero moments', '', beats, '', '### Chapter screen notes', '']
        lines += [f'- {n.start}–{n.end}: {n.text}' for n in chapters[cid].screen]
        lines += ['', '## Your workspace', '',
                  f'Read {ROOT / "references/taste.md"} and {ROOT / "references/kit.md"}.', '',
                  f'Write only scenes/{cid}.js, cues/{cid}.json and data/{cid}/. Use absolute timeline seconds or narration anchors in your cues. Prefix cue names with {cid}-.',
                  'Treat every shared file as read-only. Report any needed change to the main session. Put proposed sound and typing plans in your data folder for the main session to apply.',
                  'Keep the agreed voice, story and timing. Perform the hero moment, fill the frame and leave time for it to settle.', '',
                  'Run these commands from the main session’s environment:', '', '```sh', *commands, '```', '',
                  f'The check writes frames to .cache/chapters/{cid}/. Inspect them. Return the changed paths, the check result and any shared changes needed.', '']
        path = out / f'{cid}.md'
        path.write_text('\n'.join(lines))
        jobs.append({'chapter': cid, 'brief': str(path), 'prompt': f'Read {path} and build chapter {cid}. Follow its workspace boundary. Check and inspect your frames, then report back.'})
    return jobs


def main(args):
    jobs = prepare(args.video)
    print('Use the main session’s Agent tool to start these jobs together, one agent per chapter:')
    for job in jobs:
        print(f'\n{job["chapter"]}: {job["prompt"]}')
    print('\nWhen every chapter has landed, apply the reported shared changes, rebuild the timeline and make one cut:')
    v = shlex.quote(str(args.video))
    print(f'studio timeline {v}\nstudio cut {v}\nstudio desk {v}')
    return 0
