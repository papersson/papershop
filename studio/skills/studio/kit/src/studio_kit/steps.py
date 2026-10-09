"""Execute language-neutral full-file program versions; scenes consume the captured artifacts."""
import hashlib
import json
import os
import signal
import tempfile
import time
import uuid
from pathlib import Path

from . import proc
from .workspace import atomic_json


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inside(root, relative):
    root = Path(root).resolve()
    p = (root / relative).resolve()
    if p == root or not p.is_relative_to(root):
        raise SystemExit(f"path escapes its project: {relative}")
    return p


def execute(argv, cwd, timeout):
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
        raise SystemExit("commands must be nonempty argv arrays (no implicit shell)")
    t = time.monotonic()
    p = proc.popen(argv, cwd=cwd, stdout=proc.PIPE, stderr=proc.PIPE, start_new_session=True)
    expired = False
    try:
        out, err = p.communicate(timeout=timeout)
    except proc.TimeoutExpired:
        expired = True
        os.killpg(p.pid, signal.SIGKILL)
        out, err = p.communicate()
    return {"argv": argv, "stdout": out.decode("utf-8", errors="replace"), "stderr": err.decode("utf-8", errors="replace"),
            "exit": p.returncode, "timeout": expired, "seconds": round(time.monotonic() - t, 6)}, out, err


def run(video, manifest):
    video, manifest = Path(video).resolve(), Path(manifest).resolve()
    spec = json.loads(manifest.read_text())
    if spec.get("version") != 1 or not spec.get("steps") or not spec.get("source"):
        raise SystemExit("steps need version: 1, source: {project/file: real-source-file}, and a nonempty steps list")
    ids = [s.get("id") for s in spec["steps"]]
    import re
    if any(not isinstance(i, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", i) for i in ids) or len(ids) != len(set(ids)):
        raise SystemExit("step IDs must be unique path-safe names")
    source = {}
    for name, path in spec["source"].items():
        inside(video / "data" / "steps", name)
        p = (manifest.parent / path).resolve()
        b = p.read_bytes()
        git = proc.run([proc.tool("git"), "-C", str(p.parent), "rev-parse", "HEAD"], capture_output=True, text=True)
        source[name] = {"path": str(p), "sha256": digest(b), "text": b.decode("utf-8"),
                        "commit": git.stdout.strip() if git.returncode == 0 else None}
    # Content-addressed results avoid overwriting evidence from an earlier run.
    input_files = {name: (manifest.parent / path).resolve().read_bytes() for name, path in spec.get("inputs", {}).items()}
    file_versions = []
    for step in spec["steps"]:
        file_versions.append({name: (manifest.parent / path).resolve().read_bytes() for name, path in step["files"].items()})
    key = digest(manifest.read_bytes() + json.dumps(source, sort_keys=True).encode() +
                 b"".join(name.encode() + data for files in [input_files, *file_versions] for name, data in sorted(files.items())))[:16]
    root = video / "data" / "steps"
    key += "-" + uuid.uuid4().hex[:8]
    outdir = root / key
    # A rerun gets a new directory even when its inputs match: external commands can be nondeterministic.
    outdir.mkdir(parents=True, exist_ok=True)
    result = {"version": 1, "manifest": spec, "source": source, "input_hashes": {n: digest(b) for n, b in input_files.items()},
              "steps": [], "ok": True}
    for step, files in zip(spec["steps"], file_versions):
        rec = {"id": step["id"], "files": {n: {"text": b.decode("utf-8"), "sha256": digest(b)} for n, b in files.items()}, "commands": []}
        timeout = float(step.get("timeout", spec.get("timeout", 30)))
        if not 0 < timeout <= 3600:
            raise SystemExit("step timeout must be in (0, 3600] seconds")
        with tempfile.TemporaryDirectory(prefix="studio-step-") as scratch:
            for name, data in {**input_files, **files}.items():
                p = inside(scratch, name)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(data)
            cwd = Path(scratch) if step.get("cwd", ".") == "." else inside(scratch, step["cwd"])
            commands = step.get("commands", spec.get("commands"))
            if not commands:
                raise SystemExit(f"step {step['id']} has no commands")
            rec["ok"] = True
            for i, command in enumerate(commands):
                command = {"argv": command} if isinstance(command, list) else command
                try:
                    run, stdout, stderr = execute(command["argv"], cwd, timeout)
                except OSError as e:
                    run, stdout, stderr = {"argv": command["argv"], "exit": None, "timeout": False, "seconds": 0,
                                           "stdout": "", "stderr": str(e)}, b"", str(e).encode()
                run["expected_exit"] = command.get("expected_exit", 0)
                run["ok"] = not run["timeout"] and run["exit"] == run["expected_exit"]
                prefix = f"{step['id']}-{i}"
                (outdir / f"{prefix}.stdout").write_bytes(stdout)
                (outdir / f"{prefix}.stderr").write_bytes(stderr)
                rec["commands"].append(run)
                rec["ok"] &= run["ok"]
                if not run["ok"]:
                    break
        result["steps"].append(rec)
        result["ok"] &= rec["ok"]
        if not rec["ok"]:
            break
    final = result["steps"][-1]["files"]
    result["source_matches"] = all(n in final and final[n]["sha256"] == s["sha256"] for n, s in source.items())
    result["ok"] &= result["source_matches"]
    atomic_json(outdir / "results.json", result)
    atomic_json(root / "index.json", {"results": f"{key}/results.json", "sha256": digest((outdir / "results.json").read_bytes())})
    return result, outdir / "results.json"


def check(video):
    video = Path(video)
    root = video / "data" / "steps"
    if not (root / "index.json").exists():
        return [{"check": "code-source", "clip": "source", "ok": False, "detail": "run studio steps first"}]
    index = json.loads((root / "index.json").read_text())
    path = inside(root, index["results"])
    data = path.read_bytes()
    result = json.loads(data)
    ok = digest(data) == index["sha256"] and result["ok"]
    final = result["steps"][-1]["files"]
    reasons = []
    for name, source in result["source"].items():
        p = Path(source["path"])
        matches = (p.is_file() and digest(p.read_bytes()) == source["sha256"] and name in final
                   and final[name]["text"].encode() == p.read_bytes())
        ok &= matches
        if not matches:
            reasons.append(f"{name}: real source missing or changed; rerun steps deliberately")
    # The scene must consume recorded results, not an unrelated copy of the source.
    scenes = [p.read_text() for p in (video / "scenes").rglob("*") if p.suffix in (".ts", ".tsx")]
    bound = any(index["results"] in s and "data/steps/" in s for s in scenes)
    if not bound:
        reasons.append(f"scene must import data/steps/{index['results']} and pass its files to CodePanel")
    return [{"check": "code-source", "clip": "source", "ok": bool(ok and bound),
             "detail": "; ".join(reasons) or ("recorded source and scene import match" if ok else "step results failed or changed")}]


def main(args):
    result, path = run(args.video, args.manifest)
    print(f"steps: {'ok' if result['ok'] else 'FAIL'}; {path}")
    return 0 if result["ok"] else 1
