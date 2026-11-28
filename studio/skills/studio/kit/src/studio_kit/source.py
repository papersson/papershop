"""Code tours: real source files at one pinned commit, and the check that every citation is right.

`studio source VIDEO REPO PATH... [--rev REV] [--url URL]` reads each PATH from the git checkout
REPO at REV (default HEAD) with `git show`, writes it to data/source/PATH and lists it in
data/source.json:

    {"repo": "https://github.com/tigerbeetle/tigerbeetle", "commit": "0aeb306…",
     "files": {"src/vsr/replica.zig": {"file": "data/source/src/vsr/replica.zig",
                                       "sha256": "…", "lines": 12459}}}

Running it again for more paths adds them; a different commit replaces the list, so one film
reads one version of the code. The live engine's SourceView (engines/live/src/source.js) draws
the views in data/tour.json.

The `source` check (part of `studio check` whenever data/tour.json or a data/CLIP/tour.json exists) fails when a file's
bytes no longer match its sha256, a view or stop names a file that is not listed, a range runs
past the end of its file or backwards, a focus line is not shown, or a pointed token is not on its
line. It warns when a shown line is wider than the view's `cols`, which would shrink the type.
Wrong line numbers in a code tour are the error a reader notices first and forgives last.
"""
import hashlib
import json
from pathlib import Path

from . import proc


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _git(repo, *args):
    r = proc.run(["git", "-C", str(repo), *args], capture_output=True)
    if r.returncode:
        raise SystemExit(f"git {' '.join(args)} in {repo}: {r.stderr.decode().strip()}")
    return r.stdout


def add(video, repo, paths, rev="HEAD", url=None):
    video, repo = Path(video), Path(repo)
    commit = _git(repo, "rev-parse", rev + "^{commit}").decode().strip()
    index = video / "data" / "source.json"
    data = json.loads(index.read_text()) if index.exists() else {}
    if data.get("commit") and data["commit"] != commit:
        print(f"source: {data['commit'][:7]} → {commit[:7]}: the film now reads the new commit; re-adding its files")
        old = list(data.get("files", {}))
        paths = list(dict.fromkeys(old + list(paths)))
        data["files"] = {}
    if url is None:
        try:
            url = _git(repo, "remote", "get-url", "origin").decode().strip()
        except SystemExit:
            url = data.get("repo")
    data.update({"repo": url, "commit": commit})
    files = data.setdefault("files", {})
    for p in paths:
        body = _git(repo, "show", f"{commit}:{p}")
        out = video / "data" / "source" / p
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(body)
        files[p] = {"file": str(out.relative_to(video)), "sha256": _sha(body),
                    "lines": body.decode("utf-8", "replace").count("\n")}
        print(f"source: {p} @ {commit[:7]}, {files[p]['lines']} lines")
    data["files"] = dict(sorted(files.items()))
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(json.dumps(data, indent=1) + "\n")
    return data


def main(args):
    add(args.video, args.repo, args.paths, args.rev, args.url)
    return 0


def link(source, path, a=None, b=None):
    """A permalink to PATH (lines a to b) at the film's commit, for the Evidence table and the page."""
    base = (source.get("repo") or "").removesuffix(".git")
    url = f"{base}/blob/{source['commit']}/{path}"
    return url + (f"#L{a}" + (f"-L{b}" if b and b != a else "") if a else "")


def tour_files(video):
    """data/tour.json and every chapter's data/CLIP/tour.json."""
    data = Path(video) / "data"
    return [p for p in [data / "tour.json", *sorted(data.glob("*/tour.json"))] if p.exists()]


def check(video):
    """The source check's rows (see the module docstring)."""
    video = Path(video)
    index = video / "data" / "source.json"
    tours = tour_files(video)
    if not tours:
        return []
    rows = []
    bad = lambda detail, t=None: rows.append({"check": "source", "clip": "source", "ok": False, "detail": detail})  # noqa: E731
    warn = lambda detail: rows.append({"check": "source", "clip": "source", "ok": True, "severity": "warning", "detail": detail})  # noqa: E731
    if not index.exists():
        bad("data/tour.json exists but data/source.json does not; run `studio source VIDEO REPO PATH...`")
        return rows
    source = json.loads(index.read_text())
    lines = {}
    for p, f in source.get("files", {}).items():
        fp = video / f["file"]
        if not fp.exists():
            bad(f"{p}: {f['file']} is missing; run `studio source` again")
            continue
        body = fp.read_bytes()
        if _sha(body) != f["sha256"]:
            bad(f"{p}: {f['file']} changed since `studio source` copied it at {source['commit'][:7]}; a tour shows the code as it was")
        lines[p] = body.decode("utf-8", "replace").replace("\r\n", "\n").split("\n")
    stops_n = 0
    views = [(f"{t.parent.name}/{n}" if t.parent.name != "data" else n, v)
             for t in tours for n, v in json.loads(t.read_text()).get("views", {}).items()]
    for name, view in views:
        file, cols = view.get("file"), view.get("cols", 90)
        for i, stop in enumerate(view.get("stops", [])):
            stops_n += 1
            file = stop.get("file", file)
            where = f"view {name}, stop {i + 1} ({stop.get('at')})"
            if file not in lines:
                bad(f"{where}: {file} is not in data/source.json")
                continue
            src, n = lines[file], len(lines[file]) - (1 if lines[file] and lines[file][-1] == "" else 0)
            shown = set()
            prev = 0
            for a, b in stop.get("show", []):
                if a < 1 or b > n or a > b:
                    bad(f"{where}: lines {a}–{b} are outside {file} (1–{n}) or backwards")
                    continue
                if a <= prev:
                    bad(f"{where}: ranges overlap or are out of order at {a}")
                prev = b
                shown.update(range(a, b + 1))
                for k in range(a, b + 1):
                    w = len(src[k - 1].replace("\t", "    "))
                    if w > cols:
                        warn(f"{where}: {file}:{k} is {w} columns, wider than the view's {cols}; "
                             "raise cols (smaller type) or show fewer lines")
            if not stop.get("show"):
                bad(f"{where}: no `show` ranges")
            for a, b in stop.get("focus", []):
                if not set(range(a, b + 1)) <= shown:
                    bad(f"{where}: focus {a}–{b} is not all shown")
            pt = stop.get("point")
            if pt:
                k, text = pt.get("line"), pt.get("text", "")
                if k not in shown:
                    bad(f"{where}: pointed line {k} is not shown")
                elif text not in src[k - 1]:
                    bad(f"{where}: {text!r} is not on {file}:{k} ({src[k - 1].strip()[:60]!r})")
    if not rows or all(r["ok"] for r in rows):
        rows.append({"check": "source", "clip": "source", "ok": True,
                     "detail": f"{len(lines)} files at {source.get('commit', '?')[:7]} match their sha256; "
                               f"{stops_n} stops, every range, focus and pointed token is in its file"})
    return rows
