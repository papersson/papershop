"""Snapshot personal defaults; older videos never read a changing global lexicon."""
import hashlib
import json
import re
import shutil
from pathlib import Path

from . import settings
from .env import studio_home
from .workspace import atomic_json, locked


def snapshot(video):
    video, home = Path(video), studio_home()
    origin = {}
    for name in ("house.md", "lexicon.json"):
        src = home / name
        if not src.exists():
            continue
        dst = video / "research" / name if name == "house.md" else video / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        origin[name] = {"path": str(src), "sha256": hashlib.sha256(src.read_bytes()).hexdigest()}
    if origin:
        atomic_json(video / "research" / "preferences.json", origin)
    script = video / "SCRIPT.md"
    if script.exists():
        with script.open("a") as f:
            f.write(f"\n## House style\n\nSource: {home / 'house.md'}. Read research/house.md when present (creation-time snapshot).\n")


def lexicon(video):
    p = Path(video) / "lexicon.json"
    return json.loads(p.read_text()) if p.exists() else {}


def main_lexicon(args):
    home = studio_home()
    p = home / "lexicon.json"
    if not args.spoken and not args.phonemes:
        raise SystemExit("provide --spoken or --phonemes (Kokoro IPA)")
    home.mkdir(parents=True, exist_ok=True)
    with locked(home):
        cfg = json.loads(p.read_text()) if p.exists() else {}
        if args.spoken:
            pairs = dict(cfg.get("spoken", []))
            pairs[args.word] = args.spoken
            cfg["spoken"] = list(pairs.items())
        if args.phonemes:
            cfg.setdefault("phonemes", {})[args.word] = args.phonemes
        atomic_json(p, cfg)
    print(f"saved {args.word!r} in {p}; existing videos keep their snapshot")


def inherit(video, source, includes=()):
    """Copy selected portable source/evidence and relative module imports, never live links."""
    from .steps import inside
    from .script import sections
    video, source = Path(video), Path(source).resolve()
    source_cfg = settings.raw(source)
    copied = {}

    def copy(rel):
        src = inside(source, rel)
        if src.is_symlink() or not src.is_file():
            raise SystemExit(f"series include is not a regular file: {rel}")
        if src.suffix in (".mp4", ".wav") or Path(rel).parts[0] not in ("scenes", "data", "sims", "assets", "research"):
            raise SystemExit(f"series includes must select source/evidence files: {rel}")
        if str(rel) in copied:
            return
        dst = inside(video, rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        copied[str(rel)] = hashlib.sha256(src.read_bytes()).hexdigest()
        if src.suffix in (".ts", ".tsx", ".js"):
            for module in re.findall(r"(?:from\s*|import\s*|import\s*\()['\"](\.[^'\"]+)['\"]", src.read_text()):
                base = src.parent / module
                candidates = [base, *(Path(str(base) + ext) for ext in (".ts", ".tsx", ".js", ".json")), base / "index.ts", base / "index.tsx"]
                dep = next((p.resolve() for p in candidates if p.is_file()), None)
                if dep is None or not dep.is_relative_to(source):
                    raise SystemExit(f"missing or nonportable series dependency {module} from {rel}")
                copy(dep.relative_to(source))

    for rel in includes:
        copy(Path(rel))
    for name in ("layout.json", "lexicon.json", "narration.json"):
        src = source / name
        if src.exists():
            cfg = json.loads(src.read_text())
            if name == "narration.json":
                for k in ("holds", "spoken_by_id", "phonemes_by_id", "accepted"):
                    cfg.pop(k, None)
            atomic_json(video / name, cfg)
    if any(p.startswith("assets/") for p in copied) and (source / "assets/provenance.json").exists():
        # Preserve the original rows, not a new claim that the sibling video created these assets.
        copy(Path("assets/provenance.json"))
    if (source / "SCRIPT.md").exists():
        evidence = sections((source / "SCRIPT.md").read_text()).get("Evidence", "")
        (video / "research" / "series-evidence.md").write_text(
            f"# Evidence from {source.name}\n\nReference only: select the rows supporting this episode.\n\n" + evidence)
    if (source / "research/house.md").exists():
        shutil.copyfile(source / "research/house.md", video / "research/house.md")
    atomic_json(video / "research" / "series.json", {"source": str(source), "original_source": source_cfg.get("source"), "files": copied})
    return copied
