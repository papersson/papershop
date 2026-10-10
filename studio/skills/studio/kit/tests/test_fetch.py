import hashlib
import http.server
import io
import socket
import threading
import zipfile

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


def make_zip(path, members, links=()):
    with zipfile.ZipFile(path, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
        for name in links:
            info = zipfile.ZipInfo(name)
            info.external_attr = (0o120777 << 16)
            z.writestr(info, "/etc/passwd")
    return path


def test_unpack_takes_only_the_whitelisted_members(tmp_path):
    z = make_zip(tmp_path / "p.zip", {"Audio/a.ogg": b"a", "Audio/b.ogg": b"b", "Kenney.url": b"[InternetShortcut]",
                                      "License.txt": b"CC0"})
    got = fetch.unpack(z, tmp_path / "out", ["Audio/*.ogg", "License.txt"])
    assert sorted(got) == ["Audio/a.ogg", "Audio/b.ogg", "License.txt"]
    assert (tmp_path / "out/Audio/a.ogg").read_bytes() == b"a" and not (tmp_path / "out/Kenney.url").exists()
    flat = fetch.unpack(z, tmp_path / "flat", ["Audio/*"], flatten=True)
    assert sorted(p.name for p in flat.values()) == ["a.ogg", "b.ogg"] and (tmp_path / "flat/a.ogg").exists()


@pytest.mark.parametrize("bad, why", [("../escape.ogg", "leaves the folder"), ("Audio/../../x.ogg", "leaves the folder"),
                                      ("/abs.ogg", "absolute"), ("C:/win.ogg", "absolute"), ("..\\back.ogg", "leaves the folder")])
def test_unpack_refuses_an_archive_with_an_unsafe_name(tmp_path, bad, why):
    z = make_zip(tmp_path / "p.zip", {"Audio/a.ogg": b"a", bad: b"evil"})
    with pytest.raises(fetch.FetchError, match=why):
        fetch.unpack(z, tmp_path / "out", ["*"])
    assert not (tmp_path / "out").exists()                  # checked before anything is written


def test_unpack_refuses_a_symbolic_link(tmp_path):
    z = make_zip(tmp_path / "p.zip", {"Audio/a.ogg": b"a"}, links=["Audio/link.ogg"])
    with pytest.raises(fetch.FetchError, match="symbolic link"):
        fetch.unpack(z, tmp_path / "out", ["Audio/*.ogg"])


def test_flattening_two_members_to_one_name_is_refused(tmp_path):
    z = make_zip(tmp_path / "p.zip", {"a/x.ogg": b"1", "b/x.ogg": b"2"})
    with pytest.raises(fetch.FetchError, match="same name"):
        fetch.unpack(z, tmp_path / "out", ["*"], flatten=True)


def test_the_cache_lives_under_studio_home_and_ignores_itself(tmp_path, monkeypatch):
    monkeypatch.delenv("STUDIO_CACHE", raising=False)
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    root = fetch.cache_root()
    assert root == tmp_path / "home" / "cache" and not root.exists()      # a check makes nothing
    assert fetch.cache_root(create=True) == root and (root / ".gitignore").read_text() == "*\n"
    monkeypatch.setenv("STUDIO_CACHE", str(tmp_path / "elsewhere"))
    assert fetch.cache_root() == tmp_path / "elsewhere"
