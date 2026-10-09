from studio_kit import publish
from test_render import make_video


def test_page_is_ascii_and_matches_the_drive(tmp_path):
    t = make_video(tmp_path)
    t["tracks"]["narration"][0]["caption"] = "Charged twice · or once"
    author = publish.page_html(t, {"title": "T", "drive": "author"}, 3)
    learner = publish.page_html(t, {"title": "T", "drive": "learner"}, 3)
    script = author.split("<script>", 1)[1]
    script.encode("ascii")
    assert '<meta charset="utf-8">' in author
    assert ">Annotate<" in author and 'data-kind="picture"' in author
    assert ">Lost me here<" in learner and 'data-kind="picture"' not in learner
    assert '"v1 (cut 3)"' in author
    assert "[hidden]{display:none!important}" in author      # buttons without a database stay hidden


def test_poster_offsets_count_from_start_or_back_from_end(tmp_path):
    t = make_video(tmp_path)
    assert publish.poster_time(t, ["s2_01", 1.0]) == 3.5
    assert publish.poster_time(t, ["s2_01", -0.2]) == 3.3


def test_a_piece_without_narration_gets_a_poster(tmp_path):
    t = make_video(tmp_path)
    t["tracks"]["narration"] = []
    assert publish.poster_time(t, None) == 1.0
    assert publish.poster_time({**t, "duration": 1.2}, None) == 0.6


def test_web_settings_fit_the_artifact_limit_at_every_length():
    for seconds in (60, 591, 900, 1493, 3600):
        height, video_kbps, audio_kbps = publish.web_settings(seconds)
        assert (video_kbps + audio_kbps) * 1000 * seconds / 8 <= publish.WEB_LIMIT
        assert height in (1080, 720, 540)
    assert publish.web_settings(591)[0] == 1080 and publish.web_settings(1493)[0] == 720


def test_web_encode_fits_the_limit(tmp_path):
    import subprocess
    src = tmp_path / "src.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1920x1080:d=4:r=30", "-f", "lavfi",
                    "-i", "sine=d=4", "-shortest", "-c:v", "libx264", "-crf", "10", "-c:a", "aac", str(src)], check=True)
    limit = 120_000
    r = publish.web_encode(src, tmp_path / "web.mp4", 4.0, limit=limit)
    assert (tmp_path / "web.mp4").stat().st_size <= limit and r["bytes"] <= limit


def test_web_encode_from_parts_reencodes_only_changed_parts(tmp_path, capsys):
    import subprocess
    parts = []
    for i, colour in enumerate(("red", "blue")):
        f = tmp_path / f"s{i + 1}-final-key{i}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={colour}:s=640x360:d=2:r=30",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(f)], check=True)
        parts.append(f)
    sound = tmp_path / "sound.m4a"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=d=4", "-c:a", "aac", str(sound)], check=True)
    cache = tmp_path / "web"
    r = publish.web_encode(None, tmp_path / "web.mp4", 4.0, parts=parts, sound=sound, cache=cache)
    assert r["bytes"] <= publish.WEB_LIMIT and "encoded 2 chapter(s), 0 unchanged" in capsys.readouterr().out
    publish.web_encode(None, tmp_path / "web.mp4", 4.0, parts=parts, sound=sound, cache=cache)
    assert "encoded 0 chapter(s), 2 unchanged" in capsys.readouterr().out
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                str(tmp_path / "web.mp4")], capture_output=True, text=True).stdout)
    assert abs(dur - 4.0) < 0.1


def test_a_final_cut_is_redone_when_its_sound_is_stale(tmp_path, monkeypatch):
    """The finish runs before the final cut, so a final cut mixed before it has the unfinished sound."""
    from studio_kit import audio, cuts, render
    from studio_kit import timeline as tl
    t = {"tracks": {"scene": [{"id": "s1"}]}}
    monkeypatch.setattr(tl, "load", lambda v: t)
    monkeypatch.setattr(cuts, "latest", lambda v, kinds: 3)
    monkeypatch.setattr(render, "plan", lambda v, t, q: [("s1", "k1", None)])
    monkeypatch.setattr(render, "read_cut", lambda v, n: {"cut": 3, "quality": "final", "video": "video.mp4",
                                                         "clips": [{"id": "s1", "key": "k1"}], "sound": "raw.m4a"})
    monkeypatch.setattr(render, "make_cut", lambda v, q: {"cut": 4})
    monkeypatch.setattr(audio, "soundtrack", lambda v, t: tmp_path / "raw.m4a")
    assert publish.final_cut(tmp_path)["cut"] == 3
    monkeypatch.setattr(audio, "soundtrack", lambda v, t: tmp_path / "finished.m4a")
    assert publish.final_cut(tmp_path)["cut"] == 4
