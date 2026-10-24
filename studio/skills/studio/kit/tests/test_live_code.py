"""Performed code survives seeking, folds and repeated runs in the real live renderer."""
import hashlib
import json
import subprocess

from studio_kit import codeview
from studio_kit.engine import Engine
from studio_kit.env import engine_dir
from test_live_engine import live_video, needs_engine

TYPED = {'x': {'cue': 'type-x', 'clip': 's1', 'file': 'main.c',
    'before': ['int main(void) {', '}'], 'after': ['int main(void) {', '    return 0;', '}'], 'end': 12,
    'steps': [[0, 'key', [['mode', 'INSERT'], ['ins', 1, ['    ']], ['caret', 1, 4]]],
              [4, 'key', [['set', 1, '    returm'], ['caret', 1, 10]]],
              [6, 'back', [['set', 1, '    retur'], ['caret', 1, 9]]],
              [8, 'key', [['set', 1, '    return 0;'], ['caret', 1, 13]]],
              [12, 'enter', [['mode', 'WRITTEN:main.c written'], ['caret', 1, 12], ['save']]]],
    'run': {'cmd': '$ cc main.c && ./a.out', 'up': 16, 'enter': 20, 'pop': 30, 'log': [[28, 'ok']]}}}
VIEW = {'open': [['begin', 'collapse'], ['reopen', 'end']], 'payoff': 'payoff',
        'folds': [{'lines': [1, 1], 'label': 'main()', 'to': 'payoff'}],
        'highlights': [{'lines': [2, 2], 'from': 'lit', 'to': 'collapse'}],
        'helpers': [{'id': 'main', 'title': 'Entry point', 'text': 'Returns zero.', 'from': 'collapse', 'to': 'reopen'}]}
CUES = {'type-x': .5, 'begin': 0, 'lit': 1, 'collapse': 2, 'reopen': 3, 'payoff': 4, 'end': 6}
SCENE = '''
const typing=await (await fetch(new URL('../data/typing.json',import.meta.url))).json();
const view=await (await fetch(new URL('../data/codeview.json',import.meta.url))).json();
export default function(c){const k=c.kit;
 k.Editor(c,{typing,ids:['x'],at:[-2,.5],w:8,rows:6,title:'',view});
 k.RunTerminal(c,{typing,ids:['x'],at:[5,-2],w:5,rows:3});
 k.HelperCard(c,{view,id:'main',at:[0,2],w:5});
 k.ProgramWindow(c,{typing,ids:['x'],at:[4,1],w:4,h:2,draw(id,pop,d){
  const {x,y,w,h}=d.window;c.S.rect('window pixels',x,y,w,h,{fill:'#8FD3FF',box:'window pixels'});
  c.S.group('nested',{opacity:.5},()=>c.S.text('output',x+w/2,y+h/2,'ok',{anchor:'middle'}));
 }});
}
'''


def make(tmp_path):
    t = live_video(tmp_path, SCENE)
    t['duration'] = 6
    t['tracks']['scene'] = [{**t['tracks']['scene'][0], 'end': 6}]
    t['cues'] = CUES
    (tmp_path / 'timeline.json').write_text(json.dumps(t))
    (tmp_path / 'data').mkdir()
    (tmp_path / 'data/typing.json').write_text(json.dumps(TYPED))
    (tmp_path / 'data/codeview.json').write_text(json.dumps(VIEW))
    return Engine(tmp_path)


def test_key_frames_preserve_the_wrong_buffer_correction_and_save_and_view_model(tmp_path):
    module = (engine_dir('live') / 'src/code.js').as_uri()
    script = f'''import {{editorAt,codeViewAt,runAt,windowMotion}} from {json.dumps(module)};
const typing={json.dumps(TYPED)},view={json.dumps(VIEW)},cues={json.dumps(CUES)},cue=n=>cues[n];
const at=f=>editorAt(typing,['x'],.5+f/30,cue,30);
console.log(JSON.stringify({{wrong:at(4),back:at(6),correct:at(8),saved:at(12),
 views:[.2,1.2,2.5,4.5].map(t=>{{const v=codeViewAt(typing.x.after.map(text=>({{text}})),view,t,cue);return {{...v,lit:[...v.lit]}}}}),
 run:runAt(typing,['x'],1.4,cue,30),pop:windowMotion(1.6,null,1.5)}}));'''
    r = json.loads(subprocess.check_output(['node', '--input-type=module', '-e', script], text=True))
    assert r['wrong']['lines'][1]['text'] == '    returm'
    assert r['back']['lines'][1]['text'] == '    retur'
    assert [l['text'] for l in r['correct']['lines']] == TYPED['x']['after']
    assert r['saved']['mode'] == 'WRITTEN:main.c written'
    assert r['run']['enter'] == .5 + 20 / 30 and r['pop']['scale'] > 1
    for t, actual in zip([.2, 1.2, 2.5, 4.5], r['views']):
        model = codeview.project(TYPED['x']['after'], VIEW, CUES, t)
        assert [x['text'] for x in actual['rows']] == [x['text'] for x in model]
        assert actual['lit'] == [x['n'] for x in model if x['kind'] == 'lit']
        assert actual['open'] == codeview.is_open(VIEW, CUES, t)


@needs_engine
def test_typed_editor_and_result_are_measured_and_deterministic_across_seeks(tmp_path):
    e = make(tmp_path)
    before, typing, ran, collapsed, payoff = e.boxes_at([{'clip': 's1', 't': t} for t in [.2, .7, 1.6, 2.5, 4.5]])
    names = lambda f: {b['name'] for b in f['boxes']}
    assert 'editor line 3' not in names(before)
    assert {'editor line 2', 'editor line 3', 'editor caret'} <= names(typing)
    assert {'terminal row 1', 'program window', 'output'} <= names(ran)
    assert {'editor collapsed', 'helper title', 'helper text'} <= names(collapsed)
    assert 'editor line 1' not in names(collapsed) and 'helper title' not in names(payoff)
    assert min(b['h'] for b in typing['boxes'] if b['name'].startswith('editor line ')) >= 18
    assert next(b for b in ran['boxes'] if b['name'] == 'output')['opacity'] == .5
    e.stills([{'clip': 's1', 't': t, 'out': str(tmp_path / f'{i}.png')} for i, t in enumerate([1.6, 2.5, .7, 4.5, 1.6])])
    assert hashlib.sha256((tmp_path / '0.png').read_bytes()).digest() == hashlib.sha256((tmp_path / '4.png').read_bytes()).digest()


@needs_engine
def test_recorded_panels_and_terminal_mark_their_own_accent_states(tmp_path):
    live_video(tmp_path, '''export default function(c){
 c.kit.CodePanel(c,{at:[-3,0],w:6,source:{text:'x = 1\\ny = 2\\n'},current:1,tokens:[{line:1,text:'1',progress:1}],markers:{1:'>'}});
 c.kit.Terminal(c,{at:[3,0],w:5,runs:[{argv:['run'],stdout:'',stderr:'boom\\n',exit:1}]});}''')
    boxes = Engine(tmp_path).boxes_at([{'clip': 's1', 't': 1}])[0]['boxes']
    assert {'code line 1', 'terminal row 1'} <= {b['name'] for b in boxes if b.get('means') == 'kit'}


def test_code_view_cues_invalidate_only_the_chapter_that_reads_them(tmp_path):
    from studio_kit import keys
    make(tmp_path)
    (tmp_path / 'scenes/s2.js').write_text('export default c => c.S.text("label",100,100,"other")')
    assert {'collapse', 'reopen', 'payoff', 'lit', 'type-x'} <= keys.scene_cues(tmp_path, 's1', ['s1', 's2'])
    assert keys.scene_cues(tmp_path, 's2', ['s1', 's2']) == set()
