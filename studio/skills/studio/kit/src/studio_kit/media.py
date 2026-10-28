"""A video's media on any machine: media.json in Git names each file by its SHA-256, the bytes live in
the media bucket under that hash, and `studio media pull` brings back what a clone lacks.

Git keeps the text a video is made from; a checkpoint leaves media out (checkpoint.MEDIA). What a clone
then cannot remake, a recording, a downloaded asset, a shipped master, `push` uploads and lists. The
default set is every file the video's Git ignores with a media extension, outside the caches, cut
folders and review bundles, which studio makes again; a file passed by name is listed too, and a
listed file stays listed. Objects are named by content, so a file that comes back unchanged costs
nothing, two videos sharing a sound share one object, and a download is checked against its hash
before it replaces anything.

The bucket speaks S3 (Cloudflare R2). Its credentials are papershop's RCLONE_CONFIG_R2_* secrets (the
names rclone reads), from the environment or decrypted at the moment of a transfer; requests are
signed here with AWS Signature V4, so no client needs installing.
"""
import datetime
import hashlib
import hmac
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import checkpoint, proc
from .workspace import atomic_json

MANIFEST = "media.json"
REMADE = (".cache/", "cuts/", "research/", "node_modules/", ".venv/", ".studio/")
KINDS = {f".{e}" for e in checkpoint.MEDIA}
PREFIX = "sha256/"
CHUNK = 1 << 20


# --- signing ---------------------------------------------------------------------------------------

def _hmac(key, text):
    return hmac.new(key, text.encode(), hashlib.sha256).digest()


def sign(method, url, headers, access, secret, region="auto", now=None, payload="UNSIGNED-PAYLOAD"):
    """HEADERS plus x-amz-date, x-amz-content-sha256 and the Authorization of AWS Signature V4."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    stamp, day = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
    u = urllib.parse.urlsplit(url)
    h = {k.lower(): str(v).strip() for k, v in headers.items()}
    h.update({"host": u.netloc, "x-amz-date": stamp, "x-amz-content-sha256": payload})
    names = sorted(h)
    query = "&".join(sorted(f"{urllib.parse.quote(k, safe='-_.~')}={urllib.parse.quote(v, safe='-_.~')}"
                            for k, v in urllib.parse.parse_qsl(u.query, keep_blank_values=True)))
    canonical = "\n".join([method, urllib.parse.quote(u.path or "/", safe="/-_.~"), query,
                           "".join(f"{n}:{h[n]}\n" for n in names), ";".join(names), payload])
    scope = f"{day}/{region}/s3/aws4_request"
    text = "\n".join(["AWS4-HMAC-SHA256", stamp, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    key = _hmac(_hmac(_hmac(_hmac(("AWS4" + secret).encode(), day), region), "s3"), "aws4_request")
    signature = hmac.new(key, text.encode(), hashlib.sha256).hexdigest()
    h["authorization"] = f"AWS4-HMAC-SHA256 Credential={access}/{scope}, SignedHeaders={';'.join(names)}, Signature={signature}"
    return h


# --- the bucket ------------------------------------------------------------------------------------

NO_KEYS = ("no media bucket credentials: this machine can't decrypt papershop's RCLONE_CONFIG_R2_* secrets. "
           "In a cloud session, set SOPS_AGE_KEY in the environment's variables and allow the bucket's host; "
           "elsewhere, `script/secrets init NAME` (see script/doctor). Nothing was transferred")


class Bucket:
    """The media bucket over S3: has, put and get by object name."""

    def __init__(self, endpoint, name, access, secret):
        self.base, self.access, self.secret = f"{endpoint.rstrip('/')}/{name}/", access, secret

    @classmethod
    def from_secrets(cls):
        from .narration import secret
        keys = [secret(f"RCLONE_CONFIG_R2_{k}") for k in ("ENDPOINT", "ACCESS_KEY_ID", "SECRET_ACCESS_KEY")]
        if not all(keys):
            raise SystemExit(NO_KEYS)
        return cls(keys[0], os.environ.get("STUDIO_MEDIA_BUCKET", "studio-media"), *keys[1:])

    def _open(self, method, name, data=None, headers=None):
        url = self.base + urllib.parse.quote(name)
        req = urllib.request.Request(url, method=method, data=data,
                                     headers=sign(method, url, headers or {}, self.access, self.secret))
        return urllib.request.urlopen(req, timeout=600)

    def has(self, name):
        try:
            self._open("HEAD", name).close()
            return True
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False
            raise SystemExit(f"media bucket refused HEAD {name}: HTTP {e.code}")

    def put(self, name, path):
        with open(path, "rb") as f:
            try:
                self._open("PUT", name, data=f, headers={"content-length": os.path.getsize(path)}).close()
            except urllib.error.HTTPError as e:
                raise SystemExit(f"media bucket refused PUT {name}: HTTP {e.code}")

    def get(self, name, path):
        try:
            with self._open("GET", name) as r, open(path, "wb") as f:
                while chunk := r.read(CHUNK):
                    f.write(chunk)
        except urllib.error.HTTPError as e:
            raise SystemExit(f"media bucket has no {name} (HTTP {e.code})")


# --- the manifest ----------------------------------------------------------------------------------

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


def load(video):
    p = Path(video) / MANIFEST
    return json.loads(p.read_text())["files"] if p.exists() else {}


def candidates(video):
    """The files Git leaves out that a clone cannot remake: ignored, a media kind, not a cache or a cut's."""
    r = proc.run([proc.tool("git"), "-C", str(video), "ls-files", "-o", "-i", "--exclude-standard", "-z", "--", "."],
                 capture_output=True, text=True, check=True)
    return sorted(f for f in r.stdout.split("\0")
                  if f and Path(f).suffix.lower() in KINDS and not f.startswith(REMADE))


def push(video, paths=(), bucket=None):
    """Upload what the bucket lacks and rewrite media.json; returns (listed, uploaded, bytes uploaded)."""
    video = Path(video).resolve()
    files = load(video)
    named = [os.path.relpath(Path(p).resolve(), video) for p in paths]
    if bad := [n for n in named if n.startswith("..") or not (video / n).is_file()]:
        raise SystemExit(f"not a file in {video}: {', '.join(bad)}")
    bucket = bucket or Bucket.from_secrets()
    sent = size = 0
    for rel in sorted(set(candidates(video)) | set(named) | set(files)):
        f = video / rel
        if not f.is_file():
            continue                          # listed, but never pulled to this machine: the entry stands
        digest = sha256(f)
        if not bucket.has(PREFIX + digest):
            bucket.put(PREFIX + digest, f)
            sent, size = sent + 1, size + f.stat().st_size
        files[rel] = {"sha256": digest, "bytes": f.stat().st_size}
    atomic_json(video / MANIFEST, {"files": dict(sorted(files.items()))})
    return len(files), sent, size


def pull(video, bucket=None, dry_run=False, force=False):
    """Fetch each listed file this folder lacks, checked against its hash; returns [(path, what happened)]."""
    video = Path(video).resolve()
    files = load(video)
    if not files:
        return []
    todo, report = [], []
    for rel, entry in files.items():
        f = video / rel
        if not f.exists():
            todo.append((rel, entry))
        elif sha256(f) != entry["sha256"]:
            if force:
                todo.append((rel, entry))
            else:
                report.append((rel, "differs from media.json; kept this copy (push to list it, --force to replace it)"))
        else:
            report.append((rel, "present"))
    if dry_run:
        return report + [(rel, f"missing, {e['bytes'] / 1e6:.1f} MB to fetch") for rel, e in todo]
    bucket = bucket or (Bucket.from_secrets() if todo else None)
    for rel, entry in todo:
        f = video / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_name(f".{f.name}.part")
        try:
            bucket.get(PREFIX + entry["sha256"], tmp)
            if sha256(tmp) != entry["sha256"]:
                raise SystemExit(f"{rel}: the download does not match media.json's SHA-256; nothing was replaced")
            tmp.replace(f)
        finally:
            tmp.unlink(missing_ok=True)
        report.append((rel, "fetched"))
    return report


def main(args):
    if args.action == "push":
        listed, sent, size = push(args.video, args.paths)
        print(f"media.json lists {listed} file{'s' * (listed != 1)}; uploaded {sent} ({size / 1e6:.1f} MB), the rest were in the bucket")
        return 0
    if args.paths:
        raise SystemExit("pull takes no paths: it fetches what media.json lists")
    report = pull(args.video, dry_run=args.dry_run, force=args.force)
    if not report:
        print(f"no {MANIFEST} here: nothing to pull")
    for rel, what in report:
        print(f"{rel}: {what}")
    return 0
