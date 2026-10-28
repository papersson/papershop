import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer

from studio_kit import page
from test_render import make_video


def test_fold_applies_edits_and_deletes_and_filters_by_cut():
    log = [
        {"type": "note", "id": "a", "cut": 1, "note": "too fast", "kind": "picture"},
        {"type": "note", "id": "b", "cut": 1, "note": "wrong term", "kind": "narration"},
        {"type": "note", "id": "c", "cut": 2, "note": "better", "kind": "both"},
        {"type": "edit", "id": "a", "note": "too fast at the retry"},
        {"type": "delete", "id": "b"},
        {"type": "round", "cut": 1, "notes": ["a"]},
    ]
    notes, rounds = page.fold(log, cut=1)
    assert [(n["id"], n["note"]) for n in notes] == [("a", "too fast at the retry")]
    assert len(rounds) == 1


def test_page_script_is_ascii():
    page.PAGE.encode("ascii")
    assert '<meta charset="utf-8">' in page.PAGE


def serve(video):
    handler = type("H", (page.Handler,), {"video": video})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_port}"


def post(url, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())


def test_notes_round_trip_through_the_server(tmp_path):
    make_video(tmp_path)
    cut = tmp_path / "cuts" / "cut1"
    cut.mkdir(parents=True)
    (cut / "cut.json").write_text(json.dumps({"cut": 1, "stills": [], "changelog": []}))
    (cut / "video.mp4").write_bytes(bytes(range(256)) * 4)
    server, base = serve(tmp_path)
    try:
        n = post(base + "/api/notes", {"cut": 1, "t": 1.2, "clip": "s1", "sentence_id": "s1_01",
                                       "sentence": "One.", "kind": "picture", "note": "move the card left"})
        st = json.loads(urllib.request.urlopen(base + "/api/state").read())
        assert [x["id"] for x in st["notes"]] == [n["id"]] and st['rounds'] == []
        text = page.notes_text(tmp_path)
        assert "1 note; notes arrive immediately" in text and "1. [0:01.2 s1_01 picture] move the card left" in text

        req = urllib.request.Request(base + "/cut1/video.mp4", headers={"Range": "bytes=10-19"})
        r = urllib.request.urlopen(req)
        assert r.status == 206 and r.read() == bytes(range(10, 20))
        assert r.headers["Content-Range"] == "bytes 10-19/1024"
    finally:
        server.shutdown()


def test_fold_tracks_status_and_carries_open_notes_to_later_cuts():
    log = [
        {"type": "note", "id": "a", "cut": 1, "note": "slower", "kind": "picture"},
        {"type": "note", "id": "b", "cut": 1, "note": "what is a key?", "kind": "narration"},
        {"type": "start", "id": "a"},
        {"type": "resolve", "id": "a", "reply": "held 1.5 s longer"},
        {"type": "start", "id": "b"},
        {"type": "note", "id": "c", "cut": 2, "note": "nice", "kind": "both"},
    ]
    notes, _ = page.fold(log)
    assert [(n["id"], n["status"], n["reply"]) for n in notes] == [
        ("a", "done", "held 1.5 s longer"), ("b", "working", None), ("c", "queued", None)]
    # cut 2 shows its own notes plus the one still open from cut 1, not the resolved one...
    assert [n["id"] for n in page.fold(log, cut=2)[0]] == ["b", "c"]
    # ...unless it was resolved after cut 2 was made: then its reply shows on the cut that answers it
    log[3]["created"] = "2026-10-09 10:05:00"
    assert [n["id"] for n in page.fold(log, cut=2, since="2026-10-09 10:00:00")[0]] == ["a", "b", "c"]


def test_wait_recovers_queued_notes_after_a_watcher_restart(tmp_path):
    page.append(tmp_path, {"type": "note", "id": "old", "cut": 1, "t": 0, "clip": "s1", "sentence_id": "s1_01",
                           "sentence": "One.", "kind": "picture", "note": "seen"})

    assert [n['id'] for n in page.wait(tmp_path, timeout=1)] == ['old']
    assert [n['id'] for n in page.wait(tmp_path, timeout=1)] == ['old']  # read is not acknowledgement
    page.mark(tmp_path, 'old', 'start')
    def later():
        import time
        time.sleep(0.3)
        page.append(tmp_path, {"type": "note", "id": "new", "cut": 1, "t": 2.5, "clip": "s1", "sentence_id": "s1_02",
                               "sentence": "Two.", "kind": "narration", "note": "explain the log"})
    threading.Thread(target=later).start()
    new = page.wait(tmp_path, timeout=5, poll=0.05, settle=0.1)
    assert [n["id"] for n in new] == ["new"]
    page.mark(tmp_path, 'new', 'start')
    assert page.wait(tmp_path, timeout=0.2, poll=0.05) is None
    text = "\n".join(page.describe(new))
    assert "s1_02 narration] explain the log  (id new, cut 1)" in text


def test_lane_inbox_does_not_consume_another_chapters_note(tmp_path):
    page.append(tmp_path, {'type': 'note', 'id': 'a', 'lane': 's1', 'cut': 1})
    page.append(tmp_path, {'type': 'note', 'id': 'b', 'lane': 's2', 'cut': 1})
    assert [n['id'] for n in page.wait(tmp_path, timeout=1, chapter='s2')] == ['b']
    assert [n['id'] for n in page.wait(tmp_path, timeout=1, chapter='s1')] == ['a']


def test_note_writes_do_not_wait_for_a_render_lock(tmp_path):
    from studio_kit.workspace import operation
    with operation(tmp_path):
        thread = threading.Thread(target=lambda: page.append(tmp_path, {'type': 'note', 'id': 'during', 'cut': 1}))
        thread.start()
        thread.join(1)
        assert not thread.is_alive()


def test_redundant_autosave_does_not_reopen_a_resolved_note():
    log = [{'type': 'note', 'id': 'n', 'cut': 1, 'note': 'Hold', 'kind': 'picture'},
           {'type': 'resolve', 'id': 'n', 'reply': 'Held'},
           {'type': 'edit', 'id': 'n', 'note': 'Hold', 'kind': 'picture'}]
    assert page.fold(log)[0][0]['status'] == 'done'
    log.append({'type': 'edit', 'id': 'n', 'note': 'Hold longer'})
    assert page.fold(log)[0][0]['status'] == 'queued'


def test_marks_and_status_reach_the_page(tmp_path):
    make_video(tmp_path)
    page.append(tmp_path, {"type": "note", "id": "n1", "cut": 1, "t": 1.0, "clip": "s1", "sentence_id": "s1_01",
                           "sentence": "One.", "kind": "picture", "note": "bigger"})
    page.mark(tmp_path, "n1", "start")
    page.mark(tmp_path, "n1", "resolve", "the card is 20% larger")
    page.write_status(tmp_path, "rendering chapter 2", busy=True)
    st = page.state(tmp_path, 1)
    assert st["status"]["text"] == "rendering chapter 2" and st["status"]["busy"]
    assert st["notes"][0]["reply"] == "the card is 20% larger"
    import pytest
    with pytest.raises(SystemExit):
        page.mark(tmp_path, "nope", "start")


def test_events_announce_a_new_note(tmp_path):
    make_video(tmp_path)
    server, base = serve(tmp_path)
    try:
        r = urllib.request.urlopen(base + "/api/events", timeout=5)
        page.append(tmp_path, {"type": "note", "id": "e1", "cut": 1, "t": 0, "clip": "s1", "sentence_id": "s1_01",
                               "sentence": "One.", "kind": "picture", "note": "x"})
        lines = []
        while not any(line.startswith(b"event: notes") for line in lines):
            lines.append(r.readline())
        assert b"event: notes\n" in lines
    finally:
        server.shutdown()


def test_a_note_naming_a_glossary_word_points_the_builder_at_it():
    note = {"id": "g1", "cut": 1, "t": 3.0, "clip": "s1", "sentence_id": "s1_02", "sentence": "Two.", "kind": "picture",
            "note": "Stagger these and blur them together", "status": "queued"}
    text = "\n".join(page.describe([note]))
    assert "glossary: stagger, blur together" in text


def test_a_busy_port_moves_the_desk_unless_the_port_was_asked_for(tmp_path, monkeypatch):
    import socket
    import pytest
    busy = socket.socket()
    busy.bind(("127.0.0.1", 0))
    busy.listen()
    taken = busy.getsockname()[1]
    try:
        monkeypatch.setattr(page, "PORT", taken)
        server = page.bind(tmp_path)
        assert server.server_port != taken
        server.server_close()
        with pytest.raises(SystemExit, match=f"port {taken} on 127.0.0.1 is not available"):
            page.bind(tmp_path, taken)
    finally:
        busy.close()


def test_the_live_page_reloads_scenes_in_place_and_everything_else_by_reloading(tmp_path):
    """A chapter's scene file and the JSON the page fetches reload in place; a helper the scenes import
    (which a browser keeps by URL), anything under scenes/ in a folder, and the engine's own files only
    load in a fresh page, so they are watched as the page's."""
    from studio_kit.env import engine_dir
    make_video(tmp_path)
    (tmp_path / "scenes" / "s1.js").write_text("export default function draw(c) {}\n")
    (tmp_path / "scenes" / "lib").mkdir()
    (tmp_path / "scenes" / "lib" / "model.js").write_text("export const R = 300\n")
    (tmp_path / "video.json").write_text("{}")
    in_place, fresh = page.live_inputs(tmp_path)
    assert tmp_path / "scenes" / "s1.js" in in_place and tmp_path / "video.json" in in_place
    assert tmp_path / "scenes" / "lib" / "model.js" in fresh and tmp_path / "scenes" / "kit.js" in fresh
    assert engine_dir("live") / "render.html" in fresh and engine_dir("live") / "src" / "stage3d.js" in fresh
    before = page.inventory(fresh)
    (tmp_path / "scenes" / "lib" / "model.js").unlink()
    assert page.inventory([f for f in fresh if f.exists()]) != before        # a deletion changes it too


def test_the_live_page_can_read_video_json_for_the_legend(tmp_path):
    make_video(tmp_path)
    (tmp_path / "video.json").write_text(json.dumps({"legend": {"request": "warm"}}))
    server, base = serve(tmp_path)
    try:
        got = json.loads(urllib.request.urlopen(base + "/live/video/video.json", timeout=5).read())
        assert got["legend"] == {"request": "warm"}
    finally:
        server.shutdown()


def live_video(tmp_path, kind="cut"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    make_video(tmp_path)
    if kind == "animatic":
        for cid in ("s1", "s2"):
            (tmp_path / "scenes" / f"{cid}.js").unlink()
    (tmp_path / "video.json").write_text(json.dumps({"title": "t", "engine": "live"}))
    cut = tmp_path / "cuts" / "cut1"
    cut.mkdir(parents=True)
    (cut / "cut.json").write_text(json.dumps({"cut": 1, "kind": kind, "stills": [], "changelog": [], "video": "video.mp4"}))
    (cut / "video.mp4").write_bytes(b"mp4")
    return tmp_path


def test_the_story_reel_plays_and_live_scenes_follow_it(tmp_path):
    reel = page.state(live_video(tmp_path / "reel", "animatic"))
    assert reel["live"] is None and reel["cut"]["kind"] == "animatic"
    video = live_video(tmp_path / "shoot")
    assert page.state(video)["live"] is not None
    assert page.state(video, 1)["live"] is None


def test_the_live_desk_plays_the_whole_mix(tmp_path, monkeypatch):
    # The desk played the narration alone, so a builder's effects were heard only in a rendered cut.
    from studio_kit import audio
    video = live_video(tmp_path)
    mix = video / ".cache" / "sound" / "abc.m4a"
    mix.parent.mkdir(parents=True)
    mix.write_bytes(b"m4a")
    monkeypatch.setattr(audio, "soundtrack", lambda v, t: mix)
    assert page.state(video)["live"]["audio"] == ".cache/sound/abc.m4a"
    server, base = serve(video)
    try:
        assert urllib.request.urlopen(base + "/live/video/.cache/sound/abc.m4a").read() == b"m4a"
    finally:
        server.shutdown()

    def unavailable(v, t):
        raise audio.MixUnavailable("an effect's cue is gone")
    monkeypatch.setattr(audio, "soundtrack", unavailable)
    assert page.state(video)["live"]["audio"] != ".cache/sound/abc.m4a"     # the narration, as before

    def wrong_length(v, t):
        # A re-narration moved the timeline while the effects still pointed at the old one; the
        # desk's whole state failed and the page broke mid-review.
        raise RuntimeError("the soundtrack did not come out at 1149.8 s; nothing was cached")
    monkeypatch.setattr(audio, "soundtrack", wrong_length)
    assert page.state(video)["live"]["audio"] != ".cache/sound/abc.m4a"


def test_reading_notes_does_not_acknowledge_them_or_create_a_round(tmp_path):
    make_video(tmp_path)
    page.append(tmp_path, {"type": "note", "id": "a", "cut": 1, "t": 1.0, "clip": "s1", "sentence_id": "s1_01",
                           "sentence": "One.", "previous_id": None, "previous": None, "kind": "picture", "note": "x"})
    page.notes_text(tmp_path, 1)
    notes, rounds = page.fold(page.read_log(tmp_path), 1)
    assert notes[0]['status'] == 'queued' and rounds == []
    page.notes_text(tmp_path, 1)
    assert len(page.read_log(tmp_path)) == 1


def test_paused_film_pixels_survive_desk_theme_changes(tmp_path):
    """DOM boxes passed while Chromium painted a paused iframe blank. Check actual pixels."""
    import shutil
    import subprocess
    import pytest
    from PIL import Image
    from studio_kit.env import engine_dir, resolve_browser
    browser = resolve_browser()[0]
    playwright = engine_dir('live') / 'node_modules/playwright-core/index.mjs'
    if not browser or not playwright.exists() or not shutil.which('node'):
        pytest.skip('needs the installed desk browser')
    live_video(tmp_path)
    t = json.loads((tmp_path / 'timeline.json').read_text())
    t['timing'] = 'estimate'
    (tmp_path / 'timeline.json').write_text(json.dumps(t))
    (tmp_path / 'scenes/s1.js').write_text("export default c=>c.S.rect('film',0,0,c.W,c.H,{fill:'#1568c9',r:0});")
    server, base = serve(tmp_path)
    script = tmp_path / 'theme.mjs'
    script.write_text('import {chromium} from ' + json.dumps(playwright.as_uri()) + ';\n' + '''
import fs from 'node:fs';
const b=await chromium.launch({executablePath:process.argv[2],headless:true});
try {
 const p=await b.newPage({viewport:{width:1440,height:900}});
 await p.goto(process.argv[3]);
 await p.waitForFunction(()=>document.querySelector('#live').contentWindow.studioReady);
 await p.waitForTimeout(300);
 const r=await p.locator('#screen').boundingBox();
 fs.writeFileSync(process.argv[4]+'/point.json',JSON.stringify([Math.round(r.x+r.width/2),Math.round(r.y+r.height/2)]));
 for(let i=0;i<4;i++) {
  await p.locator('#theme').click();
  await p.waitForTimeout(250);
  await p.screenshot({path:process.argv[4]+'/theme-'+i+'.png'});
 }
} finally {await b.close()}
''')
    try:
        subprocess.run(['node', str(script), browser, base, str(tmp_path)], check=True, timeout=45)
        point = tuple(json.loads((tmp_path / 'point.json').read_text()))
        for i in range(4):
            assert Image.open(tmp_path / f'theme-{i}.png').convert('RGB').getpixel(point) == (21, 104, 201)
    finally:
        server.shutdown()
        server.server_close()
