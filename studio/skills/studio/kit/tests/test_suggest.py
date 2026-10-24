import json
import shutil
import subprocess
import threading
import time
import urllib.request

import pytest

from studio_kit import page, suggest
from studio_kit.env import engine_dir, resolve_browser
from test_page import make_video, serve


def saved_video(v):
    t = make_video(v)
    t['tracks']['scene'] = [dict(t['tracks']['scene'][0], end=4)]
    t['tracks']['narration'][1].update(id='s1_02', clip='s1')
    cut = v / 'cuts/cut1'
    cut.mkdir(parents=True)
    (cut / 'cut.json').write_text('{"cut":1,"kind":"cut"}')
    (cut / 'timeline.json').write_text(json.dumps(t))


def findings(v, rows, cut=1):
    f = v / 'findings.json'
    f.write_text(json.dumps({'cut': cut, 'chapter': 's1', 'findings': rows}))
    return f


def test_suggestions_keep_the_reviewed_sentence_until_user_accepts(tmp_path):
    saved_video(tmp_path)
    f = findings(tmp_path, [{'sentence_id': 's1_01', 'note': 'Make the subject larger.'},
                            {'t': 2.6, 'kind': 'narration', 'note': 'Define the term.'}])
    notes = suggest.import_file(tmp_path, f)
    assert len(notes) == 2 and all(n['author'] == 'review' and n['status'] == 'suggested' for n in notes)
    assert notes[0]['sentence_id'] == 's1_01' and notes[1]['sentence_id'] == 's1_02'
    assert page.wait(tmp_path, timeout=.1, poll=.01) is None
    with pytest.raises(SystemExit, match='user must accept'):
        page.mark(tmp_path, notes[0]['id'], 'start')
    server, base = serve(tmp_path)
    try:
        def accept():
            time.sleep(.1)
            req = urllib.request.Request(base + f'/api/notes/{notes[0]["id"]}/accept', data=b'{}', headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req).read()
        t = threading.Thread(target=accept)
        t.start()
        accepted = page.wait(tmp_path, timeout=2, poll=.02, settle=.01)
        t.join()
        assert [n['id'] for n in accepted] == [notes[0]['id']]
        page.mark(tmp_path, notes[1]['id'], 'dismiss')
        assert suggest.import_file(tmp_path, f) == []
        assert [n['status'] for n in page.fold(page.read_log(tmp_path))[0]] == ['queued', 'dismissed']
    finally:
        server.shutdown()
        server.server_close()


def test_invalid_finding_makes_no_partial_import(tmp_path):
    saved_video(tmp_path)
    f = findings(tmp_path, [{'t': 1, 'note': 'Valid.'}, {'t': 900, 'note': 'Outside.'}])
    with pytest.raises(SystemExit, match='absolute video seconds'):
        suggest.import_file(tmp_path, f)
    assert page.read_log(tmp_path) == []


@pytest.mark.parametrize('engine', ['remotion', 'live'])
def test_the_desk_buttons_accept_and_dismiss_suggestions(tmp_path, engine):
    """The API worked while the click delegation silently ignored both suggestion buttons."""
    playwright = engine_dir('live') / 'node_modules/playwright-core/index.mjs'
    browser = resolve_browser()[0]
    if not playwright.exists() or not browser or not shutil.which('node'):
        pytest.skip('the desk browser test needs Node, Playwright and Chrome')
    saved_video(tmp_path)
    (tmp_path / 'video.json').write_text(json.dumps({'engine': engine}))
    t = json.loads((tmp_path / 'timeline.json').read_text())
    t['timing'] = 'estimate'
    (tmp_path / 'timeline.json').write_text(json.dumps(t))
    (tmp_path / 'cuts/cut1/cut.json').write_text(json.dumps({
        'cut': 1, 'kind': 'stills', 'quality': 'draft', 'created': '',
        'stills': [], 'changelog': [], 'video': None, 'duration': 4,
    }))
    notes = suggest.import_file(tmp_path, findings(tmp_path, [
        {'sentence_id': 's1_01', 'note': 'Enlarge the subject.'},
        {'sentence_id': 's1_02', 'note': 'Add a label.'},
    ]))
    server, base = serve(tmp_path)
    script = tmp_path / 'desk.mjs'
    script.write_text('import {chromium} from ' + json.dumps(playwright.as_uri()) + ';\n' + """
const browser = await chromium.launch({executablePath: process.argv[2], headless: true});
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.route('**/live/engine/render.html*', route => route.fulfill({
    contentType: 'text/html', body: '<script>window.studio={drawAt:()=>({}),reload:async()=>{}}</script>'
  }));
  await page.goto(process.argv[3]);
  await page.locator('[data-accept]').first().click();
  await page.waitForFunction(() => document.querySelectorAll('[data-accept]').length === 1);
  await page.locator('[data-dismiss]').first().click();
  await page.waitForFunction(() => document.querySelectorAll('[data-accept]').length === 0);
  if (process.argv[4] === 'live') {
    if (await page.locator('.livewrap').count() !== 1) throw new Error('Note refresh left the live view');
    await page.locator('[data-seek]').first().click();
    await page.selectOption('#cutpick', '1');
    await page.waitForFunction(() => document.querySelectorAll('.livewrap').length === 0);
    await page.locator('[data-edit]').first().click();
    await page.fill('#fnote', 'Enlarge the subject and keep this saved version.');
    await page.click('#save');
    await page.waitForSelector('#form[hidden]', {state: 'attached'});
    if (await page.locator('.livewrap').count() !== 0) throw new Error('Note refresh left the saved version');
    if (await page.locator('#cutpick').inputValue() !== '1') throw new Error('Version selection changed');
    await page.selectOption('#cutpick', '0');
    await page.waitForSelector('.livewrap');
  }
  if (errors.length) throw new Error(errors.join('\\n'));
} finally {
  await browser.close();
}
""")
    try:
        subprocess.run(['node', str(script), browser, base, engine], check=True, timeout=90)
        current, _ = page.fold(page.read_log(tmp_path))
        assert [(n['id'], n['status'], n['sentence_id']) for n in current] == [
            (notes[0]['id'], 'queued', 's1_01'), (notes[1]['id'], 'dismissed', 's1_02')]
    finally:
        server.shutdown()
        server.server_close()
