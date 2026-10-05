import json

from studio_kit import clean, render
from test_narration import SCRIPT
from test_render import make_video

PROTECTED = ["SCRIPT.md", "scenes/s1.tsx", "data/x.json", "sims/x.py", "research/r.md", "narration.json",
             "timeline.json", "audio/narration.mp3", "audio/narration.wav", "out/master.mp4", "out/page/video.mp4",
             "review/notes.jsonl", "audio/elevenlabs_cache/abc.json"]


def cuts(video, n):
    for i in range(1, n + 1):
        d = video / "cuts" / f"cut{i}"
        (d / "stills").mkdir(parents=True)
        (d / "cut.json").write_text(json.dumps({"cut": i, "quality": "draft", "video": "video.mp4"}))
        (d / "stills" / "s1.jpg").write_bytes(b"s" * 100)
        (d / "video.mp4").write_bytes(b"x" * 1000)


def test_prune_keeps_all_movies_and_records_but_removes_old_unprotected_previews(tmp_path):
    cuts(tmp_path, 14)
    (tmp_path / "video.json").write_text(json.dumps({"keep_cuts": 3}))
    (tmp_path / "review").mkdir()
    (tmp_path / "review" / "notes.jsonl").write_text("\n".join(json.dumps({"type": "round", "cut": n}) for n in (2, 4)) + "\n")
    from studio_kit.cuts import mark_watched
    mark_watched(tmp_path, 3)
    (tmp_path / "cuts/cut5/cut.json").write_text(json.dumps({"quality": "final"}))
    (tmp_path / "cuts/cut6/cut.json").write_text("{}")  # unknown legacy quality
    freed = clean.prune_cuts(tmp_path)
    assert freed > 0
    for n in range(1, 15):
        assert (tmp_path / f"cuts/cut{n}/video.mp4").exists()
        assert (tmp_path / f"cuts/cut{n}/cut.json").exists()
        assert (tmp_path / f"cuts/cut{n}/stills").exists() == (n in (2, 3, 4, 5, 6, 12, 13, 14))
    clean.clean(tmp_path, videos=True)
    for n in range(1, 15):
        assert (tmp_path / f"cuts/cut{n}/video.mp4").exists() == (n in (2, 3, 4, 5, 6, 12, 13, 14))
        assert (tmp_path / f"cuts/cut{n}/cut.json").exists()
    assert json.loads((tmp_path / "cuts/cut1/cut.json").read_text())["video"] is None


def test_stills_only_does_not_displace_playable_or_noted_cut(tmp_path):
    cuts(tmp_path, 2)
    (tmp_path / "video.json").write_text('{"keep_cuts": 1}')
    (tmp_path / "review").mkdir()
    (tmp_path / "review/notes.jsonl").write_text('{"type":"note","cut":1}\n')
    for n in range(3, 20):
        d = tmp_path / f"cuts/cut{n}"
        d.mkdir()
        (d / "cut.json").write_text('{"quality":"draft","video":null}')
    clean.clean(tmp_path, videos=True)
    assert (tmp_path / "cuts/cut1/video.mp4").exists()
    assert (tmp_path / "cuts/cut2/video.mp4").exists()




def test_clean_removes_regenerable_files_only_and_dry_run_removes_nothing(tmp_path):
    t = make_video(tmp_path)
    for p in PROTECTED:
        f = tmp_path / p
        f.parent.mkdir(parents=True, exist_ok=True)
        if not f.exists():
            f.write_text({"narration.json": "{}", "review/notes.jsonl": "", "SCRIPT.md": SCRIPT}.get(p, "keep"))
    cuts(tmp_path, 5)
    cache = tmp_path / ".cache"
    current = f"s1-draft-{render.clip_key(tmp_path, t, 's1', 'draft')}.mp4"
    (cache / "clips").mkdir(parents=True)
    (cache / "clips" / current).write_bytes(b"c" * 100)
    (cache / "clips" / "s1-draft-0000000000000000.mp4").write_bytes(b"c" * 100)
    (cache / "clips" / "s9-final-0000000000000000.mp4").write_bytes(b"c" * 100)
    (cache / "narration").mkdir()
    (cache / "narration" / "deadbeefdeadbeef.npy").write_bytes(b"n" * 100)
    from studio_kit import narration as nr, script as sc
    S = nr.Settings(tmp_path)
    used = nr.kokoro_key(S, " ".join(x for _, x, _ in nr.all_chunks(S, sc.load(tmp_path))[0][0]))
    (cache / "narration" / f"{used}.npy").write_bytes(b"u" * 100)
    (tmp_path / "out" / "sheets").mkdir(parents=True)
    (tmp_path / "out" / "sheets" / "phone.png").write_bytes(b"s" * 100)
    (tmp_path / "out" / "web.mp4").write_bytes(b"w" * 100)
    before = sorted(str(p) for p in tmp_path.rglob("*"))
    total, _ = clean.clean(tmp_path, dry_run=True)
    assert total > 0 and sorted(str(p) for p in tmp_path.rglob("*")) == before
    total2, by = clean.clean(tmp_path)
    assert total2 == total
    for p in PROTECTED:
        assert (tmp_path / p).exists(), p
    assert (cache / "clips" / current).exists()
    assert not (cache / "clips" / "s1-draft-0000000000000000.mp4").exists()
    assert not (cache / "clips" / "s9-final-0000000000000000.mp4").exists()
    assert not (cache / "narration" / "deadbeefdeadbeef.npy").exists()
    assert (cache / "narration" / f"{used}.npy").exists()
    assert not (tmp_path / "out" / "sheets").exists() and not (tmp_path / "out" / "web.mp4").exists()
    assert sorted(p.name for p in (tmp_path / "cuts").iterdir()) == ["cut1", "cut2", "cut3", "cut4", "cut5"]
