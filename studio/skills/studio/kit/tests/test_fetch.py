import hashlib
import http.server
import io
import socket
import threading

import pytest

from studio_kit import fetch


def digest(data):
    return hashlib.sha256(data).hexdigest()


def served(tmp_path, name, data):
    src = tmp_path / "remote" / name
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_bytes(data)
    return src.as_uri()


def test_a_download_is_verified_and_renamed_into_place(tmp_path):
    url = served(tmp_path, "pack.zip", b"pinned bytes")
    dest = tmp_path / "cache" / "pack.zip"
    out = io.StringIO()
    assert fetch.fetch(url, dest, digest(b"pinned bytes"), size=12, progress=out) == dest
    assert dest.read_bytes() == b"pinned bytes" and "fetching" in out.getvalue()
    assert [p.name for p in dest.parent.iterdir()] == ["pack.zip"]          # no partial file left beside it


def test_a_cached_file_that_matches_is_not_fetched_again(tmp_path):
    dest = tmp_path / "pack.zip"
    dest.write_bytes(b"already here")
    assert fetch.fetch((tmp_path / "nowhere.zip").as_uri(), dest, digest(b"already here"), progress=None) == dest


def test_a_mismatch_deletes_the_download_and_names_both_digests(tmp_path):
    url = served(tmp_path, "pack.zip", b"changed upstream")
    dest = tmp_path / "cache" / "pack.zip"
    want = digest(b"what was reviewed")
    with pytest.raises(fetch.FetchError) as e:
        fetch.fetch(url, dest, want, progress=None)
    msg = str(e.value)
    assert url in msg and want in msg and digest(b"changed upstream") in msg
    assert not dest.exists() and list(dest.parent.iterdir()) == []


def test_a_wrong_cached_file_is_replaced(tmp_path):
    url = served(tmp_path, "pack.zip", b"good")
    dest = tmp_path / "pack.zip"
    dest.write_bytes(b"tampered")
    fetch.fetch(url, dest, digest(b"good"), progress=io.StringIO())
    assert dest.read_bytes() == b"good"


def test_a_size_that_differs_from_the_manifest_is_refused(tmp_path):
    url = served(tmp_path, "pack.zip", b"good")
    with pytest.raises(fetch.FetchError, match="manifest says 5"):
        fetch.fetch(url, tmp_path / "out.zip", digest(b"good"), size=5, progress=None)
    assert not (tmp_path / "out.zip").exists()


def test_an_unreachable_host_is_offline_not_a_crash(tmp_path):
    with socket.socket() as s:                   # a port nothing listens on
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    with pytest.raises(fetch.Offline, match="could not reach"):
        fetch.fetch(f"http://127.0.0.1:{port}/pack.zip", tmp_path / "p.zip", "0" * 64, timeout=5, progress=None)
    assert list(tmp_path.iterdir()) == []


def test_over_http_with_a_progress_line(tmp_path):
    data = b"x" * 200_000
    served(tmp_path, "pack.zip", data)
    root = tmp_path / "remote"

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(root), **kw)

        def log_message(self, *a):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        out = io.StringIO()
        url = f"http://127.0.0.1:{server.server_address[1]}/pack.zip"
        fetch.fetch(url, tmp_path / "got.zip", digest(data), size=len(data), progress=out)
        assert "(100%)" in out.getvalue() and (tmp_path / "got.zip").read_bytes() == data
        with pytest.raises(fetch.FetchError, match="HTTP 404"):
            fetch.fetch(url.replace("pack", "gone"), tmp_path / "gone.zip", digest(data), progress=None)
    finally:
        server.shutdown()


class Flood(http.server.BaseHTTPRequestHandler):
    """Sends far more than any pin expects: with no Content-Length (path /endless), or announcing it."""
    protocol_version = "HTTP/1.0"

    def do_GET(self):
        self.send_response(200)
        if self.path != "/endless":
            self.send_header("Content-Length", str(50 * 2**20))
        self.end_headers()
        try:
            for _ in range(800):                      # 50 MB, unless the client hangs up first
                self.wfile.write(b"\0" * 65536)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *a):
        pass


def test_a_download_past_its_pinned_size_stops_and_is_deleted(tmp_path):
    """No cap during the download let a host fill the disk before the digest was checked."""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Flood)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        with pytest.raises(fetch.FetchError, match="over the 100000 expected"):
            fetch.fetch(f"{base}/endless", tmp_path / "p.zip", "0" * 64, size=100_000, progress=None)
        with pytest.raises(fetch.FetchError, match="52428800 bytes or more"):
            fetch.fetch(f"{base}/announced", tmp_path / "p.zip", "0" * 64, size=100_000, progress=None)
        assert list(tmp_path.iterdir()) == []
    finally:
        server.shutdown()


def test_concurrent_fetches_of_one_file_each_write_their_own(tmp_path):
    """Two `doctor --fetch --sounds` at once crashed on a shared temporary name."""
    data = bytes(range(256)) * 20_000
    url = served(tmp_path, "pack.zip", data)
    dest, errors = tmp_path / "cache" / "pack.zip", []

    def one():
        try:
            fetch.fetch(url, dest, digest(data), size=len(data), progress=None)
        except BaseException as e:            # noqa: BLE001 (a thread's failure is the test's)
            errors.append(e)
    threads = [threading.Thread(target=one) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == [] and dest.read_bytes() == data and [p.name for p in dest.parent.iterdir()] == ["pack.zip"]


def test_the_cache_lives_under_studio_home_and_ignores_itself(tmp_path, monkeypatch):
    monkeypatch.delenv("STUDIO_CACHE", raising=False)
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    root = fetch.cache_root()
    assert root == tmp_path / "home" / "cache" and not root.exists()      # a check makes nothing
    assert fetch.cache_root(create=True) == root and (root / ".gitignore").read_text() == "*\n"
    monkeypatch.setenv("STUDIO_CACHE", str(tmp_path / "elsewhere"))
    assert fetch.cache_root() == tmp_path / "elsewhere"
