"""Prepare comparable starts for a bare agent and Studio without running either."""
import shlex
from datetime import date
from pathlib import Path

from . import new
from .env import ROOT, studio_home
from .workspace import atomic_json


def prepare(topic='shaders', today=None):
    day = studio_home() / 'ablation' / (today or date.today().isoformat())
    day.mkdir(parents=True, exist_ok=True)
    for number in range(1, 10000):
        run = day / f'{number:02}'
        try:
            run.mkdir()
            break
        except FileExistsError:
            continue
    else:
        raise SystemExit(f'No free run folder in {day}')
    bare, studio = run / 'bare', run / 'studio'
    bare.mkdir()
    new.create('studio', directory=studio, title=f'Ablation: {topic}')
    common = f'Create me a 5 min explainer on {topic.strip()}.'
    prompts = {
        'bare': common + '\nWork in this folder using your own approach. Do not use Studio, its instructions, components or assets. Record your elapsed time and leave a playable video here.\n',
        'studio': common + f'\nUse the Studio skill at {ROOT / "SKILL.md"}. This video folder is already created. Develop the story with me, then shoot after I lock it. Record stage timing and leave the playable video on the desk.\n',
    }
    commands = {}
    for name, folder in (('bare', bare), ('studio', studio)):
        (folder / 'PROMPT.md').write_text(prompts[name])
        flags = '--safe-mode --disable-slash-commands' if name == 'bare' else '--plugin-dir ' + shlex.quote(str(ROOT.parent.parent))
        commands[name] = f'cd {shlex.quote(str(folder))}\nclaude {flags} "$(cat PROMPT.md)"'
    atomic_json(run / 'comparison.json', {'topic': topic, 'minutes': 5, 'model': None, 'bare_seconds': None,
                'studio_seconds': None, 'user_notes': [], 'commands': commands})
    (run / 'README.md').write_text('''# Paired video comparison

Run both prompts with the same model and starting topic. Keep the two working folders separate.
Record wall time, active time, time spent waiting for the user and the exact model in comparison.json.
Use the same viewer and length when answering either agent's questions. Save the resulting briefs.
Watch the videos side by side and record the user's own notes on clarity, scope, breathing room,
frame occupancy, sound and the performed hero moments. Count the time the whole workflow takes.
This command prepares the comparison; it does not start either agent or claim a result.
''')
    return run, prompts, commands


def main(args):
    run, prompts, commands = prepare(args.topic)
    print(f'Ablation prepared at {run}')
    for name in prompts:
        print(f'\n{name.upper()} PROMPT\n{prompts[name]}\nCOMMAND\n{commands[name]}')
    return 0
