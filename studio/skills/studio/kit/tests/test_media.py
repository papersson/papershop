import datetime
import hashlib
import json

import pytest

from studio_kit import media, new


class FakeBucket:
    def __init__(self):
        self.objects, self.puts = {}, []

    def has(self, name):
        return name in self.objects

    def put(self, name, path):
        self.puts.append(name)
        self.objects[name] = path.read_bytes()

    def get(self, name, path):
        path.write_bytes(self.objects[name])


def test_requests_are_signed_as_aws_documents_signature_v4():
    """The GET example of Amazon's "Signature Calculations for the Authorization Header"."""
    h = media.sign("GET", "https://examplebucket.s3.amazonaws.com/test.txt", {"Range": "bytes=0-9"},
                   "AKIAIOSFODNN7EXAMPLE", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", region="us-east-1",
                   now=datetime.datetime(2013, 5, 24, tzinfo=datetime.timezone.utc),
                   payload=hashlib.sha256(b"").hexdigest())
    assert h["authorization"] == (
        "AWS4-HMAC-SHA256 Credential=AKIAIOSFODNN7EXAMPLE/20130524/us-east-1/s3/aws4_request, "
        "SignedHeaders=host;range;x-amz-content-sha256;x-amz-date, "
        "Signature=f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41")


def video_with_media(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_HOME", str(tmp_path / "home"))
    v, _ = new.create("v", directory=tmp_path / "video")
    files = {"out/master.mp4": b"master", "assets/sounds/keys.MP3": b"keys", "footage/take1.mov": b"take",
             "cuts/cut1/video.mp4": b"cut", ".cache/sound/mix.m4a": b"mix", "research/reviews/cut1/s0/a.wav": b"r",
             "notes.txt": b"text in git"}
    for rel, data in files.items():
        (v / rel).parent.mkdir(parents=True, exist_ok=True)
        (v / rel).write_bytes(data)
    return v


def test_push_lists_the_media_a_clone_cannot_remake_and_uploads_each_content_once(tmp_path, monkeypatch):
    v = video_with_media(tmp_path, monkeypatch)
    bucket = FakeBucket()
    assert media.push(v, bucket=bucket) == (3, 3, len(b"master") + len(b"keys") + len(b"take"))
    listed = media.load(v)
    assert set(listed) == {"out/master.mp4", "assets/sounds/keys.MP3", "footage/take1.mov"}
    assert listed["out/master.mp4"] == {"sha256": hashlib.sha256(b"master").hexdigest(), "bytes": 6}
    assert set(bucket.objects) == {"sha256/" + e["sha256"] for e in listed.values()}

    (v / "out/web.mp4").write_bytes(b"master")                          # same bytes: listed, not sent again
    media.push(v, [v / "cuts/cut1/video.mp4"], bucket=bucket)          # a file named on purpose is listed
    assert len(bucket.puts) == 4 and {"out/web.mp4", "cuts/cut1/video.mp4"} <= set(media.load(v))
    with pytest.raises(SystemExit, match="not a file"):
        media.push(v, [tmp_path / "elsewhere.mp4"], bucket=bucket)


def test_pull_fetches_what_a_clone_lacks_checks_it_and_keeps_a_local_change(tmp_path, monkeypatch):
    v = video_with_media(tmp_path, monkeypatch)
    bucket = FakeBucket()
    media.push(v, bucket=bucket)
    (v / "out/master.mp4").unlink()
    (v / "footage/take1.mov").write_bytes(b"edited here")
    assert dict(media.pull(v, bucket=bucket, dry_run=True))["out/master.mp4"].startswith("missing")
    assert not (v / "out/master.mp4").exists()
    report = dict(media.pull(v, bucket=bucket))
    assert report["out/master.mp4"] == "fetched" and (v / "out/master.mp4").read_bytes() == b"master"
    assert report["assets/sounds/keys.MP3"] == "present"
    assert report["footage/take1.mov"].startswith("differs") and (v / "footage/take1.mov").read_bytes() == b"edited here"
    media.pull(v, bucket=bucket, force=True)
    assert (v / "footage/take1.mov").read_bytes() == b"take"

    (v / "out/master.mp4").unlink()
    bucket.objects["sha256/" + hashlib.sha256(b"master").hexdigest()] = b"corrupt"
    with pytest.raises(SystemExit, match="does not match"):
        media.pull(v, bucket=bucket)
    assert not (v / "out/master.mp4").exists() and not (v / "out/.master.mp4.part").exists()


def test_a_listed_file_this_machine_never_pulled_stays_listed(tmp_path, monkeypatch):
    v = video_with_media(tmp_path, monkeypatch)
    bucket = FakeBucket()
    media.push(v, bucket=bucket)
    (v / "footage/take1.mov").unlink()
    media.push(v, bucket=bucket)
    assert "footage/take1.mov" in json.loads((v / "media.json").read_text())["files"]


def test_without_credentials_nothing_is_transferred_and_the_fix_is_named(tmp_path, monkeypatch):
    for k in ("ENDPOINT", "ACCESS_KEY_ID", "SECRET_ACCESS_KEY"):
        monkeypatch.delenv(f"RCLONE_CONFIG_R2_{k}", raising=False)
    monkeypatch.setenv("PAPERSHOP_SECRETS", str(tmp_path / "none.json"))
    with pytest.raises(SystemExit, match="SOPS_AGE_KEY"):
        media.Bucket.from_secrets()
