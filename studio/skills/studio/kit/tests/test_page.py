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
        post(base + "/api/round", {"cut": 1})
        st = json.loads(urllib.request.urlopen(base + "/api/state").read())
        assert [x["id"] for x in st["notes"]] == [n["id"]] and st["rounds"][0]["notes"] == [n["id"]]
        text = page.notes_text(tmp_path)
        assert "1 note, round sent" in text and "1. [0:01.2 s1_01 picture] move the card left" in text

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


def test_wait_returns_the_notes_added_after_it_started(tmp_path):
    page.append(tmp_path, {"type": "note", "id": "old", "cut": 1, "t": 0, "clip": "s1", "sentence_id": "s1_01",
                           "sentence": "One.", "kind": "picture", "note": "seen"})

    def later():
        import time
        time.sleep(0.3)
        page.append(tmp_path, {"type": "note", "id": "new", "cut": 1, "t": 2.5, "clip": "s1", "sentence_id": "s1_02",
                               "sentence": "Two.", "kind": "narration", "note": "explain the log"})
    threading.Thread(target=later).start()
    new = page.wait(tmp_path, timeout=5, poll=0.05, settle=0.1)
    assert [n["id"] for n in new] == ["new"]
    assert page.wait(tmp_path, timeout=0.2, poll=0.05) is None
    text = "\n".join(page.describe(new))
    assert "s1_02 narration] explain the log  (id new, cut 1)" in text


def test_marks_and_status_reach_the_page_and_the_stage_report(tmp_path):
    make_video(tmp_path)
    page.append(tmp_path, {"type": "note", "id": "n1", "cut": 1, "t": 1.0, "clip": "s1", "sentence_id": "s1_01",
                           "sentence": "One.", "kind": "picture", "note": "bigger"})
    from studio_kit import stage
    assert any("open note n1 on s1_01: bigger" in line for line in stage.mark(tmp_path, "scenes"))
    page.mark(tmp_path, "n1", "start")
    page.mark(tmp_path, "n1", "resolve", "the card is 20% larger")
    assert not any("open note" in line for line in stage.mark(tmp_path, "scenes"))
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
