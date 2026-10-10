"""Pinned downloads: a URL fetched once into the cache and verified by its size and sha256.

Every download the kit makes for data (the sound kit's packs) names its digest in a committed
manifest, so what arrives is what was reviewed, or nothing: a mismatch deletes the file and stops,
naming the URL and both digests. A file already in the cache with the right digest is not fetched
again. A download is written to a temporary file beside its destination and renamed into place
once verified, so an interrupted fetch never leaves a file that looks complete, and two fetches
of the same file at once each write their own. The download stops as soon as more than the expected
size has arrived, so a host can't fill the disk before the digest is checked.

Nothing is unpacked: a pack stays one verified zip, and a sound is read from it by its member name
(soundkit.read_member), so no archive's paths ever reach the file system.

The cache is $STUDIO_HOME/cache/ (STUDIO_CACHE overrides it): one per user, shared by every video
and every pinned kit, and outside the plugin, whose folder an update replaces. Cached paths carry
the digest, so a pinned kit with an older manifest finds its own files beside a newer kit's.
"""
import hashlib
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from .env import studio_home

CHUNK = 1 << 16
MAX_BYTES = 512 * 2**20        # bytes: the most a download without a pinned size may be


class FetchError(SystemExit):
    """A download that failed; the message says what and how to repair it."""


class Offline(FetchError):
    """The host could not be reached: no network, a proxy, or a timeout."""


def cache_root(create=False):
    """The download cache. `create` makes it, with a .gitignore of its own, so a STUDIO_HOME that is
    a repository never commits it; a check only reads it."""
    root = Path(os.environ.get("STUDIO_CACHE") or studio_home() / "cache").expanduser()
    if create:
        root.mkdir(parents=True, exist_ok=True)
        (root / ".gitignore").exists() or (root / ".gitignore").write_text("*\n")
    return root


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def verified(path, sha256):
    path = Path(path)
    return path.is_file() and sha256_of(path) == sha256


def _progress(url, done, total, out):
    if out is None:
        return
    size = f"{done // 1024} KB" + (f" of {total // 1024} KB ({100 * done // total}%)" if total else "")
    print(f"\rfetching {url}: {size}", end="", file=out, flush=True)


def fetch(url, dest, sha256, size=None, timeout=30, progress=sys.stderr):
    """`dest`, downloaded from `url` unless it is already there with digest `sha256`. Raises Offline
    when the host can't be reached and FetchError on any other failure or a digest or size
    mismatch; neither leaves a file at `dest` or a partial one beside it. More than `size` bytes
    (MAX_BYTES when it is None) stops the download there."""
    dest = Path(dest)
    if verified(dest, sha256):
        return dest
    if dest.exists():
        print(f"{dest} does not match its pinned digest; fetching it again", file=progress or sys.stderr)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dest.parent, prefix=f".{dest.name}.", suffix=".part")
    tmp = Path(tmp)
    try:
        h, done, limit = hashlib.sha256(), 0, MAX_BYTES if size is None else size
        too_big = lambda n: FetchError(f"{url} sent {n} bytes or more, over the {limit} expected; "
                                       "stopped and deleted the download")
        try:
            with os.fdopen(fd, "wb") as f, urllib.request.urlopen(url, timeout=timeout) as r:
                total = int(r.headers.get("Content-Length") or 0) or size
                if total and total > limit:
                    raise too_big(total)
                for block in iter(lambda: r.read(CHUNK), b""):
                    done += len(block)
                    if done > limit:
                        raise too_big(done)
                    f.write(block)
                    h.update(block)
                    _progress(url, done, total, progress)
        except urllib.error.HTTPError as e:
            raise FetchError(f"{url}: HTTP {e.code} {e.reason}; the pinned URL may have moved (a manifest update is needed)")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            reason = getattr(e, "reason", e)
            raise Offline(f"could not reach {url} ({reason}); check the network or proxy, or fetch on a machine "
                          "that can reach it and copy the cache over")
        finally:
            if progress is not None and done:
                print(file=progress)
        if size is not None and done != size:
            raise FetchError(f"{url} is {done} bytes, the manifest says {size}; the download was deleted")
        actual = h.hexdigest()
        if actual != sha256:
            raise FetchError(f"{url} did not match its pinned digest: expected sha256 {sha256}, got {actual} "
                             f"({done} bytes); the download was deleted. The file at the URL changed: "
                             "review it before updating the manifest")
        os.replace(tmp, dest)
        return dest
    finally:
        tmp.unlink(missing_ok=True)
