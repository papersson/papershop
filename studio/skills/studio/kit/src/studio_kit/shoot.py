"""Prepare independent chapter jobs from the story the user has locked."""
import shlex
from pathlib import Path

from . import agent_hook, chapter, narration, script, timeline as tl
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
    active = agent_hook.activate(video, timeline['tracks']['scene'])
    jobs = []
    for c in timeline['tracks']['scene']:
        cid = chapter.validate(video, c['id'])
        (video / 'data' / cid).mkdir(parents=True, exist_ok=True)
        (video / 'cues').mkdir(exist_ok=True)
        cues = video / 'cues' / f'{cid}.json'
        if not cues.exists():
            cues.write_text('{}\n')
        scene = f"scenes/{cid}.js"
        commands = [f'studio check {shlex.quote(str(video))} --chapter {cid}',
                    f'studio run {shlex.quote(str(video))} data/{cid}/build.py']
        identity = active['lanes'][cid]
        lines = [f'# Shoot {cid}: {c["title"]}', '',
                 f'Claude Agent description: `{identity["tag"]} Build chapter {cid}`.',
                 f'Launch in the background. Your first tool call must be Read on `{identity["job"]}`. The tagged launch result or this Read joins your subagent id to the lane; subsequent scoped tool activity and stop are automatic.', '',
                 f'This chapter occupies {c["start"]:.3f}–{c["end"]:.3f} seconds on the shared timeline.', '',
                 '## Locked story', '', brief.read_text().strip(), '',
                 '## Chapter narration', '', '| Sentence | Start | End | Words |', '|---|---:|---:|---|']
        for s in timeline['tracks']['narration']:
            if s['clip'] == cid:
                words = s.get('caption', s['text']).replace('|', '\\|')
                lines.append(f'| {s["id"]} | {s["start"]:.3f} | {s["end"]:.3f} | {words} |')
        own_beats = '\n'.join(line for line in beats.splitlines() if not line.startswith('|') or line.startswith('| Chapter') or line.startswith('|---') or line.split('|')[1].strip() == cid)
        lines += ['', '## Beats and hero moments', '', own_beats, '', '### Chapter screen notes', '']
        lines += [f'- {n.start}–{n.end}: {n.text}' for n in chapters[cid].screen]
        craft = video / 'research' / 'story' / f'{cid}.md'
        if craft.is_file():
            lines += ['', '## Chapter craft', '', craft.read_text().strip()]
        lines += ['', '## Your workspace', '',
                  f'Read {ROOT / "references/taste.md"} and {ROOT / "references/kit.md"}.', '',
                  f'Write only {scene}, cues/{cid}.json and data/{cid}/. Use absolute timeline seconds or narration anchors in your cues. Prefix cue names with {cid}-.',
                  'Treat every shared file as read-only. Report any needed change to the main session. Put proposed sound and typing plans in your data folder for the main session to apply.',
                  'Keep the agreed voice, story and timing. Perform the hero moment, fill the frame and leave time for it to settle.', '',
                  f'Codex (or sessions without hooks): emit `studio event {shlex.quote(str(video))} agent.activity "plain-language action" --lane {cid}` on meaningful actions; never send fake heartbeats. Claude reports scoped tool activity automatically. Legacy Task payloads without tool-event agent ids can use explicit events for generic commands/shared-file reads; only owned paths and Studio VIDEO+CLIP commands are automatically attributable there.',
                  f'Run `studio wait {shlex.quote(str(video))} --chapter {cid} --timeout 1` between actions. It returns queued notes even after a restart. Acknowledge each with `studio notes VIDEO --start ID`, act, then `--resolve ID --reply "what changed"`. Honour control notes immediately: stop this lane (or the whole build when addressed to all), emit agent.stopped and return.',
                  f'Pin a judgment call with `studio event VIDEO decision "reason" --lane {cid} --t SECONDS`. End with `studio event VIDEO chapter.done "Checked and inspected" --lane {cid}`.', '',
                  'Run these commands from the main session’s environment:', '', '```sh', *commands, '```', '',
                  f'The check writes frames to .cache/chapters/{cid}/. Inspect them. Return the changed paths, the check result and any shared changes needed.', '']
        path = Path(identity['job'])
        path.parent.mkdir(parents=True, exist_ok=True)
        text = '\n'.join(lines)
        path.write_text(text)
        (out / f'{cid}.md').write_text(text)  # convenient latest job; the unique path binds hooks
        jobs.append({'chapter': cid, 'brief': str(path), 'description': f'{identity["tag"]} Build chapter {cid}',
                     'prompt': f'Your first tool call must be Read on {path}. Build chapter {cid}, following its workspace boundary. Check and inspect your frames, then report back.'})
    return jobs


def main(args):
    jobs = prepare(args.video)
    print('Use the main session’s Agent tool to start these jobs together, one agent per chapter:')
    for job in jobs:
        print(f'\nAgent description: {job["description"]}\nrun_in_background: true\n{job["chapter"]}: {job["prompt"]}')
    print('\nWhen every chapter has landed, apply the reported shared changes, rebuild the timeline and make one cut:')
    v = shlex.quote(str(args.video))
    print(f'studio timeline {v}\nstudio cut {v}\nstudio desk {v}')
    return 0
