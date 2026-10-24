import json
import threading
import time
import urllib.request

import pytest

from studio_kit import page, suggest
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
