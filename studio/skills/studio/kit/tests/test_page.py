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
