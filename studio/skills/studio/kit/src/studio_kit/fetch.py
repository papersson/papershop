"""Pinned downloads: a URL fetched once into the cache, verified by its sha256, and unpacked safely.

Every download the kit makes for data (the sound kit's packs) names its digest in a committed
manifest, so what arrives is what was reviewed, or nothing: a mismatch deletes the file and stops,
naming the URL and both digests. A file already in the cache with the right digest is not fetched
again. A download is written to a temporary file beside its destination and renamed into place
once verified, so an interrupted fetch never leaves a file that looks complete.

The cache is $STUDIO_HOME/cache/ (STUDIO_CACHE overrides it): one per user, shared by every video
and every pinned kit, and outside the plugin, whose folder an update replaces. Cached paths carry
the digest, so a pinned kit with an older manifest finds its own files beside a newer kit's.
"""
import fnmatch
import hashlib
import os
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from .env import studio_home

CHUNK = 1 << 16
UNPACK_LIMIT = 512 * 2**20     # bytes: an archive that unpacks to more than this is refused


class FetchError(SystemExit):
    """A download or unpack that failed; the message says what and how to repair it."""


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
    mismatch; neither leaves a file at `dest` or a partial one beside it."""
    dest = Path(dest)
    if verified(dest, sha256):
        return dest
    if dest.exists():
        print(f"{dest} does not match its pinned digest; fetching it again", file=progress or sys.stderr)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dest.parent, prefix=f".{dest.name}.", suffix=".part")
    tmp = Path(tmp)
    try:
        h, done = hashlib.sha256(), 0
        try:
            with os.fdopen(fd, "wb") as f, urllib.request.urlopen(url, timeout=timeout) as r:
                total = int(r.headers.get("Content-Length") or 0) or size
                for block in iter(lambda: r.read(CHUNK), b""):
                    f.write(block)
                    h.update(block)
                    done += len(block)
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
        actual = h.hexdigest()
        if actual != sha256:
            raise FetchError(f"{url} did not match its pinned digest: expected sha256 {sha256}, got {actual} "
                             f"({done} bytes); the download was deleted. The file at the URL changed: "
                             "review it before updating the manifest")
        if size is not None and done != size:
            raise FetchError(f"{url} is {done} bytes, the manifest says {size}; the download was deleted")
        os.replace(tmp, dest)
        return dest
    finally:
        tmp.unlink(missing_ok=True)


def _unsafe(info):
    """Why a zip member may not be unpacked, or None. Names are checked in both slash styles, since
    a zip made on Windows may use backslashes."""
    name = info.filename.replace("\\", "/")
    p = PurePosixPath(name)
    if name.startswith("/") or (len(name) > 1 and name[1] == ":"):
        return "an absolute path"
    if ".." in p.parts:
        return "a path that leaves the folder"
    if (info.external_attr >> 16) & 0o170000 == 0o120000:
        return "a symbolic link"
    return None


def unpack(archive, dest, members=("*",), flatten=False):
    """The files of zip `archive` whose names match one of the glob patterns `members`, written
    under `dest` (at their base names when `flatten`). Every member is checked before anything is
    written: an absolute name, a `..` or a symbolic link anywhere in the archive refuses it whole.
    Returns {member name: written path}."""
    archive, dest = Path(archive), Path(dest)
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        bad = [(i.filename, why) for i in infos if (why := _unsafe(i))]
        if bad:
            raise FetchError(f"{archive.name} holds {bad[0][0]!r}, {bad[0][1]}; refusing to unpack it")
        chosen = [i for i in infos if not i.is_dir() and any(fnmatch.fnmatchcase(i.filename, m) for m in members)]
        names = [PurePosixPath(i.filename).name if flatten else i.filename for i in chosen]
        if len(set(names)) != len(names):
            raise FetchError(f"{archive.name}: two members unpack to the same name; unpack without flatten")
        if sum(i.file_size for i in chosen) > UNPACK_LIMIT:
            raise FetchError(f"{archive.name} unpacks to more than {UNPACK_LIMIT // 2**20} MB; refusing it")
        written = {}
        for info, name in zip(chosen, names):
            out = dest / name
            out.parent.mkdir(parents=True, exist_ok=True)
            tmp = out.with_name(f".{out.name}.part")
            with z.open(info) as src, open(tmp, "wb") as f:
                for block in iter(lambda: src.read(CHUNK), b""):
                    f.write(block)
            os.replace(tmp, out)
            written[info.filename] = out
    return written
